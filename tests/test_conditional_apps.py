"""Real HTTP receipts, actual mock-transport cold Runs, independent typed-scenario oracle."""

import copy

import pytest
from sqlalchemy import select, update
from test_conditional_run_bindings import env as bounded_env
from test_conditional_run_bindings import envelope, extract_body, facts, get, prepared, work

from sim2act.conditional_apps import NAMESPACE
from sim2act.conditional_runs import SOURCE, candidate_for, contract_snapshot, inputs_for
from sim2act.db import app_drafts, app_previews, grants, principals, protocol_jobs
from sim2act.worker import Worker


@pytest.fixture
def env(env):
    return bounded_env.__wrapped__(env)


def prefix(env):
    return f"/api/projects/{env[5]}/conditional-apps"


def authority(env):
    with env[0].tx() as c:
        return (
            [dict(r) for r in c.execute(select(principals).order_by(principals.c.id)).mappings()],
            [dict(r) for r in c.execute(select(grants).order_by(grants.c.id)).mappings()],
        )


def saved(env, tmp_path):
    rid, source, checked, wires, _ = prepared(env, tmp_path)
    response = env[2].post(
        f"/api/projects/{env[5]}/conditional-runs/extract", json=extract_body(rid, source, checked)
    )
    assert response.status_code == 202, response.text
    eid = response.json()["run_id"]
    work(
        env,
        tmp_path,
        [envelope(candidate_for(contract_snapshot(SOURCE, inputs_for(facts())), env[6]))],
        wires,
    )
    plan = get(env, eid)["result"]["compiled_plan"]
    body = {
        "extraction_run_id": eid,
        "expected_plan_fingerprint": plan["plan_fingerprint"],
        "expected_check_fingerprint": checked["fingerprint"],
        "target_resource_id": env[7],
        "expected_target_hash": contract_snapshot(SOURCE, inputs_for(facts()))["source_hash"],
        "name": "Saved hypothetical travel report",
        "request_key": "save-draft",
    }
    response = env[2].post(prefix(env), json=body)
    assert response.status_code == 201, response.text
    return response.json(), body, wires


def independent_report(states, decision, actions):
    from pathlib import Path

    lines = (
        Path("docs/evidence/model-protocol-preparation-20261006/materials/a-source/policy.txt")
        .read_text()
        .splitlines()
    )
    return {
        "findings": [
            {
                "rule_id": f"R{i}",
                "applies": state,
                "citation": {"line": i + 2, "quote": lines[i + 1]},
            }
            for i, state in enumerate(states, 1)
        ],
        "decision": decision,
        "next_actions": actions,
        "deadline_days": 10,
        "absolute_date": "UNKNOWN",
        "receipt_restarts_deadline": False,
        "explanation": "Independent test response. No business action executed.",
    }


def test_named_draft_two_actual_new_scenarios_history_and_recovery(env, tmp_path):
    before = authority(env)
    draft, saved_body, wires = saved(env, tmp_path)
    assert draft["namespace"] == NAMESPACE and draft["owner_acceptance"] == "PENDING"
    retry = env[2].post(prefix(env), json=saved_body)
    assert retry.status_code == 201 and retry.json()["id"] == draft["id"] and retry.json()["cached"]
    assert draft["id"] not in [x["id"] for x in env[2].get("/api/apps").json()["items"]]
    assert env[2].get("/api/apps/" + draft["id"]).status_code >= 400
    assert (
        env[2]
        .post(
            "/api/apps/" + draft["id"] + "/previews",
            json={"input": {"column": "amount"}, "request_key": "wrong-family"},
        )
        .status_code
        >= 400
    )
    # Fresh client has no source/extraction UI memory; reopen solely by persisted app ID.
    from fastapi.testclient import TestClient

    fresh = TestClient(env[2].app)
    fresh.headers.update({"Authorization": "Bearer synthetic-test-A"})
    reopened = fresh.get(prefix(env) + "/" + draft["id"])
    assert reopened.status_code == 200 and reopened.json()["fingerprint"] == draft["fingerprint"]
    cases = [
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
    for index, (scenario, output) in enumerate(cases):
        body = {
            "expected_app_fingerprint": draft["fingerprint"],
            "scenario": scenario,
            "request_key": f"new-scenario-{index}",
        }
        accepted = fresh.post(prefix(env) + "/" + draft["id"] + "/runs", json=body)
        assert accepted.status_code == 202, accepted.text
        rid = accepted.json()["run_id"]
        ids.append(rid)
        assert (
            fresh.post(prefix(env) + "/" + draft["id"] + "/runs", json=body).json()["run_id"] == rid
        )
        work(env, tmp_path, [envelope(output)], wires)
        actual = get(env, rid)
        assert actual["result"]["protocol_result"]["evidence"]["output"] == output
        assert actual["status"] == "WAITING_APPROVAL" and actual["semantic_status"] == "UNKNOWN"
        check = fresh.post(
            f"/api/projects/{env[5]}/conditional-runs/{rid}/checks",
            json={
                "expected_result_fingerprint": actual["result_fingerprint"],
                "expected_version": actual["version"],
                "expected_fence": actual["fence"],
                "request_key": f"check-{index}",
            },
        )
        assert (
            check.status_code == 201 and check.json()["value"]["checks"]["check_status"] == "PASS"
        ), check.text
    assert len(set(ids)) == 2
    history = fresh.get(prefix(env) + "/" + draft["id"] + "/history")
    assert history.status_code == 200, history.text
    assert {x["run"]["run_id"] for x in history.json()["items"]} == set(ids)
    assert {
        x["run"]["result"]["protocol_result"]["evidence"]["output"]["decision"]
        for x in history.json()["items"]
    } == {"ALLOW", "BLOCK"}
    assert authority(env) == before
    fresh.close()


@pytest.mark.parametrize(
    "extra", ["candidate", "report", "gold", "replay", "runtime_id", "permissions"]
)
def test_closed_save_and_run_payloads(env, tmp_path, extra):
    draft, body, _ = saved(env, tmp_path)
    assert env[2].post(prefix(env), json={**body, extra: {}}).status_code == 422
    request = {
        "expected_app_fingerprint": draft["fingerprint"],
        "scenario": facts(500),
        "request_key": "closed",
    }
    assert (
        env[2]
        .post(prefix(env) + "/" + draft["id"] + "/runs", json={**request, extra: {}})
        .status_code
        == 422
    )


def test_project_identity_and_hash_boundaries(env, tmp_path):
    draft, body, _ = saved(env, tmp_path)
    assert env[2].post(prefix(env), json={**body, "name": "changed"}).status_code == 409
    other = env[2].post("/api/projects", json={"name": "other own project"}).json()["id"]
    assert env[2].get(f"/api/projects/{other}/conditional-apps/" + draft["id"]).status_code == 403
    env[2].headers.update({"Authorization": "Bearer synthetic-test-B"})
    assert env[2].get(prefix(env) + "/" + draft["id"]).status_code == 403
    env[2].headers.update({"Authorization": "Bearer synthetic-test-A"})
    assert (
        env[2]
        .post(
            prefix(env),
            json={**body, "request_key": "wrong-target", "expected_target_hash": "0" * 64},
        )
        .status_code
        == 409
    )
    with env[0].tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == env[7]).values(revoked=True))
    assert env[2].get(prefix(env) + "/" + draft["id"]).status_code == 403
    assert env[2].get(prefix(env) + "/" + draft["id"] + "/history").status_code == 403


def test_default_worker_has_no_provider_and_lost_receipt_recovery_sends_zero(env, tmp_path):
    draft, _, wires = saved(env, tmp_path)
    before = authority(env)
    body = {
        "expected_app_fingerprint": draft["fingerprint"],
        "scenario": facts(500),
        "request_key": "default",
    }
    reply = env[2].post(prefix(env) + "/" + draft["id"] + "/runs", json=body)
    assert reply.status_code == 202
    assert Worker(env[0], env[1]).once()
    assert get(env, reply.json()["run_id"])["status"] == "WAITING_RESOURCE"
    assert (
        env[2].post(prefix(env) + "/" + draft["id"] + "/runs", json=body).json()["run_id"]
        == reply.json()["run_id"]
    )
    assert len(wires) == 3 and authority(env) == before
    assert (
        env[2]
        .post(prefix(env) + "/" + draft["id"] + "/runs", json={**body, "scenario": facts(700)})
        .status_code
        == 409
    )


@pytest.mark.parametrize("target", ["draft", "plan", "history"])
def test_rehashed_tamper_does_not_create_trusted_history(env, tmp_path, target):
    from sim2act.db import fingerprint

    draft, body, _ = saved(env, tmp_path)
    if target == "history":
        request = {
            "expected_app_fingerprint": draft["fingerprint"],
            "scenario": facts(500),
            "request_key": "history",
        }
        assert (
            env[2].post(prefix(env) + "/" + draft["id"] + "/runs", json=request).status_code == 202
        )
    with env[0].tx() as c:
        if target == "draft":
            row = (
                c.execute(select(app_drafts).where(app_drafts.c.id == draft["id"])).mappings().one()
            )
            bad = copy.deepcopy(row["candidate"])
            bad["permissions"]["tool_refs"].append("artifact.save_text")
            c.execute(
                update(app_drafts)
                .where(app_drafts.c.id == draft["id"])
                .values(candidate=bad, fingerprint=fingerprint(bad))
            )
        elif target == "plan":
            row = (
                c.execute(
                    select(protocol_jobs).where(protocol_jobs.c.run_id == body["extraction_run_id"])
                )
                .mappings()
                .one()
            )
            bad = copy.deepcopy(row["result_snapshot"])
            bad["compiled_plan"]["candidate"]["steps"][0]["tool_ref"] = "artifact.save_text"
            c.execute(
                update(protocol_jobs)
                .where(protocol_jobs.c.run_id == body["extraction_run_id"])
                .values(result_snapshot=bad)
            )
        else:
            row = (
                c.execute(select(app_previews).where(app_previews.c.app_id == draft["id"]))
                .mappings()
                .one()
            )
            bad = copy.deepcopy(row["input"])
            bad["scenario"]["amount"] = 700
            c.execute(
                update(app_previews)
                .where(app_previews.c.id == row["id"])
                .values(
                    input=bad,
                    fingerprint=fingerprint({"namespace": NAMESPACE, "app_id": draft["id"], **bad}),
                )
            )
    response = env[2].get(
        prefix(env) + "/" + draft["id"] + ("/history" if target == "history" else "")
    )
    assert response.status_code >= 400, response.text


def test_same_payload_different_run_cannot_replace_history_receipt(env, tmp_path):
    draft, _, _ = saved(env, tmp_path)
    path = prefix(env) + "/" + draft["id"] + "/runs"
    body = {
        "expected_app_fingerprint": draft["fingerprint"],
        "scenario": facts(500),
        "request_key": "first",
    }
    first = env[2].post(path, json=body).json()["run_id"]
    second = env[2].post(path, json={**body, "request_key": "second"}).json()["run_id"]
    assert first != second
    with env[0].tx() as c:
        c.execute(
            update(app_previews)
            .where(app_previews.c.app_id == draft["id"], app_previews.c.request_key == "first")
            .values(output={"namespace": NAMESPACE, "run_id": second})
        )
    assert env[2].get(prefix(env) + "/" + draft["id"] + "/history").status_code == 409


@pytest.mark.parametrize("ref", [6, 7])
def test_source_or_target_revoke_prevents_new_run_and_protected_history(env, tmp_path, ref):
    draft, _, wires = saved(env, tmp_path)
    with env[0].tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == env[ref]).values(revoked=True))
    request = {
        "expected_app_fingerprint": draft["fingerprint"],
        "scenario": facts(500),
        "request_key": "revoked",
    }
    assert env[2].post(prefix(env) + "/" + draft["id"] + "/runs", json=request).status_code == 403
    assert env[2].get(prefix(env) + "/" + draft["id"] + "/history").status_code == 403
    assert len(wires) == 3


@pytest.mark.parametrize("damage", ["row_key", "missing_origin_field", "boolean_wrapper_version"])
def test_final_frozen_key_and_wrapper_hardening(env, tmp_path, damage):
    from sim2act.db import fingerprint, task_extractions

    draft, _, _ = saved(env, tmp_path)
    if damage == "row_key":
        request = {
            "expected_app_fingerprint": draft["fingerprint"],
            "scenario": facts(500),
            "request_key": "original",
        }
        assert (
            env[2].post(prefix(env) + "/" + draft["id"] + "/runs", json=request).status_code == 202
        )
        with env[0].tx() as c:
            c.execute(
                update(app_previews)
                .where(app_previews.c.app_id == draft["id"])
                .values(request_key="different-row-key")
            )
        response = env[2].get(prefix(env) + "/" + draft["id"] + "/history")
    else:
        with env[0].tx() as c:
            row = (
                c.execute(select(app_drafts).where(app_drafts.c.id == draft["id"])).mappings().one()
            )
            bad = copy.deepcopy(row["candidate"])
            if damage == "missing_origin_field":
                del bad["origin"]["extraction_run_id"]
            else:
                bad["version"] = True
            fp = fingerprint(bad)
            c.execute(
                update(app_drafts)
                .where(app_drafts.c.id == draft["id"])
                .values(candidate=bad, fingerprint=fp)
            )
            c.execute(
                update(task_extractions)
                .where(task_extractions.c.app_id == draft["id"])
                .values(snapshot={"kind": NAMESPACE, "wrapper": bad, "wrapper_fingerprint": fp})
            )
        response = env[2].get(prefix(env) + "/" + draft["id"])
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "VERSION_CONFLICT"
