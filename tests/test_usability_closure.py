"""Concrete independent review defects and expiration of both preview source chains."""

import copy
import time

import pytest
from sqlalchemy import select, update
from test_app_previews import draft, execute
from test_goal_candidates import counts, create_candidate, setup_card
from test_preview_extraction import extract, setup_source

from sim2act.db import app_drafts, fingerprint, grants


@pytest.mark.parametrize("tamper", ["remove_origin", "null_origin", "sum_wiring"])
def test_generated_candidate_cannot_drop_origin_or_redirect_sum(env, tamper):
    store, _, client, _, _, pid, rid = env
    note = client.post(
        f"/api/projects/{pid}/resources",
        json={"name": "conditions.txt", "format": "txt", "content": "synthetic constraint"},
    ).json()["id"]
    card, _ = setup_card(env, [rid, note])
    aid = create_candidate(env, card).json()["id"]
    with store.tx() as c:
        candidate = copy.deepcopy(
            c.execute(select(app_drafts.c.candidate).where(app_drafts.c.id == aid)).scalar_one()
        )
        if tamper == "remove_origin":
            del candidate["generation"]
            c.execute(
                update(grants)
                .where(grants.c.resource_id == note, grants.c.principal_id == env[3])
                .values(revoked=True)
            )
        elif tamper == "null_origin":
            candidate["generation"] = None
        else:
            candidate["manifest"]["outputs"]["sum"]["field"] = "column"
        c.execute(
            update(app_drafts)
            .where(app_drafts.c.id == aid)
            .values(candidate=candidate, fingerprint=fingerprint(candidate))
        )
    before = counts(store)
    assert client.get(f"/api/apps/{aid}").status_code in [400, 409]
    assert execute(client, aid).status_code in [400, 409]
    assert counts(store) == before


def test_direct_fixed_template_cannot_redirect_sum_even_when_rehashed(env):
    aid = draft(env)
    with env[0].tx() as c:
        candidate = copy.deepcopy(
            c.execute(select(app_drafts.c.candidate).where(app_drafts.c.id == aid)).scalar_one()
        )
        candidate["manifest"]["outputs"]["sum"]["field"] = "column"
        c.execute(
            update(app_drafts)
            .where(app_drafts.c.id == aid)
            .values(candidate=candidate, fingerprint=fingerprint(candidate))
        )
    before = counts(env[0])
    assert env[2].get(f"/api/apps/{aid}").status_code == 400
    assert execute(env[2], aid).status_code == 400
    assert counts(env[0]) == before


@pytest.mark.parametrize("content", ["n\n1e1000000\n", "n\n9e999999\n9e999999\n"])
def test_decimal_overflow_is_disabled_in_guidance_and_retained_as_failed_history(env, content):
    client = env[2]
    rid = client.post(
        f"/api/projects/{env[-2]}/resources",
        json={"name": "overflow.csv", "format": "csv", "content": content},
    ).json()["id"]
    aid = draft(env, rid)
    guidance = client.get(f"/api/apps/{aid}").json()["input_guidance"]
    assert guidance["columns"][0]["numeric"] is False
    response = execute(client, aid, "n")
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "FAILED" and result["error"]["code"] == "INVALID_INPUT"
    assert result["output"] is None
    assert client.get(f"/api/apps/{aid}").json()["history"][0]["id"] == result["id"]


@pytest.mark.parametrize(
    "scope", ["user_source", "project_source", "app_source", "target_user", "target_app"]
)
def test_expired_source_or_target_grant_blocks_extraction_readback_and_new_preview(env, scope):
    source, receipt, rid, body, _ = setup_source(env)
    aid = extract(env[2], receipt, body).json()["id"]
    with env[0].tx() as c:
        source_runtime = c.execute(
            select(app_drafts.c.runtime_id).where(app_drafts.c.id == source)
        ).scalar_one()
        target_runtime = c.execute(
            select(app_drafts.c.runtime_id).where(app_drafts.c.id == aid)
        ).scalar_one()
        who = (
            env[3]
            if scope in ["user_source", "target_user"]
            else source_runtime
            if scope == "app_source"
            else target_runtime
            if scope == "target_app"
            else None
        )
        query = update(grants).where(
            grants.c.resource_id == (rid if scope.startswith("target") else env[-1]),
            grants.c.tool_ref == "resource.read",
        )
        if who:
            query = query.where(grants.c.principal_id == who)
        else:
            query = query.where(grants.c.principal_id.like("runtime_%"))
        c.execute(query.values(expires_at=time.time() - 1))
    before = counts(env[0])
    assert env[2].get(f"/api/apps/{aid}").status_code == 403
    assert execute(env[2], aid).status_code == 403
    assert extract(env[2], receipt, body).status_code == 403
    assert counts(env[0]) == before
