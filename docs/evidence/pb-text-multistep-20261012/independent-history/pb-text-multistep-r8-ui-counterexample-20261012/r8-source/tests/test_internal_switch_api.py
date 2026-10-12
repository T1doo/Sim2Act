"""Real authenticated switch adapter and retained result/source boundaries."""

import copy
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select, update
from test_internal_api import enqueue, instance, release
from test_internal_lifecycle import limits
from test_persistent_app_runs import NoModel

from sim2act import lifecycle
from sim2act.db import fingerprint, grants, internal_approvals, internal_instances
from sim2act.worker import Worker


def prepare(env, i, target):
    return env[2].post(
        f"/api/internal/instances/{i['id']}/switch-approvals",
        json={
            "target_release_id": target["id"],
            "expected_target_fingerprint": target["fingerprint"],
            "expected_revision": i["revision"],
        },
    )


def path(i, a):
    return f"/api/internal/instances/{i['id']}/switch-approvals/{a['id']}"


def test_http_switch_rollback_preserves_results_grants_history_and_one_shot(env):
    old, aid, fp = release(env)
    i = instance(env, old)
    queued = enqueue(env, i, old).json()
    assert Worker(env[0], env[1], NoModel()).once()
    before = env[2].get(f"/api/internal/instances/{i['id']}").json()
    with env[0].tx() as c:
        grant_before = [dict(x) for x in c.execute(select(grants)).mappings()]
    target, _, _ = release(env, aid, fp)
    for selected in [target, old]:
        a = prepare(env, i, selected)
        assert a.status_code == 201, a.text
        a = a.json()
        detail = env[2].get(path(i, a))
        assert detail.status_code == 200
        assert detail.json()["retained_records"] == 1
        assert detail.json()["data_preserved"] and not detail.json()["new_grants"]
        assert (
            env[2].post(path(i, a) + "/commit", json={"fingerprint": "0" * 64}).status_code == 409
        )
        responses = list(
            ThreadPoolExecutor(2).map(
                lambda _, i=i, a=a: env[2].post(
                    path(i, a) + "/commit", json={"fingerprint": a["fingerprint"]}
                ),
                range(2),
            )
        )
        assert sorted(r.status_code for r in responses) == [200, 409]
        assert env[2].get(path(i, a)).status_code == 409
        i = env[2].get(f"/api/internal/instances/{i['id']}").json()
        assert i["data"] == before["data"] and i["runs"] == before["runs"]
    assert i["revision"] == 3 and len(i["history"]) == 3 and i["release_id"] == old["id"]
    assert i["runs"][0]["id"] == queued["run_id"]
    with env[0].tx() as c:
        assert [dict(x) for x in c.execute(select(grants)).mappings()] == grant_before


@pytest.mark.parametrize(
    "fault",
    ["expired", "missing", "hash", "pointer", "grant", "foreign_app", "bad_type", "bool_revision"],
)
def test_switch_stale_tamper_scope_rejected_without_consumption(env, fault):
    old, aid, fp = release(env)
    target, _, _ = release(env, aid, fp)
    i = instance(env, old)
    a = prepare(env, i, target).json()
    foreign = release(env)[0] if fault == "foreign_app" else None
    with env[0].tx() as c:
        row = (
            c.execute(select(internal_approvals).where(internal_approvals.c.id == a["id"]))
            .mappings()
            .one()
        )
        p = copy.deepcopy(row["payload"])
        if fault == "expired":
            p["expires_at"] = time.time() - 1
        if fault == "bad_type":
            p["target_release_id"] = []
        if fault == "bool_revision":
            p["revision"] = True
        if fault == "missing":
            p.pop("instance_id")
        if fault == "foreign_app":
            p.update(target_release_id=foreign["id"], target_fingerprint=foreign["fingerprint"])
        if fault in ["expired", "missing", "foreign_app", "hash", "bad_type", "bool_revision"]:
            a["fingerprint"] = fingerprint(p) if fault != "hash" else "0" * 64
            c.execute(
                update(internal_approvals)
                .where(internal_approvals.c.id == a["id"])
                .values(payload=p, fingerprint=a["fingerprint"], expires_at=p["expires_at"])
            )
        if fault == "pointer":
            c.execute(
                update(internal_instances)
                .where(internal_instances.c.id == i["id"])
                .values(revision=2)
            )
        if fault == "grant":
            c.execute(update(grants).where(grants.c.project_id == env[5]).values(revoked=True))
    for suffix, method in [("", "get"), ("/commit", "post")]:
        response = getattr(env[2], method)(
            path(i, a) + suffix,
            **({"json": {"fingerprint": a["fingerprint"]}} if method == "post" else {}),
        )
        assert response.status_code in [403, 409], response.text
    with env[0].tx() as c:
        assert not c.execute(
            select(internal_approvals.c.consumed).where(internal_approvals.c.id == a["id"])
        ).scalar_one()
        assert (
            c.execute(
                select(internal_instances.c.release_id).where(internal_instances.c.id == i["id"])
            ).scalar_one()
            == old["id"]
        )
    if fault in ["missing", "foreign_app", "bad_type", "bool_revision"]:
        with pytest.raises(Exception) as error:
            lifecycle.commit_switch(env[0], env[3], a["id"], a["fingerprint"], limits(env))
        assert error.value.__class__.__name__ == "DomainError"


def test_switch_url_instance_owner_target_and_incompatibility(env):
    old, aid, fp = release(env)
    target, _, _ = release(env, aid, fp)
    i, other = instance(env, old), instance(env, old, "other")
    a = prepare(env, i, target).json()
    assert env[2].get(path(other, a)).status_code == 403
    assert (
        env[2].post(path(other, a) + "/commit", json={"fingerprint": a["fingerprint"]}).status_code
        == 403
    )
    env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    assert env[2].get(path(i, a)).status_code == 403
    assert (
        env[2].post(path(i, a) + "/commit", json={"fingerprint": a["fingerprint"]}).status_code
        == 403
    )
    env[2].headers["Authorization"] = "Bearer synthetic-test-A"
    target["fingerprint"] = "0" * 64
    assert prepare(env, i, target).status_code == 409
    schema = copy.deepcopy(old["snapshot"]["data_schema"])
    schema["properties"]["release_ref"] = {"type": "string"}
    schema["required"].append("release_ref")
    prepared = lifecycle.prepare_release(
        env[0],
        env[3],
        aid,
        fp,
        limits(env),
        {"column": "amount"},
        data_schema=schema,
        data_schema_version=2,
    )
    bad = lifecycle.commit_release(
        env[0], env[3], prepared["id"], prepared["fingerprint"], limits(env)
    )
    assert prepare(env, i, bad).status_code == 409


def test_coherently_rehashed_cross_project_approval_rejects_direct_commit(env):
    old, aid, fp = release(env)
    target, _, _ = release(env, aid, fp)
    i = instance(env, old)
    a = prepare(env, i, target).json()
    pid = env[2].post("/api/projects", json={"name": "synthetic other project"}).json()["id"]
    rid = (
        env[2]
        .post(
            f"/api/projects/{pid}/resources",
            json={"name": "other.csv", "format": "csv", "content": "amount\n2\n3\n"},
        )
        .json()["id"]
    )
    other_env = (*env[:5], pid, rid)
    other_old, other_aid, other_fp = release(other_env)
    other_target, _, _ = release(other_env, other_aid, other_fp)
    other = instance(other_env, other_old)
    with env[0].tx() as c:
        p = copy.deepcopy(
            c.execute(
                select(internal_approvals.c.payload).where(internal_approvals.c.id == a["id"])
            ).scalar_one()
        )
        p.update(
            instance_id=other["id"],
            from_release_id=other_old["id"],
            target_release_id=other_target["id"],
            target_fingerprint=other_target["fingerprint"],
        )
        fp = fingerprint(p)
        c.execute(
            update(internal_approvals)
            .where(internal_approvals.c.id == a["id"])
            .values(payload=p, fingerprint=fp)
        )
    from sim2act.errors import DomainError

    with pytest.raises(DomainError, match="Approval project differs"):
        lifecycle.commit_switch(env[0], env[3], a["id"], fp, limits(env))
    assert env[2].post(path(other, a) + "/commit", json={"fingerprint": fp}).status_code == 403
    with env[0].tx() as c:
        assert not c.execute(
            select(internal_approvals.c.consumed).where(internal_approvals.c.id == a["id"])
        ).scalar_one()
        assert (
            c.execute(
                select(internal_instances.c.revision).where(internal_instances.c.id == other["id"])
            ).scalar_one()
            == 1
        )
