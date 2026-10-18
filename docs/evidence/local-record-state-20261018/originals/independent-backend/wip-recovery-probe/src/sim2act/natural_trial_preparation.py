"""Server-authored P-A consent scope. Preparation never creates or dispatches Runs."""

import math
import time
from typing import Literal

from pydantic import Field, model_validator
from sqlalchemy import select

from . import natural_live_admission as gate
from .contracts import Strict
from .db import delivery_graph_requests, fingerprint, goal_card_versions, goal_cards
from .delivery_graph_apps import controlled
from .errors import DomainError
from .goals import validate_card_version
from .text_logic_reuse import pair, remember
from .tools import authorized_read

PREPARE = gate.VERSION + ".pa-preparation"


class GoalChoice(Strict):
    card_id: str = Field(pattern=r"^goal_[a-f0-9]{32}$")
    expected_version: int = Field(strict=True, ge=1)


class PrepareInput(Strict):
    bindings: list[GoalChoice] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def distinct(self):
        gate.require(self.bindings[0].card_id != self.bindings[1].card_id)
        return self


class ConsentInput(Strict):
    review_token: str = Field(pattern=gate.HASH)
    confirm_exact_scope: Literal[True]


class WithdrawInput(Strict):
    review_token: str = Field(pattern=gate.HASH)
    confirm_withdrawal: Literal[True]


class EndInput(Strict):
    confirm_end: Literal[True]


class Closure(Strict):
    principal_id: str
    project_id: str
    trial_key: str = Field(pattern=gate.KEY)
    review_token: str = Field(pattern=gate.HASH)
    preparation_fingerprint: str = Field(pattern=gate.HASH)
    closed_at: float
    request: EndInput


def entity(user, pid, key):
    return "naturaltrial_" + fingerprint(dict(user=user, project=pid, key=key))[:32]


def stage_keys(user, pid, key):
    prefix = fingerprint(dict(user=user, project=pid, key=key))[:32]
    return gate.StageKeys(**{s: prefix + "_" + s for s in ("generate", "source", "cold")})


def approval_key(contract):
    return contract.stage_keys.generate + "_approval"


def _load(store, c, user, pid, key, *, current=True):
    project = store.lock_project(c, user, pid)
    eid = entity(user, pid, key)
    query = select(delivery_graph_requests).where(
        delivery_graph_requests.c.principal_id == user,
        delivery_graph_requests.c.app_id == eid,
        delivery_graph_requests.c.kind == PREPARE,
        delivery_graph_requests.c.request_key == "prepare")
    # Authorize both projected resource IDs before reading private paired JSON.
    for index in range(2):
        rid = c.execute(query.with_only_columns(delivery_graph_requests.c.snapshot[
            "response"]["bindings"][index]["resource_id"].as_string())).scalar()
        if rid is None:
            raise DomainError("OUTCOME_UNKNOWN", "No complete preparation under this original key")
        store.authorize(c, user, project["runtime_id"], pid, rid, "resource.read")
    store.authorize(c, user, project["runtime_id"], pid, pid, "artifact.save_text")
    request, value = pair(c, user, eid, PREPARE, "prepare", PrepareInput)
    contract = gate.parse_contract(value)
    gate.require(contract.principal_id == user and contract.project_id == pid
        and contract.trial_key == key and entity(user, pid, key) == gate.entity(contract)
        and contract.stage_keys == stage_keys(user, pid, key)
        and request.bindings == [GoalChoice(card_id=b.card_id,
            expected_version=b.goal_version) for b in contract.bindings])
    if current:
        gate._current(store, c, user, contract, active=False)
    else:
        # Ending grants no execution authority; only current project/READ/SAVE
        # authority and the original immutable pair are needed after Goal drift.
        gate._authorize(store, c, user, contract)
    return request, contract


def _receipt(store, c, user, contract):
    closed = _closed(c, user, contract.project_id, contract.trial_key)
    if closed:
        return closed
    approved = bool(gate._keys(c, user, gate.entity(contract), gate.APPROVE))
    receipt = dict(status="PREPARED_LIVE_BLOCKED", path="P-A", contract=contract.model_dump(),
        review_token=fingerprint(contract.model_dump()), approved=approved,
        expired=time.time() >= contract.expires_at, live_allowed=False,
        new_runs=0, new_slots=0, actual_model_requests=0,
        fee_status="NOT_VERIFIED", formal_publication_enabled=False)
    if isinstance(contract, gate.TrialContractV2):
        receipt["review_expired"] = time.time() >= contract.review_expires_at
    if approved:
        approval = gate._approved(store, c, user, contract, approval_key(contract), active=False)
        receipt["approval"] = gate._receipt(approval)
        receipt["revoked"] = bool(gate._keys(c, user, gate.entity(contract), gate.REVOKE))
    else:
        receipt["revoked"] = False
    return receipt


def _closed(c, user, pid, key):
    eid = entity(user, pid, key)
    keys = gate._keys(c, user, eid, gate.CLOSED)
    if not keys:
        return None
    gate.require(keys == {"close"} and gate._keys(c, user, eid, PREPARE) == {"prepare"})
    record = gate._saved(c, user, eid, gate.CLOSED, "close", Closure)
    gate.require(record.principal_id == user and record.project_id == pid
        and record.trial_key == key and math.isfinite(record.closed_at) and record.closed_at > 0)
    # Metadata-only recovery checks original pair fingerprints without TXT/Goal JSON.
    prepared_fps = c.execute(select(delivery_graph_requests.c.request_fingerprint).where(
        delivery_graph_requests.c.principal_id == user,
        delivery_graph_requests.c.app_id == eid,
        delivery_graph_requests.c.kind.in_([PREPARE, PREPARE + "_seal"]),
        delivery_graph_requests.c.request_key == "prepare")).scalars().all()
    gate.require(len(prepared_fps) == 2
        and all(fp == record.preparation_fingerprint for fp in prepared_fps))
    for kind in (gate.SCOPE, gate.APPROVE, gate.PHASE, gate.REVOKE):
        gate.require(not gate._keys(c, user, eid, kind), "Closed preparation has conflicting records")
    return dict(status="PREPARATION_CLOSED_NO_APPROVAL", approved=False,
        review_token=record.review_token, closed_at=record.closed_at, live_allowed=False,
        new_runs=0, new_slots=0, actual_model_requests=0)


@controlled
def end_preparation(store, user, pid, key, body: EndInput):
    with store.tx() as c:
        store.lock_project(c, user, pid)
        # Complete pair + fresh authority, without requiring obsolete Goal head equality.
        request, contract = _load(store, c, user, pid, key, current=False)
        closed = _closed(c, user, pid, key)
        if closed:
            gate.require(closed["review_token"] == fingerprint(contract.model_dump()))
            return closed
        eid = entity(user, pid, key)
        for kind in (gate.SCOPE, gate.APPROVE, gate.PHASE, gate.REVOKE):
            gate.require(not gate._keys(c, user, eid, kind), "Approved preparation must be withdrawn")
        record = Closure(principal_id=user, project_id=pid, trial_key=key,
            review_token=fingerprint(contract.model_dump()),
            preparation_fingerprint=fingerprint(request.model_dump()),
            closed_at=time.time(), request=body)
        gate._save(c, user, eid, gate.CLOSED, "close", record)
        return _closed(c, user, pid, key)


@controlled
def prepare(store, user, pid, key, body: PrepareInput):
    with store.tx() as c:
        project = store.lock_project(c, user, pid)
        eid = entity(user, pid, key)
        existing = c.execute(select(delivery_graph_requests.c.request_key).where(
            delivery_graph_requests.c.principal_id == user,
            delivery_graph_requests.c.app_id == eid,
            delivery_graph_requests.c.kind.in_([PREPARE, PREPARE + "_seal"]),
            delivery_graph_requests.c.request_key == "prepare")).first()
        if existing:
            original, contract = _load(store, c, user, pid, key)
            gate.require(original == body, "Original preparation key belongs to another scope")
            return _receipt(store, c, user, contract)
        gate.require(not gate._keys(c, user, eid, gate.SCOPE), "Trial key already has another scope")
        sources = []
        # Scalar goal location/version and resource projections precede private reads.
        for choice in body.bindings:
            card = c.execute(select(goal_cards.c.project_id, goal_cards.c.version).where(
                goal_cards.c.id == choice.card_id)).mappings().first()
            if card is None or card["project_id"] != pid:
                raise DomainError("PERMISSION_DENIED")
            gate.require(card["version"] == choice.expected_version, "Goal version changed")
            query = select(goal_card_versions).where(goal_card_versions.c.card_id == choice.card_id,
                goal_card_versions.c.version == choice.expected_version)
            refs = c.execute(query.with_only_columns(
                goal_card_versions.c.snapshot["content"]["resource_refs"])).scalar()
            gate.require(isinstance(refs, list) and len(refs) == 1,
                         "Each complete Goal must bind exactly one TXT")
            store.authorize(c, user, project["runtime_id"], pid, refs[0], "resource.read")
            sources.append(refs[0])
        store.authorize(c, user, project["runtime_id"], pid, pid, "artifact.save_text")
        bindings = []
        for choice, rid in zip(body.bindings, sources, strict=True):
            saved = validate_card_version(store, c, user, choice.card_id, choice.expected_version)
            material = authorized_read(store, c, user, project["runtime_id"], pid,
                                       "resource.read", {"resource_id": rid})
            bindings.append(gate.MaterialGoal(resource_id=rid, content=material["content"],
                source_hash=material["hash"], card_id=choice.card_id,
                goal_version=choice.expected_version, goal_fingerprint=saved["fingerprint"],
                goal_snapshot=saved["snapshot"]))
            gate.require(material["format"] == "txt", "Only finite TXT is supported")
        prepared_at = time.time()
        contract = gate.TrialContractV2(prepared_at=prepared_at,
            review_expires_at=prepared_at + 300, execution_expires_at=prepared_at + 3600,
            trial_key=key, project_id=pid, principal_id=user,
            runtime_id=project["runtime_id"], quota_subject="unconfigured:" + user,
            software_fingerprint=gate.implementation(),
            authorization_fingerprint=gate.authorization_fingerprint(c, user, pid,
                project["runtime_id"], sources), bindings=bindings,
            stage_keys=stage_keys(user, pid, key), expires_at=prepared_at + 3600)
        gate._current(store, c, user, contract)
        remember(c, user, eid, PREPARE, "prepare", body, contract.model_dump())
        gate._current(store, c, user, contract)
        return _receipt(store, c, user, contract)


@controlled
def recover(store, user, pid, key):
    with store.tx() as c:
        store.lock_project(c, user, pid)
        closed = _closed(c, user, pid, key)
        if closed:
            return closed
        _, contract = _load(store, c, user, pid, key)
        return _receipt(store, c, user, contract)


@controlled
def approve(store, user, pid, key, body: ConsentInput):
    with store.tx() as c:
        _, contract = _load(store, c, user, pid, key)
        gate.require(body.review_token == fingerprint(contract.model_dump()), "Reviewed scope changed")
    return gate.approve(store, user, contract, gate.ApproveInput(
        expected_contract_fingerprint=body.review_token, request_key=approval_key(contract),
        consent="APPROVE_ONLY_THIS_EXACT_SEVEN_SLOT_ZERO_PAID_NATURAL_TRIAL"))


@controlled
def withdraw(store, user, pid, key, body: WithdrawInput):
    # Reuse exact metadata-only stop. No private material read or renewed authority.
    return gate.revoke_exact(store, user, pid, entity(user, pid, key), body.review_token,
        gate.RevokeInput(expected_contract_fingerprint=body.review_token,
            request_key=stage_keys(user, pid, key).generate + "_revoke",
            consent="REVOKE_ONLY_THIS_EXACT_NATURAL_TRIAL"))


@controlled
def status(store, user, pid, key):
    """Original-key consent metadata remains readable for stopping after READ revocation."""
    with store.tx() as c:
        store.lock_project(c, user, pid)
        eid = entity(user, pid, key)
        gate.require(gate._keys(c, user, eid, PREPARE) == {"prepare"})
        closed = _closed(c, user, pid, key)
        if closed:
            return closed
        approved = gate._keys(c, user, eid, gate.APPROVE)
        if not approved:
            return dict(status="PREPARED_NOT_APPROVED", approved=False, live_allowed=False,
                        new_runs=0, new_slots=0, actual_model_requests=0)
        gate.require(approved == {"approve"}
            and gate._keys(c, user, eid, gate.SCOPE) == {"scope"})
        approval = gate._saved(c, user, eid, gate.APPROVE, "approve", gate.Approval)
        fp = approval.contract_fingerprint
        scope_fps = c.execute(select(delivery_graph_requests.c.request_fingerprint).where(
            delivery_graph_requests.c.app_id == eid,
            delivery_graph_requests.c.principal_id == user,
            delivery_graph_requests.c.kind.in_([gate.SCOPE, gate.SCOPE + "_seal"]),
            delivery_graph_requests.c.request_key == "scope")).scalars().all()
        gate.require(approval.principal_id == user and approval.project_id == pid
            and approval.request.request_key == stage_keys(user, pid, key).generate + "_approval"
            and approval.request.expected_contract_fingerprint == fp
            and len(scope_fps) == 2 and all(value == fp for value in scope_fps))
        revoked = gate._keys(c, user, eid, gate.REVOKE)
        gate.require(revoked <= {"revoke"})
        if revoked:
            revocation = gate._saved(c, user, eid, gate.REVOKE, "revoke", gate.RevokeInput)
            gate.require(revocation.expected_contract_fingerprint == fp)
        return dict(status="CONSENT_METADATA_ONLY_LIVE_BLOCKED", approved=True,
            review_token=fp, revoked=bool(revoked), expired=time.time() >= approval.expires_at,
            expires_at=approval.expires_at, live_allowed=False,
            new_runs=0, new_slots=0, actual_model_requests=0)
