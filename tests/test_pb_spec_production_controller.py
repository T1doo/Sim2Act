"""Actual P-B controller with finite MockTransport; no real account/model facts."""

import copy
import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest
import test_natural_spec_apps as apps
from fastapi.testclient import TestClient
from sqlalchemy import event, select, update
from test_natural_live_admission import frozen
from test_pb_trial_dispatch import approve_stage, failure_trace
from test_spec_app_operations import snapshot
from test_spec_production_controller import configured
from test_spec_production_controller import no_real_http as no_real_http

from sim2act import natural_live_admission as gate
from sim2act import natural_source_archives as archive
from sim2act import natural_spec_runtime as runtime
from sim2act import natural_specs as natural
from sim2act import pa_trial_dispatch as trial
from sim2act import pb_natural_specs as pb
from sim2act import pb_natural_uses as use
from sim2act import production_trial_admission as admission
from sim2act import production_trial_journal as journal
from sim2act import spec_production as controller
from sim2act.api import create_app
from sim2act.db import Store, attempts, delivery_graph_requests, fingerprint
from sim2act.errors import DomainError
from sim2act.worker import Worker


@pytest.fixture(autouse=True)
def observe_original_lease_failures(monkeypatch, tmp_path):
    heartbeat, guard = Store.heartbeat, Store.guard
    observation_failures = []

    def record(kind, **fields):
        try:
            with (tmp_path / "lease-observations.jsonl").open("a") as stream:
                stream.write(json.dumps(dict(at=time.time(), kind=kind, **fields)) + "\n")
        except (OSError, ValueError, TypeError) as error:
            observation_failures.append(type(error).__name__)

    def observed_heartbeat(*args, **kwargs):
        try:
            result = heartbeat(*args, **kwargs)
        except Exception as error:
            record("original_heartbeat_error", type=type(error).__name__,
                sqlite_errorcode=getattr(getattr(error, "orig", None), "sqlite_errorcode", None),
                trace=failure_trace(error, guard_code=guard.__code__))
            raise
        record("original_heartbeat_return", run_id=args[2] if len(args) > 2 else None, returned=result)
        return result

    def observed_guard(*args, **kwargs):
        try:
            return guard(*args, **kwargs)
        except DomainError as error:
            record("original_guard_error", error=error.public(),
                trace=failure_trace(error, guard_code=guard.__code__))
            raise

    monkeypatch.setattr(Store, "heartbeat", observed_heartbeat)
    monkeypatch.setattr(Store, "guard", observed_guard)
    yield
    assert observation_failures == [], "Passive observer IO failed independently of the original heartbeat"


def prepare_pb(env, out):
    data = apps.setup(env)
    account = "synthetic-pb-production-shape"
    subject = admission.canonical_quota_subject(account)
    data = (data[0], replace(data[1], quota_subject=subject), *data[2:])
    data[0].initialize(quota_subject=subject)
    original, consent = frozen(data, ttl=1800)
    contract = gate.PBTrialContract(**(original.model_dump() | dict(quota_subject=subject,
        caps=gate.SQLiteSettlementCaps().model_dump())),
        path="P-B", extraction_request_key="original-pb-production-extraction",
        extraction_recipe=apps.recipe("ordered"))
    consent = consent.model_copy(update=dict(expected_contract_fingerprint=fingerprint(contract.model_dump())))
    gate.approve(data[0], data[3], contract, consent)
    return data, SimpleNamespace(contract=contract, approval_key=consent.request_key, account_id=account)


def test_pb_production_default_source_configuration_stays_closed(env, tmp_path, monkeypatch):
    data, selected = prepare_pb(env, tmp_path)
    binding = controller.ProductionTrialBinding(selected.contract, selected.approval_key, selected.account_id)
    before = snapshot(data[0])
    with pytest.raises(DomainError, match="disabled"):
        Worker(data[0], data[1], pa_trial=binding)
    with pytest.raises(DomainError):
        trial.JournalTrialBinding(selected.contract, selected.approval_key, selected.account_id)
    monkeypatch.setattr(controller, "environment", lambda *args: None)
    with pytest.raises(DomainError, match="Configured Intern credential missing"):
        Worker(data[0], data[1], pa_trial=binding)
    admission._qualified()
    assert snapshot(data[0]) == before
    (tmp_path / "default-boundaries.json").write_text(json.dumps(dict(
        missing_source="LIVE_BLOCKED", software="QUALIFIED", changed_tables=0,
        real_models=0, live_authorized=False), indent=2))
    data[2].close()


def test_pb_production_account_checks_reuse_the_extraction_transaction(env, tmp_path, monkeypatch):
    data, binding, fixture, factory = configured(env, tmp_path, monkeypatch, prepare_case=prepare_pb)
    worker = factory(data[0], data[1], goal_planner_transport=httpx.MockTransport(
        lambda request: pytest.fail("Account checks must not send")))
    before = snapshot(data[0])
    with data[0].tx() as c:
        def deny_nested_transaction(*args, **kwargs):
            raise AssertionError("Account verification must use the original extraction connection")
        with monkeypatch.context() as patch:
            patch.setattr(data[0], "tx", deny_nested_transaction)
            first = trial._account(worker, binding, connection=c)
            second = trial._account(worker, binding, connection=c)
            assert first.account_id == second.account_id == binding.account_id
    assert fixture["sends"] == [] and snapshot(data[0]) == before
    data[2].close()


def refused_archive_copies(data, binding, root):
    """Only four new join boundaries; no restart/fault matrix or model sends."""
    reports = []
    for fault in ("generation_marker", "ns_provenance", "trial_provenance", "ns_body"):
        target = root / (fault + ".db")
        with sqlite3.connect(data[0].engine.url.database) as origin, sqlite3.connect(target) as dest:
            origin.backup(dest)
        store = Store("sqlite:///" + str(target), test_only=True)
        try:
            with store.tx() as c:
                if fault == "generation_marker":
                    from sim2act.db import runs
                    rows = c.execute(select(attempts).join(runs, attempts.c.run_id == runs.c.id).where(
                        runs.c.runtime_id == binding.contract.runtime_id,
                        runs.c.request_key == binding.contract.stage_keys.generate)).mappings().all()
                    assert len(rows) == 3
                    for row in rows:
                        params = copy.deepcopy(row["parameters"])
                        params.pop("pa_trial_binding")
                        c.execute(update(attempts).where(attempts.c.id == row["id"]).values(parameters=params))
                else:
                    kind = trial.RESPONSE if fault == "trial_provenance" else archive.RESPONSE
                    row = c.execute(select(delivery_graph_requests).where(
                        delivery_graph_requests.c.kind == kind)).mappings().first()
                    saved = copy.deepcopy(row["snapshot"])
                    if fault == "ns_body":
                        saved["response"]["body_b64"] = "e30="
                    else:
                        saved["response"]["provenance"] = "OFFLINE_MOCKTRANSPORT"
                        if kind == archive.RESPONSE:
                            saved["request"]["provenance"] = "OFFLINE_MOCKTRANSPORT"
                    c.execute(update(delivery_graph_requests).where(
                        delivery_graph_requests.c.app_id == row["app_id"],
                        delivery_graph_requests.c.principal_id == row["principal_id"],
                        delivery_graph_requests.c.request_key == row["request_key"],
                        delivery_graph_requests.c.kind.in_([kind, kind + "_seal"]))
                        .values(snapshot=saved, fingerprint=fingerprint(saved),
                                request_fingerprint=fingerprint(saved["request"])))
            before = snapshot(store)
            with pytest.raises(DomainError) as denied:
                archive.resolve_trial_source(store, data[3], binding.contract, binding.approval_key)
            assert snapshot(store) == before
            reports.append(dict(fault=fault, error=denied.value.code, new_sends=0, tables_unchanged=True))
        finally:
            store.engine.dispose()
    return reports


def observe_reservation_reads(monkeypatch):
    """Passively inspect real checks and ensure their scope exits before writes."""
    local, reports, tokens = threading.local(), [], []
    reserve, preflight, guard = Worker.reserve, trial.preflight, Store.guard
    reservation_check, journal_reads = runtime.reservation_check, trial._journal_reads

    def check_token(worker, c, name):
        record = getattr(local, "record", None)
        if record is not None:
            token = c.info.get("pb_source_reads")
            assert pb._source_reads_current(worker.store, c, token)
            assert token is record["token"]
            record["checks"].append(name)

    def observed_preflight(worker, c, run, **kwargs):
        check_token(worker, c, "preflight")
        record = getattr(local, "record", None)
        if record is not None:
            assert record["guard_entered"] == record["guard_returned"] >= 1
            assert record["guard_depth"] == 0
        return preflight(worker, c, run, **kwargs)

    def observed_guard(store, c, *args, **kwargs):
        record = getattr(local, "record", None)
        if record is not None:
            token = c.info.get("pb_source_reads")
            assert pb._source_reads_current(store, c, token) and token is record["token"]
            record["guard_entered"] += 1
            record["guard_depth"] += 1
        try:
            value = guard(store, c, *args, **kwargs)
        finally:
            if record is not None:
                record["guard_depth"] -= 1
        if record is not None:
            assert pb._source_reads_current(store, c, token)
            record["guard_returned"] += 1
        return value

    def observed_check(worker, c, *args):
        check_token(worker, c, "reservation_check")
        result = reservation_check(worker, c, *args)
        check_token(worker, c, "reservation_check_return")
        return result

    @contextmanager
    def observed_reads(worker, c):
        record = getattr(local, "record", None)
        with journal_reads(worker, c):
            if record is not None:
                assert record["depth"] == 0
                token = c.info.get("pb_source_reads")
                assert pb._source_reads_current(worker.store, c, token)
                assert all(token is not old for old in tokens)
                tokens.append(token)
                record["token"], record["depth"] = token, 1
            try:
                yield
            finally:
                if record is not None:
                    record["depth"] = 0
        if record is not None:
            assert "pb_source_reads" not in c.info
            assert token.results == {} and token.inflight == set()
            record["cleared"] = True

    def observed_reserve(worker, run_id, *args, **kwargs):
        if kwargs.get("natural_spec_request") is None:
            return reserve(worker, run_id, *args, **kwargs)
        record = dict(run_id=run_id, depth=0, checks=[], writes=0, cleared=False,
                      guard_entered=0, guard_returned=0, guard_depth=0)
        local.record = record
        try:
            result = reserve(worker, run_id, *args, **kwargs)
            assert record["checks"] == ["preflight", "reservation_check", "reservation_check_return"]
            assert record["guard_entered"] == record["guard_returned"] >= 1
            assert record["guard_depth"] == 0
            assert record["cleared"] and record["depth"] == 0 and record["writes"] > 0
            reports.append({k: v for k, v in record.items() if k != "token"})
            return result
        finally:
            local.record = None

    def before_sql(c, cursor, statement, parameters, context, executemany):
        record = getattr(local, "record", None)
        if record is not None and not statement.lstrip().upper().startswith("SELECT "):
            assert record["depth"] == 0
            record["writes"] += 1

    monkeypatch.setattr(Worker, "reserve", observed_reserve)
    monkeypatch.setattr(Store, "guard", observed_guard)
    monkeypatch.setattr(trial, "preflight", observed_preflight)
    monkeypatch.setattr(runtime, "reservation_check", observed_check)
    monkeypatch.setattr(trial, "_journal_reads", observed_reads)
    return reports, before_sql


def test_pb_production_original_source_extraction_explicit_use_and_cold(env, tmp_path, monkeypatch):
    data, binding, fixture, factory = configured(env, tmp_path, monkeypatch, prepare_case=prepare_pb)
    generation, _, release, source_instance, generated = apps.ready(data, style="ordered")
    assert len(generated) == 3
    read_reports, before_sql = observe_reservation_reads(monkeypatch)
    event.listen(data[0].engine, "before_cursor_execute", before_sql)
    source_id = apps.enqueue(data, release, source_instance, key=binding.contract.stage_keys.source)
    approve_stage(data, binding, "source", source_id)
    source_bytes = []
    normal = apps.transport([], apps.SOURCE)

    def source_response(request):
        raw = normal.handle_request(request).json()
        raw["archive_note"] = "合成原始正文；非真实模型"
        payload = (json.dumps(raw, ensure_ascii=False, indent=2) + "\n").encode()
        source_bytes.append((request.content, payload))
        return httpx.Response(200, content=payload)

    assert factory(data[0], data[1], goal_planner_transport=httpx.MockTransport(source_response)).once()
    source_result = apps.inspect(data, source_instance, source_id)
    assert source_result.status_code == 200 and source_result.json()["status"] == "SUCCEEDED", source_result.text
    assert len(source_bytes) == 2 and len(fixture["sends"]) == 5
    route = f"/api/projects/{data[4]}/natural-spec-task-runs/{source_id}"
    options = data[2].get(route + "/extraction-options")
    assert options.status_code == 200, options.text
    target = binding.contract.bindings[1]
    review = dict(source_run_id=source_id,
        expected_source_proof_fingerprint=options.json()["source_proof_fingerprint"],
        expected_source_recipe_fingerprint=options.json()["recipe_fingerprint"],
        card_id=target.card_id, expected_goal_version=target.goal_version,
        expected_goal_fingerprint=target.goal_fingerprint, expected_source_hash=target.source_hash,
        recipe=binding.contract.extraction_recipe.model_dump(exclude_none=True),
        name="P-B production-shaped fixture", request_key=binding.contract.extraction_request_key)
    preview = data[2].post(route + "/extraction-reviews", json=review)
    assert preview.status_code == 200, preview.text
    body = pb.ExtractInput(review=review, expected_review_fingerprint=preview.json()["review_fingerprint"],
        consent=pb.CONSENT, artifact_write_consent=natural.CONSENT)
    worker = factory(data[0], data[1], goal_planner_transport=httpx.MockTransport(
        lambda request: pytest.fail("Extraction must not send")))
    made = trial.extract_pb(worker, data[3], source_id, body)
    assert trial.extract_pb(worker, data[3], source_id, body) == made
    assert len(fixture["sends"]) == 5
    resolved = archive.resolve_trial_source(data[0], data[3], binding.contract, binding.approval_key)
    assert list(zip(resolved.request_bodies, resolved.response_bodies, strict=True)) == source_bytes
    assert resolved.public_receipt["verification"] == "SPEC_PRODUCTION_CONTROLLER_ARCHIVE"
    assert resolved.public_receipt["live_allowed"] is False
    assert all(p["decoded_body_sha256"] != p["canonical_ascii_sha256"]
               for p in resolved.public_receipt["attempts"])
    failures = refused_archive_copies(data, binding, tmp_path)
    release, inst = apps.instance(data, made["id"])
    catalog = data[2].get("/api/apps", params={"metadata_only": "true"})
    assert catalog.status_code == 200, catalog.text
    assert next(item for item in catalog.json()["items"] if item["id"] == made["id"])["use_family"] == "NATURAL_PB"

    # Fresh Store/client/Worker on the same durable database; no old worker result.
    cold_store = Store(data[1].database_url, test_only=True)
    event.listen(cold_store.engine, "before_cursor_execute", before_sql)
    cold_client = TestClient(create_app(cold_store, data[1]))
    cold_client.headers["Authorization"] = "Bearer synthetic-test-A"
    cold_data = (cold_store, data[1], cold_client, *data[3:])
    original_environment = controller.environment

    def cold_environment(store, settings, transport):
        if store is cold_store:
            assert settings is data[1] and transport is None and store.test_only and store.sqlite
        else:
            original_environment(store, settings, transport)

    monkeypatch.setattr(controller, "environment", cold_environment)
    try:
        current = cold_client.get("/api/internal/instances/" + inst["id"]).json()
        current_app = cold_client.get("/api/apps/" + made["id"])
        assert current_app.status_code == 200, current_app.text
        app = current_app.json()
        assert app["fingerprint"] == made["candidate_fingerprint"]
        use_review = dict(expected_revision=current["revision"],
            expected_release_fingerprint=release["fingerprint"], expected_app_fingerprint=app["fingerprint"],
            expected_recipe_fingerprint=fingerprint(binding.contract.extraction_recipe.model_dump(exclude_none=True)),
            resource_id=target.resource_id, card_id=target.card_id,
            expected_goal_version=target.goal_version, expected_goal_fingerprint=target.goal_fingerprint,
            expected_source_hash=target.source_hash, request_key=binding.contract.stage_keys.cold)
        base = "/api/internal/instances/" + inst["id"]
        checked = cold_client.post(base + "/pb-use-reviews", json=use_review)
        assert checked.status_code == 200, checked.text
        submitted = dict(review=use_review, expected_review_fingerprint=checked.json()["review_fingerprint"],
            consent=use.CONSENT)
        queued = cold_client.post(base + "/pb-use-runs", json=submitted)
        assert queued.status_code == 202, queued.text
        replayed = cold_client.post(base + "/pb-use-runs", json=submitted)
        assert replayed.status_code == 202, replayed.text
        assert queued.json()["cached"] is False and replayed.json()["cached"] is True
        assert {k: v for k, v in replayed.json().items() if k != "cached"} == {
            k: v for k, v in queued.json().items() if k != "cached"}
        cold_id = queued.json()["run_id"]
        approve_stage(cold_data, binding, "cold", cold_id)
        assert factory(cold_store, data[1], goal_planner_transport=apps.transport([], apps.COLD)).once()
        result = apps.inspect(cold_data, inst, cold_id)
        assert result.status_code == 200 and result.json()["status"] == "SUCCEEDED", result.text
        owner = cold_client.get(base + f"/runs/{cold_id}/spec-owner-review")
        assert owner.status_code == 200 and owner.json()["owner_acceptance"] == "PENDING", owner.text
        history = journal.read(cold_store, data[3], binding.contract, binding.approval_key, binding.account_id)
        assert len(history.ledger.slots) == len(fixture["sends"]) == 7
        assert not history.ledger.halted and all(s.accepted for s in history.ledger.slots)
        assert len(read_reports) == 4
        assert [r["run_id"] for r in read_reports] == [source_id] * 2 + [cold_id] * 2
        assert [s.identity.stage for s in history.ledger.slots] == ["generate"] * 3 + ["source"] * 2 + ["cold"] * 2
        assert all(b.reserved_at - a.reserved_at >= 60 for a, b in zip(history.ledger.slots[:-1], history.ledger.slots[1:], strict=True))
        with cold_store.tx() as c:
            rows = c.execute(select(attempts)).mappings().all()
            assert len(rows) == 7 and all(row["mode"] == "LIVE" for row in rows)
            bodies = c.execute(select(delivery_graph_requests.c.snapshot).where(
                delivery_graph_requests.c.kind.in_([trial.REQUEST, trial.RESPONSE, archive.REQUEST, archive.RESPONSE]))).scalars().all()
            assert len(bodies) == 22 and all(b["response"]["provenance"] == "SPEC_PRODUCTION_CONTROLLER" for b in bodies)
        (tmp_path / "pb-controller-proof.json").write_text(json.dumps(dict(
            classification="SYNTHETIC_MOCK_PRODUCTION_BRANCH_NOT_REAL_LIVE_EVIDENCE", real_models=0,
            generation=generation, source=source_id, extraction=made["id"], cold=cold_id,
            original_source=resolved.public_receipt, refusals=failures, result=result.json(),
            owner=owner.json(), journal=history.model_dump(mode="json"),
            reservation_read_segments=read_reports,
            same_key_no_duplicate=True, extraction_new_sends=0, cold_store_reopened=True), indent=2))
    finally:
        cold_client.close()
        cold_store.engine.dispose()
        data[2].close()
