"""Same saved P-A app/Release/instance: explicit new material, actual Worker."""

import copy
import hashlib
import json
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, insert, select, update
from test_natural_spec_apps import COLD, SOURCE, enqueue, material, ready, setup, transport
from test_natural_spec_owner_acceptance import decision, preview, state
from test_pb_natural_specs import drive_to_success
from test_pb_natural_use_read_gates import TypedPrivateBarrier
from test_pb_natural_uses import THIRD
from test_spec_app_operations import snapshot

from sim2act import natural_specs as natural
from sim2act import pb_natural_uses as use
from sim2act.api import create_app
from sim2act.db import (
    Store,
    attempts,
    delivery_graph_requests,
    fingerprint,
    goal_cards,
    grants,
    internal_instance_data,
    internal_instances,
    new_id,
    operations,
    runs,
)
from sim2act.worker import Worker


def base_pa(env):
    data = setup(env)
    _, aid, release, inst, _ = ready(data)
    original = enqueue(data, release, inst)
    drive_to_success(data, original, transport([]))
    app = data[2].get("/api/apps/" + aid).json()
    return data, app, release, inst, original


def target_use(data, app, release, inst, content, key):
    resource, goal = material(data[2], data[4], content, "Exact P-A use Goal " + key)
    body = dict(
        expected_revision=inst["revision"],
        expected_release_fingerprint=release["fingerprint"],
        expected_app_fingerprint=app["fingerprint"],
        expected_recipe_fingerprint=fingerprint(app["candidate"]["spec_recipe"]),
        resource_id=resource,
        card_id=goal["id"],
        expected_goal_version=goal["version"],
        expected_goal_fingerprint=goal["fingerprint"],
        expected_source_hash=hashlib.sha256(content.encode()).hexdigest(),
        request_key=key,
    )
    return resource, goal, body


def prepare(data, route, body):
    before = snapshot(data[0])
    response = data[2].post(route + "/pa-use-reviews", json=body)
    assert response.status_code == 200, response.text
    assert snapshot(data[0]) == before
    checked = response.json()
    commit = dict(
        review=body,
        expected_review_fingerprint=checked["review_fingerprint"],
        consent=use.PA_CONSENT,
    )
    return checked, commit


def prepared_pa(env, history=False):
    data, app, release, inst, original = base_pa(env)
    route = "/api/internal/instances/" + inst["id"]
    if history:
        _, _, second_body = target_use(data, app, release, inst, COLD, "second-same-pa")
        _, second_commit = prepare(data, route, second_body)
        second = data[2].post(route + "/pa-use-runs", json=second_commit)
        assert second.status_code == 202, second.text
        drive_to_success(data, second.json()["run_id"], transport([], COLD))
    resource, goal, body = target_use(data, app, release, inst, THIRD, "third-same-pa")
    return data, app, release, inst, original, resource, goal, body, route


def test_same_saved_pa_third_material_cold_worker_and_fresh_owner(env, tmp_path):
    data, app, release, inst, original, resource, goal, body, route = prepared_pa(env, history=True)
    before = snapshot(data[0])
    checked, commit = prepare(data, route, body)
    assert checked["namespace"] == use.PA.namespace and checked["instance_data_version"] == 2
    assert checked["effective_candidate"]["manifest"]["origin"] == "goal"
    assert "spec_task" not in checked["effective_candidate"]
    assert checked["effective_candidate"]["spec_recipe"] == app["candidate"]["spec_recipe"]
    assert checked["real_model_allowance"] == 0 and checked["new_model_requests"] == 0
    queued = data[2].post(route + "/pa-use-runs", json=commit)
    assert queued.status_code == 202, queued.text
    rid = queued.json()["run_id"]
    assert rid != original
    cold = Store(data[1].database_url, test_only=True)
    try:
        client = TestClient(create_app(cold, data[1]))
        client.headers["Authorization"] = "Bearer synthetic-test-A"
        current = (cold, data[1], client, *data[3:])
        received = client.get(route + "/pa-use-requests/" + body["request_key"])
        assert received.status_code == 200 and received.json()["reviewed"] == checked, received.text
        sent = []
        drive_to_success(current, rid, transport(sent, THIRD))
        result = client.get("/api/internal/app-run-jobs/" + rid + "/spec-artifact")
        assert result.status_code == 200, result.text
        checklist = json.loads(result.json()["resource"]["content"])
        assert (
            checklist["source_content"] == THIRD and checklist["source"]["resource_id"] == resource
        )
        assert (
            checklist["owner_acceptance"] == "PENDING"
            and checklist["semantic_goal_acceptance"] == "NOT_RUN"
        )
        assert (
            len(sent) == 1
            and THIRD in json.dumps(sent)
            and SOURCE not in json.dumps(sent)
            and COLD not in json.dumps(sent)
        )
        after = snapshot(cold)
        for table in [
            "app_drafts",
            "internal_releases",
            "goal_cards",
            "goal_card_versions",
            "natural_owner_records",
            "natural_owner_seals",
        ]:
            assert after[table] == before[table]
        assert all(
            row in after["internal_instance_data"] for row in before["internal_instance_data"]
        )
        assert sorted(
            r["version"] for r in after["internal_instance_data"] if r["instance_id"] == inst["id"]
        ) == [1, 2, 3]
        before_cached = snapshot(cold)
        cached = client.post(route + "/pa-use-runs", json=commit)
        assert (
            cached.status_code == 202 and cached.json()["run_id"] == rid and cached.json()["cached"]
        ), cached.text
        assert snapshot(cold) == before_cached
        path = route + "/runs/" + rid + "/spec-owner-review"
        s = state(current, path)
        assert s["current"]["source_goal"]["card_id"] == goal["id"] and s["latest"] is None
        reviewed, _ = preview(current, path)
        accepted = client.post(path + "-requests", json=decision(reviewed))
        assert accepted.status_code == 201 and accepted.json()["status"] == "ACCEPTED", (
            accepted.text
        )
        assert checklist["owner_acceptance"] == "PENDING"
        (tmp_path / "third-proof.json").write_text(
            json.dumps(
                dict(
                    review=checked,
                    receipt=received.json(),
                    result=result.json(),
                    wire=sent,
                    same_app=True,
                    same_release=True,
                    typed_versions=[1, 2, 3],
                    real_model_requests=0,
                    fresh_owner=accepted.json(),
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        client.close()
    finally:
        cold.engine.dispose()


def test_illegal_inputs_and_cross_family_no_partial_write(env, tmp_path):
    data, app, release, inst, _, resource, goal, body, route = prepared_pa(env)
    _, commit = prepare(data, route, body)
    outcomes = []
    for field, wrong in [
        ("expected_revision", 0),
        ("resource_id", data[5]),
        ("card_id", "goal_" + "0" * 32),
        ("expected_source_hash", "0" * 64),
        ("expected_goal_fingerprint", "0" * 64),
        ("expected_recipe_fingerprint", "0" * 64),
        ("expected_release_fingerprint", "0" * 64),
        ("expected_app_fingerprint", "0" * 64),
    ]:
        bad = copy.deepcopy(commit)
        bad["review"][field] = wrong
        before = snapshot(data[0])
        response = data[2].post(route + "/pa-use-runs", json=bad)
        assert response.status_code in (403, 409, 422), response.text
        assert snapshot(data[0]) == before
        outcomes.append(dict(field=field, status=response.status_code, error=response.json()))
    for bad in [
        {**commit, "expected_review_fingerprint": "0" * 64},
        {**commit, "consent": use.CONSENT},
    ]:
        before = snapshot(data[0])
        r = data[2].post(route + "/pa-use-runs", json=bad)
        assert r.status_code in (409, 422) and snapshot(data[0]) == before, r.text
    before = snapshot(data[0])
    other = data[2].post(route + "/pb-use-reviews", json=body)
    assert other.status_code == 409 and snapshot(data[0]) == before, other.text
    with data[0].tx() as c:
        c.execute(update(goal_cards).where(goal_cards.c.id == goal["id"]).values(version=2))
    before = snapshot(data[0])
    r = data[2].post(route + "/pa-use-runs", json=commit)
    assert r.status_code == 409 and snapshot(data[0]) == before, r.text
    (tmp_path / "illegal-proof.json").write_text(json.dumps(outcomes, indent=2))


@pytest.mark.parametrize(
    "fault",
    ["target_revoke", "save_revoke", "cancel", "goal", "instance_revision", "bad_output", "fence"],
)
def test_late_pa_target_result_cannot_commit(env, tmp_path, fault):
    data, app, release, inst, _, resource, goal, body, route = prepared_pa(env)
    _, commit = prepare(data, route, body)
    queued = data[2].post(route + "/pa-use-runs", json=commit)
    assert queued.status_code == 202, queued.text
    rid = queued.json()["run_id"]
    before = snapshot(data[0])
    sent = []

    def mutate(raw, payload):
        if fault == "bad_output":
            value = json.loads(raw["choices"][0]["message"]["content"])
            value["items"][0]["citations"][0]["quote"] = "not third source"
            raw["choices"][0]["message"]["content"] = json.dumps(value)
        else:
            with data[0].tx() as c:
                if fault == "cancel":
                    c.execute(update(runs).where(runs.c.id == rid).values(cancel_intent=True))
                elif fault == "goal":
                    c.execute(
                        update(goal_cards).where(goal_cards.c.id == goal["id"]).values(version=2)
                    )
                elif fault == "instance_revision":
                    c.execute(
                        update(internal_instances)
                        .where(internal_instances.c.id == inst["id"])
                        .values(revision=2)
                    )
                elif fault == "fence":
                    c.execute(update(runs).where(runs.c.id == rid).values(fence=99))
                else:
                    c.execute(
                        update(grants)
                        .where(
                            grants.c.principal_id == inst["runtime_id"],
                            grants.c.resource_id
                            == (data[4] if fault == "save_revoke" else resource),
                        )
                        .values(revoked=True)
                    )

    assert Worker(data[0], data[1], goal_planner_transport=transport(sent, THIRD, mutate)).once()
    with data[0].tx() as c:
        assert not c.execute(
            select(internal_instance_data).where(
                internal_instance_data.c.run_id == queued.json()["app_run_id"]
            )
        ).first()
        assert not c.execute(
            select(operations.c.id).where(
                operations.c.run_id == rid, operations.c.tool_ref == natural.SAVE
            )
        ).first()
        attempt = dict(c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().one())
        assert attempt["status"] == "REJECTED_KNOWN" and attempt["response"]["received_raw"]
    for table in [
        "app_drafts",
        "internal_releases",
        "internal_instance_data",
        "natural_owner_records",
        "natural_owner_seals",
    ]:
        assert snapshot(data[0])[table] == before[table]
    assert len(sent) == 1
    (tmp_path / "late-proof.json").write_text(
        json.dumps(
            dict(fault=fault, attempt=attempt, typed_saves=0, real_model_requests=0), indent=2
        )
    )


@pytest.mark.parametrize("fault", ["revoke", "missing-seals"])
def test_target_read_gates_and_no_default_downgrade(env, tmp_path, fault):
    data, app, release, inst, original, resource, goal, body, route = prepared_pa(env)
    _, commit = prepare(data, route, body)
    queued = data[2].post(route + "/pa-use-runs", json=commit)
    assert queued.status_code == 202, queued.text
    rid, aid = queued.json()["run_id"], queued.json()["app_run_id"]
    with data[0].tx() as c:
        if fault == "revoke":
            c.execute(
                update(grants)
                .where(
                    grants.c.principal_id == inst["runtime_id"], grants.c.resource_id == resource
                )
                .values(revoked=True)
            )
        else:
            c.execute(
                delete(delivery_graph_requests).where(
                    delivery_graph_requests.c.app_id == rid,
                    delivery_graph_requests.c.kind.in_([use.PA.meta, use.PA.meta + "_seal"]),
                )
            )
    before = snapshot(data[0])
    proof = []
    with TypedPrivateBarrier(data[0], rid, aid, resource) as barrier:
        for method, path, b in [
            ("GET", route + "/pa-use-requests/" + body["request_key"], None),
            ("POST", route + "/pa-use-runs", commit),
            ("GET", "/api/internal/app-run-jobs/" + rid + "/spec-artifact", None),
            ("GET", route, None),
            ("GET", "/api/internal/apps/" + app["id"] + "/instances", None),
        ]:
            response = data[2].request(method, path, json=b)
            assert response.status_code in (403, 409), response.text
            proof.append(dict(path=path, status=response.status_code))
        assert not barrier.blocked and not barrier.full_binding_reads
        assert data[2].get(route + "/runs/" + original).status_code == 200
    assert snapshot(data[0]) == before
    (tmp_path / "read-gate-proof.json").write_text(
        json.dumps(
            dict(
                fault=fault,
                requests=proof,
                blocked=barrier.blocked,
                full_binding_reads=barrier.full_binding_reads,
            ),
            indent=2,
        )
    )


def test_actual_pa_cancel_after_target_revocation(env, tmp_path):
    data, app, release, inst, _, resource, goal, body, route = prepared_pa(env)
    _, commit = prepare(data, route, body)
    queued = data[2].post(route + "/pa-use-runs", json=commit)
    assert queued.status_code == 202, queued.text
    rid = queued.json()["run_id"]
    with data[0].tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == resource).values(revoked=True))
    status = data[2].get(route + "/runs/" + rid + "/control-status")
    assert status.status_code == 200, status.text
    response = data[2].post(
        route + "/runs/" + rid + "/commands",
        json=dict(command="cancel", version=status.json()["version"]),
    )
    assert response.status_code == 200, response.text
    sent = []
    Worker(data[0], data[1], goal_planner_transport=transport(sent, THIRD)).once()
    with data[0].tx() as c:
        assert c.execute(select(runs.c.status).where(runs.c.id == rid)).scalar_one() == "CANCELLED"
        assert not c.execute(select(attempts.c.id).where(attempts.c.run_id == rid)).first()
    assert not sent
    (tmp_path / "cancel-proof.json").write_text(
        json.dumps(dict(response=response.json(), actual_worker=True, model_requests=0), indent=2)
    )


def test_natural_pa_grant_expiry_invalidates_preview(env, tmp_path):
    data, app, release, inst, _, resource, goal, body, route = prepared_pa(env)
    expires = time.time() + 10
    with data[0].tx() as c:
        c.execute(
            insert(grants).values(
                id=new_id("grant"),
                principal_id=inst["runtime_id"],
                project_id=data[4],
                resource_id=resource,
                tool_ref=natural.READ,
                expires_at=expires,
                revision=1,
                revoked=False,
            )
        )
    checked, commit = prepare(data, route, body)
    assert checked["approved_grant_state"][0]["effective"] is True
    before = snapshot(data[0])
    time.sleep(max(0, expires - time.time()) + 0.05)
    r = data[2].post(route + "/pa-use-runs", json=commit)
    assert r.status_code == 409 and snapshot(data[0]) == before, r.text
    (tmp_path / "expiry-proof.json").write_text(
        json.dumps(dict(expires=expires, confirmed=time.time(), error=r.json()), indent=2)
    )
