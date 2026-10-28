"""Actual read-only budget HTTP/JSDOM; synthetic ledger, no model or Worker IO."""

import hashlib
import json
import os
import socket
import subprocess
import threading
import time
from pathlib import Path

import uvicorn
from test_natural_spec_apps import COLD, material, setup
from test_spec_app_operations import snapshot

from sim2act import natural_live_admission as gate
from sim2act import natural_trial_budget as budget
from sim2act import natural_trial_preparation as preparation
from sim2act.api import create_app
from sim2act.db import fingerprint


def test_original_trial_budget_is_visible_unknown_and_readonly(env, monkeypatch, tmp_path):
    root = Path.cwd()
    production = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (root / "src/sim2act").rglob("*")
        if p.is_file() and p.suffix in {".py", ".js", ".html", ".css", ".json"}}
    data = setup(env)
    store, settings, client, user, pid, *_ = data
    assert store.sqlite and settings.mode == "mock" and not settings.live_enabled
    fixture_http, provider_calls = [], []

    def capture(reply):
        reply.read()
        fixture_http.append(dict(method=reply.request.method,
            path=reply.request.url.raw_path.decode(), body_text=reply.request.content.decode(),
            status=reply.status_code, response_text=reply.content.decode(),
            response_sha256=hashlib.sha256(reply.content).hexdigest()))

    def no_provider(*args, **kwargs):
        provider_calls.append("BLOCKED_PROVIDER_CALL")
        raise AssertionError("No provider HTTP is part of budget viewing")

    import httpx

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", no_provider)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", no_provider)
    client.event_hooks["response"].append(capture)
    try:
        _, cold_card = material(client, pid, COLD)
        with store.tx() as c:
            project = store.own_project(c, user, pid)
            store.add_grants(c, user, project["runtime_id"], pid, pid, ["artifact.save_text"])
        body = dict(bindings=[dict(card_id=card["id"], expected_version=card["version"])
            for card in (data[6], cold_card)])
        receipts = {}
        for key in ["empty-budget-view", "held-budget-view"]:
            base = f"/api/projects/{pid}/natural-trials/{key}"
            prepared = client.post(base + "/preparation", json=body)
            assert prepared.status_code == 200, prepared.text
            receipts[key] = prepared.json()
            consent = client.post(base + "/consent", json=dict(
                review_token=prepared.json()["review_token"], confirm_exact_scope=True))
            assert consent.status_code == 200 and consent.json()["live_allowed"] is False
        contract = gate.parse_contract(receipts["held-budget-view"]["contract"])
        approval_key = preparation.approval_key(contract)
        made = client.post(f"/api/projects/{pid}/goal-cards/{data[6]['id']}/application-runs",
            json=dict(expected_version=data[6]["version"], expected_fingerprint=data[6]["fingerprint"],
                request_key=contract.stage_keys.generate, family="natural_spec"))
        assert made.status_code == 202, made.text
        rid = made.json()["run_id"]
        job = store.claim("budget-view-fixture-claim", 30)
        assert job["id"] == rid and job["status"] == "RUNNING"
        fee = gate.SyntheticOnlyFeeAuthority(fingerprint(contract.model_dump()), contract.quota_subject)
        permits = []

        def admitted(store, c, principal, frozen, key, stage, run_id, version, fence):
            permit = gate.admit(store, c, principal, frozen, key, stage, run_id, version, fence, fee)
            assert permit.scope == "SYNTHETIC_ONLY" and permit.live_allowed is False
            permits.append(permit.model_dump())
            return permit

        scope = budget.scope_for(contract, approval_key)
        wire = b"synthetic-ledger-only".ljust(100, b" ")
        request = budget.Reservation(request_key="held-unknown", stage="generate", run_id=rid,
            expected_version=job["version"], fence=job["fence"], wire_bytes=len(wire),
            wire_sha256=hashlib.sha256(wire).hexdigest())
        reserved = budget.reserve(store, user, scope, contract, request, admission=admitted)
        result = budget.settle(store, user, scope, contract,
            budget.Settlement(request_key=request.request_key, response_sha256="b" * 64,
                response_ascii_bytes=10, prompt_tokens=5, completion_tokens=None, total_tokens=None),
            admission=admitted)
        assert result["status"] == "RECONCILING" and result["total_tokens"] is None
        assert result["ledger"]["halted"] and result["reserved_envelope"] == 1124
        other = store.project(user, "Other budget-view project")
        before = snapshot(store)
        assert not before["attempts"] and not before["reservations"] and not before["internal_app_runs"]
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        (tmp_path / "info.json").write_text(json.dumps(dict(base=f"http://127.0.0.1:{port}",
            project=pid, other_project=other, trial=contract.trial_key, empty_trial="empty-budget-view",
            approval_key=approval_key, contract_fingerprint=fingerprint(contract.model_dump()),
            run=rid, held_requests=1, held_envelope=1124)), encoding="utf-8")
        (tmp_path / "synthetic-ledger-fixture.json").write_text(json.dumps(dict(
            classification="SYNTHETIC_ONLY_REAL_ADMISSION_AND_LEDGER_NO_PROVIDER_OR_WORKER",
            permits=permits, request=request.model_dump(), reserved=reserved, settled=result,
            consent_is_live_authority=False, valid_live_tokens_created=0, worker_once_calls=0), indent=2), encoding="utf-8")
        server = uvicorn.Server(uvicorn.Config(create_app(store, settings), host="127.0.0.1",
            port=port, log_level="error"))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        try:
            until = time.monotonic() + 10
            while not server.started:
                assert thread.is_alive() and time.monotonic() < until
                time.sleep(.01)
            try:
                process = subprocess.run(["node", str(Path(__file__).with_name("natural_trial_budget_view_ui.cjs")),
                    str(tmp_path)], capture_output=True, text=True, timeout=360,
                    env={**os.environ, "NODE_PATH": os.environ.get("NODE_PATH", str(root / "scripts/engineering-ci/node_modules"))})
            except subprocess.TimeoutExpired as error:
                for name, content in [("stdout", error.stdout), ("stderr", error.stderr)]:
                    (tmp_path / ("driver." + name)).write_bytes(content.encode() if isinstance(content, str) else content or b"")
                raise
            (tmp_path / "driver.stdout").write_text(process.stdout, encoding="utf-8")
            (tmp_path / "driver.stderr").write_text(process.stderr, encoding="utf-8")
            assert process.returncode == 0, process.stdout + process.stderr
            page = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
            assert page["status"] == "PASS" and not page["downloads"]
            assert all(row["method"] == "GET" for row in page["requests"])
            assert len(page["static_resource_loads"]) == 27
            for row in page["static_resource_loads"]:
                source = root / "src/sim2act/web" / (row["path"].lstrip("/") or "index.html")
                assert row["status"] == 200 and row["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
            after = snapshot(store)
            assert after == before, [name for name in before if before[name] != after[name]]
            assert not provider_calls
            assert production == {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in production}
            (tmp_path / "proof.json").write_text(json.dumps(dict(status="PASS",
                production_sha256=production, before_fingerprint=fingerprint(before), after_fingerprint=fingerprint(after),
                table_fingerprints={name: dict(rows=len(rows), sha256=fingerprint(rows)) for name, rows in before.items()},
                protected_tables_unchanged=sorted(before), changed_tables=[], page_post_requests=0,
                page_worker_calls=0, provider_calls=provider_calls, real_model_requests=0,
                valid_live_tokens_created=0, pg="NOT_RUN", native_browser="NOT_RUN", windows="NOT_RUN",
                real_semantic_acceptance="NOT_RUN"), indent=2), encoding="utf-8")
        finally:
            server.should_exit = True
            thread.join(10)
            assert not thread.is_alive(), "Owned loopback server did not stop"
    finally:
        (tmp_path / "fixture-http.json").write_text(json.dumps(fixture_http, indent=2), encoding="utf-8")
        (tmp_path / "provider-calls.json").write_text(json.dumps(provider_calls), encoding="utf-8")
        client.close()
