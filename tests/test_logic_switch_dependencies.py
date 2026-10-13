"""Finite metadata cycle gate, without claiming synthetic graphs are valid apps."""

import copy

import pytest
from sqlalchemy import insert, update
from test_internal_lifecycle import create, limits, release

from sim2act import lifecycle
from sim2act.db import (
    fingerprint,
    internal_approvals,
    internal_instances,
    internal_releases,
    new_id,
)
from sim2act.errors import DomainError


def metadata_release(store, user, base, source):
    """New artificial envelope solely for iterative pointer-graph boundary tests."""
    snapshot = copy.deepcopy(base["snapshot"])
    snapshot["natural_logic_source"] = dict(
        namespace="natural-local-logic.v1",
        instance_id=source,
        preview_key="metadata-only",
        preview_fingerprint="a" * 64,
        check_fingerprint="b" * 64,
        execution_digest="c" * 64,
    )
    with store.tx() as c:
        a = lifecycle.new_approval(c, user, base["project_id"], "release", dict(snapshot=snapshot))
        row = dict(
            id=new_id("irelease"),
            project_id=base["project_id"],
            principal_id=user,
            approval_id=a["id"],
            snapshot=snapshot,
            fingerprint=fingerprint(snapshot),
        )
        c.execute(insert(internal_releases).values(**row))
        c.execute(
            update(internal_approvals)
            .where(internal_approvals.c.id == a["id"])
            .values(consumed=True)
        )
    return row


def test_multilevel_metadata_existing_and_proposed_cycles_are_finite(env):
    store, user = env[0], env[3]
    base, _, _ = release(env)
    source = create(env, base)
    middle = create(env, base)
    first = metadata_release(store, user, base, source["id"])
    second = metadata_release(store, user, base, middle["id"])
    with store.tx() as c:
        c.execute(
            update(internal_instances)
            .where(internal_instances.c.id == middle["id"])
            .values(release_id=first["id"])
        )
        trace = lifecycle.logic_release_trace(store, c, user, second)
        assert not trace["cyclic"] and len(trace["edges"]) == 2
        trace = lifecycle.logic_release_trace(
            store, c, user, second, proposed_instance=source["id"]
        )
        assert trace["cyclic"] and len(trace["edges"]) == 2
    with pytest.raises(DomainError, match="cycle"):
        lifecycle.prepare_switch(
            store, user, source["id"], second["id"], source["revision"], limits(env)
        )
    with store.tx() as c:
        # Represent a pre-existing damaged pointer graph, not a supported nested app.
        c.execute(
            update(internal_instances)
            .where(internal_instances.c.id == source["id"])
            .values(release_id=second["id"])
        )
        with pytest.raises(DomainError, match="cycle"):
            lifecycle.read_release(store, c, user, second["id"], limits(env))
    with pytest.raises(DomainError, match="cycle"):
        lifecycle.prepare_switch(
            store, user, source["id"], base["id"], source["revision"], limits(env)
        )


def test_unrelated_normal_switch_freezes_dependency_digest_and_duplicate_is_no_write(env):
    store, user = env[0], env[3]
    base, aid, fp = release(env)
    i = create(env, base)
    target, _, _ = release(env, aid, fp)
    a = lifecycle.prepare_switch(store, user, i["id"], target["id"], i["revision"], limits(env))
    detail = lifecycle.inspect_switch_approval(store, user, i["id"], a["id"], limits(env))
    assert len(detail["payload"]["logic_dependency_fingerprint"]) == 64
    got = lifecycle.commit_switch(store, user, a["id"], a["fingerprint"], limits(env))
    assert got["revision"] == i["revision"] + 1
    before = lifecycle.inspect_instance(store, user, i["id"], limits(env))
    with pytest.raises(DomainError):
        lifecycle.commit_switch(store, user, a["id"], a["fingerprint"], limits(env))
    assert lifecycle.inspect_instance(store, user, i["id"], limits(env)) == before


def test_foreign_instance_cannot_read_dependency_metadata(env):
    base, _, _ = release(env)
    i = create(env, base)
    with env[0].tx() as c, pytest.raises(DomainError):
        lifecycle.switch_preflight(env[0], c, env[4], i["id"], base["id"])


@pytest.mark.parametrize("fault", ["grant", "approval", "history"])
def test_post_pointer_failure_rolls_back_switch_and_approval(env, monkeypatch, fault):
    from sqlalchemy import select
    from test_spec_app_operations import snapshot

    from sim2act.db import grants

    store, user = env[0], env[3]
    base, aid, fp = release(env)
    i = create(env, base)
    target, _, _ = release(env, aid, fp)
    a = lifecycle.prepare_switch(store, user, i["id"], target["id"], i["revision"], limits(env))
    before = snapshot(store)
    read = lifecycle.read_release
    injected = False

    def after_actual_read(store, c, user, rid, limits, **kwargs):
        nonlocal injected
        result = read(store, c, user, rid, limits, **kwargs)
        live = c.execute(
            select(internal_instances.c.release_id, internal_instances.c.revision).where(
                internal_instances.c.id == i["id"]
            )
        ).one()
        if not injected and live == (target["id"], i["revision"] + 1):
            injected = True
            if fault == "grant":
                c.execute(
                    update(grants)
                    .where(grants.c.project_id == i["project_id"])
                    .values(revoked=True)
                )
            elif fault == "approval":
                c.execute(
                    update(internal_approvals)
                    .where(internal_approvals.c.id == a["id"])
                    .values(expires_at=0)
                )
            else:
                c.execute(
                    update(internal_instances)
                    .where(internal_instances.c.id == i["id"])
                    .values(history=[])
                )
        return result

    monkeypatch.setattr(lifecycle, "read_release", after_actual_read)
    with pytest.raises(DomainError):
        lifecycle.commit_switch(store, user, a["id"], a["fingerprint"], limits(env))
    assert injected and snapshot(store) == before


def test_actual_existing_business_adopts_modified_logic_and_keeps_history(env, tmp_path):
    """New-source full Worker proof plus a pre-existing ordinary business instance."""
    import json

    from fastapi.testclient import TestClient
    from sqlalchemy import select
    from test_logic_version_uses import pa_saved, version
    from test_natural_spec_apps import SOURCE, enqueue, transport
    from test_natural_spec_owner_acceptance import decision, preview, state
    from test_pb_natural_specs import drive_to_success
    from test_spec_app_operations import snapshot

    from sim2act import natural_logic_patches as logic
    from sim2act.api import create_app
    from sim2act.db import Store, delivery_graph_requests

    data, app, base, source = pa_saved(env)
    client, store = data[2], data[0]
    r = client.post(
        "/api/internal/releases/" + base["id"] + "/instances",
        json=dict(
            expected_release_fingerprint=base["fingerprint"],
            request_key="existing-business-before-change",
        ),
    )
    assert r.status_code == 201, r.text
    business = r.json()
    old_run = enqueue(data, base, business)
    drive_to_success(data, old_run, transport([]))
    owner_path = (
        "/api/internal/instances/" + business["id"] + "/runs/" + old_run + "/spec-owner-review"
    )
    old_review, _ = preview(data, owner_path)
    r = client.post(owner_path + "-requests", json=decision(old_review))
    assert r.status_code == 201, r.text
    source_path = "/api/internal/instances/" + source["id"]
    # Actual permitted approval before the delivered Release pins this source.
    r = client.post(
        source_path + "/switch-approvals",
        json=dict(
            target_release_id=base["id"],
            expected_target_fingerprint=base["fingerprint"],
            expected_revision=source["revision"],
        ),
    )
    assert r.status_code == 201, r.text
    stale = r.json()
    modified, unused_new, checked = version(data, app, base, source)
    with store.tx() as c:
        started = c.execute(
            select(delivery_graph_requests.c.snapshot).where(
                delivery_graph_requests.c.app_id == source["id"],
                delivery_graph_requests.c.kind == logic.CHECK,
                delivery_graph_requests.c.request_key == "use-logic",
            )
        ).scalar_one()["response"]
    check_id = started["check_instance_id"]
    after_version = snapshot(store)
    failures = []
    for iid, rid in [
        (source["id"], modified["id"]),
        (source["id"], base["id"]),
        (check_id, modified["id"]),
        (check_id, base["id"]),
    ]:
        current = client.get("/api/internal/instances/" + iid)
        assert current.status_code == 200, current.text
        assert current.json()["switch_policy"]["roles"]
        target = modified if rid == modified["id"] else base
        r = client.post(
            "/api/internal/instances/" + iid + "/switch-approvals",
            json=dict(
                target_release_id=rid,
                expected_target_fingerprint=target["fingerprint"],
                expected_revision=current.json()["revision"],
            ),
        )
        assert r.status_code == 409 and any(word in r.text for word in ("cycle", "immutable")), (
            r.text
        )
        failures.append(dict(instance_id=iid, target=rid, status=r.status_code, body=r.json()))
    for path, method, body in [
        (source_path + "/switch-approvals/" + stale["id"], "GET", None),
        (
            source_path + "/switch-approvals/" + stale["id"] + "/commit",
            "POST",
            dict(fingerprint=stale["fingerprint"]),
        ),
    ]:
        r = client.request(method, path, json=body)
        assert r.status_code == 409 and "immutable" in r.text, r.text
        failures.append(dict(path=path, status=r.status_code, body=r.json()))
    assert snapshot(store) == after_version
    for path in [
        source_path,
        "/api/internal/instances/" + check_id,
        "/api/internal/releases/" + modified["id"],
    ]:
        r = client.get(path)
        assert r.status_code == 200, r.text
    path = "/api/internal/instances/" + business["id"]
    before = client.get(path).json()
    assert before["data_version"] == 1 and not before["switch_policy"]["roles"]
    assert modified["id"] not in before["switch_policy"]["blocked_release_ids"]
    r = client.post(
        path + "/switch-approvals",
        json=dict(
            target_release_id=modified["id"],
            expected_target_fingerprint=modified["fingerprint"],
            expected_revision=before["revision"],
        ),
    )
    assert r.status_code == 201, r.text
    a = r.json()
    inspected = client.get(path + "/switch-approvals/" + a["id"])
    assert inspected.status_code == 200 and inspected.json()["retained_records"] == 1, (
        inspected.text
    )
    r = client.post(
        path + "/switch-approvals/" + a["id"] + "/commit", json=dict(fingerprint=a["fingerprint"])
    )
    assert r.status_code == 200, r.text
    switched = client.get(path).json()
    assert (
        switched["release_id"] == modified["id"] and switched["revision"] == before["revision"] + 1
    )
    assert switched["data"] == before["data"] and switched["data_version"] == before["data_version"]
    assert switched["history"][:-1] == before["history"]
    stable = snapshot(store)
    r = client.post(
        path + "/switch-approvals/" + a["id"] + "/commit", json=dict(fingerprint=a["fingerprint"])
    )
    assert r.status_code == 409, (
        r.text
    )  # Existing consumed-approval protocol, no duplicate mutation.
    assert snapshot(store) == stable
    new_run = enqueue(data, modified, switched, key="business-modified-actual")
    cold = Store(data[1].database_url, test_only=True)
    coldclient = TestClient(create_app(cold, data[1]))
    coldclient.headers["Authorization"] = "Bearer synthetic-test-A"
    current = (cold, data[1], coldclient, *data[3:])
    sent = []
    try:
        drive_to_success(current, new_run, transport(sent, SOURCE))
        result = coldclient.get("/api/internal/app-run-jobs/" + new_run + "/spec-artifact")
        assert result.status_code == 200, result.text
        content = json.loads(result.json()["resource"]["content"])
        assert content["source_content"] == SOURCE and content["owner_acceptance"] == "PENDING"
        assert len(sent) == 2
        model_inputs = json.loads(sent[1]["messages"][1]["content"])["current_inputs"]
        assert ("prior_items" in model_inputs) == (
            "prior_items" in checked["effective_candidate"]["spec_recipe"]["steps"][2]["inputs"]
        )
        after = coldclient.get(path).json()
        assert (
            after["data_version"] == 2
            and after["data"][:-1] == before["data"]
            and after["history"] == switched["history"]
        )
        new_owner_path = path + "/runs/" + new_run + "/spec-owner-review"
        assert state(current, new_owner_path)["latest"] is None
        fresh, _ = preview(current, new_owner_path)
        r = coldclient.post(new_owner_path + "-requests", json=decision(fresh))
        assert r.status_code == 201, r.text
        assert state(current, new_owner_path, "decision")["owner_acceptance"] == "ACCEPTED"
        saved = snapshot(cold)
        for table in ("app_drafts", "internal_releases", "goal_cards", "goal_card_versions"):
            assert stable[table] == saved[table], table
        for table in ("natural_owner_records", "natural_owner_seals", "internal_instance_data"):
            assert all(row in saved[table] for row in stable[table]), table
        (tmp_path / "business-proof.json").write_text(
            json.dumps(
                dict(
                    source_instance_id=source["id"],
                    check_instance_id=check_id,
                    base_release=base,
                    modified_release=modified,
                    business_instance=after,
                    old_run=old_run,
                    new_run=new_run,
                    rejected=failures,
                    actual_wire=sent,
                    checked=checked,
                    simulated_human_only=True,
                    real_paid_models=0,
                ),
                indent=2,
            )
            + "\n"
        )
    finally:
        coldclient.close()
        cold.engine.dispose()


def test_long_metadata_chain_is_bounded_and_unrelated_instance_stays_readable(env):
    store, user = env[0], env[3]
    base, _, _ = release(env)
    business = create(env, base)
    previous = base
    for _ in range(lifecycle.MAX_LOGIC_SOURCE_DEPTH):
        source = create(env, base)
        with store.tx() as c:
            c.execute(
                update(internal_instances)
                .where(internal_instances.c.id == source["id"])
                .values(release_id=previous["id"])
            )
        previous = metadata_release(store, user, base, source["id"])
    with store.tx() as c:
        trace = lifecycle.logic_release_trace(store, c, user, previous)
        assert trace["over_limit"] and len(trace["nodes"]) == lifecycle.MAX_LOGIC_SOURCE_DEPTH
        with pytest.raises(DomainError, match="finite depth"):
            lifecycle.read_release(store, c, user, previous["id"], limits(env))
    with pytest.raises(DomainError, match="finite depth"):
        lifecycle.prepare_switch(
            store, user, business["id"], previous["id"], business["revision"], limits(env)
        )
    state = lifecycle.inspect_instance(store, user, business["id"], limits(env))
    assert state["release_id"] == base["id"] and not state["switch_policy"]["roles"]
    assert previous["id"] in state["switch_policy"]["blocked_release_ids"]
