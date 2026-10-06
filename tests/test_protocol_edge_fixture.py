"""Prepared protected Edge fixture really uses the new offline gates; no native claim."""

import importlib.util
import json
from pathlib import Path

from fastapi.testclient import TestClient
from protocol_socket_oracle import forbid_external_network
from sqlalchemy import select

from sim2act.api import create_app
from sim2act.db import events


def test_edge_fixture_gated_actual_http_and_metadata_recovery(tmp_path, monkeypatch):
    forbid_external_network(monkeypatch, "Protected Edge fixture controller attempted external connection")
    spec = importlib.util.spec_from_file_location(
        "protocol_native_fixture", Path(__file__).parents[1] / "scripts/protocol-ui/fixture.py"
    )
    assert spec and spec.loader
    f = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(f)
    root = tmp_path
    f.seed(root, 9019)
    info = json.loads((root / "info.json").read_text())
    store, settings = f.context(root)
    with TestClient(
        create_app(store, settings), headers={"Authorization": "Bearer " + info["bearer"]}
    ) as client:
        url = f"/api/projects/{info['project']}/protocol"
        public = next(
            c
            for c in client.get(url + "/contracts").json()["items"]
            if c["contract_id"] == info["source_contract"]
        )
        response = client.post(
            url + "/source",
            json={
                "contract_id": info["source_contract"],
                "goal": public["public_goal"],
                "inputs": public["public_inputs"],
                "resource_ids": [info["source"]],
                "request_key": "smoke-source",
            },
        )
        assert response.status_code == 202, response.text
        source = response.json()["run_id"]
        first = f.action(root, "worker", source)
        assert first["requests"] == 2 and first["guarded_actual_header_body"]
        pending = client.get(url + "/runs/" + source).json()
        assert (
            pending["status"] == "WAITING_APPROVAL"
            and pending["owner_semantic_acceptance"] == "PENDING"
        )
        reviewed = f.action(root, "review", source)
        assert reviewed["decision"] == "PASS" and reviewed["experiment"]["accepted_stages"] == 1
        accepted = client.get(url + "/runs/" + source).json()
        response = client.post(
            url + "/extract",
            json={
                "source_run_id": source,
                "expected_source_fingerprint": accepted["result_fingerprint"],
                "request_key": "smoke-extract",
            },
        )
        assert response.status_code == 202, response.text
        extracted = response.json()["run_id"]
        second = f.action(root, "worker", extracted)
        assert second["requests"] == 1 and second["experiment"]["accepted_stages"] == 2
        plan = client.get(url + "/runs/" + extracted).json()["result"]["compiled_plan"]
        assert set(plan["candidate"]["resources"]) == {"material_0"}
        public = next(
            c
            for c in client.get(url + "/contracts").json()["items"]
            if c["contract_id"] == info["cold_contract"]
        )
        response = client.post(
            url + "/cold",
            json={
                "extraction_run_id": extracted,
                "expected_plan_fingerprint": plan["plan_fingerprint"],
                "contract_id": info["cold_contract"],
                "inputs": public["public_inputs"],
                "resource_bindings": {"material_0": info["cold"]},
                "request_key": "smoke-cold",
            },
        )
        assert response.status_code == 202, response.text
        cold = response.json()["run_id"]
        third = f.action(root, "worker", cold)
        assert third["requests"] == 1 and third["guarded_actual_header_body"]
        pending = client.get(url + "/runs/" + cold).json()
        assert (
            pending["status"] == "WAITING_APPROVAL"
            and pending["semantic_status"] == "UNKNOWN"
            and pending["owner_semantic_acceptance"] == "PENDING"
        )
        summary = f.action(root, "counts")
        assert (
            summary["attempts"] == 4
            and summary["experiment"]["bound_stages"] == 3
            and summary["experiment"]["accepted_stages"] == 2
            and summary["experiment"]["requests"] == summary["experiment"]["settled"] == 4
            and summary["experiment"]["status"] == "ACTIVE"
        )
        assert (
            summary["grant_fingerprint"] == info["initial_counts"]["grant_fingerprint"]
            and summary["principal_fingerprint"] == info["initial_counts"]["principal_fingerprint"]
        )
        # Unbound default UI intent after pending cold must never adopt experiment/legacy fallback.
        public = next(
            c
            for c in client.get(url + "/contracts").json()["items"]
            if c["contract_id"] == info["source_contract"]
        )
        for index in range(3):
            race = client.post(
                url + "/source",
                json={
                    "contract_id": info["source_contract"],
                    "goal": public["public_goal"],
                    "inputs": public["public_inputs"],
                    "resource_ids": [info["source"]],
                    "request_key": f"prior-native-race-{index}",
                },
            )
            assert race.status_code == 202
        made = client.post(
            url + "/source",
            json={
                "contract_id": info["source_contract"],
                "goal": public["public_goal"],
                "inputs": public["public_inputs"],
                "resource_ids": [info["source"]],
                "request_key": "smoke-default",
            },
        ).json()
        default = f.action(root, "default-worker", made["run_id"])
        assert default["requests"] == 0 and default["drained"] == 4
        assert len(default["drained_runs"]) == 4
        waiting = client.get(url + "/runs/" + made["run_id"]).json()
        assert waiting["status"] == "WAITING_RESOURCE"
        with store.tx() as c:
            default_events = list(
                c.execute(select(events.c.kind).where(events.c.run_id == made["run_id"])).scalars()
            )
        assert (
            "PROTOCOL_EXPERIMENT_BINDING" not in default_events
            and "PROTOCOL_OFFLINE_HANDOFF" not in default_events
        )
        recovered = client.post(
            url + "/runs/" + made["run_id"] + "/recover",
            json={
                "expected_version": waiting["version"],
                "expected_fence": waiting["fence"],
                "request_key": "smoke-default-recover",
            },
        )
        assert recovered.status_code == 200 and recovered.json()["provider_requests"] == 0
        again = f.action(root, "counts")
        assert again["attempts"] == 4 and again["experiment"] == summary["experiment"]
    store.engine.dispose()
