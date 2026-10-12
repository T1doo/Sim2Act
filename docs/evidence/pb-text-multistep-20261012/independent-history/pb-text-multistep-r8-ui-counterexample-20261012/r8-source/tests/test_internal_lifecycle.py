"""Internal F2-T08 lifecycle; no publication endpoint, model or new permission."""

import copy
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select, update
from test_local_task_retirement import extract, retire, setup_completed

from sim2act.contracts import Limits
from sim2act.db import (
    Store,
    app_drafts,
    app_previews,
    fingerprint,
    grants,
    internal_app_runs,
    internal_approvals,
    internal_instance_data,
    internal_instances,
    internal_releases,
    principals,
)
from sim2act.errors import DomainError
from sim2act.lifecycle import (
    commit_release,
    commit_switch,
    create_instance,
    inspect_instance,
    prepare_release,
    prepare_switch,
    read_release,
    run_instance,
)


def limits(env):
    return Limits(**{k: getattr(env[1], k) for k in Limits.model_fields})


def setup_draft(env):
    store, _, client, _, _, pid, rid = env
    aid = client.post(
        f"/api/projects/{pid}/apps/csv-preview",
        json={"name": "internal fixture", "resource_id": rid, "goal": "synthetic exact sum"},
    ).json()["id"]
    with store.tx() as c:
        fp = c.execute(select(app_drafts.c.fingerprint).where(app_drafts.c.id == aid)).scalar_one()
    return aid, fp


def release(env, aid=None, fp=None, schema=None, version=1):
    store, _, _, user, *_ = env
    if aid is None:
        aid, fp = setup_draft(env)
    a = prepare_release(
        store,
        user,
        aid,
        fp,
        limits(env),
        {"column": "amount"},
        data_schema=schema,
        data_schema_version=version,
    )
    r = commit_release(store, user, a["id"], a["fingerprint"], limits(env))
    return r, aid, fp


def create(env, r):
    return create_instance(env[0], env[3], r["id"], r["fingerprint"], limits(env))


def run(env, i, r, column="amount", key="request"):
    return run_instance(
        env[0],
        env[3],
        i["id"],
        i["revision"],
        r["fingerprint"],
        {"column": column},
        key,
        limits(env),
    )


def counts(store):
    with store.tx() as c:
        return {
            t.name: c.execute(select(func.count()).select_from(t)).scalar_one()
            for t in [
                internal_releases,
                internal_instances,
                internal_app_runs,
                internal_instance_data,
                app_previews,
                grants,
                principals,
            ]
        }


def test_completed_task_internal_release_instances_fresh_runs_cold_data_no_preview_copy(env):
    store, s, client, user, *_ = env
    task, _, body, retirement = setup_completed(env)
    aid = extract(client, task, body)
    assert retire(client, task, retirement).status_code == 200
    fp = client.get(f"/api/apps/{aid}").json()["fingerprint"]
    before = counts(store)
    r, _, _ = release(env, aid, fp)
    a, b = create(env, r), create(env, r)
    x = run(env, a, r)
    y = run(env, a, r, "quantity", "other")
    z = run(env, b, r, key="request")
    assert (x["output"]["sum"], y["output"]["sum"], z["output"]["sum"]) == ("40", "5", "40")
    assert (x["result_version"], y["result_version"], z["result_version"]) == (1, 2, 1)
    assert x["namespace"] == "INTERNAL_APPRUN" and x["release_id"] == r["id"] and x["id"] != z["id"]
    assert run(env, a, r)["id"] == x["id"]
    bad = run(env, a, r, "missing", "bad")
    assert bad["status"] == "FAILED" and bad["result_version"] is None and bad["output"] is None
    after = counts(store)
    for table in [app_previews, grants, principals]:
        assert before[table.name] == after[table.name]
    assert after["internal_app_runs"] == 4 and after["internal_instance_data"] == 3
    cold = Store(s.database_url, test_only=True)
    if not store.sqlite:
        cold.engine = cold.engine.execution_options(**store.engine.get_execution_options())
    data_a = inspect_instance(cold, user, a["id"], limits(env))
    data_b = inspect_instance(cold, user, b["id"], limits(env))
    assert [d["data"]["result"]["sum"] for d in data_a["data"]] == ["40", "5"]
    assert [d["version"] for d in data_b["data"]] == [1]
    assert all(d["instance_id"] == a["id"] for d in data_a["data"])
    cold.engine.dispose()
    assert client.post("/api/releases", json={}).status_code == 404
    assert client.post("/api/internal/releases", json={}).status_code == 404


@pytest.mark.parametrize(
    "change", ["fingerprint", "draft", "grant", "expiry", "source_content", "bytes"]
)
def test_release_exact_approval_changed_preconditions_reject_without_release(env, change):
    store, _, _, user, _, _, rid = env
    aid, fp = setup_draft(env)
    a = prepare_release(store, user, aid, fp, limits(env), {"column": "amount"})
    exact = a["fingerprint"]
    with store.tx() as c:
        if change == "fingerprint":
            exact = "0" * 64
        elif change == "draft":
            candidate = copy.deepcopy(
                c.execute(select(app_drafts.c.candidate).where(app_drafts.c.id == aid)).scalar_one()
            )
            candidate["goal"]["known"] = "changed after approval"
            c.execute(
                update(app_drafts)
                .where(app_drafts.c.id == aid)
                .values(candidate=candidate, fingerprint=fingerprint(candidate))
            )
        elif change == "grant":
            c.execute(update(grants).where(grants.c.resource_id == rid).values(revision=2))
        elif change == "expiry":
            p = copy.deepcopy(
                c.execute(
                    select(internal_approvals.c.payload).where(internal_approvals.c.id == a["id"])
                ).scalar_one()
            )
            p["expires_at"] = 0
            exact = fingerprint(p)
            c.execute(
                update(internal_approvals)
                .where(internal_approvals.c.id == a["id"])
                .values(payload=p, fingerprint=exact, expires_at=0)
            )
        else:
            from sim2act.db import resources

            values = {"content": "amount\n99\n"}
            if change == "source_content":
                values["hash"] = "0" * 64
            c.execute(update(resources).where(resources.c.id == rid).values(**values))
    with pytest.raises(DomainError):
        commit_release(store, user, a["id"], exact, limits(env))
    assert counts(store)["internal_releases"] == 0


def test_release_frozen_draft_change_does_not_mutate_old_run_spec(env):
    store, _, _, user, *_ = env
    r, aid, _ = release(env)
    i = create(env, r)
    original = copy.deepcopy(r["snapshot"])
    with store.tx() as c:
        candidate = copy.deepcopy(
            c.execute(select(app_drafts.c.candidate).where(app_drafts.c.id == aid)).scalar_one()
        )
        candidate["goal"]["known"] = "mutable working draft"
        c.execute(
            update(app_drafts)
            .where(app_drafts.c.id == aid)
            .values(candidate=candidate, fingerprint=fingerprint(candidate))
        )
        frozen = read_release(store, c, user, r["id"], limits(env))
        assert frozen["snapshot"] == original
    assert run(env, i, r)["output"]["sum"] == "4.00"


@pytest.mark.parametrize("part", ["manifest", "actions", "dependency_lock", "check_evidence"])
def test_release_snapshot_rehash_tamper_independent_approval_anchor(env, part):
    store, _, _, user, *_ = env
    r, _, _ = release(env)
    with store.tx() as c:
        s = copy.deepcopy(r["snapshot"])
        if part == "manifest":
            s["draft"]["candidate"]["manifest"]["data_schema_version"] = 2
        elif part == "actions":
            s["draft"]["candidate"]["actions"][0]["executor"]["version"] = "2"
        elif part == "dependency_lock":
            s["dependency_lock"][0]["version"] = "2"
        else:
            s["check_evidence"]["output_fingerprint"] = "0" * 64
        c.execute(
            update(internal_releases)
            .where(internal_releases.c.id == r["id"])
            .values(snapshot=s, fingerprint=fingerprint(s))
        )
    with pytest.raises(DomainError, match="release/approval"):
        create(env, {**r, "fingerprint": fingerprint(s)})
    assert counts(store)["internal_instances"] == 0


@pytest.mark.parametrize("who", ["user", "project", "app"])
@pytest.mark.parametrize("expiry", [False, True])
def test_current_grant_revocation_or_expiry_blocks_new_run_and_read(env, who, expiry):
    store, _, _, user, _, pid, rid = env
    r, _, _ = release(env)
    i = create(env, r)
    run(env, i, r)
    with store.tx() as c:
        identity = (
            user
            if who == "user"
            else r["snapshot"]["draft"]["runtime_id"]
            if who == "app"
            else store.own_project(c, user, pid)["runtime_id"]
        )
        c.execute(
            update(grants)
            .where(grants.c.principal_id == identity, grants.c.resource_id == rid)
            .values(**({"expires_at": 0} if expiry else {"revoked": True}))
        )
    before = counts(store)
    with pytest.raises(DomainError):
        run(env, i, r, key="after")
    with pytest.raises(DomainError):
        inspect_instance(store, user, i["id"], limits(env))
    assert counts(store) == before


def test_cross_owner_and_cross_app_switch_reject(env):
    store, _, _, _, other, *_ = env
    r, _, _ = release(env)
    i = create(env, r)
    with pytest.raises(DomainError):
        inspect_instance(store, other, i["id"], limits(env))
    with pytest.raises(DomainError):
        run_instance(
            store, other, i["id"], 1, r["fingerprint"], {"column": "amount"}, "attack", limits(env)
        )
    target, _, _ = release(env)
    with pytest.raises(DomainError):
        prepare_switch(store, env[3], i["id"], target["id"], 1, limits(env))


def test_upgrade_rollback_compatible_history_and_incompatible_schema(env):
    store, _, _, user, *_ = env
    r1, aid, fp = release(env)
    i = create(env, r1)
    first = run(env, i, r1)
    # Same schema/version, new immutable release: compatible switch and rollback retain data.
    r2, _, _ = release(env, aid, fp)
    a = prepare_switch(store, user, i["id"], r2["id"], 1, limits(env))
    v = commit_switch(store, user, a["id"], a["fingerprint"], limits(env))
    assert v["data_version"] == 1
    back = prepare_switch(store, user, i["id"], r1["id"], 2, limits(env))
    v = commit_switch(store, user, back["id"], back["fingerprint"], limits(env))
    assert v["revision"] == 3
    assert inspect_instance(store, user, i["id"], limits(env))["data"][0]["run_id"] == first["id"]
    schema = copy.deepcopy(r1["snapshot"]["data_schema"])
    schema["properties"]["release_ref"] = {"type": "string"}
    schema["required"].append("release_ref")
    required, _, _ = release(env, aid, fp, schema, 2)
    with pytest.raises(DomainError, match="Incompatible"):
        prepare_switch(store, user, i["id"], required["id"], 3, limits(env))
    schema["required"].remove("release_ref")
    optional, _, _ = release(env, aid, fp, schema, 2)
    a = prepare_switch(store, user, i["id"], optional["id"], 3, limits(env))
    changed = commit_switch(store, user, a["id"], a["fingerprint"], limits(env))
    run(env, {**i, "revision": changed["revision"]}, optional, key="v2")
    before = inspect_instance(store, user, i["id"], limits(env))
    with pytest.raises(DomainError, match="Incompatible"):
        prepare_switch(store, user, i["id"], r1["id"], 4, limits(env))
    after = inspect_instance(store, user, i["id"], limits(env))
    assert before == after and len(after["data"]) == 2 and len(after["history"]) == 4


@pytest.mark.parametrize("change", ["data", "pointer", "grant", "fingerprint"])
def test_switch_exact_approval_data_and_pointer_cas(env, change):
    store, _, _, user, *_ = env
    r, aid, fp = release(env)
    i = create(env, r)
    target, _, _ = release(env, aid, fp)
    a = prepare_switch(store, user, i["id"], target["id"], 1, limits(env))
    exact = a["fingerprint"]
    if change == "data":
        run(env, i, r)
    elif change == "pointer":
        other = prepare_switch(store, user, i["id"], target["id"], 1, limits(env))
        commit_switch(store, user, other["id"], other["fingerprint"], limits(env))
    elif change == "grant":
        with store.tx() as c:
            c.execute(update(grants).where(grants.c.project_id == env[-2]).values(revision=2))
    else:
        exact = "0" * 64
    with pytest.raises(DomainError):
        commit_switch(store, user, a["id"], exact, limits(env))
    with store.tx() as c:
        assert (
            c.execute(
                select(internal_approvals.c.consumed).where(internal_approvals.c.id == a["id"])
            ).scalar_one()
            is False
        )


def test_instance_lineage_copy_and_request_key_fingerprint_reject(env):
    store, _, _, user, *_ = env
    r, _, _ = release(env)
    a, b = create(env, r), create(env, r)
    x = run(env, a, r)
    with pytest.raises(DomainError):
        run(env, a, r, column="missing")
    run(env, b, r)
    with store.tx() as c:
        c.execute(
            update(internal_instance_data)
            .where(internal_instance_data.c.instance_id == b["id"])
            .values(run_id=x["id"] + "bad")
        )
    with pytest.raises(DomainError, match="lineage"):
        inspect_instance(store, user, b["id"], limits(env))
    assert inspect_instance(store, user, a["id"], limits(env))["data_version"] == 1


def test_concurrent_run_same_key_records_once_per_instance(env):
    r, _, _ = release(env)
    i = create(env, r)
    with ThreadPoolExecutor(max_workers=2) as pool:
        values = list(pool.map(lambda _: run(env, i, r), range(2)))
    assert values[0]["id"] == values[1]["id"]
    assert (
        counts(env[0])["internal_app_runs"] == 1 and counts(env[0])["internal_instance_data"] == 1
    )


def test_internal_lifecycle_application_role_no_grant_expansion(env, runtime_role):
    store, settings, client, *_ = env
    aid, fp = setup_draft(env)
    application = Store(runtime_role)
    role_env = (application, settings, client, *env[3:])
    before = counts(store)
    r, _, _ = release(role_env, aid, fp)
    i = create(role_env, r)
    assert run(role_env, i, r)["status"] == "SUCCEEDED"
    assert run(role_env, i, r, column="missing", key="bad")["status"] == "FAILED"
    assert inspect_instance(application, env[3], i["id"], limits(env))["data_version"] == 1
    after = counts(store)
    assert after["grants"] == before["grants"] and after["principals"] == before["principals"]
    application.engine.dispose()


@pytest.mark.parametrize("malformed", ["missing_properties", "enum", "open_record"])
def test_review_schema_shape_rejected_before_approval(env, malformed):
    aid, fp = setup_draft(env)
    with env[0].tx() as c:
        candidate = c.execute(
            select(app_drafts.c.candidate).where(app_drafts.c.id == aid)
        ).scalar_one()
    schema = {
        "type": "object",
        "properties": {"result": candidate["manifest"]["output_schema"]},
        "required": ["result"],
        "additionalProperties": False,
    }
    if malformed == "missing_properties":
        schema.pop("properties")
        schema.pop("required")
    elif malformed == "enum":
        schema["enum"] = [{"result": {"sum": "99"}}]
    else:
        schema["additionalProperties"] = True
    with pytest.raises(DomainError):
        prepare_release(
            env[0], env[3], aid, fp, limits(env), {"column": "amount"}, data_schema=schema
        )
    with env[0].tx() as c:
        assert c.execute(select(func.count()).select_from(internal_approvals)).scalar_one() == 0


@pytest.mark.parametrize("transition", ["same_shape_changed_version", "changed_shape_same_version"])
def test_unknown_schema_version_transition_rejected(env, transition):
    r, aid, fp = release(env)
    i = create(env, r)
    schema = copy.deepcopy(r["snapshot"]["data_schema"])
    version = 2
    if transition == "changed_shape_same_version":
        schema["properties"]["release_ref"] = {"type": "string"}
        version = 1
    target, _, _ = release(env, aid, fp, schema, version)
    with pytest.raises(DomainError, match="Unknown data version"):
        prepare_switch(env[0], env[3], i["id"], target["id"], 1, limits(env))
    assert inspect_instance(env[0], env[3], i["id"], limits(env))["revision"] == 1


def test_committed_release_current_bytes_tamper_blocks_instance(env):
    from sim2act.db import resources

    r, _, _ = release(env)
    with env[0].tx() as c:
        c.execute(update(resources).where(resources.c.id == env[6]).values(content="amount\n99\n"))
    with pytest.raises(DomainError):
        create(env, r)
    assert counts(env[0])["internal_instances"] == 0
