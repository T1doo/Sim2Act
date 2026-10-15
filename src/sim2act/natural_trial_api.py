"""Authenticated trial consent interface; no sender or LIVE authority registered."""

import re

from fastapi import Depends
from pydantic import Field
from sqlalchemy import select

from . import natural_live_admission as gate
from . import natural_trial_budget as budget
from . import production_trial_admission as production
from .contracts import Strict
from .db import delivery_graph_requests, fingerprint
from .delivery_graph_apps import controlled
from .errors import DomainError

Contract = gate.PBTrialContract | gate.TrialContract


class ApprovalRequest(Strict):
    contract: Contract
    approval: gate.ApproveInput


class RevokeRequest(Strict):
    contract: Contract
    revocation: gate.RevokeInput


class StageReviewRequest(Strict):
    contract: Contract
    approval_key: str = Field(pattern=gate.KEY)
    stage: gate.Stage
    run_id: str = Field(pattern=r"^run_[a-f0-9]{32}$")


class StageApprovalRequest(Strict):
    contract: Contract
    approval: gate.StageApproveInput


class AdmissionRequest(StageReviewRequest):
    expected_version: int = Field(strict=True, ge=1)
    fence: int = Field(strict=True, ge=1)


def _scope(user, pid, key, contract):
    if contract.principal_id != user or contract.project_id != pid:
        raise DomainError("PERMISSION_DENIED")
    gate.require(contract.trial_key == key)


@controlled
def original_contract(store, user, pid, key):
    """Original key lookup: scalar authorization gates before private JSON body."""
    eid = "naturaltrial_" + fingerprint(dict(user=user, project=pid, key=key))[:32]
    with store.tx() as c:
        project = store.lock_project(c, user, pid)
        query = select(delivery_graph_requests).where(
            delivery_graph_requests.c.principal_id == user,
            delivery_graph_requests.c.app_id == eid,
            delivery_graph_requests.c.kind == gate.SCOPE,
            delivery_graph_requests.c.request_key == "scope")
        for index in range(2):
            resource = c.execute(query.with_only_columns(
                delivery_graph_requests.c.snapshot["request"]["bindings"][index]["resource_id"].as_string()
            )).scalar()
            if resource is None:
                raise DomainError("OUTCOME_UNKNOWN", "No complete original trial scope")
            store.authorize(c, user, project["runtime_id"], pid, resource, "resource.read")
        store.authorize(c, user, project["runtime_id"], pid, pid, "artifact.save_text")
        value = c.execute(query).mappings().one()["snapshot"]["request"]
        model = gate.PBTrialContract if value.get("path") == "P-B" else gate.TrialContract
        contract = gate._saved(c, user, eid, gate.SCOPE, "scope", model)
        _scope(user, pid, key, contract)
        gate._current(store, c, user, contract, active=False)
        return contract


def mount(app, store, identity):
    dependency = Depends(identity)
    base = "/api/projects/{pid}/natural-trials/{key}"

    from . import natural_trial_preparation as preparation

    @app.post(base + "/preparation")
    def prepare(pid: str, key: str, body: preparation.PrepareInput, user=dependency):
        gate.require(re.fullmatch(gate.KEY, key) is not None)
        return preparation.prepare(store, user, pid, key, body)

    @app.get(base + "/preparation")
    def prepared(pid: str, key: str, user=dependency):
        return preparation.recover(store, user, pid, key)

    @app.get(base + "/consent-status")
    def consent_status(pid: str, key: str, user=dependency):
        return preparation.status(store, user, pid, key)

    @app.post(base + "/consent")
    def consent(pid: str, key: str, body: preparation.ConsentInput, user=dependency):
        return preparation.approve(store, user, pid, key, body)

    @app.post(base + "/withdrawal")
    def withdrawal(pid: str, key: str, body: preparation.WithdrawInput, user=dependency):
        return preparation.withdraw(store, user, pid, key, body)

    @app.post(base + "/approval")
    def approve(pid: str, key: str, body: ApprovalRequest, user=dependency):
        _scope(user, pid, key, body.contract)
        return gate.approve(store, user, body.contract, body.approval)

    @app.get(base + "/approvals/{approval_key}")
    def recover(pid: str, key: str, approval_key: str, user=dependency):
        contract = original_contract(store, user, pid, key)
        return gate.recover(store, user, contract, approval_key)

    @app.post(base + "/revocation")
    def revoke(pid: str, key: str, body: RevokeRequest, user=dependency):
        _scope(user, pid, key, body.contract)
        return gate.revoke(store, user, body.contract, body.revocation)

    @app.post(base + "/stage-review")
    def stage_review(pid: str, key: str, body: StageReviewRequest, user=dependency):
        _scope(user, pid, key, body.contract)
        gate.require(body.stage in ("source", "cold"))
        return gate.stage_review(store, user, body.contract, body.approval_key,
                                 body.stage, body.run_id)

    @app.post(base + "/stage-approval")
    def stage_approval(pid: str, key: str, body: StageApprovalRequest, user=dependency):
        _scope(user, pid, key, body.contract)
        return gate.approve_stage(store, user, body.contract, body.approval)

    @app.get(base + "/approvals/{approval_key}/stages/{stage}/{request_key}")
    def stage_receipt(pid: str, key: str, approval_key: str, stage: str,
                      request_key: str, user=dependency):
        contract = original_contract(store, user, pid, key)
        return gate.recover_stage(store, user, contract, approval_key, stage, request_key)

    @app.get(base + "/approvals/{approval_key}/budget")
    def ledger(pid: str, key: str, approval_key: str, user=dependency):
        contract = original_contract(store, user, pid, key)
        gate.recover(store, user, contract, approval_key)
        return budget.read(store, user, budget.scope_for(contract, approval_key).model_dump())

    @app.get(base + "/approvals/{approval_key}/source-archive")
    def source_archive(pid: str, key: str, approval_key: str, user=dependency):
        from .natural_source_archives import resolve_trial_source

        contract = original_contract(store, user, pid, key)
        return resolve_trial_source(store, user, contract, approval_key).public_receipt

    @app.post(base + "/admission")
    def admission(pid: str, key: str, body: AdmissionRequest, user=dependency):
        _scope(user, pid, key, body.contract)
        return production.production_preflight(store, user, body.contract, body.approval_key, body)

    @app.post(base + "/production-admission")
    def production_admission(pid: str, key: str, body: AdmissionRequest, user=dependency):
        _scope(user, pid, key, body.contract)
        return production.production_preflight(store, user, body.contract, body.approval_key, body)
