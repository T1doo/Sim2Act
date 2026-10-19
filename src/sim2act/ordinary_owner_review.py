"""Prospectively frozen ordinary Goal rubric and explicit owner declarations.

The shared owner protocol is adapted to a Run, never to an internal instance.
This ledger is the sole declaration state; Run.result and automatic verdicts stay intact.
"""

import time
from typing import Annotated, Literal

from fastapi import Depends
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy import select

from . import lifecycle
from . import owner_acceptance as owner
from .contracts import OrdinaryHumanReview
from .db import (
    attempts,
    fingerprint,
    goal_cards,
    internal_run_bindings,
    operations,
    ordinary_owner_records,
    ordinary_owner_seals,
    resources,
    runs,
)
from .errors import DomainError
from .goals import GoalCardInput
from .tools import reconcile_readback

VERSION: Literal["owner.ordinary-goal.v1"] = "owner.ordinary-goal.v1"
MD_VERSION = "owner.ordinary-goal-md.v2"
POLICY = OrdinaryHumanReview(version=VERSION, declarant="current-project-and-run-owner",
    automatic_goal_acceptance="NOT_RUN").model_dump()
MD_POLICY = {**POLICY, "version": MD_VERSION}


def require(condition, message="Exact prospective ordinary Goal review required"):
    if not condition:
        raise DomainError("VERSION_CONFLICT", message)


def items(content):
    result = [dict(id="goal", text=content["goal"])]
    for field in ("known", "assumptions", "unresolved", "constraints", "acceptance_checks"):
        result.extend(dict(id=f"{field}.{n}", text=text) for n, text in enumerate(content[field], 1))
    return result


def require_prospective(source, policy):
    require(source is not None and policy["human_review"] in (POLICY, MD_POLICY)
        and not any(policy.get(k) is not None for k in
                    ("natural_planning", "application_generation", "ordinary_csv_report")))
    from .ordinary_artifacts import delivery_policy

    require((policy["human_review"] == MD_POLICY) == (policy.get("artifact_delivery") is not None))
    if policy.get("artifact_delivery") is not None:
        require(policy["artifact_delivery"] == delivery_policy(), "MD policy or tool version changed")
    content = GoalCardInput.model_validate(source.snapshot["content"]).model_dump()
    if not content["acceptance_checks"] or any(not text.strip() for text in content["acceptance_checks"]):
        raise DomainError("INVALID_INPUT", "Save explicit nonblank acceptance checks before starting")
    if not content["resource_refs"]:
        raise DomainError("INVALID_INPUT", "Select authorized source material before starting")


def scope(store, c, user, rid, *, _lock_project=True):
    # Metadata only; do not read Run/contract/owner payload before current human ownership.
    header = c.execute(select(runs.c.project_id, runs.c.runtime_id)
        .where(runs.c.id == rid, runs.c.principal_id == user)).mappings().first()
    if not header or not user.startswith("user_"):
        raise DomainError("PERMISSION_DENIED")
    project = (store.lock_project if _lock_project else store.own_project)(c, user, header["project_id"])
    if project["runtime_id"] != header["runtime_id"]:
        raise DomainError("PERMISSION_DENIED")
    from .db import run_contracts

    frozen = c.execute(select(
        run_contracts.c.snapshot["human_review"]["version"].as_string().label("version"),
        run_contracts.c.snapshot["goal"]["owner_id"].as_string().label("owner"))
        .where(run_contracts.c.run_id == rid)).mappings().first()
    require(frozen is not None and frozen["version"] in (VERSION, MD_VERSION) and frozen["owner"] == user,
        "This Run did not freeze a prospective human rubric")
    require(not c.execute(select(internal_run_bindings.c.run_id)
        .where(internal_run_bindings.c.run_id == rid)).first(), "Internal Run is a different review scope")
    return header["project_id"]


def context(store, c, user, rid, *, _lock_project=True):
    pid = scope(store, c, user, rid, _lock_project=_lock_project)
    # Existing authorization barrier checks current principal + runtime Grants before bodies.
    from .goal_applications import source_scope_gate

    source_scope_gate(store, c, rid)
    run = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
    store.authorize_receipts(c, run)
    contract = store.frozen_contract(c, run)
    require(contract.human_review is not None)
    require_prospective(contract.source_goal_card, contract.model_dump(exclude_none=True))
    source = contract.source_goal_card.model_dump()
    head = c.execute(select(goal_cards.c.version, goal_cards.c.fingerprint)
        .where(goal_cards.c.id == source["card_id"], goal_cards.c.project_id == pid)).mappings().first()
    require(head is not None and head["version"] == source["version"] and head["fingerprint"] == source["fingerprint"],
        "Saved Goal version changed")
    require(run["status"] == "PARTIAL" and run["error"] is None and not run["cancel_intent"]
        and isinstance(run["result"], dict) and run["result"].get("goal_acceptance") == "NOT_RUN",
        "Only this completed ordinary result can receive a human declaration")
    require(all(status == "RECEIVED" for status in c.execute(select(attempts.c.status)
        .where(attempts.c.run_id == rid)).scalars()), "Unresolved model attempt")
    actual = [dict(r) for r in c.execute(select(operations).where(operations.c.run_id == rid)
        .order_by(operations.c.id)).mappings()]
    require(bool(actual) and len(actual) <= contract.limits.max_tools)
    for operation in actual:
        require(operation["status"] == "VERIFIED" and operation["tool_ref"] in
            ({"resource.read", "data.aggregate_csv", "artifact.save_text"} if contract.artifact_delivery else
             {"resource.read", "data.aggregate_csv"}), "Unverified or unsupported ordinary effect")
        status, receipt = reconcile_readback(store, c, run, operation)
        require(status == "VERIFIED" and receipt == operation["receipt"], "Actual tool readback changed")
    require(sorted(map(fingerprint, run["result"].get("receipts", []))) ==
        sorted(fingerprint(op["receipt"]) for op in actual), "Result differs from exact Run receipts")
    materials = [dict(r) for r in c.execute(select(resources).where(resources.c.id.in_(run["resource_refs"]))
        .order_by(resources.c.id)).mappings()]
    artifact_details = {}
    if contract.artifact_delivery is not None:
        from .ordinary_artifacts import projection

        artifact_details["artifacts"] = projection(store, c, run, contract)["artifacts"]
    content = GoalCardInput.model_validate(source["snapshot"]["content"]).model_dump()
    return dict(version=contract.human_review.version, principal_id=user, project_id=pid, runtime_id=run["runtime_id"],
        run_id=rid, result_version=run["version"], run_input_fingerprint=run["fingerprint"],
        contract_fingerprint=fingerprint(contract.model_dump(exclude_none=True)),
        source_goal=source, goal=content, items=items(content) + ([dict(id="artifact.md", text=contract.artifact_delivery.acceptance_check)] if contract.artifact_delivery else []), materials=materials,
        **({"human_correction": contract.ordinary_correction.model_dump()} if contract.ordinary_correction else {}),
        **artifact_details,
        output=run["result"], output_fingerprint=fingerprint(run["result"]), actual_operations=actual,
        grant_version=lifecycle.grant_version(c, pid, user), automatic_goal_acceptance="NOT_RUN",
        technical_semantic_status="UNKNOWN", formal_publication_enabled=False)


def ledger(c, user, rid):
    return owner.run_ledger(c, user, rid, ordinary_owner_records, ordinary_owner_seals, {})


def payload(c, row):
    return owner.run_payload(c, row, ordinary_owner_records)


def append(c, user, pid, rid, rows, body, status, **details):
    return owner.run_append(c, user, pid, rid, rows, body, status,
        records=ordinary_owner_records, seals=ordinary_owner_seals, scope_metadata={}, **details)


def final_gate(store, c, user, rid, fresh, *, expires_at=None):
    # Independently repeat current permissions, exact source/result/proofs before commit.
    require(fingerprint(context(store, c, user, rid)) == fingerprint(fresh), "Review changed before commit")
    require(expires_at is None or time.time() < expires_at, "Review expired before commit")


def submit(store, user, rid, body):
    return owner.scoped_run_submit(store, user, rid, body, dict(
        namespace="ordinary-owner-submission-rejection.v1",
        scope=lambda c: scope(store, c, user, rid),
        ledger=lambda c: ledger(c, user, rid), payload=payload,
        context=lambda c: context(store, c, user, rid),
        append=lambda c, pid, rows, body, status, **kw: append(c, user, pid, rid, rows, body, status, **kw),
        final_gate=lambda c, fresh, **kw: final_gate(store, c, user, rid, fresh, **kw)))


def read(store, user, rid, key=None):
    with store.tx() as c:
        pid = scope(store, c, user, rid)
        rows = ledger(c, user, rid)
        last = rows[-1] if rows else None
        from .db import run_contracts

        version = c.execute(select(run_contracts.c.snapshot["human_review"]["version"].as_string())
            .where(run_contracts.c.run_id == rid)).scalar_one()
        out = dict(version=version, principal_id=user, project_id=pid, run_id=rid,
            sequence=len(rows), history=rows, latest=last, owner_acceptance=last["status"] if last else "PENDING",
            content_access=False, automatic_goal_acceptance="NOT_RUN", technical_semantic_status="UNKNOWN",
            formal_publication_enabled=False)
        recovered = next((r for r in rows if r["request_key"] == key), None) if key else None
        if key and not recovered:
            raise DomainError("OUTCOME_UNKNOWN", "Original declaration key not found")
        try:
            fresh = context(store, c, user, rid)
            values = {r["id"]: payload(c, r) for r in rows}
            if last and last["kind"] in {"PREPARE", "DECIDE"}:
                value = values[last["id"]]
                require(fingerprint(fresh) == fingerprint(value["contract"]), "Exact review context changed")
                out["record"] = dict(last, payload=value)
                if last["kind"] == "PREPARE" and time.time() >= value["expires_at"]:
                    out["owner_acceptance"] = "EXPIRED"
            out.update(content_access=True, current=fresh)
            if recovered and fingerprint(values[recovered["id"]].get("contract", fresh)) == fingerprint(fresh):
                recovered = dict(recovered, payload=values[recovered["id"]])
        except DomainError as error:
            out.pop("record", None)
            out["invalidation_reason"] = error.code
            if last and last["kind"] not in {"CANCEL", "REVOKE"}:
                out["owner_acceptance"] = "STALE"
        if recovered:
            out["recovered"] = recovered
        return out


def mount(app, store, limits, identity):
    user_dependency = Depends(identity)

    @app.get("/api/runs/{rid}/owner-review")
    def state(rid: str, request_key: str | None = None, user=user_dependency):
        try:
            return read(store, user, rid, request_key)
        except DomainError as error:
            if error.code != "OUTCOME_UNKNOWN":
                raise
            return JSONResponse({"error": error.public()}, status_code=409)

    @app.post("/api/runs/{rid}/owner-review-requests", status_code=201)
    def command(rid: str,
        body: Annotated[owner.NaturalPrepare | owner.Decide | owner.Stop, Field(discriminator="command")],
        user=user_dependency):
        return dict(formal_publication_enabled=False, record=submit(store, user, rid, body.model_dump()))
