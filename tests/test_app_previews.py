"""F2 engineering subset only; does not mark frozen acceptance cases passed."""

import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from sim2act.api import create_app
from sim2act.db import app_drafts, app_previews, attempts, grants, operations, resources, runs


def draft(env, resource=None):
    store, settings, client, user, other, pid, rid = env
    response = client.post(
        f"/api/projects/{pid}/apps/csv-preview",
        json={
            "name": "Reusable CSV sum",
            "goal": "Sum a chosen numeric column",
            "resource_id": resource or rid,
        },
    )
    assert response.status_code == 201, response.json()
    assert not response.json()["publishable"]
    return response.json()["id"]


def execute(client, aid, column="amount", key="request-one", **extra):
    return client.post(
        f"/api/apps/{aid}/previews",
        json={
            "input": {"column": column, **extra},
            "request_key": key,
        },
    )


def count(store, table):
    with store.engine.connect() as c:
        return c.execute(select(func.count()).select_from(table)).scalar_one()


def test_new_input_new_result_and_persisted_history_without_model_or_business_write(env):
    store, settings, client, user, other, pid, rid = env
    r = client.post(
        f"/api/projects/{pid}/resources",
        json={
            "name": "unseen.csv",
            "format": "csv",
            "content": "amount,quantity\n1.25,7\n2.75,8\n",
        },
    ).json()["id"]
    aid = draft(env, r)
    before = {t.name: count(store, t) for t in [resources, runs, operations, attempts]}
    first = execute(client, aid).json()
    second = execute(client, aid, "quantity", "request-two").json()
    assert first["status"] == second["status"] == "SUCCEEDED"
    assert first["output"]["sum"] == "4.00" and second["output"]["sum"] == "15"
    assert first["id"] != second["id"]
    assert (
        second["output"]["source_hash"]
        == hashlib.sha256(b"amount,quantity\n1.25,7\n2.75,8\n").hexdigest()
    )
    assert second["namespace"] == "PREVIEW" and second["release_id"] is None
    assert second["model_requests"] == second["business_writes"] == 0
    assert before == {t.name: count(store, t) for t in [resources, runs, operations, attempts]}
    with TestClient(create_app(store, settings)) as cold:
        cold.headers.update({"Authorization": "Bearer synthetic-test-A"})
        history = cold.get(f"/api/apps/{aid}").json()["history"]
        assert [r["id"] for r in history] == [second["id"], first["id"]]


def test_request_key_retry_returns_same_execution_and_changed_input_conflicts(env):
    store, _, client, *_ = env
    aid = draft(env)
    first = execute(client, aid).json()
    assert execute(client, aid).json() == first
    assert count(store, app_previews) == 1
    assert execute(client, aid, "other").status_code == 409
    assert count(store, app_previews) == 1


def test_invalid_column_is_failed_history_and_next_request_can_succeed(env):
    store, _, client, *_ = env
    aid = draft(env)
    bad = execute(client, aid, "missing").json()
    assert bad["status"] == "FAILED" and bad["output"] is None
    assert bad["error"]["code"] == "INVALID_INPUT"
    assert execute(client, aid, "missing").json()["id"] == bad["id"]
    assert execute(client, aid, key="new-request").json()["status"] == "SUCCEEDED"
    assert count(store, app_previews) == 2


@pytest.mark.parametrize("scope", ["user", "project", "app"])
def test_scope_revocation_prevents_new_execution_and_history_readback(env, scope):
    store, _, client, user, _, pid, rid = env
    aid = draft(env)
    execute(client, aid)
    with store.tx() as c:
        runtime = c.execute(
            select(app_drafts.c.runtime_id).where(app_drafts.c.id == aid)
        ).scalar_one()
        rows = (
            c.execute(
                select(grants).where(
                    grants.c.resource_id == rid, grants.c.tool_ref == "resource.read"
                )
            )
            .mappings()
            .all()
        )
        g = (
            next(x for x in rows if x["principal_id"] == user)
            if scope == "user"
            else next(x for x in rows if x["principal_id"] == runtime)
            if scope == "app"
            else next(x for x in rows if x["principal_id"].startswith("runtime_"))
        )
        c.execute(update(grants).where(grants.c.id == g["id"]).values(revoked=True))
    assert execute(client, aid, key="after-revoke").status_code == 403
    assert client.get(f"/api/apps/{aid}").status_code == 403
    assert count(store, app_previews) == 1


def test_cross_user_and_project_and_runtime_identity_have_no_execution(env):
    store, _, client, _, _, pid, rid = env
    aid = draft(env)
    other_pid = client.post("/api/projects", json={"name": "separate"}).json()["id"]
    assert (
        client.post(
            f"/api/projects/{other_pid}/apps/csv-preview",
            json={"name": "cross-project", "goal": "denied", "resource_id": rid},
        ).status_code
        == 403
    )
    client.headers.update({"Authorization": "Bearer synthetic-test-B"})
    assert client.get("/api/apps").json()["items"] == []
    assert execute(client, aid).status_code == 403
    assert client.get(f"/api/apps/{aid}").status_code == 403
    with store.engine.connect() as c:
        runtime = c.execute(
            select(app_drafts.c.runtime_id).where(app_drafts.c.id == aid)
        ).scalar_one()
    client.headers.update({"Authorization": "Bearer " + runtime})
    assert client.get("/api/apps").status_code == 403
    assert count(store, app_drafts) == 1 and count(store, app_previews) == 0


@pytest.mark.parametrize("change", ["candidate", "resource", "content_hash"])
def test_changed_candidate_or_resource_cannot_execute(env, change):
    store, _, client, _, _, _, rid = env
    aid = draft(env)
    with store.tx() as c:
        if change == "candidate":
            candidate = dict(
                c.execute(select(app_drafts.c.candidate).where(app_drafts.c.id == aid)).scalar_one()
            )
            candidate["goal"] = {"known": "tampered"}
            c.execute(update(app_drafts).where(app_drafts.c.id == aid).values(candidate=candidate))
        else:
            c.execute(
                update(resources).where(resources.c.id == rid).values(hash="f" * 64)
                if change == "resource"
                else update(resources)
                .where(resources.c.id == rid)
                .values(content="changed-but-old-hash")
            )
    response = execute(client, aid)
    if change == "content_hash":
        assert response.json()["status"] == "FAILED"
        assert response.json()["error"]["code"] == "VERIFICATION_FAILED"
    else:
        assert response.status_code == 409 and count(store, app_previews) == 0


def test_input_cannot_add_executor_or_cross_resource_argument(env):
    store, _, client, *_ = env
    aid = draft(env)
    result = execute(client, aid, script="bad", resource_id="/private/path").json()
    assert result["status"] == "FAILED" and result["error"]["code"] == "INVALID_INPUT"
    assert result["output"] is None
    assert count(store, attempts) == count(store, runs) == 0


def test_input_guidance_lists_numeric_columns_without_cells_or_execution(env):
    store, _, client, _, _, pid, _ = env
    rid = client.post(
        f"/api/projects/{pid}/resources",
        json={"name": "choices.csv", "format": "csv", "content": "label,amount,quantity,bad\nprivate-cell,1.25,7,NaN\nother-cell,2.75,8,2\n"},
    ).json()["id"]
    aid = draft(env, rid)
    before = {t.name: count(store, t) for t in [resources, runs, operations, attempts, app_previews]}
    response = client.get(f"/api/apps/{aid}")
    assert response.status_code == 200
    guidance = response.json()["input_guidance"]
    assert guidance["row_count"] == 2 and guidance["error"] is None
    assert [(c["name"], c["numeric"]) for c in guidance["columns"]] == [
        ("label", False), ("amount", True), ("quantity", True), ("bad", False)
    ]
    assert "private-cell" not in response.text and "other-cell" not in response.text
    assert before == {t.name: count(store, t) for t in [resources, runs, operations, attempts, app_previews]}
    assert execute(client, aid, "amount").json()["output"]["sum"] == "4.00"
    assert execute(client, aid, "quantity", "next").json()["output"]["sum"] == "15"


@pytest.mark.parametrize(
    "content,error,columns,rows",
    [
        ("", True, [], None),
        ("amount,amount\n1,2\n", True, [], None),
        (",amount\nx,2\n", True, [], None),
        ("amount\n1,2\n", True, [], None),
        ("amount\n" + "1\n" * 1001, True, [], None),
        ("amount,missing\n1\n", False, [("amount", True), ("missing", False)], 1),
        ("amount\nInfinity\n", False, [("amount", False)], 1),
        ("amount\n", False, [("amount", True)], 0),
    ],
)
def test_input_guidance_handles_invalid_or_empty_csv_without_new_preview(env, content, error, columns, rows):
    store, _, client, _, _, pid, _ = env
    rid = client.post(
        f"/api/projects/{pid}/resources",
        json={"name": "edge.csv", "format": "csv", "content": content},
    ).json()["id"]
    aid = draft(env, rid)
    response = client.get(f"/api/apps/{aid}")
    assert response.status_code == 200
    guidance = response.json()["input_guidance"]
    assert bool(guidance["error"]) == error
    assert [(c["name"], c["numeric"]) for c in guidance["columns"]] == columns
    assert guidance["row_count"] == rows
    assert count(store, app_previews) == 0


def test_guidance_checks_actual_material_hash_before_exposing_headers(env):
    store, _, client, _, _, _, rid = env
    aid = draft(env)
    with store.tx() as c:
        c.execute(update(resources).where(resources.c.id == rid).values(content="private-header\n1\n"))
    response = client.get(f"/api/apps/{aid}")
    assert response.json()["error"]["code"] == "VERIFICATION_FAILED"
    assert "private-header" not in response.text and count(store, app_previews) == 0
