"""The same saved P-B logic/Release/instance explicitly runs unseen third input."""
import hashlib
import json

from fastapi.testclient import TestClient
from sqlalchemy import select
from test_natural_spec_apps import COLD, enqueue, material, transport
from test_pa_spec_apps import instance
from test_pb_natural_specs import drive_to_success, prepare, preview_commit
from test_spec_app_operations import snapshot

from sim2act import pb_natural_uses as use
from sim2act.api import create_app
from sim2act.db import Store, app_drafts, internal_instance_data, internal_releases

THIRD = "The field beacon transmits twice per day while solar power is available. During a storm it keeps a cached signal. The beacon night policy has yet to be agreed."


def prepared_use(env, run_base=False):
    prepared = prepare(env)
    data, _, _, _, _, path, _, _ = prepared
    _, extraction = preview_commit(prepared)
    saved = data[2].post(path + "/extractions", json=extraction)
    assert saved.status_code == 201, saved.text
    app = data[2].get(f"/api/apps/{saved.json()['id']}").json()
    release, inst = instance(data, app["id"])
    if run_base:
        original_run = enqueue(data, release, inst)
        drive_to_success(data, original_run, transport([], COLD))
    resource, goal = material(data[2], data[4], THIRD, "Third material for the SAME saved logic")
    body = dict(expected_revision=inst["revision"], expected_release_fingerprint=release["fingerprint"],
        expected_app_fingerprint=app["fingerprint"],
        expected_recipe_fingerprint=app["candidate"]["spec_task"]["edited_recipe_fingerprint"],
        resource_id=resource, card_id=goal["id"], expected_goal_version=goal["version"],
        expected_goal_fingerprint=goal["fingerprint"], expected_source_hash=hashlib.sha256(THIRD.encode()).hexdigest(),
        request_key="third-use-original-key")
    route=f"/api/internal/instances/{inst['id']}"
    return data, app, release, inst, resource, goal, body, route


def test_same_saved_logic_third_material_cold_worker(env, tmp_path):
    data, app, release, inst, resource, goal, body, route = prepared_use(env, run_base=True)
    before = snapshot(data[0])
    response = data[2].post(route + "/pb-use-reviews", json=body)
    assert response.status_code == 200, response.text
    checked = response.json()
    assert snapshot(data[0]) == before
    assert checked["app_id"] == app["id"] and checked["release_id"] == release["id"]
    assert checked["effective_candidate"]["spec_recipe"] == app["candidate"]["spec_recipe"]
    commit = dict(review=body, expected_review_fingerprint=checked["review_fingerprint"], consent=use.CONSENT)
    queued = data[2].post(route + "/pb-use-runs", json=commit)
    assert queued.status_code == 202, queued.text
    rid = queued.json()["run_id"]
    cold = Store(data[1].database_url, test_only=True)
    try:
        with TestClient(create_app(cold, data[1])) as client:
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            current = (cold, data[1], client, *data[3:])
            received = client.get(route + "/pb-use-requests/" + body["request_key"])
            assert received.status_code == 200, received.text
            assert received.json()["reviewed"] == checked
            sent = []
            drive_to_success(current, rid, transport(sent, THIRD))
            result = client.get(f"/api/internal/app-run-jobs/{rid}/spec-artifact")
            assert result.status_code == 200, result.text
            assert json.loads(result.json()["resource"]["content"])["source_content"] == THIRD
            assert json.loads(result.json()["resource"]["content"])["source"]["resource_id"] == resource
            assert len(sent) == 1 and THIRD in json.dumps(sent)
            with cold.tx() as c:
                assert dict(c.execute(select(app_drafts).where(app_drafts.c.id == app["id"])).mappings().one()) == next(r for r in before["app_drafts"] if r["id"] == app["id"])
                assert {r["id"]: dict(r) for r in c.execute(select(internal_releases)).mappings()} == {r["id"]: r for r in before["internal_releases"]}
                rows = c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id == inst["id"])).mappings().all()
                assert len(rows) == 2 and sorted(r["version"] for r in rows) == [1, 2]
                previous = [r for r in before["internal_instance_data"] if r["instance_id"] == inst["id"]]
                assert all(dict(r) in [dict(x) for x in rows] for r in previous)
            (tmp_path / "third-material-proof.json").write_text(json.dumps(dict(review=checked, receipt=received.json(),
                result=result.json(), wire=sent, same_app=True, same_release=True, real_model_requests=0), ensure_ascii=False, indent=2))
    finally:
        cold.engine.dispose()


def test_reject_stale_illegal_inputs_without_partial_writes(env, tmp_path):
    import copy

    from sqlalchemy import insert, update

    from sim2act.db import grants, new_id

    data, app, release, inst, resource, goal, body, route = prepared_use(env)
    checked = data[2].post(route + '/pb-use-reviews', json=body).json()
    commit = dict(review=body, expected_review_fingerprint=checked['review_fingerprint'], consent=use.CONSENT)
    outcomes = []
    for field, wrong in [('expected_revision', 0), ('resource_id', data[5]),
        ('expected_source_hash', '0'*64), ('expected_goal_fingerprint', '0'*64),
        ('expected_recipe_fingerprint', '0'*64), ('expected_release_fingerprint', '0'*64),
        ('expected_app_fingerprint', '0'*64), ('card_id', 'goal_' + '0'*32)]:
        bad = copy.deepcopy(commit)
        bad['review'][field] = wrong
        before = snapshot(data[0])
        response = data[2].post(route + '/pb-use-runs', json=bad)
        assert response.status_code in (403, 409, 422), response.text
        assert snapshot(data[0]) == before
        outcomes.append(dict(field=field, status=response.status_code, error=response.json()))
    bad = {**commit, 'expected_review_fingerprint': '0'*64}
    before = snapshot(data[0])
    assert data[2].post(route + '/pb-use-runs', json=bad).status_code == 409
    assert snapshot(data[0]) == before
    # A newly issued or revoked app target grant invalidates a prior approval.
    with data[0].tx() as c:
        gid = new_id('grant')
        c.execute(insert(grants).values(id=gid, principal_id=inst['runtime_id'], project_id=data[4],
            resource_id=resource, tool_ref='resource.read', expires_at=9999999999, revision=1, revoked=False))
    refreshed = data[2].post(route + '/pb-use-reviews', json=body).json()
    with data[0].tx() as c:
        c.execute(update(grants).where(grants.c.id == gid).values(revoked=True, revision=2))
    before = snapshot(data[0])
    revoked_commit = {**commit, 'expected_review_fingerprint': refreshed['review_fingerprint']}
    denied = data[2].post(route + '/pb-use-runs', json=revoked_commit)
    assert denied.status_code == 409, denied.text
    assert snapshot(data[0]) == before
    (tmp_path / 'illegal-proof.json').write_text(json.dumps(outcomes, indent=2))


def test_recovery_scope_cannot_downgrade_or_read_private_run(env, tmp_path):
    from sql_private_barrier import PrivateReadBarrier
    from sqlalchemy import delete, update

    from sim2act.db import delivery_graph_requests, grants

    data, app, release, inst, resource, goal, body, route = prepared_use(env)
    checked = data[2].post(route + '/pb-use-reviews', json=body).json()
    commit = dict(review=body, expected_review_fingerprint=checked['review_fingerprint'], consent=use.CONSENT)
    queued = data[2].post(route + '/pb-use-runs', json=commit)
    assert queued.status_code == 202, queued.text
    rid = queued.json()['run_id']
    # Exact key is idempotent; changed intent under that key is not accepted.
    before = snapshot(data[0])
    same = data[2].post(route + '/pb-use-runs', json=commit)
    assert same.status_code == 202 and same.json()['run_id'] == rid
    assert snapshot(data[0]) == before
    changed = {**commit, 'expected_review_fingerprint': '0'*64}
    assert data[2].post(route + '/pb-use-runs', json=changed).status_code == 409
    assert snapshot(data[0]) == before
    with data[0].tx() as c:
        c.execute(update(grants).where(grants.c.principal_id == inst['runtime_id'],
            grants.c.resource_id == resource).values(revoked=True))
    with PrivateReadBarrier(data[0], {rid}, {resource}) as barrier:
        denied = data[2].get(route + '/pb-use-requests/' + body['request_key'])
        assert denied.status_code == 403, denied.text
        assert not barrier.blocked
    with data[0].tx() as c:
        c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.app_id == rid,
            delivery_graph_requests.c.kind.in_([use.META, use.META + '_seal'])))
    before = snapshot(data[0])
    with PrivateReadBarrier(data[0], {rid}, {resource}) as barrier:
        for path in [route + '/pb-use-requests/' + body['request_key'],
                     f'/api/internal/app-run-jobs/{rid}/spec-artifact']:
            response = data[2].get(path)
            assert response.status_code in (403, 409), response.text
        assert not barrier.blocked
        (tmp_path / 'scope-barrier-proof.json').write_text(json.dumps(dict(
            blocked=barrier.blocked, statements=barrier.statements), indent=2))
    assert snapshot(data[0]) == before
