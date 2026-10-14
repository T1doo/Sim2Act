"""Synthetic SQLite admission proofs; no real HTTP, fee or account probing."""

import asyncio
import copy
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import delete, select, update
from test_natural_spec_apps import COLD, SOURCE, enqueue, material, ready, setup, transport

from sim2act import natural_live_admission as gate
from sim2act import pb_natural_uses as use
from sim2act.db import (
    attempts,
    delivery_graph_requests,
    fingerprint,
    grants,
    internal_instances,
    runs,
)
from sim2act.errors import DomainError
from sim2act.goal_applications import response_archive
from sim2act.goals import inspect_card
from sim2act.model import normalize_usage
from sim2act.worker import Worker


def frozen(data, *, ttl=300.0):
    store, _, client, user, pid, rid, card = data
    cold, cold_card = material(client, pid, COLD)
    with store.tx() as c:
        project = store.own_project(c, user, pid)
        store.add_grants(c, user, project["runtime_id"], pid, pid, ["artifact.save_text"])
    bindings = []
    for resource, goal, text in ((rid, card, SOURCE), (cold, cold_card, COLD)):
        record = inspect_card(store, user, goal["id"])
        saved = record["history"][0]
        bindings.append(dict(resource_id=resource, content=text,
            source_hash=saved["snapshot"]["resource_snapshots"][0]["hash"],
            card_id=goal["id"], goal_version=goal["version"], goal_fingerprint=goal["fingerprint"],
            goal_snapshot=saved["snapshot"]))
    with store.tx() as c:
        authorization = gate.authorization_fingerprint(c, user, pid, project["runtime_id"],
                                                       [b["resource_id"] for b in bindings])
    contract = gate.TrialContract(trial_key="one-neutral-trial", project_id=pid,
        principal_id=user, runtime_id=project["runtime_id"], quota_subject="synthetic-only-account",
        software_fingerprint=gate.implementation(), authorization_fingerprint=authorization,
        bindings=bindings, stage_keys=gate.StageKeys(generate="natural-generation",
            source="spec-actual", cold="cold-trial-run"), expires_at=time.time() + ttl)
    body = gate.ApproveInput(expected_contract_fingerprint=fingerprint(contract.model_dump()),
                            request_key="exact-approval", consent=gate.CONSENT)
    return contract, body


@pytest.fixture
def approved(env):
    data = setup(env)
    contract, body = frozen(data)
    receipt = gate.approve(data[0], data[3], contract, body)
    yield data, contract, body, receipt
    data[2].close()


def started(data, contract):
    client, card = data[2], data[6]
    made = client.post(f"/api/projects/{data[4]}/goal-cards/{card['id']}/application-runs",
        json=dict(expected_version=card["version"], expected_fingerprint=card["fingerprint"],
                  request_key=contract.stage_keys.generate, family="natural_spec"))
    assert made.status_code == 202, made.text
    job = data[0].claim("synthetic-admission-worker", 30)
    assert job["id"] == made.json()["run_id"]
    return job


def permit(data, contract, body, job, *, authority=True, stage="generate"):
    fee = gate.SyntheticOnlyFeeAuthority(fingerprint(contract.model_dump()), contract.quota_subject)
    with data[0].tx() as c:
        return gate.admit(data[0], c, data[3], contract, body.request_key, stage,
                          job["id"], job["version"], job["fence"], fee if authority else None)


def records(store):
    with store.tx() as c:
        return [dict(r) for r in c.execute(select(delivery_graph_requests).order_by(
            delivery_graph_requests.c.app_id, delivery_graph_requests.c.kind,
            delivery_graph_requests.c.request_key)).mappings()]


def test_exact_approval_idempotent_cold_recovery_does_not_extend_expiry(approved):
    data, contract, body, receipt = approved
    before = records(data[0])
    assert gate.approve(data[0], data[3], contract, body) == receipt
    recovered = gate.recover(data[0], data[3], contract, body.request_key)
    assert recovered["approval"] == receipt["approval"]
    assert recovered["live_allowed"] is False and recovered["fee_status"] == "NOT_VERIFIED"
    assert recovered["actual_model_requests"] == 0 and records(data[0]) == before
    assert len([r for r in before if r["kind"].startswith(gate.VERSION)]) == 4


def test_default_real_deny_and_test_permit_is_not_live(approved):
    data, contract, body, _ = approved
    job = started(data, contract)
    with pytest.raises(DomainError, match="production zero-charge") as error:
        permit(data, contract, body, job, authority=False)
    assert error.value.code == "LIVE_BLOCKED"
    allowed = permit(data, contract, body, job)
    assert allowed.scope == "SYNTHETIC_ONLY" and allowed.live_allowed is False
    assert allowed.runtime_id == contract.runtime_id and allowed.stage_authority_fingerprint is None
    assert allowed.expires_at <= contract.expires_at


def test_user_free_claim_or_arbitrary_authority_never_called(approved):
    data, contract, body, _ = approved
    job = started(data, contract)

    class FakeFree:
        def verify(self, value):
            raise AssertionError("Untrusted authority must not be invoked")

    with data[0].tx() as c, pytest.raises(DomainError) as error:
        gate.admit(data[0], c, data[3], contract, body.request_key, "generate",
                   job["id"], job["version"], job["fence"], FakeFree())
    assert error.value.code == "LIVE_BLOCKED"
    raw = body.model_dump() | {"free": True}
    with pytest.raises(ValidationError):
        gate.ApproveInput.model_validate(raw)


def test_synthetic_authority_never_works_as_production(approved):
    data, contract, body, _ = approved
    job = started(data, contract)
    data[0].test_only = False
    try:
        with pytest.raises(DomainError) as error:
            permit(data, contract, body, job)
        assert error.value.code == "LIVE_BLOCKED"
    finally:
        data[0].test_only = True


@pytest.mark.parametrize("field,value", [
    ("max_requests", 8), ("generate_requests", 4), ("cold_requests", 3),
    ("max_output_tokens", 1025), ("max_wire_bytes", 32769), ("total_reserved", 192001),
    ("paid_cap", 1), ("run_seconds", 301), ("lease_seconds", 31),
    ("requests_per_minute", 2), ("total_output_tokens", 7169),
])
def test_original_caps_cannot_expand(field, value):
    with pytest.raises(ValidationError):
        gate.TrialCaps.model_validate(gate.TrialCaps().model_dump() | {field: value})


@pytest.mark.parametrize("change", ["quota", "expiry", "software", "stage-key", "goal"])
def test_same_trial_key_changed_contract_never_overwrites_approval(approved, change):
    data, contract, body, _ = approved
    before = records(data[0])
    raw = contract.model_dump()
    if change == "quota":
        raw["quota_subject"] = "different-account"
    elif change == "expiry":
        raw["expires_at"] += 1.0
    elif change == "software":
        raw["software_fingerprint"] = "f" * 64
    elif change == "stage-key":
        raw["stage_keys"]["generate"] = "different-original-key"
    else:
        raw["bindings"][0]["goal_snapshot"]["content"]["goal"] += " changed"
        raw["bindings"][0]["goal_fingerprint"] = fingerprint(raw["bindings"][0]["goal_snapshot"])
    changed = gate.TrialContract.model_validate(raw)
    changed_body = body.model_copy(update={"expected_contract_fingerprint": fingerprint(raw)})
    with pytest.raises(DomainError):
        gate.approve(data[0], data[3], changed, changed_body)
    assert records(data[0]) == before


@pytest.mark.parametrize("field,value", [
    ("cancel_intent", True), ("status", "CANCEL_REQUESTED"), ("version", 999),
    ("fence", 999), ("lease_until", 0.0), ("created_at", 0.0),
    ("runtime_id", "runtime_" + "a" * 32), ("request_key", "another-run"),
])
def test_fresh_run_cancel_fence_version_lease_identity_rejected(approved, field, value):
    data, contract, body, _ = approved
    job = started(data, contract)
    with data[0].tx() as c:
        c.execute(update(runs).where(runs.c.id == job["id"]).values(**{field: value}))
    before = records(data[0])
    with pytest.raises(DomainError):
        permit(data, contract, body, job)
    assert records(data[0]) == before


def test_revocation_irreversible_and_readable_with_no_new_permission(approved):
    data, contract, body, _ = approved
    job = started(data, contract)
    stop = gate.RevokeInput(expected_contract_fingerprint=fingerprint(contract.model_dump()),
        request_key="stop", consent="REVOKE_ONLY_THIS_EXACT_NATURAL_TRIAL")
    assert gate.revoke(data[0], data[3], contract, stop)["status"] == "REVOKED"
    before = records(data[0])
    assert gate.revoke(data[0], data[3], contract, stop)["status"] == "REVOKED"
    assert gate.recover(data[0], data[3], contract, body.request_key)["revoked"] is True
    with pytest.raises(DomainError):
        permit(data, contract, body, job)
    assert records(data[0]) == before


def test_permission_loss_denies_before_private_approval_read(approved, monkeypatch):
    data, contract, body, _ = approved
    with data[0].tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == contract.bindings[1].resource_id)
                  .values(revoked=True))

    def private(*args, **kwargs):
        raise AssertionError("Approval body must not be read before all current READ gates")

    monkeypatch.setattr(gate, "pair", private)
    with pytest.raises(DomainError) as error:
        gate.recover(data[0], data[3], contract, body.request_key)
    assert error.value.code == "GRANT_REVOKED"


def test_expired_history_does_not_restore_admission(env):
    data = setup(env)
    contract, body = frozen(data, ttl=3.0)
    gate.approve(data[0], data[3], contract, body)
    job = started(data, contract)
    delay = contract.expires_at - time.time()
    if delay > 0:
        time.sleep(delay + 0.01)
    assert gate.recover(data[0], data[3], contract, body.request_key)["expired"] is True
    with pytest.raises(DomainError, match="expired"):
        permit(data, contract, body, job)
    data[2].close()


def test_pair_loss_does_not_reprepare_or_reapprove(approved):
    data, contract, body, _ = approved
    with data[0].tx() as c:
        c.execute(delete(delivery_graph_requests).where(
            delivery_graph_requests.c.app_id == gate.entity(contract),
            delivery_graph_requests.c.kind == gate.SCOPE + "_seal"))
    before = records(data[0])
    with pytest.raises(DomainError):
        gate.approve(data[0], data[3], contract, body)
    assert records(data[0]) == before


def load_budget():
    try:
        from sim2act import natural_trial_budget
        return natural_trial_budget
    except ImportError:
        # Read-only dependency in the explicitly isolated parallel work package.
        # Root's combined tree takes the normal import branch after integration.
        path = Path('/workspace/Sim2Act-trial-budget-20261015/src/sim2act/natural_trial_budget.py')
        spec = importlib.util.spec_from_file_location("sim2act.natural_trial_budget", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module


def test_actual_mock_generated_app_stage_binding_and_cold_per_use(env, monkeypatch, tmp_path):
    budget = load_budget()
    budget_path = Path(budget.__file__)
    budget_hash = hashlib.sha256(budget_path.read_bytes()).hexdigest()
    data = setup(env)
    # Exact new fixture expiry accommodates seven real one-per-minute slots;
    # no existing approval, Run clock, 300s deadline or 30s lease is extended.
    contract, body = frozen(data, ttl=1200.0)
    gate.approve(data[0], data[3], contract, body)
    scope = budget.scope_for(contract, body.request_key)
    permits = []
    slot_ids = []
    raw_handle = httpx.MockTransport.handle_request
    fee = gate.SyntheticOnlyFeeAuthority(fingerprint(contract.model_dump()), contract.quota_subject)

    def admitted(*args):
        result = gate.admit(*args, fee_authority=fee)
        permits.append(result)
        return result

    def accountable(self, request):
        with data[0].tx() as c:
            active = c.execute(select(runs).where(runs.c.status == "RUNNING",
                runs.c.principal_id == data[3], runs.c.project_id == data[4])).mappings().one()
            actual = c.execute(select(attempts).where(attempts.c.run_id == active["id"],
                attempts.c.status == "STARTED")).mappings().one()
        stage = "generate" if active["runtime_id"] == contract.runtime_id else (
            "source" if active["resource_refs"] == [contract.bindings[0].resource_id] else "cold")
        reservation = budget.Reservation(request_key=actual["id"], stage=stage,
            run_id=active["id"], expected_version=active["version"], fence=active["fence"],
            wire_sha256=hashlib.sha256(request.content).hexdigest(), wire_bytes=len(request.content))
        receipt = budget.reserve(data[0], data[3], scope, contract, reservation, admission=admitted)
        assert receipt["dispatch_authorized"] is False
        # Fresh admission follows durable accounting before this offline fixture dispatch.
        with data[0].tx() as c:
            admitted(data[0], c, data[3], contract, body.request_key, stage,
                     active["id"], active["version"], active["fence"])
        response = raw_handle(self, request)
        raw, archive = response_archive(response.json())
        usage = normalize_usage(response.json())
        assert raw is not None and archive["status"] == "COMPLETE"
        settlement = budget.Settlement(request_key=actual["id"], response_sha256=archive["sha256"],
            response_ascii_bytes=archive["bytes"], **{k: usage["tokens"][k] for k in
                ("prompt_tokens", "completion_tokens", "total_tokens")})
        result = budget.settle(data[0], data[3], scope, contract, settlement, admission=admitted)
        assert result["ledger"]["slots"][-1]["accepted"] is True
        slot_ids.append(actual["id"])
        return response

    async def async_accountable(self, request):
        await request.aread()
        try:
            previous = budget.read(data[0], data[3], scope.model_dump())["ledger"]["last_reserved_at"]
        except DomainError as error:
            assert error.code == "VERSION_CONFLICT"
            previous = None
        # Actual wall time with a cancellation-cooperative transport. Deadline
        # and heartbeat mechanisms stay active; no fake clock or longer lease.
        while previous is not None and time.time() < previous + 60:
            await asyncio.sleep(min(0.5, previous + 60 - time.time()))
        return accountable(self, request)

    monkeypatch.setattr(httpx.MockTransport, "handle_async_request", async_accountable)
    generation, _, release, inst, sent = ready(data, style="ordered")
    assert len(sent) == 3
    job_id = enqueue(data, release, inst)
    reviewed = gate.stage_review(data[0], data[3], contract, body.request_key, "source", job_id)
    stage_body = gate.StageApproveInput(authority=gate.StageAuthority.model_validate(reviewed["authority"]),
        expected_authority_fingerprint=reviewed["authority_fingerprint"], approval_key=body.request_key,
        request_key="source-stage-consent",
        consent="BIND_ONLY_THIS_ACCEPTED_STAGE_RUN_APP_RELEASE_AND_COMPLETE_GOAL_TO_ORIGINAL_TRIAL")
    before = records(data[0])
    accepted = gate.approve_stage(data[0], data[3], contract, stage_body)
    assert accepted["live_allowed"] is False and accepted["authority"]["generation_run_id"] == generation
    assert gate.approve_stage(data[0], data[3], contract, stage_body) == accepted
    assert len(records(data[0])) == len(before) + 2
    observed = []

    def guard(request):
        with data[0].tx() as c:
            job = c.execute(select(runs).where(runs.c.id == job_id)).mappings().one()
        observed.append(permit(data, contract, body, job, stage="source"))
        history = gate.recover_stage(data[0], data[3], contract, body.request_key,
                                     "source", stage_body.request_key)
        assert history["request"] == stage_body.model_dump() and history["live_allowed"] is False
        return raw_handle(transport([], SOURCE), request)

    assert Worker(data[0], data[1], goal_planner_transport=httpx.MockTransport(guard)).once()
    assert data[2].get("/api/runs/" + job_id).json()["status"] == "SUCCEEDED"
    assert len(observed) == 2
    source_history = gate.recover_stage(data[0], data[3], contract, body.request_key,
                                        "source", stage_body.request_key)
    assert source_history["request"] == stage_body.model_dump()
    assert all(p.runtime_id == accepted["authority"]["runtime_id"]
               and p.stage_authority_fingerprint == reviewed["authority_fingerprint"] for p in observed)
    # The same saved app's exact new-material use is an existing, independently confirmed intent.
    target = contract.bindings[1]
    current = data[2].get("/api/internal/instances/" + inst["id"]).json()
    review = dict(expected_revision=current["revision"], expected_release_fingerprint=release["fingerprint"],
        expected_app_fingerprint=accepted["authority"]["candidate_fingerprint"],
        expected_recipe_fingerprint=accepted["authority"]["recipe_fingerprint"],
        resource_id=target.resource_id, card_id=target.card_id, expected_goal_version=target.goal_version,
        expected_goal_fingerprint=target.goal_fingerprint, expected_source_hash=target.source_hash,
        request_key=contract.stage_keys.cold)
    route = "/api/internal/instances/" + inst["id"]
    preview = data[2].post(route + "/pa-use-reviews", json=review)
    assert preview.status_code == 200, preview.text
    queued = data[2].post(route + "/pa-use-runs", json=dict(review=review,
        expected_review_fingerprint=preview.json()["review_fingerprint"], consent=use.PA_CONSENT))
    assert queued.status_code == 202, queued.text
    cold_id = queued.json()["run_id"]
    cold = gate.stage_review(data[0], data[3], contract, body.request_key, "cold", cold_id)
    consent = stage_body.model_copy(update=dict(authority=gate.StageAuthority.model_validate(cold["authority"]),
        expected_authority_fingerprint=cold["authority_fingerprint"], request_key="cold-stage-consent"))
    gate.approve_stage(data[0], data[3], contract, consent)
    old = records(data[0])
    altered = copy.deepcopy(consent.model_dump())
    altered["authority"]["release_fingerprint"] = "f" * 64
    altered["expected_authority_fingerprint"] = fingerprint(altered["authority"])
    with pytest.raises(DomainError):
        gate.approve_stage(data[0], data[3], contract, gate.StageApproveInput.model_validate(altered))
    assert records(data[0]) == old
    cold_permits = []

    def cold_guard(request):
        with data[0].tx() as c:
            job = c.execute(select(runs).where(runs.c.id == cold_id)).mappings().one()
        cold_permits.append(permit(data, contract, body, job, stage="cold"))
        return raw_handle(transport([], COLD), request)

    assert Worker(data[0], data[1], goal_planner_transport=httpx.MockTransport(cold_guard)).once()
    assert data[2].get("/api/runs/" + cold_id).json()["status"] == "SUCCEEDED"
    assert len(cold_permits) == 2
    saved_before = records(data[0])
    history = gate.recover_stage(data[0], data[3], contract, body.request_key, "cold", consent.request_key)
    assert history["request"] == consent.model_dump() and history["dispatch_authorized"] is False
    with pytest.raises(DomainError):
        gate.recover_stage(data[0], data[3], contract, body.request_key, "cold", "another-consent")
    assert records(data[0]) == saved_before
    accounting = budget.read(data[0], data[3], scope.model_dump())
    assert accounting["reserved_requests"] == 7 and accounting["usage_status"] == "KNOWN"
    assert accounting["ledger"]["stage_runs"] == dict(generate=generation, source=job_id, cold=cold_id)
    assert len(set(slot_ids)) == 7 and {p.stage for p in permits} == {"generate", "source", "cold"}
    assert hashlib.sha256(budget_path.read_bytes()).hexdigest() == budget_hash
    (tmp_path / "actual-combined-admission-budget.json").write_text(json.dumps(dict(
        admission_path=gate.__file__, admission_sha256=hashlib.sha256(Path(gate.__file__).read_bytes()).hexdigest(),
        budget_path=str(budget_path), budget_sha256=budget_hash, slot_ids=slot_ids,
        permits=[p.model_dump() for p in permits], accounting=accounting), indent=2))
    # Stage authority cannot follow another Release/revision after the immutable approval.
    with data[0].tx() as c:
        c.execute(update(internal_instances).where(internal_instances.c.id == inst["id"])
                  .values(revision=current["revision"] + 1))
    with pytest.raises(DomainError):
        gate.approve_stage(data[0], data[3], contract, consent)
    assert gate.recover_stage(data[0], data[3], contract, body.request_key,
                             "cold", consent.request_key)["request"] == consent.model_dump()
    with data[0].tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == contract.bindings[1].resource_id)
                  .values(revoked=True))
    with pytest.raises(DomainError) as revoked:
        gate.recover_stage(data[0], data[3], contract, body.request_key, "cold", consent.request_key)
    assert revoked.value.code == "GRANT_REVOKED"
    data[2].close()


def test_preexisting_confirmed_generate_cannot_be_adopted_into_new_trial(env):
    data = setup(env)
    _, _, release, inst, _ = ready(data)
    contract, body = frozen(data)
    gate.approve(data[0], data[3], contract, body)
    source = enqueue(data, release, inst)
    before = records(data[0])
    with pytest.raises(DomainError, match="accepted under this precise trial"):
        gate.stage_review(data[0], data[3], contract, body.request_key, "source", source)
    assert records(data[0]) == before
    data[2].close()
