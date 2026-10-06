"""Actual authenticated internal HTTP chain; no models, external data or publication."""

import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from test_internal_lifecycle import limits, setup_draft
from test_persistent_app_runs import NoModel

from sim2act.api import create_app
from sim2act.db import (
    Store,
    app_drafts,
    grants,
    internal_approvals,
    internal_instances,
    principals,
)
from sim2act.lifecycle import commit_switch, prepare_switch
from sim2act.worker import Worker


def prepare(env, aid=None, fp=None):
    if aid is None:
        aid, fp = setup_draft(env)
    r = env[2].post(
        f"/api/internal/apps/{aid}/release-approvals",
        json={"expected_draft_fingerprint": fp, "sample_input": {"column": "amount"}},
    )
    assert r.status_code == 201, r.text
    return r.json(), aid, fp


def release(env, aid=None, fp=None):
    a, aid, fp = prepare(env, aid, fp)
    detail = env[2].get("/api/internal/approvals/" + a["id"])
    assert detail.status_code == 200, detail.text
    assert detail.json()["payload"]["snapshot"]["check_evidence"]["status"] == "PASS"
    assert detail.json()["fingerprint"] == a["fingerprint"]
    r = env[2].post(
        "/api/internal/approvals/" + a["id"] + "/commit", json={"fingerprint": a["fingerprint"]}
    )
    assert r.status_code == 200, r.text
    return r.json(), aid, fp


def instance(env, r, key="instance"):
    response = env[2].post(
        f"/api/internal/releases/{r['id']}/instances",
        json={
            "expected_release_fingerprint": r["fingerprint"],
            "request_key": key,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def enqueue(env, i, r, key="run", column="amount", **extra):
    return env[2].post(
        f"/api/internal/instances/{i['id']}/runs",
        json={
            "expected_release_fingerprint": r["fingerprint"],
            "expected_revision": i["revision"],
            "input": {"column": column},
            "request_key": key,
            **extra,
        },
    )


def path(i, job):
    return f"/api/internal/instances/{i['id']}/runs/{job['run_id']}"


def test_http_exact_approval_instance_enqueue_worker_reopen_no_grant(env):
    aid, fp = setup_draft(env)
    with env[0].tx() as c:
        before = [dict(x) for x in c.execute(select(grants).order_by(grants.c.id)).mappings()]
        principal_before = c.execute(select(func.count()).select_from(principals)).scalar_one()
    r, _, _ = release(env, aid, fp)
    i = instance(env, r)
    queued = enqueue(env, i, r)
    assert queued.status_code == 202, queued.text
    job = queued.json()
    assert job["formal_publication_enabled"] is False
    assert Worker(env[0], env[1], NoModel()).once()
    response = env[2].get(path(i, job)).json()
    assert response["status"] == "SUCCEEDED" and response["result"]["sum"] == "4.00"
    assert response["result_version"] == 1 and response["cancel_intent"] is False
    cold = Store(env[1].database_url, test_only=True)
    if not cold.sqlite:
        cold.engine = cold.engine.execution_options(**env[0].engine.get_execution_options())
    with TestClient(create_app(cold, env[1])) as client:
        client.headers.update({"Authorization": "Bearer synthetic-test-A"})
        snapshot = client.get("/api/internal/instances/" + i["id"]).json()
        assert snapshot["data"][0]["data"]["result"] == response["result"]
        assert snapshot["runs"][0]["id"] == job["run_id"]
    cold.engine.dispose()
    assert len(env[2].get(f"/api/internal/apps/{aid}/releases").json()["items"]) == 1
    assert len(env[2].get(f"/api/internal/apps/{aid}/instances").json()["items"]) == 1
    with env[0].tx() as c:
        assert before == [
            dict(x) for x in c.execute(select(grants).order_by(grants.c.id)).mappings()
        ]
        assert (
            principal_before == c.execute(select(func.count()).select_from(principals)).scalar_one()
        )
    assert env[2].post("/api/publish", json={}).status_code == 404


def test_repeat_approval_instance_run_concurrency_and_changed_fingerprint(env):
    a, aid, fp = prepare(env)
    body = {"fingerprint": a["fingerprint"]}
    url = f"/api/internal/approvals/{a['id']}/commit"
    assert env[2].post(url, json={"fingerprint": "0" * 64}).status_code == 409
    saved = env[2].post(url, json=body).json()
    assert env[2].post(url, json=body).json()["id"] == saved["id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        items = list(pool.map(lambda _: instance(env, saved), range(2)))
    assert items[0]["id"] == items[1]["id"]
    i = items[0]
    assert (
        env[2]
        .post(
            f"/api/internal/releases/{saved['id']}/instances",
            json={"expected_release_fingerprint": "0" * 64, "request_key": "instance"},
        )
        .status_code
        == 409
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = list(pool.map(lambda _: enqueue(env, i, saved).json(), range(2)))
    assert jobs[0]["run_id"] == jobs[1]["run_id"]
    assert enqueue(env, i, saved, column="missing").status_code == 409
    assert enqueue(env, i, saved, tool_ref="artifact.save_text").status_code == 422
    with env[0].tx() as c:
        assert c.execute(select(func.count()).select_from(internal_instances)).scalar_one() == 1


@pytest.mark.parametrize(
    "endpoint",
    [
        "approval",
        "commit",
        "release",
        "create",
        "releases",
        "instances",
        "instance",
        "enqueue",
        "run",
        "command",
        "control",
    ],
)
def test_no_identity_and_foreign_owner_all_internal_endpoints(env, endpoint):
    r, aid, _ = release(env)
    i = instance(env, r)
    job = enqueue(env, i, r).json()
    urls = {
        "approval": ("GET", f"/api/internal/approvals/{r['approval_id']}", None),
        "commit": (
            "POST",
            f"/api/internal/approvals/{r['approval_id']}/commit",
            {"fingerprint": "0" * 64},
        ),
        "release": ("GET", f"/api/internal/releases/{r['id']}", None),
        "create": (
            "POST",
            f"/api/internal/releases/{r['id']}/instances",
            {"expected_release_fingerprint": r["fingerprint"], "request_key": "other"},
        ),
        "releases": ("GET", f"/api/internal/apps/{aid}/releases", None),
        "instances": ("GET", f"/api/internal/apps/{aid}/instances", None),
        "instance": ("GET", f"/api/internal/instances/{i['id']}", None),
        "enqueue": (
            "POST",
            f"/api/internal/instances/{i['id']}/runs",
            {
                "expected_release_fingerprint": r["fingerprint"],
                "expected_revision": 1,
                "input": {"column": "amount"},
                "request_key": "other",
            },
        ),
        "run": ("GET", path(i, job), None),
        "command": ("POST", path(i, job) + "/commands", {"command": "cancel", "version": 1}),
    }
    urls["control"] = ("GET", path(i, job) + "/control-status", None)
    method, url, body = urls[endpoint]
    for headers in [{}, {"Authorization": "Bearer synthetic-test-B"}]:
        old = dict(env[2].headers)
        env[2].headers.clear()
        env[2].headers.update(headers)
        try:
            response = env[2].request(method, url, json=body)
            assert response.status_code == 403, response.text
            assert "40" not in response.text and r["fingerprint"] not in response.text
        finally:
            env[2].headers.clear()
            env[2].headers.update(old)


@pytest.mark.parametrize("change", ["draft", "grant", "expired"])
def test_approval_precondition_change_http_reject(env, change):
    a, aid, fp = prepare(env)
    with env[0].tx() as c:
        if change == "draft":
            c.execute(update(app_drafts).where(app_drafts.c.id == aid).values(fingerprint="0" * 64))
        elif change == "grant":
            c.execute(update(grants).where(grants.c.project_id == env[5]).values(revision=2))
        else:
            row = (
                c.execute(select(internal_approvals).where(internal_approvals.c.id == a["id"]))
                .mappings()
                .one()
            )
            payload = {**row["payload"], "expires_at": time.time() - 1}
            from sim2act.db import fingerprint

            a["fingerprint"] = fingerprint(payload)
            c.execute(
                update(internal_approvals)
                .where(internal_approvals.c.id == a["id"])
                .values(
                    payload=payload, expires_at=payload["expires_at"], fingerprint=a["fingerprint"]
                )
            )
    assert (
        env[2]
        .post(f"/api/internal/approvals/{a['id']}/commit", json={"fingerprint": a["fingerprint"]})
        .status_code
        == 409
    )


def test_cross_instance_version_pause_resume_cancel_and_revoked_stop(env):
    r, aid, fp = release(env)
    i = instance(env, r)
    other = instance(env, r, key="other")
    job = enqueue(env, i, r).json()
    url = path(i, job)
    foreign = path(other, job)
    assert env[2].get(foreign).status_code == 403
    assert (
        env[2].post(foreign + "/commands", json={"command": "cancel", "version": 1}).status_code
        == 403
    )
    assert (
        env[2].post(url + "/commands", json={"command": "pause", "version": 1}).json()["status"]
        == "PAUSED"
    )
    assert (
        env[2].post(url + "/commands", json={"command": "resume", "version": 1}).status_code == 409
    )
    assert (
        env[2].post(url + "/commands", json={"command": "resume", "version": 2}).json()["status"]
        == "QUEUED"
    )
    new, _, _ = release(env, aid, fp)
    switch = prepare_switch(env[0], env[3], i["id"], new["id"], 1, limits(env))
    commit_switch(env[0], env[3], switch["id"], switch["fingerprint"], limits(env))
    assert enqueue(env, i, r, key="stale").status_code == 409
    with env[0].tx() as c:
        c.execute(update(grants).where(grants.c.project_id == env[5]).values(revoked=True))
    assert env[2].get(url).status_code == 403
    control = env[2].get(url + "/control-status").json()
    assert control["content_access"] is False and control["status"] == "QUEUED"
    assert not {"input", "result", "events", "snapshot", "error"} & set(control)
    assert env[2].get(foreign + "/control-status").status_code == 403
    assert (
        env[2].post(url + "/commands", json={"command": "cancel", "version": 3}).json()["status"]
        == "CANCELLED"
    )
    assert not Worker(env[0], env[1], NoModel()).once()


def test_bad_input_retains_failed_run_and_independent_instance_empty(env):
    r, _, _ = release(env)
    i = instance(env, r)
    other = instance(env, r, key="other")
    job = enqueue(env, i, r, column="missing").json()
    assert Worker(env[0], env[1], NoModel()).once()
    result = env[2].get(path(i, job)).json()
    assert result["status"] == "FAILED" and result["result_version"] is None
    assert env[2].get("/api/internal/instances/" + other["id"]).json()["data"] == []


def test_pg_minimum_role_authenticated_internal_http(env, runtime_role):
    """Internal HTTP create/queue/control/read with actual CRUD-only application DB role."""
    aid, fp = setup_draft(env)
    role_store = Store(runtime_role)
    with TestClient(create_app(role_store, env[1])) as client:
        client.headers.update({"Authorization": "Bearer synthetic-test-A"})
        role_env = (role_store, env[1], client, *env[3:])
        r, _, _ = release(role_env, aid, fp)
        i = instance(role_env, r)
        assert instance(role_env, r)["id"] == i["id"]
        job = enqueue(role_env, i, r).json()
        url = path(i, job)
        assert (
            client.post(url + "/commands", json={"command": "pause", "version": 1}).json()["status"]
            == "PAUSED"
        )
        assert (
            client.post(url + "/commands", json={"command": "resume", "version": 2}).json()[
                "status"
            ]
            == "QUEUED"
        )
        assert Worker(role_store, env[1], NoModel()).once()
        assert client.get(url).json()["status"] == "SUCCEEDED"
        assert client.get("/api/internal/instances/" + i["id"]).json()["data_version"] == 1
        target, _, _ = release(role_env, aid, fp)
        a = client.post(
            f"/api/internal/instances/{i['id']}/switch-approvals",
            json={
                "target_release_id": target["id"],
                "expected_target_fingerprint": target["fingerprint"],
                "expected_revision": 1,
            },
        )
        assert a.status_code == 201, a.text
        switch_url = f"/api/internal/instances/{i['id']}/switch-approvals/{a.json()['id']}"
        assert client.get(switch_url).json()["retained_records"] == 1
        assert (
            client.post(
                switch_url + "/commit", json={"fingerprint": a.json()["fingerprint"]}
            ).status_code
            == 200
        )
        assert client.get("/api/internal/instances/" + i["id"]).json()["revision"] == 2
        assert client.get("/api/internal/instances/" + i["id"]).json()["data_version"] == 1
    role_store.engine.dispose()
