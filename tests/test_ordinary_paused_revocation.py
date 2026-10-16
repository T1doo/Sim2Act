"""Memory SQLite/API/Worker proof; no new process or browser recovery claim."""

import gzip
import json
import uuid

import httpx
from fastapi.testclient import TestClient
from sql_private_barrier import PrivateReadBarrier
from sqlalchemy import create_engine, select
from sqlalchemy.exc import DatabaseError
from sqlalchemy.pool import QueuePool
from test_internal_api import instance as csv_instance
from test_internal_api import release as csv_release
from test_natural_spec_apps import SOURCE, ready, setup
from test_pa_spec_apps import enqueue

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import (
    Store,
    attempts,
    events,
    grants,
    internal_app_runs,
    internal_instance_data,
    internal_instances,
    internal_run_bindings,
    local_effects,
    operations,
    runs,
)
from sim2act.worker import Worker


def test_ordinary_paused_source_revoke_read_resume_cancel(tmp_path, monkeypatch):
    url = f"sqlite:///file:paused-revoke-{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"
    # Engineering adapter: retain Store's original guards and SQL listeners,
    # but avoid SingletonThreadPool evicting the held memory anchor/API threads.
    def memory_engine(*args, **kwargs):
        return create_engine(*args, **kwargs, poolclass=QueuePool,
                             connect_args={"check_same_thread": False})

    with monkeypatch.context() as patch:
        patch.setattr("sim2act.db.create_engine", memory_engine)
        store = Store(url, test_only=True)
    anchor = store.engine.connect()  # Keep the named memory DB alive across API threads.
    store.initialize()
    assert anchor.exec_driver_sql("PRAGMA database_list").all()[0][2] == ""
    owner = store.user("memory fixture A", "synthetic-test-A")
    other = store.user("memory fixture B", "synthetic-test-B")
    settings = Settings(url, tmp_path, mode="mock", lease_seconds=30, run_seconds=300)
    fixture = TestClient(create_app(store, settings))
    fixture.headers["Authorization"] = "Bearer synthetic-test-A"
    pid = fixture.post("/api/projects", json={"name": "Paused original source"}).json()["id"]
    foreign_pid = fixture.post("/api/projects", json={"name": "Separate project"}).json()["id"]
    data = setup((store, settings, fixture, owner, other, pid, None))
    client = data[2]
    proof, calls = {}, []

    def request(method, path, body=None, expected=200):
        response = client.request(method, path, json=body)
        calls.append(dict(method=method, path=path, body=body, status=response.status_code,
                          response=response.json()))
        assert response.status_code == expected, response.text
        return response.json()

    def snapshot():
        with store.tx() as c:
            def rows(table):
                return sorted((dict(r) for r in c.execute(select(table)).mappings()),
                              key=lambda r: json.dumps(r, sort_keys=True))
            return {t.name: rows(t) for t in (runs, internal_app_runs, internal_run_bindings,
                    attempts, operations, internal_instance_data, local_effects, grants, internal_instances, events)}

    try:
        origin, app, release, instance, generation = ready(data, "sequential")
        assert len(generation) == 3
        foreign_resource = fixture.post(f"/api/projects/{foreign_pid}/resources",
            json=dict(name="other.csv", format="csv", content="amount\n1\n")).json()["id"]
        foreign_env = (store, settings, fixture, owner, other, foreign_pid, foreign_resource)
        foreign_release, _, _ = csv_release(foreign_env)
        foreign_instance = csv_instance(foreign_env, foreign_release)
        rid = enqueue(data, release, instance, key="paused-original-source-revoke")
        route = f"/api/internal/instances/{instance['id']}/runs/{rid}"
        initial = request("GET", route)
        paused = request("POST", route + "/commands", dict(command="pause", version=initial["version"]))
        assert paused["status"] == "PAUSED"
        runtime_calls = []

        def forbidden(request):
            runtime_calls.append(str(request.url))
            raise AssertionError("No runtime model request is authorized")

        worker = Worker(store, data[1], goal_planner_transport=httpx.MockTransport(forbidden))
        assert not worker.once() and not runtime_calls
        listed = request("GET", f"/api/projects/{pid}/grants")
        chosen = [g for g in listed if g["principal_id"] == instance["runtime_id"]
                  and g["resource_id"] == data[5] and g["tool_ref"] == "resource.read"
                  and not g["revoked"]]
        assert len(chosen) == 1
        grant = chosen[0]
        request("POST", f"/api/grants/{grant['id']}/revoke", dict(command="revoke", version=grant["revision"]))
        revoked = snapshot()
        assert next(g for g in revoked["grants"] if g["id"] == grant["id"])["revoked"]
        with PrivateReadBarrier(store, {origin, rid}, {data[5]}) as barrier:
            for path in [route, f"/api/internal/instances/{instance['id']}",
                         f"/api/internal/instances/{instance['id']}/spec-run-requests/paused-original-source-revoke"]:
                request("GET", path, expected=403)
            control = request("GET", route + "/control-status")
            assert control["id"] == rid and control["status"] == "PAUSED"
            assert control["content_access"] is False
            assert set(control) <= {"namespace", "formal_publication_enabled", "id", "instance_id",
                                    "status", "version", "cancel_intent", "content_access"}
            request("POST", route + "/commands", dict(command="resume", version=control["version"]), 403)
            client.headers["Authorization"] = "Bearer synthetic-test-B"
            request("GET", route + "/control-status", expected=403)
            request("POST", route + "/commands", dict(command="cancel", version=control["version"]), 403)
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            wrong = f"/api/internal/instances/{foreign_instance['id']}/runs/{rid}"
            request("GET", wrong + "/control-status", expected=403)
            request("POST", wrong + "/commands", dict(command="cancel", version=control["version"]), 403)
            assert not barrier.blocked and not barrier.evaluated
            proof["private_reads_before_cancel"] = dict(blocked=list(barrier.blocked),
                                                        evaluated=list(barrier.evaluated))
        assert snapshot() == revoked
        with PrivateReadBarrier(store, {origin, rid}, {data[5]}) as barrier:
            cancelled = request("POST", route + "/commands", dict(command="cancel", version=control["version"]))
            assert cancelled["status"] == "CANCELLED"
            final_control = request("GET", route + "/control-status")
            assert final_control["status"] == "CANCELLED" and final_control["cancel_intent"]
            request("POST", route + "/commands", dict(command="resume", version=final_control["version"]), 403)
            assert not worker.once() and not runtime_calls
            assert not barrier.blocked and not barrier.evaluated
            proof["private_reads_cancel_and_worker"] = dict(blocked=list(barrier.blocked),
                                                            evaluated=list(barrier.evaluated))
            # Calibration occurs after the zero-private-read assertions.
            try:
                with store.tx() as c:
                    c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
            except DatabaseError:
                pass
            else:
                raise AssertionError("Private-cell barrier did not reject calibration")
            assert barrier.blocked
            proof["calibration"] = list(barrier.blocked)
        final = snapshot()
        for table in ("internal_run_bindings", "attempts", "operations", "internal_instance_data", "local_effects", "grants", "internal_instances"):
            assert final[table] == revoked[table]
        for table, allowed in (("runs", {"status", "version", "cancel_intent"}),
                               ("internal_app_runs", {"status"})):
            before = {r["id"]: r for r in revoked[table]}
            after = {r["id"]: r for r in final[table]}
            assert before.keys() == after.keys()
            target = rid if table == "runs" else initial["app_run_id"]
            for key in before:
                changed = {field for field in before[key] if before[key][field] != after[key][field]}
                assert changed == (allowed if key == target else set())
            if table == "runs":
                assert after[target]["version"] == before[target]["version"] + 1
        old_events = {r["id"]: r for r in revoked["events"]}
        new_events = {r["id"]: r for r in final["events"]}
        assert all(new_events[key] == value for key, value in old_events.items())
        added = [value for key, value in new_events.items() if key not in old_events]
        assert len(added) == 1 and added[0]["run_id"] == rid and added[0]["kind"] == "COMMAND"
        assert added[0]["data"] == dict(command="cancel", status="CANCELLED")
        job = next(r for r in final["runs"] if r["id"] == rid)
        assert job["status"] == "CANCELLED" and job["cancel_intent"]
        assert next(r for r in final["internal_app_runs"] if r["id"] == initial["app_run_id"])["status"] == "CANCELLED"
        assert SOURCE not in json.dumps(calls[calls.index(next(c for c in calls if c["path"].endswith('/revoke'))) + 1:])
        proof.update(status="PASS", run_id=rid, app_run_id=initial["app_run_id"], source_resource=data[5],
                     project_id=pid, separate_project_id=foreign_pid, revoked_grant_id=grant["id"],
                     database="NAMED_SHARED_MEMORY_SQLITE", browser="NOT_RUN", new_process="NOT_RUN",
                     generation_mock_calls=3, runtime_model_calls=runtime_calls, actual_worker=True,
                     requests=calls, final_control=final_control)
    finally:
        proof.setdefault("status", "INCOMPLETE_FAILURE")
        proof.setdefault("requests", calls)
        if "barrier" in locals():
            proof["last_barrier"] = dict(blocked=barrier.blocked, evaluated=barrier.evaluated,
                                          statements=barrier.statements)
        for label in ("revoked", "final"):
            if label in locals():
                (tmp_path / (label + ".json.gz")).write_bytes(gzip.compress(
                    json.dumps(locals()[label], sort_keys=True).encode(), mtime=0))
        try:
            (tmp_path / "database.sqlite.gz").write_bytes(gzip.compress(
                anchor.connection.driver_connection.serialize(), mtime=0))
            proof["database_snapshot"] = "PASS"
        except Exception as error:
            proof["database_snapshot"] = str(error)
        (tmp_path / "proof.json.gz").write_bytes(gzip.compress(json.dumps(proof, indent=2).encode(), mtime=0))
        client.close()
        fixture.close()
        anchor.close()
        store.engine.dispose()
        if proof["status"] == "PASS":
            assert proof["database_snapshot"] == "PASS"
