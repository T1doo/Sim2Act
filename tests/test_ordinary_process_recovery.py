"""Real loopback page -> separate API/Worker -> saved Source -> restart -> Cold.

No TestClient, Trial qualification, native browser or real provider is used.
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
from sqlalchemy import select
from test_natural_spec_apps import COLD, SOURCE, material

from sim2act.db import Store, attempts, internal_instance_data


@pytest.mark.skipif(sys.platform != "linux", reason="Ownership proof requires Linux /proc")
@pytest.mark.parametrize("durable", [False, True])
def test_same_page_recovers_saved_source_after_owned_process_restart(tmp_path, durable):
    root = Path(os.environ.get("SIM2ACT_PROCESS_EVIDENCE", str(tmp_path / "process-evidence")))
    if durable:
        root = root.with_name(root.name + "-new-dom")
    root.mkdir()  # Atomic: an existing/UNKNOWN execution is never reused.
    repo = Path(__file__).parents[1]
    token = uuid.uuid4().hex
    config = root / "config.json"
    events = root / "processes.jsonl"
    children = []
    handles = []
    child_env = {key: os.environ[key] for key in ("PATH", "LANG", "TMPDIR") if key in os.environ}
    child_env.update(PYTHONPATH=str(repo / "src"), NODE_PATH="/workspace/node-tools/node_modules")

    def record(value):
        with events.open("a") as output:
            output.write(json.dumps(value) + "\n")

    def identity(process):
        stat = Path(f"/proc/{process.pid}/stat").read_text().rsplit(")", 1)[1].split()
        argv = Path(f"/proc/{process.pid}/cmdline").read_bytes().rstrip(b"\0").decode().split("\0")
        return dict(pid=process.pid, starttime=stat[19], argv=argv, token=token)

    def start(role, argv):
        log = (root / f"{role}-{len(children)}.log").open("w")
        handles.append(log)
        process = subprocess.Popen(argv, cwd=repo, env=child_env, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE if role == "page" else log,
                                   stderr=log, text=True)
        owned = identity(process)
        child = dict(process=process, identity=owned, role=role, expected_argv=argv)
        children.append(child)
        # /proc/cmdline can be transiently empty while exec is completing.
        # Register the Popen PID/starttime first; never leave an untracked child.
        record(dict(event="CREATED", role=role, expected_argv=argv, **owned))
        deadline = time.monotonic() + 2
        while owned["argv"] != argv and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
            current = identity(process)
            assert current["starttime"] == owned["starttime"], "UNKNOWN PID reuse"
            owned = current
        child["identity"] = owned
        assert owned["argv"] == argv and token in argv
        record(dict(event="START", role=role, **owned))
        return child

    def stop(child):
        process = child["process"]
        if process.poll() is None:
            assert child["identity"]["argv"] == child["expected_argv"], "UNKNOWN exec ownership: will not signal"
            assert identity(process) == child["identity"], "UNKNOWN ownership: will not signal"
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                assert identity(process) == child["identity"], "UNKNOWN ownership: will not kill"
                process.kill()
                process.wait(timeout=5)
        record(dict(event="STOP", role=child["role"], exit=process.returncode, **child["identity"]))

    def api_start():
        child = start("api", [sys.executable, str(repo / "tests/ordinary_process_child.py"), str(config), "api", token])
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            assert child["process"].poll() is None, "API exited before readiness"
            try:
                bound_path = root / f"api-{child['process'].pid}-bound.json"
                if not bound_path.exists():
                    time.sleep(0.05)
                    continue
                assert json.loads(bound_path.read_text()) == dict(
                    pid=child["identity"]["pid"], starttime=child["identity"]["starttime"],
                    token=token, host="127.0.0.1", port=port,
                )
                if client.get("/").status_code == 200 and child["process"].poll() is None:
                    return child
            except httpx.TransportError:
                pass
            time.sleep(0.05)
        raise AssertionError("Owned API readiness timed out")

    def worker(role):
        child = start(role, [sys.executable, str(repo / "tests/ordinary_process_child.py"), str(config), role, token])
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            assert child["process"].poll() is None, f"{role} Worker exited before completion"
            if (root / f"{role}-done.json").exists():
                return child
            time.sleep(0.05)
        raise AssertionError(f"{role} Worker timed out; no retry")

    def snapshot(instance, run_id):
        with store.tx() as connection:
            data = [dict(row) for row in connection.execute(select(internal_instance_data).where(
                internal_instance_data.c.instance_id == instance)).mappings()]
            history = [dict(row) for row in connection.execute(select(attempts).where(
                attempts.c.run_id == run_id)).mappings()]
        assert len(data) == 1 and len(history) == 2
        assert all(row["status"] == "VERIFIED" for row in history)
        return dict(data=data, attempts=history)

    def http_get(path):
        response = client.get(path)
        record(dict(event="HARNESS_HTTP_READ", path=path, status=response.status_code, text=response.text))
        assert response.status_code == 200, response.text
        return response.json()

    def closure():
        names = subprocess.check_output([
            "git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--",
            "src", "tests", "pyproject.toml",
        ], cwd=repo).decode().split("\0")
        return {name: hashlib.sha256((repo / name).read_bytes()).hexdigest()
                for name in sorted(set(names)) if name and (repo / name).is_file()}

    before = closure()
    (root / "source-before.json").write_text(json.dumps(before, indent=2))
    store = Store("sqlite:///" + str(root / "fixture.db"), test_only=True)
    store.initialize()
    store.user("isolated process fixture", "synthetic-test-A")
    store.user("isolated alternate identity", "synthetic-test-B")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    config.write_text(json.dumps(dict(port=port, token=token)))
    base = f"http://127.0.0.1:{port}"
    client = httpx.Client(base_url=base, headers={"Authorization": "Bearer synthetic-test-A"}, timeout=15,
                          trust_env=False)
    source_snapshot = None
    source_artifact = None
    try:
        api = api_start()
        made = client.post("/api/projects", json={"name": "Owned cross-process proof"})
        assert made.status_code == 201, made.text
        project = made.json()["id"]
        resource, card = material(client, project, SOURCE)
        target, target_card = material(client, project, COLD, "Cold operating notes")
        config.write_text(json.dumps(dict(port=port, token=token, resource=resource)))
        info = root / "info.json"
        info.write_text(json.dumps(dict(base_url=base, project=project, card=card["id"],
                                       target_card=target_card["id"], target_resource=target,
                                       output=str(root / "page.json.gz"), http_log=str(root / "page-http.jsonl.gz"),
                                       storage_path=str(root / "browser-storage.json"), durable=durable, token=token)))
        page = start("page", ["node", str(repo / "tests/ordinary_process_ui.cjs"), str(info), token])
        process = page["process"]
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            if not selector.select(timeout=1):
                assert process.poll() is None, "Page exited without completion receipt"
                continue
            line = process.stdout.readline()
            assert line, "Page output ended without completion receipt"
            request = json.loads(line)
            if request.get("done"):
                break
            command = request["command"]
            if command == "generation":
                stop(worker("generation"))
            elif command == "source-restart":
                source_worker = worker("source")
                rid = request["accepted"]["run_id"]
                result = http_get(f"/api/internal/instances/{request['instance']}/runs/{rid}")
                assert result["status"] == "SUCCEEDED" and result["result"]["checklist"]["source_content"] == SOURCE
                source_artifact = http_get(f"/api/internal/app-run-jobs/{rid}/spec-artifact")
                source_snapshot = snapshot(request["instance"], rid)
                (root / "source-saved.json").write_text(json.dumps(dict(request=request, result=result,
                    artifact=source_artifact, snapshot=source_snapshot), indent=2))
                old_api = api["identity"]
                stop(source_worker)
                stop(api)
                api = api_start()
                assert api["identity"]["pid"] != old_api["pid"]
                assert api["identity"]["starttime"] != old_api["starttime"]
                assert snapshot(request["instance"], rid) == source_snapshot
            elif command == "cold":
                stop(worker("cold"))
            else:
                assert command == "verify-history" and source_snapshot is not None
                assert snapshot(request["instance"], request["accepted"]["run_id"]) == source_snapshot
                assert http_get(f"/api/internal/app-run-jobs/{request['accepted']['run_id']}/spec-artifact") == source_artifact
                record(dict(event="SOURCE_HISTORY_UNCHANGED", status="PASS"))
            process.stdin.write(json.dumps(dict(id=request["id"], status=200)) + "\n")
            process.stdin.flush()
        else:
            raise AssertionError("Page workflow timed out; no retry")
        assert process.wait(timeout=10) == 0
        proof = json.loads(gzip.decompress((root / "page.json.gz").read_bytes()))
        assert proof["status"] == "PASS" and len(proof["checks"]) >= 23
        class Assets(HTMLParser):
            def __init__(self):
                super().__init__()
                self.paths = ["/", "/app.css"]

            def handle_starttag(self, tag, attrs):
                attributes = dict(attrs)
                if tag == "script" and attributes.get("src"):
                    self.paths.append(attributes["src"])

        expected_assets = Assets()
        expected_assets.feed((repo / "src/sim2act/web/index.html").read_text())
        assert [asset["path"] for asset in proof["assets"]] == expected_assets.paths * (3 if durable else 1)
        for asset in proof["assets"]:
            path = repo / "src/sim2act/web" / ("index.html" if asset["path"] == "/" else asset["path"].lstrip("/"))
            assert asset["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        calls = {role: [json.loads(line) for line in (root / f"{role}-wire.jsonl").read_text().splitlines()]
                 for role in ("generation", "source", "cold")}
        assert [len(calls[role]) for role in calls] == [3, 2, 2]
        assert SOURCE not in json.dumps(calls["cold"]) and COLD in json.dumps(calls["cold"])
        (root / "RESULT.json").write_text(json.dumps(dict(status="PASS", page_checks=len(proof["checks"]),
            dispatches={role: len(values) for role, values in calls.items()}, source_history_unchanged=True,
            browser="JSDOM_NOT_NATIVE", same_document=not durable, new_dom_count=3 if durable else 1,
            platform_storage_locks="TEST_ADAPTER_NOT_NATIVE", native_browser="NOT_RUN", postgres="NOT_RUN",
            windows="NOT_RUN", real_provider="NOT_RUN", semantic_acceptance="NOT_RUN"), indent=2))
    finally:
        cleanup_errors = []
        for child in reversed(children):
            try:
                stop(child)
            except Exception as error:
                cleanup_errors.append(dict(role=child["role"], identity=child["identity"], error=str(error)))
        for handle in handles:
            handle.close()
        client.close()
        store.engine.dispose()
        after = closure()
        (root / "source-after.json").write_text(json.dumps(after, indent=2))
        (root / "CLEANUP.json").write_text(json.dumps(dict(
            status="UNKNOWN" if cleanup_errors else "PASS", errors=cleanup_errors,
        ), indent=2))
        assert not cleanup_errors, "Some process ownership/cleanup is UNKNOWN; preserved without signaling it"
        assert after == before, "Source changed during proof"
