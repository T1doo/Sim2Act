"""Real canonical AppManifest private preview, not a structural-label acceptance."""

import copy
import json

import pytest
from sqlalchemy import select, update
from test_conditional_apps import authority, independent_report, saved
from test_conditional_run_bindings import env as bounded_env
from test_conditional_run_bindings import envelope, facts, get, work

from sim2act.apps import compile_preview
from sim2act.contracts import schema_check, validate_manifest, validate_value
from sim2act.db import app_drafts, app_previews, fingerprint, protocol_jobs, task_extractions
from sim2act.errors import DomainError
from sim2act.report_manifest_apps import NAMESPACE, scenario_schema


@pytest.fixture
def env(env):
    return bounded_env.__wrapped__(env)


def promoted(env, tmp_path):
    named, _, wires = saved(env, tmp_path)
    body = {"expected_app_fingerprint": named["fingerprint"], "request_key": "manifest"}
    path = f"/api/projects/{env[5]}/conditional-apps/{named['id']}/manifest-preview"
    response = env[2].post(path, json=body)
    assert response.status_code == 201, response.text
    return response.json(), named, path, body, wires


def preview_path(env, aid):
    return f"/api/projects/{env[5]}/apps/{aid}/previews"


def test_real_common_manifest_compiler_catalog_and_two_actual_cold_scenarios(env, tmp_path):
    before = authority(env)
    app, parent, promotion, body, wires = promoted(env, tmp_path)
    assert app["namespace"] == NAMESPACE and app["state"] == "PREVIEW_ONLY"
    assert env[2].post(promotion, json=body).json()["id"] == app["id"]
    manifest = validate_manifest(json.dumps(app["candidate"]["manifest"]))
    compiled, action, report = compile_preview(app["candidate"], manifest.runtime_limits)
    assert compiled == manifest and action.executor.kind == "bounded_report"
    assert compiled.runtime_identity_requirements.mode == "user_and_project_intersection"
    assert report["topological_order"] == ["report"] and report["execution_performed"] is False
    assert app["id"] in [x["id"] for x in env[2].get("/api/apps").json()["items"]]
    assert env[2].get("/api/apps/" + app["id"]).json()["candidate"] == app["candidate"]
    from fastapi.testclient import TestClient

    fresh = TestClient(env[2].app)
    fresh.headers.update({"Authorization": "Bearer synthetic-test-A"})
    reopened = fresh.get(f"/api/projects/{env[5]}/apps/" + app["id"])
    assert reopened.status_code == 200 and reopened.json()["history"] == []
    reports = [
        (
            facts(500),
            independent_report(("TRUE", "FALSE", "FALSE"), "ALLOW", ["submit_claim_and_receipt"]),
        ),
        (
            facts(680, receipt_present=False),
            independent_report(
                ("TRUE", "TRUE", "TRUE"), "BLOCK", ["obtain_receipt", "obtain_prior_approval"]
            ),
        ),
    ]
    ids = []
    for i, (scenario, output) in enumerate(reports):
        request = {
            "expected_candidate_fingerprint": app["fingerprint"],
            "input": scenario,
            "request_key": f"cold-{i}",
        }
        accepted = fresh.post(preview_path(env, app["id"]), json=request)
        assert accepted.status_code == 202, accepted.text
        rid = accepted.json()["run_id"]
        ids.append(rid)
        assert fresh.post(preview_path(env, app["id"]), json=request).json()["run_id"] == rid
        work(env, tmp_path, [envelope(output)], wires)
        actual = get(env, rid)
        assert actual["result"]["protocol_result"]["evidence"]["output"] == output
        assert (
            actual["status"] == "WAITING_APPROVAL"
            and actual["overall_run_acceptance"] == "NOT_ACCEPTED"
        )
        with env[0].tx() as c:
            job = (
                c.execute(select(protocol_jobs).where(protocol_jobs.c.run_id == rid))
                .mappings()
                .one()
            )
        assert job["accepted_snapshot"]["limits"] == compiled.runtime_limits.model_dump()
        assert (
            json.loads(job["accepted_snapshot"]["payload"]["inputs"]["scenario_json"]) == scenario
        )
        assert "report" not in job["accepted_snapshot"]["payload"]["inputs"]
    history = fresh.get(f"/api/projects/{env[5]}/apps/" + app["id"] + "/history")
    assert history.status_code == 200, history.text
    assert {x["run"]["run_id"] for x in history.json()["history"]} == set(ids) and len(
        set(ids)
    ) == 2
    assert authority(env) == before
    fresh.close()


@pytest.mark.parametrize(
    "damage", ["wiring", "executor", "dependency", "schema", "runtime_mode", "budget"]
)
def test_complete_canonical_binding_rejects_rehashed_candidate_and_marker(env, tmp_path, damage):
    app, _, _, _, _ = promoted(env, tmp_path)
    bad = copy.deepcopy(app["candidate"])
    if damage == "wiring":
        bad["manifest"]["workflow"][0]["inputs"]["amount"] = {
            "source": "input",
            "field": "elapsed_days",
        }
    elif damage == "executor":
        bad["actions"][0]["executor"]["ref"] = "intern.agent"
    elif damage == "dependency":
        bad["manifest"]["dependency_lock"].pop()
    elif damage == "schema":
        bad["manifest"]["input_schema"]["properties"]["amount"]["maximum"] = 1000001
    elif damage == "runtime_mode":
        bad["manifest"]["runtime_identity_requirements"]["mode"] = "user_and_app_intersection"
    else:
        for value in [
            bad["manifest"]["runtime_limits"],
            bad["actions"][0]["limits"],
            bad["report_proof"]["limits"],
        ]:
            value["max_requests"] = 2
    with env[0].tx() as c:
        marker = (
            c.execute(select(task_extractions).where(task_extractions.c.app_id == app["id"]))
            .mappings()
            .one()
        )
        snapshot = copy.deepcopy(marker["snapshot"])
        snapshot["candidate"] = bad
        snapshot["candidate_fingerprint"] = fingerprint(bad)
        c.execute(
            update(app_drafts)
            .where(app_drafts.c.id == app["id"])
            .values(candidate=bad, fingerprint=fingerprint(bad))
        )
        c.execute(
            update(task_extractions)
            .where(task_extractions.c.app_id == app["id"])
            .values(snapshot=snapshot)
        )
    response = env[2].get(f"/api/projects/{env[5]}/apps/" + app["id"])
    assert response.status_code >= 400, response.text


@pytest.mark.parametrize(
    "extra", ["candidate", "report", "gold", "replay", "model", "runtime_id", "permissions"]
)
def test_no_client_program_report_or_authority_fields(env, tmp_path, extra):
    app, _, path, body, _ = promoted(env, tmp_path)
    assert env[2].post(path, json={**body, extra: {}}).status_code == 422
    request = {
        "expected_candidate_fingerprint": app["fingerprint"],
        "input": facts(500),
        "request_key": "strict",
    }
    assert env[2].post(preview_path(env, app["id"]), json={**request, extra: {}}).status_code == 422


def test_projects_identity_versions_history_and_internal_release_are_separate(env, tmp_path):
    app, _, _, _, _ = promoted(env, tmp_path)
    other = env[2].post("/api/projects", json={"name": "different own project"}).json()["id"]
    assert env[2].get(f"/api/projects/{other}/apps/" + app["id"]).status_code == 403
    request = {
        "expected_candidate_fingerprint": app["fingerprint"],
        "input": facts(500),
        "request_key": "history",
    }
    assert (
        env[2]
        .post(f"/api/projects/{other}/apps/" + app["id"] + "/previews", json=request)
        .status_code
        == 403
    )
    env[2].headers.update({"Authorization": "Bearer synthetic-test-B"})
    assert env[2].get("/api/apps/" + app["id"]).status_code == 403
    env[2].headers.update({"Authorization": "Bearer synthetic-test-A"})
    assert (
        env[2]
        .post(
            preview_path(env, app["id"]),
            json={**request, "expected_candidate_fingerprint": "0" * 64},
        )
        .status_code
        == 409
    )
    first = env[2].post(preview_path(env, app["id"]), json=request).json()["run_id"]
    second = (
        env[2]
        .post(preview_path(env, app["id"]), json={**request, "request_key": "second"})
        .json()["run_id"]
    )
    assert first != second
    with env[0].tx() as c:
        c.execute(
            update(app_previews)
            .where(app_previews.c.app_id == app["id"], app_previews.c.request_key == "history")
            .values(output={"namespace": NAMESPACE, "run_id": second})
        )
    assert env[2].get(f"/api/projects/{env[5]}/apps/" + app["id"] + "/history").status_code == 409
    # Old internal lifecycle cannot treat this model-backed preview as CSV or Replay agent.
    assert env[2].get("/api/internal/apps/" + app["id"] + "/releases").status_code >= 400


@pytest.mark.parametrize(
    "schema",
    [
        {"type": "boolean", "nullable": 1},
        {"type": "integer", "nullable": "true"},
        {"type": "string", "nullable": True},
        {"type": "integer", "nullable": True, "anyOf": []},
        {"type": "boolean", "nullable": None},
    ],
)
def test_nullable_does_not_broaden_schema_subset(schema):
    with pytest.raises(DomainError):
        schema_check(schema)


def test_nullable_keeps_enum_and_bool_integer_coercion_closed():
    schema_check(scenario_schema())
    validate_value(scenario_schema(), facts(amount=None, approved=None))
    for value in [True, 1.0, "1"]:
        with pytest.raises(DomainError):
            validate_value({"type": "integer", "nullable": True}, value)
    with pytest.raises(DomainError):
        validate_value({"type": "boolean", "nullable": True, "enum": [True]}, None)
    schema_check({"type": "boolean", "nullable": True, "enum": [True, None]})
    validate_value({"type": "boolean", "nullable": True, "enum": [True, None]}, None)


def test_tightened_platform_refuses_promotion_before_write(env, tmp_path):
    from sim2act.contracts import Limits
    from sim2act.report_manifest_apps import PromoteRequest, promote

    parent, _, _ = saved(env, tmp_path)
    with env[0].tx() as c:
        before = (
            c.execute(select(app_drafts)).mappings().all(),
            c.execute(select(task_extractions)).mappings().all(),
        )
    with pytest.raises(DomainError):
        promote(
            env[0],
            env[3],
            env[5],
            parent["id"],
            PromoteRequest(expected_app_fingerprint=parent["fingerprint"], request_key="lower"),
            Limits(
                **{
                    key: (1 if key == "max_requests" else getattr(env[1], key))
                    for key in Limits.model_fields
                }
            ),
        )
    with env[0].tx() as c:
        after = (
            c.execute(select(app_drafts)).mappings().all(),
            c.execute(select(task_extractions)).mappings().all(),
        )
    assert before == after


def test_existing_pg_crud_role_manifest_preview_without_ddl_or_authority_expansion(
    env, runtime_role, tmp_path
):
    from dataclasses import replace

    from fastapi.testclient import TestClient
    from sqlalchemy import event
    from test_registered_run_generation_pg_role import role_capabilities, schema_objects

    from sim2act.api import create_app
    from sim2act.db import Store, attempts
    from sim2act.worker import Worker

    parent, _, _ = saved(env, tmp_path)  # Explicit owner fixture provisioning only.
    store = Store(runtime_role, test_only=True)
    settings = replace(env[1], database_url=runtime_role)
    client = TestClient(create_app(store, settings))
    client.headers["Authorization"] = "Bearer synthetic-test-A"
    role_env = (store, settings, client, *env[3:])
    verbs = []

    def inspect_statement(_conn, _cursor, statement, _parameters, _context, _many):
        verb = statement.lstrip().split(None, 1)[0].upper()
        verbs.append(verb)
        assert verb not in {"CREATE", "ALTER", "DROP", "GRANT", "REVOKE", "TRUNCATE"}

    event.listen(store.engine, "before_cursor_execute", inspect_statement)
    try:
        assert role_capabilities(store) == dict(
            rolsuper=False, rolcreatedb=False, rolcreaterole=False, schema_create=False
        )
        inventory, before = schema_objects(store), authority(role_env)
        path = f"/api/projects/{env[5]}/conditional-apps/{parent['id']}/manifest-preview"
        reply = client.post(
            path, json=dict(expected_app_fingerprint=parent["fingerprint"], request_key="crud")
        )
        assert reply.status_code == 201, reply.text
        app = reply.json()
        assert client.get(f"/api/projects/{env[5]}/apps/{app['id']}").status_code == 200
        accepted = client.post(
            preview_path(role_env, app["id"]),
            json=dict(
                expected_candidate_fingerprint=app["fingerprint"],
                input=facts(500),
                request_key="crud-preview",
            ),
        )
        assert accepted.status_code == 202, accepted.text
        rid = accepted.json()["run_id"]
        Worker(store, settings).once()
        assert get(role_env, rid)["status"] == "WAITING_RESOURCE"
        with store.tx() as c:
            assert not c.execute(select(attempts).where(attempts.c.run_id == rid)).first()
        assert client.get(f"/api/projects/{env[5]}/apps/{app['id']}/history").status_code == 200
        assert client.get(f"/api/projects/{env[5]}/apps/{parent['id']}").status_code >= 400
        assert schema_objects(store) == inventory and authority(role_env) == before
        assert "INSERT" in verbs and "SELECT" in verbs
    finally:
        client.close()
        store.engine.dispose()
