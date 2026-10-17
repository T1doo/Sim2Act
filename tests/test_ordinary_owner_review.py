"""Prospective ordinary Goal human declarations; synthetic users, never real signoff."""

import copy
import json

import pytest
from sqlalchemy import select, update
from test_goal_card_runs import authority, card

from sim2act.db import goal_cards, grants, run_contracts, runs
from sim2act.model import MockModel
from sim2act.worker import Worker


def start(env, source, key="prospective-human-rubric", route="reviewable-runs"):
    return env[2].post(f"/api/projects/{env[5]}/goal-cards/{source['id']}/{route}", json={
        "expected_version": source["version"], "expected_fingerprint": source["fingerprint"],
        "request_key": key})


def review(env, rid, method="get", body=None, key=None):
    path = f"/api/runs/{rid}/owner-review"
    if method == "post":
        return env[2].post(path + "-requests", json=body)
    return env[2].get(path, params={"request_key": key} if key else None)


def prepare(env, rid):
    current = review(env, rid)
    assert current.status_code == 200, current.text
    current = current.json()
    from sim2act.db import fingerprint
    body = dict(command="PREPARE", request_key="prepare-rubric", expected_sequence=current["sequence"],
        expected_contract_fingerprint=fingerprint(current["current"]))
    response = review(env, rid, "post", body)
    assert response.status_code == 201, response.text
    return current, response.json()["record"], body


def decision(env, rid, accept=True):
    state = review(env, rid).json()
    record = state["record"]
    return dict(command="DECIDE", request_key="manual-decision", expected_sequence=state["sequence"],
        review_id=record["id"], review_fingerprint=record["fingerprint"],
        choices=[dict(item_id=item["id"], decision="ACCEPT" if accept or n else "REJECT",
            reason="SIMULATED user declaration; not real human or semantic acceptance")
            for n, item in enumerate(record["payload"]["contract"]["items"])])


def execute(env, source):
    response = start(env, source)
    assert response.status_code == 202, response.text
    rid = response.json()["run_id"]
    assert Worker(env[0], env[1], MockModel()).once()
    actual = env[2].get(f"/api/runs/{rid}")
    assert actual.status_code == 200, actual.text
    assert actual.json()["status"] == "PARTIAL"
    return rid


@pytest.mark.parametrize("accept", [True, False])
def test_frozen_goal_same_run_explicit_ordered_declaration_and_history(env, tmp_path, accept):
    source, content = card(env)
    before = authority(env[0])
    rid = execute(env, source)
    initial = env[2].get(f"/api/runs/{rid}").json()
    current, prepared, body = prepare(env, rid)
    assert current["current"]["goal"] == content
    assert current["current"]["source_goal"]["fingerprint"] == source["fingerprint"]
    assert current["current"]["result_version"] == initial["version"]
    assert current["current"]["output"] == initial["result"]
    assert [i["text"] for i in current["current"]["items"] if i["id"].startswith("acceptance_checks.")] == content["acceptance_checks"]
    assert review(env, rid, "post", body).json()["record"] == prepared
    intent = decision(env, rid, accept)
    for choices in (intent["choices"][:-1], list(reversed(intent["choices"])),
                    [{**x, "reason": " "} for x in intent["choices"]]):
        assert review(env, rid, "post", {**intent, "choices": choices}).status_code in (400, 409)
    result = review(env, rid, "post", intent)
    assert result.status_code == 201, result.text
    assert result.json()["record"]["status"] == ("ACCEPTED" if accept else "REJECTED")
    assert review(env, rid, "post", intent).json() == result.json()
    changed = copy.deepcopy(intent)
    changed["choices"][0]["reason"] = "different body"
    assert review(env, rid, "post", changed).status_code == 409
    state = review(env, rid).json()
    assert state["owner_acceptance"] == result.json()["record"]["status"]
    assert state["automatic_goal_acceptance"] == "NOT_RUN" and not state["formal_publication_enabled"]
    assert env[2].get(f"/api/runs/{rid}").json() == initial
    assert authority(env[0]) == before
    assert start(env, source).json()["run_id"] == rid
    (tmp_path / "simulated-declaration.json").write_text(json.dumps({"source": source,
        "before": initial, "current": current, "prepare": body, "decision": intent, "state": state,
        "real_model_calls": 0, "real_human_signoff": "NOT_RUN"}, ensure_ascii=False, indent=2))


def test_old_run_no_retroactive_rubric_and_wrong_identity_denied(env):
    source, _ = card(env)
    old = start(env, source, route="runs").json()["run_id"]
    assert review(env, old).status_code == 409
    rid = execute(env, source)
    env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    assert review(env, rid).status_code == 403
    assert review(env, rid, "post", dict(command="PREPARE", request_key="foreign", expected_sequence=0,
        expected_contract_fingerprint="0"*64)).status_code == 403


def test_missing_checks_not_accepted_and_queued_run_cannot_be_signed(env):
    source, content = card(env)
    content["acceptance_checks"] = []
    edited = env[2].put(f"/api/goal-cards/{source['id']}", json={**content, "expected_version": 1}).json()
    assert start(env, edited).status_code == 400
    with env[0].tx() as c:
        assert not c.execute(select(runs)).first()
    source, _ = card(env)
    rid = start(env, source).json()["run_id"]
    state = review(env, rid).json()
    assert not state["content_access"] and "current" not in state
    assert review(env, rid, "post", dict(command="PREPARE", request_key="queued", expected_sequence=0,
        expected_contract_fingerprint="0"*64)).status_code == 409


@pytest.mark.parametrize("change", ["goal", "result", "grant", "expiry", "seal"])
def test_current_version_permissions_expiry_and_immutable_seal(env, change):
    source, _ = card(env)
    rid = execute(env, source)
    _, prepared, _ = prepare(env, rid)
    intent = decision(env, rid)
    with env[0].tx() as c:
        if change == "goal":
            c.execute(update(goal_cards).where(goal_cards.c.id == source["id"]).values(version=2))
        elif change == "result":
            value = c.execute(select(runs.c.result).where(runs.c.id == rid)).scalar_one()
            c.execute(update(runs).where(runs.c.id == rid).values(result={**value, "answer": "changed after preview"}))
        elif change == "grant":
            c.execute(update(grants).where(grants.c.principal_id == env[3], grants.c.resource_id == env[6]).values(revoked=True))
        elif change == "expiry":
            from sim2act import ordinary_owner_review
            ordinary_owner_review.EXPIRY_TEST_UNUSED = None
        else:
            from sim2act.db import ordinary_owner_seals
            c.execute(update(ordinary_owner_seals).where(ordinary_owner_seals.c.record_id == prepared["id"]).values(metadata_fingerprint="0"*64))
    if change == "expiry":
        from unittest.mock import patch
        import time
        with patch("sim2act.owner_acceptance.time.time", return_value=time.time()+901):
            assert review(env, rid, "post", intent).status_code == 409
        return
    assert review(env, rid, "post", intent).status_code in (403, 409)
    if change == "seal":
        assert review(env, rid).status_code == 409
        return
    stale = review(env, rid).json()
    assert stale["owner_acceptance"] == "STALE" and not stale["content_access"] and "record" not in stale
    stopped = review(env, rid, "post", dict(command="CANCEL", request_key="metadata-stop", expected_sequence=1,
        target_id=prepared["id"], target_fingerprint=prepared["fingerprint"], reason="Stop this exact preview"))
    assert stopped.status_code == 201, stopped.text
    assert review(env, rid).json()["owner_acceptance"] == "CANCELLED"
