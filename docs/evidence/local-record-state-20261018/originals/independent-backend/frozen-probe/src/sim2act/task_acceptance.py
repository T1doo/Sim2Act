"""Prospective finite offline goal checks; never owner/general semantic acceptance."""

import csv
import hashlib
import io

from .contracts import FixedGoalAcceptance
from .db import fingerprint
from .errors import DomainError
from .extraction import exact_sum_oracle
from .natural_activations import validate_run
from .tools import authorized_read


def definition(goal):
    return FixedGoalAcceptance(
        version="fixed-csv-goal-acceptance.v1",
        kind=goal["kind"],
        resource_id=goal["resource_id"],
        source_hash=goal["resource_hash"],
        goal_fingerprint=goal["expected_fingerprint"],
        check="csv.complete_preview.v1"
        if goal["kind"] == "read_preview"
        else "csv.exact_integer_sum.v1",
    )


def evaluate(store, c, run, contract, binding, receipts):
    spec = contract.natural_planning.goal_acceptance if contract.natural_planning else None
    if spec is None:
        return None
    if (
        contract.mode != "mock"
        or not contract.natural_planning.activation
        or run["cancel_intent"]
        or run["error"] is not None
    ):
        raise DomainError("VERIFICATION_FAILED", "Fixed acceptance requires intact offline goal")
    session = validate_run(store, c, run)
    goal = next(
        g for g in session["scope"]["goals"] if g["card_id"] == contract.source_goal_card.card_id
    )
    if (
        session["scope"]["mode"] != "OFFLINE_TEST"
        or session["status"] != "APPROVED"
        or fingerprint(spec.model_dump()) != fingerprint(definition(goal).model_dump())
    ):
        raise DomainError("VERIFICATION_FAILED", "Prospective finite goal scope changed")
    # Existing verified_plan/verify_confirmation already check exact single plan,
    # all original intents/actual VERIFIED receipts and original acceptance seals.
    expected_tool = "resource.read" if spec.kind == "read_preview" else "data.aggregate_csv"
    steps = binding["plan"]["steps"]
    if (
        len(steps) != 1
        or len(receipts) != 1
        or steps[0]["tool_ref"] != expected_tool
        or steps[0]["resource_id"] != spec.resource_id
        or steps[0]["depends_on"]
        or receipts[0]["status"] != "VERIFIED"
    ):
        raise DomainError("VERIFICATION_FAILED", "Every declared goal step must be verified")
    material = authorized_read(
        store,
        c,
        run["principal_id"],
        run["runtime_id"],
        run["project_id"],
        "resource.read",
        {"resource_id": spec.resource_id},
    )
    if (
        material["format"] != "csv"
        or hashlib.sha256(material["content"].encode()).hexdigest() != spec.source_hash
    ):
        raise DomainError("VERSION_CONFLICT", "Acceptance source changed")
    if spec.kind == "sum_quantity_z":
        if steps[0].get("column") != "quantity_z":
            raise DomainError("VERIFICATION_FAILED")
        exact_sum_oracle(material["content"], "quantity_z", receipts[0]["data"])
    else:
        rows = list(csv.reader(io.StringIO(material["content"])))
        if (
            len(rows) != 3
            or rows[0] != ["item", "quantity_z"]
            or fingerprint(receipts[0]["data"]) != fingerprint(material)
        ):
            raise DomainError("VERIFICATION_FAILED", "Complete bound preview required")
    return {
        "version": spec.version,
        "contract_fingerprint": fingerprint(spec.model_dump()),
        "objective": spec.kind,
        "status": "PASS",
        "whole_task_accepted": True,
        "scope": "EXACT_FIXED_SYNTHETIC_GOAL_ONLY",
        "single_step_status": "VERIFIED",
        "check": spec.check,
        "source_hash": spec.source_hash,
        "receipt_fingerprint": fingerprint(receipts[0]),
        "general_semantic_acceptance": "NOT_RUN",
        "owner_acceptance": "PENDING",
        "formal_publication_enabled": False,
    }
