"""Controller-only offline handoff oracle; never an approval or LIVE activation.

Existing offline fixtures remain independent. Any future activation must wire this
oracle into its actual sender and add the explicitly listed missing real gates.
"""

import copy
import re
import time

from pydantic import Field, ValidationError
from sqlalchemy import select

from .contracts import Strict, resource_id
from .db import attempts, events, fingerprint, operations, protocol_request_slots, resources
from .errors import DomainError
from .model_budget import ENDPOINT, READ_TOOL_FINGERPRINT, STAGES
from .model_protocol import obj
from .protocol_jobs import verified_pending
from .protocol_pool import audit_pool
from .protocol_reviews import contract_snapshot

VERSION = "protocol-offline-handoff.v1"
EVENT = "PROTOCOL_OFFLINE_HANDOFF"
BLOCKERS = [
    "LIVE approval and exact outbound data/wire approval absent",
    "Real provider transport activation absent",
    "Six stages share neither one sidecar scope nor a global six-second clock",
    "Private sidecar path and persistent experiment identity not approved",
    "Real semantic acceptance remains independent and UNKNOWN",
]


class HandoffInput(Strict):
    expected_version: int = Field(ge=1)
    expected_fence: int = Field(ge=0)
    request_key: str = Field(min_length=1, max_length=100)


def candidate_for(public_contract, resource_ids):
    """One public read/interpret template; no source answer-bearing free fields."""
    registered = contract_snapshot(public_contract.get("contract_id"))
    if fingerprint(public_contract) != fingerprint(registered):
        raise DomainError("VERSION_CONFLICT", "Registered public contract required")
    if (
        not isinstance(resource_ids, list)
        or not 1 <= len(resource_ids) <= 6
        or len(set(resource_ids)) != len(resource_ids)
    ):
        raise DomainError("INVALID_INPUT")
    for rid in resource_ids:
        resource_id(rid)
    bindings = {f"material_{i}": rid for i, rid in enumerate(resource_ids)}
    steps = [
        {
            "id": f"read_{i}",
            "kind": "registered_tool",
            "depends_on": [],
            "inputs": {
                "resource_id": {"source": "data", "ref": f"material_{i}", "field": "resource_id"}
            },
            "tool_ref": "resource.read",
        }
        for i in range(len(resource_ids))
    ]
    steps.append(
        {
            "id": "interpret",
            "kind": "language",
            "depends_on": [f"read_{i}" for i in range(len(resource_ids))],
            "inputs": {
                "format": {"source": "input", "ref": "input", "field": "format"},
                **{
                    f"material_{i}": {"source": "step", "ref": f"read_{i}", "field": "content"}
                    for i in range(len(resource_ids))
                },
            },
            "instruction": registered["public_goal"],
            "output_schema": registered["output_schema"],
        }
    )
    return {
        "schema_version": "model-protocol.v1",
        "input_schema": obj({"format": {"type": "string"}}),
        "resources": bindings,
        "steps": steps,
        "output_schema": registered["output_schema"],
        "outputs": {
            key: {"source": "step", "ref": "interpret", "field": key}
            for key in registered["output_schema"]["properties"]
        },
    }


def validate_handoff_candidate(candidate, public_contract, source_resource_ids):
    expected = candidate_for(public_contract, source_resource_ids)
    if fingerprint(candidate) != fingerprint(expected):
        raise DomainError(
            "UNSUPPORTED_CAPABILITY",
            "Cold handoff requires the exact public template; free fields may contain source answers",
        )
    return fingerprint(candidate)


def _prepared(store, c, job, run):
    snapshot = job["snapshot"]
    if not store.test_only or snapshot["scope"]["mode"] != "offline":
        raise DomainError("PERMISSION_DENIED", "Only explicit offline engineering handoff exists")
    contract = snapshot["contract"]
    match = re.fullmatch(r"protocol\.synthetic\.([ab])-(source|cold)\.v1", contract["contract_id"])
    if not match:
        raise DomainError("RESOURCE_UNAVAILABLE", "No registered offline experiment family")
    phase = job["phase"]
    if match[2] != ("cold" if phase == "cold" else "source"):
        raise DomainError("VERSION_CONFLICT", "Registered material role differs from phase")
    stage = phase + "_" + match[1]
    if stage not in STAGES:
        raise DomainError("VERSION_CONFLICT")
    # Complete every dependency/Run lock before taking the shared pool lock.
    # No verified_pending or other project/Run acquisition follows audit_pool.
    source: dict = {}
    candidate_fp = None
    if phase in {"extract", "cold"}:
        source, _ = verified_pending(store, c, run["principal_id"], snapshot["source"]["run_id"])
    if phase == "source":
        egress_ids = snapshot["payload"]["resource_ids"]
    elif phase == "cold":
        egress_ids = list(snapshot["payload"]["resource_bindings"].values())
        candidate_fp = validate_handoff_candidate(
            snapshot["compiled_plan"]["candidate"],
            contract,
            source["snapshot"]["scope"]["resource_ids"],
        )
    else:
        egress_ids = source["result"]["protocol_result"]["evidence"]["resource_ids"]
    pool = audit_pool(c, snapshot["request_pool_id"])
    if not pool["consistent"] or pool["halted"] or pool["has_pending"] or pool["has_unknown"]:
        raise DomainError("OUTCOME_UNKNOWN", "Shared experiment cannot hand off unresolved sends")
    if (
        pool["reserved_requests"] >= pool["request_limit"]
        or pool["reserved_tokens"] >= pool["token_limit"]
    ):
        raise DomainError("BUDGET_EXHAUSTED")
    rows = (
        c.execute(select(resources).where(resources.c.id.in_(snapshot["scope"]["resource_ids"])))
        .mappings()
        .all()
    )
    data = sorted(
        [{"resource_id": r["id"], "format": r["format"], "sha256": r["hash"]} for r in rows],
        key=lambda r: r["resource_id"],
    )
    return {
        "namespace": VERSION,
        "run_id": run["id"],
        "project_id": run["project_id"],
        "principal_id": run["principal_id"],
        "accepted_snapshot_fingerprint": job["fingerprint"],
        "scope_fingerprint": fingerprint(snapshot["scope"]),
        "contract_fingerprint": contract["fingerprint"],
        "phase": phase,
        "stage": stage,
        "dependency_resources": data,
        "egress": {
            "transport": "httpx.MockTransport only",
            "target_endpoint": ENDPOINT,
            "actual_network": False,
            "model": "intern-s2",
            "stream": False,
            "max_output_tokens": 1024,
            "max_wire_characters": 8000,
            "max_wire_bytes": 10000,
            "tool_schema_fingerprint": READ_TOOL_FINGERPRINT,
            "resources": [r for r in data if r["resource_id"] in egress_ids],
            "public_goal": contract["public_goal"],
            "input_fingerprint": contract["expected_inputs_fingerprint"],
            "public_output_schema_fingerprint": fingerprint(contract["output_schema"]),
            "source_evidence_allowed": phase == "extract",
            "source_result_fingerprint": snapshot["source"]["result_fingerprint"]
            if phase == "extract"
            else None,
            "candidate_fingerprint": candidate_fp,
            "gold_or_rubric_allowed": False,
        },
        "budgets": {
            "pool_id": pool["id"],
            "pool_policy_fingerprint": pool["policy_fingerprint"],
            "db_global_request_limit": pool["request_limit"],
            "db_global_token_limit": pool["token_limit"],
            "db_single_inflight": True,
            "sidecar_scope_fingerprint": fingerprint(snapshot["scope"]),
            "sidecar_stage_request_limit": min(STAGES[stage], snapshot["scope"]["max_requests"]),
            "sidecar_spacing_seconds": 6,
            "spacing_scope": "per-sidecar, not DB-wide or six-stage experiment-wide",
        },
        "live_ready": False,
        "semantic_acceptance": "UNKNOWN",
        "automatic_review": False,
        "automatic_continuation": False,
        "activation_blockers": BLOCKERS,
    }


def prepare_handoff(store, user, rid, body):
    """Freeze an authorized, unsent QUEUED job without allocating or dispatching."""
    try:
        request = HandoffInput.model_validate(body).model_dump()
    except ValidationError as exc:
        raise DomainError("INVALID_INPUT", "Closed strict handoff request required") from exc
    with store.tx() as c:
        job, run = verified_pending(store, c, user, rid)
        if run["status"] != "QUEUED" or run["error"] is not None or run["cancel_intent"]:
            raise DomainError("VERSION_CONFLICT", "Only a fresh queued job can prepare handoff")
        if (
            request["expected_version"] != run["version"]
            or request["expected_fence"] != run["fence"]
        ):
            raise DomainError("VERSION_CONFLICT")
        if (
            run["context"].get("requests") != 0
            or job["result"] is not None
            or any(
                c.execute(select(table).where(table.c.run_id == rid)).first()
                for table in [attempts, operations, protocol_request_slots]
            )
            or c.execute(
                select(events.c.id).where(
                    events.c.run_id == rid, events.c.kind == "PROTOCOL_COMPLETED"
                )
            ).first()
        ):
            raise DomainError("OUTCOME_UNKNOWN", "Handoff cannot reset or resume any sent job")
        prepared = {
            **_prepared(store, c, job, run),
            "prepared_version": run["version"],
            "prepared_fence": run["fence"],
        }
        value = {"request": request, "prepared": prepared, "fingerprint": fingerprint(prepared)}
        prior = (
            c.execute(select(events.c.data).where(events.c.run_id == rid, events.c.kind == EVENT))
            .scalars()
            .all()
        )
        if prior:
            if len(prior) != 1 or fingerprint(prior[0]) != fingerprint(value):
                raise DomainError("VERSION_CONFLICT", "Controller handoff is immutable")
        else:
            store.event(c, rid, EVENT, value)
        return copy.deepcopy(prepared)


def require_handoff(store, user, rid):
    """Recheck a frozen offline handoff before each new model call; never sends."""
    with store.tx() as c:
        job, run = verified_pending(store, c, user, rid)
        rows = (
            c.execute(select(events).where(events.c.run_id == rid, events.c.kind == EVENT))
            .mappings()
            .all()
        )
        if len(rows) != 1 or not isinstance(rows[0]["data"], dict):
            raise DomainError("RESOURCE_UNAVAILABLE", "Explicit controller handoff missing")
        saved = rows[0]["data"]
        if set(saved) != {"request", "prepared", "fingerprint"}:
            raise DomainError("VERSION_CONFLICT")
        try:
            request = HandoffInput.model_validate(saved["request"]).model_dump()
        except ValidationError as exc:
            raise DomainError("VERSION_CONFLICT", "Stored handoff request is invalid") from exc
        prepared = _prepared(store, c, job, run)
        prepared.update(
            prepared_version=request["expected_version"], prepared_fence=request["expected_fence"]
        )
        if fingerprint(saved) != fingerprint(
            {"request": request, "prepared": prepared, "fingerprint": fingerprint(prepared)}
        ):
            raise DomainError("VERSION_CONFLICT", "Handoff data or event changed")
        if (
            run["version"] != request["expected_version"]
            or run["error"] is not None
            or run["cancel_intent"]
        ):
            raise DomainError("VERSION_CONFLICT")
        if run["status"] == "QUEUED":
            if run["fence"] != request["expected_fence"]:
                raise DomainError("VERSION_CONFLICT")
        elif run["status"] == "RUNNING":
            claims = (
                c.execute(
                    select(events.c.data).where(
                        events.c.run_id == rid,
                        events.c.kind == "CLAIMED",
                        events.c.created_at >= rows[0]["created_at"],
                    )
                )
                .scalars()
                .all()
            )
            if (
                run["lease_until"] <= time.time()
                or run["fence"] != request["expected_fence"] + 1
                or len(claims) != 1
                or fingerprint(claims[0]) != fingerprint({"fence": run["fence"]})
            ):
                raise DomainError(
                    "VERSION_CONFLICT", "Only current first worker ownership can use handoff"
                )
        else:
            raise DomainError("VERSION_CONFLICT", "Handoff never resumes or signs a result")
        return copy.deepcopy(prepared)
