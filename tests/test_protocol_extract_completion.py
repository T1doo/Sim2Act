"""Known-response completion: real SQLite/Worker/Mock, no G0 or real HTTP.

One reviewed prefix, normal extract and interrupted extract are shared as
immutable synthetic inputs. Each counterexample has a fresh isolated DB copy.
At most eight Mock requests including the separate experiment/Cold controls.
"""

import copy
import hashlib
import json
import shutil
import threading
import time
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select, update
from test_protocol_jobs import LIMITS, source_payload, wire
from test_protocol_jobs import env as jobs_env

from sim2act import protocol_jobs as jobs
from sim2act.api import create_app
from sim2act.db import Store, attempts, events, fingerprint, grants, meta, protocol_jobs, runs
from sim2act.db import protocol_request_pools as pools
from sim2act.db import protocol_request_slots as slots
from sim2act.errors import DomainError
from sim2act.model import InternModel
from sim2act.model_budget import BudgetedProvider, initialize_ledger
from sim2act.protocol_api import ProtocolAttemptRunner
from sim2act.protocol_extract_completion import ACCEPTED, COMPLETED, ORIGIN, complete_extract
from sim2act.protocol_readiness import candidate_for
from sim2act.protocol_reviews import contract_snapshot, evaluation_contract, review
from sim2act.worker import Worker


class Interrupted(BaseException):
    pass


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    root = tmp_path_factory.mktemp("extract-v2-original")
    patch = pytest.MonkeyPatch()
    ticks, sends = [1800000000.0], []
    patch.delenv("SIM2ACT_TEST_DATABASE_URL", raising=False)
    patch.setattr(time, "time", lambda: ticks[0])
    gen = jobs_env.__wrapped__(root)
    env = next(gen)
    store, user, pid, a, b, worker, _ = env
    before_threads = set(threading.enumerate())

    def configure(replies, stage):
        pending = list(replies)

        def factory(worker, run, snapshot):
            def transport(request):
                assert len(sends) < 8, "Synthetic suite Mock allowance exceeded"
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
                    for rid in scope["resource_ids"]:
                        store.authorize(c, user, run["runtime_id"], pid, rid, "resource.read")
                return True

            provider = BudgetedProvider(
                model, path, snapshot["scope"], stage, authorize=authorize, clock=lambda: ticks[0]
            )
            return ProtocolAttemptRunner(worker, run, snapshot, provider)

        worker.protocol_runner_factory = factory

    def execute():
        run = store.claim(worker.id, worker.s.lease_seconds)
        assert run is not None
        jobs.process_job(worker, run)
        return jobs.inspect(store, user, run["id"])

    try:
        src = jobs.enqueue(store, user, pid, "source", source_payload(a), "source", LIMITS)
        contract, _ = evaluation_contract("protocol.synthetic.a-source.v1")
        configure([wire(rid=a), wire(contract["expected_output"])], "source_a")
        done = execute()
        review(
            store,
            user,
            src["run_id"],
            dict(
                contract_id=contract["id"],
                expected_result_fingerprint=done["result_fingerprint"],
                expected_fence=done["fence"],
                expected_version=done["version"],
                request_key="review",
            ),
        )
        source = jobs.inspect(store, user, src["run_id"])
        candidate = candidate_for(contract_snapshot(contract["id"]), [a])
        payload = dict(
            source_run_id=src["run_id"], expected_source_fingerprint=source["result_fingerprint"]
        )
        normal = jobs.enqueue(store, user, pid, "extract", payload, "normal", LIMITS)
        configure([wire(candidate)], "extract_a")
        normal = execute()
        assert normal["status"] == "SUCCEEDED"
        assert (
            normal["result"]["compiled_plan"]["candidate_receipt"]["namespace"]
            == "protocol-attempt-receipt.v2"
        )
        interrupted = jobs.enqueue(store, user, pid, "extract", payload, "interrupted", LIMITS)
        configure([wire(candidate)], "extract_a")
        captured = {}
        original = jobs.complete_in_tx

        def stop(store, c, current, snapshot, result, compiled, fence):
            assert current["id"] == interrupted["run_id"]
            captured.update(result=copy.deepcopy(result), compiled=copy.deepcopy(compiled))
            # This is the actual post-acceptance, pre-completion boundary.
            raise Interrupted()

        with patch.context() as cut:
            cut.setattr(jobs, "complete_in_tx", stop)
            with pytest.raises(Interrupted):
                execute()
        assert jobs.complete_in_tx is original and len(sends) == 4
        with store.tx() as c:
            current = dict(
                c.execute(select(runs).where(runs.c.id == interrupted["run_id"])).mappings().one()
            )
            assert current["result"] is None and current["status"] == "RUNNING"
            assert c.execute(
                select(events.c.id).where(
                    events.c.run_id == current["id"], events.c.kind == ACCEPTED
                )
            ).first()
            assert not c.execute(
                select(events.c.id).where(
                    events.c.run_id == current["id"], events.c.kind == "PROTOCOL_COMPLETED"
                )
            ).first()
            origin = c.execute(
                select(events.c.data).where(
                    events.c.run_id == current["id"], events.c.kind == ORIGIN
                )
            ).scalar_one()
            actual_wire = bytes.fromhex(next(s["body"] for s in sends if s["run"] == current["id"]))
            assert hashlib.sha256(actual_wire).hexdigest() == origin["wire"]["sha256"]
        # Copy only committed, genuine fixture state. No DTO/seal is fabricated.
        archive = root / "interrupted.sqlite"
        with store.engine.connect() as c:
            import sqlite3

            with sqlite3.connect(archive) as target:
                c.connection.driver_connection.backup(target)
        yield dict(
            root=root,
            archive=archive,
            settings=worker.s,
            ticks=ticks,
            sends=sends,
            interrupted=interrupted["run_id"],
            normal=normal,
            captured=captured,
            user=user,
            pid=pid,
            current=current,
            source=source,
            candidate=candidate,
            a=a,
            b=b,
            env=env,
            configure=configure,
            execute=execute,
            end=ticks[0],
        )
        assert len(sends) <= 8
        assert not any(t.is_alive() for t in threading.enumerate() if t not in before_threads)
    finally:
        (root / "test-budget.json").write_text(
            json.dumps(
                dict(
                    classification="SYNTHETIC_EXTRACT_COMPLETION_NOT_G0",
                    mock_allowance=8,
                    mock_requests=len(sends),
                    requests=sends,
                    real_models=0,
                    real_http=0,
                    lease_seconds=worker.s.lease_seconds,
                    run_seconds=worker.s.run_seconds,
                    clock="explicit synthetic business clock; not real-clock acceptance",
                ),
                indent=2,
            )
        )
        with pytest.raises(StopIteration):
            next(gen)
        patch.undo()


@pytest.fixture
def cold(prepared, tmp_path, monkeypatch):
    p = prepared
    p["ticks"][0] = p["end"] + 31  # Explicit synthetic clock; no lease extension.
    db = tmp_path / "reopened.sqlite"
    shutil.copyfile(p["archive"], db)
    for name in (p["interrupted"] + ".json", p["interrupted"] + ".lock"):
        shutil.copyfile(p["root"] / name, tmp_path / name)
    store = Store("sqlite:///" + str(db), test_only=True)  # Never initialize/reset.
    settings = replace(p["settings"], database_url=str(store.engine.url), data_dir=tmp_path)

    def forbidden(*args, **kwargs):
        pytest.fail("Completion tried to send, reserve or accept again")

    for owner, name in (
        (BudgetedProvider, "call"),
        (BudgetedProvider, "preflight"),
        (BudgetedProvider, "accept_candidate"),
        (InternModel, "request"),
        (InternModel, "request_serialized"),
        (Worker, "reserve"),
    ):
        monkeypatch.setattr(owner, name, forbidden)
    request = dict(
        expected_version=p["current"]["version"],
        expected_fence=p["current"]["fence"],
        request_key="finish-known",
    )
    try:
        yield store, settings, request
    finally:
        store.engine.dispose()


def snapshot(store):
    with store.engine.connect() as c:
        return {
            t.name: sorted(fingerprint(dict(r)) for r in c.execute(select(t)).mappings())
            for t in meta.sorted_tables
        }


def recover(p, cold, request=None):
    store, settings, body = cold
    return complete_extract(store, p["user"], p["interrupted"], request or body, settings)


def test_cold_completion_exact_plan_budgets_fences_and_idempotency(prepared, cold):
    p, (store, settings, request) = prepared, cold
    before, sent = snapshot(store), len(p["sends"])
    side = settings.data_dir / (p["interrupted"] + ".json")
    original_bytes = side.read_bytes()
    reply = recover(p, cold)
    assert reply["status"] == "SUCCEEDED" and reply["provider_requests"] == 0
    assert reply["fence"] == request["expected_fence"] + 1
    done = jobs.inspect(store, p["user"], p["interrupted"])
    assert done["result"]["compiled_plan"] == p["captured"]["compiled"]
    assert done["result"]["protocol_result"] == p["captured"]["result"]
    # Separate normal request has a different audit receipt; its business plan
    # and source proof are the same. Never compare different audit IDs as equal.
    for key in ("candidate", "candidate_fingerprint", "source_proof", "source_proof_fingerprint"):
        assert done["result"]["compiled_plan"][key] == p["normal"]["result"]["compiled_plan"][key]
    after = snapshot(store)
    assert {k for k in before if before[k] != after[k]} == {"runs", "protocol_jobs", "events"}
    assert side.read_bytes() == original_bytes and len(p["sends"]) == sent
    assert recover(p, cold) == dict(reply, cached=True)
    assert snapshot(store) == after
    with pytest.raises(DomainError):
        recover(p, cold, dict(request, request_key="another-key"))
    with store.tx() as c, pytest.raises(DomainError):
        store.guard(c, p["interrupted"], request["expected_fence"])


@pytest.mark.parametrize(
    "change",
    [
        "slot",
        "wire",
        "cross_run",
        "missing_usage",
        "v1",
        "started",
        "unknown",
        "multi",
        "sidecar_origin",
        "provider_halt",
        "pool_halt",
        "source",
        "bound_check",
        "receipt",
        "namespace",
        "pending_operation",
        "revoke",
        "expired",
        "cancel",
        "pause",
        "active_lease",
        "fence",
        "version",
        "sidecar_missing",
        "origin_missing",
        "provider_usage_missing",
        "coherent_cross_run",
        "genuine_v1_shape",
    ],
)
def test_incomplete_wrong_or_dynamic_evidence_cannot_finish(prepared, cold, change):
    p, (store, settings, _) = prepared, cold
    rid = p["interrupted"]
    path = settings.data_dir / (rid + ".json")
    with store.tx() as c:
        a = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().one()
        if change in {
            "slot",
            "wire",
            "cross_run",
            "missing_usage",
            "v1",
            "started",
            "receipt",
            "origin_missing",
        }:
            params = copy.deepcopy(a["parameters"])
            values = {}
            if change == "slot":
                c.execute(update(slots).where(slots.c.attempt_id == a["id"]).values(ordinal=99))
            elif change == "wire":
                params["protocol_wire"]["sha256"] = "0" * 64
            elif change == "cross_run":
                params["extract_origin_v2"]["run_id"] = p["source"]["run_id"]
            elif change == "missing_usage":
                values["usage"] = dict(status="unknown", tokens=None)
            elif change == "v1":
                params.pop("extract_origin_v2")
                params["protocol_candidate_receipt"]["namespace"] = "protocol-attempt-receipt.v1"
            elif change == "started":
                values["status"] = "STARTED"
            elif change == "receipt":
                params["protocol_candidate_receipt"]["slot"] = 1
            else:
                c.execute(
                    events.delete().where(events.c.run_id == a["id"], events.c.kind == ORIGIN)
                )
            c.execute(
                update(attempts).where(attempts.c.id == a["id"]).values(parameters=params, **values)
            )
        elif change == "unknown":
            c.execute(update(slots).where(slots.c.attempt_id == a["id"]).values(status="UNKNOWN"))
        elif change in {"multi", "active_lease", "fence", "version", "cancel", "pause"}:
            values = {}
            if change == "multi":
                ctx = copy.deepcopy(p["current"]["context"])
                ctx["requests"] = 2
                values["context"] = ctx
            elif change == "active_lease":
                values["lease_until"] = p["ticks"][0] + 30
            elif change == "cancel":
                values["cancel_intent"] = True
            elif change == "pause":
                values["status"] = "PAUSED"
            else:
                values[change] = p["current"][change] + 1
            c.execute(update(runs).where(runs.c.id == rid).values(**values))
        elif change in {"source", "bound_check"}:
            row = (
                c.execute(select(protocol_jobs).where(protocol_jobs.c.run_id == rid))
                .mappings()
                .one()
            )
            value = copy.deepcopy(row["accepted_snapshot"])
            if change == "source":
                value["phase"] = "source"
            else:
                value["bounded_check_namespace"] = "not-ordinary"
            c.execute(
                update(protocol_jobs)
                .where(protocol_jobs.c.run_id == rid)
                .values(accepted_snapshot=value)
            )
        elif change == "pool_halt":
            c.execute(update(pools).values(halted=True, halt_reason="OUTCOME_UNKNOWN"))
        elif change == "namespace":
            c.execute(
                update(events)
                .where(
                    events.c.kind == "PROTOCOL_POOL_INITIALIZED",
                    events.c.run_id == "protocol-request-pool.v1:offline",
                )
                .values(id="event_" + "f" * 32)
            )
        elif change == "revoke":
            c.execute(update(grants).where(grants.c.project_id == p["pid"]).values(revoked=True))
        elif change == "pending_operation":
            from sim2act.db import operations

            c.execute(
                operations.insert().values(
                    id="op_pending",
                    run_id=rid,
                    call_id="pending",
                    tool_ref="resource.read",
                    status="OUTCOME_UNKNOWN",
                )
            )
    if change in {"sidecar_origin", "provider_halt"}:
        value = json.loads(path.read_text())
        if change == "provider_halt":
            value["halted"] = True
        else:
            value["slots"][0]["protocol_origin_v2"]["attempt_id"] = "other-attempt"
        path.write_text(json.dumps(value))
    elif change == "provider_usage_missing":
        value = json.loads(path.read_text())
        del value["slots"][0]["normalized_usage_v2"]
        path.write_text(json.dumps(value))
    elif change in {"coherent_cross_run", "genuine_v1_shape"}:
        value = json.loads(path.read_text())
        with store.tx() as c:
            a = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().one()
            params = copy.deepcopy(a["parameters"])
            if change == "coherent_cross_run":
                origin = copy.deepcopy(params["extract_origin_v2"])
                origin["run_id"] = p["source"]["run_id"]
                params["extract_origin_v2"] = origin
                value["slots"][0]["protocol_origin_v2"] = origin
                c.execute(
                    update(events)
                    .where(events.c.run_id.in_([rid, a["id"]]), events.c.kind == ORIGIN)
                    .values(data=origin)
                )
            else:
                params.pop("extract_origin_v2")
                r = params["protocol_candidate_receipt"]
                r["namespace"] = "protocol-attempt-receipt.v1"
                for key in (
                    "receipt_version",
                    "origin_fingerprint",
                    "safe_response_fingerprint",
                    "usage",
                ):
                    r.pop(key)
                value["slots"][0]["candidate_receipt"] = {
                    k: v
                    for k, v in r.items()
                    if k not in {"namespace", "attempt_id", "extraction_run_id"}
                }
                for key in (
                    "protocol_origin_v2",
                    "normalized_usage_v2",
                    "safe_response_fingerprint_v2",
                    "raw_response_fingerprint_v2",
                ):
                    value["slots"][0].pop(key)
                c.execute(
                    events.delete().where(
                        events.c.run_id.in_([rid, a["id"]]), events.c.kind.in_([ORIGIN, ACCEPTED])
                    )
                )
            c.execute(update(attempts).where(attempts.c.id == a["id"]).values(parameters=params))
        path.write_text(json.dumps(value))
    elif change == "sidecar_missing":
        path.unlink()
    elif change == "expired":
        p["ticks"][0] = p["current"]["created_at"] + 301
    before, sent = snapshot(store), len(p["sends"])
    before_sidecar = path.read_bytes() if path.exists() else None
    with pytest.raises(DomainError):
        recover(p, cold)
    assert snapshot(store) == before and len(p["sends"]) == sent
    assert (path.read_bytes() if path.exists() else None) == before_sidecar


def test_completion_write_failure_rolls_back_entire_group(prepared, cold):
    p, (store, _, _) = prepared, cold
    before = snapshot(store)

    def fail(c, cursor, statement, parameters, context, many):
        if statement.startswith("INSERT INTO events") and COMPLETED in str(parameters):
            raise RuntimeError("synthetic recovery receipt write failure")

    event.listen(store.engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="synthetic recovery receipt"):
            recover(p, cold)
    finally:
        event.remove(store.engine, "before_cursor_execute", fail)
    assert snapshot(store) == before


def test_owner_project_and_closed_http_input(prepared, cold):
    p, (store, settings, request) = prepared, cold
    before = snapshot(store)
    with TestClient(create_app(store, settings)) as client:
        client.headers["Authorization"] = "Bearer secret test token"
        base = f"/api/projects/{p['pid']}/protocol/runs/{p['interrupted']}/complete-extraction"
        assert client.post(base, json=dict(request, response={})).status_code == 422
        assert client.post(base, json=dict(request, expected_fence=True)).status_code == 422
        assert (
            client.post(base.replace(p["pid"], "proj_" + "f" * 32), json=request).status_code == 403
        )
        client.headers["Authorization"] = "Bearer unknown-owner"
        assert client.post(base, json=request).status_code == 403
        assert snapshot(store) == before
        client.headers["Authorization"] = "Bearer secret test token"
        response = client.post(base, json=request)
        assert response.status_code == 200, response.text
        assert response.json()["provider_requests"] == 0


@pytest.mark.parametrize("fault", ["authority", "cancel", "deadline"])
def test_final_gate_rejects_change_after_completion_writes(prepared, cold, fault):
    p, (store, _, _) = prepared, cold
    before = snapshot(store)
    fired = []

    def change(c, cursor, statement, params, context, many):
        if not fired and statement.startswith("UPDATE protocol_jobs SET result_snapshot"):
            fired.append(True)
            if fault == "authority":
                c.execute(
                    update(grants).where(grants.c.project_id == p["pid"]).values(revoked=True)
                )
            elif fault == "cancel":
                c.execute(
                    update(runs).where(runs.c.id == p["interrupted"]).values(cancel_intent=True)
                )
            else:
                p["ticks"][0] = p["current"]["created_at"] + 301

    event.listen(store.engine, "before_cursor_execute", change)
    try:
        with pytest.raises(DomainError):
            recover(p, cold)
    finally:
        event.remove(store.engine, "before_cursor_execute", change)
    assert fired and snapshot(store) == before


def test_original_protocol_cold_verifies_v2_without_downgrade(prepared):
    """Existing ordinary protocol Cold, not P-B Cold2 or a G0 window."""
    p = prepared
    before_sends = len(p["sends"])
    p["ticks"][0] = p["end"] + 40
    store = p["env"][0]
    normal = p["normal"]
    plan = normal["result"]["compiled_plan"]
    contract, _ = evaluation_contract("protocol.synthetic.a-cold.v1")
    jobs.enqueue(
        store,
        p["user"],
        p["pid"],
        "cold",
        dict(
            contract_id=contract["id"],
            extraction_run_id=normal["run_id"],
            expected_plan_fingerprint=plan["plan_fingerprint"],
            inputs=contract["expected_inputs"],
            resource_bindings={"material_0": p["b"]},
        ),
        "cold-compatible",
        LIMITS,
    )
    p["configure"]([wire(contract["expected_output"])], "cold_a")
    done = p["execute"]()
    assert done["status"] == "WAITING_APPROVAL"
    assert len(p["sends"]) == before_sends + 1


def test_actual_wire_rechecked_after_original_guard(prepared, tmp_path):
    """A trusted guard's accidental mutation cannot reach even MockTransport."""
    p = prepared
    p["ticks"][0] = p["end"] + 40
    with p["env"][0].engine.connect() as c:
        a = (
            c.execute(select(attempts).where(attempts.c.run_id == p["interrupted"]))
            .mappings()
            .one()
        )
        origin = copy.deepcopy(a["parameters"]["extract_origin_v2"])
    model = InternModel(
        replace(p["settings"], live_enabled=True, token="synthetic"),
        httpx.MockTransport(lambda request: pytest.fail("Changed wire reached transport")),
    )
    scope = origin["provider_scope_fingerprint"]
    with p["env"][0].engine.connect() as c:
        accepted = c.execute(
            select(protocol_jobs.c.accepted_snapshot).where(
                protocol_jobs.c.run_id == p["interrupted"]
            )
        ).scalar_one()
    assert fingerprint(accepted["scope"]) == scope
    path = tmp_path / "guard-only.json"
    initialize_ledger(path, accepted["scope"])
    provider = BudgetedProvider(
        model,
        path,
        accepted["scope"],
        "extract_a",
        authorize=lambda value: True,
        clock=lambda: p["ticks"][0],
    )

    def change(request):
        if request.headers.get("Authorization"):
            request._content = b"{}"  # Explicit test-only accidental callback mutation.

    provider.wire_guard = change
    with pytest.raises(DomainError, match="guard changed the wire"):
        provider.call(p["current"]["context"]["messages"], [], request_binding=origin)
    data = json.loads(path.read_text())
    assert data["halted"] and data["slots"][0]["status"] == "FAILED_OR_UNKNOWN"


def test_experiment_settlement_matches_and_is_preserved(prepared, tmp_path, monkeypatch):
    """Separate genuine controller-bound source/extract: three Mock requests."""
    from sim2act.protocol_experiment import SETTLED, advance, bind_run, initialize_experiment

    p = prepared
    before_sends = len(p["sends"])
    root = tmp_path / "experiment"
    root.mkdir()
    p["ticks"][0] = p["end"] + 50
    gen = jobs_env.__wrapped__(root)
    env = next(gen)
    store, user, pid, a, _, worker, _ = env
    worker.protocol_clock = lambda: p["ticks"][0]

    def configure(replies, stage):
        pending = list(replies)

        def factory(worker, run, snapshot):
            def transport(request):
                assert len(p["sends"]) < 8
                p["sends"].append(dict(run=run["id"], body=request.content.hex()))
                p["ticks"][0] += 7
                return httpx.Response(200, json=pending.pop(0))

            model = InternModel(
                replace(worker.s, live_enabled=True, token="synthetic"),
                httpx.MockTransport(transport),
            )
            path = root / (run["id"] + ".json")
            initialize_ledger(path, snapshot["scope"])

            def authorize(scope):
                with store.tx() as c:
                    store.guard(c, run["id"], run["fence"])
                    for ref in scope["resource_ids"]:
                        store.authorize(c, user, run["runtime_id"], pid, ref, "resource.read")
                return True

            provider = BudgetedProvider(
                model,
                path,
                snapshot["scope"],
                stage,
                authorize=authorize,
                clock=worker.protocol_clock,
            )
            runner = ProtocolAttemptRunner(worker, run, snapshot, provider)
            call = runner.call

            def scheduled(messages, tools):
                p["ticks"][0] += 7  # Same explicit controller clock, no waiting.
                return call(messages, tools)

            runner.call = scheduled
            return runner

        worker.protocol_runner_factory = factory

    try:
        exp = initialize_experiment(store, user, pid, "known-completion", request_limit=14)
        source = jobs.enqueue(store, user, pid, "source", source_payload(a), "source", LIMITS)
        bind_run(store, user, exp["experiment_id"], source["run_id"], clock=worker.protocol_clock)
        contract, _ = evaluation_contract("protocol.synthetic.a-source.v1")
        configure([wire(rid=a), wire(contract["expected_output"])], "source_a")
        first = store.claim(worker.id, 30)
        jobs.process_job(worker, first)
        done = jobs.inspect(store, user, source["run_id"])
        review(
            store,
            user,
            source["run_id"],
            dict(
                contract_id=contract["id"],
                expected_result_fingerprint=done["result_fingerprint"],
                expected_fence=done["fence"],
                expected_version=done["version"],
                request_key="review",
            ),
        )
        advance(store, user, exp["experiment_id"], source["run_id"], clock=worker.protocol_clock)
        done = jobs.inspect(store, user, source["run_id"])
        extracted = jobs.enqueue(
            store,
            user,
            pid,
            "extract",
            dict(
                source_run_id=source["run_id"],
                expected_source_fingerprint=done["result_fingerprint"],
            ),
            "extract",
            LIMITS,
        )
        rid = extracted["run_id"]
        bind_run(store, user, exp["experiment_id"], rid, clock=worker.protocol_clock)
        configure([wire(candidate_for(contract_snapshot(contract["id"]), [a]))], "extract_a")
        with monkeypatch.context() as cut:

            def stop(*args):
                raise Interrupted()

            cut.setattr(jobs, "complete_in_tx", stop)
            claimed = store.claim(worker.id, 30)
            with pytest.raises(Interrupted):
                jobs.process_job(worker, claimed)
        p["ticks"][0] += 31
        req = dict(
            expected_version=claimed["version"],
            expected_fence=claimed["fence"],
            request_key="complete",
        )
        # Negative clone changes only one independent experiment settlement.
        bad_root = tmp_path / "bad-experiment"
        bad_root.mkdir()
        import sqlite3

        with store.engine.connect() as c, sqlite3.connect(bad_root / "db.sqlite") as dst:
            c.connection.driver_connection.backup(dst)
        for suffix in (".json", ".lock"):
            shutil.copyfile(root / (rid + suffix), bad_root / (rid + suffix))
        bad = Store("sqlite:///" + str(bad_root / "db.sqlite"), test_only=True)
        try:
            with bad.tx() as c:
                row = (
                    c.execute(
                        select(events).where(
                            events.c.run_id == exp["experiment_id"], events.c.kind == SETTLED
                        )
                    )
                    .mappings()
                    .first()
                )
                value = copy.deepcopy(row["data"])
                value["value"]["slot_result_fingerprint"] = "0" * 64
                c.execute(update(events).where(events.c.id == row["id"]).values(data=value))
            before_bad = snapshot(bad)
            with pytest.raises(DomainError):
                complete_extract(bad, user, rid, req, replace(worker.s, data_dir=bad_root))
            assert snapshot(bad) == before_bad
        finally:
            bad.engine.dispose()
        before, sent = snapshot(store), len(p["sends"])

        def no_send(*args, **kwargs):
            pytest.fail("Experiment completion tried to send/reserve/accept")

        with monkeypatch.context() as guard:
            guard.setattr(BudgetedProvider, "call", no_send)
            guard.setattr(Worker, "reserve", no_send)
            guard.setattr(BudgetedProvider, "accept_candidate", no_send)
            reply = complete_extract(store, user, rid, req, worker.s)
        assert reply["status"] == "SUCCEEDED" and reply["provider_requests"] == 0
        assert len(p["sends"]) == sent == before_sends + 3
        after = snapshot(store)
        assert {k for k in before if before[k] != after[k]} == {"runs", "protocol_jobs", "events"}
        # Experiment send/settlement/advance/halt facts are preserved verbatim.
        with store.engine.connect() as c:
            witness = c.execute(
                select(events.c.data).where(events.c.run_id == rid, events.c.kind == ACCEPTED)
            ).scalar_one()
            assert witness["experiment"]["send"]["attempt_id"] == witness["origin"]["attempt_id"]
        advance(store, user, exp["experiment_id"], rid, clock=worker.protocol_clock)
        assert complete_extract(store, user, rid, req, worker.s)["cached"] is True
        plan = jobs.inspect(store, user, rid)["result"]["compiled_plan"]
        contract, _ = evaluation_contract("protocol.synthetic.a-cold.v1")
        cold = jobs.enqueue(
            store,
            user,
            pid,
            "cold",
            dict(
                contract_id=contract["id"],
                extraction_run_id=rid,
                expected_plan_fingerprint=plan["plan_fingerprint"],
                inputs=contract["expected_inputs"],
                resource_bindings={"material_0": env[4]},
            ),
            "cold-history",
            LIMITS,
        )
        bind_run(store, user, exp["experiment_id"], cold["run_id"], clock=worker.protocol_clock)
        configure([], "cold_a")
        claimed = store.claim(worker.id, 30)
        with store.engine.connect() as c:
            accepted = c.execute(
                select(protocol_jobs.c.accepted_snapshot).where(
                    protocol_jobs.c.run_id == cold["run_id"]
                )
            ).scalar_one()
        adapter = worker.protocol_runner_factory(worker, claimed, accepted)
        before_audit = snapshot(store)
        assert (
            adapter.verify_candidate_receipt(
                plan["candidate_receipt"],
                plan["candidate_fingerprint"],
                plan["source_proof_fingerprint"],
            )
            is True
        )
        assert snapshot(store) == before_audit and len(p["sends"]) == sent
    finally:
        with pytest.raises(StopIteration):
            next(gen)
