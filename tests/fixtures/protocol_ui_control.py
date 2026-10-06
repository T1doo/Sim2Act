"""Explicit local test controller; no production endpoint or provider network."""

import json
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_protocol_http import envelope, factory  # noqa: E402

from sim2act.config import Settings  # noqa: E402
from sim2act.db import Store, protocol_jobs, runs  # noqa: E402
from sim2act.model_protocol import obj  # noqa: E402
from sim2act.protocol_reviews import contract_snapshot, evaluation_contract, review  # noqa: E402
from sim2act.worker import Worker  # noqa: E402

root, action = Path(sys.argv[1]), sys.argv[2]
info = json.loads((root / "info.json").read_text())
store = Store(info["database"], test_only=True)
settings = Settings(info["database"], root, max_requests=3, max_repairs=0)
source, _ = evaluation_contract("protocol.synthetic.a-source.v1")


def candidate():
    schema = contract_snapshot(source["id"])["output_schema"]
    return {
        "schema_version": "model-protocol.v1",
        "input_schema": obj({"format": {"type": "string"}}),
        "resources": {"material": info["source"]},
        "steps": [
            {
                "id": "read",
                "kind": "registered_tool",
                "depends_on": [],
                "inputs": {
                    "resource_id": {"source": "data", "ref": "material", "field": "resource_id"}
                },
                "tool_ref": "resource.read",
            },
            {
                "id": "interpret",
                "kind": "language",
                "depends_on": ["read"],
                "inputs": {
                    "content": {"source": "step", "ref": "read", "field": "content"},
                    "format": {"source": "input", "ref": "input", "field": "format"},
                },
                "instruction": source["public_goal"],
                "output_schema": schema,
            },
        ],
        "output_schema": schema,
        "outputs": {
            key: {"source": "step", "ref": "interpret", "field": key}
            for key in schema["properties"]
        },
    }


try:
    with store.tx() as c:
        run = (
            c.execute(
                select(runs)
                .where(runs.c.project_id == info["project"])
                .order_by(runs.c.created_at.desc())
            )
            .mappings()
            .first()
        )
        job = (
            c.execute(select(protocol_jobs).where(protocol_jobs.c.run_id == run["id"]))
            .mappings()
            .one()
        )
    if action == "review":
        result = review(
            store,
            info["user"],
            run["id"],
            {
                "contract_id": job["accepted_snapshot"]["payload"]["contract_id"],
                "expected_result_fingerprint": job["result_fingerprint"],
                "expected_fence": run["fence"],
                "expected_version": run["version"],
                "request_key": "explicit-test-review-" + run["id"],
            },
        )
        print(json.dumps({"decision": result["decision"]}))
    elif action == "default-worker":
        assert Worker(store, settings).once()
        print(json.dumps({"requests": 0}))
    elif action == "worker":
        phase = job["kind"]
        cold, _ = evaluation_contract("protocol.synthetic.a-cold.v1")
        replies = {
            "source": [envelope(resource=info["source"]), envelope(source["expected_output"])],
            "extract": [envelope(candidate())],
            "cold": [envelope(cold["expected_output"])],
        }[phase]
        env = (
            store,
            settings,
            None,
            info["user"],
            info["other_user"],
            info["project"],
            info["source"],
        )
        seen = []
        worker = Worker(
            store, settings, protocol_runner_factory=factory(env, root, replies, seen, phase + "_a")
        )
        assert worker.once()
        print(json.dumps({"requests": len(seen), "phase": phase}))
    else:
        raise ValueError("Unknown explicit fixture action")
finally:
    store.engine.dispose()
