"""Locate a persisted V2 completion command; never enter a completion writer."""

import math

from sqlalchemy import select

from .db import attempts, events, fingerprint, runs
from .errors import DomainError
from .protocol_extract_completion import (
    COMPLETED as EXTRACT_COMPLETED,
)
from .protocol_extract_completion import (
    CompletionInput,
    _stored,
    require,
    sidecar,
    verified_receipt,
)
from .protocol_jobs import _plan, verified_pending
from .protocol_source_completion import COMPLETED as SOURCE_COMPLETED
from .protocol_source_completion import _admission, _bounds, _verified

KINDS = {"source": SOURCE_COMPLETED, "extract": EXTRACT_COMPLETED}


def _location(store, c, user, pid, rid):
    store.own_project(c, user, pid)
    location = c.execute(
        select(runs.c.project_id).where(runs.c.id == rid, runs.c.principal_id == user)
    ).scalar()
    if location != pid:
        raise DomainError("PERMISSION_DENIED")
    job, run = verified_pending(store, c, user, rid)
    require(job["phase"] in KINDS and not job["snapshot"].get("bounded_check_namespace"))
    return job, run


def _markers(c, rid, phase):
    # Search both families over the complete actual Attempt set, including
    # misplaced mirrors. An absent Run mirror alone is never NOT_FOUND.
    aids = list(c.execute(select(attempts.c.id).where(attempts.c.run_id == rid)).scalars())
    rows = c.execute(
        select(events.c.run_id, events.c.kind, events.c.data).where(
            events.c.run_id.in_([rid, *aids]), events.c.kind.in_(KINDS.values())
        )
    ).all()
    if not rows:
        return None
    require(len(rows) == 2 and all(r.kind == KINDS[phase] for r in rows))
    roots = [r for r in rows if r.run_id == rid]
    mirrors = [r for r in rows if r.run_id in aids]
    require(len(roots) == len(mirrors) == 1)
    require(fingerprint(roots[0].data) == fingerprint(mirrors[0].data))
    return roots[0].data, mirrors[0].run_id


def _response(old, job, run):
    request = CompletionInput.model_validate(old["request"]).model_dump()
    phase = job["phase"]
    expected = dict(
        namespace=f"protocol-{phase}-completion.v2",
        run_id=run["id"],
        status="WAITING_APPROVAL" if phase == "source" else "SUCCEEDED",
        version=request["expected_version"] + 1,
        fence=request["expected_fence"] + 1,
        **(
            {"result_fingerprint": job["result_fingerprint"]}
            if phase == "source"
            else {"plan_fingerprint": job["result"]["compiled_plan"]["plan_fingerprint"]}
        ),
        provider_requests=0,
        automatic_resend=False,
        cached=False,
    )
    require(
        fingerprint(old["request"]) == fingerprint(request)
        and fingerprint(old["response"]) == fingerprint(expected)
        and not run["cancel_intent"]
        and run["error"] is None
        and run["fence"] == job["completed_fence"] == expected["fence"]
        and job["result"]["completed_run_version"] == expected["version"]
        and type(old["recovery_fence"]) is int
        and old["recovery_fence"] == expected["fence"]
    )
    return request, expected


def _historical(at, start, end, bounds):
    require(
        all(type(v) in (int, float) and math.isfinite(v) for v in [at, start, end, *bounds])
        and start <= end <= at < min(bounds),
        "Original completion timing evidence changed",
    )


def _source(store, c, user, rid, data, old, aid, settings):
    facts, witness = _verified(store, c, user, rid, data)
    job, run, expected_aid, origins, result, _, _ = facts
    require(aid == expected_aid)
    require(
        set(old)
        == {
            "request",
            "response",
            "completed_at",
            "original_send_fence",
            "recovery_fence",
            "admission",
        }
    )
    request, response = _response(old, job, run)
    require(
        type(old["original_send_fence"]) is int
        and old["original_send_fence"] == origins[0]["fence"]
        and fingerprint(old["admission"])
        == fingerprint(
            _admission(c, rid, witness, request["expected_version"], request["expected_fence"])
        )
        and fingerprint(job["result"]["protocol_result"]) == fingerprint(result)
    )
    _historical(
        old["completed_at"],
        run["created_at"],
        witness["ready_at"],
        _bounds(store, c, run, witness, settings, current=False),
    )
    if run["status"] == "SUCCEEDED":
        from .protocol_reviews import review_proof

        review_proof(store, c, user, rid)
        require(run["version"] == response["version"] + 1)
    else:
        require(run["status"] == "WAITING_APPROVAL" and run["version"] == response["version"])
    return request, response


def _extract(store, c, user, rid, data, old, aid):
    rows = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().all()
    require(len(rows) == 1 and rows[0]["id"] == aid)
    receipt = rows[0]["parameters"].get("protocol_candidate_receipt")
    facts, witness = verified_receipt(store, c, user, rid, receipt, data)
    job, run, _, origin, _, _, _, experiment = facts
    require(
        set(old) == {"request", "response", "completed_at", "original_send_fence", "recovery_fence"}
    )
    request, response = _response(old, job, run)
    require(
        run["status"] == "SUCCEEDED"
        and run["version"] == response["version"]
        and type(old["original_send_fence"]) is int
        and old["original_send_fence"] == origin["fence"]
    )
    _plan(store, c, user, rid, response["plan_fingerprint"])
    frozen = store.frozen_contract(c, run)
    bounds = [
        origin["deadline"],
        origin["provider_deadline"],
        run["created_at"] + frozen.limits.run_seconds,
    ]
    if experiment is not None:
        bounds.append(experiment["binding"]["bound_at"] + 300)
    _historical(old["completed_at"], run["created_at"], witness["accepted_at"], bounds)
    return request, response


@_stored
def read_receipt(store, user, pid, rid, settings):
    if not store.test_only or settings.mode != "mock":
        raise DomainError("PERMISSION_DENIED", "Original offline protocol boundary required")
    with store.tx() as c:
        job, _ = _location(store, c, user, pid, rid)
        marks = _markers(c, rid, job["phase"])
        if marks is None:
            return dict(
                namespace="protocol-completion-readback.v1",
                run_id=rid,
                phase=job["phase"],
                state="NOT_FOUND",
                request=None,
                receipt=None,
            )
    # An existing server-selected lock and sidecar only. Authorization and every
    # marker are read again in this transaction; no prior PASS is retained.
    with sidecar(settings.data_dir, rid) as data, store.tx() as c:
        job, run = _location(store, c, user, pid, rid)
        marks = _markers(c, rid, job["phase"])
        require(marks is not None)
        old, aid = marks
        if job["phase"] == "source":
            request, response = _source(store, c, user, rid, data, old, aid, settings)
        else:
            request, response = _extract(store, c, user, rid, data, old, aid)
        final_job, final_run = _location(store, c, user, pid, rid)
        require(fingerprint([job, run]) == fingerprint([final_job, final_run]))
        require(fingerprint(_markers(c, rid, job["phase"])) == fingerprint(marks))
        return dict(
            namespace="protocol-completion-readback.v1",
            run_id=rid,
            phase=job["phase"],
            state="FOUND",
            request=request,
            receipt=response,
        )
