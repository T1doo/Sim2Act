"""Synthetic complete report recipe, real ASGI/SQLite/original Worker, NoModel."""

import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import delete, select, update
from test_natural_receipt_candidate import table_snapshot
from test_ordinary_csv_report import NoModel, prepare

from sim2act.db import (
    attempts,
    csv_report_workflow_uses,
    csv_report_workflows,
    events,
    fingerprint,
    grants,
    operations,
    reservations,
    runs,
)
from sim2act.worker import Worker


def source(env):
    store, settings, client, _, _, project, material = env
    response = prepare(client, project, material)
    assert response.status_code == 202, response.text
    rid = response.json()["run_id"]
    frozen = client.get(f"/api/runs/{rid}").json()
    assert (
        client.post(
            f"/api/runs/{rid}/confirm-csv-report",
            json=dict(
                version=frozen["version"],
                contract_fingerprint=frozen["contract"]["fingerprint"],
                request_key="confirm-original",
            ),
        ).status_code
        == 200
    )
    assert Worker(store, settings, NoModel()).once()
    original = client.get(f"/api/runs/{rid}").json()
    assert original["result"]["goal_acceptance"] == "PASS_CSV_REPORT_CONTRACT"
    options = client.get(f"/api/runs/{rid}/csv-full-report-workflow-options")
    assert options.status_code == 200, options.text
    body = dict(
        name="完整报告流程",
        request_key="save-full-report",
        expected_definition_fingerprint=options.json()["fingerprint"],
        consent="SAVE_READ_SUM_COMPLETE_MD_WORKFLOW",
    )
    return rid, original, options.json(), body


def saved(env):
    rid, original, options, body = source(env)
    response = env[2].post(f"/api/runs/{rid}/csv-full-report-workflows", json=body)
    assert response.status_code == 201, response.text
    app = response.json()
    material = (
        env[2]
        .post(
            f"/api/projects/{env[5]}/resources",
            json=dict(
                name="different.csv", format="csv", content="amount,quantity,bad\n30,6,x\n50,9,y\n"
            ),
        )
        .json()["id"]
    )
    use = dict(
        expected_version=1,
        expected_definition_fingerprint=app["fingerprint"],
        resource_id=material,
        column="quantity",
        request_key="use-new-input",
        consent="PREPARE_NEW_COMPLETE_MD_CONTRACT_ONLY",
    )
    return rid, original, options, body, app, material, use


def test_complete_report_saved_directory_new_contract_run_and_md(env, tmp_path):
    rid, original, options, save_body = source(env)
    before = table_snapshot(env[0])
    made = env[2].post(f"/api/runs/{rid}/csv-full-report-workflows", json=save_body)
    assert made.status_code == 201, made.text
    made = made.json()
    after = table_snapshot(env[0])
    assert all(before[k] == after[k] for k in before if k != "csv_report_workflows")
    assert len(after["csv_report_workflows"]) == 1
    for suffix in ("", "?metadata_only=true"):
        directory = env[2].get("/api/apps" + suffix).json()
        item = next(x for x in directory["items"] if x["id"] == made["id"])
        assert item["use_family"] == "CSV_FULL_REPORT" and item["csv_instance_candidate"] is False
    app = env[2].get(f"/api/apps/{made['id']}").json()
    assert app["definition"]["tools"] == {
        "resource.read": "1",
        "data.aggregate_csv": "1",
        "artifact.save_text": "1",
    }
    assert app["definition"]["scope"] == "READ_SUM_SAVE_COMPLETE_MD"
    material = (
        env[2]
        .post(
            f"/api/projects/{env[5]}/resources",
            json=dict(name="fresh.csv", format="csv", content="amount,quantity\n30,6\n50,9\n"),
        )
        .json()["id"]
    )
    body = dict(
        expected_version=1,
        expected_definition_fingerprint=made["fingerprint"],
        resource_id=material,
        column="quantity",
        request_key="new-independent-run",
        consent="PREPARE_NEW_COMPLETE_MD_CONTRACT_ONLY",
    )
    snapshot = table_snapshot(env[0])
    reply = env[2].post(f"/api/apps/{made['id']}/csv-full-report-uses", json=body)
    assert reply.status_code == 202, reply.text
    new_id = reply.json()["run_id"]
    assert new_id != rid
    frozen = env[2].get(f"/api/runs/{new_id}")
    assert frozen.status_code == 200, frozen.text
    frozen = frozen.json()
    assert frozen["status"] == "WAITING_APPROVAL" and frozen["ordinary_csv"]["confirmed"] is False
    assert frozen["contract"]["fingerprint"] != original["contract"]["fingerprint"]
    spec = frozen["contract"]["snapshot"]["ordinary_csv_report"]
    assert spec["resource_id"] == material and spec["sum"] == "15" and spec["count"] == 2
    assert not Worker(env[0], env[1], NoModel()).once()
    pending = table_snapshot(env[0])
    assert (
        snapshot["grants"] == pending["grants"] and snapshot["operations"] == pending["operations"]
    )
    confirm = dict(
        version=frozen["version"],
        contract_fingerprint=frozen["contract"]["fingerprint"],
        request_key="confirm-new",
    )
    assert env[2].post(f"/api/runs/{new_id}/confirm-csv-report", json=confirm).status_code == 200
    assert Worker(env[0], env[1], NoModel()).once()
    result = env[2].get(f"/api/runs/{new_id}")
    assert result.status_code == 200, result.text
    result = result.json()
    assert (
        result["status"] == "SUCCEEDED"
        and result["result"]["goal_acceptance"] == "PASS_CSV_REPORT_CONTRACT"
    )
    assert result["result"]["task_acceptance"]["owner_acceptance"] == "PENDING"
    artifact_id = result["result"]["receipts"][-1]["data"]["resource_id"]
    artifact = env[2].get(f"/api/resources/{artifact_id}").json()
    assert artifact["content"] == spec["report_text"] and artifact["hash"] == spec["report_hash"]
    assert artifact["content"].endswith("\n") and "精确合计：15" in artifact["content"]
    assert env[2].get(f"/api/runs/{rid}").json() == original
    assert env[2].get(f"/api/runs/{new_id}/csv-full-report-workflow-options").status_code == 409
    with env[0].tx() as c:
        assert len(c.execute(select(operations)).all()) == 6
        assert len(c.execute(select(grants)).all()) == len(pending["grants"]) + 2
        assert (
            not c.execute(select(attempts)).first() and not c.execute(select(reservations)).first()
        )
    (tmp_path / "delivery.json").write_text(
        json.dumps(
            dict(
                source=original,
                options=options,
                workflow=app,
                request=body,
                accepted=reply.json(),
                frozen=frozen,
                result=result,
                artifact=artifact,
                model_requests=0,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
    (tmp_path / "fresh-complete-report.md").write_text(artifact["content"])


def test_consent_atomic_idempotency_original_key_and_invalid_input(env, tmp_path):
    rid, original, _, save_body = source(env)
    path = f"/api/runs/{rid}/csv-full-report-workflows"
    missing = {k: v for k, v in save_body.items() if k != "consent"}
    assert env[2].post(path, json=missing).status_code == 422
    with ThreadPoolExecutor(2) as pool:
        replies = list(pool.map(lambda _: env[2].post(path, json=save_body), range(2)))
    assert [r.status_code for r in replies] == [201, 201], [r.text for r in replies]
    app = replies[0].json()
    assert replies[1].json() == app
    assert env[2].post(path, json={**save_body, "name": "changed"}).status_code == 409
    assert (
        env[2]
        .get(f"/api/runs/{rid}/csv-full-report-workflow-requests/{save_body['request_key']}")
        .json()
        == app
    )
    material = (
        env[2]
        .post(
            f"/api/projects/{env[5]}/resources",
            json=dict(name="new.csv", format="csv", content="value,bad\n2,x\n3,y\n"),
        )
        .json()["id"]
    )
    body = dict(
        expected_version=1,
        expected_definition_fingerprint=app["fingerprint"],
        resource_id=material,
        column="bad",
        request_key="same-use-key",
        consent="PREPARE_NEW_COMPLETE_MD_CONTRACT_ONLY",
    )
    before = table_snapshot(env[0])
    endpoint = f"/api/apps/{app['id']}/csv-full-report-uses"
    assert env[2].post(endpoint, json=body).status_code == 400
    assert table_snapshot(env[0]) == before
    body["column"] = "value"
    with ThreadPoolExecutor(2) as pool:
        replies = list(pool.map(lambda _: env[2].post(endpoint, json=body), range(2)))
    assert [r.status_code for r in replies] == [202, 202], [r.text for r in replies]
    assert replies[0].json() == replies[1].json()
    assert env[2].post(endpoint, json={**body, "column": "bad"}).status_code == 409
    assert env[2].post(endpoint, json={**body, "expected_version": True}).status_code == 422
    recovered = env[2].get(
        f"/api/apps/{app['id']}/csv-full-report-use-requests/{body['request_key']}"
    )
    assert (
        recovered.json() == replies[0].json() and recovered.headers["cache-control"] == "no-store"
    )
    with env[0].tx() as c:
        assert len(c.execute(select(csv_report_workflows)).all()) == 1
        assert len(c.execute(select(csv_report_workflow_uses)).all()) == 1
        assert len(c.execute(select(runs)).all()) == 2
    (tmp_path / "idempotency.json").write_text(
        json.dumps(
            dict(workflow=app, replies=[r.json() for r in replies], recovered=recovered.json()),
            indent=2,
        )
    )
    assert env[2].get(f"/api/runs/{rid}").json() == original


@pytest.mark.parametrize(
    "target", ["source", "new-material", "project-save", "account", "marker", "link", "event-type"]
)
def test_current_scope_and_independent_binding_before_protected_read_or_confirm(env, target):
    rid, _, _, _, app, material, body = saved(env)
    response = env[2].post(f"/api/apps/{app['id']}/csv-full-report-uses", json=body)
    assert response.status_code == 202, response.text
    run_id = response.json()["run_id"]
    frozen = env[2].get(f"/api/runs/{run_id}").json()
    with env[0].tx() as c:
        if target in ("source", "new-material", "project-save"):
            resource = (
                env[6] if target == "source" else material if target == "new-material" else env[5]
            )
            c.execute(
                update(grants)
                .where(grants.c.project_id == env[5], grants.c.resource_id == resource)
                .values(revoked=True)
            )
        elif target == "marker":
            context = dict(
                c.execute(select(runs.c.context).where(runs.c.id == run_id)).scalar_one()
            )
            context.pop("csv_full_report_use")
            c.execute(update(runs).where(runs.c.id == run_id).values(context=context))
        elif target == "event-type":
            data = dict(
                c.execute(
                    select(events.c.data).where(
                        events.c.run_id == run_id, events.c.kind == "CSV_FULL_REPORT_USE"
                    )
                ).scalar_one()
            )
            data["definition_version"] = True
            c.execute(
                update(events)
                .where(events.c.run_id == run_id, events.c.kind == "CSV_FULL_REPORT_USE")
                .values(data=data)
            )
        elif target == "link":
            c.execute(
                delete(csv_report_workflow_uses).where(csv_report_workflow_uses.c.run_id == run_id)
            )
    if target == "account":
        env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    status = 403 if target in ("source", "new-material", "project-save", "account") else 409
    rejected = env[2].get(f"/api/runs/{run_id}")
    assert rejected.status_code == status, rejected.text
    assert "report_text" not in rejected.text and material not in rejected.text
    confirm = env[2].post(
        f"/api/runs/{run_id}/confirm-csv-report",
        json=dict(
            version=frozen["version"],
            contract_fingerprint=frozen["contract"]["fingerprint"],
            request_key="must-refuse",
        ),
    )
    assert confirm.status_code == status, confirm.text
    with env[0].tx() as c:
        row = c.execute(select(runs.c.status).where(runs.c.id == run_id)).scalar_one()
        assert row == "WAITING_APPROVAL"
        assert len(c.execute(select(operations)).all()) == 3


def test_definition_self_rehash_cannot_change_recipe(env):
    _, _, _, _, app, _, body = saved(env)
    with env[0].tx() as c:
        definition = dict(
            c.execute(
                select(csv_report_workflows.c.definition).where(
                    csv_report_workflows.c.id == app["id"]
                )
            ).scalar_one()
        )
        definition["tools"] = {"data.aggregate_csv": "1"}
        c.execute(
            update(csv_report_workflows)
            .where(csv_report_workflows.c.id == app["id"])
            .values(definition=definition, fingerprint=fingerprint(definition))
        )
    assert env[2].get(f"/api/apps/{app['id']}").status_code == 409
    assert env[2].post(f"/api/apps/{app['id']}/csv-full-report-uses", json=body).status_code == 409
    with env[0].tx() as c:
        assert not c.execute(select(csv_report_workflow_uses)).first()


@pytest.mark.parametrize("case", ["deliver", "lost", "misbound", "navigation", "revoked-source"])
def test_visible_complete_report_directory_and_new_run(env, tmp_path, case):
    import hashlib
    import os
    import subprocess
    import threading
    from pathlib import Path

    rid, original, _, _ = source(env)
    material = (
        env[2]
        .post(
            f"/api/projects/{env[5]}/resources",
            json=dict(name="page-new.csv", format="csv", content="amount,quantity\n30,6\n50,9\n"),
        )
        .json()["id"]
    )
    other = env[2].post("/api/projects", json={"name": "other project"}).json()["id"]
    info = dict(
        case=case,
        run=rid,
        project=env[5],
        other=other,
        material=material,
        output=str(tmp_path / "page-result.json"),
    )
    (tmp_path / "info.json").write_text(json.dumps(info))
    process = None
    watchdog = None
    worker_runs = []
    try:
        with (tmp_path / "node.stderr").open("w") as errors:
            process = subprocess.Popen(
                ["node", "tests/csv_full_report.cjs", str(tmp_path / "info.json")],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=errors,
                text=True,
                env={
                    **os.environ,
                    "NODE_PATH": str(Path.cwd() / "scripts/engineering-ci/node_modules"),
                },
            )
            watchdog = threading.Timer(90, process.kill)
            watchdog.start()
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                if request.get("command") in ("revoke-source", "revoke-output"):
                    resource = (
                        env[6] if request["command"] == "revoke-source" else request["resource"]
                    )
                    with env[0].tx() as c:
                        c.execute(
                            update(grants)
                            .where(grants.c.project_id == env[5], grants.c.resource_id == resource)
                            .values(revoked=True)
                        )
                    answer = dict(status=200, text="{}")
                elif request.get("command") == "worker":
                    assert Worker(env[0], env[1], NoModel()).once()
                    result = env[2].get(f"/api/runs/{request['run']}")
                    assert result.status_code == 200, result.text
                    worker_runs.append(result.json())
                    answer = dict(status=200, text="{}")
                else:
                    response = env[2].request(
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
                process.stdin.write(json.dumps(dict(id=request["id"], **answer)) + "\n")
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=15)
        assert code == 0, (tmp_path / "node.stderr").read_text()
        page = json.loads((tmp_path / "page-result.json").read_text())
        assert page["status"] == "PASS"
        for asset in page["assets"]:
            path = Path("src/sim2act/web") / (asset["path"].lstrip("/") or "index.html")
            assert hashlib.sha256(path.read_bytes()).hexdigest() == asset["sha256"]
        assert len(worker_runs) == (0 if case in ("navigation", "revoked-source") else 1)
        with env[0].tx() as c:
            assert (
                not c.execute(select(attempts)).first()
                and not c.execute(select(reservations)).first()
            )
            assert len(c.execute(select(csv_report_workflows)).all()) == (
                0 if case == "revoked-source" else 1
            )
            assert len(c.execute(select(csv_report_workflow_uses)).all()) == (
                0 if case == "revoked-source" else 2 if case == "navigation" else 1
            )
        # Browser case may end as B; assert A's historical original remains identical.
        env[2].headers["Authorization"] = "Bearer synthetic-test-A"
        if case != "revoked-source":
            assert env[2].get(f"/api/runs/{rid}").json() == original
        else:
            assert env[2].get(f"/api/runs/{rid}").status_code == 403
    finally:
        if watchdog is not None:
            watchdog.cancel()
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        (tmp_path / "page-worker-proof.json").write_text(
            json.dumps(
                dict(
                    original=original,
                    worker_runs=worker_runs,
                    real_model_requests=0,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )


def test_queued_use_reauthorizes_source_before_original_worker_claim(env):
    _, _, _, _, app, _, body = saved(env)
    response = env[2].post(f"/api/apps/{app['id']}/csv-full-report-uses", json=body)
    assert response.status_code == 202, response.text
    rid = response.json()["run_id"]
    frozen = env[2].get(f"/api/runs/{rid}").json()
    assert (
        env[2]
        .post(
            f"/api/runs/{rid}/confirm-csv-report",
            json=dict(
                version=frozen["version"],
                contract_fingerprint=frozen["contract"]["fingerprint"],
                request_key="queue-before-source-revoked",
            ),
        )
        .status_code
        == 200
    )
    with env[0].tx() as c:
        c.execute(
            update(grants)
            .where(grants.c.project_id == env[5], grants.c.resource_id == env[6])
            .values(revoked=True)
        )
    assert not Worker(env[0], env[1], NoModel()).once()
    with env[0].tx() as c:
        row = c.execute(
            select(runs.c.status, runs.c.error, runs.c.fence).where(runs.c.id == rid)
        ).one()
        assert (
            row.status == "WAITING_RESOURCE"
            and row.error["code"] == "GRANT_REVOKED"
            and row.fence == 0
        )
        assert len(c.execute(select(operations)).all()) == 3
        assert (
            not c.execute(select(attempts)).first() and not c.execute(select(reservations)).first()
        )


def test_source_result_numeric_type_change_does_not_inherit_pass(env):
    rid, original, _, body = source(env)
    with env[0].tx() as c:
        result = dict(original["result"])
        result["model_requests"] = 0.0
        c.execute(update(runs).where(runs.c.id == rid).values(result=result))
    assert env[2].get(f"/api/runs/{rid}/csv-full-report-workflow-options").status_code == 409
    assert env[2].post(f"/api/runs/{rid}/csv-full-report-workflows", json=body).status_code == 409
    with env[0].tx() as c:
        assert not c.execute(select(csv_report_workflows)).first()


def test_saved_output_reauthorized_from_effect_before_private_run_body(env, tmp_path):
    from sqlalchemy import event

    _, _, _, _, app, _, body = saved(env)
    reply = env[2].post(f"/api/apps/{app['id']}/csv-full-report-uses", json=body)
    assert reply.status_code == 202, reply.text
    rid = reply.json()["run_id"]
    frozen = env[2].get(f"/api/runs/{rid}").json()
    confirmation = dict(
        version=frozen["version"],
        contract_fingerprint=frozen["contract"]["fingerprint"],
        request_key="confirm-output-gate",
    )
    assert env[2].post(f"/api/runs/{rid}/confirm-csv-report", json=confirmation).status_code == 200
    assert Worker(env[0], env[1], NoModel()).once()
    statements = []

    def trace(_conn, _cursor, statement, parameters, _context, _many):
        if rid in str(parameters):
            statements.append(statement)

    event.listen(env[0].engine, "before_cursor_execute", trace)
    try:
        positive = env[2].get(f"/api/runs/{rid}")
        assert positive.status_code == 200, positive.text
        result = positive.json()
    finally:
        event.remove(env[0].engine, "before_cursor_execute", trace)
    positive_statements = list(statements)
    assert any("runs.context, runs.result" in sql for sql in positive_statements)
    statements.clear()
    receipt = result["result"]["receipts"][-1]
    with env[0].tx() as c:
        c.execute(
            update(grants)
            .where(
                grants.c.project_id == env[5],
                grants.c.resource_id == receipt["data"]["resource_id"],
            )
            .values(revoked=True)
        )
        changed = dict(receipt)
        changed["artifact_refs"] = []
        c.execute(
            update(operations)
            .where(operations.c.id == receipt["operation_id"])
            .values(receipt=changed)
        )
    event.listen(env[0].engine, "before_cursor_execute", trace)
    try:
        for response in (
            env[2].get(f"/api/runs/{rid}"),
            env[2].post(f"/api/runs/{rid}/confirm-csv-report", json=confirmation),
            env[2].get(f"/api/apps/{app['id']}/csv-full-report-use-requests/{body['request_key']}"),
        ):
            assert response.status_code == 403, response.text
            assert "report_text" not in response.text and "精确合计" not in response.text
    finally:
        event.remove(env[0].engine, "before_cursor_execute", trace)
    assert statements and not any("runs.context, runs.result" in sql for sql in statements)
    (tmp_path / "private-run-sql.json").write_text(
        json.dumps(
            dict(
                run_id=rid,
                positive_statements=positive_statements,
                positive_full_run_reads=sum(
                    "runs.context, runs.result" in sql for sql in positive_statements
                ),
                statements=statements,
                target_full_run_reads=0,
                receipt_refs_removed=True,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
