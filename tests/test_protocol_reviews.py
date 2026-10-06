"""Real zero-network worker evidence reviewed by separate pinned synthetic oracles."""

import copy
import json
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import func, select, update
from test_protocol_http import NoProvider, envelope

from sim2act.contracts import Limits
from sim2act.db import fingerprint, grants, principals, protocol_jobs, protocol_reviews, runs
from sim2act.errors import DomainError
from sim2act.model import InternModel
from sim2act.model_budget import BudgetedProvider, initialize_ledger
from sim2act.protocol_api import ProtocolAttemptRunner
from sim2act.protocol_jobs import enqueue
from sim2act.protocol_reviews import (
    PINS,
    ReviewInput,
    contract_snapshot,
    evaluation_contract,
    freeze_contract,
    review,
    source_proof,
)
from sim2act.worker import Worker

CONTRACT = "protocol.synthetic.a-source.v1"
MATERIAL = (
    Path(__file__).resolve().parents[1]
    / "docs/evidence/model-protocol-preparation-20261006/materials/a-source/policy.txt"
)


def prepared(env, tmp_path, *, output=None, inputs=None):
    contract, _ = evaluation_contract(CONTRACT)
    output = contract["expected_output"] if output is None else output
    client, pid = env[2], env[5]
    resource = client.post(
        f"/api/projects/{pid}/resources",
        json={"name": "independent-source.txt", "format": "txt", "content": MATERIAL.read_text()},
    ).json()["id"]
    payload = {
        "goal": contract["public_goal"],
        "inputs": contract["expected_inputs"] if inputs is None else inputs,
        "resource_ids": [resource],
        "contract_id": CONTRACT,
    }
    limits = Limits(**{k: getattr(env[1], k) for k in Limits.model_fields})
    accepted = enqueue(env[0], env[3], pid, "source", payload, "review-source", limits)
    seen = []

    def factory(worker, run, snapshot):
        scope = snapshot["scope"]
        path = tmp_path / "review-provider.json"
        initialize_ledger(path, scope)
        replies = [envelope(resource=resource), envelope(output)]
        ticks = [1000.0]

        def respond(request):
            seen.append(json.loads(request.content))
            ticks[0] += 6
            return httpx.Response(200, json=replies.pop(0))

        model = InternModel(
            replace(env[1], live_enabled=True, token="OFFLINE_REVIEW_FAKE"),
            httpx.MockTransport(respond),
        )

        def authorize(_):
            with env[0].tx() as c:
                env[0].guard(c, run["id"], run["fence"])
                env[0].authorize(c, env[3], run["runtime_id"], pid, resource, "resource.read")
            return True

        provider = BudgetedProvider(
            model, path, scope, "source_a", authorize=authorize, clock=lambda: ticks[0]
        )
        return ProtocolAttemptRunner(worker, run, snapshot, provider)

    assert Worker(env[0], env[1], NoProvider(), protocol_runner_factory=factory).once()
    rid = accepted["run_id"]
    with env[0].tx() as c:
        run = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        job = c.execute(select(protocol_jobs).where(protocol_jobs.c.run_id == rid)).mappings().one()
        assert run["status"] == "WAITING_APPROVAL", run["error"]
        body = {
            "contract_id": CONTRACT,
            "expected_result_fingerprint": job["result_fingerprint"],
            "expected_fence": run["fence"],
            "expected_version": run["version"],
            "request_key": "review",
        }
    return rid, body, resource, seen


def test_real_pending_exact_oracle_atomic_success_cold_proof_and_no_runtime_gold(env, tmp_path):
    rid, body, _, sent = prepared(env, tmp_path)
    with env[0].tx() as c:
        before = dict(
            c.execute(select(protocol_jobs).where(protocol_jobs.c.run_id == rid)).mappings().one()
        )
        rights = [dict(r) for r in c.execute(select(grants)).mappings()]
        identities = c.execute(select(func.count()).select_from(principals)).scalar_one()
        with pytest.raises(DomainError):
            source_proof(env[0], c, env[3], rid)
    made = review(env[0], env[3], rid, body)
    assert made["decision"] == "PASS"
    assert review(env[0], env[3], rid, body) == made
    with env[0].tx() as c:
        run = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        after = dict(
            c.execute(select(protocol_jobs).where(protocol_jobs.c.run_id == rid)).mappings().one()
        )
        assert run["status"] == "SUCCEEDED" and run["version"] == body["expected_version"] + 1
        assert before == after and run["result"] == before["result_snapshot"]
        proof = source_proof(env[0], c, env[3], rid)
        assert proof["semantic_status"] == "PASS"
        assert proof["output_fingerprint"] == fingerprint(
            before["result_snapshot"]["protocol_result"]["evidence"]["output"]
        )
        assert rights == [dict(r) for r in c.execute(select(grants)).mappings()]
        assert identities == c.execute(select(func.count()).select_from(principals)).scalar_one()
    # The fake response contains expected output; only actual request messages are audited.
    wire = json.dumps(sent)
    assert "gold_sha256" not in wire and "expected_output" not in wire
    assert "exact-json-semantic" not in wire and "rubric" not in wire
    assert evaluation_contract(CONTRACT)[0]["expected_output"] not in sent


def test_wrong_output_persists_failure_never_promotes_source(env, tmp_path):
    rid, body, _, _ = prepared(env, tmp_path, output={"may_submit_now": True})
    result = review(env[0], env[3], rid, body)
    assert result["decision"] == "FAIL"
    assert review(env[0], env[3], rid, body) == result
    with env[0].tx() as c:
        assert (
            c.execute(select(runs.c.status).where(runs.c.id == rid)).scalar_one()
            == "WAITING_APPROVAL"
        )
        with pytest.raises(DomainError):
            source_proof(env[0], c, env[3], rid)


@pytest.mark.parametrize(
    "change", ["owner", "contract", "fence", "version", "result", "key_binding"]
)
def test_owner_exact_acceptance_and_idempotency_boundaries(env, tmp_path, change):
    rid, body, _, _ = prepared(env, tmp_path)
    who = env[4] if change == "owner" else env[3]
    if change == "contract":
        body["contract_id"] = "protocol.synthetic.a-cold.v1"
    elif change in {"fence", "version"}:
        body["expected_" + change] += 1
    elif change == "result":
        body["expected_result_fingerprint"] = "0" * 64
    elif change == "key_binding":
        review(env[0], who, rid, body)
        body["expected_fence"] += 1
    with pytest.raises(DomainError):
        review(env[0], who, rid, body)


@pytest.mark.parametrize("state", ["PARTIAL", "FAILED", "UNKNOWN", "RUNNING", "CANCELLED"])
def test_old_or_ineligible_state_cannot_be_promoted(env, tmp_path, state):
    rid, body, _, _ = prepared(env, tmp_path)
    with env[0].tx() as c:
        c.execute(update(runs).where(runs.c.id == rid).values(status=state))
    with pytest.raises(DomainError):
        review(env[0], env[3], rid, body)
    with env[0].tx() as c:
        assert c.execute(select(runs.c.status).where(runs.c.id == rid)).scalar_one() == state


@pytest.mark.parametrize(
    "change", ["grant", "fence", "output", "proof", "checker", "evaluator", "extra"]
)
def test_persisted_pass_cannot_bypass_current_authority_or_rehash_tampering(env, tmp_path, change):
    rid, body, resource, _ = prepared(env, tmp_path)
    review(env[0], env[3], rid, body)
    with env[0].tx() as c:
        if change == "grant":
            c.execute(update(grants).where(grants.c.resource_id == resource).values(revoked=True))
        elif change == "fence":
            c.execute(update(runs).where(runs.c.id == rid).values(fence=body["expected_fence"] + 1))
        elif change == "output":
            job = (
                c.execute(select(protocol_jobs).where(protocol_jobs.c.run_id == rid))
                .mappings()
                .one()
            )
            value = copy.deepcopy(job["result_snapshot"])
            value["protocol_result"]["evidence"]["output"] = {"decision": "PASS"}
            c.execute(
                update(protocol_jobs)
                .where(protocol_jobs.c.run_id == rid)
                .values(result_snapshot=value, result_fingerprint=fingerprint(value))
            )
            c.execute(update(runs).where(runs.c.id == rid).values(result=value))
        else:
            row = (
                c.execute(select(protocol_reviews).where(protocol_reviews.c.run_id == rid))
                .mappings()
                .one()
            )
            payload = copy.deepcopy(row["payload"])
            if change == "proof":
                payload["verification"]["output_fingerprint"] = "0" * 64
            elif change == "checker":
                payload["checker"] = "caller-PASS"
            elif change == "evaluator":
                payload["evaluator"] = env[4]
            else:
                payload["gold"] = {}
            c.execute(
                update(protocol_reviews)
                .where(protocol_reviews.c.id == row["id"])
                .values(payload=payload, fingerprint=fingerprint(payload))
            )
    with env[0].tx() as c, pytest.raises(DomainError):
        source_proof(env[0], c, env[3], rid)


@pytest.mark.parametrize("field", ["PASS", "decision", "gold", "checker", "verification", "output"])
def test_closed_review_request_has_no_caller_semantics_or_code(field):
    body = {
        "contract_id": CONTRACT,
        "expected_result_fingerprint": "a" * 64,
        "expected_fence": 1,
        "expected_version": 1,
        "request_key": "key",
        field: "PASS",
    }
    with pytest.raises(ValidationError):
        ReviewInput.model_validate(body)


def test_all_private_registry_assets_versioned_public_shapes_without_expected_values():
    for contract_id in PINS:
        private, _ = evaluation_contract(contract_id)
        public = contract_snapshot(contract_id)
        assert public["checker"] == "exact-json-semantic.v1" and public["version"] == 1
        assert "expected_output" not in public and "gold" not in public
        assert (
            freeze_contract(
                contract_id,
                "source",
                private["public_goal"],
                [{"content_hash": h} for h in private["resource_hashes"]],
            )
            == public
        )
    with pytest.raises(DomainError):
        evaluation_contract("../../arbitrary-gold")
    with pytest.raises(DomainError):
        freeze_contract(CONTRACT, "source", "different goal", [{"content_hash": "0" * 64}])


def test_concurrent_identical_review_has_one_persisted_acceptance(env, tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    rid, body, _, _ = prepared(env, tmp_path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: review(env[0], env[3], rid, body), range(2)))
    assert outcomes[0] == outcomes[1]
    with env[0].tx() as c:
        assert (
            c.execute(
                select(func.count())
                .select_from(protocol_reviews)
                .where(protocol_reviews.c.run_id == rid)
            ).scalar_one()
            == 1
        )
        assert (
            c.execute(select(runs.c.version).where(runs.c.id == rid)).scalar_one()
            == body["expected_version"] + 1
        )


@pytest.mark.parametrize(
    "mutation",
    [{"status": "CANCELLED"}, {"cancel_intent": True}, {"error": {"code": "OUTCOME_UNKNOWN"}}],
)
def test_cached_pass_is_not_returned_for_changed_terminal_state(env, tmp_path, mutation):
    rid, body, _, _ = prepared(env, tmp_path)
    review(env[0], env[3], rid, body)
    with env[0].tx() as c:
        c.execute(update(runs).where(runs.c.id == rid).values(**mutation))
    with pytest.raises(DomainError):
        review(env[0], env[3], rid, body)


def test_registry_asset_changed_does_not_accept_caller_replacement(tmp_path, monkeypatch):
    from sim2act import protocol_reviews as module

    name, _ = PINS[CONTRACT]
    contract, _ = evaluation_contract(CONTRACT)
    contract["expected_output"] = {"decision": "PASS"}
    (tmp_path / name).write_text(json.dumps(contract))
    monkeypatch.setattr(module, "ASSETS", tmp_path)
    with pytest.raises(DomainError, match="asset changed"):
        evaluation_contract(CONTRACT)


@pytest.mark.parametrize("field", ["expected_fence", "expected_version"])
def test_boolean_does_not_coerce_into_review_version(field):
    body = {
        "contract_id": CONTRACT,
        "expected_result_fingerprint": "a" * 64,
        "expected_fence": 1,
        "expected_version": 1,
        "request_key": "key",
        field: True,
    }
    with pytest.raises(ValidationError):
        ReviewInput.model_validate(body)


@pytest.mark.parametrize(
    "change", ["fence_bool", "contract_bool", "request_bool", "request_extra", "reason"]
)
def test_rehashed_stored_review_is_bound_to_strict_canonical_record_and_event(
    env, tmp_path, change
):
    rid, body, _, _ = prepared(env, tmp_path)
    review(env[0], env[3], rid, body)
    with env[0].tx() as c:
        row = (
            c.execute(select(protocol_reviews).where(protocol_reviews.c.run_id == rid))
            .mappings()
            .one()
        )
        payload = copy.deepcopy(row["payload"])
        if change == "fence_bool":
            payload["completed_fence"] = True
        elif change == "contract_bool":
            payload["contract_version"] = True
        elif change == "request_bool":
            payload["request"]["expected_fence"] = True
        elif change == "request_extra":
            payload["request"]["gold"] = "PASS"
        else:
            payload["reason"] = "caller says PASS"
        c.execute(
            update(protocol_reviews)
            .where(protocol_reviews.c.id == row["id"])
            .values(payload=payload, fingerprint=fingerprint(payload))
        )
    with pytest.raises(DomainError):
        review(env[0], env[3], rid, body)
    with env[0].tx() as c, pytest.raises(DomainError):
        source_proof(env[0], c, env[3], rid)
