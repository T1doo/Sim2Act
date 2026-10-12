"""SIMULATED owner declarations, actual SQLite/HTTP/normal Worker evidence.

No fixture choice constitutes the real user's semantic acceptance.
"""

import copy
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select, update
from test_goal_text_applications import confirm, generate, release_instance, run_input, setup

from sim2act.db import (
    app_drafts,
    fingerprint,
    grants,
    internal_app_runs,
    internal_instance_data,
    internal_instances,
    internal_releases,
    principals,
    run_contracts,
    runs,
)


def flow(env):
    data = setup(env)
    rid, result, _ = generate(data)
    aid, _ = confirm(data, rid, result)
    release, instance = release_instance(data, aid)
    job = run_input(data, release, instance, {"term": "Beta"}, "owner-new-input")
    assert job["status"] == "SUCCEEDED"
    return data, release, instance, job


def path(instance):
    return f"/api/internal/instances/{instance['id']}/owner-review"


def state(data, instance, key=None):
    response = data[2].get(path(instance), params={"request_key": key} if key else {})
    assert response.status_code == 200, response.text
    value = response.json()
    assert value["principal_id"] == data[3]
    assert value["project_id"] == data[4]
    assert value["instance_id"] == instance["id"]
    assert value["app_id"] == instance["source_app_id"]
    return value


def prepare(data, release, instance, job, key="prepare", sequence=None):
    body = {
        "command": "PREPARE",
        "request_key": key,
        "expected_sequence": state(data, instance)["sequence"] if sequence is None else sequence,
        "expected_revision": instance["revision"],
        "expected_release_fingerprint": release["fingerprint"],
        "run_ids": [job["id"]],
    }
    response = data[2].post(path(instance) + "-requests", json=body)
    assert response.status_code == 201, response.text
    recovered = state(data, instance, key)["recovered"]
    assert recovered["id"] == response.json()["record"]["id"]
    return recovered, body


def choice_body(review, reject=False, key="decision"):
    return {
        "command": "DECIDE",
        "request_key": key,
        "expected_sequence": review["sequence"],
        "review_id": review["id"],
        "review_fingerprint": review["fingerprint"],
        "choices": [
            {
                "item_id": item["id"],
                "decision": "REJECT" if reject and n == 0 else "ACCEPT",
                "reason": "SIMULATED owner test choice; not real semantic signoff",
            }
            for n, item in enumerate(review["payload"]["contract"]["items"])
        ],
    }


def existing_rows(store):
    with store.tx() as c:
        return {
            t.name: [dict(x) for x in c.execute(select(t)).mappings()]
            for t in [
                principals,
                grants,
                app_drafts,
                internal_releases,
                internal_instances,
                internal_instance_data,
                internal_app_runs,
                runs,
                run_contracts,
            ]
        }


@pytest.mark.parametrize("reject", [False, True], ids=["accept", "reject"])
def test_owner_exact_explicit_decision(env, reject):
    data, release, instance, job = flow(env)
    before = existing_rows(data[0])
    review, _ = prepare(data, release, instance, job)
    contract = review["payload"]["contract"]
    assert contract["goal"] == data[-1]["content"]
    assert contract["source_goal"]["version"] == data[-1]["version"]
    assert contract["evidence"][0]["run_id"] == job["id"]
    assert contract["evidence"][0]["input"] == {"term": "Beta"}
    assert contract["evidence"][0]["actual_operations"][0]["receipt"]["status"] == "VERIFIED"
    assert state(data, instance)["owner_acceptance"] == "PENDING"
    body = choice_body(review, reject)
    response = data[2].post(path(instance) + "-requests", json=body)
    assert response.status_code == 201, response.text
    expected = "REJECTED" if reject else "ACCEPTED"
    current = state(data, instance)
    assert current["owner_acceptance"] == expected and current["sequence"] == 2
    assert current["formal_publication_enabled"] is False
    assert current["technical_semantic_status"] == "UNKNOWN"
    assert current["record"]["payload"]["choices"] == body["choices"]
    assert existing_rows(data[0]) == before
    assert state(data, instance, "decision")["recovered"]["status"] == expected
    replay = data[2].post(path(instance) + "-requests", json=body)
    assert replay.status_code == 201 and replay.json()["record"] == response.json()["record"]
    assert state(data, instance)["sequence"] == 2


@pytest.mark.parametrize(
    "mutation", ["missing", "reordered", "duplicate", "blank", "extra", "wrong_fp"]
)
def test_owner_cannot_lower_frozen_items(env, mutation):
    data, release, instance, job = flow(env)
    review, _ = prepare(data, release, instance, job)
    body = choice_body(review)
    if mutation == "missing":
        body["choices"].pop()
    if mutation == "reordered":
        body["choices"].reverse()
    if mutation == "duplicate":
        body["choices"][1] = copy.deepcopy(body["choices"][0])
    if mutation == "blank":
        body["choices"][0]["reason"] = " "
    if mutation == "extra":
        body["choices"][0]["technical_pass"] = True
    if mutation == "wrong_fp":
        body["review_fingerprint"] = "0" * 64
    assert data[2].post(path(instance) + "-requests", json=body).status_code in {400, 409, 422}
    assert state(data, instance)["sequence"] == 1


@pytest.mark.parametrize(
    "mutation",
    [
        "goal_head",
        "resource",
        "grant",
        "cancel_intent",
        "output",
        "run_version",
        "new_result",
        "active",
        "expiry",
    ],
)
def test_owner_commit_rechecks_real_current_context(env, monkeypatch, mutation):
    from sim2act.db import resources

    data, release, instance, job = flow(env)
    store, _, client, user, pid, text, card = data
    review, _ = prepare(data, release, instance, job)
    if mutation == "goal_head":
        content = {
            **card["content"],
            "expected_version": card["version"],
            "title": "New criteria version",
        }
        assert client.put(f"/api/goal-cards/{card['id']}", json=content).status_code == 200
    elif mutation == "new_result":
        run_input(data, release, instance, {"term": "owner"}, "owner-newer-result")
    elif mutation == "active":
        assert (
            client.post(
                f"/api/internal/instances/{instance['id']}/runs",
                json={
                    "expected_revision": 1,
                    "expected_release_fingerprint": release["fingerprint"],
                    "input": {"term": "owner"},
                    "request_key": "owner-still-queued",
                },
            ).status_code
            == 202
        )
    elif mutation == "expiry":
        now = time.time()
        monkeypatch.setattr("sim2act.owner_acceptance.time.time", lambda: now + 901)
    else:
        with store.tx() as c:
            if mutation == "resource":
                c.execute(update(resources).where(resources.c.id == text).values(content="changed"))
            if mutation == "grant":
                c.execute(
                    update(grants)
                    .where(
                        grants.c.project_id == pid,
                        grants.c.principal_id == user,
                        grants.c.resource_id == text,
                    )
                    .values(revoked=True, revision=2)
                )
            if mutation == "cancel_intent":
                c.execute(update(runs).where(runs.c.id == job["id"]).values(cancel_intent=True))
            if mutation == "output":
                c.execute(
                    update(internal_app_runs)
                    .where(internal_app_runs.c.id == job["app_run_id"])
                    .values(output={})
                )
            if mutation == "run_version":
                c.execute(
                    update(runs).where(runs.c.id == job["id"]).values(version=job["version"] + 1)
                )
    assert client.post(path(instance) + "-requests", json=choice_body(review)).status_code in {
        400,
        403,
        409,
    }
    current = state(data, instance)
    assert current["sequence"] == 1 and current["owner_acceptance"] != "ACCEPTED"
    if mutation in {"goal_head", "resource", "grant"}:
        assert (
            not current["content_access"] and "record" not in current and "current" not in current
        )
    assert state(data, instance, "prepare")["recovered"]["id"] == review["id"]


@pytest.mark.parametrize("kind", ["CANCEL", "REVOKE"])
def test_owner_stop_after_revocation_and_fresh_review(env, kind):
    data, release, instance, job = flow(env)
    store, _, client, user, pid, text, _ = data
    review, _ = prepare(data, release, instance, job)
    target = review
    if kind == "REVOKE":
        response = client.post(path(instance) + "-requests", json=choice_body(review))
        assert response.status_code == 201
        target = response.json()["record"]
    with store.tx() as c:
        before = [dict(x) for x in c.execute(select(grants)).mappings()]
        c.execute(
            update(grants)
            .where(
                grants.c.project_id == pid,
                grants.c.principal_id == user,
                grants.c.resource_id == text,
            )
            .values(revoked=True, revision=2)
        )
    body = {
        "command": kind,
        "request_key": "stop",
        "expected_sequence": target["sequence"],
        "target_id": target["id"],
        "target_fingerprint": target["fingerprint"],
        "reason": "SIMULATED stop",
    }
    response = client.post(path(instance) + "-requests", json=body)
    assert response.status_code == 201, response.text
    current = state(data, instance)
    assert current["owner_acceptance"] == ("CANCELLED" if kind == "CANCEL" else "REVOKED")
    assert (
        not current["content_access"]
        and "payload" not in state(data, instance, "stop")["recovered"]
    )
    with store.tx() as c:
        after = [dict(x) for x in c.execute(select(grants)).mappings()]
    assert all(
        x == y
        for x, y in zip(before, after, strict=True)
        if x["resource_id"] != text or x["principal_id"] != user
    )
    assert (
        client.post(path(instance) + "-requests", json=choice_body(review, key="late")).status_code
        == 409
    )


def test_owner_concurrent_decision_only_one_and_new_review_no_old_accept(env):
    data, release, instance, job = flow(env)
    review, _ = prepare(data, release, instance, job)
    bodies = [choice_body(review, key=f"parallel-{n}") for n in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda b: data[2].post(path(instance) + "-requests", json=b), bodies)
        )
    assert sorted(r.status_code for r in results) == [201, 409]
    accepted_key = next(
        b["request_key"] for b, r in zip(bodies, results, strict=True) if r.status_code == 201
    )
    old = state(data, instance, accepted_key)["recovered"]
    newer, _ = prepare(data, release, instance, job, key="recheck")
    assert newer["id"] != review["id"] and state(data, instance)["owner_acceptance"] == "PENDING"
    recovered = state(data, instance, accepted_key)
    assert (
        recovered["recovered"]["id"] == old["id"] and recovered["recovered"]["status"] == "ACCEPTED"
    )
    assert recovered["owner_acceptance"] == "PENDING"


@pytest.mark.parametrize(
    "damage", ["delete_record", "delete_seal", "resign_payload", "lower_sequence"]
)
def test_owner_history_cannot_delete_latest_or_resign_to_reactivate(env, damage):
    from sqlalchemy import delete

    from sim2act.db import internal_owner_records, internal_owner_seals

    data, release, instance, job = flow(env)
    review, _ = prepare(data, release, instance, job)
    assert data[2].post(path(instance) + "-requests", json=choice_body(review)).status_code == 201
    newer, _ = prepare(data, release, instance, job, key="recheck")
    with data[0].tx() as c:
        if damage == "delete_record":
            c.execute(
                delete(internal_owner_records).where(internal_owner_records.c.id == newer["id"])
            )
        if damage == "delete_seal":
            c.execute(
                delete(internal_owner_seals).where(internal_owner_seals.c.record_id == newer["id"])
            )
        if damage == "lower_sequence":
            c.execute(
                update(internal_owner_records)
                .where(internal_owner_records.c.id == newer["id"])
                .values(sequence=10)
            )
        if damage == "resign_payload":
            value = copy.deepcopy(newer["payload"])
            value["contract"]["items"] = []
            c.execute(
                update(internal_owner_records)
                .where(internal_owner_records.c.id == newer["id"])
                .values(payload=value, fingerprint=fingerprint(value))
            )
    response = data[2].get(path(instance))
    assert response.status_code == 409, response.text


def test_owner_wrong_identity_missing_key_no_write_and_key_intent_conflict(env):
    data, release, instance, job = flow(env)
    review, body = prepare(data, release, instance, job)
    before = state(data, instance)["sequence"]
    assert data[2].get(path(instance), params={"request_key": "unknown"}).status_code == 409
    changed = {**body, "run_ids": []}
    assert data[2].post(path(instance) + "-requests", json=changed).status_code == 422
    changed = {**body, "expected_revision": 2}
    assert data[2].post(path(instance) + "-requests", json=changed).status_code == 409
    for headers in [{"Authorization": "Bearer synthetic-test-B"}, {"Authorization": ""}]:
        assert data[2].get(path(instance), headers=headers).status_code in {401, 403}
        assert data[2].post(
            path(instance) + "-requests", json=choice_body(review), headers=headers
        ).status_code in {401, 403}
    assert state(data, instance)["sequence"] == before


@pytest.mark.parametrize("invalid", ["sample", "failed", "foreign", "unknown"])
def test_owner_selects_only_proven_current_new_input(env, invalid):
    from sim2act.db import operations

    data, release, instance, job = flow(env)
    if invalid == "sample":
        job = run_input(data, release, instance, {"term": "Alpha"}, "same-sample")
    if invalid == "failed":
        job = run_input(data, release, instance, {"term": " Beta"}, "invalid-input")
    if invalid == "foreign":
        other = data[2].post(
            f"/api/internal/releases/{release['id']}/instances",
            json={"expected_release_fingerprint": release["fingerprint"], "request_key": "other"},
        )
        assert other.status_code == 201
        job = run_input(data, release, other.json(), {"term": "Beta"}, "foreign-instance")
    if invalid == "unknown":
        with data[0].tx() as c:
            c.execute(
                update(operations)
                .where(operations.c.run_id == job["id"], operations.c.call_id == "instance_result")
                .values(status="OUTCOME_UNKNOWN")
            )
    before = existing_rows(data[0])
    response = data[2].post(
        path(instance) + "-requests",
        json={
            "command": "PREPARE",
            "request_key": "invalid-evidence",
            "expected_sequence": 0,
            "expected_revision": instance["revision"],
            "expected_release_fingerprint": release["fingerprint"],
            "run_ids": [job["id"]],
        },
    )
    assert response.status_code in {400, 403, 409}, response.text
    assert existing_rows(data[0]) == before
    assert state(data, instance)["sequence"] == 0


@pytest.mark.parametrize("change", ["new_result", "goal_aba", "instance_aba"])
def test_owner_accepted_exact_version_cannot_survive_changes_or_aba(env, change):
    data, release, instance, job = flow(env)
    review, _ = prepare(data, release, instance, job)
    body = choice_body(review)
    assert data[2].post(path(instance) + "-requests", json=body).status_code == 201
    assert state(data, instance)["owner_acceptance"] == "ACCEPTED"
    if change == "new_result":
        run_input(data, release, instance, {"term": "owner"}, "newer-after-accept")
    elif change == "goal_aba":
        card = data[-1]
        for title in ["Changed goal title", card["content"]["title"]]:
            response = data[2].put(
                f"/api/goal-cards/{card['id']}",
                json={**card["content"], "title": title, "expected_version": card["version"]},
            )
            assert response.status_code == 200
            card = data[2].get(f"/api/goal-cards/{card['id']}").json()
        assert card["content"] == data[-1]["content"] and card["version"] == 3
    else:
        other_release, _ = release_instance(data, instance["source_app_id"])
        for target in [other_release, release]:
            current = data[2].get(f"/api/internal/instances/{instance['id']}").json()
            response = data[2].post(
                f"/api/internal/instances/{instance['id']}/switch-approvals",
                json={
                    "target_release_id": target["id"],
                    "expected_target_fingerprint": target["fingerprint"],
                    "expected_revision": current["revision"],
                },
            )
            assert response.status_code == 201, response.text
            approval = response.json()
            response = data[2].post(
                f"/api/internal/instances/{instance['id']}/switch-approvals/{approval['id']}/commit",
                json={"fingerprint": approval["fingerprint"]},
            )
            assert response.status_code == 200, response.text
        assert response.json()["revision"] == 3
        assert response.json()["release_id"] == release["id"]
    current = state(data, instance, "decision")
    assert current["owner_acceptance"] == "STALE" and current["sequence"] == 2
    assert current["recovered"]["status"] == "ACCEPTED" and "payload" not in current["recovered"]
    assert data[2].post(path(instance) + "-requests", json=body).status_code == 201
    assert state(data, instance)["owner_acceptance"] == "STALE"


def test_owner_budget_reserves_explicit_revocation(env, monkeypatch):
    data, release, instance, job = flow(env)
    monkeypatch.setattr("sim2act.owner_acceptance.MAX_RECORDS", 3)
    review, _ = prepare(data, release, instance, job)
    response = data[2].post(path(instance) + "-requests", json=choice_body(review))
    assert response.status_code == 201
    last = response.json()["record"]
    response = data[2].post(
        path(instance) + "-requests",
        json={
            "command": "PREPARE",
            "request_key": "budget-full",
            "expected_sequence": 2,
            "expected_revision": 1,
            "expected_release_fingerprint": release["fingerprint"],
            "run_ids": [job["id"]],
        },
    )
    assert response.status_code == 400 and response.json()["error"]["code"] == "BUDGET_EXHAUSTED"
    response = data[2].post(
        path(instance) + "-requests",
        json={
            "command": "REVOKE",
            "request_key": "last-stop",
            "expected_sequence": 2,
            "target_id": last["id"],
            "target_fingerprint": last["fingerprint"],
            "reason": "SIMULATED explicit stop at budget boundary",
        },
    )
    assert response.status_code == 201
    assert state(data, instance)["owner_acceptance"] == "REVOKED"


@pytest.mark.parametrize("command", ["PREPARE", "DECIDE"])
def test_owner_earlier_payload_corruption_blocks_new_content_commit(env, command):
    from sim2act.db import internal_owner_records, internal_owner_seals

    data, release, instance, job = flow(env)
    original, _ = prepare(data, release, instance, job)
    assert data[2].post(path(instance) + "-requests", json=choice_body(original)).status_code == 201
    target = original
    if command == "DECIDE":
        target, _ = prepare(data, release, instance, job, key="latest-preview")
    with data[0].tx() as c:
        corrupt = copy.deepcopy(original["payload"])
        corrupt["contract"]["items"][0]["text"] = "CORRUPTED earlier audit payload"
        c.execute(
            update(internal_owner_records)
            .where(internal_owner_records.c.id == original["id"])
            .values(payload=corrupt)
        )
        records = [dict(x) for x in c.execute(select(internal_owner_records)).mappings()]
        seals = [dict(x) for x in c.execute(select(internal_owner_seals)).mappings()]
    current = state(data, instance)
    assert current["owner_acceptance"] == "STALE" and not current["content_access"]
    body = (
        {
            "command": "PREPARE",
            "request_key": "direct-api-after-corruption",
            "expected_sequence": current["sequence"],
            "expected_revision": instance["revision"],
            "expected_release_fingerprint": release["fingerprint"],
            "run_ids": [job["id"]],
        }
        if command == "PREPARE"
        else choice_body(target, key="direct-api-after-corruption")
    )
    response = data[2].post(path(instance) + "-requests", json=body)
    assert response.status_code == 409, response.text
    with data[0].tx() as c:
        assert [dict(x) for x in c.execute(select(internal_owner_records)).mappings()] == records
        assert [dict(x) for x in c.execute(select(internal_owner_seals)).mappings()] == seals
