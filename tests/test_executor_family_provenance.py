"""Independent stored source families must survive coordinated executor replacement."""

import copy
from pathlib import Path

import pytest
from sqlalchemy import func, select, update
from test_bounded_agent_apps import candidate, limits, output, replay
from test_goal_candidates import create_candidate, setup_card
from test_preview_extraction import extract, setup_source

from sim2act import app_jobs
from sim2act.db import (
    app_drafts,
    fingerprint,
    grants,
    internal_app_runs,
    internal_approvals,
    internal_instance_data,
    internal_instances,
    internal_releases,
    runs,
)
from sim2act.errors import DomainError
from sim2act.lifecycle import commit_release, create_instance, prepare_release

SOURCE = Path(__file__).parents[1] / "docs/evidence/bounded-agent-offline-20261006/source-a.md"


def effects(store):
    with store.tx() as c:
        return {
            t.name: c.execute(select(func.count()).select_from(t)).scalar_one()
            for t in [
                grants,
                internal_approvals,
                internal_releases,
                internal_instances,
                internal_app_runs,
                internal_instance_data,
                runs,
            ]
        }


def switched_fixture(env, family):
    store, _, client, user, _, pid, original = env
    if family == "goal":
        card, _ = setup_card(env)
        aid = create_candidate(env, card).json()["id"]
    else:
        _, receipt, _, body, _ = setup_source(env)
        response = extract(client, receipt, body)
        assert response.status_code == 201
        aid = response.json()["id"]
    with store.tx() as c:
        original_draft = dict(
            c.execute(select(app_drafts).where(app_drafts.c.id == aid)).mappings().one()
        )
    text = SOURCE.read_bytes().decode()
    md = client.post(
        f"/api/projects/{pid}/resources",
        json={"name": "already authorized synthetic.md", "format": "md", "content": text},
    ).json()["id"]
    # Explicit test setup establishes legitimate MD rights BEFORE corruption/revocation.
    with store.tx() as c:
        store.add_grants(c, user, original_draft["runtime_id"], pid, md, ["resource.read"])
        c.execute(update(grants).where(grants.c.resource_id == original).values(revoked=True))
    assert client.get(f"/api/apps/{aid}").status_code == 403
    forged = candidate(md, text)
    forged["manifest"]["app_id"] = aid
    with store.tx() as c:
        c.execute(
            update(app_drafts)
            .where(app_drafts.c.id == aid)
            .values(candidate=forged, fingerprint=fingerprint(forged))
        )
    return aid, md, forged, output(md, text, "source_a"), original_draft


@pytest.mark.parametrize("family", ["goal", "preview"])
def test_independent_source_family_blocks_executor_replacement_before_approval(env, family):
    aid, md, forged, value, _ = switched_fixture(env, family)
    before = effects(env[0])
    actual = env[2].get(f"/api/apps/{aid}")
    protocol = replay(md, value)
    accepted = None
    rejection = None
    try:
        accepted = prepare_release(
            env[0],
            env[3],
            aid,
            fingerprint(forged),
            limits(env),
            {"term": value["term"]},
            replay=protocol,
        )
    except DomainError as exc:
        rejection = exc.code
    reached = {
        "family": family,
        "inspection_status": actual.status_code,
        "approval_created": accepted is not None,
        "rejection": rejection,
        "replay_rounds": len(protocol.requests),
        "run_created": False,
    }
    if accepted:
        release = commit_release(
            env[0], env[3], accepted["id"], accepted["fingerprint"], limits(env)
        )
        instance = create_instance(
            env[0], env[3], release["id"], release["fingerprint"], limits(env)
        )
        queued = app_jobs.enqueue(
            env[0],
            env[3],
            instance["id"],
            1,
            release["fingerprint"],
            {"term": value["term"]},
            "corrupt-source-family",
            limits(env),
        )
        reached["run_created"] = bool(queued["run_id"])
    print("ISOLATED_SOURCE_FAMILY_RESULT", reached)
    assert actual.status_code == 409, reached
    assert rejection == "VERSION_CONFLICT" and accepted is None, reached
    assert not protocol.requests
    assert effects(env[0]) == before


def assert_blocked(env, aid, forged):
    with env[0].tx() as c:
        c.execute(
            update(app_drafts)
            .where(app_drafts.c.id == aid)
            .values(candidate=forged, fingerprint=fingerprint(forged))
        )
    before = effects(env[0])
    protocol = replay("unused", {})
    assert env[2].get(f"/api/apps/{aid}").status_code == 409
    with pytest.raises(DomainError) as caught:
        prepare_release(env[0], env[3], aid, fingerprint(forged), limits(env), {}, replay=protocol)
    assert caught.value.code == "VERSION_CONFLICT"
    assert not protocol.requests
    assert effects(env[0]) == before


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate",
        "conflict",
        "owner",
        "extra_claim",
        "actions_none",
        "executor_none",
        "actions_empty",
    ],
)
def test_independent_marker_conflict_and_malformed_executor_fail_closed(env, mutation):
    from sqlalchemy import insert

    from sim2act.db import goal_candidate_requests, preview_extractions

    card, _ = setup_card(env)
    aid = create_candidate(env, card).json()["id"]
    with env[0].tx() as c:
        forged = copy.deepcopy(
            c.execute(select(app_drafts.c.candidate).where(app_drafts.c.id == aid)).scalar_one()
        )
        row = dict(
            c.execute(
                select(goal_candidate_requests).where(goal_candidate_requests.c.app_id == aid)
            )
            .mappings()
            .one()
        )
        if mutation == "duplicate":
            row["request_key"] = "duplicate-marker"
            c.execute(insert(goal_candidate_requests).values(**row))
        elif mutation == "conflict":
            c.execute(
                insert(preview_extractions).values(
                    preview_id="synthetic-conflict",
                    principal_id=env[3],
                    request_key="conflict",
                    request_fingerprint="0" * 64,
                    app_id=aid,
                    snapshot={},
                )
            )
        elif mutation == "owner":
            c.execute(
                update(goal_candidate_requests)
                .where(goal_candidate_requests.c.app_id == aid)
                .values(principal_id="other-owner")
            )
    if mutation == "extra_claim":
        forged["agent_provenance"] = {}
    elif mutation == "actions_none":
        forged["actions"] = None
    elif mutation == "executor_none":
        forged["actions"][0]["executor"] = None
    elif mutation == "actions_empty":
        forged["actions"] = []
    assert_blocked(env, aid, forged)


@pytest.mark.parametrize(
    "snapshot",
    [
        None,
        [],
        {},
        {"kind": "unknown"},
        {"kind": "agent_source.v2"},
        {"kind": "completed_fixed_csv_task", "proof": {"kind": "completed_fixed_csv_task"}},
    ],
)
def test_unknown_task_marker_never_dispatches_as_initial_candidate(env, snapshot):
    from sqlalchemy import insert

    from sim2act.db import task_extractions

    aid = (
        env[2]
        .post(
            f"/api/projects/{env[-2]}/apps/csv-preview",
            json={"name": "fixture", "resource_id": env[-1], "goal": "fixture"},
        )
        .json()["id"]
    )
    with env[0].tx() as c:
        forged = copy.deepcopy(
            c.execute(select(app_drafts.c.candidate).where(app_drafts.c.id == aid)).scalar_one()
        )
        c.execute(
            insert(task_extractions).values(
                task_id="synthetic-task",
                principal_id=env[3],
                request_key="unknown",
                request_fingerprint="0" * 64,
                app_id=aid,
                snapshot=snapshot,
            )
        )
    assert_blocked(env, aid, forged)


@pytest.mark.parametrize(
    "field", ["generation", "extraction", "task_proof", "agent_provenance", "task_origin"]
)
def test_initial_candidate_cannot_claim_unrecorded_source_family(env, field):
    aid = (
        env[2]
        .post(
            f"/api/projects/{env[-2]}/apps/csv-preview",
            json={"name": "fixture", "resource_id": env[-1], "goal": "fixture"},
        )
        .json()["id"]
    )
    with env[0].tx() as c:
        forged = copy.deepcopy(
            c.execute(select(app_drafts.c.candidate).where(app_drafts.c.id == aid)).scalar_one()
        )
    if field == "task_origin":
        forged["manifest"]["origin"] = "task_run"
        forged["manifest"]["source_run_ref"] = "unrecorded-run"
    else:
        forged[field] = {}
    assert_blocked(env, aid, forged)


@pytest.mark.parametrize("preserve_claim", [False, True])
def test_agent_extraction_cannot_replace_executor_with_authorized_csv(env, preserve_claim):
    from test_bounded_agent_apps import extract_agent_candidate, run, setup, verified_source

    runtime, ids, texts, _, _, rel, inst, value = setup(env)
    accepted, result = run(env, inst, rel, ids[0], value)
    assert result["status"] == "SUCCEEDED"
    with env[0].tx() as c:
        proof = verified_source(env[0], c, env[3], accepted["run_id"], limits(env))
    made = extract_agent_candidate(
        env[0],
        env[3],
        accepted["run_id"],
        fingerprint(proof),
        candidate(ids[1], texts[1]),
        runtime,
        "derived",
        "reverse",
        limits(env),
    )
    # The original CSV app sharing this runtime already has legitimate CSV tool grants.
    with env[0].tx() as c:
        drafts = (
            c.execute(select(app_drafts).where(app_drafts.c.runtime_id == runtime)).mappings().all()
        )
        csv = next(
            d
            for d in drafts
            if d["candidate"]["actions"][0]["executor"]["kind"] == "registered_tool"
        )
        forged = copy.deepcopy(csv["candidate"])
        derived = next(d for d in drafts if d["id"] == made["id"])
        if preserve_claim:
            forged["agent_provenance"] = derived["candidate"]["agent_provenance"]
        forged["manifest"]["app_id"] = made["id"]
    assert_blocked(env, made["id"], forged)


def test_legacy_csv_task_marker_cannot_become_initial_agent(env):
    from test_local_task_retirement import extract as extract_task
    from test_local_task_retirement import setup_completed

    task, _, body, _ = setup_completed(env)
    aid = extract_task(env[2], task, body)
    text = SOURCE.read_bytes().decode()
    md = (
        env[2]
        .post(
            f"/api/projects/{env[-2]}/resources",
            json={"name": "legal.md", "format": "md", "content": text},
        )
        .json()["id"]
    )
    with env[0].tx() as c:
        old = c.execute(select(app_drafts).where(app_drafts.c.id == aid)).mappings().one()
        env[0].add_grants(c, env[3], old["runtime_id"], env[-2], md, ["resource.read"])
    forged = candidate(md, text)
    forged["manifest"]["app_id"] = aid
    assert_blocked(env, aid, forged)
