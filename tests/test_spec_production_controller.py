"""Isolated production-branch wiring, never real service authority or IO.

Only these tests replace the fixed source, software qualification and production
environment check. Actual Store/Worker/controllers/ledger remain in use. The
real HTTP transport methods raise; only a finite MockTransport receives bodies.
"""

import base64
import json
import traceback
from dataclasses import replace

import httpx
import pytest
import test_natural_spec_apps as apps
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from test_production_trial_stages import approve_stage, prepare
from test_spec_app_operations import snapshot

from sim2act import pb_natural_uses as use
from sim2act import production_evidence as evidence
from sim2act import production_trial_admission as admission
from sim2act import production_trial_policy as policy
from sim2act import spec_production as controller
from sim2act.api import create_app
from sim2act.db import attempts, fingerprint, runs
from sim2act.errors import DomainError
from sim2act.worker import Worker


@pytest.fixture(autouse=True)
def no_real_http(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Real HTTP forbidden in SPEC controller qualification")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", denied)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", denied)


@pytest.fixture(autouse=True)
def save_closed_state(env, tmp_path):
    yield
    (tmp_path / "closed-state.json").write_text(json.dumps(snapshot(env[0]), indent=2, default=str) + "\n")


def test_default_closed_and_missing_fixed_source_before_claim(env, tmp_path, monkeypatch):
    data, old = prepare(env, tmp_path)
    binding = controller.ProductionTrialBinding(old.contract, old.approval_key, old.account_id)
    before = snapshot(data[0])
    with pytest.raises(DomainError, match="disabled"):
        Worker(data[0], data[1], pa_trial=binding)
    # Isolated eligibility substitution only; the actual fixed resolver still
    # rejects. No source/ALLOW is passed into a production constructor or DTO.
    monkeypatch.setattr(controller, "environment", lambda *args: None)
    with pytest.raises(DomainError) as error:
        Worker(data[0], data[1], pa_trial=binding)
    assert error.value.code == "LIVE_BLOCKED"
    assert snapshot(data[0]) == before


def configured(env, tmp_path, monkeypatch, *, revoke_received=False):
    data, old = prepare(env, tmp_path)
    settings = replace(data[1], mode="live", live_enabled=True,
        application_generation_activation_enabled=True, token="isolated-noncredential-placeholder")
    client = TestClient(create_app(data[0], settings))
    client.headers["Authorization"] = "Bearer synthetic-test-A"
    data = (data[0], settings, client, *data[3:])
    binding = controller.ProductionTrialBinding(old.contract, old.approval_key, old.account_id)
    fixture = dict(revoked=False, sends=[], workers=[], transport=None, source_reads=0)

    def environment(store, selected, transport):
        assert store is data[0] and store.test_only and store.sqlite
        assert selected.mode == "live" and selected.live_enabled is True
        assert selected.application_generation_activation_enabled is True and transport is None

    def source(user, contract, key):
        assert user == data[3] and key == binding.approval_key
        scope = evidence.requirements_for(user, contract, key)
        fixture["source_reads"] += 1
        return policy.SourceVerificationResult(
            requirements_fingerprint=fingerprint(scope.model_dump()), account_id=binding.account_id,
            quota_subject=scope.quota_subject, provider=scope.provider, model=scope.model,
            endpoint=scope.endpoint, evidence_fingerprint="a" * 64,
            decision="DENY" if fixture["revoked"] else "ALLOW",
            legal_free_entitlement=not fixture["revoked"],
            enforced_non_chargeable=not fixture["revoked"], revoked=fixture["revoked"],
            observed_at=contract.prepared_at, expires_at=contract.expires_at)

    monkeypatch.setattr(controller, "environment", environment)
    monkeypatch.setattr(evidence, "resolve_account", source)
    monkeypatch.setattr(admission, "_qualified", lambda: None)
    from sim2act import natural_spec_runtime as runtime
    original_fail = runtime.fail_owned
    def record_failure(worker, run, error):
        with (tmp_path / "failure-observations.jsonl").open("a") as stream:
            stream.write(json.dumps(dict(run_id=run["id"], error=error.public(),
                traceback=traceback.format_exception(error))) + "\n")
        return original_fail(worker, run, error)
    monkeypatch.setattr(runtime, "fail_owned", record_failure)
    original_async = httpx.AsyncClient

    def synthetic_client(*args, **kwargs):
        assert kwargs.get("transport") is None
        assert type(fixture["transport"]) is httpx.MockTransport
        return original_async(*args, **{**kwargs, "transport": fixture["transport"]})

    monkeypatch.setattr(httpx, "AsyncClient", synthetic_client)

    def factory(*args, **kwargs):
        transport = kwargs.pop("goal_planner_transport")
        def receive(request):
            fixture["sends"].append(json.loads(request.content))
            response = transport.handler(request)
            with (tmp_path / "mock-exchanges.jsonl").open("a") as stream:
                stream.write(json.dumps(dict(classification="SYNTHETIC_MOCK_TRANSPORT_NOT_REAL_HTTP",
                    request_b64=base64.b64encode(request.content).decode(),
                    response_b64=base64.b64encode(response.content).decode(),
                    status=response.status_code)) + "\n")
            if revoke_received:
                fixture["revoked"] = True
            return response
        fixture["transport"] = httpx.MockTransport(receive)
        worker = Worker(*args, **kwargs, pa_trial=binding)
        fixture["workers"].append(worker)
        return worker

    monkeypatch.setattr(apps, "Worker", factory)
    return data, binding, fixture, factory


def test_live_shaped_spec_generation_source_and_cold_existing_controller(env, tmp_path, monkeypatch):
    data, binding, fixture, factory = configured(env, tmp_path, monkeypatch)
    generation, app, release, inst, sent = apps.ready(data, style="ordered")
    source_id = apps.enqueue(data, release, inst)
    reviewed, _ = approve_stage(data, binding, "source", source_id)
    assert factory(data[0], data[1], goal_planner_transport=apps.transport([])).once()
    source = apps.inspect(data, inst, source_id)
    assert source.status_code == 200 and source.json()["status"] == "SUCCEEDED", source.text
    target = binding.contract.bindings[1]
    fresh = data[2].get("/api/internal/instances/" + inst["id"]).json()
    review = dict(expected_revision=fresh["revision"],
        expected_release_fingerprint=release["fingerprint"],
        expected_app_fingerprint=reviewed["authority"]["candidate_fingerprint"],
        expected_recipe_fingerprint=reviewed["authority"]["recipe_fingerprint"],
        resource_id=target.resource_id, card_id=target.card_id,
        expected_goal_version=target.goal_version, expected_goal_fingerprint=target.goal_fingerprint,
        expected_source_hash=target.source_hash, request_key=binding.contract.stage_keys.cold)
    route = "/api/internal/instances/" + inst["id"]
    preview = data[2].post(route + "/pa-use-reviews", json=review)
    assert preview.status_code == 200, preview.text
    queued = data[2].post(route + "/pa-use-runs", json=dict(review=review,
        expected_review_fingerprint=preview.json()["review_fingerprint"],
        consent=use.PA_CONSENT))
    assert queued.status_code == 202, queued.text
    cold_id = queued.json()["run_id"]
    approve_stage(data, binding, "cold", cold_id)
    assert factory(data[0], data[1], goal_planner_transport=apps.transport([], apps.COLD)).once()
    result = apps.inspect(data, inst, cold_id)
    assert result.status_code == 200 and result.json()["status"] == "SUCCEEDED", result.text
    assert len(fixture["sends"]) == 7 and fixture["source_reads"] > 7
    with data[0].tx() as c:
        rows = c.execute(select(attempts).where(attempts.c.run_id.in_([generation, source_id, cold_id]))).mappings().all()
        assert len(rows) == 7 and all(row["mode"] == "LIVE" for row in rows)
        assert all(row["parameters"]["pa_trial_binding"]["version"] == controller.VERSION for row in rows)
        from sim2act.db import delivery_graph_requests
        from sim2act.natural_source_archives import REQUEST, RESPONSE
        from sim2act.production_trial_sender import CAPTURE
        archives = c.execute(select(delivery_graph_requests.c.snapshot).where(
            delivery_graph_requests.c.kind.in_([CAPTURE, CAPTURE + "_seal",
                REQUEST, REQUEST + "_seal", RESPONSE, RESPONSE + "_seal"]))).scalars().all()
        assert len(archives) == 30
        assert all(row["response"]["provenance"] == "SPEC_PRODUCTION_CONTROLLER" for row in archives)
    (tmp_path / "controller-proof.json").write_text(json.dumps(dict(
        generation=generation, source=source_id, cold=cold_id, result=result.json(),
        source_reads=fixture["source_reads"], requests=len(fixture["sends"]),
        workers=[w.id for w in fixture["workers"]], classification="ISOLATED_FAKE_APPROVAL_NOT_LIVE_AUTHORITY"),
        indent=2) + "\n")
    data[2].close()


def test_production_binding_cannot_enter_either_public_offline_sender(env, tmp_path, monkeypatch):
    from sim2act import production_trial_sender as sender
    data, binding, fixture, _ = configured(env, tmp_path, monkeypatch)
    # Even a coincidentally matching old synthetic header cannot select its path.
    settings = replace(data[1], token="synthetic-offline-planner")
    worker = Worker(data[0], settings, pa_trial=binding)
    before, reads, sql = snapshot(data[0]), fixture["source_reads"], []
    def observed(*args):
        sql.append(True)
    event.listen(data[0].engine, "before_cursor_execute", observed)
    try:
        for dispatch in (sender.dispatch_offline, sender.dispatch_from_source_offline):
            args = (None,) if dispatch is sender.dispatch_offline else ()
            with pytest.raises(DomainError) as error:
                dispatch(worker, None, None, None, b"", *args, expected_revision=0)
            assert error.value.code == "LIVE_BLOCKED"
    finally:
        event.remove(data[0].engine, "before_cursor_execute", observed)
    assert sql == [] and fixture["source_reads"] == reads and fixture["sends"] == []
    assert snapshot(data[0]) == before
    data[2].close()


def test_received_body_and_usage_survive_source_revocation(env, tmp_path, monkeypatch):
    data, binding, fixture, factory = configured(env, tmp_path, monkeypatch, revoke_received=True)
    with pytest.raises(AssertionError):
        # The original helper requires a successful candidate; source is revoked
        # by the synthetic handler before reception. No second send may follow.
        apps.generate(data, style="ordered")
    assert len(fixture["sends"]) == 1
    with data[0].tx() as c:
        rows = c.execute(select(attempts)).mappings().all()
        assert len(rows) == 1 and rows[0]["mode"] == "LIVE"
        assert rows[0]["usage"]["status"] == "known"
        from sim2act.production_trial_journal import read
    state = read(data[0], data[3], binding.contract, binding.approval_key, binding.account_id)
    assert state.ledger.halted and len(state.ledger.slots) == 1
    assert state.ledger.slots[0].settlement is not None and not state.ledger.slots[0].accepted
    assert state.ledger.slots[0].settlement.total_tokens is not None
    from sim2act.db import delivery_graph_requests
    from sim2act.production_trial_sender import CAPTURE
    with data[0].tx() as c:
        captures = c.execute(select(delivery_graph_requests).where(
            delivery_graph_requests.c.kind.in_([CAPTURE, CAPTURE + "_seal"]))).mappings().all()
        assert len(captures) == 2
        payload = captures[0]["snapshot"]["response"]
        assert payload == captures[1]["snapshot"]["response"]
        assert payload["outcome"]["response_sha256"] == state.ledger.slots[0].settlement.response_sha256
        assert payload["provenance"] == "SPEC_PRODUCTION_CONTROLLER"
        body = base64.b64decode(payload["body_b64"], validate=True)
        assert body and payload["raw_bytes"] == len(body)
    with data[0].tx() as c:
        job = c.execute(select(runs)).mappings().one()
        assert job["status"] != "SUCCEEDED" and job["result"] is None
    data[2].close()
