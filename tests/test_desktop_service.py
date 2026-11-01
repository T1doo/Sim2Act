"""Real dual-process TEST_ONLY SQLite integration, plus fail-closed lifecycle cases."""
import json
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest
from desktop_service_fixture import TOKEN

from sim2act.desktop_protocol import TEST_ONLY
from sim2act.process_env import system_environment

FIXTURE = Path(__file__).with_name("desktop_service_fixture.py")


class Running:
    def __init__(self, root, *flags):
        self.root = root
        self.started = time.monotonic()
        self.timeline = []
        self.child = subprocess.Popen([sys.executable, "-B", "-u", str(FIXTURE),
            "--root", str(root), *flags], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, env=system_environment())
        self.events, self.lines, self.errors = queue.Queue(), [], []
        self.threads = []
        for name in ("stdout", "stderr"):
            thread = threading.Thread(target=self._read, args=(name,), daemon=True)
            thread.start()
            self.threads.append(thread)

    def _read(self, name):
        for line in getattr(self.child, name):
            if name == "stdout":
                value = json.loads(line)
                self.lines.append(value)
                self.timeline.append(dict(elapsed_seconds=time.monotonic() - self.started, receipt=value))
                self.events.put(value)
            else:
                self.errors.append(line)
        if name == "stdout":
            self.events.put(None)

    def event(self, expected, timeout=20):
        until = time.monotonic() + timeout
        while time.monotonic() < until:
            value = self.events.get(timeout=max(.01, until - time.monotonic()))
            assert value is not None, (self.lines, self.errors)
            if value["event"] == expected:
                return value
        pytest.fail(str(self.lines))

    def close(self, session=None):
        if not self.child.stdin.closed:
            if session:
                self.child.stdin.write(json.dumps(dict(command="stop", session=session)) + "\n")
                self.child.stdin.flush()
            self.child.stdin.close()
        code = self.child.wait(timeout=20)
        for thread in self.threads:
            thread.join(2)
            assert not thread.is_alive()
        self.child.stdout.close()
        self.child.stderr.close()
        self.root.parent.mkdir(parents=True, exist_ok=True)
        destination = self.root.parent / ("controller-" + str(self.child.pid) + ".json")
        destination.write_text(json.dumps(dict(backend=TEST_ONLY, exitcode=code,
            stderr_line_count=len(self.errors), timeline=self.timeline), indent=2) + "\n")
        return code


def request(client, path, body, status=201):
    response = client.post(path, json=body)
    assert response.status_code == status, response.text
    return response.json()


def test_real_api_worker_save_stop_and_same_origin_new_process_reopen(tmp_path):
    root = tmp_path / "test-only-dual-process"
    running = Running(root)
    try:
        ready = running.event("DESKTOP_SERVICE_READY")
        assert ready["backend"] == TEST_ONLY
        assert len({running.child.pid, ready["api_pid"], ready["worker_pid"]}) == 3
        claim = json.loads((root / "desktop-service-claim.json").read_text())
        assert {c["pid"] for c in claim["children"]} == {ready["api_pid"], ready["worker_pid"]}
        assert all(c["created_at"] > 0 for c in claim["children"])
        with httpx.Client(base_url=ready["url"], headers={"Authorization": "Bearer " + TOKEN},
                trust_env=False, timeout=5) as client:
            assert client.get("/health").status_code == 200
            project = request(client, "/api/projects", dict(name="Dual process actual save"))["id"]
            resource = request(client, f"/api/projects/{project}/resources",
                dict(name="values.csv", format="csv", content="item,amount\nA,10\nB,20\n"))
            app = request(client, f"/api/projects/{project}/apps/csv-preview",
                dict(name="sum amount", resource_id=resource["id"], goal="Sum amount"))
            app = client.get("/api/apps/" + app["id"]).json()
            approval = request(client, f"/api/internal/apps/{app['id']}/release-approvals",
                dict(expected_draft_fingerprint=app["fingerprint"], sample_input=dict(column="amount")))
            release = request(client, f"/api/internal/approvals/{approval['id']}/commit",
                dict(fingerprint=approval["fingerprint"]), 200)
            instance = request(client, f"/api/internal/releases/{release['id']}/instances",
                dict(expected_release_fingerprint=release["fingerprint"], request_key="dual-instance"))
            body = dict(expected_release_fingerprint=release["fingerprint"], expected_revision=instance["revision"],
                input=dict(column="amount"), request_key="dual-run")
            accepted = request(client, f"/api/internal/instances/{instance['id']}/runs", body, 202)
            route = f"/api/internal/instances/{instance['id']}/runs/{accepted['run_id']}"
            until = time.monotonic() + 15
            while True:
                result = client.get(route).json()
                if result["status"] not in {"QUEUED", "RUNNING"}:
                    break
                assert time.monotonic() < until, result
                time.sleep(.05)
            assert result["status"] == "SUCCEEDED" and result["result"]["sum"] == "30"
            (root / "actual-test-only-result.json").write_text(json.dumps(result, indent=2) + "\n")
            # The original request identity still returns the same Run.
            again = request(client, f"/api/internal/instances/{instance['id']}/runs", body, 202)
            assert again["run_id"] == accepted["run_id"]
            pending = request(client, f"/api/projects/{project}/csv-report-runs",
                dict(resource_id=resource["id"], column="amount", request_key="cancel-before-confirm"), 202)
            cancel_route = "/api/runs/" + pending["run_id"]
            pending = client.get(cancel_route).json()
            assert pending["status"] == "WAITING_APPROVAL"
            cancelled_reply = request(client, cancel_route + "/commands",
                dict(command="cancel", version=pending["version"]), 200)
            assert cancelled_reply["status"] == "CANCELLED"
            cancelled = client.get(cancel_route).json()
            assert cancelled["status"] == "CANCELLED" and cancelled["result"] is None
            (root / "actual-test-only-cancelled.json").write_text(json.dumps(cancelled, indent=2) + "\n")
    finally:
        assert running.close(ready["session"] if "ready" in locals() else None) == 0, running.lines
    stopped = running.lines[-1]
    assert stopped["event"] == "DESKTOP_SERVICE_STOPPED" and stopped["clean"]
    assert stopped["ready_seen"] and not stopped["claim_preserved"]
    assert all(v["exitcode"] == 0 and v["stdout_eof"] and v["stderr_eof"]
        and v["receipt"]["clean"] for v in stopped["roles"].values())
    assert not (root / "desktop-service-claim.json").exists()
    reopened = Running(root)
    try:
        current = reopened.event("DESKTOP_SERVICE_READY")
        assert current["session"] != ready["session"] and current["url"] == ready["url"]
        with httpx.Client(base_url=current["url"], headers={"Authorization": "Bearer " + TOKEN},
                trust_env=False, timeout=5) as client:
            assert client.get(route).json() == result
            assert client.get(cancel_route).json() == cancelled
            assert client.get("/api/resources/" + resource["id"]).json()["content"] == "item,amount\nA,10\nB,20\n"
            again = request(client, f"/api/internal/instances/{instance['id']}/runs", body, 202)
            assert again["run_id"] == accepted["run_id"]
    finally:
        assert reopened.close() == 0, reopened.lines  # Parent EOF is normal stop.
    assert reopened.lines[-1]["clean"] and not (root / "desktop-service-claim.json").exists()


def test_parent_eof_during_preflight_prevents_both_children(tmp_path):
    running = Running(tmp_path / "early-eof", "--preflight-delay", ".2")
    running.event("DESKTOP_SERVICE_STARTING")
    assert running.close() == 0
    assert running.lines[-1]["clean"] and running.lines[-1]["children_started"] == 0
    assert not any(e["event"] == "DESKTOP_SERVICE_READY" for e in running.lines)


def test_wrong_current_worker_receipt_never_ready_retains_unknown_claim(tmp_path):
    root = tmp_path / "wrong-pid"
    running = Running(root, "--wrong-worker-pid")
    running.event("DESKTOP_SERVICE_ERROR")
    assert running.close() == 1
    assert not any(e["event"] == "DESKTOP_SERVICE_READY" for e in running.lines)
    assert not running.lines[-1]["clean"] and running.lines[-1]["claim_preserved"]
    assert (root / "desktop-service-claim.json").is_file()
    assert all(v["exitcode"] is not None and v["stdout_eof"] and v["stderr_eof"]
        for v in running.lines[-1]["roles"].values())


def test_owned_heartbeat_handle_must_actually_finish(env):
    from sim2act.worker import Worker
    worker = Worker(env[0], env[1])
    release = threading.Event()
    owned = threading.Thread(target=release.wait)
    owned.start()
    with worker._owned_heartbeat_lock:
        worker._owned_heartbeats.add(owned)
    try:
        assert not worker.drain_owned_heartbeats(.01)
    finally:
        release.set()
        owned.join(1)
    assert worker.drain_owned_heartbeats(.1)


def test_production_role_rejects_sqlite_without_creating_data(tmp_path):
    root = tmp_path / "production-must-not-use-test-db"
    environment = system_environment()
    environment.update(SIM2ACT_DATABASE_URL="sqlite:///" + str(root / "not-created.db"),
        SIM2ACT_DATA_DIR=str(root))
    result = subprocess.run([sys.executable, "-B", "-m", "sim2act.desktop_service",
        "--role", "worker", "--session", "a" * 32, "--port", "0"],
        input="", text=True, capture_output=True, env=environment, timeout=10)
    assert result.returncode == 1 and not root.exists()
    events = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(events) == 1 and events[0]["event"] == "ROLE_ERROR"
    assert events[0]["backend"] == "CONFIGURED_POSTGRESQL"


def test_connection_namespace_binding_includes_options_and_overrides_without_password(tmp_path):
    from dataclasses import replace

    from sim2act.config import Settings
    from sim2act.desktop_protocol import ProtocolError
    from sim2act.desktop_service import configuration_binding
    settings = Settings("postgresql+psycopg://app:first@localhost/source?options=-c+search_path%3Done", tmp_path)
    first = configuration_binding(settings)
    assert len(first) == 64
    assert configuration_binding(replace(settings, database_url=settings.database_url.replace(":first@", ":second@"))) == first
    assert configuration_binding(replace(settings, database_url=settings.database_url.replace("%3Done", "%3Dtwo"))) != first
    assert configuration_binding(replace(settings, database_url=settings.database_url + "&host=other")) != first
    with pytest.raises(ProtocolError, match="INDIRECT_DATABASE_IDENTITY_UNSUPPORTED"):
        configuration_binding(replace(settings, database_url=settings.database_url + "&service=unobserved-file"))


def test_second_controller_cannot_touch_first_owned_children_or_claim(tmp_path):
    root = tmp_path / "exclusive-controller"
    first = Running(root)
    try:
        ready = first.event("DESKTOP_SERVICE_READY")
        claim = (root / "desktop-service-claim.json").read_bytes()
        second = Running(root)
        second.event("DESKTOP_SERVICE_ERROR")
        assert second.close() == 1
        assert second.lines[-1]["children_started"] == 0
        assert (root / "desktop-service-claim.json").read_bytes() == claim
        with httpx.Client(base_url=ready["url"], trust_env=False, timeout=5) as client:
            assert client.get("/health").status_code == 200
    finally:
        assert first.close() == 0, first.lines


def test_preflight_timeout_is_bounded_and_never_reports_clean_while_still_active(tmp_path):
    import io
    import os

    from sim2act.desktop_protocol import Supervisor
    begin, finish = threading.Event(), threading.Event()
    read_fd, write_fd = os.pipe()
    output = io.StringIO()
    with os.fdopen(read_fd) as parent, os.fdopen(write_fd, "w") as writer:
        controller = Supervisor(tmp_path / "bounded-preflight", TEST_ONLY, "a" * 64,
            lambda *_: pytest.fail("No spawn while preflight pending"), system_environment(),
            input_stream=parent, output_stream=output, startup_seconds=.05, stop_seconds=.05)
        def preflight():
            begin.set()
            finish.wait(5)
        try:
            started = time.monotonic()
            assert controller.run(preflight) == 1
            assert time.monotonic() - started < 1
            assert begin.is_set()
            events = [json.loads(line) for line in output.getvalue().splitlines()]
            assert events[-1]["children_started"] == 0
            assert not events[-1]["clean"] and not events[-1]["preflight_stopped"]
            assert events[-1]["claim_preserved"] and controller.claim_file.is_file()
        finally:
            finish.set()
            controller.preflight_thread.join(1)
            writer.close()


def test_preflight_never_inherits_libpq_identity_defaults(tmp_path, monkeypatch):
    from sim2act.config import Settings
    from sim2act.desktop_protocol import ProtocolError
    from sim2act.desktop_service import configuration_binding
    settings = Settings("postgresql+psycopg://app@localhost/database", tmp_path)
    monkeypatch.setenv("PGOPTIONS", "-c search_path=synthetic_other")
    with pytest.raises(ProtocolError, match="EXTERNAL_LIBPQ_DEFAULTS_UNSUPPORTED"):
        configuration_binding(settings)
    monkeypatch.delenv("PGOPTIONS")
    for url in ("postgresql+psycopg:///database", "postgresql+psycopg://app@localhost"):
        with pytest.raises(ProtocolError, match="EXPLICIT_DATABASE_IDENTITY_REQUIRED"):
            configuration_binding(Settings(url, tmp_path))


def test_actual_app_job_blocked_heartbeat_remains_owned_after_its_old_two_second_join(env, monkeypatch):
    """A real accepted CSV app commits; its blocked sender is NOT certified gone.

    The finite injected wait exercises lifecycle only, never a timing score,
    PostgreSQL behavior or a provider success. No clock/lease guard is replaced.
    """
    from dataclasses import replace

    from sim2act import app_jobs
    from sim2act.worker import Worker
    store, settings, client, _owner, _other, project, material = env
    app = request(client, f"/api/projects/{project}/apps/csv-preview",
        dict(name="owned background sender", resource_id=material, goal="Sum amount"))
    app = client.get("/api/apps/" + app["id"]).json()
    approval = request(client, f"/api/internal/apps/{app['id']}/release-approvals",
        dict(expected_draft_fingerprint=app["fingerprint"], sample_input=dict(column="amount")))
    release = request(client, f"/api/internal/approvals/{approval['id']}/commit",
        dict(fingerprint=approval["fingerprint"]), 200)
    instance = request(client, f"/api/internal/releases/{release['id']}/instances",
        dict(expected_release_fingerprint=release["fingerprint"], request_key="heartbeat-instance"))
    accepted = request(client, f"/api/internal/instances/{instance['id']}/runs",
        dict(expected_release_fingerprint=release["fingerprint"], expected_revision=instance["revision"],
            input=dict(column="amount"), request_key="heartbeat-run"), 202)
    worker = Worker(store, replace(settings, lease_seconds=3))
    entered, unblock = threading.Event(), threading.Event()
    original_heartbeat, original_compute = store.heartbeat, app_jobs.compute

    def blocked_heartbeat(worker_id, run_id=None, *args, **kwargs):
        if run_id == accepted["run_id"]:
            entered.set()
            assert unblock.wait(8), "Bounded test sender was not released"
        return original_heartbeat(worker_id, run_id, *args, **kwargs)

    def compute(*args, **kwargs):
        assert entered.wait(2), "Real app heartbeat never started"
        return original_compute(*args, **kwargs)

    monkeypatch.setattr(store, "heartbeat", blocked_heartbeat)
    monkeypatch.setattr(app_jobs, "compute", compute)
    try:
        assert worker.once()
        assert entered.is_set()
        assert not worker.drain_owned_heartbeats(.01)
    finally:
        unblock.set()
        assert worker.drain_owned_heartbeats(2)
    result = client.get(f"/api/internal/instances/{instance['id']}/runs/{accepted['run_id']}").json()
    assert result["status"] == "SUCCEEDED" and result["result"]["sum"] == "4.00"
