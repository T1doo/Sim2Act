"""Prospective finite CSV report contract; synthetic SQLite and NoModel only."""

import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import select, update
from test_literal_directory import rows

from sim2act.db import (
    Store,
    attempts,
    fingerprint,
    grants,
    operations,
    reservations,
    resources,
    run_contracts,
    runs,
)
from sim2act.worker import Worker


class NoModel:
    def request(self, *args, **kwargs):
        raise AssertionError("This task must never call a model")


def prepare(client, project, material, key="prepare", column="amount"):
    return client.post(
        f"/api/projects/{project}/csv-report-runs",
        json={"resource_id": material, "column": column, "request_key": key},
    )


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
    confirm = {
        "version": before["version"],
        "contract_fingerprint": before["contract"]["fingerprint"],
        "request_key": "confirm",
    }
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
        assert (
            not c.execute(select(attempts)).first() and not c.execute(select(reservations)).first()
        )
        assert len(c.execute(select(resources)).all()) == 2
    (tmp_path / "actual-run.json").write_text(json.dumps(actual, ensure_ascii=False, indent=2))
    (tmp_path / "saved-report.md").write_bytes(artifact["content"].encode())


@pytest.mark.parametrize(
    "content,column,expected,count",
    [
        ("名字,总价😀\n甲,9007199254740993.01\n乙,-0.02\n", "总价😀", "9007199254740992.99", 2),
        ("value\n1e30\n-1e30\n0.000000000000000000000000000001\n", "value", "1E-30", 3),
        ("empty\n", "empty", "0", 0),
    ],
)
def test_distinct_exact_contract_inputs(env, tmp_path, content, column, expected, count):
    store, settings, client, _, _, project, _ = env
    material = client.post(
        f"/api/projects/{project}/resources",
        json={"name": "unseen.csv", "format": "csv", "content": content},
    ).json()["id"]
    response = prepare(client, project, material, column=column)
    assert response.status_code == 202, response.text
    rid = response.json()["run_id"]
    result = client.get(f"/api/runs/{rid}").json()
    spec = result["contract"]["snapshot"]["ordinary_csv_report"]
    from decimal import Decimal

    assert Decimal(spec["sum"]) == Decimal(expected) and spec["count"] == count
    assert spec["source_hash"] == hashlib.sha256(content.encode()).hexdigest()
    assert (
        client.post(
            f"/api/runs/{rid}/confirm-csv-report",
            json={
                "version": result["version"],
                "contract_fingerprint": result["contract"]["fingerprint"],
                "request_key": "yes",
            },
        ).status_code
        == 200
    )
    assert Worker(store, settings, NoModel()).once()
    actual = client.get(f"/api/runs/{rid}")
    assert actual.status_code == 200, actual.text
    assert actual.json()["status"] == "SUCCEEDED"
    (tmp_path / "actual-run.json").write_text(
        json.dumps(actual.json(), ensure_ascii=False, indent=2)
    )


@pytest.mark.parametrize(
    "change",
    ["version", "fingerprint", "source", "revoke-save", "cancel", "other-user", "deadline"],
)
def test_confirm_refuses_changed_scope_before_effects(env, tmp_path, change):
    store, settings, client, owner, _, project, material = env
    prepared = prepare(client, project, material).json()
    rid = prepared["run_id"]
    result = client.get(f"/api/runs/{rid}").json()
    body = dict(
        version=result["version"],
        contract_fingerprint=result["contract"]["fingerprint"],
        request_key="yes",
    )
    if change == "version":
        body["version"] += 1
    elif change == "fingerprint":
        body["contract_fingerprint"] = "a" * 64
    elif change == "source":
        # Explicit synthetic persisted-source corruption, not a supported material-edit API.
        with store.tx() as c:
            c.execute(
                update(resources)
                .where(resources.c.id == material)
                .values(content="amount\n99\n", hash=hashlib.sha256(b"amount\n99\n").hexdigest())
            )
    elif change == "revoke-save":
        with store.tx() as c:
            grant = (
                c.execute(
                    select(grants).where(
                        grants.c.principal_id == owner,
                        grants.c.resource_id == project,
                        grants.c.tool_ref == "artifact.save_text",
                    )
                )
                .mappings()
                .one()
            )
        assert (
            client.post(
                f"/api/grants/{grant['id']}/revoke",
                json={"command": "revoke", "version": grant["revision"]},
            ).status_code
            == 200
        )
    elif change == "cancel":
        assert (
            client.post(
                f"/api/runs/{rid}/commands",
                json={"command": "cancel", "version": result["version"]},
            ).status_code
            == 200
        )
    elif change == "deadline":
        from unittest.mock import patch

        with patch(
            "sim2act.ordinary_csv.time.time", return_value=result["ordinary_csv"]["deadline"] + 1
        ):
            reply = client.post(f"/api/runs/{rid}/confirm-csv-report", json=body)
        assert reply.status_code in {400, 409}, reply.text
    initial = rows(store)
    if change != "deadline":
        reply = client.post(
            f"/api/runs/{rid}/confirm-csv-report",
            json=body,
            headers={"Authorization": "Bearer synthetic-test-B"} if change == "other-user" else {},
        )
        assert reply.status_code in {403, 409}, reply.text
    assert rows(store) == initial
    assert not Worker(store, settings, NoModel()).once()
    with store.tx() as c:
        assert not c.execute(select(operations)).first()
        assert (
            not c.execute(select(attempts)).first() and not c.execute(select(reservations)).first()
        )
    (tmp_path / "rejection.json").write_text(reply.text)


@pytest.mark.parametrize("kind", ["arithmetic-receipt", "saved-bytes", "removed-contract"])
def test_cold_checker_refuses_tampering_without_rewrite(env, tmp_path, kind):
    store, settings, client, _, _, project, material = env
    rid = prepare(client, project, material).json()["run_id"]
    prepared = client.get(f"/api/runs/{rid}").json()
    assert (
        client.post(
            f"/api/runs/{rid}/confirm-csv-report",
            json={
                "version": 1,
                "contract_fingerprint": prepared["contract"]["fingerprint"],
                "request_key": "yes",
            },
        ).status_code
        == 200
    )
    assert Worker(store, settings, NoModel()).once()
    actual = client.get(f"/api/runs/{rid}").json()
    assert actual["status"] == "SUCCEEDED"
    with store.tx() as c:
        if kind == "arithmetic-receipt":
            op = (
                c.execute(
                    select(operations).where(
                        operations.c.run_id == rid, operations.c.tool_ref == "data.aggregate_csv"
                    )
                )
                .mappings()
                .one()
            )
            receipt = json.loads(json.dumps(op["receipt"]))
            receipt["data"]["sum"] = "400"
            c.execute(update(operations).where(operations.c.id == op["id"]).values(receipt=receipt))
        elif kind == "saved-bytes":
            artifact = actual["result"]["receipts"][-1]["data"]["resource_id"]
            c.execute(
                update(resources)
                .where(resources.c.id == artifact)
                .values(content="truncated", hash=hashlib.sha256(b"truncated").hexdigest())
            )
        else:
            saved = dict(prepared["contract"]["snapshot"])
            saved.pop("ordinary_csv_report")
            saved["goal"]["acceptance_version"] = "F1-tool-chain.v1"
            c.execute(
                update(run_contracts)
                .where(run_contracts.c.run_id == rid)
                .values(snapshot=saved, fingerprint=fingerprint(saved))
            )
    before = rows(store)
    reply = client.get(f"/api/runs/{rid}")
    assert reply.status_code in {400, 409}, reply.text
    assert rows(store) == before
    assert not Worker(store, settings, NoModel()).once()
    assert (
        rows(store)["operations"] == before["operations"]
        and rows(store)["resources"] == before["resources"]
    )
    (tmp_path / "rejection.json").write_text(reply.text)


@pytest.mark.parametrize(
    "column,value",
    [("量" * 5400, "1"), ("x" * 7900, "1"), ("value", "1e1001")],
    ids=["json-32768-bytes", "text-8000-chars", "oracle-exponent"],
)
def test_rejects_original_save_or_oracle_bounds_before_run(env, column, value):
    store, _, client, _, _, project, _ = env
    material = client.post(
        f"/api/projects/{project}/resources",
        json={"name": "bounds.csv", "format": "csv", "content": f"{column}\n{value}\n"},
    ).json()["id"]
    before = rows(store)
    reply = prepare(client, project, material, column=column)
    assert reply.status_code == 400, reply.text
    assert rows(store) == before


def test_current_worker_budget_tightening_stops_before_tools(env, tmp_path):
    from dataclasses import replace

    store, settings, client, _, _, project, material = env
    rid = prepare(client, project, material).json()["run_id"]
    prepared = client.get(f"/api/runs/{rid}").json()
    assert (
        client.post(
            f"/api/runs/{rid}/confirm-csv-report",
            json={
                "version": 1,
                "contract_fingerprint": prepared["contract"]["fingerprint"],
                "request_key": "yes",
            },
        ).status_code
        == 200
    )
    assert Worker(store, replace(settings, max_tools=2), NoModel()).once()
    actual = client.get(f"/api/runs/{rid}").json()
    assert actual["status"] == "FAILED" and actual["error"]["code"] == "BUDGET_EXHAUSTED"
    with store.tx() as c:
        assert not c.execute(select(operations)).first() and not c.execute(select(attempts)).first()
        assert (
            not c.execute(select(reservations)).first()
            and len(c.execute(select(resources)).all()) == 1
        )
    (tmp_path / "actual-run.json").write_text(json.dumps(actual, ensure_ascii=False, indent=2))


@pytest.mark.parametrize("case", ["deliver", "lost", "navigation"])
def test_visible_prospective_csv_report(env, tmp_path, case):
    import os
    import subprocess
    import threading

    store, settings, client, owner, _, project, material = env
    other = store.project(owner, "Other owned project")
    info = dict(
        case=case,
        project=project,
        other=other,
        material=material,
        output=str(tmp_path / "result.json"),
    )
    (tmp_path / "info.json").write_text(json.dumps(info))
    process = None
    watchdog = None
    proof = {}
    worker_runs = 0
    try:
        with (tmp_path / "node.stderr").open("w") as errors:
            process = subprocess.Popen(
                ["node", "tests/ordinary_csv_report.cjs", str(tmp_path / "info.json")],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=errors,
                text=True,
                env={
                    **os.environ,
                    "NODE_PATH": str(Path.cwd() / "scripts/engineering-ci/node_modules"),
                },
            )
            watchdog = threading.Timer(60, process.kill)
            watchdog.start()
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                command = request.get("command")
                if command == "before":
                    actual = client.get(f"/api/runs/{request['run']}").json()
                    assert actual["status"] == "WAITING_APPROVAL"
                    assert not Worker(store, settings, NoModel()).once()
                    with store.tx() as c:
                        assert (
                            not c.execute(select(operations)).first()
                            and len(c.execute(select(resources)).all()) == 1
                        )
                    proof["before"] = actual
                    answer = dict(status=200, text="{}")
                elif command == "worker":
                    cold = Store(settings.database_url, test_only=True)
                    try:
                        assert Worker(cold, settings, NoModel()).once()
                    finally:
                        cold.engine.dispose()
                    worker_runs += 1
                    actual = client.get(f"/api/runs/{request['run']}").json()
                    assert actual["status"] == "SUCCEEDED"
                    artifact = client.get(
                        f"/api/resources/{actual['result']['receipts'][-1]['data']['resource_id']}"
                    ).json()
                    proof["actual"] = actual
                    proof["artifact"] = artifact
                    answer = dict(status=200, text=json.dumps(dict(run=actual, artifact=artifact)))
                elif command == "after":
                    with store.tx() as c:
                        assert len(c.execute(select(operations)).all()) == 3
                        assert (
                            len(c.execute(select(runs)).all()) == 1
                            and len(c.execute(select(resources)).all()) == 2
                        )
                        assert (
                            not c.execute(select(attempts)).first()
                            and not c.execute(select(reservations)).first()
                        )
                    assert not Worker(store, settings, NoModel()).once()
                    assert worker_runs == 1
                    answer = dict(status=200, text="{}")
                else:
                    response = client.request(
                        request["method"],
                        request["path"],
                        json=request.get("body"),
                        headers=request.get("headers"),
                    )
                    answer = dict(
                        status=response.status_code,
                        text=response.text,
                        content_type=response.headers.get("content-type"),
                    )
                process.stdin.write(json.dumps({"id": request["id"], **answer}) + "\n")
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=20)
        assert code == 0, (tmp_path / "node.stderr").read_text()
        result = json.loads((tmp_path / "result.json").read_text())
        assert result["status"] == "PASS"
        for asset in result["assets"]:
            file = Path("src/sim2act/web") / (asset["path"].lstrip("/") or "index.html")
            assert hashlib.sha256(file.read_bytes()).hexdigest() == asset["sha256"]
    finally:
        if watchdog is not None:
            watchdog.cancel()
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        (tmp_path / "database-proof.json").write_text(
            json.dumps(
                dict(
                    case=case,
                    worker_runs=worker_runs,
                    model_requests=0,
                    real_model_requests=0,
                    proof=proof,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )


def test_no_model_reservation_or_retroactive_confirmation(env):
    from sim2act.errors import DomainError

    store, settings, client, _, _, project, material = env
    old = client.post(
        f"/api/projects/{project}/runs",
        json={
            "goal": "汇总并保存报告，但未选择结构化合同",
            "resource_refs": [material],
            "request_key": "ordinary-old",
        },
    ).json()["run_id"]
    view = client.get(f"/api/runs/{old}").json()
    before = rows(store)
    denied = client.post(
        f"/api/runs/{old}/confirm-csv-report",
        json={
            "version": view["version"],
            "contract_fingerprint": view["contract"]["fingerprint"],
            "request_key": "no-retrofit",
        },
    )
    assert denied.status_code == 400 and rows(store) == before
    assert (
        client.post(
            f"/api/runs/{old}/commands", json={"command": "cancel", "version": view["version"]}
        ).status_code
        == 200
    )
    rid = prepare(client, project, material).json()["run_id"]
    view = client.get(f"/api/runs/{rid}").json()
    assert (
        client.post(
            f"/api/runs/{rid}/confirm-csv-report",
            json={
                "version": 1,
                "contract_fingerprint": view["contract"]["fingerprint"],
                "request_key": "yes",
            },
        ).status_code
        == 200
    )
    worker = Worker(store, settings, NoModel())
    claimed = store.claim(worker.id, settings.lease_seconds)
    assert claimed["id"] == rid
    before = rows(store)
    with pytest.raises(DomainError, match="禁止模型请求"):
        worker.reserve(rid, claimed["fence"], {"messages": []})
    assert rows(store) == before
