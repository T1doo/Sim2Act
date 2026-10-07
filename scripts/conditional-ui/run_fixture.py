"""Owned existing protocol fixture: actual Worker, four hand-authored offline replies."""

import json
import sys
from pathlib import Path

from sqlalchemy import select

from sim2act.conditional_runs import candidate_for
from sim2act.config import Settings
from sim2act.db import Store, protocol_jobs, runs
from sim2act.worker import Worker


def work(root, phase):
    # Reuse the canonical test transport, never its gold or a product provider setting.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))
    from test_conditional_run_bindings import envelope, factory, report

    info = json.loads((root / "info.json").read_text())
    store = Store("sqlite:///" + str(root / "fixture.db"), test_only=True)
    settings = Settings("sqlite:///" + str(root / "fixture.db"), root, mode="mock", max_requests=3, max_repairs=0)
    wires = []
    try:
        with store.tx() as c:
            # Match Worker FIFO globally; never reorder or silently consume another job.
            oldest = c.execute(
                select(runs).where(runs.c.status == "QUEUED").order_by(runs.c.created_at, runs.c.id)
            ).mappings().first()
            if not oldest or oldest["project_id"] != info["project"]:
                raise ValueError("Expected current project's oldest queued Run")
            job = c.execute(select(protocol_jobs).where(
                protocol_jobs.c.run_id == oldest["id"]
            )).mappings().one()
        if phase not in {"source", "extract", "cold"} or job["kind"] != phase:
            raise ValueError("Requested phase does not match FIFO queued Run")
        snapshot = job["accepted_snapshot"]
        if phase == "source":
            replies = [envelope(resource=info["source"]), envelope(report())]
        elif phase == "extract":
            replies = [envelope(candidate_for(snapshot["contract"], info["source"]))]
        else:
            replies = [envelope(report(("TRUE", "FALSE", "FALSE"), "ALLOW",
                                       ["submit_claim_and_receipt"]))]
        env = (store, settings)
        if not Worker(store, settings, protocol_runner_factory=factory(
            env, root, replies, wires
        )).once():
            raise RuntimeError("Normal Worker did not execute owned queued Run")
        if replies or len(wires) != (2 if phase == "source" else 1):
            raise RuntimeError("Worker did not consume the exact bounded mock replies")
        return {"kind": "owned-conditional-native-fixture.v1", "action": "run-" + phase,
                "run_id": oldest["id"], "actual_mock_requests": len(wires),
                "real_model_requests": 0, "report_origin": "hand-authored-test-only",
                "cold_scope": "same-resource/new-Scenario"}
    finally:
        store.engine.dispose()
