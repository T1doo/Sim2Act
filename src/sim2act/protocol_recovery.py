"""State-only protocol recovery: never continue, reconstruct, refund or resend."""

import time

from fastapi import Depends
from pydantic import Field
from sqlalchemy import select, update

from .contracts import Strict
from .db import attempts, events, fingerprint, operations, runs
from .errors import DomainError


class RecoveryInput(Strict):
    expected_version: int = Field(ge=1)
    expected_fence: int = Field(ge=0)
    request_key: str = Field(min_length=1, max_length=100)


def _is_protocol(c, run):
    from .protocol_jobs import protocol_run_ids

    return run["id"] in protocol_run_ids(c)


def _evidence(c, rid):
    from .db import protocol_request_slots

    actual_attempts = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().all()
    actual_operations = (
        c.execute(select(operations).where(operations.c.run_id == rid)).mappings().all()
    )
    slots = (
        c.execute(select(protocol_request_slots).where(protocol_request_slots.c.run_id == rid))
        .mappings()
        .all()
    )
    completed = c.execute(
        select(events.c.id).where(events.c.run_id == rid, events.c.kind == "PROTOCOL_COMPLETED")
    ).first()
    return actual_attempts, actual_operations, slots, completed


def _pool_state(c, snapshot):
    from .protocol_pool import audit_pool, selected_pool

    selected = selected_pool(snapshot["scope"]["mode"])
    if snapshot.get("request_pool_id") != selected:
        raise DomainError("VERSION_CONFLICT", "Accepted shared pool binding changed")
    return audit_pool(c, selected)


def _blocked(pool):
    return bool(
        pool["halted"]
        or pool["has_pending"]
        or pool["has_unknown"]
        or pool["reserved_requests"] >= pool["request_limit"]
        or pool["reserved_tokens"] >= pool["token_limit"]
    )


def _classify(store, c, run, job):
    """A complete result must already pass persisted verification; no rebuilding."""
    actual_attempts, actual_operations, slots, completed = _evidence(c, run["id"])
    if job["result"] is not None:
        if job["phase"] in {"source", "cold"} and run["status"] == "SUCCEEDED":
            from .protocol_reviews import review_proof

            review_proof(store, c, run["principal_id"], run["id"])
        if run["status"] == "WAITING_APPROVAL":
            return "AWAITING_REVIEW", None
        if run["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            return "TERMINAL_PRESERVED", None
        raise DomainError("VERSION_CONFLICT", "Completed protocol result state changed")
    if run["status"] in {"SUCCEEDED", "PARTIAL"}:
        raise DomainError("VERIFICATION_FAILED", "Success has no sealed protocol result")
    if (
        {a["id"] for a in actual_attempts} != {s["attempt_id"] for s in slots}
        or any(a["status"] == "STARTED" for a in actual_attempts)
        or any(s["status"] in {"STARTED", "UNKNOWN"} for s in slots)
        or store.has_unknown(c, run["id"])
    ):
        return "STOPPED_UNKNOWN", "RECONCILING" if run["cancel_intent"] else "WAITING_RESOURCE"
    if actual_attempts or actual_operations or slots or completed:
        # Even a known response does not certify a missing atomic completion.
        return "CONTINUATION_NOT_IMPLEMENTED", "WAITING_RESOURCE"
    if run["context"].get("requests") != 0:
        return "STOPPED_UNKNOWN", "WAITING_RESOURCE"
    if run["cancel_intent"]:
        return "UNSENT_CANCELLED", "CANCELLED"
    return "UNSENT_PAUSED", "PAUSED"


def recover_expired_protocols(store):
    """Each Run's project -> Run -> pool locks end before another Run is read.

    Normal Store.claim owns a separate transaction with no pool lock. In
    particular, no recovery pool lock is carried into another project's claim.
    """
    from .protocol_jobs import protocol_run_ids

    with store.engine.connect() as c:
        ids = protocol_run_ids(c)
        candidates = (
            c.execute(
                select(runs.c.id, runs.c.project_id, runs.c.principal_id)
                .where(
                    runs.c.id.in_(ids),
                    runs.c.status.in_(["RUNNING", "PAUSE_REQUESTED", "CANCEL_REQUESTED"]),
                    runs.c.lease_until <= time.time(),
                )
                .order_by(runs.c.project_id, runs.c.id)
            )
            .mappings()
            .all()
        )
    for candidate in candidates:
        try:
            with store.tx() as c:
                store.lock_project(c, candidate["principal_id"], candidate["project_id"])
                current = (
                    c.execute(
                        select(runs)
                        .where(runs.c.id == candidate["id"])
                        .with_for_update(skip_locked=True)
                    )
                    .mappings()
                    .first()
                )
                if (
                    current
                    and current["status"] in {"RUNNING", "PAUSE_REQUESTED", "CANCEL_REQUESTED"}
                    and current["lease_until"] <= time.time()
                ):
                    recover_expired(store, c, current)
        except DomainError:
            # A corrupt/foreign namespace marker cannot enter generic recovery.
            # Leave it stopped for explicit owner inspection; disclose no data.
            continue


def recover_expired(store, c, run):
    """Handle only expired protocol claims inside Store.claim's existing transaction.

    Return True even when authority/evidence is corrupt, so generic F1 recovery
    cannot queue the namespace. Failure returns metadata only, with no provider.
    """
    if not _is_protocol(c, run):
        return False
    from .protocol_jobs import verified_pending

    reason, state = "RECOVERY_REQUIRES_INSPECTION", "WAITING_RESOURCE"
    try:
        job, current = verified_pending(store, c, run["principal_id"], run["id"])
        if current["lease_until"] > time.time():
            return True
        pool = _pool_state(c, job["snapshot"])
        reason, classified = _classify(store, c, current, job)
        if not pool["consistent"]:
            reason, classified = "STOPPED_UNKNOWN", "WAITING_RESOURCE"
        if reason == "STOPPED_UNKNOWN":
            from .protocol_pool import halt_unknown_in_tx

            halt_unknown_in_tx(store, c, job["snapshot"]["request_pool_id"], "RECOVERY_UNKNOWN")
        state = classified or "WAITING_RESOURCE"
    except DomainError as exc:
        reason = exc.code
        if run["cancel_intent"] and store.has_unknown(c, run["id"]):
            state = "RECONCILING"
    # Advance ownership exactly once; all old in-flight writers are fenced out.
    c.execute(
        update(runs)
        .where(
            runs.c.id == run["id"], runs.c.fence == run["fence"], runs.c.version == run["version"]
        )
        .values(
            status=state,
            fence=run["fence"] + 1,
            version=run["version"] + 1,
            lease_until=0,
            worker_id=None,
            error={"code": "OUTCOME_UNKNOWN" if reason == "STOPPED_UNKNOWN" else reason},
        )
    )
    store.event(
        c,
        run["id"],
        "PROTOCOL_RECOVERY_STATE",
        {"status": state, "reason": reason, "provider_requests": 0, "receipts_preserved": True},
    )
    return True


def recover(store, user, rid, request):
    """Owner-authorized, idempotent state inspection; no execution continuation."""
    request = RecoveryInput.model_validate(request)
    from .protocol_jobs import _dependencies, verified_pending

    with store.tx() as c:
        job, run = verified_pending(store, c, user, rid)
        _dependencies(store, c, user, job["snapshot"])
        pool = _pool_state(c, job["snapshot"])
        if not pool["consistent"]:
            raise DomainError("OUTCOME_UNKNOWN", "Shared pool and actual Attempts disagree")
        prior = (
            c.execute(
                select(events.c.data).where(
                    events.c.run_id == rid, events.c.kind == "PROTOCOL_RECOVERY_REQUEST"
                )
            )
            .scalars()
            .all()
        )
        if any(
            not isinstance(p, dict) or set(p) != {"request_key", "request_fingerprint", "response"}
            for p in prior
        ):
            raise DomainError("VERSION_CONFLICT")
        matched = [p for p in prior if p.get("request_key") == request.request_key]
        if matched:
            if len(matched) != 1 or matched[0]["request_fingerprint"] != fingerprint(
                request.model_dump()
            ):
                raise DomainError("VERSION_CONFLICT")
            reason, _ = _classify(store, c, run, job)
            response = _response(run, reason, _blocked(pool))
            if fingerprint(matched[0]["response"]) != fingerprint(response):
                raise DomainError("VERSION_CONFLICT")
            return {**response, "cached": True}
        if run["version"] != request.expected_version or run["fence"] != request.expected_fence:
            raise DomainError("VERSION_CONFLICT")
        if (
            run["status"] in {"RUNNING", "PAUSE_REQUESTED", "CANCEL_REQUESTED"}
            and run["lease_until"] > time.time()
        ):
            raise DomainError("VERSION_CONFLICT", "Current worker ownership is still active")
        reason, state = _classify(store, c, run, job)
        if reason == "STOPPED_UNKNOWN":
            from .protocol_pool import halt_unknown_in_tx

            halt_unknown_in_tx(store, c, job["snapshot"]["request_pool_id"], "RECOVERY_UNKNOWN")
        if run["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            state = None  # Inspection never reopens a terminal run.
        if state is not None and state != run["status"]:
            values = {
                "status": state,
                "version": run["version"] + 1,
                "fence": run["fence"] + 1,
                "lease_until": 0,
                "worker_id": None,
                "error": {"code": "OUTCOME_UNKNOWN" if reason == "STOPPED_UNKNOWN" else reason},
            }
            c.execute(update(runs).where(runs.c.id == rid).values(**values))
            run = {**run, **values}
        response = _response(run, reason, _blocked(pool))
        store.event(
            c,
            rid,
            "PROTOCOL_RECOVERY_REQUEST",
            {
                "request_key": request.request_key,
                "request_fingerprint": fingerprint(request.model_dump()),
                "response": response,
            },
        )
        return response


def _response(run, reason, global_send_blocked):
    return {
        "namespace": "protocol-recovery.v1",
        "run_id": run["id"],
        "status": run["status"],
        "version": run["version"],
        "fence": run["fence"],
        "recovery": reason,
        "provider_requests": 0,
        "automatic_resend": False,
        "global_send_blocked": global_send_blocked,
        "cached": False,
    }


def mount(app, store, identity):
    user_dependency = Depends(identity)

    @app.post("/api/projects/{pid}/protocol/runs/{rid}/recover")
    def recover_run(pid: str, rid: str, body: RecoveryInput, user=user_dependency):
        with store.tx() as c:
            store.own_project(c, user, pid)
            if c.execute(select(runs.c.project_id).where(runs.c.id == rid)).scalar() != pid:
                raise DomainError("PERMISSION_DENIED")
        return recover(store, user, rid, body)
