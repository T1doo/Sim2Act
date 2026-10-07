"""Actual global-pool seal rejects an unbound new Report Run in either project."""

import importlib.util
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from test_conditional_run_bindings import envelope, factory, report

from sim2act.api import create_app
from sim2act.db import (
    attempts,
    events,
    fingerprint,
    protocol_request_pools,
    protocol_request_slots,
    runs,
)
from sim2act.protocol_jobs import verified_pending
from sim2act.worker import Worker


def main():
    root, scope = Path(sys.argv[1]), sys.argv[2]
    spec = importlib.util.spec_from_file_location("original_protocol_fixture", "scripts/protocol-ui/fixture.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    info = json.loads((root / "info.json").read_text(encoding="utf-8"))
    store, settings = fixture.context(root)
    try:
        pid, source = info["project"], info["source"]
        if scope == "other":
            with store.tx() as c:
                _, existing = verified_pending(store, c, info["user"], info["other_run"])
                pid, source = existing["project_id"], existing["resource_refs"][0]

        def seals():
            with store.tx() as c:
                return {table.name: fingerprint([dict(row) for row in c.execute(select(table)).mappings()])
                        for table in [protocol_request_pools, protocol_request_slots, attempts]}

        before = seals()
        with TestClient(create_app(store, settings), headers={"Authorization": "Bearer " + info["bearer"]}) as client:
            base = f"/api/projects/{pid}/conditional-runs"
            contract = client.get(base + "/contract").json()
            reply = client.post(base + "/source", json={"resource_id": source,
                "expected_source_hash": contract["source_hash"], "expected_contract_fingerprint": contract["check_contract_fingerprint"],
                "goal": contract["goal"], "request_key": "global-seal-negative",
                "scenario": {"kind": "HYPOTHETICAL_EMPLOYEE", "trip_ended": True, "amount": 680,
                             "receipt_present": True, "approved": False, "elapsed_days": 2}})
            if reply.status_code != 202:
                raise RuntimeError("Bounded Run actual enqueue failed")
            rid = reply.json()["run_id"]
        wires, replies = [], [envelope(resource=source), envelope(report())]
        if not Worker(store, settings, protocol_runner_factory=factory((store, settings), root, replies, wires)).once():
            raise RuntimeError("Actual normal Worker did not claim queued Run")
        with store.tx() as c:
            current = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
            trace = [dict(r) for r in c.execute(select(events).where(events.c.run_id == rid)).mappings()]
        after = seals()
        if (current["status"] != "WAITING_RESOURCE" or current["error"]["code"] != "RESOURCE_UNAVAILABLE"
            or wires or len(replies) != 2 or before != after):
            raise RuntimeError("Global experiment gate did not reject before model/slot allocation")
        (root / "global-gate-receipt.json").write_text(json.dumps({"status": "PASS", "scope": scope,
            "optimized": sys.flags.optimize, "run_status": current["status"], "error": current["error"],
            "actual_new_mock_requests": 0, "before": before, "after": after,
            "pool_slots_attempts_unchanged": True, "events": trace}, indent=2))
    finally:
        store.engine.dispose()


if __name__ == "__main__":
    main()
