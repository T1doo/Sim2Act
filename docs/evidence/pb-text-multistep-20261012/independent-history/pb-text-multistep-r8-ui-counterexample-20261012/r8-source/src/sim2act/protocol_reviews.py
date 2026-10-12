"""Independent, fixed synthetic evaluation; never exposed to the model runtime.

The registry is a service-owned allowlist, not an HTTP registration endpoint.
Exact JSON is intentionally narrow: alternate wording is not general semantic PASS.
"""

import copy
import hashlib
import time
from pathlib import Path

from fastapi import Depends
from pydantic import Field, ValidationError
from sqlalchemy import insert, select, update

from .contracts import Strict, schema_check, strict_json
from .db import events, fingerprint, new_id, protocol_reviews, runs
from .errors import DomainError
from .tools import authorized_read

VERSION = "protocol-review.v1"
ASSETS = (
    Path(__file__).resolve().parents[2] / "docs/evidence/protocol-store-loop-20261006/evaluation"
)
PINS = {
    "protocol.synthetic.a-source.v1": (
        "a-source.json",
        "89773350ebef455df85ea93034abb4bdf613d602b15101835f7d472e65ba4acf",
    ),
    "protocol.synthetic.a-cold.v1": (
        "a-cold.json",
        "a1b13eecbd7be479c4b28dad1a9abbf0c7d126b46f4466b58d159d4c0bd58d8b",
    ),
    "protocol.synthetic.b-source.v1": (
        "b-source.json",
        "ede9a7e5db423b3108e70e49af91433f63efc8bd17226ef902257063b7cd56e1",
    ),
    "protocol.synthetic.b-cold.v1": (
        "b-cold.json",
        "73f435ff6934371c50e54776030d3a00de4a54d7d6e071b8c41821bf45f4791e",
    ),
}


class ReviewInput(Strict):
    contract_id: str = Field(min_length=1, max_length=100)
    expected_result_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_fence: int = Field(ge=1, strict=True)
    expected_version: int = Field(ge=1, strict=True)
    request_key: str = Field(min_length=1, max_length=100)


def evaluation_contract(contract_id):
    """Read a pinned server-only contract. No arbitrary path, checker or gold input."""
    entry = PINS.get(contract_id)
    if entry is None:
        raise DomainError("RESOURCE_UNAVAILABLE", "No registered evaluation contract")
    name, expected = entry
    try:
        raw = (ASSETS / name).read_bytes()
    except OSError as exc:
        raise DomainError("RESOURCE_UNAVAILABLE", "Evaluation asset unavailable") from exc
    if hashlib.sha256(raw).hexdigest() != expected:
        raise DomainError("VERSION_CONFLICT", "Registered evaluation asset changed")
    value = strict_json(raw, 32000)
    if (
        value.get("id") != contract_id
        or value.get("version") != 1
        or value.get("checker") != "exact-json-semantic.v1"
        or value.get("provider_allowed") is not False
    ):
        raise DomainError("VERSION_CONFLICT", "Evaluation registry version changed")
    return value, expected


def _schema(value):
    """Public shape only: never include expected values, enums or gold explanations."""
    if isinstance(value, dict):
        return {
            "type": "object",
            "properties": {k: _schema(v) for k, v in value.items()},
            "required": list(value),
            "additionalProperties": False,
        }
    if isinstance(value, list):
        return {"type": "array", "items": _schema(value[0]), "maxItems": 16}
    return {
        "type": "boolean" if type(value) is bool else "integer" if type(value) is int else "string"
    }


def contract_snapshot(contract_id):
    """Controller freezes this registration at enqueue, before any model response."""
    contract, asset_hash = evaluation_contract(contract_id)
    shape = _schema(contract["expected_output"])
    schema_check(shape)
    value = {
        "contract_id": contract_id,
        "version": contract["version"],
        "checker": contract["checker"],
        "resource_hashes": contract["resource_hashes"],
        "public_goal": contract["public_goal"],
        "expected_inputs_fingerprint": fingerprint(contract["expected_inputs"]),
        "output_schema": shape,
        "registry_asset_ref": PINS[contract_id][0],
        "registry_asset_sha256": asset_hash,
        "gold_sha256": contract["gold_sha256"],
        "rubric_sha256": contract["rubric_sha256"],
        "review_basis": contract["review_basis"],
    }
    return {**value, "fingerprint": fingerprint(value)}


def freeze_contract(contract_id, phase, goal, resource_snapshots):
    value = contract_snapshot(contract_id)
    if (
        phase not in {"source", "cold"}
        or not contract_id.endswith(f"-{phase}.v1")
        or goal != value["public_goal"]
        or sorted(r["content_hash"] for r in resource_snapshots) != sorted(value["resource_hashes"])
    ):
        raise DomainError("PERMISSION_DENIED", "Input is outside the frozen evaluation contract")
    return value


def _pending(store, c, user, rid):
    from .protocol_jobs import verified_pending

    job, run = verified_pending(store, c, user, rid)
    frozen_contract = job["accepted_snapshot"].get("contract")
    if not isinstance(frozen_contract, dict) or frozen_contract != contract_snapshot(
        frozen_contract.get("contract_id")
    ):
        raise DomainError("VERSION_CONFLICT", "Enqueue-time evaluation contract changed")
    store.own_project(c, user, run["project_id"])
    result = job["result_snapshot"]
    if (
        job["kind"] not in {"source", "cold"}
        or not isinstance(result, dict)
        or result.get("completed_fence") != job["completed_fence"]
        or result.get("completed_fence") != run["fence"]
        or fingerprint(result) != job["result_fingerprint"]
        or run["result"] != result
    ):
        raise DomainError("VERSION_CONFLICT", "Completed protocol result changed")
    technical = result.get("protocol_result")
    if (
        not isinstance(technical, dict)
        or technical.get("kind") != "model-protocol.v1"
        or technical.get("status") != "AWAITING_EVALUATION"
        or technical.get("semantic_status") != "UNKNOWN"
        or technical.get("verification") is not None
    ):
        raise DomainError("VERIFICATION_FAILED", "Independent pending evaluation required")
    evidence = technical.get("evidence")
    if (
        not isinstance(evidence, dict)
        or set(evidence) != {"goal", "inputs", "resource_ids", "tool_trace", "output", "attempts"}
        or not isinstance(evidence["resource_ids"], list)
        or not evidence["resource_ids"]
        or not isinstance(evidence["attempts"], list)
        or not evidence["attempts"]
        or not isinstance(evidence["tool_trace"], list)
        or not evidence["tool_trace"]
    ):
        raise DomainError("VERIFICATION_FAILED", "Complete frozen evidence required")
    # Current user/project runtime intersection plus independent byte readback.
    hashes = []
    project = store.own_project(c, user, run["project_id"])
    for resource in evidence["resource_ids"]:
        for runtime in {run["runtime_id"], project["runtime_id"]}:
            value = authorized_read(
                store,
                c,
                user,
                runtime,
                run["project_id"],
                "resource.read",
                {"resource_id": resource},
            )
        hashes.append(value["hash"])
    return job, run, evidence, hashes


def _oracle(contract, evidence, hashes):
    if (
        fingerprint(evidence["goal"]) != fingerprint(contract["public_goal"])
        or fingerprint(evidence["inputs"]) != fingerprint(contract["expected_inputs"])
        or sorted(hashes) != sorted(contract["resource_hashes"])
    ):
        return "UNKNOWN", "Input does not match this frozen synthetic contract"
    if fingerprint(evidence["output"]) != fingerprint(contract["expected_output"]):
        return "FAIL", "Output fails the independently registered exact semantic assertions"
    return "PASS", "Frozen synthetic semantic assertions and provenance match"


def _proof(evidence):
    return {
        "status": "SUCCEEDED",
        "semantic_status": "PASS",
        "evidence_fingerprint": fingerprint(evidence),
        "goal_fingerprint": fingerprint(evidence["goal"]),
        "input_fingerprint": fingerprint(evidence["inputs"]),
        "output_fingerprint": fingerprint(evidence["output"]),
        "trace_fingerprint": fingerprint(evidence["tool_trace"]),
        "checks": [
            {"check_id": "frozen-source-readback.v1", "status": "PASS"},
            {"check_id": "exact-json-semantic.v1", "status": "PASS"},
        ],
    }


def _public(row):
    data = row["payload"]
    return {
        "id": row["id"],
        "run_id": row["run_id"],
        "contract_id": row["contract_id"],
        "namespace": VERSION,
        "decision": data["decision"],
        "reason": data["reason"],
        "fingerprint": row["fingerprint"],
        "publishable": False,
        "model_requests": 0,
    }


def _validated_review(c, row, contract, contract_hash, job, run, evidence):
    payload = row["payload"]
    if (
        not isinstance(payload, dict)
        or set(payload)
        != {
            "namespace",
            "request",
            "decision",
            "reason",
            "contract_hash",
            "contract_version",
            "checker",
            "reviewer",
            "review_basis",
            "evaluator",
            "gold_sha256",
            "rubric_sha256",
            "result_fingerprint",
            "completed_fence",
            "completed_run_version",
            "accepted_run_version",
            "verification",
        }
        or fingerprint(payload) != row["fingerprint"]
        or run["status"]
        != ("SUCCEEDED" if payload.get("decision") == "PASS" else "WAITING_APPROVAL")
        or run["error"] is not None
        or run["cancel_intent"]
        or row["principal_id"] != run["principal_id"]
        or row["project_id"] != run["project_id"]
        or payload.get("namespace") != VERSION
        or payload.get("contract_hash") != contract_hash
        or payload.get("checker") != contract["checker"]
        or payload.get("contract_version") != contract["version"]
        or payload.get("review_basis") != contract["review_basis"]
        or payload.get("reviewer") != contract["reviewer"]
        or payload.get("gold_sha256") != contract["gold_sha256"]
        or payload.get("rubric_sha256") != contract["rubric_sha256"]
        or payload.get("result_fingerprint") != job["result_fingerprint"]
        or payload.get("completed_fence") != run["fence"]
        or payload.get("completed_run_version") != job["result_snapshot"]["completed_run_version"]
        or payload.get("evaluator") != run["principal_id"]
        or payload.get("verification")
        != (_proof(evidence) if payload.get("decision") == "PASS" else None)
        or payload.get("accepted_run_version") != run["version"]
    ):
        raise DomainError("VERSION_CONFLICT", "Independent evaluation record changed")
    try:
        request = ReviewInput.model_validate(payload.get("request")).model_dump()
    except ValidationError as exc:
        raise DomainError("VERSION_CONFLICT", "Stored review request is invalid") from exc
    # JSON fingerprints distinguish bool/int and disallow noncanonical nested fields.
    expected = {
        "namespace": VERSION,
        "request": {
            "contract_id": row["contract_id"],
            "request_key": row["request_key"],
            "expected_result_fingerprint": job["result_fingerprint"],
            "expected_fence": run["fence"],
            "expected_version": job["result_snapshot"]["completed_run_version"],
        },
        "decision": payload["decision"],
        "reason": {
            "PASS": "Frozen synthetic semantic assertions and provenance match",
            "FAIL": "Output fails the independently registered exact semantic assertions",
            "UNKNOWN": "Input does not match this frozen synthetic contract",
        }.get(payload["decision"]),
        "contract_hash": contract_hash,
        "contract_version": contract["version"],
        "checker": contract["checker"],
        "reviewer": contract["reviewer"],
        "review_basis": contract["review_basis"],
        "evaluator": run["principal_id"],
        "gold_sha256": contract["gold_sha256"],
        "rubric_sha256": contract["rubric_sha256"],
        "result_fingerprint": job["result_fingerprint"],
        "completed_fence": run["fence"],
        "completed_run_version": job["result_snapshot"]["completed_run_version"],
        "accepted_run_version": run["version"],
        "verification": _proof(evidence) if payload["decision"] == "PASS" else None,
    }
    seal = {
        "review_id": row["id"],
        "decision": payload["decision"],
        "contract_id": row["contract_id"],
        "review_fingerprint": row["fingerprint"],
    }
    seals = (
        c.execute(
            select(events.c.data).where(
                events.c.run_id == run["id"], events.c.kind == "PROTOCOL_REVIEW"
            )
        )
        .scalars()
        .all()
    )
    matching = [
        value for value in seals if isinstance(value, dict) and value.get("review_id") == row["id"]
    ]
    if (
        fingerprint(payload) != fingerprint(expected)
        or len(matching) != 1
        or fingerprint(matching[0]) != fingerprint(seal)
    ):
        raise DomainError("VERSION_CONFLICT", "Independent review seal or canonical record changed")
    if (
        not isinstance(request, dict)
        or request.get("contract_id") != row["contract_id"]
        or request.get("request_key") != row["request_key"]
        or request.get("expected_result_fingerprint") != job["result_fingerprint"]
        or request.get("expected_fence") != run["fence"]
        or request.get("expected_version") != job["result_snapshot"]["completed_run_version"]
        or row["contract_id"] != job["accepted_snapshot"]["contract"]["contract_id"]
    ):
        raise DomainError("VERSION_CONFLICT", "Accepted review request changed")


def review(store, user, rid, body):
    body = ReviewInput.model_validate(body).model_dump()
    contract, contract_hash = evaluation_contract(body["contract_id"])
    with store.tx() as c:
        location = c.execute(select(runs.c.project_id).where(runs.c.id == rid)).scalar()
        store.lock_project(c, user, location)
        # Run lock serializes review against control/worker and duplicate requests.
        c.execute(select(runs.c.id).where(runs.c.id == rid).with_for_update()).first()
        job, run, evidence, hashes = _pending(store, c, user, rid)
        if body["contract_id"] != job["accepted_snapshot"]["contract"]["contract_id"]:
            raise DomainError(
                "VERSION_CONFLICT", "Evaluation contract cannot be selected after execution"
            )
        old = (
            c.execute(
                select(protocol_reviews).where(
                    protocol_reviews.c.run_id == rid,
                    protocol_reviews.c.request_key == body["request_key"],
                )
            )
            .mappings()
            .first()
        )
        if old:
            if old["contract_id"] != body["contract_id"] or old["payload"].get("request") != body:
                raise DomainError("VERSION_CONFLICT", "Review key already bound to another request")
            _validated_review(c, old, contract, contract_hash, job, run, evidence)
            decision, _ = _oracle(contract, evidence, hashes)
            if decision != old["payload"]["decision"]:
                raise DomainError("VERSION_CONFLICT")
            return _public(old)
        result = job["result_snapshot"]
        if run["status"] != "WAITING_APPROVAL" or run["error"] is not None or run["cancel_intent"]:
            raise DomainError(
                "VERIFICATION_FAILED", "Only new pending protocol runs may be reviewed"
            )
        if (
            body["expected_result_fingerprint"] != job["result_fingerprint"]
            or body["expected_fence"] != run["fence"]
            or body["expected_version"] != run["version"]
            or result["completed_run_version"] != run["version"]
        ):
            raise DomainError("VERSION_CONFLICT", "Review request is stale")
        decision, reason = _oracle(contract, evidence, hashes)
        accepted_version = run["version"] + (decision == "PASS")
        if decision == "PASS":
            changed = c.execute(
                update(runs)
                .where(
                    runs.c.id == rid,
                    runs.c.status == "WAITING_APPROVAL",
                    runs.c.fence == body["expected_fence"],
                    runs.c.version == body["expected_version"],
                    runs.c.cancel_intent.is_(False),
                )
                .values(status="SUCCEEDED", version=accepted_version, lease_until=0)
            )
            if changed.rowcount != 1:
                raise DomainError("VERSION_CONFLICT")
        payload = {
            "namespace": VERSION,
            "request": body,
            "decision": decision,
            "reason": reason,
            "contract_hash": contract_hash,
            "contract_version": contract["version"],
            "checker": contract["checker"],
            "reviewer": contract["reviewer"],
            "review_basis": contract["review_basis"],
            "evaluator": user,
            "gold_sha256": contract["gold_sha256"],
            "rubric_sha256": contract["rubric_sha256"],
            "result_fingerprint": job["result_fingerprint"],
            "completed_fence": run["fence"],
            "completed_run_version": result["completed_run_version"],
            "accepted_run_version": accepted_version,
            "verification": _proof(evidence) if decision == "PASS" else None,
        }
        row = {
            "id": new_id("review"),
            "run_id": rid,
            "principal_id": user,
            "project_id": run["project_id"],
            "contract_id": body["contract_id"],
            "payload": payload,
            "fingerprint": fingerprint(payload),
            "request_key": body["request_key"],
            "created_at": time.time(),
        }
        c.execute(insert(protocol_reviews).values(**row))
        store.event(
            c,
            rid,
            "PROTOCOL_REVIEW",
            {
                "review_id": row["id"],
                "decision": decision,
                "contract_id": body["contract_id"],
                "review_fingerprint": row["fingerprint"],
            },
        )
        return _public(row)


def review_proof(store, c, user, rid):
    """Read current independent PASS for source/cold; technical status is not proof."""
    job, run, evidence, hashes = _pending(store, c, user, rid)
    if (
        job["kind"] not in {"source", "cold"}
        or run["status"] != "SUCCEEDED"
        or run["error"] is not None
        or run["cancel_intent"]
    ):
        raise DomainError("VERIFICATION_FAILED", "Reviewed successful protocol source required")
    records = (
        c.execute(select(protocol_reviews).where(protocol_reviews.c.run_id == rid)).mappings().all()
    )
    passed = [
        r
        for r in records
        if isinstance(r["payload"], dict) and r["payload"].get("decision") == "PASS"
    ]
    if len(passed) != 1:
        raise DomainError(
            "VERIFICATION_FAILED", "Unique independent persisted semantic PASS required"
        )
    row = passed[0]
    contract, contract_hash = evaluation_contract(row["contract_id"])
    _validated_review(c, row, contract, contract_hash, job, run, evidence)
    decision, _ = _oracle(contract, evidence, hashes)
    if decision != "PASS":
        raise DomainError("VERIFICATION_FAILED")
    return copy.deepcopy(row["payload"]["verification"])


def source_proof(store, c, user, rid, limits=None):
    """Only a reviewed successful source can authorize candidate extraction."""
    job, _, _, _ = _pending(store, c, user, rid)
    if job["kind"] != "source":
        raise DomainError("VERIFICATION_FAILED", "Only source jobs authorize extraction")
    return review_proof(store, c, user, rid)


def mount(app, store, identity):
    """Closed owner command; assets/checkers/decisions are never caller arguments."""
    user_dependency = Depends(identity)

    @app.post("/api/internal/protocol/runs/{rid}/reviews", status_code=201)
    def submit_review(rid: str, body: ReviewInput, user=user_dependency):
        return review(store, user, rid, body.model_dump())
