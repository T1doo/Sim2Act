"""Owned real backend process close/reopen; JSDOM storage is an explicit adapter."""
import hashlib
import json
import os
import queue
import shutil
import socket
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_pa_spec_apps import SOURCE, confirm, generate, instance, material

from sim2act import synthetic_workspace as workspace
from sim2act.api import create_app
from sim2act.db import internal_app_runs, internal_run_bindings, meta, runs


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def business_fingerprints(root):
    _, store, _ = workspace.open_workspace(root)
    try:
        with store.engine.connect() as c:
            return {table.name: hashlib.sha256(json.dumps(sorted(
                json.dumps(dict(row), sort_keys=True, default=str)
                for row in c.execute(select(table)).mappings()), sort_keys=True).encode()).hexdigest()
                for table in meta.sorted_tables if table.name != "heartbeats"}
    finally:
        store.engine.dispose()


def start(root, log, *, new=False):
    source = Path(__file__).resolve().parents[1] / "src"
    child = subprocess.Popen([sys.executable, "-B", "-m", "sim2act.cli", "synthetic-workspace",
        "--data-dir", str(root), "--control-stdin", *(["--new"] if new else [])],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        env={**os.environ, "PYTHONPATH": str(source)})
    messages, lines = queue.Queue(), []

    def read():
        with log.open("w") as stream:
            for line in child.stdout:
                lines.append(line)
                stream.write(line)
                stream.flush()
                messages.put(line)
        messages.put(None)

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    try:
        end = time.monotonic() + 25
        while time.monotonic() < end:
            line = messages.get(timeout=max(.01, end-time.monotonic()))
            if line is None:
                return child, reader, lines, None
            if line.startswith("{"):
                event = json.loads(line)
                if event.get("event") == "SYNTHETIC_WORKSPACE_READY":
                    return child, reader, lines, event
        raise AssertionError("Owned backend did not reach READY: " + "".join(lines))
    except Exception:
        child.stdin.close()
        child.wait(timeout=20)
        reader.join(timeout=5)
        raise


def stop(child, reader, lines):
    if not child.stdin.closed:
        child.stdin.close()
    assert child.wait(timeout=20) == 0, "".join(lines)
    reader.join(timeout=5)
    assert not reader.is_alive()
    child.stdout.close()
    receipt = next(json.loads(line) for line in lines
        if line.startswith('{') and json.loads(line).get("event") == "SYNTHETIC_WORKSPACE_STOPPED")
    assert receipt["worker_stopped"] and receipt["clean"] and receipt["data_preserved"]
    return receipt


def test_origin_publication_concurrency_and_replacement_fail_closed(tmp_path):
    root, store, marker = workspace.open_workspace(tmp_path / "origin", new=True)
    store.engine.dispose()
    barrier = threading.Barrier(2)

    def publish(port):
        barrier.wait(timeout=5)
        try:
            return workspace._bind_desktop_origin(root, marker, port, None)
        except workspace.WorkspaceError as error:
            return str(error)

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(publish, [49101, 49102]))
    winners = [r for r in results if isinstance(r, tuple)]
    assert len(winners) == 1 and results.count("DESKTOP_ORIGIN_CHANGED") == 1
    winner = winners[0]
    assert workspace._read_desktop_origin(root) == winner
    path = root / workspace.DESKTOP_ORIGIN
    before = path.read_bytes()
    # A same-bytes replacement is still a different startup record.
    replacement = root / "replacement"
    replacement.write_bytes(before)
    replacement.replace(path)
    with pytest.raises(workspace.WorkspaceError, match="DESKTOP_ORIGIN_CHANGED"):
        workspace._bind_desktop_origin(root, marker, winner[0]["port"], winner)
    assert path.read_bytes() == before and not list(root.glob(".desktop-origin-pending-*"))


def test_same_bytes_replacement_during_first_publication_is_not_adopted(tmp_path, monkeypatch):
    root, store, marker = workspace.open_workspace(tmp_path / "origin", new=True)
    store.engine.dispose()
    operation = "rename" if os.name == "nt" else "link"
    original_publish = getattr(os, operation)

    def replace_published(source, destination, **kwargs):
        original_publish(source, destination, **kwargs)
        replacement = root / "replacement"
        replacement.write_bytes(Path(destination).read_bytes())
        replacement.replace(destination)

    monkeypatch.setattr(workspace.os, operation, replace_published)
    with pytest.raises(workspace.WorkspaceError, match="DESKTOP_ORIGIN_CHANGED"):
        workspace._bind_desktop_origin(root, marker, 49104, None)
    assert workspace._read_desktop_origin(root)[0]["port"] == 49104
    assert not list(root.glob(".desktop-origin-pending-*"))


@pytest.mark.parametrize("fault", ["malformed", "bool-port", "host", "oversize", "linked", "foreign-workspace"])
def test_invalid_origin_never_rewritten(tmp_path, fault):
    root, store, marker = workspace.open_workspace(tmp_path / "origin", new=True)
    store.engine.dispose()
    saved = workspace._bind_desktop_origin(root, marker, 49103, None)
    path = root / workspace.DESKTOP_ORIGIN
    if fault == "linked":
        target = root / "other-record"
        path.rename(target)
        path.symlink_to(target)
    elif fault == "foreign-workspace":
        changed = {**marker, "principal_id": "user_" + "0"*32}
        before = path.read_bytes()
        with pytest.raises(workspace.WorkspaceError, match="DESKTOP_ORIGIN_CHANGED"):
            workspace._bind_desktop_origin(root, changed, 49103, saved)
        assert path.read_bytes() == before
        return
    else:
        record = dict(saved[0])
        if fault == "bool-port":
            record["port"] = True
        if fault == "host":
            record["host"] = "0.0.0.0"
        path.write_bytes(b'{' if fault == "malformed" else b'x'*4097 if fault == "oversize" else workspace._origin_bytes(record))
    before = path.read_bytes()
    with pytest.raises(workspace.WorkspaceError):
        workspace._read_desktop_origin(root)
    assert path.read_bytes() == before


def test_real_owned_restart_retains_spec_original_key_and_busy_port_never_falls_back(tmp_path):
    if not shutil.which("node") or subprocess.run(["node", "-e", "require.resolve('jsdom')"], capture_output=True).returncode:
        pytest.skip("Existing Node/jsdom developer tools required")
    root, store, marker = workspace.open_workspace(tmp_path / "workspace", new=True)
    settings = replace(workspace.settings_for(root), goal_planner_provider="intern-s2")
    with TestClient(create_app(store, settings)) as client:
        client.headers["Authorization"] = "Bearer " + workspace.TOKEN
        pid = client.post("/api/projects", json=dict(name="Synthetic restart")).json()["id"]
        rid, card = material(client, pid, SOURCE)
        data = store, settings, client, marker["principal_id"], pid, rid, card
        generation, generated, sent = generate(data)
        assert len(sent) == 3
        made = confirm(data, generation, generated)
        assert made.status_code == 200, made.text
        release, inst = instance(data, made.json()["id"])
    store.engine.dispose()
    profile = tmp_path / "origin-partitioned-profile.json"
    info = dict(project=pid, instance=inst["id"], token=workspace.TOKEN, profile=str(profile))
    proof, child = [], None
    try:
        for serial, mode in enumerate(("submit-lost", "recover-corrupt", "recover-valid")):
            child, reader, lines, ready = start(root, tmp_path/f"backend-{serial}.log")
            assert ready is not None, "".join(lines)
            if serial:
                assert ready["url"] == proof[0]["origin"]
            info.update(base=ready["url"], mode=mode, output=str(tmp_path/f"page-{serial}.json"))
            path = tmp_path/f"info-{serial}.json"
            path.write_text(json.dumps(info))
            result = subprocess.run(["node", "tests/desktop_origin_recovery.cjs", str(path)], capture_output=True, text=True, timeout=45)
            (tmp_path/f"node-{serial}.log").write_text(result.stdout+result.stderr)
            assert result.returncode == 0, result.stdout+result.stderr
            page = json.loads(Path(info["output"]).read_text())
            assert page["status"] == "PASS"
            if not serial:
                info.update(accepted=page["accepted"], request=page["request"])
                # The ordinary backend Worker, not the browser adapter, performs
                # the deterministic saved spec. The fixture's three model calls
                # happened only during generation, before any child existed.
                # The real launcher serializes API reads behind an in-flight
                # Worker transaction. Bound this observation explicitly; the
                # default HTTPX five-second client timeout is not its lease.
                with httpx.Client(base_url=ready["url"], headers={"Authorization":"Bearer "+workspace.TOKEN}, timeout=20) as api:
                    end = time.monotonic()+20
                    while time.monotonic() < end:
                        response = api.get(f"/api/internal/instances/{inst['id']}/spec-run-requests/{info['request']['request_key']}")
                        assert response.status_code == 200, response.text
                        if response.json()["status"] == "SUCCEEDED":
                            break
                        time.sleep(.1)
                    assert response.json()["status"] == "SUCCEEDED", response.text
            stopped = stop(child, reader, lines)
            child = None
            proof.append(dict(origin=ready["url"], worker_id=ready["worker_id"], page=page, stopped=stopped,
                              database_sha256=digest(root/workspace.DATABASE), business_tables=business_fingerprints(root),
                              origin_sha256=digest(root/workspace.DESKTOP_ORIGIN)))
        assert len({p["worker_id"] for p in proof}) == 3
        # A fresh actual Worker deliberately persists its own heartbeat. Every
        # other table, including Runs/operations/typed data/grants, must agree.
        assert all(p["business_tables"] == proof[0]["business_tables"] for p in proof)
        assert len({p["origin_sha256"] for p in proof}) == 1
        _, cold, _ = workspace.open_workspace(root)
        try:
            with cold.engine.connect() as c:
                assert c.execute(select(func.count()).select_from(internal_app_runs).where(internal_app_runs.c.instance_id==inst["id"])).scalar_one() == 1
                assert c.execute(select(func.count()).select_from(internal_run_bindings).where(internal_run_bindings.c.run_id==info["accepted"]["run_id"])).scalar_one() == 1
                assert c.execute(select(runs.c.status).where(runs.c.id==info["accepted"]["run_id"])).scalar_one() == "SUCCEEDED"
        finally:
            cold.engine.dispose()
        before = digest(root/workspace.DATABASE), (root/workspace.DESKTOP_ORIGIN).read_bytes()
        port = json.loads(before[1])["port"]
        with socket.socket() as occupant:
            occupant.bind(("127.0.0.1",port));occupant.listen(1);occupant.settimeout(.05)
            child, reader, lines, ready = start(root,tmp_path/"occupied.log")
            assert ready is None and child.wait(timeout=10)==1
            reader.join(timeout=5);child.stdin.close();child.stdout.close();child=None
            assert "PORT_UNAVAILABLE" in "".join(lines)
            with pytest.raises(socket.timeout):
                occupant.accept()
        assert before==(digest(root/workspace.DATABASE),(root/workspace.DESKTOP_ORIGIN).read_bytes())
        (tmp_path/"restart-proof.json").write_text(json.dumps(dict(status="PASS",restarts=proof,model_mock_generation_calls=len(sent),runtime_real_model_calls=0,runtime_mock_calls=0,windows_webview="NOT_RUN",busy_port_no_connection=True),indent=2))
    finally:
        if child is not None and child.poll() is None:
            stop(child, reader, lines)
