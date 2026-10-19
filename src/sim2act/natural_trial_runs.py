"""Atomic server-controller trial acceptance, with no sender or HTTP authority.

Current literal software qualification remains mandatory. Controlled synthetic
proofs of this coordinator do not qualify a Worker or authorize provider IO.
"""

import math
import time
from typing import Literal

from pydantic import Field
from sqlalchemy import exists, or_, select, update

from . import natural_live_admission as gate
from . import production_trial_admission as production
from .contracts import Limits, Strict
from .db import delivery_graph_requests as rows
from .db import fingerprint, run_contracts, runs
from .delivery_graph_apps import controlled
from .errors import DomainError
from .pa_trial_dispatch import PATrialBinding
from .pb_natural_uses import PACommitInput

ASSOCIATION: Literal["natural-trial-run.v1"] = "natural-trial-run.v1"
MARKER = "natural_trial_run"


class StageInput(Strict):
    instance_id: str = Field(pattern=r"^iinstance_[a-f0-9]{32}$")
    expected_revision: int = Field(strict=True, ge=1)
    expected_release_fingerprint: str = Field(pattern=gate.HASH)
    pa_use: PACommitInput | None = None


class Association(Strict):
    namespace: Literal["natural-trial-run.v1"] = ASSOCIATION
    principal_id: str
    project_id: str
    trial_key: str
    contract_fingerprint: str = Field(pattern=gate.HASH)
    approval_key: str = Field(pattern=gate.KEY)
    stage: gate.Stage
    request_key: str = Field(pattern=gate.KEY)
    input_fingerprint: str = Field(pattern=gate.HASH)
    run_id: str = Field(pattern=r"^run_[a-f0-9]{32}$")
    created_at: float = Field(gt=0, allow_inf_nan=False)
    run_fingerprint: str = Field(pattern=gate.HASH)
    frozen_fingerprint: str = Field(pattern=gate.HASH)


def _scope(store, c, user, binding, *, active=True, qualified=True):
    gate.require(
        type(binding) is PATrialBinding and type(binding.contract) is gate.TrialContractV2,
        "Atomic acceptance requires the exact prepared P-A V2 trial",
    )
    contract = binding.contract
    gate.require(fingerprint(contract.model_dump()) == binding.contract_fingerprint)
    if user != contract.principal_id:
        raise DomainError("PERMISSION_DENIED")
    gate._approved(store, c, user, contract, binding.approval_key, active=active)
    if qualified:
        production._qualified()
        # File qualification can consume the final execution interval. Reprove
        # the complete original approval after that work, before accepting it.
        gate._approved(store, c, user, contract, binding.approval_key, active=active)
    return contract


def _receipt(body):
    return dict(
        run_id=body.run_id,
        stage=body.stage,
        request_key=body.request_key,
        contract_fingerprint=body.contract_fingerprint,
        dispatch_allowed=False,
        new_model_requests=0,
        live_allowed=False,
    )


def _existing(c, user, contract, stage):
    key = getattr(contract.stage_keys, stage)
    keys = gate._keys(c, user, gate.entity(contract), ASSOCIATION)
    gate.require(keys <= set(contract.stage_keys.model_dump().values()))
    if key not in keys:
        return None
    body = gate._saved(c, user, gate.entity(contract), ASSOCIATION, key, Association)
    gate.require(
        body.principal_id == user
        and body.project_id == contract.project_id
        and body.trial_key == contract.trial_key
        and body.stage == stage
        and body.request_key == key
        and body.contract_fingerprint == fingerprint(contract.model_dump())
    )
    return body


@controlled
def context_association(c, job):
    """Validate metadata only; never grants claim, send or stage authority.

    Called after the caller's ordinary source scope proof. Preserve the marker
    in durable context and accept it only with both original paired histories.
    """
    associated = c.execute(select(runs.c.id, runs.c.principal_id, runs.c.project_id,
        runs.c.runtime_id, runs.c.created_at, runs.c.fingerprint,
        runs.c.context[MARKER].label("marker")).where(
        runs.c.id == job["id"], associated_sql())).mappings().first()
    if associated is None:
        gate.require(MARKER not in job["context"])
        return None
    body = Association.model_validate(job["context"].get(MARKER))
    frozen = c.execute(select(run_contracts).where(
        run_contracts.c.run_id == job["id"])).mappings().one()
    gate.require(
        associated["marker"] == body.model_dump()
        and all(associated[k] == job[k] for k in (
            "id", "principal_id", "project_id", "runtime_id", "created_at", "fingerprint"))
        and body.run_id == job["id"]
        and body.principal_id == job["principal_id"]
        and body.project_id == job["project_id"]
        and body.created_at == job["created_at"]
        and body.run_fingerprint == job["fingerprint"]
        and fingerprint(frozen["snapshot"]) == frozen["fingerprint"] == body.frozen_fingerprint
        and gate._saved(c, body.principal_id, body.run_id,
            ASSOCIATION, body.request_key, Association) == body
        and gate._saved(c, body.principal_id, gate.entity(body),
            ASSOCIATION, body.request_key, Association) == body
    )
    return body


def _check_run(store, c, body):
    # Authorize the exact Run before any context/contract or association body.
    from .goal_applications import source_scope_gate

    source_scope_gate(store, c, body.run_id)
    job = c.execute(select(runs).where(runs.c.id == body.run_id)).mappings().one()
    gate.require(context_association(c, job) == body)
    return job


def _record(store, c, user, binding, stage, value, rid):
    contract = binding.contract
    job = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
    # An already existing ordinary Run cannot be adopted into a new trial.
    gate.require(
        job["status"] == "QUEUED"
        and job["fence"] == 0
        and job["cancel_intent"] is False
        and MARKER not in job["context"]
    )
    body = Association(
        principal_id=user,
        project_id=contract.project_id,
        trial_key=contract.trial_key,
        contract_fingerprint=binding.contract_fingerprint,
        approval_key=binding.approval_key,
        stage=stage,
        request_key=getattr(contract.stage_keys, stage),
        input_fingerprint=fingerprint(value),
        run_id=rid,
        created_at=job["created_at"],
        run_fingerprint=job["fingerprint"],
        frozen_fingerprint=c.execute(
            select(run_contracts.c.fingerprint).where(run_contracts.c.run_id == rid)
        ).scalar_one(),
    )
    c.execute(
        update(runs)
        .where(runs.c.id == rid)
        .values(context={**job["context"], MARKER: body.model_dump()})
    )
    gate._save(c, user, rid, ASSOCIATION, body.request_key, body)
    gate._save(c, user, gate.entity(contract), ASSOCIATION, body.request_key, body)
    store.event(c, rid, "NATURAL_TRIAL_ASSOCIATED", body.model_dump())
    _check_run(store, c, body)
    _scope(store, c, user, binding)
    return _receipt(body)


@controlled
def submit_generate(store, user, binding):
    """Use only the prepared Generate key/Goal/caps, in one owning transaction."""
    from .goal_applications import policy

    with store.tx() as c:
        contract = _scope(store, c, user, binding)
        first = contract.bindings[0]
        value = dict(
            card_id=first.card_id,
            expected_version=first.goal_version,
            expected_fingerprint=first.goal_fingerprint,
            request_key=contract.stage_keys.generate,
            family="natural_spec",
        )
        old = _existing(c, user, contract, "generate")
        if old:
            gate.require(
                old.approval_key == binding.approval_key
                and old.input_fingerprint == fingerprint(value)
            )
            _check_run(store, c, old)
            _scope(store, c, user, binding)
            return _receipt(old)
        gate.require(
            c.execute(
                select(runs.c.id).where(
                    runs.c.principal_id == user,
                    runs.c.project_id == contract.project_id,
                    runs.c.request_key == contract.stage_keys.generate,
                )
            ).first()
            is None,
            "Original Generate key belongs to an unassociated operation",
        )
        limits = gate._limits(contract)
        app_limits = Limits(
            **{**limits.model_dump(), "max_requests": 2, "max_tools": 4, "max_repairs": 0}
        )
        selected = policy("intern-s2", user, contract.project_id, value, app_limits=app_limits)
        rid = store.submit_tx(
            c,
            user,
            contract.project_id,
            "",
            [],
            contract.stage_keys.generate,
            policy=dict(
                limits={**limits.model_dump(), "max_tools": 2},
                mode="mock",
                request_model=contract.model,
                application_generation=selected,
            ),
            goal_source=dict(
                card_id=first.card_id,
                version=first.goal_version,
                fingerprint=first.goal_fingerprint,
            ),
        )
        return _record(store, c, user, binding, "generate", value, rid)


@controlled
def submit_stage(store, user, binding, stage: Literal["source", "cold"], body: StageInput):
    """Queue a fully proved existing application; explicit phase consent stays separate."""
    from .app_jobs import enqueue
    from .db import internal_app_runs, internal_instances

    gate.require(
        stage in ("source", "cold")
        and type(body) is StageInput
        and StageInput.model_validate(body.model_dump()) == body
    )
    with store.tx() as c:
        contract = _scope(store, c, user, binding)
        value = body.model_dump()
        old = _existing(c, user, contract, stage)
        if old:
            gate.require(
                old.approval_key == binding.approval_key
                and old.input_fingerprint == fingerprint(value)
            )
            _check_run(store, c, old)
            _scope(store, c, user, binding)
            return _receipt(old)
        gate.require(
            c.execute(
                select(internal_instances.c.project_id).where(
                    internal_instances.c.id == body.instance_id
                )
            ).scalar()
            == contract.project_id
        )
        key = getattr(contract.stage_keys, stage)
        gate.require(
            c.execute(
                select(internal_app_runs.c.id).where(
                    internal_app_runs.c.principal_id == user,
                    internal_app_runs.c.instance_id == body.instance_id,
                    internal_app_runs.c.request_key == key,
                )
            ).first()
            is None,
            "Original stage key belongs to an unassociated operation",
        )
        gate.require(
            (stage == "source" and body.pa_use is None)
            or (stage == "cold" and body.pa_use is not None)
        )
        result = enqueue(
            store,
            user,
            body.instance_id,
            body.expected_revision,
            body.expected_release_fingerprint,
            {},
            key,
            gate._limits(contract),
            pa_use=body.pa_use,
            logic_tx=c,
        )
        gate.require(result.get("cached") is False, "Existing stage cannot be adopted")
        rid = result["run_id"]
        authority, _ = gate._stage_current(store, c, user, contract, stage, rid)
        gate._stage_review_window(authority)
        receipt = _record(store, c, user, binding, stage, value, rid)
        fresh, _ = gate._stage_current(store, c, user, contract, stage, rid)
        gate.require(fresh == authority)
        gate._stage_review_window(fresh)
        _scope(store, c, user, binding)
        return receipt


@controlled
def recover(store, user, binding, stage):
    """Original-key metadata only; never POST, retry, extend, or resume execution."""
    gate.require(type(binding) is PATrialBinding and stage in ("generate", "source", "cold"))
    contract = binding.contract
    with store.tx() as c:
        gate._authorize(store, c, user, contract)
        gate.require(fingerprint(contract.model_dump()) == binding.contract_fingerprint)
        old = _existing(c, user, contract, stage)
        if old is None:
            raise DomainError("OUTCOME_UNKNOWN", "No complete original acceptance")
        gate.require(old.approval_key == binding.approval_key)
        # No Goal/material bodies or current execution proof: this is only history.
        gate.require(
            gate._saved(c, user, old.run_id, ASSOCIATION, old.request_key, Association) == old
        )
        return _receipt(old)


def associated_sql():
    """Scalar marker OR either durable side: partial damage cannot open the queue."""
    return or_(
        runs.c.context[MARKER]["run_id"].as_string().is_not(None),
        exists(
            select(rows.c.app_id).where(
                rows.c.app_id == runs.c.id, rows.c.kind.in_([ASSOCIATION, ASSOCIATION + "_seal"])
            )
        ),
    )


@controlled
def check_claim(store, c, rid, binding):
    """No boolean bypass; original approval and literal qualification rechecked."""
    meta = (
        c.execute(select(runs.c.principal_id, runs.c.project_id).where(runs.c.id == rid))
        .mappings()
        .one()
    )
    gate.require(type(binding) is PATrialBinding)
    contract = _scope(store, c, meta["principal_id"], binding)
    gate.require(meta["project_id"] == contract.project_id)
    from .goal_applications import source_scope_gate

    source_scope_gate(store, c, rid)
    marker = c.execute(select(runs.c.context[MARKER]).where(runs.c.id == rid)).scalar_one()
    body = Association.model_validate(marker)
    gate.require(
        body == _existing(c, meta["principal_id"], contract, body.stage)
        and body.approval_key == binding.approval_key
        and body.run_id == rid
    )
    job = _check_run(store, c, body)
    created = job["created_at"]
    frozen_seconds = store.frozen_contract(c, job).limits.run_seconds
    gate.require(
        job["cancel_intent"] is False
        and type(created) in (int, float)
        and math.isfinite(created)
        and created
        <= time.time()
        < min(
            created + min(contract.caps.run_seconds, frozen_seconds), contract.execution_expires_at
        ),
        "Original associated Run deadline ended",
    )
    if body.stage != "generate":
        gate.require(
            body.stage in gate._keys(c, body.principal_id, gate.entity(contract), gate.PHASE),
            "Stage requires its original explicit approval before claim",
        )
        phase = gate._saved(
            c,
            body.principal_id,
            gate.entity(contract),
            gate.PHASE,
            body.stage,
            gate.StageApproveInput,
        )
        authority, _ = gate._stage_current(store, c, body.principal_id, contract, body.stage, rid)
        gate.require(
            phase.authority == authority
            and phase.approval_key == binding.approval_key
            and phase.expected_authority_fingerprint == fingerprint(authority.model_dump())
        )
        # Handoff bounds explicit approval, not dispatch of an already approved
        # Run. Existing admission keeps execution/Run/lease deadlines mandatory.
    _scope(store, c, meta["principal_id"], binding)
    deadline = min(
        created + min(contract.caps.run_seconds, frozen_seconds), contract.execution_expires_at
    )
    gate.require(time.time() < deadline, "Original associated Run deadline ended")
    return deadline


def check_worker_tx(worker, c, rid):
    """Reprove association inside the actual owning send/final-write transaction."""
    marked = c.execute(select(runs.c.id).where(runs.c.id == rid, associated_sql())).first()
    if marked:
        from .pa_trial_dispatch import _account, _binding

        binding = _binding(worker)
        _account(worker, binding)
        check_claim(worker.store, c, rid, binding)


def check_worker(worker, rid):
    with worker.store.tx() as c:
        check_worker_tx(worker, c, rid)
