"""Accepted View AST over normal synthetic generation, Worker and actual HTTP page."""

import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import test_goal_text_applications as literal
from test_local_record_apps import snapshot
from test_persistent_app_runs import NoModel

from sim2act.worker import Worker


def test_manifest_text_table_actual_page(env, tmp_path, monkeypatch):
    data = literal.setup(env)
    store, settings, client, _, _, _, _ = data
    assert store.sqlite and store.test_only and settings.mode == "mock" and not settings.token
    http, workers, claims = [], [], []
    original_request, original_claim = client.request, store.claim

    def request(method, path, **kwargs):
        response = original_request(method, path, **kwargs)
        http.append(dict(method=method, path=str(path), body=kwargs.get("json"),
                         status=response.status_code, response=response.text))
        return response

    def claim(worker_id, *args, **kwargs):
        result = original_claim(worker_id, *args, **kwargs)
        claims.append(dict(worker_id=worker_id, run_id=result["id"] if result else None,
                           fence=result["fence"] if result else None))
        return result

    def observed_worker(*args, **kwargs):
        worker = Worker(*args, **kwargs)
        original_once = worker.once

        def once():
            observed = dict(worker_id=worker.id, started_utc=datetime.now(timezone.utc).isoformat(),
                            runtime="MockTransport generation" if kwargs.get("goal_planner_transport") else "NoModel")
            workers.append(observed)
            started = time.monotonic()
            try:
                value = original_once()
                observed["once_result"] = value
                return value
            finally:
                observed["elapsed_seconds"] = time.monotonic() - started
                observed["finished_utc"] = datetime.now(timezone.utc).isoformat()

        worker.once = once
        return worker

    def save(name, value):
        (tmp_path / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")

    monkeypatch.setattr(client, "request", request)
    monkeypatch.setattr(store, "claim", claim)
    monkeypatch.setattr(literal, "Worker", observed_worker)
    save("before-fixture.json", snapshot(store))
    process, before_page = None, None
    try:
        def compose(raw, turn, _):
            if turn == 2:
                value = json.loads(raw["choices"][0]["message"]["content"])
                value["manifest"]["views"] = [
                    dict(component_ref="text", output_field="term"),
                    dict(component_ref="table", output_field="citations"),
                    dict(component_ref="text", output_field="semantic_status"),
                ]
                raw["choices"][0]["message"]["content"] = json.dumps(value, ensure_ascii=False)

        generation, generated, sent = literal.generate(data, mutation=compose)
        save("mock-generation-requests.json", sent)
        assert len(sent) == 2
        aid, _ = literal.confirm(data, generation, generated)
        release, instance = literal.release_instance(data, aid)
        empty = client.post(f"/api/internal/releases/{release['id']}/instances", json={
            "expected_release_fingerprint": release["fingerprint"], "request_key": "empty-view-instance",
        })
        assert empty.status_code == 201, empty.text
        runs = []
        terms = ["Alpha", "Beta", "NoMatch"]
        for index, term in enumerate(terms):
            accepted = client.post(f"/api/internal/instances/{instance['id']}/runs", json={
                "expected_revision": instance["revision"],
                "expected_release_fingerprint": release["fingerprint"],
                "input": {"term": term}, "request_key": f"view-composition-{index}",
            })
            assert accepted.status_code == 202, accepted.text
            rid = accepted.json()["run_id"]
            worker = observed_worker(store, settings, NoModel())
            assert worker.once()
            result = client.get(f"/api/internal/instances/{instance['id']}/runs/{rid}")
            assert result.status_code == 200 and result.json()["status"] == "SUCCEEDED", result.text
            assert result.json()["result"]["term"] == term
            runs.append(rid)
        assert [c["run_id"] for c in claims] == [generation, *runs]
        assert len(workers) == 4 and all(w["once_result"] is True for w in workers)
        assert [w["worker_id"] for w in workers] == [c["worker_id"] for c in claims]
        manifest = release["snapshot"]["draft"]["candidate"]["manifest"]
        read = client.get(f"/api/internal/instances/{instance['id']}").json()
        info = dict(app=aid, instance=instance["id"], empty=empty.json()["id"], release=release["id"],
                    runs=runs, terms=terms, manifest=manifest, example=read["data"][0]["data"]["result"],
                    columns=list(manifest["output_schema"]["properties"]["citations"]["items"]["properties"]),
                    output=str(tmp_path / "page-proof.json"))
        save("info.json", info)
        before_page = snapshot(store)
        save("before-page.json", before_page)
        page_http_offset = len(http)
        with (tmp_path / "node.stderr").open("w") as errors:
            process = subprocess.Popen(["node", "tests/manifest_views_ui.cjs", str(tmp_path / "info.json")],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True,
                env={**os.environ, "NODE_PATH": os.environ.get("NODE_PATH", str(Path.cwd() / "scripts/engineering-ci/node_modules"))})
            for line in process.stdout:
                message = json.loads(line)
                if message.get("done"):
                    break
                assert message["method"] == "GET"
                response = client.request(message["method"], message["path"],
                                          headers=message.get("headers"))
                process.stdin.write(json.dumps(dict(id=message["id"], status=response.status_code,
                    text=response.text, content_type=response.headers.get("content-type"))) + "\n")
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=20)
        assert code == 0, (tmp_path / "node.stderr").read_text()
        proof = json.loads((tmp_path / "page-proof.json").read_text())
        assert proof["status"] == "PASS"
        assert snapshot(store) == before_page
        assert len(claims) == len(workers) == 4
        assert all(row["method"] == "GET" for row in http[page_http_offset:])
        for asset in proof["assets"]:
            file = Path("src/sim2act/web") / (asset["path"].lstrip("/") or "index.html")
            assert hashlib.sha256(file.read_bytes()).hexdigest() == asset["sha256"]
        save("measurement.json", dict(status="PASS", tables=len(before_page), all_page_rows_unchanged=True,
            generation_mock_requests=len(sent), runtime_no_model_runs=3, page_worker_calls=0,
            claims=claims, workers=workers, page_requests=len(proof["requests"]),
            checks=len(proof["checks"]), assets=len(proof["assets"]), boots=proof["boots"],
            real_model="NOT_RUN", native_browser="NOT_RUN", windows="NOT_RUN", pg="NOT_RUN", remote_ci="NOT_RUN"))
    finally:
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        save("workers.json", workers)
        save("claims.json", claims)
        save("actual-http.json", http)
        save("after-page-or-failure.json", snapshot(store))
        client.close()
