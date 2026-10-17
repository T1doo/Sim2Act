"""Prospective finite CSV report contract; synthetic SQLite and NoModel only."""
import json
from pathlib import Path

from sqlalchemy import select

from sim2act.db import Store, attempts, operations, reservations, resources, runs
from sim2act.worker import Worker


class NoModel:
    def request(self, *args, **kwargs):
        raise AssertionError("This task must never call a model")


def prepare(client, project, material, key="prepare", column="amount"):
    return client.post(f"/api/projects/{project}/csv-report-runs", json={
        "resource_id": material, "column": column, "request_key": key})


def test_prospective_csv_report(env, tmp_path):
    store, settings, client, owner, _, project, material = env
    response = prepare(client, project, material)
    assert response.status_code == 202, response.text
    rid = response.json()["run_id"]
    before = client.get(f"/api/runs/{rid}").json()
    assert before["status"] == "WAITING_APPROVAL"
    assert not Worker(store, settings, NoModel()).once()
    with store.tx() as c:
        assert not c.execute(select(operations)).first()
        assert not c.execute(select(attempts)).first()
        assert not c.execute(select(reservations)).first()
        assert len(c.execute(select(resources)).all()) == 1
    confirm = {"version": before["version"], "contract_fingerprint": before["contract"]["fingerprint"],
               "request_key": "confirm"}
    reply = client.post(f"/api/runs/{rid}/confirm-csv-report", json=confirm)
    assert reply.status_code == 200, reply.text
    assert client.post(f"/api/runs/{rid}/confirm-csv-report", json=confirm).json() == reply.json()
    cold = Store(settings.database_url, test_only=True)
    try:
        assert Worker(cold, settings, NoModel()).once()
        assert not Worker(cold, settings, NoModel()).once()
    finally:
        cold.engine.dispose()
    actual = client.get(f"/api/runs/{rid}")
    assert actual.status_code == 200, actual.text
    actual = actual.json()
    assert actual["status"] == "SUCCEEDED"
    assert actual["result"]["goal_acceptance"] == "PASS_CSV_REPORT_CONTRACT"
    assert actual["result"]["task_acceptance"]["general_semantic_acceptance"] == "NOT_RUN"
    assert actual["result"]["task_acceptance"]["owner_acceptance"] == "PENDING"
    saved = actual["result"]["receipts"][-1]["data"]
    artifact = client.get(f"/api/resources/{saved['resource_id']}").json()
    spec = before["contract"]["snapshot"]["ordinary_csv_report"]
    assert artifact["content"] == spec["report_text"]
    assert artifact["hash"] == spec["report_hash"] and artifact["format"] == "md"
    with store.tx() as c:
        assert len(c.execute(select(operations)).all()) == 3
        assert not c.execute(select(attempts)).first() and not c.execute(select(reservations)).first()
        assert len(c.execute(select(resources)).all()) == 2
    (tmp_path / "actual-run.json").write_text(json.dumps(actual, ensure_ascii=False, indent=2))
    (tmp_path / "saved-report.md").write_bytes(artifact["content"].encode())
