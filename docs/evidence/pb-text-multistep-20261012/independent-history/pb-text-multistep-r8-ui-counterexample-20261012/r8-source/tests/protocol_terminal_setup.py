"""Existing native old26-equivalent persisted state, not new queued prerequisites."""

import importlib.util
import json

from fastapi.testclient import TestClient
from sqlalchemy import select

from sim2act.api import create_app
from sim2act.db import runs


def prepare(root):
    spec = importlib.util.spec_from_file_location("terminal_protocol_fixture", "scripts/protocol-ui/fixture.py")
    f = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(f)
    info = json.loads((root / "info.json").read_text(encoding="utf-8"))
    store, settings = f.context(root)
    try:
        with TestClient(create_app(store, settings), headers={"Authorization": "Bearer " + info["bearer"]}) as client:
            base = f"/api/projects/{info['project']}/protocol"
            catalog = client.get(base + "/contracts").json()["items"]
            source = next(v for v in catalog if v["contract_id"] == info["source_contract"])

            def post(path, body):
                response = client.post(base + path, json=body)
                if response.status_code not in {200, 202}:
                    raise RuntimeError("Existing protocol setup HTTP failure")
                return response.json()

            body = {"contract_id": source["contract_id"], "goal": source["public_goal"],
                    "inputs": source["public_inputs"], "resource_ids": [info["source"]]}
            made = post("/source", {**body, "request_key": "terminal-source"})
            if f.action(root, "worker", made["run_id"])["requests"] != 2:
                raise RuntimeError("Source Mock request count changed")
            f.action(root, "review", made["run_id"])
            result = client.get(base + "/runs/" + made["run_id"]).json()
            extracted = post("/extract", {"source_run_id": made["run_id"],
                             "expected_source_fingerprint": result["result_fingerprint"],
                             "request_key": "terminal-extract"})
            if f.action(root, "worker", extracted["run_id"])["requests"] != 1:
                raise RuntimeError("Extraction Mock request count changed")
            plan = client.get(base + "/runs/" + extracted["run_id"]).json()["result"]["compiled_plan"]
            cold = next(v for v in catalog if v["contract_id"] == info["cold_contract"])
            made_cold = post("/cold", {"contract_id": cold["contract_id"],
                            "extraction_run_id": extracted["run_id"],
                            "expected_plan_fingerprint": plan["plan_fingerprint"],
                            "inputs": cold["public_inputs"], "resource_bindings": {"material_0": info["cold"]},
                            "request_key": "terminal-cold"})
            if f.action(root, "worker", made_cold["run_id"])["requests"] != 1:
                raise RuntimeError("Cold Mock request count changed")
            default = post("/source", {**body, "request_key": "terminal-default"})
            drained = f.action(root, "default-worker", default["run_id"])
            if drained["requests"] != 0 or drained["drained"] != 1:
                raise RuntimeError("Existing default Worker must naturally drain one last intent")
            waiting = client.get(base + "/runs/" + default["run_id"]).json()
            recovery = post("/runs/" + default["run_id"] + "/recover", {
                "expected_version": waiting["version"], "expected_fence": waiting["fence"],
                "request_key": "terminal-recovery"})
            if recovery["provider_requests"] != 0:
                raise RuntimeError("Metadata recovery cannot dispatch")
            counts = f.action(root, "counts")
            with store.tx() as c:
                states = [dict(r) for r in c.execute(select(runs.c.id, runs.c.status)).mappings()]
            if counts["jobs"] != 5 or counts["attempts"] != 4 or any(r["status"] == "QUEUED" for r in states):
                raise RuntimeError("Exact old native terminal precondition changed")
            (root / "old-terminal-receipt.json").write_text(json.dumps({
                "scope": "old26-equivalent durable state; not browser26 execution", "jobs": 5,
                "actual_mock_attempts": 4, "default": drained, "recovery": recovery,
                "states": states, "queued": 0, "real_model_requests": 0,
            }, indent=2))
    finally:
        store.engine.dispose()
