"""Accepted natural-spec Run pauses safely, changes Worker PID, resumes once.

Real loopback API and two real Worker processes; JSDOM is not a native browser.
All fixture generation/runtime responses use explicit offline MockTransport.
"""

import gzip
import hashlib
import json
import os
import selectors
import socket
import subprocess
import sys
import time
import uuid
from html.parser import HTMLParser
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_natural_spec_apps import ready, setup

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import (
    Store,
    attempts,
    internal_app_runs,
    internal_instance_data,
    internal_run_bindings,
    local_effects,
    operations,
    reservations,
    runs,
)


@pytest.mark.skipif(sys.platform != "linux", reason="PID/starttime ownership requires Linux /proc")
@pytest.mark.parametrize("cancel", [False, True], ids=["resume", "cancel"])
def test_safe_step_pause_new_worker_and_new_dom_resume_same_run(tmp_path, cancel):
    root = tmp_path / "owned-safe-step"
    root.mkdir()
    repo = Path(__file__).parents[1]
    token = uuid.uuid4().hex
    children, handles = [], []
    events = root / "ownership.jsonl"
    child_env = {key: os.environ[key] for key in ("PATH", "LANG", "TMPDIR") if key in os.environ}
    child_env.update(PYTHONPATH=str(repo / "src"), NODE_PATH="/workspace/node-tools/node_modules",
                     PYTHONDONTWRITEBYTECODE="1")

    def closure():
        files = [p for directory in (repo / "src", repo / "tests") for p in directory.rglob("*")
                 if p.is_file() and "__pycache__" not in p.parts] + [repo / "pyproject.toml"]
        return {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}

    def record(value):
        with events.open("a") as output:
            output.write(json.dumps(value) + "\n")

    def dump(name, value):
        (root / (name + ".json.gz")).write_bytes(gzip.compress(json.dumps(value, sort_keys=True).encode()))

    def identity(process):
        path = Path(f"/proc/{process.pid}")
        return dict(pid=process.pid, starttime=(path / "stat").read_text().rsplit(")", 1)[1].split()[19],
                    argv=(path / "cmdline").read_bytes().rstrip(b"\0").decode().split("\0"))

    def start(role, argv):
        log = (root / (role + ".log")).open("w")
        handles.append(log)
        process = subprocess.Popen(argv, cwd=repo, env=child_env, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=log, text=True)
        child = dict(process=process, role=role, argv=argv, identity=None)
        children.append(child)
        deadline = time.monotonic() + 2
        initial = identity(process)
        child["identity"] = initial
        record(dict(event="CREATED", role=role, token=token, **initial))
        while time.monotonic() < deadline:
            current = identity(process)
            assert current["starttime"] == initial["starttime"], "UNKNOWN PID ownership"
            if current["argv"] == argv:
                child["identity"] = current
                break
            assert process.poll() is None
            time.sleep(0.01)
        assert child["identity"]["argv"] == argv and token in argv
        record(dict(event="START", role=role, token=token, **child["identity"]))
        return child

    def receive(child, expected=None, timeout=180):
        process = child["process"]
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if selector.select(timeout=0.5):
                    line = process.stdout.readline()
                    assert line, f"{child['role']} ended without receipt: {process.poll()}"
                    value = json.loads(line)
                    record(dict(event="CHILD_RECEIPT", role=child["role"], receipt=value))
                    if expected:
                        assert value["event"] == expected
                        assert value["pid"] == child["identity"]["pid"]
                        assert value["starttime"] == child["identity"]["starttime"]
                        assert value["token"] == token and value["initialize_calls"] == 0
                        assert value["lease_seconds"] == 30 and value["run_seconds"] == 300
                    return value
                assert process.poll() is None, f"{child['role']} exited before receipt"
        raise AssertionError(f"{child['role']} bounded wait expired; no retry")

    def send(child, value):
        child["process"].stdin.write(json.dumps(value) + "\n")
        child["process"].stdin.flush()

    def stop(child):
        process = child["process"]
        if process.poll() is None:
            assert child["identity"] and identity(process) == child["identity"], "UNKNOWN process: not signalled"
            assert child["identity"]["argv"] == child["argv"] and token in child["argv"]
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                assert identity(process) == child["identity"], "UNKNOWN process: not killed"
                process.kill()
                process.wait(timeout=5)
        record(dict(event="STOP", role=child["role"], exit=process.returncode, identity=child["identity"]))

    before = closure()
    (root / "source-before.json").write_text(json.dumps(before, indent=2))
    url = "sqlite:///" + str(root / "fixture.db")
    store = Store(url, test_only=True)
    store.initialize()  # Exactly one parent initialization; all children forbid it.
    owner = store.user("owned safe-step fixture A", "synthetic-test-A")
    alternate = store.user("owned safe-step fixture B", "synthetic-test-B")
    settings = Settings(url, root, mode="mock", lease_seconds=30, run_seconds=300)
    fixture = TestClient(create_app(store, settings))
    fixture.headers["Authorization"] = "Bearer synthetic-test-A"
    made = fixture.post("/api/projects", json=dict(name="Owned safe-step process proof"))
    assert made.status_code == 201
    project = made.json()["id"]
    data = setup((store, settings, fixture, owner, alternate, project, None))
    _, app, release, instance, generation = ready(data, "sequential")
    assert len(generation) == 3
    app_name = data[2].get(f"/api/apps/{app}").json()["name"]
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    config = root / "config.json"
    config.write_text(json.dumps(dict(token=token, database_url=url, port=port, cancel=cancel)))
    base = f"http://127.0.0.1:{port}"
    client = httpx.Client(base_url=base, timeout=20, trust_env=False,
                          headers={"Authorization": "Bearer synthetic-test-A"})
    prefix = f"/api/internal/instances/{instance['id']}"
    accepted, original_request, paused, final = None, None, None, None
    old, new = None, None

    def worker(role):
        return start(role, [sys.executable, str(repo / "tests/safe_step_process_child.py"),
                            str(config), role, token])

    def get(path):
        response = client.get(path)
        record(dict(event="AUTHENTICATED_HTTP_GET", path=path, status=response.status_code))
        assert response.status_code == 200, response.text
        return response.json()

    def snapshot():
        rid = accepted["run_id"]
        with store.tx() as c:
            def rows(table, predicate):
                return sorted((dict(row) for row in c.execute(select(table).where(predicate)).mappings()),
                              key=lambda row: json.dumps(row, sort_keys=True))
            return dict(run=rows(runs, runs.c.id == rid)[0],
                app_runs=rows(internal_app_runs, internal_app_runs.c.instance_id == instance["id"]),
                binding=rows(internal_run_bindings, internal_run_bindings.c.run_id == rid),
                operations=rows(operations, operations.c.run_id == rid),
                attempts=rows(attempts, attempts.c.run_id == rid),
                reservations=rows(reservations, reservations.c.run_id == rid),
                data=rows(internal_instance_data, internal_instance_data.c.instance_id == instance["id"]),
                project_run_ids=sorted(c.execute(select(runs.c.id).where(runs.c.project_id == project)).scalars()),
                effects=rows(local_effects, local_effects.c.operation_id.in_(
                    select(operations.c.id).where(operations.c.run_id == rid))),
                unknown=store.has_unknown(c, rid))

    def safe(value):
        assert not value["unknown"] and not value["data"] and not value["effects"]
        assert len(value["attempts"]) == 1 and value["attempts"][0]["status"] == "VERIFIED"
        assert len(value["operations"]) == 2 and all(row["status"] == "VERIFIED" for row in value["operations"])
        assert len(value["reservations"]) == 1 and len(value["app_runs"]) == 1

    try:
        api = worker("api")
        bound = receive(api, "BOUND", timeout=20)
        assert bound["port"] == port and bound["host"] == "127.0.0.1"
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                if client.get("/").status_code == 200:
                    assert api["process"].poll() is None and identity(api["process"]) == api["identity"]
                    break
            except httpx.TransportError:
                pass
            assert api["process"].poll() is None
            time.sleep(0.05)
        else:
            raise AssertionError("Owned API readiness timed out")
        info = root / "info.json"
        info.write_text(json.dumps(dict(base_url=base, project=project, app_name=app_name,
            cancel=cancel,
            instance=instance["id"], storage_path=str(root / "browser-storage.json"),
            output=str(root / "page.json.gz"), http_log=str(root / "page-http.jsonl.gz"))))
        page = start("page", ["node", str(repo / "tests/safe_step_process_ui.cjs"), str(info), token])
        for _ in range(6):
            message = receive(page, timeout=240)
            if message.get("done"):
                break
            command = message["command"]
            if command == "pause-and-replace-worker":
                accepted, original_request = message["accepted"], message["request"]
                assert accepted["run_id"].startswith("run_") and accepted["app_run_id"].startswith("iapprun_")
                old = worker("old-worker")
                boundary = receive(old, "SAFE_BOUNDARY")
                assert boundary["run_id"] == accepted["run_id"] and boundary["active_senders"] == 0
                state = snapshot()
                safe(state)
                dump("safe-boundary", state)
                detail = get(prefix + "/runs/" + accepted["run_id"])
                assert detail["status"] == "RUNNING"
                response = client.post(prefix + "/runs/" + accepted["run_id"] + "/commands",
                    json=dict(command="pause", version=detail["version"]))
                record(dict(event="AUTHENTICATED_PAUSE_COMMAND", run_id=accepted["run_id"],
                    body=dict(command="pause", version=detail["version"]),
                    status=response.status_code, response=response.json()))
                assert response.status_code == 200 and response.json()["status"] == "PAUSE_REQUESTED"
                send(old, dict(command="continue-to-pause"))  # Release immediately after real pause acceptance.
                settled = receive(old, "PAUSE_SETTLED")
                assert old["process"].wait(timeout=10) == 0
                paused = snapshot()
                safe(paused)
                assert paused["run"]["status"] == paused["app_runs"][0]["status"] == "PAUSED"
                assert paused["run"]["lease_until"] == 0 and paused["run"]["worker_id"] == settled["worker_id"]
                clock = paused["binding"][0]["snapshot"]["natural_spec_clock"]
                assert clock["created_at"] == paused["run"]["created_at"]
                assert clock["deadline"] == clock["created_at"] + 300
                for key in ("binding", "operations", "attempts", "reservations"):
                    assert paused[key] == state[key]
                dump("paused-old-worker-ended", paused)
                new = worker("new-worker")
                idle = receive(new, "IDLE_BEFORE_DOM")
                assert new["identity"]["pid"] != old["identity"]["pid"]
                assert new["identity"]["starttime"] != old["identity"]["starttime"]
                assert idle["worker_id"] != settled["worker_id"] and not idle["claimed"]
                assert snapshot() == paused
            elif command == "verify-paused-before-resume":
                assert message["accepted"] == accepted and message["request"] == original_request
                send(new, dict(command="probe-before-resume"))
                assert not receive(new, "IDLE_AFTER_DOM")["claimed"]
                assert snapshot() == paused
                dump("new-dom-and-worker-before-resume", snapshot())
            elif command == "verify-explicit-cancel":
                assert cancel and message["accepted"] == accepted and message["request"] == original_request
                final = snapshot()
                safe(final)
                assert final["run"]["status"] == final["app_runs"][0]["status"] == "CANCELLED"
                assert final["run"]["cancel_intent"] and final["run"]["version"] == paused["run"]["version"] + 1
                assert final["run"]["lease_until"] == 0
                for key in ("binding", "operations", "attempts", "reservations", "data", "effects", "project_run_ids"):
                    assert final[key] == paused[key]
                changed = {key for key in final["run"] if final["run"][key] != paused["run"][key]}
                assert changed == {"status", "version", "cancel_intent"}
                assert len(final["app_runs"]) == 1
                assert {k: v for k, v in final["app_runs"][0].items() if k != "status"} == {
                    k: v for k, v in paused["app_runs"][0].items() if k != "status"}
                dump("explicit-cancel-terminal", final)
                send(new, dict(command="probe-after-cancel"))
                assert not receive(new, "IDLE_AFTER_CANCEL")["claimed"]
                assert snapshot() == final
            elif command == "verify-stale-resume-rejected":
                assert cancel and final is not None
                assert message["accepted"] == accepted and message["request"] == original_request
                send(new, dict(command="probe-after-stale-resume"))
                assert not receive(new, "CANCELLED_DONE")["claimed"]
                assert new["process"].wait(timeout=10) == 0 and snapshot() == final
                # Even a fresh terminal version cannot resume; keep this separate
                # from the actual stale-page gesture and its recorded HTTP 409.
                response = client.post(prefix + "/runs/" + accepted["run_id"] + "/commands",
                    json=dict(command="resume", version=final["run"]["version"]))
                record(dict(event="CURRENT_VERSION_TERMINAL_RESUME", status=response.status_code,
                    response=response.json(), run_id=accepted["run_id"], version=final["run"]["version"]))
                assert response.status_code == 409 and response.json()["error"]["code"] == "VERSION_CONFLICT"
                assert snapshot() == final
                dump("stable-cancel-after-stale-and-current-resume", final)
            elif command == "finish-same-run":
                assert message["accepted"] == accepted and message["request"] == original_request
                queued = snapshot()
                assert queued["run"]["status"] == queued["app_runs"][0]["status"] == "QUEUED"
                for key in ("binding", "operations", "attempts", "reservations", "data", "effects"):
                    assert queued[key] == paused[key]
                dump("explicit-resume-queued", queued)
                send(new, dict(command="run-after-resume"))
                done = receive(new, "RESUMED_DONE")
                assert new["process"].wait(timeout=10) == 0 and not done["second_claim"]
                final = snapshot()
                assert final["run"]["status"] == final["app_runs"][0]["status"] == "SUCCEEDED"
                assert final["run"]["worker_id"] == done["worker_id"]
                assert final["run"]["fence"] > paused["run"]["fence"]
                assert final["run"]["created_at"] == paused["run"]["created_at"]
                assert final["binding"] == paused["binding"] and not final["unknown"]
                for key in ("operations", "attempts", "reservations"):
                    indexed = {row["id"]: row for row in final[key]}
                    assert all(indexed[row["id"]] == row for row in paused[key])
                assert len(final["operations"]) == 6 and len(final["attempts"]) == 2
                assert all(row["status"] == "VERIFIED" for key in ("operations", "attempts") for row in final[key])
                assert len(final["data"]) == len(final["effects"]) == len(final["app_runs"]) == 1
                assert final["data"][0]["version"] == 1 and final["data"][0]["run_id"] == accepted["app_run_id"]
                assert final["app_runs"][0]["request_key"] == original_request["request_key"]
                assert final["run"]["context"]["requests"] == 2
                dump("same-run-succeeded", final)
            else:
                assert command == "verify-no-duplicate" and final is not None
                receipt = get(prefix + "/spec-run-requests/" + original_request["request_key"])
                assert receipt["run_id"] == accepted["run_id"] and receipt["app_run_id"] == accepted["app_run_id"]
                assert receipt["request"] == original_request
                assert receipt["status"] == ("CANCELLED" if cancel else "SUCCEEDED")
                assert snapshot() == final
                dump("stable-final-after-readback", snapshot())
            send(page, dict(id=message["id"], status=200))
        else:
            raise AssertionError("Page exceeded finite command budget")
        assert page["process"].wait(timeout=10) == 0 and final is not None
        proof = json.loads(gzip.decompress((root / "page.json.gz").read_bytes()))
        document_count = 3 if cancel else 2
        assert proof["status"] == "PASS" and proof["documents"] == document_count
        assert len(proof["checks"]) >= (24 if cancel else 17)

        class Assets(HTMLParser):
            def __init__(self):
                super().__init__()
                self.paths = ["/", "/app.css"]

            def handle_starttag(self, tag, attributes):
                values = dict(attributes)
                if tag == "script" and values.get("src"):
                    self.paths.append(values["src"])

        expected_assets = Assets()
        expected_assets.feed((repo / "src/sim2act/web/index.html").read_text())
        assert [(asset["document"], asset["path"]) for asset in proof["assets"]] == [
            (document, path) for document in range(1, document_count + 1) for path in expected_assets.paths]
        for asset in proof["assets"]:
            path = repo / "src/sim2act/web" / ("index.html" if asset["path"] == "/" else asset["path"].lstrip("/"))
            assert asset["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert [len((root / (role + "-wire.jsonl")).read_text().splitlines())
                if (root / (role + "-wire.jsonl")).exists() else 0
                for role in ("old-worker", "new-worker")] == [1, 0 if cancel else 1]
        (root / "RESULT.json").write_text(json.dumps(dict(status="PASS", accepted=accepted,
            original_request=original_request, old_worker=old["identity"], new_worker=new["identity"],
            page_checks=len(proof["checks"]), documents=document_count,
            model_calls=dict(fixture=3, old_worker=1, new_worker=0 if cancel else 1),
            safe_pause_no_inflight=True, no_execution_before_resume=True, prefix_unchanged=True,
            data_versions=0 if cancel else 1, artifact_effects=0 if cancel else 1,
            final_status=final["run"]["status"], stale_resume_rejected=cancel,
            no_execution_after_cancel=cancel, current_version_terminal_resume_rejected=cancel,
            duplicate_append=False, source_count=len(before),
            configured_worker_limits=dict(lease_seconds=30, run_seconds=300), frozen_clock=clock,
            exact_assets=len(proof["assets"]), closure_scope="src/tests + pyproject.toml",
            browser="JSDOM_NOT_NATIVE", database="SQLITE", real_model="NOT_RUN",
            pg="NOT_RUN", windows="NOT_RUN", strict_lock_wait_observation="NOT_RUN"), indent=2))
    finally:
        errors = []
        for child in reversed(children):
            try:
                stop(child)
            except Exception as error:
                errors.append(dict(role=child["role"], identity=child["identity"], error=str(error)))
        for handle in handles:
            handle.close()
        client.close()
        data[2].close()
        fixture.close()
        store.engine.dispose()
        after = closure()
        (root / "source-after.json").write_text(json.dumps(after, indent=2))
        (root / "CLEANUP.json").write_text(json.dumps(dict(status="UNKNOWN" if errors else "PASS", errors=errors), indent=2))
        assert not errors, "UNKNOWN process ownership preserved without signalling"
        assert before == after, "Source changed during process proof"
