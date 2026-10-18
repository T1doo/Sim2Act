"""Explicit sum-only application from a complete ordinary CSV report contract.

Historical report verification is provenance, never the new application's promise.
No new executor, runtime, Grant or internal source binding is created.
"""

import copy
import time
from typing import Literal

from fastapi import Depends
from pydantic import ValidationError
from sqlalchemy import insert, select

from .contracts import Limits
from .db import (
    app_drafts,
    fingerprint,
    local_effects,
    operation_intents,
    operations,
    run_contracts,
    runs,
    task_extractions,
)
from .errors import DomainError
from .registered_run_extraction import RegisteredExtractionInput, _candidate, _target

KIND = "ordinary_csv_sum_source.v1"
PROOF = "completed_ordinary_csv_report_sum_source.v1"
GENERATOR = "TRUSTED_ORDINARY_CSV_SUM.v1"
CONSENT = "EXTRACT_SUM_ONLY_WITHOUT_MD_REPORT"


class ExtractionInput(RegisteredExtractionInput):
    consent: Literal["EXTRACT_SUM_ONLY_WITHOUT_MD_REPORT"]


def require(value, message="Ordinary CSV sum extraction provenance changed"):
    if not value:
        raise DomainError("VERSION_CONFLICT", message)


def source_scope(store, c, user, rid):
    """Authorize identifier projections before Run, contract or receipt bodies."""
    header = c.execute(select(
        runs.c.id, runs.c.principal_id, runs.c.project_id, runs.c.runtime_id,
        runs.c.resource_refs, runs.c.status,
    ).where(runs.c.id == rid, runs.c.principal_id == user)).mappings().first()
    if header is None:
        raise DomainError("PERMISSION_DENIED")
    store.own_project(c, user, header["project_id"])
    if header["status"] != "SUCCEEDED":
        raise DomainError("VERIFICATION_FAILED", "Successful complete CSV report required")
    frozen = c.execute(select(
        run_contracts.c.snapshot["ordinary_csv_report"]["resource_id"].as_string().label("resource"),
        run_contracts.c.snapshot["goal"]["resource_refs"].label("refs"),
        run_contracts.c.snapshot["resources"][0]["resource_id"].as_string().label("material"),
    ).where(run_contracts.c.run_id == rid)).mappings().first()
    require(frozen is not None and isinstance(frozen["resource"], str))
    refs = header["resource_refs"]
    require(isinstance(refs, list) and isinstance(frozen["refs"], list))
    intents = c.execute(select(operation_intents.c.request["args"]["resource_id"].as_string())
        .join(operations, operations.c.id == operation_intents.c.operation_id)
        .where(operations.c.run_id == rid,
            operations.c.tool_ref.in_(["resource.read", "data.aggregate_csv"]))).scalars().all()
    ids = refs + frozen["refs"] + [frozen["resource"], frozen["material"]] + intents
    require(all(isinstance(value, str) for value in ids))
    for resource in set(ids):
        for tool in ("resource.read", "data.aggregate_csv"):
            store.authorize(c, user, header["runtime_id"], header["project_id"], resource, tool)
    require(refs == frozen["refs"] == [frozen["resource"]]
        and frozen["material"] == frozen["resource"] and intents == [frozen["resource"]] * 2)
    effects = c.execute(select(local_effects.c.resource_id)
        .join(operations, operations.c.id == local_effects.c.operation_id)
        .where(operations.c.run_id == rid, operations.c.tool_ref == "artifact.save_text"))
    effects = effects.scalars().all()
    receipt_refs = c.execute(select(operations.c.receipt["artifact_refs"])
        .where(operations.c.run_id == rid, operations.c.tool_ref == "artifact.save_text")).scalars().all()
    for resource in effects:
        store.authorize(c, user, header["runtime_id"], header["project_id"], resource, "resource.read")
    require(len(effects) == 1 and receipt_refs == [effects])
    return dict(header)


def target_scope(store, c, user, aid):
    row = c.execute(select(
        app_drafts.c.project_id, app_drafts.c.runtime_id,
        app_drafts.c.candidate["manifest"]["data_bindings"][0]["resource_ref"].as_string().label("resource"),
    ).where(app_drafts.c.id == aid)).mappings().first()
    if row is None:
        raise DomainError("PERMISSION_DENIED")
    project = store.own_project(c, user, row["project_id"])
    require(isinstance(row["resource"], str))
    from .apps import authorize_source

    authorize_source(store, c, user, project, row["resource"], row["runtime_id"])


def app_scope(store, c, user, aid):
    """Independent origin row plus scalar hints prevent source-family downgrade."""
    marker = c.execute(select(
        task_extractions.c.task_id, task_extractions.c.principal_id,
        task_extractions.c.snapshot["kind"].as_string().label("kind"),
        task_extractions.c.snapshot["proof"]["source_run_id"].as_string().label("source"),
    ).where(task_extractions.c.app_id == aid)).mappings().first()
    hints = c.execute(select(
        app_drafts.c.candidate["task_proof"]["proof"]["kind"].as_string().label("kind"),
        app_drafts.c.candidate["task_proof"]["proof"]["source_run_id"].as_string().label("source"),
        app_drafts.c.candidate["manifest"]["source_run_ref"].as_string().label("run"),
    ).where(app_drafts.c.id == aid)).mappings().first()
    if not (marker and marker["kind"] == KIND or hints and hints["kind"] == PROOF):
        return
    require(marker is not None and hints is not None and marker["kind"] == KIND
        and hints["kind"] == PROOF and marker["principal_id"] == user
        and marker["task_id"] == marker["source"] == hints["source"] == hints["run"])
    source_scope(store, c, user, marker["task_id"])
    target_scope(store, c, user, aid)


def source(store, c, user, rid, limits):
    source_scope(store, c, user, rid)
    row = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
    require(row["error"] is None and not row["cancel_intent"])
    contract = store.frozen_contract(c, row)
    require(contract.ordinary_csv_report is not None and contract.mode == "mock")
    from .ordinary_csv import accepted_result, confirmation

    # Recheck historical completion, not active(): an execution deadline does
    # not expire a completed source. Current read/aggregate authority is above.
    expected = accepted_result(store, c, row, contract)
    require(row["result"] == expected, "Original complete CSV report no longer verifies")
    from .apps import csv_candidate

    spec = contract.ordinary_csv_report
    bounded = Limits(**{k: min(v, limits.model_dump()[k]) for k, v in contract.limits.model_dump().items()})
    candidate = csv_candidate(spec.resource_id, spec.source_hash, "", bounded)
    candidate["manifest"]["goal_ref"] = contract.goal.goal_id
    candidate["goal"] = dict(
        known="仅对明确绑定的CSV数值列求和，输出来源、列、记录数、精确合计及hash。",
        assumptions=["仅已有授权CSV及有界有限十进制；每次明确选列"],
        unresolved=["不生成或保存原MD报告；适用范围仍待本人确认，语义UNKNOWN"],
    )
    proof = dict(
        kind=PROOF, generator=GENERATOR, source_run_id=rid,
        source_run_version=row["version"], run_fingerprint=row["fingerprint"],
        contract_fingerprint=fingerprint(contract.model_dump(exclude_none=True)),
        confirmation_fingerprint=fingerprint(confirmation(store, c, row, contract)),
        source_goal_id=contract.goal.goal_id, source_goal_fingerprint=fingerprint(contract.goal.model_dump()),
        result_fingerprint=fingerprint(expected),
        receipts_fingerprint=fingerprint(expected["receipts"]),
        source_task_acceptance=copy.deepcopy(expected["task_acceptance"]),
        source_run_status="SUCCEEDED", source_task_accepted=True,
        source_resource_id=spec.resource_id, source_hash=spec.source_hash,
        source_report_hash=spec.report_hash, selected_scope="CSV_SUM_ONLY",
        full_md_report_included=False, candidate_task_acceptance="NOT_RUN",
        semantic_status="UNKNOWN", owner_acceptance="PENDING", model_requests=0,
        parameter_scope={"creation": ["different_csv_in_existing_authorization_domain"], "runtime": ["column"]},
        stable_logic={"tool_ref": "data.aggregate_csv", "tool_version": "1", "effect": "read",
            "check": "csv.exact_integer_sum.v1", "model_judgment": "NONE"},
    )
    return dict(project_id=row["project_id"], candidate=candidate), proof


def target(store, c, user, origin, aid, limits):
    target_scope(store, c, user, aid)
    return _target(store, c, user, origin, aid, limits)


def envelope(**values):
    return dict(state="CANDIDATE_ONLY", publishable=False, formal_publication_enabled=False,
        selected_scope="CSV_SUM_ONLY", full_md_report_included=False,
        source_run_status="SUCCEEDED", source_task_accepted=True,
        candidate_task_acceptance="NOT_RUN", semantic_status="UNKNOWN", owner_acceptance="PENDING",
        generator=GENERATOR, model_requests=0, **values)


def options(store, user, rid, limits):
    with store.tx() as c:
        origin, proof = source(store, c, user, rid, limits)
        targets = []
        for aid in c.execute(select(app_drafts.c.id).where(app_drafts.c.project_id == origin["project_id"])).scalars():
            try:
                value, name = target(store, c, user, origin, aid, limits)
                targets.append(dict(id=aid, name=name, **value))
            except DomainError:
                continue
        if not targets:
            raise DomainError("NEEDS_INPUT", "请选择另一份已有授权CSV草案；不会自动增加权限")
        return envelope(proof=proof, source_proof_fingerprint=fingerprint(proof), targets=targets)


def request(rid, body):
    return dict(source_run_id=rid, **{k: v for k, v in body.items() if k != "request_key"})


def result(draft, proof, key, req, cached):
    return envelope(id=draft["id"], candidate_fingerprint=draft["fingerprint"],
        source_run_id=proof["source_run_id"], request=copy.deepcopy(req),
        source_proof_fingerprint=fingerprint(proof), request_key=key,
        request_fingerprint=fingerprint(req), cached=cached)


def extract(store, user, rid, body, limits):
    with store.tx() as c:
        pid = c.execute(select(runs.c.project_id).where(runs.c.id == rid, runs.c.principal_id == user)).scalar()
        store.lock_project(c, user, pid)
        origin, proof = source(store, c, user, rid, limits)
        selected, _ = target(store, c, user, origin, body.target_app_id, limits)
        require(fingerprint(proof) == body.expected_proof_fingerprint
            and selected["fingerprint"] == body.expected_target_draft_fingerprint)
        req = request(rid, body.model_dump())
        old = c.execute(select(task_extractions).where(
            task_extractions.c.task_id == rid, task_extractions.c.principal_id == user,
            task_extractions.c.request_key == body.request_key,
        )).mappings().first()
        from .apps import compile_preview, load_draft

        if old:
            require(old["request_fingerprint"] == fingerprint(req))
            draft, _, _, _ = load_draft(store, c, user, old["app_id"], limits)
        else:
            value = _candidate(origin, proof, selected)
            compile_preview(value, limits)
            draft = dict(id=value["manifest"]["app_id"], project_id=pid,
                runtime_id=selected["runtime_id"], name=body.name, candidate=value,
                fingerprint=fingerprint(value), created_at=time.time())
            c.execute(insert(app_drafts).values(**draft))
            c.execute(insert(task_extractions).values(task_id=rid, principal_id=user,
                request_key=body.request_key, request_fingerprint=fingerprint(req), app_id=draft["id"],
                snapshot=dict(kind=KIND, proof=proof, target=selected, request=req,
                    candidate_fingerprint=draft["fingerprint"])))
        return result(draft, proof, body.request_key, req, bool(old))


def recover(store, user, rid, key, limits):
    if not 1 <= len(key) <= 100:
        raise DomainError("INVALID_INPUT")
    with store.tx() as c:
        source_scope(store, c, user, rid)
        old = c.execute(select(task_extractions.c.app_id).where(
            task_extractions.c.task_id == rid, task_extractions.c.principal_id == user,
            task_extractions.c.request_key == key,
        )).scalar_one_or_none()
        if old is None:
            raise DomainError("RESOURCE_UNAVAILABLE", "未找到原key；这不证明原请求一定未受理")
        from .apps import load_draft

        draft, _, _, _ = load_draft(store, c, user, old, limits)
        saved = c.execute(select(task_extractions).where(task_extractions.c.app_id == old)).mappings().one()
        return result(draft, saved["snapshot"]["proof"], key, saved["snapshot"]["request"], True)


def validate_candidate(store, c, user, draft, limits):
    saved = c.execute(select(task_extractions).where(task_extractions.c.app_id == draft["id"])).mappings().one()
    snap = saved["snapshot"]
    require(saved["principal_id"] == user and isinstance(snap, dict)
        and set(snap) == {"kind", "proof", "target", "request", "candidate_fingerprint"}
        and snap["kind"] == KIND)
    try:
        req = dict(snap["request"])
        require(req.pop("source_run_id") == saved["task_id"])
        body = ExtractionInput.model_validate(dict(**req, request_key=saved["request_key"]))
    except (ValidationError, KeyError, TypeError) as exc:
        raise DomainError("VERSION_CONFLICT", "Stored sum extraction request changed") from exc
    require(request(saved["task_id"], body.model_dump()) == snap["request"]
        and fingerprint(snap["request"]) == saved["request_fingerprint"])
    origin, proof = source(store, c, user, saved["task_id"], limits)
    selected, _ = target(store, c, user, origin, body.target_app_id, limits)
    require(proof == snap["proof"] and fingerprint(proof) == body.expected_proof_fingerprint
        and selected == snap["target"] and selected["fingerprint"] == body.expected_target_draft_fingerprint
        and draft["project_id"] == origin["project_id"] and draft["runtime_id"] == selected["runtime_id"]
        and snap["candidate_fingerprint"] == draft["fingerprint"]
        and ("name" not in draft or draft["name"] == body.name))
    expected = _candidate(origin, proof, selected, draft["id"], draft["candidate"]["actions"][0]["action_id"])
    require(expected == draft["candidate"])


def mount(app, store, limits, identity):
    dependency = Depends(identity)

    @app.get("/api/runs/{rid}/csv-sum-candidate-options")
    def get_options(rid: str, user=dependency):
        return options(store, user, rid, limits)

    @app.post("/api/runs/{rid}/csv-sum-candidates", status_code=201)
    def make_candidate(rid: str, body: ExtractionInput, user=dependency):
        return extract(store, user, rid, body, limits)

    @app.get("/api/runs/{rid}/csv-sum-requests/{key}")
    def receipt(rid: str, key: str, user=dependency):
        from fastapi.responses import JSONResponse

        return JSONResponse(recover(store, user, rid, key, limits),
            headers={"Cache-Control": "no-store", "Vary": "Authorization"})
