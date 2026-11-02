"""Exact fragment source freezes through delivered JS and the real API; no worker."""
import hashlib
import json
import os
import subprocess

from sqlalchemy import select

from sim2act.db import attempts, run_contracts, runs


def test_fragment_frozen_source_and_original_key(env, tmp_path):
    store, _, client, _, _, project, _ = env
    assert store.sqlite, "This bounded frontend check requires synthetic SQLite"
    content = "A😀中文原文\r\n保留第二行。"
    resource = client.post(f"/api/projects/{project}/resources", json={
        "name": "合成片段.md", "format": "md", "content": content,
    }).json()["id"]
    output = tmp_path / "result.json"
    info = tmp_path / "info.json"
    info.write_text(json.dumps({"project": project, "resource": resource, "output": str(output)}))
    process = None
    try:
        with (tmp_path / "node.stderr").open("w") as errors:
            process = subprocess.Popen(["node", "tests/frontend_fragment_api.cjs", str(info)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True, env=os.environ)
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                if request.get("command") == "verify":
                    with store.tx() as connection:
                        rows = connection.execute(select(runs)).mappings().all()
                        assert len(rows) == 1 and rows[0]["status"] == "QUEUED"
                        assert rows[0]["request_key"] == request["body"]["request_key"]
                        assert rows[0]["goal"] == request["body"]["goal"]
                        snapshot = connection.execute(select(run_contracts.c.snapshot)).scalar_one()
                        assert snapshot["goal"]["resource_refs"] == [resource]
                        assert snapshot["resources"] == [{"resource_id": resource, "revision": 1,
                            "content_hash": hashlib.sha256(content.encode()).hexdigest(), "format": "md"}]
                        reference = json.loads(rows[0]["goal"].split("本次片段上下文（引用原文，不回写材料）：\n", 1)[1])
                        assert reference == {"resource_id": resource, "content_hash": snapshot["resources"][0]["content_hash"],
                            "range_encoding": "UTF-16", "start": 1, "end": 5, "original_text": "😀中文"}
                        assert "Semantic goal acceptance NOT_RUN" in snapshot["goal"]["unresolved"]
                        assert not connection.execute(select(attempts)).all()
                    answer = {"status": 200, "text": "{}"}
                else:
                    response = client.request(request["method"], request["path"],
                        json=request.get("body"), headers=request.get("headers"))
                    answer = {"status": response.status_code, "text": response.text,
                        "content_type": response.headers.get("content-type")}
                process.stdin.write(json.dumps({"id": request["id"], **answer}) + "\n")
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=20)
        assert code == 0, (tmp_path / "node.stderr").read_text()
        assert json.loads(output.read_text())["status"] == "PASS"
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
