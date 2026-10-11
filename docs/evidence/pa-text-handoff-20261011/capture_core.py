"""Reproduce the synthetic non-CSV vertical slice and export its actual ledger.

Run from the repository root:
PYTHONPATH=src:tests .venv/bin/python docs/evidence/pa-text-handoff-20261011/capture_core.py
No environment credentials, external model, CSV fixture, or Replay are used.
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

import test_goal_text_applications as helper
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, meta


def main():
    artifact = Path(__file__).with_name("core-trace.json")
    with tempfile.TemporaryDirectory(prefix="pa-text-core-") as directory:
        temporary = Path(directory)
        settings = Settings("sqlite:///" + str(temporary / "core.db"), temporary, mode="mock")
        store = Store(settings.database_url, test_only=True)
        store.initialize()
        user = store.user("fixture A", "synthetic-test-A")
        with TestClient(create_app(store, settings)) as client:
            client.headers.update({"Authorization": "Bearer synthetic-test-A"})
            project = client.post("/api/projects", json={"name": "Non-CSV P-A core"})
            assert project.status_code == 201, project.text
            pid = project.json()["id"]
            data = helper.setup((store, settings, client, user, None, pid, None))
            active = data[2]
            run_id, ready, sent = helper.generate(data, repair=True)
            assert ready["status"] == "PARTIAL" and len(sent) == 3
            app_id, confirmation = helper.confirm(data, run_id, ready)
            preview = active.post(
                f"/api/apps/{app_id}/previews",
                json={"input": {"term": "Alpha"}, "request_key": "trace-preview"},
            )
            assert preview.status_code == 200, preview.text
            release, instance = helper.release_instance(data, app_id)
            initial = active.get(f"/api/internal/instances/{instance['id']}").json()
            assert initial["data"] == []
            cold = Store(settings.database_url, test_only=True)
            cold_data = (cold, *data[1:])
            outputs = []
            for term in ["Beta", "beta", "Alpha"]:
                result = helper.run_input(
                    cold_data, release, instance, {"term": term}, "trace-cold-" + term
                )
                assert result["status"] == "SUCCEEDED", result
                outputs.append(result)
            assert outputs[0]["result"]["citations"] == [
                {"start_line": 2, "end_line": 2, "quote": "Beta due tomorrow"},
                {"start_line": 4, "end_line": 4, "quote": "<em>Beta literal</em>"},
            ]
            assert outputs[1]["result"]["citations"] == []
            assert outputs[2]["result"] != outputs[0]["result"]
            failures = []
            invalid = [
                {},
                {"term": 3},
                {"term": ""},
                {"term": " Alpha"},
                {"term": "a" * 81},
                {"term": "Beta", "resource_id": data[5]},
            ]
            for index, value in enumerate(invalid):
                result = helper.run_input(
                    cold_data, release, instance, value, "trace-invalid-" + str(index)
                )
                assert result["status"] == "FAILED" and result["result"] is None
                failures.append(result)
            final = active.get(f"/api/internal/instances/{instance['id']}").json()
            assert len(final["data"]) == 3
            names = [
                "projects", "resources", "grants", "goal_cards", "goal_card_versions",
                "runs", "run_contracts", "attempts", "events", "operations",
                "operation_intents", "goal_application_candidates", "app_drafts",
                "app_previews", "internal_approvals", "internal_releases",
                "internal_instances", "internal_app_runs", "internal_instance_data",
                "internal_run_bindings",
            ]
            with store.tx() as connection:
                ledger = {
                    name: [dict(row) for row in connection.execute(select(meta.tables[name])).mappings()]
                    for name in names
                }
            assert len(ledger["resources"]) == 1 and ledger["resources"][0]["format"] == "md"
            assert len(ledger["attempts"]) == 3
            assert all(row["mode"] == "MOCK" for row in ledger["attempts"])
            assert ledger["attempts"][1]["error"] == "INVALID_MANIFEST"
            assert len(ledger["app_drafts"]) == 1
            runtime = ledger["app_drafts"][0]["runtime_id"]
            app_grants = [row for row in ledger["grants"] if row["principal_id"] == runtime]
            assert len(app_grants) == 1 and app_grants[0]["tool_ref"] == "resource.read"
            assert len(ledger["internal_instance_data"]) == 3
            record = {
                "status": "PASS",
                "utc": datetime.now(timezone.utc).isoformat(),
                "scope": {
                    "database": "SQLite test_only",
                    "provider": "Intern httpx.MockTransport synthetic fixture",
                    "live_calls": 0,
                    "csv_resources": 0,
                    "candidate_template": "test fixture only; no production template",
                    "app_execution": "cold Store + actual Worker, no model or Replay",
                    "semantic_acceptance": "NOT_RUN",
                },
                "goal_card": data[6],
                "generation_run": ready,
                "actual_provider_request_wires": sent,
                "confirmation_input": confirmation,
                "preview": preview.json(),
                "release": release,
                "initial_empty_instance": initial,
                "cold_unseen_and_changed_inputs": outputs,
                "invalid_inputs": failures,
                "final_instance": final,
                "ledger": ledger,
            }
            artifact.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
            print(json.dumps({
                "artifact": str(artifact), "status": "PASS", "model_mock_requests": 3,
                "csv_resources": 0, "cold_successes": 3, "invalid_failed_history": 6,
                "typed_result_rows": 3, "live_calls": 0,
            }))
            cold.engine.dispose()
            active.close()
        store.engine.dispose()


if __name__ == "__main__":
    main()
