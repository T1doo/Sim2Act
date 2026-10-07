"""Fresh heads after private origin reuse; no transaction-local trust shortcut."""

import copy

import pytest
from sqlalchemy import select, update
from test_conditional_apps import saved
from test_conditional_run_bindings import env as bounded_env

from sim2act import conditional_apps as named
from sim2act.db import events, fingerprint, grants, meta, protocol_jobs, resources, runs


@pytest.fixture
def env(env):
    return bounded_env.__wrapped__(env)


def whole_database(store):
    with store.tx() as c:
        return fingerprint(
            {
                table.name: sorted(
                    [dict(row) for row in c.execute(select(table)).mappings()], key=fingerprint
                )
                for table in meta.sorted_tables
            }
        )


def mutate(c, parent, plan, damage):
    eid = parent["candidate"]["origin"]["extraction_run_id"]
    if damage == "source":
        c.execute(update(runs).where(runs.c.id == plan["source_run_id"]).values(result={}))
    elif damage == "extraction":
        row = c.execute(select(protocol_jobs).where(protocol_jobs.c.run_id == eid)).mappings().one()
        result = copy.deepcopy(row["result_snapshot"])
        result["compiled_plan"]["compiler_version"] = "changed"
        c.execute(
            update(protocol_jobs)
            .where(protocol_jobs.c.run_id == eid)
            .values(result_snapshot=result)
        )
    elif damage == "seal":
        row = (
            c.execute(
                select(events).where(events.c.run_id == eid, events.c.kind == "PROTOCOL_ACCEPTED")
            )
            .mappings()
            .one()
        )
        seal = copy.deepcopy(row["data"])
        seal["accepted_snapshot_fingerprint"] = "0" * 64
        c.execute(update(events).where(events.c.id == row["id"]).values(data=seal))
    elif damage == "grant":
        c.execute(
            update(grants)
            .where(
                grants.c.project_id == parent["project_id"],
                grants.c.resource_id == parent["candidate"]["origin"]["target_resource_id"],
            )
            .values(revoked=True)
        )
    elif damage == "target":
        c.execute(
            update(resources)
            .where(resources.c.id == parent["candidate"]["origin"]["target_resource_id"])
            .values(hash="0" * 64)
        )
    else:
        raise AssertionError(damage)


@pytest.mark.parametrize("damage", ["source", "extraction", "seal", "grant", "target"])
@pytest.mark.parametrize("operation", ["new", "cached", "read"])
def test_post_origin_same_transaction_mutation_rejects_without_writes(
    env, tmp_path, monkeypatch, damage, operation
):
    parent, _, wires = saved(env, tmp_path)
    path = f"/api/projects/{env[5]}/conditional-apps/{parent['id']}/manifest-preview"
    body = dict(expected_app_fingerprint=parent["fingerprint"], request_key="origin")
    app = None
    if operation != "new":
        accepted = env[2].post(path, json=body)
        assert accepted.status_code == 201, accepted.text
        app = accepted.json()
    before = whole_database(env[0])
    original = named._load_validated_origin
    reached = []

    def changed(store, c, user, pid, aid):
        result = original(store, c, user, pid, aid)
        reached.append(aid)
        mutate(c, result[0], result[1], damage)
        return result

    monkeypatch.setattr(named, "_load_validated_origin", changed)
    response = (
        env[2].get(f"/api/projects/{env[5]}/apps/{app['id']}")
        if operation == "read"
        else env[2].post(path, json=body)
    )
    assert reached == [parent["id"]]
    assert response.status_code in {400, 403, 409}, response.text
    assert response.json()["error"]["code"] in {
        "PERMISSION_DENIED",
        "GRANT_REVOKED",
        "VERSION_CONFLICT",
        "VERIFICATION_FAILED",
    }
    assert (
        whole_database(env[0]) == before
    )  # Injection rolls back along with rejected business work.
    assert len(wires) == 3


@pytest.mark.parametrize("damage", ["source", "extraction", "seal", "grant", "target"])
def test_cached_new_http_request_revalidates_current_origin(env, tmp_path, damage):
    parent, _, wires = saved(env, tmp_path)
    path = f"/api/projects/{env[5]}/conditional-apps/{parent['id']}/manifest-preview"
    body = dict(expected_app_fingerprint=parent["fingerprint"], request_key="origin")
    app = env[2].post(path, json=body)
    assert app.status_code == 201, app.text
    with env[0].tx() as c:
        current_parent, plan, _ = named._load_validated_origin(
            env[0], c, env[3], env[5], parent["id"]
        )
        mutate(c, current_parent, plan, damage)
    before = whole_database(env[0])
    response = env[2].post(path, json=body)
    assert response.status_code in {400, 403, 409}, response.text
    assert response.json()["error"]["code"] in {
        "PERMISSION_DENIED",
        "GRANT_REVOKED",
        "VERSION_CONFLICT",
        "VERIFICATION_FAILED",
    }
    assert whole_database(env[0]) == before
    assert len(wires) == 3


@pytest.mark.parametrize("operation", ["new", "cached", "read"])
def test_wrong_named_scope_is_never_reused(env, tmp_path, monkeypatch, operation):
    parent, _, wires = saved(env, tmp_path)
    path = f"/api/projects/{env[5]}/conditional-apps/{parent['id']}/manifest-preview"
    body = dict(expected_app_fingerprint=parent["fingerprint"], request_key="origin")
    app = None
    if operation != "new":
        response = env[2].post(path, json=body)
        assert response.status_code == 201, response.text
        app = response.json()
    before = whole_database(env[0])
    original = named._load_validated_origin

    def wrong(store, c, user, pid, aid):
        parent, plan, job = original(store, c, user, pid, aid)
        return {**parent, "id": "app_" + "0" * 32}, plan, job

    monkeypatch.setattr(named, "_load_validated_origin", wrong)
    response = (
        env[2].get(f"/api/projects/{env[5]}/apps/{app['id']}")
        if operation == "read"
        else env[2].post(path, json=body)
    )
    assert response.status_code == 409, response.text
    assert whole_database(env[0]) == before
    assert len(wires) == 3
