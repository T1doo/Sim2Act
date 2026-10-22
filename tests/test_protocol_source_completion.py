"""Bounded synthetic SQLite Source completion; no G0, real HTTP or UNKNOWN import."""

import copy
import json
import shutil
import threading
import time
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, insert, select, update
from test_protocol_jobs import LIMITS, source_payload, wire
from test_protocol_jobs import env as jobs_env

from sim2act import protocol_jobs as jobs
from sim2act.api import create_app
from sim2act.db import Store, attempts, events, fingerprint, grants, new_id, operations, runs
from sim2act.db import protocol_request_slots as slots
from sim2act.errors import DomainError
from sim2act.model import InternModel
from sim2act.model_budget import BudgetedProvider, initialize_ledger
from sim2act.protocol_api import ProtocolAttemptRunner
from sim2act.protocol_reviews import evaluation_contract, review
from sim2act.protocol_source_completion import COMPLETED, ORIGIN, READY, complete_source
from sim2act.worker import Worker


class Interrupted(BaseException):
    pass


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    root = tmp_path_factory.mktemp("source-v2-original")
    patch = pytest.MonkeyPatch()
    patch.delenv("SIM2ACT_TEST_DATABASE_URL", raising=False)
    ticks, sends = [1800000000.0], []
    patch.setattr(time, "time", lambda: ticks[0])
    gen = jobs_env.__wrapped__(root)
    env = next(gen)
    store, user, pid, a, _, worker, _ = env
    original_store, original_worker = store, worker
    experiment_store = None
    import sqlite3

    baseline = root / "unsent.sqlite"
    with store.engine.connect() as c, sqlite3.connect(baseline) as target:
        c.connection.driver_connection.backup(target)
    before_threads = set(threading.enumerate())
    contract, _ = evaluation_contract("protocol.synthetic.a-source.v1")

    def configure(responses):
        pending = list(responses)

        def factory(worker, run, snapshot):
            def transport(request):
                assert len(sends) < 7, "Source suite Mock allowance exceeded"
                assert request.url == InternModel.ENDPOINT
                sends.append(dict(run=run["id"], body=request.content.hex()))
                ticks[0] += 7
                return httpx.Response(200, json=pending.pop(0))

            model = InternModel(
                replace(worker.s, live_enabled=True, token="synthetic-only"),
                httpx.MockTransport(transport),
            )
            path = root / (run["id"] + ".json")
            initialize_ledger(path, snapshot["scope"])

            def authorize(scope):
                with store.tx() as c:
                    for ref in scope["resource_ids"]:
                        store.authorize(c, user, run["runtime_id"], pid, ref, "resource.read")
                return True

            provider = BudgetedProvider(
                model,
                path,
                snapshot["scope"],
                "source_a",
                authorize=authorize,
                clock=lambda: ticks[0],
            )
            return ProtocolAttemptRunner(worker, run, snapshot, provider)

        worker.protocol_runner_factory = factory

    def execute():
        claimed = store.claim(worker.id, worker.s.lease_seconds)
        assert claimed
        jobs.process_job(worker, claimed)
        return jobs.inspect(store, user, claimed["id"])

    try:
        jobs.enqueue(store, user, pid, "source", source_payload(a), "normal", LIMITS)
        configure([wire(rid=a), wire(contract["expected_output"])])
        normal = execute()
        assert normal["status"] == "WAITING_APPROVAL", normal
        # Separate controller-created experiment, copied before any request.
        # It shares only immutable fixture resources, not prior sends or budget.
        db = root / "experiment.sqlite"
        shutil.copyfile(baseline, db)
        store = experiment_store = Store("sqlite:///" + str(db), test_only=True)
        worker = Worker(store, replace(original_worker.s, database_url=str(store.engine.url)))
        from sim2act.protocol_experiment import bind_run, initialize_experiment

        experiment = initialize_experiment(store, user, pid, "source-recovery", request_limit=7)
        interrupted = jobs.enqueue(
            store, user, pid, "source", source_payload(a), "interrupted", LIMITS
        )
        bind_run(store, user, experiment["experiment_id"], interrupted["run_id"])
        configure([wire(rid=a), wire(contract["expected_output"])])
        captured = {}

        def stop(store, c, current, snapshot, result, compiled, fence):
            assert current["id"] == interrupted["run_id"] and compiled is None
            captured.update(result=copy.deepcopy(result))
            raise Interrupted()

        with patch.context() as cut:
            cut.setattr(jobs, "complete_in_tx", stop)
            original_call = ProtocolAttemptRunner.call

            def spaced_call(self, messages, tools):
                # Only this semantic experiment: explicit synthetic spacing.
                # Product clocks and 6s/30s/300s settings remain unchanged.
                ticks[0] += 7
                return original_call(self, messages, tools)

            cut.setattr(ProtocolAttemptRunner, "call", spaced_call)
            with pytest.raises(Interrupted):
                execute()
        rid = interrupted["run_id"]
        with store.tx() as c:
            current = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
            assert current["result"] is None and current["status"] == "RUNNING"
            assert c.execute(
                select(events.c.id).where(events.c.run_id == rid, events.c.kind == READY)
            ).first()
            assert not c.execute(
                select(events.c.id).where(
                    events.c.run_id == rid, events.c.kind == "PROTOCOL_COMPLETED"
                )
            ).first()
        archive = root / "sealed.sqlite"
        with store.engine.connect() as c, sqlite3.connect(archive) as target:
            c.connection.driver_connection.backup(target)
        interrupted_settings = worker.s
        store, worker = original_store, original_worker
        jobs.enqueue(store, user, pid, "source", source_payload(a), "three-requests", LIMITS)
        configure([wire(rid=a), wire(rid=a), wire(contract["expected_output"])])
        triple = execute()
        assert triple["status"] == "WAITING_APPROVAL", triple
        assert len(triple["result"]["protocol_result"]["evidence"]["tool_trace"]) == 2
        assert len(sends) == 7
        yield dict(
            root=root,
            archive=archive,
            settings=interrupted_settings,
            experiment_id=experiment["experiment_id"],
            ticks=ticks,
            sends=sends,
            rid=rid,
            current=current,
            normal=normal,
            captured=captured,
            user=user,
            pid=pid,
            contract=contract,
            end=ticks[0],
        )
        assert not any(t.is_alive() for t in threading.enumerate() if t not in before_threads)
    finally:
        (root / "test-budget.json").write_text(
            json.dumps(
                dict(
                    classification="SYNTHETIC_SQLITE_SOURCE_NOT_G0",
                    mock_allowance=7,
                    mock_requests=len(sends),
                    requests=sends,
                    real_models=0,
                    real_http=0,
                    lease_seconds=worker.s.lease_seconds,
                    run_seconds=worker.s.run_seconds,
                    clock="explicit synthetic business clock",
                ),
                indent=2,
            )
        )
        if experiment_store is not None:
            experiment_store.engine.dispose()
        with pytest.raises(StopIteration):
            next(gen)
        patch.undo()


@pytest.fixture
def cold(prepared, tmp_path, monkeypatch):
    p = prepared
    p["ticks"][0] = p["end"] + 31
    db = tmp_path / "reopened.sqlite"
    shutil.copyfile(p["archive"], db)
    for suffix in (".json", ".lock"):
        shutil.copyfile(p["root"] / (p["rid"] + suffix), tmp_path / (p["rid"] + suffix))
    store = Store("sqlite:///" + str(db), test_only=True)
    settings = replace(p["settings"], database_url=str(store.engine.url), data_dir=tmp_path)

    def forbidden(*args, **kwargs):
        pytest.fail("Completion attempted a send/reservation/candidate acceptance")

    for owner, name in (
        (BudgetedProvider, "call"),
        (BudgetedProvider, "preflight"),
        (BudgetedProvider, "accept_candidate"),
        (InternModel, "request"),
        (InternModel, "request_serialized"),
        (Worker, "reserve"),
    ):
        monkeypatch.setattr(owner, name, forbidden)
    body = dict(
        expected_version=p["current"]["version"],
        expected_fence=p["current"]["fence"],
        request_key="finish-source",
    )
    try:
        yield store, settings, body
    finally:
        store.engine.dispose()


def test_complete_known_source_and_review(prepared, cold):
    p = prepared
    store, settings, body = cold
    side = settings.data_dir / (p["rid"] + ".json")
    before = side.read_bytes()
    with store.tx() as c:
        before_slots = [dict(v) for v in c.execute(select(slots)).mappings()]
    response = complete_source(store, p["user"], p["rid"], body, settings)
    assert response["status"] == "WAITING_APPROVAL" and response["provider_requests"] == 0
    done = jobs.inspect(store, p["user"], p["rid"])
    assert done["semantic_status"] == "UNKNOWN"
    assert fingerprint(done["result"]["protocol_result"]) == fingerprint(p["captured"]["result"])
    assert fingerprint(done["result"]["protocol_result"]) == fingerprint(
        p["normal"]["result"]["protocol_result"]
    )
    assert "compiled_plan" not in done["result"]
    assert complete_source(store, p["user"], p["rid"], body, settings) == dict(
        response, cached=True
    )
    decision = review(
        store,
        p["user"],
        p["rid"],
        dict(
            contract_id=p["contract"]["id"],
            expected_result_fingerprint=done["result_fingerprint"],
            expected_fence=done["fence"],
            expected_version=done["version"],
            request_key="source-review",
        ),
    )
    assert decision["decision"] == "PASS"
    from sim2act.protocol_experiment import advance, bind_run

    advance(store, p["user"], p["experiment_id"], p["rid"])
    next_run = jobs.enqueue(
        store,
        p["user"],
        p["pid"],
        "extract",
        dict(source_run_id=p["rid"], expected_source_fingerprint=done["result_fingerprint"]),
        "next-extract-not-executed",
        LIMITS,
    )
    bind_run(store, p["user"], p["experiment_id"], next_run["run_id"])
    p["ticks"][0] += 400  # Committed command replay never renews original execution time.
    assert complete_source(store, p["user"], p["rid"], body, settings) == dict(
        response, cached=True
    )
    with store.tx() as c:
        assert [dict(v) for v in c.execute(select(slots)).mappings()] == before_slots
        with pytest.raises(DomainError):
            store.guard(c, p["rid"], body["expected_fence"])
    assert side.read_bytes() == before and len(p["sends"]) == 7


@pytest.mark.parametrize(
    "change",
    [
        "wire",
        "cross_run",
        "index",
        "missing_origin",
        "v1",
        "missing_usage",
        "started",
        "extra_attempt",
        "slot",
        "extra_operation",
        "operation_binding",
        "receipt",
        "ready",
        "ready_mirror",
        "swap_provider",
        "provider_usage",
        "provider_raw",
        "provider_total",
        "live_lease",
        "cancel",
        "revoke",
        "expired",
        "owner",
        "version",
        "key_schema",
    ],
)
def test_reject_incomplete_or_changed_facts(prepared, cold, change):
    p = prepared
    store, settings, body = cold
    path = settings.data_dir / (p["rid"] + ".json")
    user = p["user"]
    with store.tx() as c:
        rows = list(c.execute(select(attempts).where(attempts.c.run_id == p["rid"])).mappings())
        a = rows[0]
        params = copy.deepcopy(a["parameters"])
        values = {}
        if change == "wire":
            params["protocol_wire"]["sha256"] = "0" * 64
        elif change == "cross_run":
            params["source_origin_v2"]["run_id"] = p["normal"]["run_id"]
        elif change == "index":
            params["source_origin_v2"]["request_index"] = 1
        elif change == "missing_origin":
            c.execute(events.delete().where(events.c.run_id == a["id"], events.c.kind == ORIGIN))
        elif change == "v1":
            params.pop("source_origin_v2")
        elif change == "missing_usage":
            values["usage"] = dict(status="unknown", tokens=None)
        elif change == "started":
            values["status"] = "STARTED"
        elif change == "extra_attempt":
            c.execute(insert(attempts).values(**dict(a, id=new_id("attempt"))))
        elif change == "slot":
            c.execute(update(slots).where(slots.c.attempt_id == a["id"]).values(ordinal=99))
        elif change in {"extra_operation", "operation_binding", "receipt"}:
            op = (
                c.execute(select(operations).where(operations.c.run_id == p["rid"]))
                .mappings()
                .one()
            )
            if change == "extra_operation":
                c.execute(insert(operations).values(**dict(op, id=new_id("op"), call_id="extra")))
            elif change == "operation_binding":
                c.execute(
                    update(operations)
                    .where(operations.c.id == op["id"])
                    .values(call_id="different")
                )
            else:
                receipt = copy.deepcopy(op["receipt"])
                receipt["artifact_refs"] = ["unrelated"]
                c.execute(
                    update(operations).where(operations.c.id == op["id"]).values(receipt=receipt)
                )
        elif change in {"ready", "ready_mirror"}:
            c.execute(
                events.delete().where(
                    events.c.kind == READY,
                    events.c.run_id == (p["rid"] if change == "ready" else rows[-1]["id"]),
                )
            )
        elif change == "live_lease":
            c.execute(
                update(runs).where(runs.c.id == p["rid"]).values(lease_until=p["ticks"][0] + 5)
            )
        elif change == "cancel":
            c.execute(update(runs).where(runs.c.id == p["rid"]).values(cancel_intent=True))
        elif change == "revoke":
            c.execute(update(grants).where(grants.c.project_id == p["pid"]).values(revoked=True))
        elif change == "expired":
            p["ticks"][0] += 301
        elif change == "owner":
            user = "someone-else"
        elif change == "version":
            body["expected_version"] += 1
        elif change == "key_schema":
            body["response"] = {}
        c.execute(
            update(attempts).where(attempts.c.id == a["id"]).values(parameters=params, **values)
        )
    if change.startswith("provider") or change == "swap_provider":
        data = json.loads(path.read_text())
        if change == "swap_provider":
            data["slots"].reverse()
        elif change == "provider_usage":
            data["slots"][0].pop("normalized_usage_v2")
        elif change == "provider_raw":
            data["slots"][0]["raw_response_fingerprint_v2"] = "0" * 64
        else:
            data["reserved"] += 1
        path.write_text(json.dumps(data))
    with pytest.raises((DomainError, __import__("pydantic").ValidationError)):
        complete_source(store, user, p["rid"], body, settings)
    with store.tx() as c:
        current = c.execute(select(runs).where(runs.c.id == p["rid"])).mappings().one()
        assert current["result"] is None and current["fence"] == p["current"]["fence"]
        assert not c.execute(
            select(events.c.id).where(events.c.run_id == p["rid"], events.c.kind == COMPLETED)
        ).first()
    assert len(p["sends"]) == 7


def test_completion_write_fault_rolls_back(prepared, cold):
    p = prepared
    store, settings, body = cold
    side = (settings.data_dir / (p["rid"] + ".json")).read_bytes()

    def fault(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("UPDATE protocol_jobs SET result_snapshot"):
            raise RuntimeError("synthetic Source completion write fault")

    event.listen(store.engine, "before_cursor_execute", fault)
    try:
        with pytest.raises(RuntimeError, match="synthetic Source"):
            complete_source(store, p["user"], p["rid"], body, settings)
    finally:
        event.remove(store.engine, "before_cursor_execute", fault)
    with store.tx() as c:
        current = c.execute(select(runs).where(runs.c.id == p["rid"])).mappings().one()
        assert current["fence"] == body["expected_fence"] and current["result"] is None
        assert not c.execute(
            select(events.c.id).where(events.c.run_id == p["rid"], events.c.kind == COMPLETED)
        ).first()
    assert (settings.data_dir / (p["rid"] + ".json")).read_bytes() == side


def test_owner_http_closed_contract(prepared, cold):
    p = prepared
    store, settings, body = cold
    with TestClient(create_app(store, settings)) as client:
        route = f"/api/projects/{p['pid']}/protocol/runs/{p['rid']}/complete-source"
        assert client.post(route, json=body).status_code == 403
        headers = {"Authorization": "Bearer secret test token"}
        assert client.post(route, json=dict(body, response={}), headers=headers).status_code == 422
        response = client.post(route, json=body, headers=headers)
        assert response.status_code == 200, response.text
        assert (
            response.json()["provider_requests"] == 0
            and response.json()["status"] == "WAITING_APPROVAL"
        )


@pytest.mark.parametrize("mode", ["explicit", "automatic"])
def test_existing_metadata_recovery_then_complete_and_review(prepared, cold, mode):
    from sim2act.protocol_recovery import recover, recover_expired_protocols

    p = prepared
    store, settings, body = cold
    if mode == "explicit":
        old = recover(store, p["user"], p["rid"], dict(body, request_key="old-state-check"))
        assert old["recovery"] == "CONTINUATION_NOT_IMPLEMENTED" and old["provider_requests"] == 0
    else:
        recover_expired_protocols(store)
    with store.tx() as c:
        current = c.execute(select(runs).where(runs.c.id == p["rid"])).mappings().one()
        assert (
            current["status"] == "WAITING_RESOURCE"
            and current["fence"] == body["expected_fence"] + 1
        )
        assert current["error"] == dict(code="CONTINUATION_NOT_IMPLEMENTED")
        body.update(expected_version=current["version"], expected_fence=current["fence"])
    response = complete_source(store, p["user"], p["rid"], body, settings)
    done = jobs.inspect(store, p["user"], p["rid"])
    assert done["status"] == "WAITING_APPROVAL" and done["error"] is None
    decision = review(
        store,
        p["user"],
        p["rid"],
        dict(
            contract_id=p["contract"]["id"],
            expected_result_fingerprint=done["result_fingerprint"],
            expected_fence=done["fence"],
            expected_version=done["version"],
            request_key="review-after-old-recovery",
        ),
    )
    assert decision["decision"] == "PASS"
    assert complete_source(store, p["user"], p["rid"], body, settings) == dict(
        response, cached=True
    )


@pytest.mark.parametrize(
    "change",
    [
        "no_transition",
        "cancel",
        "extra_version",
        "bad_response",
        "late_completion",
        "missing_review",
    ],
)
def test_no_forged_transition_or_cached_receipt(prepared, cold, change):
    p = prepared
    store, settings, body = cold
    if change == "no_transition":
        with store.tx() as c:
            c.execute(
                update(runs)
                .where(runs.c.id == p["rid"])
                .values(
                    fence=body["expected_fence"] + 1,
                    version=body["expected_version"] + 1,
                    status="WAITING_RESOURCE",
                    lease_until=0,
                    worker_id=None,
                    error=dict(code="CONTINUATION_NOT_IMPLEMENTED"),
                )
            )
        body.update(
            expected_version=body["expected_version"] + 1, expected_fence=body["expected_fence"] + 1
        )
    else:
        complete_source(store, p["user"], p["rid"], body, settings)
        with store.tx() as c:
            if change == "cancel":
                c.execute(update(runs).where(runs.c.id == p["rid"]).values(cancel_intent=True))
            elif change == "extra_version":
                c.execute(
                    update(runs)
                    .where(runs.c.id == p["rid"])
                    .values(version=body["expected_version"] + 3)
                )
            elif change == "missing_review":
                c.execute(
                    update(runs)
                    .where(runs.c.id == p["rid"])
                    .values(status="SUCCEEDED", version=body["expected_version"] + 2)
                )
            else:
                values = list(
                    c.execute(
                        select(events.c.id, events.c.data).where(events.c.kind == COMPLETED)
                    ).mappings()
                )
                for row in values:
                    value = copy.deepcopy(row["data"])
                    if change == "bad_response":
                        value["response"]["provider_requests"] = False
                    else:
                        value["completed_at"] += 400
                    c.execute(update(events).where(events.c.id == row["id"]).values(data=value))
    with pytest.raises(DomainError):
        complete_source(store, p["user"], p["rid"], body, settings)
