"""Existing authenticated HTTP routes with explicit frozen offline Replay, no Grant changes."""

import copy

import pytest
from sqlalchemy import select, update
from test_bounded_agent_apps import limits, replay, setup
from test_executor_family_provenance import effects

from sim2act import app_jobs
from sim2act.db import Store, fingerprint, grants, internal_app_runs, internal_run_bindings, runs
from sim2act.worker import Worker


def body_for(env, instance, release, rid, value, key="http-replay"):
    return {
        "expected_revision": instance["revision"],
        "expected_release_fingerprint": release["fingerprint"],
        "request_key": key,
        "input": {"term": value["term"]},
        "offline_replay": replay(rid, value).responses,
    }


def test_agent_http_approval_cold_default_worker_and_history_no_grants(env):
    _, ids, _, aid, cand, _, _, value = setup(env)
    client = env[2]
    before = effects(env[0])["grants"]
    approval = client.post(
        f"/api/internal/apps/{aid}/release-approvals",
        json={
            "expected_draft_fingerprint": fingerprint(cand),
            "sample_input": {"term": value["term"]},
            "offline_replay": replay(ids[0], value).responses,
        },
    )
    assert approval.status_code == 201, approval.text
    detail = client.get(f"/api/internal/approvals/{approval.json()['id']}").json()
    evidence = detail["payload"]["snapshot"]["check_evidence"]
    assert evidence["execution_mode"] == "OFFLINE_REPLAY_ONLY"
    assert evidence["semantic_status"] == "UNKNOWN"
    assert evidence["offline_replay_fingerprint"] == fingerprint(replay(ids[0], value).responses)
    rel = client.post(
        f"/api/internal/approvals/{detail['id']}/commit",
        json={"fingerprint": detail["fingerprint"]},
    ).json()
    inst = client.post(
        f"/api/internal/releases/{rel['id']}/instances",
        json={
            "expected_release_fingerprint": rel["fingerprint"],
            "request_key": "new-agent-ui-instance",
        },
    ).json()
    body = body_for(env, inst, rel, ids[0], value)
    queued = client.post(f"/api/internal/instances/{inst['id']}/runs", json=body)
    assert queued.status_code == 202, queued.text
    cold = Store(env[1].database_url, test_only=True)
    if not env[0].sqlite:
        cold.engine = cold.engine.execution_options(**env[0].engine.get_execution_options())

    class NeverProvider:
        def request(self, *_):
            raise AssertionError("Frozen Replay must take precedence over worker adapter")

    Worker(cold, env[1], NeverProvider()).once()
    result = client.get(f"/api/internal/instances/{inst['id']}/runs/{queued.json()['run_id']}")
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "SUCCEEDED"
    assert result.json()["result"] == value
    assert result.json()["result_version"] == 1
    assert client.post(f"/api/internal/instances/{inst['id']}/runs", json=body).json()["cached"]
    assert len(client.get(f"/api/internal/instances/{inst['id']}").json()["data"]) == 1
    assert effects(env[0])["grants"] == before
    cold.engine.dispose()


@pytest.mark.parametrize("case", ["missing", "one", "extra", "gold", "bytes", "csv"])
def test_http_replay_admission_rejects_before_run_or_approval(env, case):
    _, ids, _, aid, cand, rel, inst, value = setup(env)
    body = body_for(env, inst, rel, ids[0], value)
    if case == "missing":
        body.pop("offline_replay")
    elif case == "one":
        body["offline_replay"] = body["offline_replay"][:1]
    elif case == "extra":
        body["offline_replay"].append(body["offline_replay"][1])
    elif case == "gold":
        body["offline_replay"][1]["gold"] = value
    elif case == "bytes":
        body["offline_replay"][1]["id"] = "x" * 32001
    elif case == "csv":
        with env[0].tx() as c:
            from sim2act.db import app_drafts

            aid = next(
                d["id"]
                for d in c.execute(select(app_drafts)).mappings()
                if d["candidate"]["actions"][0]["executor"]["kind"] == "registered_tool"
            )
            cand = c.execute(
                select(app_drafts.c.candidate).where(app_drafts.c.id == aid)
            ).scalar_one()
        # CSV approval rejects Replay before creating any approval.
        before = effects(env[0])
        response = env[2].post(
            f"/api/internal/apps/{aid}/release-approvals",
            json={
                "expected_draft_fingerprint": fingerprint(cand),
                "sample_input": {"column": "amount"},
                "offline_replay": body["offline_replay"],
            },
        )
        assert response.status_code == 400
        assert effects(env[0]) == before
        return
    before = effects(env[0])
    response = env[2].post(f"/api/internal/instances/{inst['id']}/runs", json=body)
    assert response.status_code in {400, 422}, response.text
    assert effects(env[0]) == before
    prepare = {"expected_draft_fingerprint": fingerprint(cand), "sample_input": body["input"]}
    if "offline_replay" in body:
        prepare["offline_replay"] = body["offline_replay"]
    assert env[2].post(f"/api/internal/apps/{aid}/release-approvals", json=prepare).status_code in {
        400,
        422,
    }
    assert effects(env[0]) == before


@pytest.mark.parametrize("mutation", ["replay", "remove", "inject_legacy"])
def test_frozen_replay_has_independent_accepted_request_anchor(env, mutation):
    _, ids, _, _, _, rel, inst, value = setup(env)
    body = body_for(env, inst, rel, ids[0], value)
    if mutation == "inject_legacy":
        queued = app_jobs.enqueue(
            env[0],
            env[3],
            inst["id"],
            inst["revision"],
            rel["fingerprint"],
            body["input"],
            body["request_key"],
            limits(env),
        )
    else:
        queued = env[2].post(f"/api/internal/instances/{inst['id']}/runs", json=body).json()
    with env[0].tx() as c:
        row = (
            c.execute(
                select(internal_run_bindings).where(
                    internal_run_bindings.c.run_id == queued["run_id"]
                )
            )
            .mappings()
            .one()
        )
        snapshot = copy.deepcopy(row["snapshot"])
        if mutation == "remove":
            snapshot.pop("offline_replay")
        elif mutation == "inject_legacy":
            snapshot["offline_replay"] = body["offline_replay"]
        else:
            snapshot["offline_replay"][1]["id"] = "coherent-binding-rewrite"
        # Mutable snapshot/binding/Run fingerprint rewritten; accepted AppRun fp retained.
        fp = fingerprint(snapshot)
        c.execute(
            update(internal_run_bindings)
            .where(internal_run_bindings.c.run_id == queued["run_id"])
            .values(snapshot=snapshot, fingerprint=fp)
        )
        c.execute(update(runs).where(runs.c.id == queued["run_id"]).values(fingerprint=fp))
    before = effects(env[0])
    response = env[2].get(f"/api/internal/instances/{inst['id']}/runs/{queued['run_id']}")
    assert response.status_code == 409, response.text
    assert effects(env[0]) == before


@pytest.mark.parametrize(
    "case", ["bad_quote", "wrong_tool", "revoke", "foreign", "same_key_other_replay"]
)
def test_http_frozen_replay_permission_idempotency_and_failure_history(env, case):
    _, ids, _, _, _, rel, inst, value = setup(env)
    body = body_for(env, inst, rel, ids[0], value)
    if case == "bad_quote":
        import json

        altered = copy.deepcopy(value)
        altered["citations"][0]["quote"] = "invented"
        body["offline_replay"][1]["choices"][0]["message"]["content"] = json.dumps(altered)
    elif case == "wrong_tool":
        body["offline_replay"][0]["choices"][0]["message"]["tool_calls"][0]["function"]["name"] = (
            "artifact.save_text"
        )
    elif case == "revoke":
        with env[0].tx() as c:
            c.execute(update(grants).where(grants.c.resource_id == ids[0]).values(revoked=True))
    before = effects(env[0])
    headers = {"Authorization": "Bearer synthetic-test-B"} if case == "foreign" else {}
    queued = env[2].post(f"/api/internal/instances/{inst['id']}/runs", json=body, headers=headers)
    if case in {"revoke", "foreign"}:
        assert queued.status_code == 403, queued.text
        assert effects(env[0]) == before
        return
    assert queued.status_code == 202, queued.text
    if case == "same_key_other_replay":
        body["offline_replay"][1]["id"] = "different-replay"
        prior = effects(env[0])
        assert (
            env[2].post(f"/api/internal/instances/{inst['id']}/runs", json=body).status_code == 409
        )
        assert effects(env[0]) == prior
        return
    Worker(env[0], env[1]).once()
    response = (
        env[2].get(f"/api/internal/instances/{inst['id']}/runs/{queued.json()['run_id']}").json()
    )
    assert response["status"] == "FAILED" and response["result_version"] is None
    assert effects(env[0])["internal_instance_data"] == before["internal_instance_data"]
    with env[0].tx() as c:
        assert (
            c.execute(
                select(internal_app_runs.c.status).where(
                    internal_app_runs.c.id == queued.json()["app_run_id"]
                )
            ).scalar_one()
            == "FAILED"
        )


@pytest.mark.parametrize("mutation", ["different_protocol", "numeric_bool"])
def test_commit_requires_exact_accepted_replay_not_only_self_consistent_protocol(env, mutation):
    from sim2act.agent_apps import offline_replay_model
    from sim2act.errors import DomainError

    _, ids, _, _, _, rel, inst, value = setup(env)
    body = body_for(env, inst, rel, ids[0], value)
    body["offline_replay"][0]["created"] = 1
    queued = env[2].post(f"/api/internal/instances/{inst['id']}/runs", json=body).json()
    worker = Worker(env[0], env[1])
    claimed = env[0].claim(worker.id, 30)
    assert claimed["id"] == queued["run_id"]
    plan = app_jobs.prepare_dispatch(worker, claimed)
    different = copy.deepcopy(plan["offline_replay"])
    if mutation == "different_protocol":
        different[0]["choices"][0]["message"]["tool_calls"][0]["id"] = "different-wire-data"
    else:
        plan["offline_replay"][0]["created"] = True
        different = plan["offline_replay"]
    value = app_jobs.compute(plan, offline_replay_model(different), lambda _: plan["source"])
    before = effects(env[0])
    with pytest.raises(DomainError) as caught:
        app_jobs.commit_result(worker, claimed, plan, value)
    assert caught.value.code == "VERSION_CONFLICT"
    assert effects(env[0]) == before


def test_success_cold_read_binds_protocol_to_accepted_replay(env):
    from sim2act.agent_apps import offline_replay_model
    from sim2act.db import operations

    _, ids, _, _, _, rel, inst, value = setup(env)
    body = body_for(env, inst, rel, ids[0], value)
    queued = env[2].post(f"/api/internal/instances/{inst['id']}/runs", json=body).json()
    worker = Worker(env[0], env[1])
    claimed = env[0].claim(worker.id, 30)
    plan = app_jobs.prepare_dispatch(worker, claimed)
    actual = app_jobs.compute(
        plan, offline_replay_model(plan["offline_replay"]), lambda _: plan["source"]
    )
    app_jobs.commit_result(worker, claimed, plan, actual)
    assert (
        env[2].get(f"/api/internal/instances/{inst['id']}/runs/{queued['run_id']}").status_code
        == 200
    )
    alternate = copy.deepcopy(plan)
    alternate["offline_replay"][0]["choices"][0]["message"]["tool_calls"][0]["id"] = (
        "changed-cold-trace"
    )
    app_jobs.compute(
        alternate, offline_replay_model(alternate["offline_replay"]), lambda _: alternate["source"]
    )
    with env[0].tx() as c:
        receipt = copy.deepcopy(
            c.execute(
                select(operations.c.receipt).where(operations.c.id == plan["operation_id"])
            ).scalar_one()
        )
        receipt["protocol"] = alternate["protocol"]
        c.execute(
            update(operations)
            .where(operations.c.id == plan["operation_id"])
            .values(receipt=receipt)
        )
    before = effects(env[0])
    assert (
        env[2].get(f"/api/internal/instances/{inst['id']}/runs/{queued['run_id']}").status_code
        == 409
    )
    assert effects(env[0]) == before


def test_replay_cannot_read_same_user_other_project_material(env):
    import json

    _, ids, _, _, _, rel, inst, value = setup(env)
    project = env[2].post("/api/projects", json={"name": "other synthetic project"}).json()["id"]
    resource = (
        env[2]
        .post(
            f"/api/projects/{project}/resources",
            json={"name": "other.md", "format": "md", "content": "private synthetic other project"},
        )
        .json()["id"]
    )
    body = body_for(env, inst, rel, ids[0], value)
    body["offline_replay"][0]["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = (
        json.dumps({"resource_id": resource})
    )
    before = effects(env[0])
    queued = env[2].post(f"/api/internal/instances/{inst['id']}/runs", json=body)
    assert queued.status_code == 202
    Worker(env[0], env[1]).once()
    result = (
        env[2].get(f"/api/internal/instances/{inst['id']}/runs/{queued.json()['run_id']}").json()
    )
    assert result["status"] == "FAILED" and result["result"] is None
    assert effects(env[0])["internal_instance_data"] == before["internal_instance_data"]
    assert effects(env[0])["grants"] == before["grants"]


def test_actual_expired_agent_approval_cannot_create_release(env, monkeypatch):
    _, ids, _, aid, cand, _, _, value = setup(env)
    approval = (
        env[2]
        .post(
            f"/api/internal/apps/{aid}/release-approvals",
            json={
                "expected_draft_fingerprint": fingerprint(cand),
                "sample_input": {"term": value["term"]},
                "offline_replay": replay(ids[0], value).responses,
            },
        )
        .json()
    )
    before = effects(env[0])
    detail = env[2].get(f"/api/internal/approvals/{approval['id']}").json()
    monkeypatch.setattr("sim2act.lifecycle.time.time", lambda: detail["expires_at"] + 1)
    response = env[2].post(
        f"/api/internal/approvals/{approval['id']}/commit",
        json={"fingerprint": approval["fingerprint"]},
    )
    assert response.status_code == 409, response.text
    assert effects(env[0]) == before
