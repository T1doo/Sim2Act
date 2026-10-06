"""Fixed DB-wide offline protocol pool. Controllers initialize; runtimes never seed.

One in-flight request is deliberately conservative. STARTED is not evidence of
absence; it consumes a slot and blocks other sends across runs/process restarts.
"""

import time

from sqlalchemy import insert, select, update

from .db import attempts, events, fingerprint, protocol_jobs
from .db import protocol_request_pools as pools
from .db import protocol_request_slots as slots
from .errors import DomainError


def _protocol_attempts(c, pool_id=None):
    from .protocol_jobs import protocol_run_ids

    ids = protocol_run_ids(c)
    rows = list(c.execute(select(attempts).where(attempts.c.run_id.in_(ids))).mappings())
    if pool_id is None:
        return rows
    return [
        a for a in rows if selected_pool("offline" if a["mode"] == "MOCK" else "live") == pool_id
    ]


def _reserved_seal(slot):
    return {
        k: slot[k]
        for k in [
            "attempt_id",
            "pool_id",
            "ordinal",
            "run_id",
            "fence",
            "phase",
            "request_fingerprint",
            "reserved_tokens",
        ]
    }


def _finished_seal(slot):
    return {
        **_reserved_seal(slot),
        "status": slot["status"],
        "usage": slot["usage"],
        "safe_response_fingerprint": slot["safe_response_fingerprint"],
    }


VERSION = "protocol-request-pool.v1"
OFFLINE_POOL = VERSION + ":offline"
LIVE_POOL = VERSION + ":live"


def selected_pool(mode):
    if mode not in {"offline", "live"}:
        raise DomainError("INVALID_INPUT")
    return OFFLINE_POOL if mode == "offline" else LIVE_POOL


def _policy(mode, limit):
    return {
        "version": VERSION,
        "pool_id": selected_pool(mode),
        "mode": mode,
        "request_limit": limit,
        "token_limit": 64000 if mode == "offline" else 0,
        "single_inflight": True,
        "live_enabled": False,
    }


def initialize_pools(store, offline_limit=0):
    """Explicit migration/controller only; no refill, replacement or historical reset."""
    if (
        type(offline_limit) is not int
        or not 0 <= offline_limit <= 14
        or (offline_limit and not store.test_only)
    ):
        raise DomainError(
            "PERMISSION_DENIED", "Only explicit synthetic offline allowance is supported"
        )
    with store.tx() as c:
        existing = c.execute(select(pools).with_for_update()).mappings().all()
        if existing:
            expected = {
                OFFLINE_POOL: _policy("offline", offline_limit),
                LIVE_POOL: _policy("live", 0),
            }
            if len(existing) != 2 or any(
                r["id"] not in expected or r["policy_fingerprint"] != fingerprint(expected[r["id"]])
                for r in existing
            ):
                raise DomainError("VERSION_CONFLICT", "Existing pool policy cannot be reset")
            for existing_pool in existing:
                _locked(c, existing_pool["id"])
            return
        historical = _protocol_attempts(c)
        if historical or c.execute(select(slots.c.attempt_id)).first():
            raise DomainError(
                "OUTCOME_UNKNOWN",
                "Existing protocol attempts require explicit accounting migration",
            )
        for mode, limit in [("offline", offline_limit), ("live", 0)]:
            policy = _policy(mode, limit)
            c.execute(
                insert(pools).values(
                    id=selected_pool(mode),
                    mode=mode,
                    request_limit=limit,
                    token_limit=policy["token_limit"],
                    reserved_requests=0,
                    reserved_tokens=0,
                    known_tokens=0,
                    halted=False,
                    halt_reason=None,
                    policy_fingerprint=fingerprint(policy),
                    version=1,
                    created_at=time.time(),
                )
            )
            store.event(c, selected_pool(mode), "PROTOCOL_POOL_INITIALIZED", policy)


def _usage_total(usage):
    """Stored normalized usage is untrusted until its complete typed shape is checked."""
    keys = {"prompt_tokens", "completion_tokens", "total_tokens"}
    if not isinstance(usage, dict) or set(usage) != {"status", "tokens"}:
        raise DomainError("OUTCOME_UNKNOWN", "Stored usage has invalid shape")
    status, tokens = usage["status"], usage["tokens"]
    if status == "unknown" and tokens is None:
        return 0
    if (
        not isinstance(status, str)
        or status not in {"known", "partial"}
        or not isinstance(tokens, dict)
        or not tokens
        or not set(tokens) <= keys
        or any(type(value) is not int or value < 0 for value in tokens.values())
    ):
        raise DomainError("OUTCOME_UNKNOWN", "Stored usage has invalid typed tokens")
    if status == "known":
        if (
            set(tokens) != keys
            or tokens["total_tokens"] != tokens["prompt_tokens"] + tokens["completion_tokens"]
        ):
            raise DomainError("OUTCOME_UNKNOWN", "Stored known usage is incomplete or inconsistent")
        return tokens["total_tokens"]
    return 0


def _locked(c, pool_id):
    pool = (
        c.execute(select(pools).where(pools.c.id == pool_id).with_for_update()).mappings().first()
    )
    if not pool:
        raise DomainError(
            "RESOURCE_UNAVAILABLE",
            "Shared protocol pool requires explicit controller initialization",
        )
    if (
        pool["token_limit"] != (64000 if pool["mode"] == "offline" else 0)
        or pool["id"] != selected_pool(pool["mode"])
        or pool["policy_fingerprint"] != fingerprint(_policy(pool["mode"], pool["request_limit"]))
        or type(pool["request_limit"]) is not int
        or not 0 <= pool["request_limit"] <= (14 if pool["mode"] == "offline" else 0)
    ):
        raise DomainError("VERSION_CONFLICT", "Fixed pool policy changed")
    genesis = (
        c.execute(
            select(events.c.data).where(
                events.c.run_id == pool_id, events.c.kind == "PROTOCOL_POOL_INITIALIZED"
            )
        )
        .scalars()
        .all()
    )
    if len(genesis) != 1 or fingerprint(genesis[0]) != pool["policy_fingerprint"]:
        raise DomainError("VERSION_CONFLICT", "Controller pool genesis seal changed")
    if any(
        type(pool[k]) is not int or pool[k] < 0
        for k in ["token_limit", "reserved_requests", "reserved_tokens", "known_tokens", "version"]
    ):
        raise DomainError(
            "OUTCOME_UNKNOWN", "Shared pool counters require exact nonnegative integers"
        )
    rows = (
        c.execute(select(slots).where(slots.c.pool_id == pool_id).order_by(slots.c.ordinal))
        .mappings()
        .all()
    )
    for row in rows:
        if type(row["reserved_tokens"]) is not int or row["reserved_tokens"] < 0:
            raise DomainError("OUTCOME_UNKNOWN", "Stored slot reservation has invalid type")
        _usage_total(row["usage"])
    if (
        pool["reserved_requests"] != len(rows)
        or pool["reserved_tokens"] != sum(r["reserved_tokens"] for r in rows)
        or [r["ordinal"] for r in rows] != list(range(1, len(rows) + 1))
    ):
        raise DomainError("OUTCOME_UNKNOWN", "Shared pool accounting differs from immutable slots")
    known = sum(_usage_total(r["usage"]) for r in rows if r["status"] in {"RECEIVED", "FAILED"})
    if (
        known != pool["known_tokens"]
        or pool["reserved_requests"] > pool["request_limit"]
        or pool["reserved_tokens"] > pool["token_limit"]
    ):
        raise DomainError("OUTCOME_UNKNOWN", "Shared pool totals differ from immutable slots")
    return dict(pool), list(rows)


def require_pool(store, pool_id):
    """Persist unknown stop before raising; capacity exhaustion only gates reserve."""
    error = None
    with store.tx() as c:
        try:
            summary = audit_pool(c, pool_id)
            if (
                (
                    summary["known_tokens"] > summary["token_limit"]
                    or summary["halted"]
                    and summary["halt_reason"] == "BUDGET_EXHAUSTED"
                )
                and not summary["has_pending"]
                and not summary["has_unknown"]
            ):
                error = DomainError(
                    "BUDGET_EXHAUSTED", "Actual shared token usage exhausted budget"
                )
            elif summary["halted"] or summary["has_pending"] or summary["has_unknown"]:
                error = DomainError("OUTCOME_UNKNOWN", "Shared pool has an unresolved request")
                halt_unknown_in_tx(store, c, pool_id, "UNRESOLVED_REQUEST")
        except DomainError as exc:
            error = exc
            if exc.code != "RESOURCE_UNAVAILABLE":
                halt_unknown_in_tx(store, c, pool_id, "ACCOUNTING_INCONSISTENCY")
    if error:
        raise error


def reserve_slot(store, c, run, fence, attempt_id, reserved_tokens, request_fingerprint):
    """Called within Worker.reserve: slot+Attempt+context commit atomically."""
    job = (
        c.execute(select(protocol_jobs).where(protocol_jobs.c.run_id == run["id"]))
        .mappings()
        .first()
    )
    if not job:
        raise DomainError("PERMISSION_DENIED")
    snapshot = job["accepted_snapshot"]
    pool_id = selected_pool(snapshot["scope"]["mode"])
    if (
        snapshot.get("request_pool_id") != pool_id
        or fingerprint(snapshot) != job["fingerprint"]
        or job["fingerprint"] != run["fingerprint"]
    ):
        raise DomainError("VERSION_CONFLICT")
    pool, rows = _locked(c, pool_id)
    summary = audit_pool(c, pool_id)
    if summary["halted"] or summary["has_pending"] or summary["has_unknown"]:
        raise DomainError("OUTCOME_UNKNOWN", "Shared pool audit refuses reservation")
    # Pool wait may consume the lease. No other project/Run lock is acquired here.
    current = store.guard(c, run["id"], fence)
    if current["status"] != "RUNNING":
        raise DomainError("VERSION_CONFLICT")
    for rid in current["resource_refs"]:
        store.authorize(
            c,
            current["principal_id"],
            current["runtime_id"],
            current["project_id"],
            rid,
            "resource.read",
        )
    if pool["mode"] != "offline" or not store.test_only:
        raise DomainError("PERMISSION_DENIED", "LIVE allowance remains zero")
    if pool["halted"] or any(r["status"] in {"STARTED", "UNKNOWN"} for r in rows):
        raise DomainError("OUTCOME_UNKNOWN")
    if (
        pool["known_tokens"] > pool["token_limit"]
        or pool["reserved_requests"] >= pool["request_limit"]
        or pool["reserved_tokens"] + reserved_tokens > pool["token_limit"]
    ):
        raise DomainError("BUDGET_EXHAUSTED", "Shared protocol request/token limit exhausted")
    ordinal = pool["reserved_requests"] + 1
    c.execute(
        insert(slots).values(
            attempt_id=attempt_id,
            pool_id=pool_id,
            ordinal=ordinal,
            run_id=run["id"],
            fence=fence,
            phase=job["kind"],
            request_fingerprint=request_fingerprint,
            reserved_tokens=reserved_tokens,
            status="STARTED",
            usage={"status": "unknown", "tokens": None},
            created_at=time.time(),
        )
    )
    store.event(
        c,
        run["id"],
        "PROTOCOL_REQUEST_RESERVED",
        {
            "attempt_id": attempt_id,
            "pool_id": pool_id,
            "ordinal": ordinal,
            "run_id": run["id"],
            "fence": fence,
            "phase": job["kind"],
            "request_fingerprint": request_fingerprint,
            "reserved_tokens": reserved_tokens,
        },
    )
    c.execute(
        update(pools)
        .where(pools.c.id == pool_id)
        .values(
            reserved_requests=ordinal,
            reserved_tokens=pool["reserved_tokens"] + reserved_tokens,
            version=pool["version"] + 1,
        )
    )


def finish_slot(store, c, run, fence, attempt_id, status, usage, safe_response):
    """Same transaction as Attempt result. Never refunds, overwrites or clears halt."""
    job = (
        c.execute(select(protocol_jobs).where(protocol_jobs.c.run_id == run["id"])).mappings().one()
    )
    pool_id = job["accepted_snapshot"]["request_pool_id"]
    pool, _ = _locked(c, pool_id)
    store.guard(c, run["id"], fence)
    slot = c.execute(select(slots).where(slots.c.attempt_id == attempt_id)).mappings().first()
    if (
        not slot
        or slot["pool_id"] != pool_id
        or slot["run_id"] != run["id"]
        or slot["fence"] != fence
        or slot["status"] != "STARTED"
    ):
        raise DomainError("OUTCOME_UNKNOWN", "Shared slot cannot be settled by this worker")
    actual_total = _usage_total(usage)
    unknown = usage["status"] != "known" or status not in {"RECEIVED", "FAILED"}
    total = 0 if unknown else actual_total
    if not unknown and (type(total) is not int or total < 0):
        raise DomainError("OUTCOME_UNKNOWN", "Known usage has invalid shape")
    over_limit = not unknown and (
        total > slot["reserved_tokens"] or pool["known_tokens"] + total > pool["token_limit"]
    )
    c.execute(
        update(slots)
        .where(slots.c.attempt_id == attempt_id)
        .values(
            status="UNKNOWN" if unknown else status,
            usage=usage,
            safe_response_fingerprint=fingerprint(safe_response),
            finished_at=time.time(),
            error="OUTCOME_UNKNOWN" if unknown else None,
        )
    )
    store.event(
        c,
        run["id"],
        "PROTOCOL_REQUEST_SETTLED",
        {
            **_reserved_seal(slot),
            "status": "UNKNOWN" if unknown else status,
            "usage": usage,
            "safe_response_fingerprint": fingerprint(safe_response),
        },
    )
    if unknown or over_limit:
        store.event(
            c,
            pool_id,
            "PROTOCOL_POOL_HALTED",
            {
                "reason": "OUTCOME_UNKNOWN" if unknown else "BUDGET_EXHAUSTED",
                "attempt_id": attempt_id,
                "pool_version": pool["version"] + 1,
            },
        )
    c.execute(
        update(pools)
        .where(pools.c.id == pool_id)
        .values(
            known_tokens=pool["known_tokens"] + total,
            halted=pool["halted"] or unknown or over_limit,
            halt_reason="OUTCOME_UNKNOWN"
            if unknown
            else "BUDGET_EXHAUSTED"
            if over_limit
            else pool["halt_reason"],
            version=pool["version"] + 1,
        )
    )


def halt_unknown(store, pool_id, reason, attempt_id=None):
    with store.tx() as c:
        halt_unknown_in_tx(store, c, pool_id, reason, attempt_id)


def inspect_pool(store, pool_id):
    """Read-only safe summary. Controllers needing slots query the protected ledger."""
    with store.tx() as c:
        return audit_pool(c, pool_id)


def audit_pool(c, pool_id):
    """Safe bidirectional accounting summary; no foreign Run/Attempt IDs."""
    pool, rows = _locked(c, pool_id)
    actual = _protocol_attempts(c, pool_id)
    inconsistent = {a["id"] for a in actual} != {r["attempt_id"] for r in rows}
    original = list(
        c.execute(
            select(events.c.data).where(events.c.kind == "PROTOCOL_REQUEST_RESERVED")
        ).scalars()
    )
    original = [e for e in original if isinstance(e, dict) and e.get("pool_id") == pool_id]
    if len(original) != len(rows) or {e.get("attempt_id") for e in original} != {
        r["attempt_id"] for r in rows
    }:
        inconsistent = True
    for slot in rows:
        attempt = next((a for a in actual if a["id"] == slot["attempt_id"]), None)
        seals = [e for e in original if e.get("attempt_id") == slot["attempt_id"]]
        if len(seals) != 1 or fingerprint(seals[0]) != fingerprint(_reserved_seal(slot)):
            inconsistent = True
        if (
            not attempt
            or attempt["run_id"] != slot["run_id"]
            or attempt["reserved_tokens"] != slot["reserved_tokens"]
            or attempt["parameters"].get("request_fingerprint") != slot["request_fingerprint"]
        ):
            inconsistent = True
            continue
        if slot["status"] == "STARTED":
            if attempt["status"] != "STARTED":
                inconsistent = True
        else:
            settled = list(
                c.execute(
                    select(events.c.data).where(
                        events.c.run_id == slot["run_id"],
                        events.c.kind == "PROTOCOL_REQUEST_SETTLED",
                    )
                ).scalars()
            )
            settled = [
                e
                for e in settled
                if isinstance(e, dict) and e.get("attempt_id") == slot["attempt_id"]
            ]
            if (
                len(settled) != 1
                or fingerprint(settled[0]) != fingerprint(_finished_seal(slot))
                or slot["status"] != "UNKNOWN"
                and attempt["status"] != slot["status"]
                or fingerprint(slot["usage"]) != fingerprint(attempt["usage"])
                or slot["safe_response_fingerprint"] != fingerprint(attempt["response"])
            ):
                inconsistent = True
    halt_facts = list(
        c.execute(
            select(events.c.data).where(
                events.c.run_id == pool_id, events.c.kind == "PROTOCOL_POOL_HALTED"
            )
        ).scalars()
    )
    if halt_facts:
        reasons = {fact.get("reason") for fact in halt_facts if isinstance(fact, dict)}
        pool["halted"] = True
        pool["halt_reason"] = (
            "BUDGET_EXHAUSTED" if reasons == {"BUDGET_EXHAUSTED"} else "OUTCOME_UNKNOWN"
        )
    return {
        **pool,
        "slots_count": len(rows),
        "has_pending": any(r["status"] == "STARTED" for r in rows),
        "has_unknown": inconsistent or any(r["status"] == "UNKNOWN" for r in rows),
        "consistent": not inconsistent,
    }


def halt_unknown_in_tx(store, c, pool_id, reason, attempt_id=None):
    """Trusted recovery can persist unknown halt using its existing transaction."""
    pool = (
        c.execute(select(pools).where(pools.c.id == pool_id).with_for_update()).mappings().first()
    )
    if not pool:
        raise DomainError("RESOURCE_UNAVAILABLE")
    c.execute(
        update(pools)
        .where(pools.c.id == pool_id)
        .values(halted=True, halt_reason=reason, version=pool["version"] + 1)
    )

    store.event(
        c,
        pool_id,
        "PROTOCOL_POOL_HALTED",
        {"reason": reason, "attempt_id": attempt_id, "pool_version": pool["version"] + 1},
    )
