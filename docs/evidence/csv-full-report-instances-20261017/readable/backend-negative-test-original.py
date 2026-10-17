"""Synthetic API/SQLite/NoModel safety checks with actual HTTP and DB evidence."""

import copy
import json
import re

import pytest
from sqlalchemy import event, select, update
from test_csv_full_report_instances import complete, delivered
from test_csv_goal_revisions import raw_trace as raw_trace
from test_natural_receipt_candidate import table_snapshot
from test_ordinary_csv_report import NoModel

from sim2act import csv_full_report_instances as adapter
from sim2act.db import (
    attempts,
    csv_report_workflows,
    delivery_graph_requests,
    events,
    fingerprint,
    internal_app_runs,
    internal_approvals,
    internal_instance_data,
    internal_instances,
    internal_releases,
    operations,
    reservations,
    runs,
)
from sim2act.worker import Worker


@pytest.fixture
def evidence(tmp_path):
    value = {}
    yield value
    (tmp_path / "actual-complete-report-negative.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )


def _answer(response):
    return {"status": response.status_code, "body": response.json()}


def _readonly(env, method, path, expected, evidence, label, *, body=None, sql=None):
    before = table_snapshot(env[0])
    if sql is not None:
        event.listen(env[0].engine, "before_cursor_execute", sql)
    try:
        response = env[2].request(method, path, json=body)
    finally:
        if sql is not None:
            event.remove(env[0].engine, "before_cursor_execute", sql)
    after = table_snapshot(env[0])
    evidence[label] = {
        **_answer(response),
        "method": method,
        "path": path,
        "request": body,
        "database_before": fingerprint(before),
        "database_after": fingerprint(after),
    }
    assert response.status_code in set(expected), response.text
    assert after == before, label
    return response


def _prepare_body(instance, release, material, key):
    return dict(
        expected_revision=instance["revision"],
        expected_release_fingerprint=release["fingerprint"],
        resource_id=material,
        column="quantity",
        request_key=key,
        consent="PREPARE_NEW_COMPLETE_MD_CONTRACT_ONLY",
    )


def _prepared(env, instance, release, material, key):
    body = _prepare_body(instance, release, material, key)
    response = env[2].post(
        f"/api/internal/instances/{instance['id']}/csv-full-report-uses", json=body
    )
    assert response.status_code == 202, response.text
    receipt = response.json()
    frozen = env[2].get("/api/runs/" + receipt["run_id"])
    assert frozen.status_code == 200, frozen.text
    assert frozen.json()["status"] == "WAITING_APPROVAL"
    return body, receipt, frozen.json()


def _confirmation(frozen, key):
    return dict(
        version=frozen["version"],
        contract_fingerprint=frozen["contract"]["fingerprint"],
        request_key=key,
    )


def _cancel_metadata(env, rid, evidence, label):
    with env[0].tx() as connection:
        row = dict(
            connection.execute(select(runs.c.status, runs.c.version).where(runs.c.id == rid))
            .mappings()
            .one()
        )
    response = env[2].post(
        f"/api/runs/{rid}/commands", json={"command": "cancel", "version": row["version"]}
    )
    evidence[label] = {"before": row, **_answer(response)}
    assert response.status_code == 200, response.text
    with env[0].tx() as connection:
        assert (
            connection.execute(select(runs.c.status).where(runs.c.id == rid)).scalar_one()
            == "CANCELLED"
        )


def _no_models_or_instance_success(env, iid):
    with env[0].tx() as connection:
        assert connection.execute(select(attempts.c.id)).first() is None
        assert connection.execute(select(reservations.c.run_id)).first() is None
        assert (
            connection.execute(
                select(internal_instance_data.c.run_id).where(
                    internal_instance_data.c.instance_id == iid
                )
            ).first()
            is None
        )
        assert (
            connection.execute(
                select(internal_app_runs.c.id).where(
                    internal_app_runs.c.instance_id == iid,
                    internal_app_runs.c.status == "SUCCEEDED",
                )
            ).first()
            is None
        )


def _patch(connection, changed, table, where, values):
    original = dict(connection.execute(select(table).where(where)).mappings().one())
    primary = {column.name: original[column.name] for column in table.primary_key.columns}
    changed.append((table, primary, original))
    connection.execute(update(table).where(where).values(**values))


def _restore_only_known_attack_rows(store, changed):
    with store.tx() as connection:
        for table, primary, original in reversed(changed):
            where = [table.c[name] == value for name, value in primary.items()]
            connection.execute(update(table).where(*where).values(**original))


def _resign_approval_release(
    connection, changed, user, recipe_id, approval, release, snapshot, *, expiry=None
):
    payload = copy.deepcopy(approval["payload"])
    payload["snapshot"] = copy.deepcopy(snapshot)
    values = {}
    if expiry is not None:
        payload["expires_at"] = expiry
        values["expires_at"] = expiry
    forged_fp = fingerprint(payload)
    _patch(
        connection,
        changed,
        internal_approvals,
        internal_approvals.c.id == approval["id"],
        {**values, "payload": payload, "fingerprint": forged_fp},
    )
    if release is not None:
        _patch(
            connection,
            changed,
            internal_releases,
            internal_releases.c.id == release["id"],
            {"snapshot": copy.deepcopy(snapshot), "fingerprint": fingerprint(snapshot)},
        )
    rows = (
        connection.execute(
            select(delivery_graph_requests).where(
                delivery_graph_requests.c.app_id == recipe_id,
                delivery_graph_requests.c.principal_id == user,
                delivery_graph_requests.c.kind.in_([adapter.RELEASE, adapter.RELEASE + "_seal"]),
                delivery_graph_requests.c.snapshot["response"]["id"].as_string() == approval["id"],
            )
        )
        .mappings()
        .all()
    )
    assert len(rows) == 2
    for row in rows:
        value = copy.deepcopy(row["snapshot"])
        value["response"]["fingerprint"] = forged_fp
        value["response"]["snapshot_fingerprint"] = fingerprint(snapshot)
        _patch(
            connection,
            changed,
            delivery_graph_requests,
            (delivery_graph_requests.c.app_id == row["app_id"])
            & (delivery_graph_requests.c.principal_id == row["principal_id"])
            & (delivery_graph_requests.c.kind == row["kind"])
            & (delivery_graph_requests.c.request_key == row["request_key"]),
            {
                "snapshot": value,
                "fingerprint": fingerprint(value),
                "request_fingerprint": fingerprint(value["request"]),
            },
        )
    return forged_fp


def _float_count(connection, changed, iid, app_run_id):
    row = (
        connection.execute(
            select(internal_instance_data).where(
                internal_instance_data.c.instance_id == iid,
                internal_instance_data.c.run_id == app_run_id,
            )
        )
        .mappings()
        .one()
    )
    value = copy.deepcopy(row["data"])
    assert type(value["result"]["count"]) is int and value["result"]["count"] == 2
    value["result"]["count"] = 2.0
    _patch(
        connection,
        changed,
        internal_instance_data,
        (internal_instance_data.c.instance_id == iid)
        & (internal_instance_data.c.version == row["version"]),
        {"data": value, "fingerprint": fingerprint(value)},
    )
    _patch(
        connection,
        changed,
        internal_app_runs,
        internal_app_runs.c.id == app_run_id,
        {"output": copy.deepcopy(value["result"])},
    )


def test_recipe_check_schema_typed_result_and_ttl_cannot_be_locally_resigned(env, evidence):
    _, original, recipe, material, release, instance, root, _, approval = delivered(env)
    _, receipt, result = complete(env, instance["id"], release, material, "typed-proof")
    assert result["result"]["goal_acceptance"] == "PASS_CSV_REPORT_CONTRACT"
    # Historical consumed approvals need not expire. TTL must attack a distinct
    # still-unconsumed approval, without creating another Run or using a clock wait.
    ttl = env[2].post(
        root + "/release-approvals",
        json=dict(
            expected_definition_fingerprint=recipe["fingerprint"],
            request_key="ttl-unconsumed",
            consent="FREEZE_COMPLETE_MD_RECIPE_AND_CHECK",
        ),
    )
    assert ttl.status_code == 201, ttl.text
    ttl = ttl.json()
    assert ttl["consumed"] is False
    evidence["original_source"] = original
    baseline = table_snapshot(env[0])
    for fault in ("recipe", "check", "schema-and-float-count", "float-count-only", "ttl"):
        changed = []
        case = evidence[fault] = {}
        try:
            with env[0].tx() as connection:
                snap = copy.deepcopy(release["snapshot"])
                if fault == "recipe":
                    definition = copy.deepcopy(snap["definition"])
                    definition["formatter"] = "synthetic.unapproved-formatter.v1"
                    _patch(
                        connection,
                        changed,
                        csv_report_workflows,
                        csv_report_workflows.c.id == recipe["id"],
                        {"definition": definition, "fingerprint": fingerprint(definition)},
                    )
                    snap["definition"] = definition
                    snap["draft"]["fingerprint"] = fingerprint(definition)
                    snap["check_evidence"]["definition_fingerprint"] = fingerprint(definition)
                elif fault == "check":
                    snap["check_evidence"]["source"]["source_report_hash"] = "0" * 64
                elif fault == "schema-and-float-count":
                    snap["data_schema"]["properties"]["result"]["properties"]["count"] = {
                        "type": "number"
                    }
                    _float_count(connection, changed, instance["id"], receipt["app_run_id"])
                elif fault == "float-count-only":
                    _float_count(connection, changed, instance["id"], receipt["app_run_id"])
                if fault == "ttl":
                    forged_fp = _resign_approval_release(
                        connection,
                        changed,
                        env[3],
                        recipe["id"],
                        ttl,
                        None,
                        ttl["payload"]["snapshot"],
                        expiry=1.0,
                    )
                elif fault != "float-count-only":
                    forged_fp = _resign_approval_release(
                        connection, changed, env[3], recipe["id"], approval, release, snap
                    )
                case["intentional_fixture_mutation"] = fault
                case["approval_pair_resigned"] = fault != "float-count-only"
                case["typed_data_rows_resigned"] = fault in {
                    "schema-and-float-count",
                    "float-count-only",
                }
            if fault == "ttl":
                _readonly(
                    env,
                    "GET",
                    root + "/release-requests/ttl-unconsumed",
                    {409},
                    case,
                    "expired_read",
                )
                _readonly(
                    env,
                    "POST",
                    f"/api/internal/approvals/{ttl['id']}/commit",
                    {409},
                    case,
                    "expired_commit",
                    body={"fingerprint": forged_fp},
                )
            else:
                _readonly(
                    env, "GET", root, {400, 409}, case, "delivery_refuses_forged_proof_or_result"
                )
                if fault != "float-count-only":
                    _readonly(
                        env,
                        "GET",
                        "/api/internal/releases/" + release["id"],
                        {409},
                        case,
                        "release_refuses_jointly_resigned_snapshot",
                    )
                    _readonly(
                        env,
                        "POST",
                        f"/api/internal/approvals/{approval['id']}/commit",
                        {409},
                        case,
                        "commit_refuses_jointly_resigned_snapshot",
                        body={"fingerprint": forged_fp},
                    )
        finally:
            # If the API unexpectedly created a new row, it is preserved for
            # diagnosis; this assertion exposes it rather than deleting evidence.
            _restore_only_known_attack_rows(env[0], changed)
            case["known_attack_rows_restored"] = table_snapshot(env[0]) == baseline
            assert case["known_attack_rows_restored"]


def _private_body(statement):
    sql = re.sub(r'["`\[\]]', "", statement).lower()
    sql = re.sub(r"\s+", " ", sql).strip()
    if not sql.startswith("select "):
        return False
    projection = re.split(r"\bfrom\b", sql, maxsplit=1)[0]
    return bool(
        re.search(
            r"(?:^select |, )(?:(?:runs\.(?:context|result))|(?:run_contracts\.snapshot)|"
            r"(?:csv_report_workflows\.definition)|(?:internal_approvals\.payload)|"
            r"(?:internal_releases\.snapshot)|(?:delivery_graph_requests\.snapshot))(?:,|\s*$)",
            projection,
        )
    )


@pytest.mark.parametrize("target", ["source-csv", "source-md", "runtime-save"])
def test_current_source_effect_and_runtime_grant_gate_precedes_private_bodies(
    env, evidence, target
):
    _, original, recipe, material, release, instance, root, _, approval = delivered(env)
    _, receipt, frozen = _prepared(env, instance, release, material, "permission-bound")
    rid = receipt["run_id"]
    selected = []

    def observe(connection, cursor, statement, parameters, context, executemany):
        if _private_body(statement):
            selected.append({"sql": statement, "parameters": repr(parameters)})

    _readonly(env, "GET", "/api/runs/" + rid, {200}, evidence, "positive_private_read", sql=observe)
    evidence["positive_sql_control"] = list(selected)
    assert selected, "positive SQL control must see a protected full body"
    selected.clear()
    runtime = release["snapshot"]["draft"]["runtime_id"]
    resource = (
        env[6]
        if target == "source-csv"
        else (
            original["result"]["receipts"][-1]["data"]["resource_id"]
            if target == "source-md"
            else env[5]
        )
    )
    tool = "artifact.save_text" if target == "runtime-save" else "resource.read"
    listed = env[2].get(f"/api/projects/{env[5]}/grants")
    assert listed.status_code == 200, listed.text
    matches = [
        row
        for row in listed.json()
        if row["principal_id"] == runtime
        and row["resource_id"] == resource
        and row["tool_ref"] == tool
        and not row["revoked"]
    ]
    assert len(matches) == 1, matches
    grant = matches[0]
    revoked = env[2].post(
        "/api/grants/" + grant["id"] + "/revoke",
        json={"command": "revoke", "version": grant["revision"]},
    )
    evidence["explicit_exact_grant_revocation"] = {
        "target": target,
        "grant": grant,
        **_answer(revoked),
    }
    assert revoked.status_code == 200, revoked.text
    for label, path in (
        ("delivery", root),
        ("approval", "/api/internal/approvals/" + approval["id"]),
        ("run", "/api/runs/" + rid),
        (
            "original_key",
            f"/api/internal/instances/{instance['id']}/csv-full-report-requests/permission-bound",
        ),
    ):
        _readonly(env, "GET", path, {403}, evidence, label, sql=observe)
    _readonly(
        env,
        "POST",
        f"/api/runs/{rid}/confirm-csv-report",
        {403},
        evidence,
        "confirm",
        body=_confirmation(frozen, "refuse-revoked-confirm"),
        sql=observe,
    )
    evidence["denied_private_body_reads"] = list(selected)
    assert selected == [], selected
    # Cancellation is a metadata control; it must remain usable after the
    # source or saved effect can no longer be read.
    _cancel_metadata(env, rid, evidence, "cancel_after_revocation")
    assert not Worker(env[0], env[1], NoModel()).once()
    _no_models_or_instance_success(env, instance["id"])


def test_exact_revision_workflow_key_collision_active_adoption_and_cancel(env, evidence):
    _, _, recipe, material, release, instance, root, release_body, _ = delivered(env)
    iid = instance["id"]
    path = f"/api/internal/instances/{iid}/csv-full-report-uses"
    body = _prepare_body(instance, release, material, "same-use-key")
    for label, changed in (
        ("wrong_revision", {**body, "expected_revision": 2}),
        ("wrong_release_fp", {**body, "expected_release_fingerprint": "0" * 64}),
    ):
        _readonly(env, "POST", path, {409}, evidence, label, body=changed)

    # This collision lives in the original workflow journal, BEFORE any AppRun
    # exists. A mere AppRun lookup cannot fence it.
    collision_key = "preexisting-workflow-use"
    original_key = "instance-" + fingerprint([iid, collision_key])[:64]
    original = env[2].post(
        f"/api/apps/{recipe['id']}/csv-full-report-uses",
        json=dict(
            expected_version=1,
            expected_definition_fingerprint=recipe["fingerprint"],
            resource_id=material,
            column="quantity",
            request_key=original_key,
            consent="PREPARE_NEW_COMPLETE_MD_CONTRACT_ONLY",
        ),
    )
    assert original.status_code == 202, original.text
    _readonly(
        env,
        "POST",
        path,
        {409},
        evidence,
        "preexisting_original_workflow_key_collision",
        body={**body, "request_key": collision_key},
    )
    with env[0].tx() as connection:
        assert connection.execute(select(internal_app_runs.c.id)).first() is None
    _cancel_metadata(env, original.json()["run_id"], evidence, "cancel_collision_control_run")

    # Freeze an otherwise valid switch BEFORE the new use becomes active.
    made = env[2].post(
        root + "/release-approvals", json={**release_body, "request_key": "target-release"}
    )
    assert made.status_code == 201, made.text
    committed = env[2].post(
        f"/api/internal/approvals/{made.json()['id']}/commit",
        json={"fingerprint": made.json()["fingerprint"]},
    )
    assert committed.status_code == 200, committed.text
    target = committed.json()
    switch_path = f"/api/internal/instances/{iid}/csv-full-report-switch-approvals"
    switch_body = dict(
        target_release_id=target["id"],
        expected_target_fingerprint=target["fingerprint"],
        expected_revision=1,
        request_key="prepared-before-active-use",
    )
    switch = env[2].post(switch_path, json=switch_body)
    assert switch.status_code == 201, switch.text
    switch = switch.json()
    _, receipt, frozen = _prepared(env, instance, release, material, body["request_key"])
    repeat = _readonly(env, "POST", path, {202}, evidence, "same_key_same_body", body=body)
    assert repeat.json()["run_id"] == receipt["run_id"]
    _readonly(
        env,
        "POST",
        path,
        {409},
        evidence,
        "same_key_changed_input",
        body={**body, "column": "amount"},
    )
    _readonly(
        env,
        "POST",
        switch_path,
        {409},
        evidence,
        "active_use_refuses_new_adoption_approval",
        body={**switch_body, "request_key": "must-not-create-active-switch"},
    )
    commit_path = f"/api/internal/instances/{iid}/csv-full-report-switch-requests/{switch_body['request_key']}/commit"
    _readonly(
        env,
        "POST",
        commit_path,
        {409},
        evidence,
        "active_use_refuses_prior_adoption_commit",
        body={"fingerprint": switch["fingerprint"]},
    )
    _cancel_metadata(env, receipt["run_id"], evidence, "cancel_original_instance_use")
    _readonly(
        env,
        "POST",
        f"/api/runs/{receipt['run_id']}/confirm-csv-report",
        {409},
        evidence,
        "cancelled_run_refuses_stale_confirmation",
        body=_confirmation(frozen, "must-not-confirm-cancelled"),
    )
    assert not Worker(env[0], env[1], NoModel()).once()
    # The same exact switch becomes usable after metadata cancellation, proving
    # the denial was the active-use fence rather than a broken switch fixture.
    allowed = env[2].post(commit_path, json={"fingerprint": switch["fingerprint"]})
    evidence["exact_adoption_after_cancel"] = _answer(allowed)
    assert allowed.status_code == 200, allowed.text
    actual = env[2].get("/api/internal/instances/" + iid)
    assert actual.status_code == 200, actual.text
    assert actual.json()["revision"] == 2 and actual.json()["release_id"] == target["id"]
    _no_models_or_instance_success(env, iid)


def test_changed_data_version_refuses_confirm_or_claim_without_tools_and_keeps_metadata_cancel(
    env, evidence
):
    _, _, _, material, release, instance, _, _, _ = delivered(env)
    iid = instance["id"]
    # First phase demonstrates cancellation remains usable while CAS is stale.
    _, receipt, frozen = _prepared(env, instance, release, material, "cancel-stale-version")
    with env[0].tx() as connection:
        connection.execute(
            update(internal_instances).where(internal_instances.c.id == iid).values(data_version=1)
        )
    _readonly(
        env,
        "POST",
        f"/api/runs/{receipt['run_id']}/confirm-csv-report",
        {409},
        evidence,
        "stale_data_version_refuses_confirmation",
        body=_confirmation(frozen, "stale-confirm"),
    )
    _cancel_metadata(env, receipt["run_id"], evidence, "cancel_while_cas_stale")
    with env[0].tx() as connection:
        connection.execute(
            update(internal_instances).where(internal_instances.c.id == iid).values(data_version=0)
        )

    # Second phase is an actually queued Run; the real Worker must decline the
    # claim before any new tool or instance ledger write. Do not assume FAILED:
    # record the authoritative status and cancel if it remains cancellable.
    _, queued, frozen = _prepared(env, instance, release, material, "claim-stale-version")
    confirmed = env[2].post(
        f"/api/runs/{queued['run_id']}/confirm-csv-report",
        json=_confirmation(frozen, "confirm-before-cas-drift"),
    )
    assert confirmed.status_code == 200, confirmed.text
    with env[0].tx() as connection:
        connection.execute(
            update(internal_instances).where(internal_instances.c.id == iid).values(data_version=1)
        )
    assert not Worker(env[0], env[1], NoModel()).once()
    with env[0].tx() as connection:
        state = dict(
            connection.execute(
                select(runs.c.status, runs.c.version, runs.c.fence, runs.c.error).where(
                    runs.c.id == queued["run_id"]
                )
            )
            .mappings()
            .one()
        )
        assert (
            connection.execute(
                select(operations.c.id).where(operations.c.run_id == queued["run_id"])
            ).first()
            is None
        )
        assert (
            connection.execute(
                select(events.c.id).where(
                    events.c.run_id == queued["run_id"], events.c.kind == "CLAIMED"
                )
            ).first()
            is None
        )
    evidence["actual_scope_rejected_claim"] = state
    assert state["status"] not in {"RUNNING", "SUCCEEDED"} and state["fence"] == 0
    if state["status"] in {
        "QUEUED",
        "PAUSED",
        "WAITING_RESOURCE",
        "RECONCILING",
        "WAITING_APPROVAL",
    }:
        _cancel_metadata(env, queued["run_id"], evidence, "cancel_after_rejected_claim")
    else:
        evidence["claim_already_terminal"] = state["status"]
    _no_models_or_instance_success(env, iid)
