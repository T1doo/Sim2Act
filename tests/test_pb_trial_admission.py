"""Synthetic SQLite admission proofs; no real HTTP, fee or account probing."""

import asyncio
import copy
import hashlib
import json
import time
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select, update
from test_natural_live_admission import frozen, load_budget, records
from test_natural_spec_apps import COLD, SOURCE, enqueue, ready, recipe, setup, transport
from test_pa_spec_apps import instance

from sim2act import natural_live_admission as gate
from sim2act import natural_specs as natural
from sim2act import pb_natural_specs as pb
from sim2act.db import (
    attempts,
    fingerprint,
    grants,
    internal_instances,
    runs,
)
from sim2act.errors import DomainError
from sim2act.goal_applications import response_archive
from sim2act.model import normalize_usage
from sim2act.worker import Worker


def test_pb_exact_same_trial_source_extraction_and_cold_seven_slots(env, monkeypatch, tmp_path):
    budget = load_budget()
    budget_path = Path(budget.__file__)
    budget_hash = hashlib.sha256(budget_path.read_bytes()).hexdigest()
    data = setup(env)
    # Exact new fixture expiry accommodates seven real one-per-minute slots;
    # no existing approval, Run clock, 300s deadline or 30s lease is extended.
    pa, body = frozen(data, ttl=1200.0)
    contract = gate.PBTrialContract(**pa.model_dump(), path="P-B",
        extraction_request_key="exact-pb-extraction", extraction_recipe=recipe("ordered"))
    body = body.model_copy(update={"expected_contract_fingerprint": fingerprint(contract.model_dump())})
    gate.approve(data[0], data[3], contract, body)
    scope = budget.scope_for(contract, body.request_key)
    permits = []
    fresh_permits = []
    slot_ids = []
    raw_handle = httpx.MockTransport.handle_request
    fee = gate.SyntheticOnlyFeeAuthority(fingerprint(contract.model_dump()), contract.quota_subject)

    def event(kind, **public):
        with (tmp_path / "settlement-events.jsonl").open("a") as stream:
            stream.write(json.dumps(dict(event=kind, at=time.time(), **public)) + "\n")

    def admitted(*args):
        identity = dict(stage=args[5], run_id=args[6], version=args[7], fence=args[8])
        started = time.time()
        try:
            result = gate.admit(*args, fee_authority=fee)
        except DomainError as error:
            event("admission_refused", **identity, elapsed=time.time() - started,
                  error=error.public())
            raise
        event("admission_returned", **identity, elapsed=time.time() - started,
              permit=result.model_dump())
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
            fresh_permits.append(admitted(data[0], c, data[3], contract, body.request_key, stage,
                                          active["id"], active["version"], active["fence"]))
        response = raw_handle(self, request)
        raw, archive = response_archive(response.json())
        usage = normalize_usage(response.json())
        assert raw is not None and archive["status"] == "COMPLETE"
        settlement = budget.Settlement(request_key=actual["id"], response_sha256=archive["sha256"],
            response_ascii_bytes=archive["bytes"], **{k: usage["tokens"][k] for k in
                ("prompt_tokens", "completion_tokens", "total_tokens")})
        result = budget.settle(data[0], data[3], scope, contract, settlement, admission=admitted)
        event("settlement_returned", stage=stage, run_id=active["id"],
              version=active["version"], fence=active["fence"], result=result)
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
        observed.append(fresh_permits[-1])
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
    target = contract.bindings[1]
    path = f"/api/projects/{data[4]}/natural-spec-task-runs/{job_id}"
    options = data[2].get(path + "/extraction-options").json()
    review = dict(source_run_id=job_id,
        expected_source_proof_fingerprint=options["source_proof_fingerprint"],
        expected_source_recipe_fingerprint=options["recipe_fingerprint"],
        card_id=target.card_id, expected_goal_version=target.goal_version,
        expected_goal_fingerprint=target.goal_fingerprint, expected_source_hash=target.source_hash,
        recipe=contract.extraction_recipe.model_dump(exclude_none=True), name="Exact trial P-B",
        request_key=contract.extraction_request_key)
    preview = data[2].post(path + "/extraction-reviews", json=review)
    assert preview.status_code == 200, preview.text
    made = data[2].post(path + "/extractions", json=dict(review=review,
        expected_review_fingerprint=preview.json()["review_fingerprint"],
        consent=pb.CONSENT, artifact_write_consent=natural.CONSENT))
    assert made.status_code == 201, made.text
    release, inst = instance(data, made.json()["id"])
    current = data[2].get("/api/internal/instances/" + inst["id"]).json()
    cold_id = enqueue(data, release, inst, key=contract.stage_keys.cold)
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
        cold_permits.append(fresh_permits[-1])
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

