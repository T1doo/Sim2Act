"""Actual SQLite/HTTP contract draft for closing an unaccepted P-B key.

No product execution is performed while authoring this file. On qualification,
the shared fresh seed uses only existing synthetic generation/Worker transports.
"""

import copy
import hashlib
import json
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sql_private_barrier import PrivateReadBarrier
from sqlalchemy import delete, event, select
from test_natural_spec_apps import COLD, SOURCE, enqueue, material, ready, transport
from test_pa_natural_spec_ui import _PageObserver
from test_spec_app_operations import snapshot

from sim2act import natural_specs as natural
from sim2act import pb_natural_specs as pb
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import (
    Store,
    delivery_graph_requests,
    events,
    fingerprint,
    internal_run_bindings,
    runs,
    task_extractions,
)
from sim2act.worker import Worker

IDENTITY_NAMESPACE = "pb-natural-extraction-recovery.v1"
TERMINAL_NAMESPACE = "pb-natural-spec-extraction-terminal.v1"
TERMINAL_KIND = "pb_natural_spec_terminal"
CLOSE_CONSENT = "CLOSE_ONLY_THIS_UNACCEPTED_PB_EXTRACTION_KEY"
ORIGINAL_KEY = "11111111-1111-4111-8111-111111111111"
IDENTITY_FIELDS = set("namespace principal_id project_id source_app_id source_instance_id source_run_id "
    "source_app_run_id source_release_id source_release_fingerprint source_result_version request_key "
    "request_fingerprint review_fingerprint candidate_fingerprint app_id runtime_id source_proof_fingerprint".split())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def sources():
    root = Path.cwd().resolve()
    paths = sorted(path for path in (root / "src/sim2act").rglob("*")
        if path.is_file() and path.suffix in {".py", ".js", ".css", ".html"})
    paths += [Path(__file__).resolve(), *[root / "tests" / name for name in [
        "test_natural_spec_apps.py", "test_pa_spec_apps.py", "test_goal_text_applications.py",
        "test_pa_natural_spec_ui.py", "test_spec_app_operations.py", "sql_private_barrier.py"]]]
    return {str(path.relative_to(root)) if path.is_relative_to(root) else str(path):
        dict(bytes=path.stat().st_size, sha256=sha(path)) for path in paths}


def ok(reply, status=200):
    assert reply.status_code == status, reply.text
    return reply.json()


def error(reply, status, code):
    assert reply.status_code == status, reply.text
    assert reply.json()["error"]["code"] == code, reply.text
    return reply.json()


def trace_http(client, observer, wire_lock):
    def trace(reply):
        reply.read()
        request = reply.request
        raw = request.content
        with wire_lock:
            observer.http_response(dict(method=request.method, path=request.url.raw_path.decode("ascii"),
                body=json.loads(raw) if raw else None), reply)
            name = f"http/{observer.http_serial:06d}-request.body"
            (observer.folder / name).write_bytes(raw)
            observer.save(f"http/{observer.http_serial:06d}-request-bytes.json", dict(
                file=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    client.event_hooks["response"].append(trace)


def source_header(store, rid):
    with store.tx() as connection:
        header = dict(connection.execute(select(runs).where(runs.c.id == rid)).mappings().one())
        clock = connection.execute(select(internal_run_bindings.c.snapshot["natural_spec_clock"])
            .where(internal_run_bindings.c.run_id == rid)).scalar_one()
        claims = [dict(row) for row in connection.execute(select(events).where(
            events.c.run_id == rid, events.c.kind == "CLAIMED")).mappings()]
    return dict(header=header, clock=clock, claims=claims)


def identity_for(checked, commit):
    proof = checked["source_proof"]
    value = dict(namespace=IDENTITY_NAMESPACE, principal_id=checked["principal_id"],
        project_id=checked["project_id"], source_app_id=proof["source_app_id"],
        source_instance_id=proof["instance_id"], source_run_id=proof["source_run_id"],
        source_app_run_id=proof["app_run_id"], source_release_id=proof["release_id"],
        source_release_fingerprint=proof["release_fingerprint"], source_result_version=proof["result_version"],
        request_key=commit["review"]["request_key"], request_fingerprint=fingerprint(commit),
        review_fingerprint=checked["review_fingerprint"], candidate_fingerprint=checked["candidate_fingerprint"],
        app_id=checked["app_id"], runtime_id=checked["runtime_id"],
        source_proof_fingerprint=checked["source_proof_fingerprint"])
    assert set(value) == IDENTITY_FIELDS
    assert all(type(item) in {str, int} for item in value.values())
    return value


@pytest.fixture(scope="module")
def pb_extraction_close_seed(tmp_path_factory):
    folder = tmp_path_factory.mktemp("pb-extraction-close-fresh-source-seed")
    database, sealed = folder / "fixture.db", folder / "sealed-source.db"
    settings = Settings("sqlite:///" + str(database), folder, mode="mock", goal_planner_provider="intern-s2")
    store = Store(settings.database_url, test_only=True)
    client = None
    seed = source_run = None
    with _PageObserver(folder, "PB_CLOSE_FRESH_SOURCE_GEN3_WORKER1") as observer:
        before_sources = sources()
        observer.save("source-before.json", before_sources)
        try:
            store.initialize()
            owner = store.user("P-B close fixture A", "synthetic-test-A")
            store.user("P-B close fixture B", "synthetic-test-B")
            client = TestClient(create_app(store, settings), raise_server_exceptions=False)
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            trace_http(client, observer, threading.Lock())
            project = ok(client.post("/api/projects", json=dict(name="P-B close fresh source")), 201)["id"]
            source_resource, source_card = material(client, project, SOURCE)
            data = store, settings, client, owner, project, source_resource, source_card
            import test_natural_spec_apps as original_fixture
            original_transport = original_fixture.httpx.MockTransport

            def observed_transport(handler):
                def observe_request(request):
                    observer.sent.append(json.loads(request.content))
                    return handler(request)
                return original_transport(observe_request)

            fixture_httpx = SimpleNamespace(MockTransport=observed_transport,
                Response=original_fixture.httpx.Response)
            with observer.phase("normal_generation_explicit_release_instance"):
                with patch.object(original_fixture, "httpx", fixture_httpx):
                    generation_run, app, release, instance, returned_wire = ready(data, "single")
            assert returned_wire == observer.sent and len(observer.sent) == 3
            source_run = enqueue(data, release, instance, key="pb-close-source-once")
            before = source_header(store, source_run)
            observer.save("source-worker-before.json", before)
            assert before["header"]["status"] == "QUEUED" and not before["claims"]
            with observer.phase("normal_source_worker_once", run_id=source_run):
                claimed = Worker(store, settings,
                    goal_planner_transport=transport(observer.runtime_sent, SOURCE)).once()
            after = source_header(store, source_run)
            observer.save("source-worker-claims.json", dict(before=before, after=after,
                once_returned=claimed, worker_calls=1, lease_or_clock_mutations=0))
            assert claimed and after["header"]["status"] == "SUCCEEDED"
            assert len(after["claims"]) == 1 and len(observer.runtime_sent) == 1
            assert before["clock"] == after["clock"]
            assert before["header"]["created_at"] == after["header"]["created_at"]
            target_resource, target_card = material(client, project, COLD, "Independent close target")
            path = f"/api/projects/{project}/natural-spec-task-runs/{source_run}"
            options = ok(client.get(path + "/extraction-options"))
            body = dict(source_run_id=source_run,
                expected_source_proof_fingerprint=options["source_proof_fingerprint"],
                expected_source_recipe_fingerprint=options["recipe_fingerprint"],
                card_id=target_card["id"], expected_goal_version=target_card["version"],
                expected_goal_fingerprint=target_card["fingerprint"],
                expected_source_hash=hashlib.sha256(COLD.encode()).hexdigest(),
                recipe=copy.deepcopy(options["recipe"]), name="Explicit unaccepted P-B extraction", request_key=ORIGINAL_KEY)
            before_review = snapshot(store)
            checked = ok(client.post(path + "/extraction-reviews", json=body))
            assert snapshot(store) == before_review, "The seed review is actually read-only"
            commit = dict(review=body, expected_review_fingerprint=checked["review_fingerprint"],
                consent=pb.CONSENT, artifact_write_consent=natural.CONSENT)
            artifact = ok(client.get(f"/api/internal/app-run-jobs/{source_run}/spec-artifact"))
            app_value = ok(client.get("/api/apps/" + app))
            proof = options["source_proof"]
            seed = dict(settings=settings, sealed=sealed, seed_folder=folder, rows=snapshot(store),
                identity=identity_for(checked, commit), review=checked, commit=commit, source_app=app_value,
                source_card=source_card, target_card=target_card, options=options, generation_run=generation_run,
                info=dict(project=project, principal=owner, source_app=app, source_name=app_value["name"],
                    source_instance=instance["id"], source_run=source_run, source_app_run=proof["app_run_id"],
                    source_release=release["id"], source_release_fingerprint=release["fingerprint"],
                    source_result_version=proof["result_version"], source_resource=source_resource,
                    source_artifact=artifact["resource"]["resource_id"], target_card=target_card["id"],
                    target_resource=target_resource, target_hash=hashlib.sha256(COLD.encode()).hexdigest(),
                    source_content=SOURCE, target_content=COLD))
            observer.save("seed-proof.json", dict(info=seed["info"], identity=seed["identity"],
                review=checked, commit=commit, generation_run=generation_run,
                generation_mock_requests=3, source_mock_requests=1, source_worker_calls=1,
                real_model_requests=0, fabricated_success_rows=0, lease_or_clock_changes=0))
            observer.save("seed-rows.json", seed["rows"])
            assert sources() == before_sources
        finally:
            observer.save("source-after.json", sources())
            try:
                observer.save("fixture-final-rows.json", snapshot(store))
                if source_run is not None:
                    observer.save("source-worker-finally.json", source_header(store, source_run))
            except Exception as failure:
                observer.save("fixture-final-observation-error.json", dict(
                    exception_type=type(failure).__name__, exception=str(failure)))
            if client is not None:
                client.close()
            store.engine.dispose()
        assert seed is not None and not Path(str(database) + "-wal").exists()
        shutil.copy2(database, sealed)
        seed["seed_sha256"] = sha(sealed)
        assert sha(database) == seed["seed_sha256"]
        observer.save("seed-copy-provenance.json", dict(original=str(database), sealed=str(sealed),
            bytes=sealed.stat().st_size, original_sha256=sha(database), sealed_sha256=sha(sealed),
            method="SHUTIL_COPY2_CLOSED_SQLITE_MAIN_FILE", all_owned_connections_closed=True,
            copy_row_mutations=0))
    return seed


class CloseCase:
    """Reusable exact clone and actual HTTP trace for backend/UI bridge authors."""

    def __init__(self, seed, folder, observer):
        folder.mkdir(parents=True, exist_ok=True)
        self.seed, self.folder, self.observer = seed, folder, observer
        self.database = folder / "fixture.db"
        shutil.copy2(seed["sealed"], self.database)
        assert sha(self.database) == seed["seed_sha256"]
        self.settings = replace(seed["settings"], database_url="sqlite:///" + str(self.database), data_dir=folder)
        self.store = Store(self.settings.database_url, test_only=True)
        assert snapshot(self.store) == seed["rows"]
        self.info = copy.deepcopy(seed["info"])
        self.identity, self.commit = copy.deepcopy(seed["identity"]), copy.deepcopy(seed["commit"])
        self.path = f"/api/projects/{self.info['project']}/natural-spec-task-runs/{self.info['source_run']}"
        self.wire_lock = threading.Lock()
        self.client = self.new_client(self.store)
        self.extra_stores, self.extra_clients = [], []
        save(folder / "clone-provenance.json", dict(source=str(seed["sealed"]), target=str(self.database),
            before_open_sha256=seed["seed_sha256"], byte_identical=True, all_rows_identical=True,
            copy_method="SHUTIL_COPY2", fabricated_success_rows=0, clock_or_lease_changes=0))

    def new_client(self, store, token="synthetic-test-A"):
        client = TestClient(create_app(store, self.settings), raise_server_exceptions=False)
        client.headers["Authorization"] = "Bearer " + token
        trace_http(client, self.observer, self.wire_lock)
        return client

    def cold(self, token="synthetic-test-A"):
        store = Store(self.settings.database_url, test_only=True)
        client = self.new_client(store, token)
        self.extra_stores.append(store)
        self.extra_clients.append(client)
        return store, client

    def by_key(self, identity=None):
        identity = identity or self.identity
        return self.path + "/extractions/by-key/" + identity["request_key"]

    def close_body(self, identity=None):
        return dict(identity=copy.deepcopy(identity or self.identity), consent=CLOSE_CONSENT)

    def close(self, identity=None, client=None):
        return (client or self.client).post(self.by_key(identity) + "/close", json=self.close_body(identity))

    def read(self, client=None):
        return (client or self.client).get(self.by_key())

    def submit(self, body=None, client=None):
        return (client or self.client).post(self.path + "/extractions", json=body or self.commit)

    def revoke_read(self, resource, runtime):
        grants = ok(self.client.get(f"/api/projects/{self.info['project']}/grants"))
        rows = [row for row in grants if row["principal_id"] == runtime and row["resource_id"] == resource
            and row["tool_ref"] == "resource.read" and not row["revoked"]]
        assert len(rows) == 1, rows
        row = rows[0]
        result = ok(self.client.post(f"/api/grants/{row['id']}/revoke", json=dict(command="revoke", version=row["revision"])))
        return dict(before=row, receipt=result)

    def __enter__(self):
        self.source_before = sources()
        save(self.folder / "source-before.json", self.source_before)
        return self

    def __exit__(self, kind, value, tb):
        try:
            save(self.folder / "final-rows.json", snapshot(self.store))
            save(self.folder / "source-after.json", sources())
            save(self.folder / "case-summary.json", dict(passed=kind is None,
                exception_type=kind.__name__ if kind else None, exception=str(value) if value else None,
                source_inputs_unchanged=sources() == self.source_before,
                real_model_requests=0, test_worker_calls=0, shared_fixture_mock_requests=4,
                mock_request_scope="ONE_MODULE_FRESH_SEED_NOT_REPEATED_PER_CASE",
                native_browser="NOT_RUN", windows="NOT_RUN", pg="NOT_RUN", real_semantics="NOT_RUN"))
            assert sources() == self.source_before
        finally:
            for client in self.extra_clients:
                client.close()
            self.client.close()
            for store in self.extra_stores:
                store.engine.dispose()
            self.store.engine.dispose()
        return False


def assert_terminal(receipt, case):
    expected = dict(namespace=TERMINAL_NAMESPACE, status="CLOSED_NOT_ACCEPTED", acceptance="NOT_ACCEPTED",
        identity=case.identity, principal_id=case.info["principal"], project_id=case.info["project"],
        source_run_id=case.info["source_run"], request_key=case.identity["request_key"],
        request_fingerprint=fingerprint(case.commit), close_request_fingerprint=fingerprint(case.close_body()),
        new_model_requests=0, project_writes=0, metadata_writes=2, formal_publication_enabled=False)
    assert receipt == {**expected, "receipt_fingerprint": fingerprint(expected)}
    assert receipt["request_fingerprint"] == receipt["identity"]["request_fingerprint"]
    assert "request" not in receipt and "reviewed" not in receipt and "candidate" not in receipt
    return receipt


def assert_only_terminal(before, after, case):
    assert before.keys() == after.keys()
    for table in before:
        if table != "delivery_graph_requests":
            assert before[table] == after[table], table
    assert all(row in after["delivery_graph_requests"] for row in before["delivery_graph_requests"])
    added = [row for row in after["delivery_graph_requests"] if row not in before["delivery_graph_requests"]]
    assert len(added) == 2
    assert {row["kind"] for row in added} == {TERMINAL_KIND, TERMINAL_KIND + "_seal"}
    assert all(row["app_id"] == case.info["source_run"] and row["principal_id"] == case.info["principal"]
        and row["request_key"] == case.identity["request_key"]
        and row["request_fingerprint"] == fingerprint(case.close_body())
        and row["fingerprint"] == fingerprint(row["snapshot"]) for row in added)
    assert added[0]["snapshot"] == added[1]["snapshot"]
    return added


def test_unaccepted_close_is_durable_and_rejects_late_original_or_changed_post(pb_extraction_close_seed, tmp_path):
    with _PageObserver(tmp_path, "PB_CLOSE_ORIGINAL_KEY") as observer:
        with CloseCase(pb_extraction_close_seed, tmp_path / "case", observer) as case:
            baseline = snapshot(case.store)
            error(case.read(), 400, "OUTCOME_UNKNOWN")
            assert snapshot(case.store) == baseline
            receipt = assert_terminal(ok(case.close()), case)
            closed = snapshot(case.store)
            assert_only_terminal(baseline, closed, case)
            assert ok(case.read()) == receipt and ok(case.close()) == receipt
            cold_store, cold_client = case.cold()
            assert ok(case.read(cold_client)) == receipt
            error(case.submit(client=cold_client), 409, "VERSION_CONFLICT")
            changed = copy.deepcopy(case.commit)
            changed["review"]["name"] = "Late changed body must also remain permanently closed"
            error(case.submit(changed), 409, "VERSION_CONFLICT")
            mismatch = copy.deepcopy(case.identity)
            mismatch["request_fingerprint"] = "0" * 64
            error(case.close(mismatch), 409, "VERSION_CONFLICT")
            assert snapshot(cold_store) == closed
            observer.save("terminal-receipt.json", receipt)


def test_unaccepted_close_survives_invalidated_target_without_reading_it(pb_extraction_close_seed, tmp_path):
    with _PageObserver(tmp_path, "PB_CLOSE_TARGET_INDEPENDENT") as observer:
        with CloseCase(pb_extraction_close_seed, tmp_path / "case", observer) as case:
            card = ok(case.client.get("/api/goal-cards/" + case.info["target_card"]))
            body = dict(card["content"], expected_version=card["version"])
            body["title"] += " — explicitly changed after the original review"
            updated = ok(case.client.put("/api/goal-cards/" + card["id"], json=body))
            revoked = case.revoke_read(case.info["target_resource"], case.info["principal"])
            baseline = snapshot(case.store)
            with PrivateReadBarrier(case.store, set(), {case.info["target_resource"]}) as barrier:
                receipt = assert_terminal(ok(case.close()), case)
                assert ok(case.read()) == receipt
                error(case.submit(), 409, "VERSION_CONFLICT")
                assert not barrier.blocked
                observer.save("target-read-barrier.json", dict(blocked=barrier.blocked,
                    evaluated=barrier.evaluated, statements=barrier.statements))
            assert_only_terminal(baseline, snapshot(case.store), case)
            observer.save("target-invalidated.json", dict(goal_update=updated, read_revocation=revoked, receipt=receipt))


def test_already_accepted_extraction_cannot_be_closed_or_modified(pb_extraction_close_seed, tmp_path):
    with _PageObserver(tmp_path, "PB_CLOSE_ACCEPTED_REFUSED") as observer:
        with CloseCase(pb_extraction_close_seed, tmp_path / "case", observer) as case:
            accepted = ok(case.submit(), 201)
            baseline = snapshot(case.store)
            error(case.close(), 409, "VERSION_CONFLICT")
            assert ok(case.read()) == accepted
            assert ok(case.submit(), 201) == accepted
            assert snapshot(case.store) == baseline
            assert not [row for row in baseline["delivery_graph_requests"] if row["kind"] == TERMINAL_KIND]
            observer.save("accepted-receipt-preserved.json", accepted)


@pytest.mark.parametrize("winner", ["close", "submit"], ids=["close-first", "post-first"])
def test_real_two_connection_close_and_submit_serialize(pb_extraction_close_seed, tmp_path, winner, monkeypatch):
    with _PageObserver(tmp_path, "PB_CLOSE_RACE_" + winner.upper()) as observer:
        with CloseCase(pb_extraction_close_seed, tmp_path / "case", observer) as case:
            baseline = snapshot(case.store)
            second_store, second_client = case.cold()
            first_locked, release_first, second_begin, second_began = [threading.Event() for _ in range(4)]
            log, log_lock = [], threading.Lock()
            original_lock = case.store.lock_project

            def mark(kind, connection=None):
                row = dict(event=kind, thread_id=threading.get_ident())
                if connection is not None:
                    row["dbapi_connection_id"] = id(connection.connection.driver_connection)
                with log_lock:
                    log.append(row)
                    observer.save("race-events.json", log)

            def hold_after_first_project_lock(connection, principal, project):
                value = original_lock(connection, principal, project)
                mark("FIRST_PROJECT_LOCK_ACQUIRED", connection)
                first_locked.set()
                assert release_first.wait(10), "Test-owned gate must always be released in finally"
                mark("FIRST_PROJECT_LOCK_RELEASED_BY_TEST", connection)
                return value

            def before_second_begin(connection, cursor, statement, parameters, context, many):
                if statement.strip().upper() == "BEGIN IMMEDIATE":
                    mark("SECOND_BEGIN_IMMEDIATE_ATTEMPTED", connection)
                    second_begin.set()

            def after_second_begin(connection, cursor, statement, parameters, context, many):
                if statement.strip().upper() == "BEGIN IMMEDIATE":
                    mark("SECOND_BEGIN_IMMEDIATE_COMPLETED", connection)
                    second_began.set()

            def request(actor, client):
                mark("REQUEST_STARTED_" + actor.upper())
                reply = case.close(client=client) if actor == "close" else case.submit(client=client)
                mark("REQUEST_RETURNED_" + actor.upper())
                return reply

            monkeypatch.setattr(case.store, "lock_project", hold_after_first_project_lock)
            event.listen(second_store.engine, "before_cursor_execute", before_second_begin)
            event.listen(second_store.engine, "after_cursor_execute", after_second_begin)
            try:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    first = pool.submit(request, winner, case.client)
                    try:
                        assert first_locked.wait(10)
                        second = pool.submit(request, "submit" if winner == "close" else "close", second_client)
                        assert second_begin.wait(10), "Second real connection must reach BEGIN while first lock is held"
                        assert not second_began.is_set() and not first.done() and not second.done()
                        mark("OVERLAP_PROVED_FIRST_LOCK_HELD_SECOND_BEGIN_INCOMPLETE")
                    finally:
                        release_first.set()
                    a, b = first.result(timeout=30), second.result(timeout=30)
            finally:
                release_first.set()
                monkeypatch.setattr(case.store, "lock_project", original_lock)
                event.remove(second_store.engine, "before_cursor_execute", before_second_begin)
                event.remove(second_store.engine, "after_cursor_execute", after_second_begin)
                observer.save("race-events.json", log)
            assert second_began.is_set()
            held = next(row for row in log if row["event"] == "FIRST_PROJECT_LOCK_ACQUIRED")
            attempted = next(row for row in log if row["event"] == "SECOND_BEGIN_IMMEDIATE_ATTEMPTED")
            assert held["dbapi_connection_id"] != attempted["dbapi_connection_id"]
            assert held["thread_id"] != attempted["thread_id"]
            if winner == "close":
                receipt = assert_terminal(ok(a), case)
                error(b, 409, "VERSION_CONFLICT")
                assert ok(case.read()) == receipt
                assert_only_terminal(baseline, snapshot(case.store), case)
            else:
                accepted = ok(a, 201)
                error(b, 409, "VERSION_CONFLICT")
                assert ok(case.read()) == accepted
                assert len(snapshot(case.store)["task_extractions"]) == len(baseline["task_extractions"]) + 1
                assert not [row for row in snapshot(case.store)["delivery_graph_requests"] if row["kind"] == TERMINAL_KIND]


def test_source_authority_tenant_and_exact_identity_gate_close(pb_extraction_close_seed, tmp_path):
    with _PageObserver(tmp_path, "PB_CLOSE_SCOPE_AND_AUTHORITY") as observer:
        with CloseCase(pb_extraction_close_seed, tmp_path / "case", observer) as case:
            other_project = ok(case.client.post("/api/projects", json=dict(name="Explicit wrong-project close scope probe")), 201)["id"]
            baseline = snapshot(case.store)
            _, foreign = case.cold("synthetic-test-B")
            with PrivateReadBarrier(case.store, {case.info["source_run"]},
                    {case.info["source_resource"], case.info["source_artifact"]}) as barrier:
                barrier.attach(case.extra_stores[-1])
                error(case.close(client=foreign), 403, "PERMISSION_DENIED")
                error(case.read(foreign), 403, "PERMISSION_DENIED")
                wrong_path = case.by_key().replace(case.info["project"], other_project)
                wrong = case.client.post(wrong_path + "/close", json=case.close_body())
                assert wrong.status_code in {403, 409}, wrong.text
                assert wrong.json()["error"]["code"] == ("PERMISSION_DENIED" if wrong.status_code == 403 else "VERSION_CONFLICT")
                assert not barrier.blocked
                observer.save("foreign-private-read-barrier.json", dict(blocked=barrier.blocked, statements=barrier.statements))
            assert snapshot(case.store) == baseline
            for field, value in [("source_instance_id", "iinstance_" + "0" * 32),
                    ("source_proof_fingerprint", "0" * 64), ("source_result_version", case.identity["source_result_version"] + 1)]:
                identity = {**case.identity, field: value}
                error(case.close(identity), 409, "VERSION_CONFLICT")
                assert snapshot(case.store) == baseline
            malformed = case.close_body()
            malformed["identity"]["token"] = "MUST_NOT_BE_ACCEPTED_OR_PERSISTED"
            assert case.client.post(case.by_key() + "/close", json=malformed).status_code == 422
            assert snapshot(case.store) == baseline
            revoked = case.revoke_read(case.info["source_resource"], case.seed["source_app"]["runtime_id"])
            revoked_baseline = snapshot(case.store)
            with PrivateReadBarrier(case.store, {case.info["source_run"]},
                    {case.info["source_resource"], case.info["source_artifact"]}) as barrier:
                error(case.close(), 403, "PERMISSION_DENIED")
                error(case.read(), 403, "PERMISSION_DENIED")
                assert not barrier.blocked
                observer.save("revoked-private-read-barrier.json", dict(revocation=revoked,
                    blocked=barrier.blocked, statements=barrier.statements))
            assert snapshot(case.store) == revoked_baseline

        with CloseCase(pb_extraction_close_seed, tmp_path / "changed-source-goal", observer) as case:
            card = ok(case.client.get("/api/goal-cards/" + case.seed["source_card"]["id"]))
            body = dict(card["content"], expected_version=card["version"])
            body["title"] += " — changed current source Goal after original intent"
            changed = ok(case.client.put("/api/goal-cards/" + card["id"], json=body))
            baseline = snapshot(case.store)
            error(case.close(), 409, "VERSION_CONFLICT")
            assert snapshot(case.store) == baseline
            save(case.folder / "source-goal-drift.json", dict(change=changed, original_identity=case.identity,
                terminal_written=False, all_rows_unchanged_by_refused_close=True))


def test_partial_acceptance_terminal_corruption_and_rollback_are_not_absence(pb_extraction_close_seed, tmp_path):
    with _PageObserver(tmp_path, "PB_CLOSE_CORRUPTION_AND_ROLLBACK") as observer:
        # Each residual starts with a genuinely committed ordinary extraction.
        # Only the named synthetic damage is then applied; success is never forged.
        for residual in ["single-extract-seal", "derived-app-runtime-only"]:
            with CloseCase(pb_extraction_close_seed, tmp_path / residual, observer) as case:
                accepted = ok(case.submit(), 201)
                with case.store.tx() as connection:
                    connection.execute(delete(task_extractions).where(task_extractions.c.app_id == accepted["id"]))
                    kinds = [pb.EXTRACT] if residual == "single-extract-seal" else [
                        pb.EXTRACT, pb.EXTRACT + "_seal", pb.META, pb.META + "_seal"]
                    connection.execute(delete(delivery_graph_requests).where(
                        delivery_graph_requests.c.app_id == accepted["id"], delivery_graph_requests.c.kind.in_(kinds)))
                baseline = snapshot(case.store)
                error(case.close(), 400, "OUTCOME_UNKNOWN")
                assert snapshot(case.store) == baseline
                if residual == "derived-app-runtime-only":
                    spoofed = {**case.identity, "app_id": "app_" + "0" * 32,
                        "runtime_id": "appruntime_" + "0" * 32}
                    error(case.close(spoofed), 400, "OUTCOME_UNKNOWN")
                    assert snapshot(case.store) == baseline
                assert not [row for row in baseline["delivery_graph_requests"] if row["kind"] == TERMINAL_KIND]
                save(case.folder / "named-corruption.json", dict(accepted_receipt=accepted,
                    damage=residual, removed_marker=True, removed_journal_kinds=kinds, terminal_written=False))

        with CloseCase(pb_extraction_close_seed, tmp_path / "single-terminal-seal", observer) as case:
            assert_terminal(ok(case.close()), case)
            with case.store.tx() as connection:
                removed = connection.execute(delete(delivery_graph_requests).where(
                    delivery_graph_requests.c.app_id == case.info["source_run"],
                    delivery_graph_requests.c.kind == TERMINAL_KIND + "_seal",
                    delivery_graph_requests.c.request_key == case.identity["request_key"])).rowcount
                assert removed == 1
            baseline = snapshot(case.store)
            error(case.read(), 409, "VERSION_CONFLICT")
            error(case.close(), 409, "VERSION_CONFLICT")
            error(case.submit(), 409, "VERSION_CONFLICT")
            assert snapshot(case.store) == baseline

        with CloseCase(pb_extraction_close_seed, tmp_path / "terminal-rollback", observer) as case:
            baseline = snapshot(case.store)
            inserted = []

            def fail_after_first_terminal_insert(connection, cursor, statement, parameters, context, many):
                if statement.lstrip().upper().startswith("INSERT INTO DELIVERY_GRAPH_REQUESTS"):
                    for parameter in context.compiled_parameters:
                        if parameter.get("kind") in {TERMINAL_KIND, TERMINAL_KIND + "_seal"}:
                            inserted.append(dict(kind=parameter["kind"], sql=statement))
                            raise RuntimeError("synthetic failure after one actual terminal insert")

            event.listen(case.store.engine, "after_cursor_execute", fail_after_first_terminal_insert)
            try:
                reply = case.close()
                assert reply.status_code == 500, reply.text
            finally:
                event.remove(case.store.engine, "after_cursor_execute", fail_after_first_terminal_insert)
                observer.save("rollback-insert-observation.json", inserted)
            assert len(inserted) == 1 and snapshot(case.store) == baseline
            error(case.read(), 400, "OUTCOME_UNKNOWN")
            assert_terminal(ok(case.close()), case)
            assert_only_terminal(baseline, snapshot(case.store), case)
