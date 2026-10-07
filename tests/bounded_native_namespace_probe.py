"""Actual original protocol/source must never be consumed by bounded native fixture."""

import importlib.util
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from sim2act.api import create_app
from sim2act.db import runs


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    root = Path(sys.argv[1])
    protocol = load("existing_protocol_native", "scripts/protocol-ui/fixture.py")
    sys.path.insert(0, str(Path("scripts/conditional-ui").resolve()))
    control = load("bounded_native_control", "scripts/conditional-ui/fixture.py")
    protocol.seed(root, 12345)
    info = json.loads((root / "info.json").read_text())
    store, settings = protocol.context(root)
    try:
        with TestClient(create_app(store, settings), headers={
            "Authorization": "Bearer " + info["bearer"]
        }) as client:
            contract = next(v for v in client.get(
                f"/api/projects/{info['project']}/protocol/contracts"
            ).json()["items"] if v["contract_id"] == info["source_contract"])
            reply = client.post(f"/api/projects/{info['project']}/protocol/source", json={
                "contract_id": contract["contract_id"], "goal": contract["public_goal"],
                "inputs": contract["public_inputs"], "resource_ids": [info["source"]],
                "request_key": "actual-original-namespace-negative",
            })
            if reply.status_code != 202:
                raise RuntimeError("Original protocol HTTP enqueue failed: " + reply.text)
            rid = reply.json()["run_id"]
            before = control.action(root, "snapshot")
            try:
                control.action(root, "run-source")
            except Exception as error:
                refused = {"type": type(error).__name__, "message": str(error)}
            else:
                raise RuntimeError("Non-bounded original namespace was executed")
            after = control.action(root, "snapshot")
            with store.tx() as c:
                status = c.execute(select(runs.c.status).where(runs.c.id == rid)).scalar_one()
            if before != after or status != "QUEUED":
                raise RuntimeError("Refusal mutated persistent records or Run status")
            (root / "namespace-refusal.json").write_text(json.dumps({
                "status": "PASS", "optimized": sys.flags.optimize,
                "created_http": reply.status_code, "run_status": status, "refused": refused,
                "before": before, "after": after, "all_tables_unchanged": True,
                "attempts_delta": after["attempts_count"] - before["attempts_count"],
            }, indent=2))
    finally:
        store.engine.dispose()


if __name__ == "__main__":
    main()
