"""Actual private-target writes through the original NoModel Worker; synthetic only."""

import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, event, select, update
from test_local_record_apps import (
    NoModel,
    commit,
    create_body,
    current,
    done_body,
    execute,
    ok,
    preview,
    ready,
    snapshot,
    write_json,
)
from test_local_record_apps import (
    evidence as shared_evidence,
)

from sim2act import local_record_apps as records
from sim2act import record_preview_storage as private
from sim2act.api import create_app
from sim2act.db import (
    Store,
    app_previews,
    delivery_graph_requests,
    fingerprint,
    grants,
    meta,
)
from sim2act.errors import DomainError
from sim2act.worker import Worker


@pytest.fixture
def evidence(env, tmp_path):
    yield from shared_evidence.__wrapped__(env, tmp_path)


def make_private(env, data, key="private-one"):
    body = dict(
        expected_release_fingerprint=data["release"]["fingerprint"],
        request_key=key,
        consent="CREATE_PRIVATE_WRITE_PREVIEW_NO_BUSINESS_PROMOTION",
    )
    route = f"/api/internal/record-releases/{data['release']['id']}/private-previews"
    reply = ok(env[2].post(route, json=body), 201)
    i = reply["instance"]
    assert reply["execution_namespace"] == private.NAMESPACE
    assert i["preview_scope"]["creation_request_fingerprint"] == fingerprint(body)
    return {**data, "instance": i, "path": f"/api/internal/record-instances/{i['id']}"}, body, reply


def assert_private_delta(before, after, iid, scope_fp):
    """Every old row is immutable; every new row has an exact private binding."""
    assert before.keys() == after.keys()
    fresh = {}
    for table in meta.sorted_tables:
        keys = [col.name for col in table.primary_key.columns]

        def key(row, columns=tuple(keys)):
            return tuple(row[k] for k in columns)

        old = {key(row): row for row in before[table.name]}
        actual = {key(row): row for row in after[table.name]}
        assert old.keys() <= actual.keys(), table.name
        assert all(actual[k] == value for k, value in old.items()), table.name
        fresh[table.name] = [row for k, row in actual.items() if k not in old]
    rids = {r["id"] for r in fresh["runs"]}
    aids = {r["id"] for r in fresh["internal_app_runs"]}
    oids = {r["id"] for r in fresh["operations"]}
    private_ids = {r["id"] for r in fresh["app_previews"]}
    allowed = {
        "internal_instances",
        "runs",
        "internal_app_runs",
        "internal_run_bindings",
        "run_contracts",
        "operations",
        "operation_intents",
        "local_effects",
        "internal_instance_data",
        "events",
        "delivery_graph_requests",
        "app_previews",
        "heartbeats",
    }
    assert all(not rows for name, rows in fresh.items() if name not in allowed)
    assert len(fresh["internal_instances"]) == 1 and fresh["internal_instances"][0]["id"] == iid
    assert all(
        r["instance_id"] == iid
        for r in fresh["internal_app_runs"] + fresh["internal_instance_data"]
    )
    assert all(r["run_id"] in aids for r in fresh["internal_instance_data"])
    assert all(
        r["run_id"] in rids
        and r["snapshot"]["instance_id"] == iid
        and r["snapshot"]["preview_scope_fingerprint"] == scope_fp
        for r in fresh["internal_run_bindings"]
    )
    assert all(r["context"]["preview_scope"]["fingerprint"] == scope_fp for r in fresh["runs"])
    assert all(
        r["run_id"] in rids
        for name in ["run_contracts", "operations", "events"]
        for r in fresh[name]
    )
    assert all(
        r["operation_id"] in oids
        for name in ["operation_intents", "local_effects"]
        for r in fresh[name]
    )
    assert all(r["resource_id"] in private_ids for r in fresh["local_effects"])
    for row in fresh["app_previews"]:
        assert row["input"]["instance_id"] == iid and row["input"]["run_id"] in rids
        assert (
            row["input"]["operation_id"] in oids and row["input"]["scope_fingerprint"] == scope_fp
        )
        assert (
            row["output"]["hash"] == hashlib.sha256(row["output"]["content"].encode()).hexdigest()
        )
    for row in fresh["delivery_graph_requests"]:
        kind = row["kind"]
        if kind.startswith(private.INSTANCE):
            assert row["snapshot"]["response"]["id"] == iid
        elif kind.startswith(records.RUN_SCOPE):
            assert (
                row["app_id"] in rids
                and row["snapshot"]["response"]["preview_scope_fingerprint"] == scope_fp
            )
        else:
            assert row["app_id"] == iid and kind in {
                records.PREVIEW,
                records.PREVIEW + "_seal",
                records.ACCEPTED,
                records.ACCEPTED + "_seal",
            }
    assert len(fresh["heartbeats"]) == len(rids)
    return {
        "tables_checked": len(before),
        "added_rows": {k: len(v) for k, v in fresh.items() if v},
        "all_existing_rows_unchanged": True,
        "new_run_ids": sorted(rids),
        "private_object_ids": sorted(private_ids),
    }


def test_real_private_storage_isolated_and_cold_readback_then_explicit_business_write(
    env, tmp_path, evidence
):
    data = ready(env)
    execute(env, data, create_body(current(env, data), "business-a", title="Synthetic business A"))
    business = current(env, data)
    before = snapshot(env[0])
    write_json(tmp_path / "before-private.json", before)
    trial, body, created = make_private(env, data)
    assert (
        ok(
            env[2].post(
                f"/api/internal/record-releases/{data['release']['id']}/private-previews", json=body
            ),
            201,
        )
        == created
    )
    delivery = ok(env[2].get(f"/api/apps/{data['app']['id']}/record-delivery"))
    assert [i["id"] for i in delivery["instances"]] == [data["instance"]["id"]]
    assert [i["id"] for i in delivery["preview_instances"]] == [trial["instance"]["id"]]
    one = execute(
        env, trial, create_body(current(env, trial), "private-b", title="Synthetic private B")
    )
    first = current(env, trial)
    two = execute(env, trial, done_body(first, first["records"][0], "private-b-done"))
    final = current(env, trial)
    replay_run = ok(
        env[2].post(trial["path"] + "/previews/private-b/commit", json=one["submitted"]), 202
    )
    assert replay_run["run"]["run_id"] == one["run"]["id"]
    assert final["data_version"] == 2 and final["records"][0]["state"] == "DONE"
    assert (
        final["records"][0]["record_revision"] == 2 and final["history"][0] == first["history"][0]
    )
    for value in (one, two):
        run = value["run"]
        assert run["execution_namespace"] == private.NAMESPACE
        assert run["preview_scope"] == final["preview_scope"]
        assert ok(env[2].get("/api/runs/" + run["id"]))["execution_namespace"] == private.NAMESPACE
        assert env[2].get("/api/resources/" + run["output"]["resource_id"]).status_code == 403
    for suffix in ("", "?metadata_only=true"):
        history = ok(env[2].get(f"/api/projects/{env[5]}/runs" + suffix))
        assert all(
            next(r for r in history if r["id"] == v["run"]["id"])["execution_namespace"]
            == private.NAMESPACE
            for v in (one, two)
        )
    assert current(env, data) == business
    after = snapshot(env[0])
    write_json(tmp_path / "after-private.json", after)
    oracle = assert_private_delta(
        before, after, trial["instance"]["id"], final["preview_scope"]["fingerprint"]
    )
    write_json(tmp_path / "private-delta-oracle.json", oracle)
    cold = Store(env[1].database_url, test_only=True)
    try:
        with TestClient(create_app(cold, env[1])) as client:
            client.headers.update({"Authorization": "Bearer synthetic-test-A"})
            assert ok(client.get(trial["path"])) == final
            assert ok(client.get(trial["path"] + "/runs/" + one["run"]["id"])) == one["run"]
    finally:
        cold.engine.dispose()
    before_real = snapshot(env[0], {"resources", "grants"})
    ordinary = execute(
        env,
        data,
        create_body(current(env, data), "business-c", title="Synthetic explicit business C"),
    )
    after_real = snapshot(env[0], {"resources", "grants"})
    assert len(after_real["resources"]) == len(before_real["resources"]) + 1
    assert len(after_real["grants"]) == len(before_real["grants"]) + 2
    assert "preview_scope" not in ordinary["run"] and current(env, trial) == final
    evidence[0].update(
        private_runs=[one["run"]["id"], two["run"]["id"]],
        oracle=oracle,
        actual_no_model_runs=4,
        business_projection_unchanged=True,
        permission_rows_unchanged=True,
    )


def test_private_creation_replay_strict_dto_and_cross_instance_record_rejected(env, evidence):
    data = ready(env)
    trial, body, _ = make_private(env, data)
    route = f"/api/internal/record-releases/{data['release']['id']}/private-previews"
    for extra in (
        {"target_instance": data["instance"]["id"]},
        {"namespace": private.NAMESPACE},
        {"consent": "OTHER"},
    ):
        assert env[2].post(route, json={**body, **extra}).status_code == 422
    original = execute(env, trial, create_body(current(env, trial)))
    bad = done_body(current(env, data), current(env, trial)["records"][0])
    assert env[2].post(data["path"] + "/previews", json=bad).status_code == 409
    replay = ok(
        env[2].get(
            f"/api/internal/record-releases/{data['release']['id']}/private-preview-requests/{body['request_key']}"
        )
    )
    assert replay["instance"]["id"] == trial["instance"]["id"]
    assert (
        env[2]
        .get(
            f"/api/internal/record-releases/{data['release']['id']}/instance-requests/{body['request_key']}"
        )
        .status_code
        == 400
    )
    assert current(env, data)["data_version"] == 0
    evidence[0]["private_run"] = original["run"]["id"]


def test_other_actor_and_other_space_rejected_before_private_content_sql(env, evidence):
    data = ready(env)
    trial, _, _ = make_private(env, data)
    other, _, _ = make_private(env, data, "private-two")
    one = execute(env, trial, create_body(current(env, trial)))
    sql = []

    def trace(conn, cursor, statement, parameters, context, many):
        sql.append(statement)

    event.listen(env[0].engine, "before_cursor_execute", trace)
    with env[0].tx() as c:
        actual, _ = records.instance_header(env[0], c, env[3], trial["instance"]["id"])
        private.artifact(env[0], c, env[3], actual, one["run"]["output"]["resource_id"])
    assert any("SELECT app_previews.output \n" in q for q in sql)
    sql.clear()
    try:
        denied = env[2].post(
            "/api/previews/" + one["run"]["output"]["resource_id"] + "/extract",
            json=dict(
                expected_source_fingerprint=data["app"]["fingerprint"],
                resource_id=env[6],
                name="Synthetic forbidden preview reuse",
                request_key="private-not-business-source",
            ),
        )
        assert denied.status_code == 403
        for path in [
            trial["path"],
            trial["path"] + "/runs/" + one["run"]["id"],
            "/api/runs/" + one["run"]["id"],
        ]:
            assert (
                env[2].get(path, headers={"Authorization": "Bearer synthetic-test-B"}).status_code
                == 403
            )
        with env[0].tx() as c:
            i, _ = records.instance_header(env[0], c, env[3], other["instance"]["id"])
            with pytest.raises(DomainError):
                private.artifact(env[0], c, env[3], i, one["run"]["output"]["resource_id"])
        assert not any("SELECT app_previews.output \n" in q for q in sql)
        assert env[2].get(other["path"] + "/runs/" + one["run"]["id"]).status_code == 403
        evidence[0].update(
            private_content_projection_reads=0,
            sql=sql,
            cross_actor="ACTUAL_HTTP_403",
            cross_space="ACTUAL_SCOPE_REJECTION",
        )
    finally:
        event.remove(env[0].engine, "before_cursor_execute", trace)


def test_real_private_insert_then_failure_rolls_back_original_transaction(
    env, monkeypatch, tmp_path, evidence
):
    data = ready(env)
    trial, _, _ = make_private(env, data)
    prepared = preview(env, trial, create_body(current(env, trial)))
    accepted, _ = commit(env, trial, prepared)
    before = snapshot(env[0])
    observed = []
    original = records.write_text_artifact

    def fail_after_save(*args, **kwargs):
        output = original(*args, **kwargs)
        row = (
            args[1]
            .execute(select(app_previews).where(app_previews.c.id == output["resource_id"]))
            .mappings()
            .one()
        )
        observed.append(dict(row))
        raise DomainError("VERSION_CONFLICT", "Synthetic failure after actual private insert")

    monkeypatch.setattr(records, "write_text_artifact", fail_after_save)
    assert Worker(env[0], env[1], NoModel()).once()
    failed = ok(env[2].get(trial["path"] + "/runs/" + accepted["run"]["run_id"]))
    assert failed["status"] == "FAILED" and failed["output"] is None and len(observed) == 1
    after = snapshot(env[0])
    write_json(tmp_path / "rollback-before.json", before)
    write_json(tmp_path / "rollback-after.json", after)
    for name in [
        "resources",
        "grants",
        "app_previews",
        "operations",
        "operation_intents",
        "local_effects",
        "internal_instance_data",
        "internal_instances",
    ]:
        assert before[name] == after[name], name
    assert current(env, trial)["data_version"] == 0
    evidence[0].update(actual_private_insert_before_rollback=observed, failed_run=failed)


def test_missing_private_creation_anchor_never_downgrades_to_business_writer(env, evidence):
    data = ready(env)
    trial, body, _ = make_private(env, data)
    before = snapshot(env[0], {"resources", "grants", "app_previews"})
    with env[0].tx() as c:
        assert (
            c.execute(
                delete(delivery_graph_requests).where(
                    delivery_graph_requests.c.kind == private.INSTANCE + "_seal",
                    delivery_graph_requests.c.request_key == body["request_key"],
                )
            ).rowcount
            == 1
        )
    assert env[2].get(trial["path"]).status_code == 409
    assert (
        env[2]
        .post(
            trial["path"] + "/previews",
            json=create_body(
                {
                    "revision": 1,
                    "data_version": 0,
                    "release_fingerprint": body["expected_release_fingerprint"],
                }
            ),
        )
        .status_code
        == 409
    )
    assert before == snapshot(env[0], {"resources", "grants", "app_previews"})
    evidence[0]["missing_private_anchor"] = "FAIL_CLOSED_NO_WRITER"


def test_write_revocation_denies_content_but_original_metadata_cancel_remains(env, evidence):
    data = ready(env)
    trial, _, _ = make_private(env, data)
    execute(env, trial, create_body(current(env, trial)))
    prepared = preview(env, trial, create_body(current(env, trial), "queued-private"))
    accepted, _ = commit(env, trial, prepared)
    with env[0].tx() as c:
        grant = (
            c.execute(
                select(grants).where(
                    grants.c.principal_id == env[3],
                    grants.c.project_id == env[5],
                    grants.c.resource_id == env[5],
                    grants.c.tool_ref == "artifact.save_text",
                    grants.c.revoked.is_(False),
                )
            )
            .mappings()
            .one()
        )
        c.execute(
            update(grants)
            .where(grants.c.id == grant["id"])
            .values(revoked=True, revision=grant["revision"] + 1)
        )
    assert env[2].get(trial["path"]).status_code == 403
    metadata = ok(
        env[2].get(trial["path"] + "/runs/" + accepted["run"]["run_id"] + "/private-control-status")
    )
    assert (
        metadata["content_access"] is False
        and metadata["status"] == "QUEUED"
        and metadata["version"] == 1
    )
    assert (
        env[2]
        .get(
            trial["path"] + "/runs/" + accepted["run"]["run_id"] + "/private-control-status",
            headers={"Authorization": "Bearer synthetic-test-B"},
        )
        .status_code
        == 403
    )
    cancelled = ok(
        env[2].post(
            trial["path"] + "/runs/" + accepted["run"]["run_id"] + "/commands",
            json=dict(command="cancel", version=1),
        )
    )
    assert cancelled["status"] == "CANCELLED" and cancelled["content_access"] is False
    evidence[0]["revoked_metadata_cancel"] = cancelled
