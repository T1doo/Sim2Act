"""Neighboring immutable-request anchor checks from connector static review."""

import copy

import pytest
from sqlalchemy import select, update
from test_goal_candidates import counts, create_candidate, setup_card

from sim2act.db import app_drafts, fingerprint, goal_card_versions, grants


@pytest.mark.parametrize("revoke_extra", [False, True])
def test_valid_old_goal_snapshot_cannot_replace_accepted_v2_origin(env, revoke_extra):
    store, _, client, user, _, pid, rid = env
    cid, content = setup_card(env)
    note = client.post(
        f"/api/projects/{pid}/resources",
        json={
            "name": "v2 condition.txt",
            "format": "txt",
            "content": "synthetic added hard condition",
        },
    ).json()["id"]
    changed = {
        **content,
        "constraints": content["constraints"] + ["v2 new hard condition"],
        "resource_refs": [rid, note],
    }
    assert (
        client.put(f"/api/goal-cards/{cid}", json={**changed, "expected_version": 1}).status_code
        == 200
    )
    response = create_candidate(env, cid, expected_version=2)
    assert response.status_code == 201
    aid = response.json()["id"]
    with store.tx() as c:
        old = (
            c.execute(
                select(goal_card_versions).where(
                    goal_card_versions.c.card_id == cid, goal_card_versions.c.version == 1
                )
            )
            .mappings()
            .one()
        )
        candidate = copy.deepcopy(
            c.execute(select(app_drafts.c.candidate).where(app_drafts.c.id == aid)).scalar_one()
        )
        candidate["generation"].update(
            goal_version=1, goal_snapshot=old["snapshot"], goal_fingerprint=old["fingerprint"]
        )
        candidate["goal"] = old["snapshot"]["content"]
        c.execute(
            update(app_drafts)
            .where(app_drafts.c.id == aid)
            .values(candidate=candidate, fingerprint=fingerprint(candidate))
        )
        if revoke_extra:
            c.execute(
                update(grants)
                .where(grants.c.resource_id == note, grants.c.principal_id == user)
                .values(revoked=True)
            )
    before = counts(store)
    read = client.get(f"/api/apps/{aid}")
    preview = client.post(
        f"/api/apps/{aid}/previews", json={"input": {"column": "amount"}, "request_key": "tampered"}
    )
    assert (read.status_code, preview.status_code) == (409, 409), (
        read.status_code,
        preview.status_code,
        preview.json().get("status"),
    )
    assert counts(store) == before


def test_genuinely_accepted_v1_remains_frozen_after_v2_extra_material_is_revoked(env):
    store, _, client, user, _, pid, rid = env
    cid, content = setup_card(env)
    aid = create_candidate(env, cid).json()["id"]
    note = client.post(
        f"/api/projects/{pid}/resources",
        json={"name": "new conditions", "format": "txt", "content": "new synthetic condition"},
    ).json()["id"]
    assert (
        client.put(
            f"/api/goal-cards/{cid}",
            json={**content, "resource_refs": [rid, note], "expected_version": 1},
        ).status_code
        == 200
    )
    with store.tx() as c:
        c.execute(
            update(grants)
            .where(grants.c.resource_id == note, grants.c.principal_id == user)
            .values(revoked=True)
        )
    read = client.get(f"/api/apps/{aid}")
    assert read.status_code == 200
    assert read.json()["candidate"]["generation"]["goal_version"] == 1
    result = client.post(
        f"/api/apps/{aid}/previews",
        json={"input": {"column": "amount"}, "request_key": "legal-old"},
    ).json()
    assert result["status"] == "SUCCEEDED"


@pytest.mark.parametrize("component", ["resource", "capability"])
def test_accepted_request_also_anchors_selected_resource_and_capability(env, component):
    store, _, client, _, _, pid, rid = env
    other = client.post(
        f"/api/projects/{pid}/resources",
        json={"name": "second.csv", "format": "csv", "content": "amount\n7\n"},
    ).json()["id"]
    cid, _ = setup_card(env, [rid, other])
    aid = create_candidate(env, cid).json()["id"]
    with store.tx() as c:
        candidate = copy.deepcopy(
            c.execute(select(app_drafts.c.candidate).where(app_drafts.c.id == aid)).scalar_one()
        )
        if component == "capability":
            candidate["generation"]["capability"] = "csv.other"
        else:
            import hashlib

            candidate["source_hash"] = hashlib.sha256(b"amount\n7\n").hexdigest()
            candidate["manifest"]["data_bindings"][0]["resource_ref"] = other
            for requirement in (
                candidate["manifest"]["permission_requirements"]
                + candidate["actions"][0]["permission_requirements"]
            ):
                requirement["resource_ref"] = other
            candidate["manifest"]["dependency_lock"][0]["ref"] = other
            candidate["actions"][0]["dependencies"][0]["ref"] = other
        c.execute(
            update(app_drafts)
            .where(app_drafts.c.id == aid)
            .values(candidate=candidate, fingerprint=fingerprint(candidate))
        )
    before = counts(store)
    assert client.get(f"/api/apps/{aid}").status_code == 409
    assert (
        client.post(
            f"/api/apps/{aid}/previews",
            json={"input": {"column": "amount"}, "request_key": "changed-anchor"},
        ).status_code
        == 409
    )
    assert counts(store) == before
