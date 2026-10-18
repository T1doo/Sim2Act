"""Bounded Goal-only revision through original HTTP/CHECK/Release/CAS and page."""

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from test_csv_goal_revisions import baseline
from test_csv_owner_review import choices, endpoint, prepare_review
from test_local_record_apps import snapshot
from test_persistent_app_runs import NoModel

from sim2act.db import Store, internal_run_bindings, run_contracts
from sim2act.worker import Worker


def test_initial_noop_and_existing_different_column_contract(env, tmp_path):
    data, aid, release, instance, cid, content, app = baseline(env)
    client = data[2]
    assert client.put(f"/api/goal-cards/{cid}", json={**content, "expected_version": 1}).status_code == 200
    assert client.post(f"/api/projects/{data[5]}/apps/{aid}/delivery-graph/derive", json={
        "request_key": "compatibility-anchor", "expected_candidate_fingerprint": app["fingerprint"],
    }).status_code == 201
    path = f"/api/internal/instances/{instance['id']}/csv-goal-revisions"
    ctx = client.get(path + "/context").json()
    body = dict(request_key="initial-noop", expected_revision=instance["revision"],
                expected_release_fingerprint=release["fingerprint"], expected_graph_fingerprint=ctx["graph_fingerprint"],
                goal_version=2, goal_fingerprint=ctx["goal"]["fingerprint"], baseline_column="amount", column="amount")
    before = snapshot(data[0])
    denied = client.post(path + "/previews", json=body)
    assert denied.status_code == 409, denied.text
    assert denied.json()["error"]["submission_rejection"]["acceptance"] == "NOT_ACCEPTED"
    assert snapshot(data[0]) == before
    accepted = client.post(path + "/previews", json={**body, "request_key": "old-combined-shape", "column": "quantity"})
    assert accepted.status_code == 201, accepted.text
    value = accepted.json()
    nodes = value["baseline_graph"]["graph"]["nodes"]
    assert set(value["impact"]["changed_nodes"]) == {n["id"] for n in nodes if n["kind"] == "GOAL" or n["key"] == "action:aggregate"}
    assert client.get(path + "/previews/old-combined-shape").json() == value
    (tmp_path / "contract-proof.json").write_text(json.dumps(dict(noop=denied.json(),
        accepted=value, all_55_noop_tables_equal=True, scope="finite API compatibility, no Worker"), indent=2))


def test_goal_only_revision_actual_page(env, tmp_path, monkeypatch):
    store, settings, client, *_ = env
    assert store.sqlite and store.test_only and settings.mode == "mock" and not settings.token
    http, workers, claims = [], [], []
    original = client.request

    def save(name, value):
        (tmp_path / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")

    def request(method, url, **kwargs):
        started = time.monotonic()
        response = original(method, url, **kwargs)
        http.append(dict(method=method, path=str(url), body=kwargs.get("json"), status=response.status_code,
                         response=response.text, elapsed_seconds=time.monotonic() - started))
        save("actual-http.json", http)
        return response

    def work(rid):
        cold = Store(settings.database_url, test_only=True)
        worker = Worker(cold, settings, NoModel())
        original_claim = cold.claim

        def claim(worker_id, *args, **kwargs):
            result = original_claim(worker_id, *args, **kwargs)
            claims.append(dict(worker_id=worker_id, run_id=result["id"] if result else None,
                               fence=result["fence"] if result else None))
            save("claims.json", claims)
            assert result and result["id"] == rid
            return result

        cold.claim = claim
        record = dict(worker_id=worker.id, expected_run_id=rid, model="NoModel",
                      started_utc=datetime.now(timezone.utc).isoformat())
        workers.append(record)
        save("workers.json", workers)
        started = time.monotonic()
        try:
            record["once_result"] = worker.once()
            assert record["once_result"]
        finally:
            record["elapsed_seconds"] = time.monotonic() - started
            record["finished_utc"] = datetime.now(timezone.utc).isoformat()
            save("workers.json", workers)
            cold.engine.dispose()

    monkeypatch.setattr(client, "request", request)
    save("before-fixture.json", snapshot(store))
    data, aid, release, instance, cid, content, app = baseline(env)
    old = client.post(f"/api/internal/instances/{instance['id']}/runs", json=dict(
        expected_revision=instance["revision"], expected_release_fingerprint=release["fingerprint"],
        input={"column": "amount"}, request_key="goal-only-before", csv_review="FREEZE_SUM_ONLY_WITHOUT_MD"))
    assert old.status_code == 202, old.text
    old_id = old.json()["run_id"]
    work(old_id)
    _, prepared, _ = prepare_review(data, instance, old_id)
    accepted = client.post(endpoint(instance, old_id) + "-requests", json=choices(prepared))
    assert accepted.status_code == 201, accepted.text
    old_state = client.get(endpoint(instance, old_id)).json()
    assert old_state["owner_acceptance"] == "ACCEPTED"
    before_page = snapshot(store)
    save("before-page.json", before_page)
    info = dict(project=data[5], app=aid, instance=instance["id"], old=old_id, card=cid,
                acceptance="\n".join(content["acceptance_checks"]), newCheck="新增：逐行保留 amount 的核对依据",
                output=str(tmp_path / "page-proof.json"))
    save("info.json", info)
    path = f"/api/internal/instances/{instance['id']}/csv-goal-revisions"
    process, new_id = None, None
    try:
        with (tmp_path / "node.stderr").open("w") as errors:
            process = subprocess.Popen(["node", "tests/goal_only_revision.cjs", str(tmp_path / "info.json")],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True,
                env={**os.environ, "NODE_PATH": os.environ.get("NODE_PATH", str(Path.cwd() / "scripts/engineering-ci/node_modules"))})
            for line in process.stdout:
                message = json.loads(line)
                if message.get("done"):
                    break
                command = message.get("command")
                if command == "worker":
                    work(message["run"])
                    response_body = dict(status=200, text="{}")
                elif command == "delivery-proof":
                    new_id = message["run"]
                    new = client.get(f"/api/internal/instances/{instance['id']}/runs/{new_id}").json()
                    state = client.get(endpoint(instance, new_id)).json()
                    original_state = client.get(endpoint(instance, old_id)).json()
                    assert new["status"] == "SUCCEEDED" and new["result"]["sum"] == "30" and new["result"]["column"] == "amount"
                    assert new["result_version"] == 2 and state["owner_acceptance"] == "PENDING"
                    assert original_state["history"] == old_state["history"]
                    assert original_state["latest"]["status"] == "ACCEPTED" and original_state["owner_acceptance"] == "STALE"
                    with store.tx() as connection:
                        contract = connection.execute(select(run_contracts.c.snapshot).where(run_contracts.c.run_id == new_id)).scalar_one()
                        binding = connection.execute(select(internal_run_bindings.c.snapshot).where(internal_run_bindings.c.run_id == new_id)).scalar_one()
                    assert contract["goal"]["goal"].endswith("v2")
                    assert info["newCheck"] in json.dumps(binding["csv_goal"], ensure_ascii=False)
                    frozen_preview = json.loads(next(row["response"] for row in http
                        if row["method"] == "POST" and row["path"] == path + "/previews" and row["status"] == 201))
                    assert binding["csv_goal"] == frozen_preview["context"]["goal"]
                    current = snapshot(store)
                    for name in ("principals", "grants", "resources", "app_drafts"):
                        assert current[name] == before_page[name], name
                    for name in ("internal_releases", "internal_instance_data", "internal_app_runs", "run_contracts", "csv_owner_records", "csv_owner_seals"):
                        assert all(row in current[name] for row in before_page[name]), name
                    save("after-delivery.json", current)
                    save("delivery-proof.json", dict(old_owner=old_state, new_owner=state, new_run=new,
                        contract=contract, binding=binding, preview_key=message["preview_key"], preserved_tables=["principals", "grants", "resources", "app_drafts"]))
                    response_body = dict(status=200, text="{}")
                elif command == "noop-proof":
                    ctx = client.get(path + "/context").json()
                    body = dict(request_key="adopted-noop", expected_revision=ctx["instance_revision"],
                        expected_release_fingerprint=ctx["release_fingerprint"], expected_graph_fingerprint=ctx["graph_fingerprint"],
                        goal_version=ctx["goal"]["version"], goal_fingerprint=ctx["goal"]["fingerprint"], baseline_column="amount", column="amount")
                    before = snapshot(store)
                    denied = client.post(path + "/previews", json=body)
                    assert denied.status_code == 409, denied.text
                    assert denied.json()["error"]["submission_rejection"]["acceptance"] == "NOT_ACCEPTED"
                    assert snapshot(store) == before
                    save("noop-before.json", before)
                    save("noop-after.json", snapshot(store))
                    response_body = dict(status=200, text="{}")
                elif command == "final-proof":
                    preview = client.get(path + "/previews/" + message["key"]).json()
                    assert preview["spec_revision"] == 3 and preview["context"]["parent"]["column"] == "amount"
                    goal = next(n for n in preview["parent_graph"]["graph"]["nodes"] if n["kind"] == "GOAL")
                    assert preview["impact"]["changed_nodes"] == [goal["id"]]
                    assert preview["effective_candidate"]["manifest"]["input_schema"]["properties"]["column"]["enum"] == ["amount"]
                    parent = preview["parent_graph"]["graph"]["nodes"]
                    assert {n["key"]: n["id"] for n in parent} == {n["key"]: n["id"] for n in preview["effective_graph"]["graph"]["nodes"]}
                    save("successive-preview.json", preview)
                    response_body = dict(status=200, text="{}")
                else:
                    response = client.request(message["method"], message["path"], json=message.get("body"), headers=message.get("headers"))
                    response_body = dict(status=response.status_code, text=response.text, content_type=response.headers.get("content-type"))
                process.stdin.write(json.dumps(dict(id=message["id"], **response_body)) + "\n")
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=20)
        assert code == 0, (tmp_path / "node.stderr").read_text()
        proof = json.loads((tmp_path / "page-proof.json").read_text())
        assert proof["status"] == "PASS"
        assert len(workers) == len(claims) == 3 and new_id
        for asset in proof["assets"]:
            source = Path("src/sim2act/web") / (asset["path"].lstrip("/") or "index.html")
            assert hashlib.sha256(source.read_bytes()).hexdigest() == asset["sha256"]
        save("measurement.json", dict(status="PASS", workers=workers, claims=claims, model_requests=0,
            page_checks=len(proof["checks"]), page_requests=len(proof["requests"]), assets=len(proof["assets"]), boots=proof["boots"],
            fixture_model="MOCK_DETERMINISTIC_CSV_SUM.v1", real_model="NOT_RUN", lock_scenario="NOT_RUN"))
    finally:
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        save("after-page-or-failure.json", snapshot(store))
        loaded = {str(Path(module.__file__).resolve()): hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
                  for module in tuple(sys.modules.values()) if getattr(module, "__file__", None)
                  and str(Path(module.__file__).resolve()).startswith(str(Path.cwd() / "src/sim2act"))
                  and Path(module.__file__).is_file()}
        save("loaded-product-module-sha256.json", loaded)
