"""Offline protocol jobs; durable Runs and verified read operations, no AppManifest claim.

Source/cold technical completion waits for separate persisted semantic review. No
provider is selected by this module; the worker must explicitly inject a runner.
"""

import copy
import threading
import time
from dataclasses import replace

from pydantic import Field, ValidationError
from sqlalchemy import insert, select, update

from .contracts import FrozenRunContract, GoalSpec, Limits, ResourceSnapshot, Strict, strict_json
from .db import (
    attempts,
    events,
    fingerprint,
    new_id,
    operation_intents,
    operations,
    resources,
    run_contracts,
    runs,
)
from .errors import DomainError
from .model_protocol import ModelProtocol, Scope, _no_gold, validate_candidate
from .tools import authorized_read, dispatch

NAMESPACE = "protocol_jobs.v1"
COMPILER_VERSION = "model-protocol-compiler.v1"


class SourceInput(Strict):
    contract_id: str = Field(min_length=1, max_length=100)
    goal: str = Field(min_length=1, max_length=2000)
    inputs: dict
    resource_ids: list[str] = Field(min_length=1, max_length=8)


class ExtractInput(Strict):
    source_run_id: str = Field(pattern=r"^run_[a-f0-9]{32}$")
    expected_source_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


class ColdInput(Strict):
    contract_id: str = Field(min_length=1, max_length=100)
    extraction_run_id: str = Field(pattern=r"^run_[a-f0-9]{32}$")
    expected_plan_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    inputs: dict
    resource_bindings: dict[str, str] = Field(min_length=1, max_length=8)


def _table():
    from .db import protocol_jobs

    return protocol_jobs


def _closed(phase, payload):
    classes: dict[str, type[Strict]] = {
        "source": SourceInput,
        "extract": ExtractInput,
        "cold": ColdInput,
    }
    cls = classes.get(phase)
    if cls is None:
        raise DomainError("INVALID_INPUT", "Unknown protocol phase")
    try:
        import json

        value = strict_json(json.dumps(payload, allow_nan=False), 16000)
        _no_gold(value)
        return cls.model_validate(value).model_dump()
    except (ValueError, TypeError, ValidationError) as exc:
        raise DomainError("INVALID_INPUT", "Closed protocol job request required") from exc


def _source(store, c, user, rid, expected=None):
    from .protocol_reviews import source_proof

    job, run = verified_pending(store, c, user, rid)
    if job["phase"] != "source" or run["status"] != "SUCCEEDED":
        raise DomainError(
            "VERIFICATION_FAILED", "A reviewed successful protocol source is required"
        )
    proof = source_proof(store, c, user, rid)
    result = job["result"]
    if expected is not None and fingerprint(result) != expected:
        raise DomainError("VERSION_CONFLICT", "Reviewed source changed")
    return {
        "run_id": rid,
        "result_fingerprint": fingerprint(result),
        "proof": proof,
        "proof_fingerprint": fingerprint(proof),
    }


def _plan(store, c, user, rid, expected):
    job, run = verified_pending(store, c, user, rid)
    result = (job["result"] or {}).get("compiled_plan")
    if job["phase"] != "extract" or run["status"] != "SUCCEEDED" or not isinstance(result, dict):
        raise DomainError("VERIFICATION_FAILED", "Completed protocol extraction required")
    if result.get("compiler_version") != COMPILER_VERSION:
        raise DomainError("VERSION_CONFLICT", "Unsupported compiled plan version")
    body = {k: v for k, v in result.items() if k != "plan_fingerprint"}
    if (
        result.get("plan_fingerprint") != fingerprint(body)
        or result["plan_fingerprint"] != expected
    ):
        raise DomainError("VERSION_CONFLICT", "Compiled plan changed")
    return copy.deepcopy(result)


def _authority(store, c, run, snapshot):
    contract = store.frozen_contract(c, run)
    if contract.limits.model_dump() != snapshot["limits"]:
        raise DomainError("VERSION_CONFLICT")
    scope = Scope.model_validate(snapshot["scope"])
    from .protocol_pool import selected_pool

    if snapshot.get("request_pool_id") != selected_pool(scope.mode):
        raise DomainError("VERSION_CONFLICT", "Fixed shared request pool changed")
    if (
        scope.mode != "offline"
        or scope.project_id != run["project_id"]
        or scope.resource_ids != run["resource_refs"]
    ):
        raise DomainError("PERMISSION_DENIED", "Only offline protocol jobs are enabled")
    for rid in scope.resource_ids:
        for tool in scope.tool_refs:
            store.authorize(c, run["principal_id"], run["runtime_id"], run["project_id"], rid, tool)
    store.authorize_receipts(c, run)


def verified_pending(store, c, user, rid, *, stop_only=False):
    """Read/authenticate a protocol job, including completed jobs used by reviews.

    The accepted Run fingerprint is an independent anchor for the job snapshot.
    Callers enforce their own expected state/version/fence while holding the lock.
    """
    table = _table()
    location = c.execute(
        select(runs.c.project_id).where(runs.c.id == rid, runs.c.principal_id == user)
    ).scalar()
    store.lock_project(c, user, location)
    run = c.execute(select(runs).where(runs.c.id == rid).with_for_update()).mappings().first()
    if not run or run["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    store.own_project(c, user, run["project_id"])
    job = c.execute(select(table).where(table.c.run_id == rid)).mappings().first()
    if not job:
        raise DomainError("PERMISSION_DENIED", "Not a protocol job")
    snapshot = job["accepted_snapshot"]
    if not isinstance(snapshot, dict):
        raise DomainError("VERSION_CONFLICT", "Invalid accepted protocol snapshot")
    accepted_seals = (
        c.execute(
            select(events.c.data).where(
                events.c.run_id == rid, events.c.kind == "PROTOCOL_ACCEPTED"
            )
        )
        .scalars()
        .all()
    )
    if len(accepted_seals) != 1 or accepted_seals[0] != {
        "phase": job["kind"],
        "fingerprint": fingerprint(snapshot),
    }:
        raise DomainError("VERSION_CONFLICT", "Accepted protocol seal changed")
    if (
        fingerprint(snapshot) != job["fingerprint"]
        or job["fingerprint"] != run["fingerprint"]
        or snapshot.get("namespace") != NAMESPACE
        or any(
            snapshot.get(k) != run[k]
            for k in ["run_id", "project_id", "principal_id", "runtime_id"]
            if k != "run_id"
        )
        or snapshot.get("run_id") != rid
        or snapshot.get("phase") != job["kind"]
        or job["project_id"] != run["project_id"]
        or job["principal_id"] != user
        or job["runtime_id"] != run["runtime_id"]
    ):
        raise DomainError("VERSION_CONFLICT", "Protocol snapshot changed")
    if stop_only:
        return {**dict(job), "phase": job["kind"], "snapshot": snapshot, "result": None}, dict(run)
    from .protocol_reviews import contract_snapshot

    if snapshot.get("contract") != contract_snapshot(
        snapshot.get("contract", {}).get("contract_id")
    ):
        raise DomainError("VERSION_CONFLICT", "Frozen evaluation registry changed")
    _authority(store, c, run, snapshot)
    if run["result"] is not None and (
        job["result_snapshot"] != run["result"]
        or job["result_fingerprint"] != fingerprint(run["result"])
    ):
        raise DomainError("VERSION_CONFLICT", "Protocol result changed")
    _completed(store, c, job, run)
    _dependencies(store, c, user, snapshot)
    return {
        **dict(job),
        "phase": job["kind"],
        "snapshot": snapshot,
        "result": job["result_snapshot"],
    }, dict(run)


def protocol_run_ids(c, rid=None):
    """Central marker oracle; optional per-Run lookups avoid scanning unrelated rows."""
    jobs_query = select(_table().c.run_id)
    events_query = select(events.c.run_id).where(events.c.kind == "PROTOCOL_ACCEPTED")
    runs_query = select(runs.c.id, runs.c.context, runs.c.result)
    contracts_query = select(run_contracts)
    if rid is not None:
        jobs_query = jobs_query.where(_table().c.run_id == rid)
        events_query = events_query.where(events.c.run_id == rid)
        runs_query = runs_query.where(runs.c.id == rid)
        contracts_query = contracts_query.where(run_contracts.c.run_id == rid)
    ids = set(c.execute(jobs_query).scalars())
    ids.update(c.execute(events_query).scalars())
    for run in c.execute(runs_query).mappings():
        context, result = run["context"], run["result"]
        if isinstance(context, dict) and context.get("kind") == NAMESPACE:
            ids.add(run["id"])
        if (
            isinstance(result, dict)
            and isinstance(result.get("protocol_result"), dict)
            and result["protocol_result"].get("kind") == "model-protocol.v1"
        ):
            ids.add(run["id"])
    for contract in c.execute(contracts_query).mappings():
        saved = contract["snapshot"]
        goal = saved.get("goal") if isinstance(saved, dict) else None
        constraints = goal.get("constraints") if isinstance(goal, dict) else None
        if (
            isinstance(constraints, list)
            and NAMESPACE in constraints
            and fingerprint(saved) == contract["fingerprint"]
        ):
            ids.add(contract["run_id"])
    return ids


def is_protocol_job(store, rid):
    with store.engine.connect() as c:
        return rid in protocol_run_ids(c, rid)


def _attempt_seal(attempt):
    return {
        "attempt_id": attempt["id"],
        "safe_response_fingerprint": fingerprint(attempt["response"]),
        "usage": attempt["usage"],
        "model_identity": attempt["parameters"].get("model_identity"),
        "parameters_fingerprint": fingerprint(attempt["parameters"]),
        "request_model": attempt["request_model"],
        "response_model": attempt["response_model"],
        "mode": attempt["mode"],
        "status": attempt["status"],
    }


def _operation_seal(c, operation):
    intent = c.execute(
        select(operation_intents.c.request).where(
            operation_intents.c.operation_id == operation["id"]
        )
    ).scalar_one()
    return {
        "operation_id": operation["id"],
        "call_id": operation["call_id"],
        "tool_ref": operation["tool_ref"],
        "status": operation["status"],
        "request_fingerprint": operation["fingerprint"],
        "intent_fingerprint": fingerprint(intent),
        "receipt_fingerprint": fingerprint(operation["receipt"]),
    }


def _completed(store, c, job, run):
    result = job["result_snapshot"]
    if result is None:
        if job["result_fingerprint"] is not None or job["completed_fence"] is not None:
            raise DomainError("VERSION_CONFLICT")
        return
    seals = (
        c.execute(
            select(events.c.data).where(
                events.c.run_id == run["id"], events.c.kind == "PROTOCOL_COMPLETED"
            )
        )
        .scalars()
        .all()
    )
    if len(seals) != 1 or seals[0] != {
        "result_fingerprint": fingerprint(result),
        "completed_fence": result["completed_fence"],
        "completed_run_version": result["completed_run_version"],
    }:
        raise DomainError("VERSION_CONFLICT", "Independent completion seal changed")
    if (
        result["completed_fence"] != job["completed_fence"]
        or result["completed_fence"] != run["fence"]
    ):
        raise DomainError("VERSION_CONFLICT")
    actual_ops = (
        c.execute(
            select(operations).where(operations.c.run_id == run["id"]).order_by(operations.c.id)
        )
        .mappings()
        .all()
    )
    actual_attempts = (
        c.execute(
            select(attempts).where(attempts.c.run_id == run["id"]).order_by(attempts.c.created_at)
        )
        .mappings()
        .all()
    )
    if fingerprint(result.get("operation_seals")) != fingerprint(
        [_operation_seal(c, o) for o in actual_ops]
    ):
        raise DomainError(
            "VERIFICATION_FAILED", "Actual Operation differs from immutable completion seal"
        )
    if fingerprint(result.get("attempt_seals")) != fingerprint(
        [_attempt_seal(a) for a in actual_attempts]
    ):
        raise DomainError(
            "VERIFICATION_FAILED", "Actual Attempt differs from immutable completion seal"
        )
    if (
        set(result["operation_refs"]) != {o["id"] for o in actual_ops}
        or set(result["attempt_refs"]) != {a["id"] for a in actual_attempts}
        or any(o["status"] != "VERIFIED" for o in actual_ops)
        or any(a["status"] != "RECEIVED" for a in actual_attempts)
        or not actual_attempts
    ):
        raise DomainError("VERIFICATION_FAILED", "Full verified operation/Attempt ledger required")
    for operation in actual_ops:
        intent = c.execute(
            select(operation_intents.c.request).where(
                operation_intents.c.operation_id == operation["id"]
            )
        ).scalar()
        if (
            not intent
            or fingerprint(intent) != operation["fingerprint"]
            or set(intent) != {"tool", "args"}
            or intent["tool"] != "resource.read"
            or operation["tool_ref"] != intent["tool"]
        ):
            raise DomainError("VERIFICATION_FAILED")
        data = authorized_read(
            store,
            c,
            run["principal_id"],
            run["runtime_id"],
            run["project_id"],
            "resource.read",
            intent["args"],
        )
        expected_receipt = {
            "operation_id": operation["id"],
            "status": "VERIFIED",
            "data": data,
            "artifact_refs": [],
            "receipt_ref": operation["id"],
            "check_results": [{"check": "receipt.readback.v1", "status": "PASS"}],
            "usage_ref": None,
            "error": None,
        }
        if fingerprint(operation["receipt"]) != fingerprint(expected_receipt):
            raise DomainError(
                "VERIFICATION_FAILED", "Full receipt identity/readback/check evidence changed"
            )
    from .model import normalize_usage, require_returned_model, returned_model_identity

    metadata = []
    for attempt in actual_attempts:
        raw = attempt["response"]
        identity = returned_model_identity(
            "intern-s2", raw.get("model") if isinstance(raw, dict) else None
        )
        require_returned_model(identity)
        usage = normalize_usage(raw)
        if (
            usage["status"] != "known"
            or fingerprint(usage) != fingerprint(attempt["usage"])
            or attempt["response_model"] != raw["model"]
            or fingerprint(attempt["parameters"].get("model_identity")) != fingerprint(identity)
        ):
            raise DomainError("VERIFICATION_FAILED")
        metadata.append({"identity": identity, "usage": usage})
    if job["kind"] != "extract":
        evidence = result["protocol_result"]["evidence"]
        if not actual_ops or fingerprint(evidence["attempts"]) != fingerprint(metadata):
            raise DomainError("VERIFICATION_FAILED")
        trace = []
        for operation in actual_ops:
            intent = c.execute(
                select(operation_intents.c.request).where(
                    operation_intents.c.operation_id == operation["id"]
                )
            ).scalar_one()
            trace.append(
                {
                    "tool": intent["tool"],
                    "args": intent["args"],
                    "data": operation["receipt"]["data"],
                }
            )
        if sorted(fingerprint(t) for t in trace) != sorted(
            fingerprint(t) for t in evidence["tool_trace"]
        ):
            raise DomainError("VERIFICATION_FAILED", "Protocol trace differs from verified ledger")
        if job["kind"] == "source":
            from .model import parse_response

            calls = {}
            for attempt in actual_attempts:
                _, requested = parse_response(attempt["response"])
                for call in requested:
                    cid = "protocol:" + fingerprint(
                        {"attempt_id": attempt["id"], "tool_call_id": call["id"]}
                    )
                    calls[cid] = {"tool": call["function"]["name"], "args": call["args"]}
            if set(calls) != {o["call_id"] for o in actual_ops}:
                raise DomainError(
                    "VERIFICATION_FAILED", "Source operations do not bind actual model calls"
                )
            for operation in actual_ops:
                intent = c.execute(
                    select(operation_intents.c.request).where(
                        operation_intents.c.operation_id == operation["id"]
                    )
                ).scalar_one()
                if fingerprint(intent) != fingerprint(calls[operation["call_id"]]):
                    raise DomainError("VERIFICATION_FAILED")
            final = strict_json(
                actual_attempts[-1]["response"]["choices"][0]["message"]["content"], 16000
            )
            if fingerprint(final) != fingerprint(evidence["output"]):
                raise DomainError(
                    "VERIFICATION_FAILED", "Source output differs from actual provider response"
                )
        if job["kind"] == "cold":
            accepted = job["accepted_snapshot"]
            expected_calls = {}
            for node in accepted["compiled_plan"]["candidate"]["steps"]:
                if node["kind"] == "registered_tool":
                    ref = node["inputs"]["resource_id"]["ref"]
                    cid = "protocol:" + fingerprint(
                        {
                            "plan_fingerprint": accepted["compiled_plan"]["plan_fingerprint"],
                            "step_id": node["id"],
                        }
                    )
                    expected_calls[cid] = {
                        "tool": "resource.read",
                        "args": {"resource_id": accepted["payload"]["resource_bindings"][ref]},
                    }
            if set(expected_calls) != {o["call_id"] for o in actual_ops}:
                raise DomainError(
                    "VERIFICATION_FAILED", "Cold operations differ from compiled step identities"
                )
            for operation in actual_ops:
                if operation["fingerprint"] != fingerprint(expected_calls[operation["call_id"]]):
                    raise DomainError("VERIFICATION_FAILED")
    else:
        candidate = strict_json(
            actual_attempts[-1]["response"]["choices"][0]["message"]["content"], 16000
        )
        if fingerprint(candidate) != result["compiled_plan"]["candidate_fingerprint"]:
            raise DomainError(
                "VERIFICATION_FAILED", "Compiled candidate differs from actual provider response"
            )


def enqueue(store, user, pid, phase, payload, key, limits):
    if not isinstance(key, str) or not 1 <= len(key) <= 100:
        raise DomainError("INVALID_INPUT")
    payload = _closed(phase, payload)
    limits = Limits.model_validate(limits.model_dump() if isinstance(limits, Limits) else limits)
    request_fp = fingerprint({"phase": phase, "payload": payload, "limits": limits.model_dump()})
    table = _table()
    with store.tx() as c:
        project = store.lock_project(c, user, pid)
        source, compiled = None, None
        if phase == "source":
            refs, goal = payload["resource_ids"], payload["goal"]
        elif phase == "extract":
            source = _source(
                store, c, user, payload["source_run_id"], payload["expected_source_fingerprint"]
            )
            _, parent = verified_pending(store, c, user, source["run_id"])
            if parent["project_id"] != pid:
                raise DomainError("PERMISSION_DENIED")
            refs, goal = parent["resource_refs"], parent["goal"]
        else:
            compiled = _plan(
                store, c, user, payload["extraction_run_id"], payload["expected_plan_fingerprint"]
            )
            source = _source(
                store, c, user, compiled["source_run_id"], compiled["source_result_fingerprint"]
            )
            _, parent = verified_pending(store, c, user, source["run_id"])
            if parent["project_id"] != pid:
                raise DomainError("PERMISSION_DENIED")
            bindings = payload["resource_bindings"]
            if set(bindings) != set(compiled["candidate"]["resources"]):
                raise DomainError("INVALID_INPUT", "Exact compiled resource bindings required")
            refs = list(dict.fromkeys(parent["resource_refs"] + list(bindings.values())))
            goal = parent["goal"]
        if len(set(refs)) != len(refs) or not 1 <= len(refs) <= 8:
            raise DomainError("INVALID_INPUT")
        for ref in refs:
            store.authorize(c, user, project["runtime_id"], pid, ref, "resource.read")
        from .protocol_reviews import freeze_contract

        if phase in {"source", "cold"}:
            actual_refs = (
                payload["resource_ids"]
                if phase == "source"
                else list(payload["resource_bindings"].values())
            )
            material = list(
                c.execute(select(resources).where(resources.c.id.in_(actual_refs))).mappings()
            )
            registered = freeze_contract(
                payload["contract_id"], phase, goal, [{"content_hash": r["hash"]} for r in material]
            )
            if fingerprint(payload["inputs"]) != registered["expected_inputs_fingerprint"]:
                raise DomainError(
                    "PERMISSION_DENIED", "Inputs differ from frozen evaluation contract"
                )
        else:
            if source is None:
                raise DomainError("VERIFICATION_FAILED")
            source_job, _ = verified_pending(store, c, user, source["run_id"])
            registered = copy.deepcopy(source_job["snapshot"]["contract"])
        old = (
            c.execute(
                select(runs).where(
                    runs.c.project_id == pid,
                    runs.c.principal_id == user,
                    runs.c.request_key == "protocol:" + key,
                )
            )
            .mappings()
            .first()
        )
        if old:
            job, current = verified_pending(store, c, user, old["id"])
            if job["snapshot"]["request_fingerprint"] != request_fp:
                raise DomainError("VERSION_CONFLICT")
            return _public(job, current, cached=True)
        rid = new_id("run")
        scope = Scope(
            approval_id=rid,
            project_id=pid,
            resource_ids=refs,
            tool_refs=["resource.read"],
            max_requests=min(limits.max_requests, 1 if phase == "extract" else 3),
            mode="offline",
            model="intern-s2",
        ).model_dump()
        if compiled:
            validate_candidate(compiled["candidate"], Scope.model_validate(scope))
        from .protocol_pool import selected_pool

        snapshot = {
            "request_pool_id": selected_pool("offline"),
            "namespace": NAMESPACE,
            "version": 1,
            "run_id": rid,
            "project_id": pid,
            "principal_id": user,
            "runtime_id": project["runtime_id"],
            "phase": phase,
            "payload": payload,
            "scope": scope,
            "limits": limits.model_dump(),
            "contract": registered,
            "request_fingerprint": request_fp,
            "source": source,
            "compiled_plan": compiled,
        }
        contract = FrozenRunContract(
            run_id=rid,
            runtime_id=project["runtime_id"],
            contract_version="F1.3",
            goal=GoalSpec(
                goal_id=new_id("goal"),
                project_id=pid,
                owner_id=user,
                goal=goal,
                constraints=[NAMESPACE],
                acceptance_version="F1-tool-chain.v1",
                resource_refs=refs,
                unresolved=["Independent semantic review pending"],
            ),
            resources=[
                ResourceSnapshot(
                    resource_id=r["id"], revision=1, content_hash=r["hash"], format=r["format"]
                )
                for r in c.execute(select(resources).where(resources.c.id.in_(refs))).mappings()
            ],
            limits=limits,
            mode="mock",
            request_model="intern-s2",
        ).model_dump()
        now, fp = time.time(), fingerprint(snapshot)
        c.execute(
            insert(run_contracts).values(
                run_id=rid, snapshot=contract, fingerprint=fingerprint(contract)
            )
        )
        c.execute(
            insert(runs).values(
                id=rid,
                project_id=pid,
                principal_id=user,
                runtime_id=project["runtime_id"],
                goal=goal,
                resource_refs=refs,
                status="QUEUED",
                request_key="protocol:" + key,
                fingerprint=fp,
                created_at=now,
                lease_until=0,
                fence=0,
                context={
                    "kind": NAMESPACE,
                    "messages": [],
                    "requests": 0,
                    "tools": 0,
                    "repairs": 0,
                    "reserved_tokens": 0,
                },
                version=1,
                cancel_intent=False,
            )
        )
        c.execute(
            insert(table).values(
                run_id=rid,
                project_id=pid,
                principal_id=user,
                runtime_id=project["runtime_id"],
                kind=phase,
                accepted_snapshot=snapshot,
                fingerprint=fp,
                created_at=now,
            )
        )
        store.event(c, rid, "PROTOCOL_ACCEPTED", {"phase": phase, "fingerprint": fp})
        job, run = verified_pending(store, c, user, rid)
        return _public(job, run)


def _public(job, run, *, cached=False):
    return {
        "namespace": NAMESPACE,
        "semantic_status": "NOT_RUN" if job["phase"] == "extract" else "UNKNOWN",
        "semantic_review": "NOT_RUN" if job["phase"] == "extract" else "WAITING_APPROVAL",
        "owner_semantic_acceptance": "PENDING",
        "run_id": run["id"],
        "phase": job["phase"],
        "status": run["status"],
        "version": run["version"],
        "fence": run["fence"],
        "result": job["result"],
        "result_fingerprint": job["result_fingerprint"],
        "error": run["error"],
        "cached": cached,
        "formal_publication_enabled": False,
    }


def inspect(store, user, rid):
    with store.tx() as c:
        job, run = verified_pending(store, c, user, rid)
        value = _public(job, run)
        if job["phase"] in {"source", "cold"} and run["status"] == "SUCCEEDED":
            from .protocol_reviews import review_proof

            proof = review_proof(store, c, user, rid)
            value["semantic_status"] = proof["semantic_status"]
            value["semantic_review"] = "APPROVED"
        return value


def _dependencies(store, c, user, snapshot):
    source = snapshot["source"]
    if source is not None:
        fresh = _source(store, c, user, source["run_id"], source["result_fingerprint"])
        if fresh != source:
            raise DomainError("VERSION_CONFLICT", "Source review changed")
    if snapshot["phase"] == "cold":
        payload = snapshot["payload"]
        if (
            _plan(
                store, c, user, payload["extraction_run_id"], payload["expected_plan_fingerprint"]
            )
            != snapshot["compiled_plan"]
        ):
            raise DomainError("VERSION_CONFLICT", "Compiled source plan changed")


def fail_job(worker, run, error):
    with worker.store.tx() as c:
        current = (
            c.execute(select(runs).where(runs.c.id == run["id"]).with_for_update())
            .mappings()
            .first()
        )
        if (
            not current
            or current["fence"] != run["fence"]
            or current["worker_id"] != worker.id
            or current["lease_until"] <= time.time()
        ):
            return
        if current["status"] not in {"RUNNING", "PAUSE_REQUESTED", "CANCEL_REQUESTED"}:
            return
        state = (
            "CANCELLED"
            if current["status"] == "CANCEL_REQUESTED"
            else "PAUSED"
            if current["status"] == "PAUSE_REQUESTED"
            else "WAITING_RESOURCE"
            if error.code
            in {"GRANT_REVOKED", "RESOURCE_UNAVAILABLE", "OUTCOME_UNKNOWN", "RATE_LIMITED"}
            else "FAILED"
        )
        if worker.store.has_unknown(c, run["id"]):
            state = "RECONCILING" if current["cancel_intent"] else "WAITING_RESOURCE"
        c.execute(
            update(runs)
            .where(runs.c.id == run["id"])
            .values(
                status=state, error=error.public(), lease_until=0, version=current["version"] + 1
            )
        )
        worker.store.event(
            c, run["id"], "PROTOCOL_STATE", {"status": state, "error": error.public()}
        )


def process_job(worker, run):
    store, rid, fence = worker.store, run["id"], run["fence"]
    stopped = threading.Event()

    def beat():
        while not stopped.wait(worker.s.lease_seconds / 3):
            try:
                store.heartbeat(worker.id, rid, fence, worker.s.lease_seconds)
            except Exception:
                stopped.set()

    thread = threading.Thread(target=beat, daemon=True)
    thread.start()
    try:
        with store.tx() as c:
            job, current = verified_pending(store, c, run["principal_id"], rid)
            current = store.guard(c, rid, fence)
            snapshot = copy.deepcopy(job["snapshot"])
            _dependencies(store, c, run["principal_id"], snapshot)
        if worker.s.mode == "live" or snapshot["scope"]["mode"] != "offline":
            raise DomainError("PERMISSION_DENIED", "LIVE protocol execution is disabled")
        if current["context"]["requests"] > 0:
            raise DomainError(
                "OUTCOME_UNKNOWN",
                "Protocol continuation requires explicit reconciliation; no hidden resend",
            )
        factory = getattr(worker, "protocol_runner_factory", None)
        if not callable(factory):
            raise DomainError(
                "RESOURCE_UNAVAILABLE", "Explicit offline protocol provider is not configured"
            )
        worker.s = replace(
            worker.s, **{k: min(getattr(worker.s, k), v) for k, v in snapshot["limits"].items()}
        )
        runner = factory(worker, run, snapshot)
        import httpx

        from .model import InternModel
        from .model_budget import BudgetedProvider
        from .protocol_api import ProtocolAttemptRunner

        if (
            type(runner) is not ProtocolAttemptRunner
            or runner.worker is not worker
            or not worker.store.test_only
            or worker.s.mode != "mock"
            or fingerprint(snapshot) != job["fingerprint"]
            or fingerprint(runner.snapshot) != job["fingerprint"]
            or runner.run != run
            or type(runner.provider) is not BudgetedProvider
            or type(runner.provider.model) is not InternModel
            or not isinstance(runner.provider.model.transport, httpx.MockTransport)
            or runner.provider.scope != snapshot["scope"]
        ):
            raise DomainError(
                "PERMISSION_DENIED", "Only explicit zero-network protocol adapter is enabled"
            )

        def read(tool, args, context):
            with store.tx() as c:
                verified_pending(store, c, run["principal_id"], rid)
                live = store.guard(c, rid, fence)
                if live["status"] != "RUNNING" or worker.stop.is_set():
                    raise DomainError("VERSION_CONFLICT")
                verified_pending(store, c, run["principal_id"], rid)
                _dependencies(store, c, run["principal_id"], snapshot)
            if tool != "resource.read":
                raise DomainError("UNSUPPORTED_CAPABILITY")
            if snapshot["phase"] == "source":
                aid = getattr(runner, "request_attempt_ids", {}).get(context["request_index"])
                with store.tx() as c:
                    attempt = (
                        c.execute(
                            select(attempts).where(
                                attempts.c.id == aid,
                                attempts.c.run_id == rid,
                                attempts.c.status == "RECEIVED",
                            )
                        )
                        .mappings()
                        .first()
                    )
                    if not attempt:
                        raise DomainError(
                            "VERIFICATION_FAILED", "Source read must bind its actual model Attempt"
                        )
                binding = {"attempt_id": aid, "tool_call_id": context["tool_call_id"]}
            else:
                binding = {
                    "plan_fingerprint": snapshot["compiled_plan"]["plan_fingerprint"],
                    "step_id": context["step_id"],
                }
            call_id = "protocol:" + fingerprint(binding)
            receipt = dispatch(
                store, rid, fence, {"id": call_id, "function": {"name": tool}, "args": args}
            )
            if receipt["status"] != "VERIFIED":
                raise DomainError("OUTCOME_UNKNOWN")
            return receipt["data"]

        def verify(stage, evidence):
            if stage != "source" or snapshot["source"] is None:
                return None
            with store.tx() as c:
                frozen = _source(
                    store,
                    c,
                    run["principal_id"],
                    snapshot["source"]["run_id"],
                    snapshot["source"]["result_fingerprint"],
                )
                source_job, _ = verified_pending(store, c, run["principal_id"], frozen["run_id"])
                if fingerprint(evidence) != fingerprint(
                    source_job["result"]["protocol_result"]["evidence"]
                ):
                    raise DomainError("VERIFICATION_FAILED")
                return frozen["proof"]

        payload, phase = snapshot["payload"], snapshot["phase"]
        source_result = None
        source_request_limit = None
        if snapshot["source"]:
            with store.tx() as c:
                source_job, _ = verified_pending(
                    store, c, run["principal_id"], snapshot["source"]["run_id"]
                )
            source_request_limit = source_job["snapshot"]["scope"]["max_requests"]
            source_result = {
                **copy.deepcopy(source_job["result"]["protocol_result"]),
                "status": "SUCCEEDED",
                "semantic_status": "PASS",
                "verification": snapshot["source"]["proof"],
            }
        protocol = ModelProtocol(
            runner,
            scope=snapshot["scope"],
            enabled=True,
            independent_verify=verify,
            read_only=read,
            defer_evaluation=True,
            read_context=True,
            source_request_limit=source_request_limit,
        )
        compiled = None
        if phase == "source":
            result = protocol.complete_task(
                payload["goal"], payload["inputs"], payload["resource_ids"]
            )
        elif phase == "extract":
            result = protocol.extract_candidate(source_result)
            compiled = {
                "kind": "protocol-compiled-plan.v1",
                "compiler_version": COMPILER_VERSION,
                **copy.deepcopy(result),
                "source_run_id": snapshot["source"]["run_id"],
                "source_result_fingerprint": snapshot["source"]["result_fingerprint"],
            }
            compiled["kind"] = "protocol-compiled-plan.v1"
            compiled["plan_fingerprint"] = fingerprint(compiled)
        else:
            plan = snapshot["compiled_plan"]
            extracted = {
                k: plan[k]
                for k in [
                    "candidate",
                    "candidate_fingerprint",
                    "source_proof",
                    "source_proof_fingerprint",
                    "candidate_receipt",
                    "executable_by_existing_apprun",
                    "semantic_status",
                ]
            }
            extracted["kind"] = "model-protocol.v1"
            result = protocol.run_candidate(
                extracted, payload["inputs"], payload["resource_bindings"], source=source_result
            )
        with store.tx() as c:
            verified_pending(store, c, run["principal_id"], rid)
            current = store.guard(c, rid, fence)
            _dependencies(store, c, run["principal_id"], snapshot)
            if current["status"] != "RUNNING" or worker.stop.is_set():
                raise DomainError("VERSION_CONFLICT")
            if store.has_unknown(c, rid):
                raise DomainError("OUTCOME_UNKNOWN")
            if phase != "extract" and (
                result.get("status") != "AWAITING_EVALUATION"
                or result.get("semantic_status") != "UNKNOWN"
            ):
                raise DomainError(
                    "VERIFICATION_FAILED", "Technical execution cannot sign semantic acceptance"
                )
            final = {
                "protocol_result": result,
                "completed_fence": fence,
                "completed_run_version": current["version"] + 1,
                "operation_refs": list(
                    c.execute(
                        select(operations.c.id).where(
                            operations.c.run_id == rid, operations.c.status == "VERIFIED"
                        )
                    ).scalars()
                ),
                "attempt_refs": list(
                    c.execute(
                        select(attempts.c.id).where(
                            attempts.c.run_id == rid, attempts.c.status == "RECEIVED"
                        )
                    ).scalars()
                ),
                "scope": snapshot["scope"],
                "operation_seals": [
                    _operation_seal(c, o)
                    for o in c.execute(
                        select(operations)
                        .where(operations.c.run_id == rid)
                        .order_by(operations.c.id)
                    ).mappings()
                ],
                "attempt_seals": [
                    _attempt_seal(a)
                    for a in c.execute(
                        select(attempts)
                        .where(attempts.c.run_id == rid)
                        .order_by(attempts.c.created_at)
                    ).mappings()
                ],
            }
            if compiled is not None:
                final["compiled_plan"] = compiled
            state = "SUCCEEDED" if phase == "extract" else "WAITING_APPROVAL"
            c.execute(
                update(_table())
                .where(_table().c.run_id == rid)
                .values(
                    result_snapshot=final,
                    result_fingerprint=fingerprint(final),
                    completed_fence=fence,
                )
            )
            c.execute(
                update(runs)
                .where(runs.c.id == rid)
                .values(result=final, status=state, lease_until=0, version=current["version"] + 1)
            )
            store.event(
                c,
                rid,
                "PROTOCOL_COMPLETED",
                {
                    "result_fingerprint": fingerprint(final),
                    "completed_fence": fence,
                    "completed_run_version": current["version"] + 1,
                },
            )
            store.event(
                c,
                rid,
                "PROTOCOL_STATE",
                {
                    "status": state,
                    "semantic_status": "NOT_RUN" if phase == "extract" else "UNKNOWN",
                },
            )
    except DomainError as exc:
        fail_job(worker, run, exc)
    finally:
        stopped.set()
        thread.join(timeout=2)


def command_job(store, user, rid, command, version):
    """Stopping needs metadata ownership; resuming requires current authority.

    No protected results are returned here. Incomplete model execution cannot be
    resumed until a separately implemented trusted continuation reconciles it.
    """
    if command not in {"pause", "cancel", "resume"} or type(version) is not int:
        raise DomainError("INVALID_INPUT")
    with store.tx() as c:
        job, run = verified_pending(store, c, user, rid, stop_only=command != "resume")
        if run["version"] != version:
            raise DomainError("VERSION_CONFLICT")
        if command == "resume":
            if (
                store.has_unknown(c, rid)
                or run["context"]["requests"] > 0
                or job["result_snapshot"] is not None
            ):
                raise DomainError("OUTCOME_UNKNOWN", "Protocol continuation cannot blindly resend")
            if run["status"] not in {"PAUSED", "WAITING_RESOURCE", "WAITING_INPUT"}:
                raise DomainError("VERSION_CONFLICT")
            state = "QUEUED"
        elif command == "pause":
            if run["status"] == "PAUSE_REQUESTED" and store.has_unknown(c, rid):
                state = "WAITING_RESOURCE"
            elif run["status"] == "RUNNING":
                state = "PAUSE_REQUESTED"
            elif run["status"] in {
                "QUEUED",
                "WAITING_RESOURCE",
                "WAITING_INPUT",
                "WAITING_APPROVAL",
            }:
                state = "PAUSED"
            else:
                raise DomainError("VERSION_CONFLICT")
        else:
            if run["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
                raise DomainError("VERSION_CONFLICT")
            state = (
                "CANCEL_REQUESTED"
                if run["status"] in {"RUNNING", "PAUSE_REQUESTED"}
                else "CANCELLED"
            )
        if command != "resume" and store.has_unknown(c, rid):
            if command == "cancel" or run["cancel_intent"]:
                state = (
                    "CANCEL_REQUESTED"
                    if run["status"] in {"RUNNING", "PAUSE_REQUESTED"}
                    else "RECONCILING"
                )
            else:
                state = "PAUSE_REQUESTED" if run["status"] == "RUNNING" else "WAITING_RESOURCE"
        values = {"status": state, "version": version + 1}
        if command == "cancel":
            values["cancel_intent"] = True
        if state not in {"PAUSE_REQUESTED", "CANCEL_REQUESTED"}:
            values["lease_until"] = 0
        c.execute(update(runs).where(runs.c.id == rid).values(**values))
        store.event(c, rid, "PROTOCOL_CONTROL", {"command": command, "status": state})
        return {"namespace": NAMESPACE, "run_id": rid, "status": state, "version": version + 1}
