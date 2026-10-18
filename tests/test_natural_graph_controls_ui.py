"""Fresh natural-app graph controls, actual HTTP/JSDOM, offline generation only."""

import hashlib
import json
import os
import socket
import subprocess
import threading
import time
from pathlib import Path

import uvicorn
from test_natural_spec_apps import ready, setup
from test_spec_app_operations import snapshot

from sim2act.api import create_app
from sim2act.db import fingerprint


def exact_graph_metadata(before, after, posts, app, instance, principal, project):
    aid = app["id"]
    added = {table: [row for row in after[table] if row not in before[table]] for table in [
        "delivery_graph_states", "delivery_graph_anchors", "delivery_graph_locks",
        "delivery_graph_requests", "delivery_graph_source_versions"]}
    journal = added["delivery_graph_requests"]
    expected = {}
    graphs = []
    for post in posts:
        body, answer = post["body"], post["response"]
        if post["status"] == 400:
            assert not any(row["request_key"] == body["request_key"] for row in journal)
            continue
        if post["path"].endswith("/derive"):
            value = {k: v for k, v in answer.items() if k != "cached"}
            expected[aid, "derive", body["request_key"]] = body, value
            graphs.append(value)
        elif post["path"].endswith("/manual-locks"):
            value = {k: v for k, v in answer.items() if k not in {"cached", "receipt_status", "is_current"}}
            for kind in ["manual_edit_lock", "manual_edit_lock_seal"]:
                expected[aid, kind, body["request_key"]] = body, value
            canonical = {k: body[k] for k in ["expected_graph_fingerprint", "change", "locked", "request_key"]}
            lock = dict(namespace="delivery-graph-apps.v1", app_id=aid, project_id=project,
                lock=answer["lock"], needs_derive=True, patch_executed=False, publishable=False)
            expected[aid, "lock", body["request_key"]] = canonical, lock
        else:
            for kind in ["natural-local-logic.v1.preview", "natural-local-logic.v1.preview_seal"]:
                expected[instance["id"], kind, body["request_key"]] = body, answer
    assert len(expected) == len(journal) == 11
    assert {(row["app_id"], row["kind"], row["request_key"]) for row in journal} == set(expected)
    for row in journal:
        request, response = expected[row["app_id"], row["kind"], row["request_key"]]
        assert row["principal_id"] == principal
        assert row["snapshot"] == dict(request=request, response=response)
        assert row["request_fingerprint"] == fingerprint(request)
        assert row["fingerprint"] == fingerprint(row["snapshot"])
    anchors = sorted(added["delivery_graph_anchors"], key=lambda row: row["revision"])
    assert len(anchors) == 3 and [row["revision"] for row in anchors] == [1, 2, 3]
    for anchor, graph in zip(anchors, graphs, strict=True):
        assert anchor["app_id"] == aid and anchor["fingerprint"] == fingerprint(anchor["snapshot"])
        assert anchor["snapshot"]["graph"] == graph["graph"]
        assert anchor["snapshot"]["source_versions"] == graph["source_versions"]
    assert len(added["delivery_graph_states"]) == 1
    state = added["delivery_graph_states"][0]
    assert (state["app_id"], state["project_id"], state["principal_id"], state["runtime_id"]) == (
        aid, project, principal, app["runtime_id"])
    assert state["anchor_id"] == anchors[-1]["id"] and state["snapshot"] == anchors[-1]["snapshot"]
    assert state["fingerprint"] == anchors[-1]["fingerprint"]
    versions = added["delivery_graph_source_versions"]
    assert len(versions) == len(graphs[-1]["source_versions"])
    assert {row["logical_key"] for row in versions} == set(graphs[-1]["source_versions"])
    for row in versions:
        version = graphs[-1]["source_versions"][row["logical_key"]]
        assert row["app_id"] == aid and row["fingerprint"] == fingerprint(row["snapshot"])
        assert row["revision"] == row["snapshot"]["revision"] == version["revision"]
        assert row["logical_key"] == row["snapshot"]["logical_key"]
        assert fingerprint(row["snapshot"]["definition"]) == version["content_fingerprint"]
    assert len(added["delivery_graph_locks"]) == 1
    lock = added["delivery_graph_locks"][0]
    unlocked = next(post["response"]["lock"] for post in posts
        if post["path"].endswith("/manual-locks") and post["body"]["locked"] is False)
    assert lock["app_id"] == aid and lock["node_id"] == unlocked["node_id"]
    assert lock["snapshot"] == unlocked and lock["fingerprint"] == fingerprint(unlocked)


def test_fresh_natural_app_derives_and_controls_edit_locks_from_page(env, tmp_path):
    root = Path.cwd()
    production = {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (root / "src/sim2act").rglob("*")
        if path.is_file() and path.suffix in {".py", ".js", ".html", ".css"}
    }
    data = setup(env)
    store, settings, client, principal, project, *_ = data
    assert store.sqlite and settings.mode == "mock"
    _, aid, release, instance, generation_wire = ready(data, "parallel")
    assert len(generation_wire) == 3
    other = store.project(principal, "Other graph-controls project")
    app = client.get("/api/apps/" + aid).json()
    assert app["candidate"]["namespace"] == "pa-natural-spec-app.v1"
    before = snapshot(store)
    assert not before["delivery_graph_states"]
    assert not before["delivery_graph_anchors"]
    assert not before["delivery_graph_locks"]
    assert not before["internal_app_runs"] and not before["internal_instance_data"]
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "info.json").write_text(json.dumps(dict(
        base=f"http://127.0.0.1:{port}", project=project, other_project=other,
        app=aid, instance=instance["id"], changed_node_key="action:qualifiers_pick")), encoding="utf-8")
    (tmp_path / "generation-wire.json").write_text(json.dumps(generation_wire, indent=2), encoding="utf-8")
    server = uvicorn.Server(uvicorn.Config(create_app(store, settings), host="127.0.0.1",
        port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    result = None
    try:
        until = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < until
            time.sleep(.01)
        try:
            result = subprocess.run(["node", str(Path(__file__).with_name("natural_graph_controls_ui.cjs")),
                str(tmp_path)], capture_output=True, text=True, timeout=360,
                env={**os.environ, "NODE_PATH": str(root / "scripts/engineering-ci/node_modules")})
        except subprocess.TimeoutExpired as error:
            for name, content in [("stdout", error.stdout), ("stderr", error.stderr)]:
                (tmp_path / ("driver." + name)).write_bytes(
                    content.encode() if isinstance(content, str) else content or b"")
            raise
        (tmp_path / "driver.stdout").write_text(result.stdout, encoding="utf-8")
        (tmp_path / "driver.stderr").write_text(result.stderr, encoding="utf-8")
        assert result.returncode == 0, result.stdout + result.stderr
        page = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
        assert page["status"] == "PASS", page
        posts = [r for r in page["requests"] if r["method"] == "POST"]
        derive = [r for r in posts if r["path"].endswith("/delivery-graph/derive")]
        lock = [r for r in posts if r["path"].endswith("/delivery-graph/manual-locks")]
        preview = [r for r in posts if r["path"].endswith("/logic-patches/previews")]
        assert len(posts) == 7 and len(derive) == 3 and len(lock) == len(preview) == 2
        assert [r["status"] for r in derive] == [201, 201, 201]
        assert [r["body"]["locked"] for r in lock] == [True, False]
        assert [r["status"] for r in lock] == [201, 201]
        assert [r["status"] for r in preview] == [400, 201]
        assert preview[0]["response"]["error"]["code"] == "LOCK_CONFLICT"
        assert preview[0]["body"]["request_key"] != preview[1]["body"]["request_key"]
        assert preview[1]["response"]["effective_candidate"]["actions"][2]["revision"] == 2
        assert all(not r["path"].endswith(("/checks", "/version-approvals", "/commit",
            "/pa-use-runs", "/pb-use-runs")) for r in posts)
        for row in page["static_resource_loads"]:
            path = root / "src/sim2act/web" / (row["path"].lstrip("/") or "index.html")
            assert row["status"] == 200
            assert row["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert len(page["static_resource_loads"]) == 27
        after = snapshot(store)
        allowed = {"delivery_graph_states", "delivery_graph_anchors", "delivery_graph_locks",
            "delivery_graph_requests", "delivery_graph_source_versions"}
        for table in before:
            if table not in allowed:
                assert before[table] == after[table], table
            else:
                assert all(row in after[table] for row in before[table]), table
        exact_graph_metadata(before, after, posts, app, instance, principal, project)
        assert after["internal_releases"] == before["internal_releases"] == [
            next(row for row in before["internal_releases"] if row["id"] == release["id"])]
        assert after["internal_instances"] == before["internal_instances"]
        assert len(after["delivery_graph_locks"]) == 1
        saved_lock = after["delivery_graph_locks"][0]
        assert saved_lock["snapshot"]["revision"] == 2 and saved_lock["snapshot"]["locked"] is False
        assert len(after["attempts"]) == len(before["attempts"])
        assert not after["internal_app_runs"] and not after["internal_instance_data"]
        assert production == {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in production}
        proof = dict(status="PASS", production_sha256=production, before_fingerprint=fingerprint(before),
            after_fingerprint=fingerprint(after), protected_tables_unchanged=sorted(set(before) - allowed),
            changed_tables=sorted(t for t in before if before[t] != after[t]),
            posts=[dict(path=r["path"], status=r["status"]) for r in posts],
            generation_mock_requests=3, page_model_requests=0, page_worker_calls=0,
            real_model_requests=0, business_data_writes=0, native_browser="NOT_RUN", pg="NOT_RUN",
            windows="NOT_RUN", real_semantic_acceptance="NOT_RUN")
        (tmp_path / "proof.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive(), "Owned loopback server did not stop"
        client.close()
