"""Provisional CSV candidate from one checked offline receipt, never Run success."""

import copy
import time

from pydantic import ValidationError
from sqlalchemy import insert, select

from .apps import csv_candidate, load_draft
from .db import app_drafts, fingerprint, operations, runs, task_extractions
from .errors import DomainError
from .extraction import exact_sum_oracle
from .goal_planner import verify_result
from .natural_activations import validate_run
from .registered_run_extraction import RegisteredExtractionInput, _candidate, _target
from .tools import authorized_read

KIND = "natural_csv_receipt_candidate.v1"
PROOF = "verified_natural_csv_receipt_only.v1"
GENERATOR = "TRUSTED_OFFLINE_RECEIPT_CANDIDATE.v1"


def source(store, c, user, rid, limits):
    row = c.execute(select(runs).where(runs.c.id == rid)).mappings().first()
    if not row or row["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    store.own_project(c, user, row["project_id"])
    if (
        row["status"] not in {"PARTIAL", "SUCCEEDED"}
        or row["error"] is not None
        or row["cancel_intent"]
    ):
        raise DomainError("VERIFICATION_FAILED", "Only intact terminal partial receipt candidate")
    contract = store.frozen_contract(c, row)
    if (
        not contract.natural_planning
        or not contract.natural_planning.activation
        or contract.mode != "mock"
    ):
        raise DomainError("UNSUPPORTED_CAPABILITY", "Approved offline fixed sum receipt only")
    whole = contract.natural_planning.goal_acceptance is not None
    if (row["status"] == "SUCCEEDED") != whole:
        raise DomainError("VERIFICATION_FAILED", "PARTIAL cannot become whole-task source")
    session = validate_run(store, c, row)
    goals = [
        g for g in session["scope"]["goals"] if g["card_id"] == contract.source_goal_card.card_id
    ]
    if (
        session["status"] != "APPROVED"
        or session["scope"]["mode"] != "OFFLINE_TEST"
        or len(goals) != 1
        or goals[0]["kind"] != "sum_quantity_z"
    ):
        raise DomainError("UNSUPPORTED_CAPABILITY", "Fixed sum scope was revoked or unsupported")
    verify_result(store, c, row, row["result"])
    result = row["result"]
    steps = result["planning"]["plan"]["steps"]
    resource = goals[0]["resource_id"]
    if (
        len(steps) != 1
        or steps[0]["tool_ref"] != "data.aggregate_csv"
        or steps[0]["column"] != "quantity_z"
        or steps[0]["resource_id"] != resource
        or steps[0]["depends_on"]
        or len(result["receipts"]) != 1
    ):
        raise DomainError("UNSUPPORTED_CAPABILITY", "Exact single aggregate receipt required")
    material = authorized_read(
        store,
        c,
        user,
        row["runtime_id"],
        row["project_id"],
        "resource.read",
        {"resource_id": resource},
    )
    receipt = result["receipts"][0]
    # verify_result checks exact operation/intent/receipt against current readback;
    # the independent parser proves sum separately from the registered tool.
    exact_sum_oracle(material["content"], "quantity_z", receipt["data"])
    authorized_read(
        store,
        c,
        user,
        row["runtime_id"],
        row["project_id"],
        "data.aggregate_csv",
        {"resource_id": resource, "column": "quantity_z"},
    )
    op = (
        c.execute(select(operations).where(operations.c.id == receipt["operation_id"]))
        .mappings()
        .one()
    )
    candidate = csv_candidate(resource, material["hash"], "", contract.limits)
    candidate["goal"] = copy.deepcopy(contract.source_goal_card.snapshot["content"])
    candidate["manifest"]["goal_ref"] = contract.source_goal_card.card_id
    draft = {"project_id": row["project_id"], "candidate": candidate}
    proof = {
        "kind": "accepted_fixed_natural_goal.v1" if whole else PROOF,
        "source_run_id": rid,
        "source_run_status": row["status"],
        "whole_task_accepted": whole,
        **({"task_acceptance": copy.deepcopy(result["task_acceptance"])} if whole else {}),
        "semantic_goal_acceptance": "NOT_RUN",
        "owner_acceptance": "PENDING",
        "model_requests": 0,
        "generator": GENERATOR,
        "source_run_version": row["version"],
        "run_fingerprint": row["fingerprint"],
        "contract_fingerprint": fingerprint(contract.model_dump(exclude_none=True)),
        "plan_fingerprint": result["planning"]["fingerprint"],
        "result_fingerprint": fingerprint(result),
        "receipt_fingerprint": fingerprint(receipt),
        "operation_fingerprint": fingerprint(dict(op)),
        "goal_version": contract.source_goal_card.version,
        "goal_fingerprint": contract.source_goal_card.fingerprint,
        "activation": contract.natural_planning.activation.model_dump(),
        "source_resource_id": resource,
        "source_hash": material["hash"],
        "parameter_scope": {
            "creation": ["new_csv_binding_in_existing_authorization_domain"],
            "runtime": ["column"],
            "applicability": "OWNER_REVIEW_REQUIRED",
        },
        "stable_logic": {
            "tool_ref": "data.aggregate_csv",
            "tool_version": "1",
            "effect": "read",
            "operation": "sum numeric column",
            "input": "CSV + column",
            "output": ["resource_id", "column", "count", "sum", "source_hash"],
            "source_check": "csv.exact_integer_sum.v1",
            "schema_version": "1.0-draft",
            "model_judgment": "NONE_IN_THIS_CANDIDATE",
        },
    }
    return draft, proof


def candidate(source_draft, proof, target, aid=None, action_id=None):
    value = _candidate(source_draft, proof, target, aid, action_id)
    value["task_proof"]["generator"] = GENERATOR
    return value


def envelope(**values):
    return {
        "state": "CANDIDATE_ONLY",
        "publishable": False,
        "formal_publication_enabled": False,
        "whole_task_accepted": False,
        "source_run_status": "PARTIAL",
        "semantic_goal_acceptance": "NOT_RUN",
        "owner_acceptance": "PENDING",
        "generator": GENERATOR,
        "model_requests": 0,
        **values,
    }


def options(store, user, rid, limits):
    with store.tx() as c:
        origin, proof = source(store, c, user, rid, limits)
        targets = []
        for aid in c.execute(
            select(app_drafts.c.id).where(app_drafts.c.project_id == origin["project_id"])
        ).scalars():
            try:
                target, name = _target(store, c, user, origin, aid, limits)
                targets.append({"id": aid, "name": name, **target})
            except DomainError:
                continue
        if not targets:
            raise DomainError("NEEDS_INPUT", "Existing authorized different CSV app required")
        return envelope(
            proof=proof,
            source_proof_fingerprint=fingerprint(proof),
            targets=targets,
            whole_task_accepted=proof["whole_task_accepted"],
            source_run_status=proof["source_run_status"],
        )


def request(rid, body):
    return {"source_run_id": rid, **body}


def extract(store, user, rid, body, limits):
    with store.tx() as c:
        pid = c.execute(select(runs.c.project_id).where(runs.c.id == rid)).scalar()
        store.lock_project(c, user, pid)
        origin, proof = source(store, c, user, rid, limits)
        target, _ = _target(store, c, user, origin, body["target_app_id"], limits)
        if (
            fingerprint(proof) != body["expected_proof_fingerprint"]
            or target["fingerprint"] != body["expected_target_draft_fingerprint"]
        ):
            raise DomainError("VERSION_CONFLICT")
        req = request(rid, {k: v for k, v in body.items() if k != "request_key"})
        fp = fingerprint(req)
        old = (
            c.execute(
                select(task_extractions).where(
                    task_extractions.c.task_id == rid,
                    task_extractions.c.principal_id == user,
                    task_extractions.c.request_key == body["request_key"],
                )
            )
            .mappings()
            .first()
        )
        if old:
            if old["request_fingerprint"] != fp:
                raise DomainError("VERSION_CONFLICT")
            draft, _, _, _ = load_draft(store, c, user, old["app_id"], limits)
        else:
            value = candidate(origin, proof, target)
            from .apps import compile_preview

            compile_preview(value, limits)
            draft = {
                "id": value["manifest"]["app_id"],
                "project_id": pid,
                "runtime_id": target["runtime_id"],
                "name": body["name"],
                "candidate": value,
                "fingerprint": fingerprint(value),
                "created_at": time.time(),
            }
            c.execute(insert(app_drafts).values(**draft))
            c.execute(
                insert(task_extractions).values(
                    task_id=rid,
                    principal_id=user,
                    request_key=body["request_key"],
                    request_fingerprint=fp,
                    app_id=draft["id"],
                    snapshot={
                        "kind": KIND,
                        "proof": proof,
                        "target": target,
                        "request": req,
                        "candidate_fingerprint": draft["fingerprint"],
                    },
                )
            )
        return envelope(
            id=draft["id"],
            candidate_fingerprint=draft["fingerprint"],
            cached=bool(old),
            whole_task_accepted=proof["whole_task_accepted"],
            source_run_status=proof["source_run_status"],
            source_proof_fingerprint=fingerprint(proof),
        )


def validate_candidate(store, c, user, draft, limits):
    saved = (
        c.execute(select(task_extractions).where(task_extractions.c.app_id == draft["id"]))
        .mappings()
        .first()
    )
    snap = saved["snapshot"] if saved else None
    if (
        not saved
        or saved["principal_id"] != user
        or not isinstance(snap, dict)
        or set(snap) != {"kind", "proof", "target", "request", "candidate_fingerprint"}
        or snap["kind"] != KIND
        or not isinstance(snap["request"], dict)
    ):
        raise DomainError("VERSION_CONFLICT")
    req = snap["request"]
    if (
        set(req)
        != {
            "source_run_id",
            "expected_proof_fingerprint",
            "target_app_id",
            "expected_target_draft_fingerprint",
            "name",
        }
        or req["source_run_id"] != saved["task_id"]
        or fingerprint(req) != saved["request_fingerprint"]
        or ("name" in draft and draft["name"] != req["name"])
    ):
        raise DomainError("VERSION_CONFLICT")
    try:
        parsed = RegisteredExtractionInput.model_validate(
            {
                **{k: v for k, v in req.items() if k != "source_run_id"},
                "request_key": saved["request_key"],
            }
        ).model_dump()
    except ValidationError as exc:
        raise DomainError("VERSION_CONFLICT", "Stored request shape changed") from exc
    if fingerprint(
        request(saved["task_id"], {k: v for k, v in parsed.items() if k != "request_key"})
    ) != fingerprint(req):
        raise DomainError("VERSION_CONFLICT")
    origin, proof = source(store, c, user, saved["task_id"], limits)
    target, _ = _target(store, c, user, origin, req["target_app_id"], limits)
    if (
        fingerprint(proof) != fingerprint(snap["proof"])
        or fingerprint(proof) != req["expected_proof_fingerprint"]
        or fingerprint(target) != fingerprint(snap["target"])
        or target["fingerprint"] != req["expected_target_draft_fingerprint"]
        or origin["project_id"] != draft["project_id"]
        or target["runtime_id"] != draft["runtime_id"]
        or snap["candidate_fingerprint"] != draft["fingerprint"]
    ):
        raise DomainError("VERSION_CONFLICT")
    expected = candidate(
        origin, proof, target, draft["id"], draft["candidate"]["actions"][0]["action_id"]
    )
    if fingerprint(expected) != fingerprint(draft["candidate"]):
        raise DomainError("VERSION_CONFLICT", "Candidate differs from checked receipt derivation")
