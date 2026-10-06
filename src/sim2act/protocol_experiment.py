"""Controller-only persistent OFFLINE experiment identity, sequence and send clock.

No tables, migration, grants, transport selection or LIVE activation. Hooks run in
existing project -> Run -> quota -> pool transactions; they never lock another Run.
The fixed DB pool remains authoritative; these sealed events add experiment bounds.
"""

import copy
import math
import time

from sqlalchemy import select

from .db import attempts, events, fingerprint, new_id, protocol_jobs, protocol_reviews, runs
from .db import protocol_request_pools as pools
from .db import protocol_request_slots as slots
from .errors import DomainError
from .protocol_jobs import verified_pending
from .protocol_pool import OFFLINE_POOL, audit_pool, halt_unknown_in_tx
from .protocol_reviews import review_proof

VERSION = "protocol-experiment.v1"
ORDER = ["source_a", "extract_a", "cold_a", "source_b", "extract_b", "cold_b"]
CAPS = {s: 1 if s.startswith("extract") else 3 for s in ORDER}
TOKENS = {s: 8000 if s.startswith("extract") else 24000 for s in ORDER}
GENESIS = "PROTOCOL_EXPERIMENT_INITIALIZED"
BOUND = "PROTOCOL_EXPERIMENT_RUN_BOUND"
BINDING = "PROTOCOL_EXPERIMENT_BINDING"
SEND = "PROTOCOL_EXPERIMENT_SEND"
SETTLED = "PROTOCOL_EXPERIMENT_SETTLED"
ADVANCED = "PROTOCOL_EXPERIMENT_ADVANCED"
STOPPED = "PROTOCOL_EXPERIMENT_STOPPED"


def _now(store, clock):
    if clock is not None and not store.test_only:
        raise DomainError("PERMISSION_DENIED")
    value = time.time() if clock is None else clock()
    if type(value) not in {int, float} or not math.isfinite(value) or value < 0:
        raise DomainError("INVALID_INPUT", "Exact finite server clock required")
    return value


def _records(c, eid, kind):
    rows = (
        c.execute(select(events.c.data).where(events.c.run_id == eid, events.c.kind == kind))
        .scalars()
        .all()
    )
    for row in rows:
        if (
            not isinstance(row, dict)
            or set(row) != {"value", "fingerprint"}
            or not isinstance(row["value"], dict)
            or fingerprint(row["value"]) != row["fingerprint"]
        ):
            raise DomainError("VERSION_CONFLICT", "Experiment event seal changed")
    return [r["value"] for r in rows]


def _event(store, c, eid, kind, value):
    store.event(c, eid, kind, {"value": value, "fingerprint": fingerprint(value)})


def _pool(c):
    row = (
        c.execute(select(pools).where(pools.c.id == OFFLINE_POOL).with_for_update())
        .mappings()
        .first()
    )
    if not row:
        raise DomainError(
            "RESOURCE_UNAVAILABLE", "Explicit shared pool controller initialization required"
        )
    return row


def _read_state(c, eid, pending_attempt_id=None):
    origin = _records(c, eid, GENESIS)
    mirror = [v for v in _records(c, OFFLINE_POOL, GENESIS) if v.get("experiment_id") == eid]
    if len(origin) != 1 or mirror != origin:
        raise DomainError("VERSION_CONFLICT", "Experiment controller identity missing or changed")
    policy = origin[0]
    expected = {
        "namespace": VERSION,
        "experiment_id": eid,
        "principal_id": policy.get("principal_id"),
        "project_id": policy.get("project_id"),
        "request_key": policy.get("request_key"),
        "pool_id": OFFLINE_POOL,
        "pool_policy_fingerprint": policy.get("pool_policy_fingerprint"),
        "request_limit": policy.get("request_limit"),
        "order": ORDER,
        "stage_caps": CAPS,
        "stage_token_caps": TOKENS,
        "spacing_seconds": 6,
        "stage_seconds": 300,
        "mode": "offline",
        "live_enabled": False,
    }
    if (
        fingerprint(policy) != fingerprint(expected)
        or type(policy["request_limit"]) is not int
        or not 0 <= policy["request_limit"] <= 14
    ):
        raise DomainError("VERSION_CONFLICT")
    pool = c.execute(select(pools).where(pools.c.id == OFFLINE_POOL)).mappings().one()
    if policy["pool_policy_fingerprint"] != pool["policy_fingerprint"]:
        raise DomainError("VERSION_CONFLICT")
    bound = sorted(_records(c, eid, BOUND), key=lambda value: value["ordinal"])
    advanced = sorted(_records(c, eid, ADVANCED), key=lambda value: ORDER.index(value["stage"]))
    if len(bound) > 6 or len(advanced) > len(bound):
        raise DomainError("VERSION_CONFLICT")
    for i, binding in enumerate(bound):
        if (
            type(binding["ordinal"]) is not int
            or type(binding["bound_at"]) not in {int, float}
            or not math.isfinite(binding["bound_at"])
            or binding["bound_at"] < 0
        ):
            raise DomainError("VERSION_CONFLICT", "Invalid bound stage clock")
        if binding["stage"] != ORDER[i] or binding["ordinal"] != i:
            raise DomainError("VERSION_CONFLICT")
        mirrors = _records(c, binding["run_id"], BINDING)
        if mirrors != [{**binding, "experiment_id": eid}]:
            raise DomainError("VERSION_CONFLICT", "Run experiment binding changed")
    actual_bindings = list(
        c.execute(
            select(events.c.data).where(
                events.c.kind == BINDING,
                events.c.data["value"]["experiment_id"].as_string() == eid,
            )
        ).scalars()
    )
    expected_bindings = [
        {
            "value": {**v, "experiment_id": eid},
            "fingerprint": fingerprint({**v, "experiment_id": eid}),
        }
        for v in bound
    ]
    if sorted(fingerprint(v) for v in actual_bindings) != sorted(
        fingerprint(v) for v in expected_bindings
    ):
        raise DomainError("VERSION_CONFLICT", "Actual Run bindings lack experiment forward seals")
    if len({v["run_id"] for v in bound}) != len(bound):
        raise DomainError("VERSION_CONFLICT")
    for i, record in enumerate(advanced):
        if record["run_id"] != bound[i]["run_id"] or record["stage"] != ORDER[i]:
            raise DomainError("VERSION_CONFLICT")
    sends = sorted(_records(c, eid, SEND), key=lambda v: v["ordinal"])
    if [v["ordinal"] for v in sends] != list(range(1, len(sends) + 1)) or len(sends) > policy[
        "request_limit"
    ]:
        raise DomainError("OUTCOME_UNKNOWN", "Experiment request accounting changed")
    actual_slot_ids = set(
        c.execute(
            select(slots.c.attempt_id).where(slots.c.run_id.in_([v["run_id"] for v in bound]))
        ).scalars()
    )
    if actual_slot_ids - ({pending_attempt_id} if pending_attempt_id is not None else set()) != {
        v["attempt_id"] for v in sends
    }:
        raise DomainError("OUTCOME_UNKNOWN", "Actual experiment slots lack sealed send accounting")
    settled = _records(c, eid, SETTLED)
    if len({v["attempt_id"] for v in settled}) != len(settled):
        raise DomainError("OUTCOME_UNKNOWN")
    for i, send in enumerate(sends):
        if (
            type(send["ordinal"]) is not int
            or type(send["at"]) not in {int, float}
            or not math.isfinite(send["at"])
            or send["at"] < 0
        ):
            raise DomainError("VERSION_CONFLICT", "Invalid sealed send clock")
        if _records(c, send["attempt_id"], SEND) != [{**send, "experiment_id": eid}]:
            raise DomainError("VERSION_CONFLICT", "Independent experiment send seal changed")
        binding = next((v for v in bound if v["run_id"] == send["run_id"]), None)
        if (
            not binding
            or send["stage"] != binding["stage"]
            or i
            and send["at"] - sends[i - 1]["at"] < 6
        ):
            raise DomainError("OUTCOME_UNKNOWN", "Experiment global send order changed")
        slot = (
            c.execute(select(slots).where(slots.c.attempt_id == send["attempt_id"]))
            .mappings()
            .first()
        )
        if (
            not slot
            or slot["run_id"] != send["run_id"]
            or slot["fence"] != send["fence"]
            or slot["reserved_tokens"] != send["reserved_tokens"]
        ):
            raise DomainError("OUTCOME_UNKNOWN", "Experiment send differs from actual slot")
    for record in settled:
        if (
            type(record["at"]) not in {int, float}
            or not math.isfinite(record["at"])
            or record["at"] < 0
        ):
            raise DomainError("VERSION_CONFLICT", "Invalid sealed settlement clock")
        if _records(c, record["attempt_id"], SETTLED) != [{**record, "experiment_id": eid}]:
            raise DomainError("VERSION_CONFLICT", "Independent experiment settlement seal changed")
        if record["attempt_id"] not in {v["attempt_id"] for v in sends}:
            raise DomainError("OUTCOME_UNKNOWN")
        slot = (
            c.execute(select(slots).where(slots.c.attempt_id == record["attempt_id"]))
            .mappings()
            .one()
        )
        if (
            fingerprint(
                {
                    "status": slot["status"],
                    "usage": slot["usage"],
                    "safe_response_fingerprint": slot["safe_response_fingerprint"],
                }
            )
            != record["slot_result_fingerprint"]
        ):
            raise DomainError("OUTCOME_UNKNOWN", "Settled experiment slot changed")
    for stage in ORDER:
        own = [v for v in sends if v["stage"] == stage]
        if len(own) > CAPS[stage] or sum(v["reserved_tokens"] for v in own) > TOKENS[stage]:
            raise DomainError("OUTCOME_UNKNOWN")
    return policy, bound, advanced, sends, settled, _records(c, eid, STOPPED)


def _state(c, eid, pending_attempt_id=None):
    try:
        return _read_state(c, eid, pending_attempt_id)
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise DomainError("VERSION_CONFLICT", "Stored experiment shape is invalid") from exc


def is_experiment_run(c, rid):
    """Any persistent experiment trace seals the fixed pool against legacy fallback.

    The experiment owns one server-selected global pool; origin, forward bindings,
    sends and settlements independently preserve that fact after marker stripping.
    """
    return bool(
        c.execute(
            select(events.c.id).where(
                events.c.kind.in_([GENESIS, BOUND, BINDING, SEND, SETTLED, ADVANCED, STOPPED])
            )
        ).first()
    )


def initialize_experiment(store, user, pid, key, request_limit=0, clock=None):
    """Explicit synthetic controller. No refill, historical adoption or LIVE allowance."""
    _now(store, clock)
    if (
        not store.test_only
        or type(request_limit) is not int
        or not 0 <= request_limit <= 14
        or not isinstance(key, str)
        or not 1 <= len(key) <= 100
    ):
        raise DomainError("PERMISSION_DENIED")
    with store.tx() as c:
        store.lock_project(c, user, pid)
        pool = _pool(c)
        origins = _records(c, OFFLINE_POOL, GENESIS)
        if origins:
            old = origins[0]
            if len(origins) != 1 or (
                old["principal_id"],
                old["project_id"],
                old["request_key"],
                old["request_limit"],
            ) != (user, pid, key, request_limit):
                raise DomainError(
                    "VERSION_CONFLICT", "Fixed pool already belongs to another experiment"
                )
            _state(c, old["experiment_id"])
            return copy.deepcopy(old)
        if is_experiment_run(c, ""):
            raise DomainError(
                "OUTCOME_UNKNOWN", "Orphaned experiment traces cannot create a fresh identity"
            )
        summary = audit_pool(c, OFFLINE_POOL)
        if summary["slots_count"] or summary["halted"] or request_limit > pool["request_limit"]:
            raise DomainError("OUTCOME_UNKNOWN", "Cannot adopt historical sends or refill pool")
        eid = new_id("experiment")
        policy = {
            "namespace": VERSION,
            "experiment_id": eid,
            "principal_id": user,
            "project_id": pid,
            "request_key": key,
            "pool_id": OFFLINE_POOL,
            "pool_policy_fingerprint": pool["policy_fingerprint"],
            "request_limit": request_limit,
            "order": ORDER,
            "stage_caps": CAPS,
            "stage_token_caps": TOKENS,
            "spacing_seconds": 6,
            "stage_seconds": 300,
            "mode": "offline",
            "live_enabled": False,
        }
        _event(store, c, eid, GENESIS, policy)
        _event(store, c, OFFLINE_POOL, GENESIS, policy)
        return copy.deepcopy(policy)


def _owned(store, c, user, eid):
    records = _records(c, eid, GENESIS)
    if len(records) != 1 or records[0].get("principal_id") != user:
        raise DomainError("PERMISSION_DENIED")
    store.lock_project(c, user, records[0]["project_id"])
    return records[0]


def bind_run(store, user, eid, rid, clock=None):
    now = _now(store, clock)
    with store.tx() as c:
        _owned(store, c, user, eid)
        job, run = verified_pending(store, c, user, rid)  # dependency locks BEFORE pool
        _pool(c)
        policy, bound, advanced, sends, _, stopped = _state(c, eid)
        if stopped:
            raise DomainError("PERMISSION_DENIED", "Experiment permanently stopped")
        existing = next((v for v in bound if v["run_id"] == rid), None)
        if existing:
            return copy.deepcopy(existing)
        if (
            len(bound) != len(advanced)
            or len(bound) == 6
            or run["project_id"] != policy["project_id"]
        ):
            raise DomainError("VERSION_CONFLICT", "Previous stage acceptance required")
        snapshot = job["snapshot"]
        stage = ORDER[len(bound)]
        family = stage[-1]
        if (
            job["phase"] != stage[:-2]
            or snapshot["contract"]["contract_id"]
            != f"protocol.synthetic.{family}-{'source' if job['phase'] == 'extract' else job['phase']}.v1"
        ):
            raise DomainError("VERSION_CONFLICT", "Frozen stage family differs")
        if (
            run["status"] != "QUEUED"
            or run["context"].get("requests") != 0
            or c.execute(select(attempts.c.id).where(attempts.c.run_id == rid)).first()
        ):
            raise DomainError("OUTCOME_UNKNOWN", "Only fresh unsent Run can bind")
        if job["phase"] != "source":
            ref = snapshot["payload"][
                "source_run_id" if job["phase"] == "extract" else "extraction_run_id"
            ]
            if ref != bound[-1]["run_id"]:
                raise DomainError("VERSION_CONFLICT", "Parent Run is outside this experiment")
        value = {
            "run_id": rid,
            "stage": stage,
            "ordinal": len(bound),
            "accepted_fingerprint": job["fingerprint"],
            "bound_at": now,
            "prepared_fence": run["fence"],
            "prepared_version": run["version"],
        }
        _event(store, c, eid, BOUND, value)
        _event(store, c, rid, BINDING, {**value, "experiment_id": eid})
        return copy.deepcopy(value)


def _binding(c, run):
    records = _records(c, run["id"], BINDING)
    if len(records) != 1:
        raise DomainError("RESOURCE_UNAVAILABLE", "Explicit experiment Run binding required")
    return records[0]


def verify_in_tx(store, c, run, fence, clock=None, pending_attempt_id=None):
    """Caller owns project/Run then fixed pool lock; no other Run acquired here."""
    now = _now(store, clock)
    _pool(c)
    binding = _binding(c, run)
    policy, bound, advanced, sends, settled, stopped = _state(
        c, binding["experiment_id"], pending_attempt_id
    )
    current = store.guard(
        c, run["id"], fence
    )  # existing current Run lock, lease refresh after pool wait
    if (
        not store.test_only
        or policy["principal_id"] != current["principal_id"]
        or policy["project_id"] != current["project_id"]
        or current["status"] != "RUNNING"
    ):
        raise DomainError("PERMISSION_DENIED")
    if stopped or len(advanced) >= len(bound) or bound[len(advanced)]["run_id"] != run["id"]:
        raise DomainError("PERMISSION_DENIED", "Experiment stage is stopped or no longer current")
    job = (
        c.execute(select(protocol_jobs).where(protocol_jobs.c.run_id == run["id"])).mappings().one()
    )
    if (
        job["fingerprint"] != binding["accepted_fingerprint"]
        or fingerprint(job["accepted_snapshot"]) != binding["accepted_fingerprint"]
    ):
        raise DomainError("VERSION_CONFLICT")
    if len(sends) >= policy["request_limit"]:
        raise DomainError("BUDGET_EXHAUSTED")
    if settled and now < max(v["at"] for v in settled) + 6:
        raise DomainError(
            "RATE_LIMITED", "Experiment-wide six-second spacing required", retryable=True
        )
    if now < binding["bound_at"] or now - binding["bound_at"] > 300:
        raise DomainError("BUDGET_EXHAUSTED", "Experiment stage deadline expired")
    own = [v for v in sends if v["stage"] == binding["stage"]]
    if len(own) >= CAPS[binding["stage"]]:
        raise DomainError("BUDGET_EXHAUSTED")
    if any(v["attempt_id"] not in {s["attempt_id"] for s in settled} for v in sends):
        raise DomainError("OUTCOME_UNKNOWN", "Unsettled experiment request forbids another send")
    return binding, sends


def reserve_in_tx(store, c, run, fence, attempt_id, clock=None):
    binding, sends = verify_in_tx(store, c, run, fence, clock, pending_attempt_id=attempt_id)
    eid = binding["experiment_id"]
    existing = next((v for v in sends if v["attempt_id"] == attempt_id), None)
    if existing:
        return existing
    slot = c.execute(select(slots).where(slots.c.attempt_id == attempt_id)).mappings().one()
    if slot["run_id"] != run["id"] or slot["fence"] != fence or slot["status"] != "STARTED":
        raise DomainError("OUTCOME_UNKNOWN")
    own = [v for v in sends if v["stage"] == binding["stage"]]
    if sum(v["reserved_tokens"] for v in own) + slot["reserved_tokens"] > TOKENS[binding["stage"]]:
        raise DomainError("BUDGET_EXHAUSTED")
    value = {
        "attempt_id": attempt_id,
        "run_id": run["id"],
        "fence": fence,
        "stage": binding["stage"],
        "ordinal": len(sends) + 1,
        "reserved_tokens": slot["reserved_tokens"],
        "at": _now(store, clock),
    }
    _event(store, c, eid, SEND, value)
    _event(store, c, attempt_id, SEND, {**value, "experiment_id": eid})
    return value


def validate_dispatch_in_tx(store, c, run, fence, clock=None):
    """Actual frozen wire guard: allow only this exact STARTED origin, before transport."""
    now = _now(store, clock)
    _pool(c)
    current = store.guard(c, run["id"], fence)
    binding = _binding(c, current)
    policy, bound, advanced, sends, settled, stopped = _state(c, binding["experiment_id"])
    summary = audit_pool(c, OFFLINE_POOL)
    pending = list(
        c.execute(
            select(slots).where(slots.c.pool_id == OFFLINE_POOL, slots.c.status == "STARTED")
        ).mappings()
    )
    if (
        not store.test_only
        or policy["principal_id"] != current["principal_id"]
        or policy["project_id"] != current["project_id"]
        or current["status"] != "RUNNING"
        or stopped
        or summary["halted"]
        or summary["has_unknown"]
        or not summary["consistent"]
        or len(pending) != 1
        or pending[0]["run_id"] != current["id"]
        or pending[0]["fence"] != fence
        or len(advanced) >= len(bound)
        or bound[len(advanced)]["run_id"] != current["id"]
    ):
        raise DomainError("OUTCOME_UNKNOWN", "Actual dispatch origin is no longer authorized")
    send = next((v for v in sends if v["attempt_id"] == pending[0]["attempt_id"]), None)
    if not send or now < send["at"] or now < binding["bound_at"] or now - binding["bound_at"] > 300:
        raise DomainError("BUDGET_EXHAUSTED", "Actual dispatch missed the stage clock")
    if settled and now < max(v["at"] for v in settled) + 6:
        raise DomainError(
            "RATE_LIMITED", "Actual dispatch requires six seconds after prior settlement"
        )
    return pending[0]["attempt_id"]


def _stop(store, c, eid, reason):
    if not _records(c, eid, STOPPED):
        _event(store, c, eid, STOPPED, {"reason": reason})


def settle_in_tx(store, c, run, fence, attempt_id, clock=None):
    now = _now(store, clock)
    _pool(c)
    store.guard(c, run["id"], fence)
    binding = _binding(c, run)
    eid = binding["experiment_id"]
    _, _, _, sends, settled, _ = _state(c, eid)
    send = next((v for v in sends if v["attempt_id"] == attempt_id), None)
    if not send:
        raise DomainError("OUTCOME_UNKNOWN")
    slot = c.execute(select(slots).where(slots.c.attempt_id == attempt_id)).mappings().one()
    result = {
        "status": slot["status"],
        "usage": slot["usage"],
        "safe_response_fingerprint": slot["safe_response_fingerprint"],
    }
    value = {"attempt_id": attempt_id, "at": now, "slot_result_fingerprint": fingerprint(result)}
    old = [v for v in settled if v["attempt_id"] == attempt_id]
    if old:
        if old != [value]:
            raise DomainError("VERSION_CONFLICT")
        return value
    _event(store, c, eid, SETTLED, value)
    _event(store, c, attempt_id, SETTLED, {**value, "experiment_id": eid})
    if slot["status"] in {"STARTED", "UNKNOWN"} or slot["usage"]["status"] != "known":
        _stop(store, c, eid, "OUTCOME_UNKNOWN")
        halt_unknown_in_tx(store, c, OFFLINE_POOL, "EXPERIMENT_UNKNOWN", attempt_id)
    elif now - binding["bound_at"] > 300 or slot["status"] == "FAILED":
        _stop(store, c, eid, "STAGE_FAILED")
    else:
        total = sum(
            c.execute(
                select(slots.c.usage).where(slots.c.attempt_id == v["attempt_id"])
            ).scalar_one()["tokens"]["total_tokens"]
            for v in sends
            if v["stage"] == binding["stage"]
        )
        if total > TOKENS[binding["stage"]]:
            _stop(store, c, eid, "BUDGET_EXHAUSTED")
    return value


def preflight(store, user, rid, clock=None):
    error = None
    with store.tx() as c:
        metadata = (
            c.execute(select(protocol_jobs).where(protocol_jobs.c.run_id == rid)).mappings().first()
        )
        if not metadata or metadata["principal_id"] != user:
            raise DomainError("PERMISSION_DENIED")
        store.lock_project(c, user, metadata["project_id"])
        fence = c.execute(select(runs.c.fence).where(runs.c.id == rid)).scalar_one()
        run = store.guard(c, rid, fence)
        try:
            summary = audit_pool(c, OFFLINE_POOL)
            if summary["halted"] or summary["has_pending"] or summary["has_unknown"]:
                raise DomainError(
                    "BUDGET_EXHAUSTED"
                    if summary["halt_reason"] == "BUDGET_EXHAUSTED"
                    else "OUTCOME_UNKNOWN"
                )
            return verify_in_tx(store, c, run, run["fence"], clock)[0]
        except DomainError as exc:
            error = exc
            binding = _binding(c, run)
            if exc.code != "RATE_LIMITED":
                _stop(store, c, binding["experiment_id"], exc.code)
            if exc.code in {"OUTCOME_UNKNOWN", "VERSION_CONFLICT"}:
                halt_unknown_in_tx(store, c, OFFLINE_POOL, "EXPERIMENT_UNKNOWN")
    raise error


def advance(store, user, eid, rid, clock=None):
    _now(store, clock)
    error = None
    with store.tx() as c:
        _owned(store, c, user, eid)
        job, run = verified_pending(store, c, user, rid)
        proof = None
        if job["phase"] in {"source", "cold"} and run["status"] == "SUCCEEDED":
            proof = review_proof(store, c, user, rid)
        _pool(c)
        _, bound, advanced, _, _, stopped = _state(c, eid)
        if stopped:
            raise DomainError("PERMISSION_DENIED")
        if len(advanced) < len(bound) and bound[len(advanced)]["run_id"] == rid:
            decisions = list(
                c.execute(
                    select(protocol_reviews.c.payload).where(protocol_reviews.c.run_id == rid)
                ).scalars()
            )
            if run["status"] in {"FAILED", "CANCELLED", "RECONCILING", "WAITING_RESOURCE"} or any(
                v.get("decision") == "FAIL" for v in decisions
            ):
                _stop(store, c, eid, "STAGE_FAILED")
                error = DomainError("VERIFICATION_FAILED", "Experiment stopped after stage failure")
            elif run["status"] != "SUCCEEDED" or job["phase"] != "extract" and proof is None:
                raise DomainError(
                    "VERIFICATION_FAILED", "Independent acceptance required before advance"
                )
            else:
                value = {
                    "run_id": rid,
                    "stage": bound[len(advanced)]["stage"],
                    "result_fingerprint": job["result_fingerprint"],
                    "proof_fingerprint": fingerprint(proof),
                }
                _event(store, c, eid, ADVANCED, value)
        elif not any(v["run_id"] == rid for v in advanced):
            raise DomainError("VERSION_CONFLICT")
    if error:
        raise error
    return inspect_experiment(store, user, eid)


def inspect_experiment(store, user, eid):
    with store.tx() as c:
        _owned(store, c, user, eid)
        _pool(c)
        policy, bound, advanced, sends, settled, stopped = _state(c, eid)
        return {
            "experiment_id": eid,
            "request_limit": policy["request_limit"],
            "bound_stages": len(bound),
            "accepted_stages": len(advanced),
            "requests": len(sends),
            "settled": len(settled),
            "status": "STOPPED" if stopped else "COMPLETED" if len(advanced) == 6 else "ACTIVE",
            "stop_reason": stopped[0]["reason"] if stopped else None,
            "live_enabled": False,
        }
