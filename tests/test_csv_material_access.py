"""Actual finite business authorization, no fixture App/B Grant insertion."""

import json
import time
from types import SimpleNamespace

from sqlalchemy import select, update
from test_csv_goal_revisions import (
    baseline,
    raw_trace,  # noqa: F401 -- original autouse HTTP evidence fixture
)
from test_local_record_apps import snapshot

from sim2act import apps
from sim2act import db as database
from sim2act.db import fingerprint, grants


def prepared(env):
    data, aid, release, instance, _cid, _content, _app = baseline(env)
    client = data[2]
    bid = client.post(
        f"/api/projects/{data[5]}/resources",
        json=dict(name="new-B.csv", format="csv", content="amount,quantity\n100,7\n250,8\n"),
    ).json()["id"]
    path = f"/api/apps/{aid}/csv-material-access"
    response = client.get(path)
    assert response.status_code == 200, response.text
    ctx = response.json()
    item = next(r for r in ctx["items"] if r["resource_id"] == bid)
    assert item["status"] == "INACTIVE" and item["app_grants"] == []
    body = dict(
        request_key="user-explicit-B",
        resource_id=bid,
        expected_source_hash=item["source_hash"],
        expected_candidate_fingerprint=ctx["candidate_fingerprint"],
        expected_grant_version=ctx["grant_version"],
        expected_app_grants_fingerprint=item["app_grants_fingerprint"],
        consent="AUTHORIZE_ONLY_THIS_APP_ALL_INSTANCES_READ_SUM_THIS_CSV_FOR_24H",
    )
    return data, aid, release, instance, bid, path, body


def call(client, path, body):
    response = client.post(path + "/authorizations", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def withdrawal(value, key="explicit-withdraw"):
    return dict(
        request_key=key,
        resource_id=value["receipt"]["record"]["resource_id"],
        expected_app_grants_fingerprint=value["app_grants_fingerprint"],
        consent="REVOKE_THIS_APP_READ_SUM_THIS_CSV",
    )


def test_exact_App_only_two_grants_explicit_scope_replay_and_stale_key(env, tmp_path):
    data, aid, _release, _instance, bid, path, body = prepared(env)
    client = data[2]
    before = snapshot(data[0])
    rejected = []
    for changes, status in [
        (dict(expected_source_hash="0" * 64), 409),
        (dict(runtime_id="appruntime_" + "0" * 32), 422),
    ]:
        response = client.post(path + "/authorizations", json={**body, **changes})
        assert response.status_code == status, response.text
        assert snapshot(data[0]) == before
        if status == 409:
            proof = response.json()["error"]["submission_rejection"]
            assert proof["acceptance"] == "NOT_ACCEPTED" and proof["phase"] == "TX_ROLLED_BACK"
            assert proof["previous_request"] == "ABSENT" and proof["app_id"] == aid
            assert proof["request_fingerprint"] == fingerprint({**body, **changes})
        rejected.append(dict(status=status, response=response.json()))
    result = call(client, path, body)
    after = snapshot(data[0])
    assert [t for t in before if before[t] != after[t]] == ["delivery_graph_requests", "grants"]
    created = [r for r in after["grants"] if r not in before["grants"]]
    assert (
        len(created) == 2
        and len(after["delivery_graph_requests"]) == len(before["delivery_graph_requests"]) + 2
    )
    assert {r["tool_ref"] for r in created} == {"resource.read", "data.aggregate_csv"}
    assert all(
        r["principal_id"] == result["receipt"]["record"]["runtime_id"]
        and r["resource_id"] == bid
        and r["project_id"] == data[5]
        and r["revision"] == 1
        and not r["revoked"]
        for r in created
    )
    assert {r["expires_at"] for r in created} == {result["receipt"]["created_at"] + 86400}
    assert result["receipt_status"] == result["app_material_status"] == "ACTIVE"
    assert (
        result["receipt"]["scope"] == "THIS_APP_ALL_INSTANCES" and result["content_access"] is False
    )
    assert call(client, path, body) == result and snapshot(data[0]) == after
    collision = client.post(
        path + "/authorizations", json={**body, "expected_source_hash": "0" * 64}
    )
    assert collision.status_code == 409 and "submission_rejection" not in collision.json()["error"]
    assert snapshot(data[0]) == after
    stale = client.post(path + "/authorizations", json={**body, "request_key": "stale-other-key"})
    assert stale.status_code == 409 and snapshot(data[0]) == after
    records = [
        r for r in after["delivery_graph_requests"] if r not in before["delivery_graph_requests"]
    ]
    assert body["expected_source_hash"] not in json.dumps(records)
    (tmp_path / "exact-app-material-authority.json").write_text(
        json.dumps(
            dict(
                app_id=aid,
                before=before,
                after=after,
                request=body,
                response=result,
                rejected=rejected,
                stale=dict(status=stale.status_code, response=stale.json()),
                fixture_App_B_grants=0,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


def test_foreign_project_and_missing_upstream_authority_reject_without_body_or_write(env, tmp_path):
    data, _aid, _release, _instance, bid, path, body = prepared(env)
    client = data[2]
    pid = client.post("/api/projects", json={"name": "different-private-project"}).json()["id"]
    foreign = client.post(
        f"/api/projects/{pid}/resources",
        json=dict(name="private-other.csv", format="csv", content="amount\n999\n"),
    ).json()["id"]
    before = snapshot(data[0])
    response = client.post(path + "/authorizations", json={**body, "resource_id": foreign})
    # The unrelated import changed the conservative project-independent fixture,
    # but B/App's project Grant version itself has not changed.
    assert response.status_code == 403, response.text
    assert snapshot(data[0]) == before
    with data[0].tx() as c:
        gid = (
            c.execute(
                select(grants).where(
                    grants.c.resource_id == bid,
                    grants.c.principal_id == data[3],
                    grants.c.tool_ref == "data.aggregate_csv",
                )
            )
            .mappings()
            .one()
        )
    old = client.post(
        "/api/grants/" + gid["id"] + "/revoke", json=dict(command="revoke", version=gid["revision"])
    )
    assert old.status_code == 200, old.text
    current = client.get(path).json()
    assert bid not in [r["resource_id"] for r in current["items"]]
    before = snapshot(data[0])
    response = client.post(
        path + "/authorizations", json={**body, "expected_grant_version": current["grant_version"]}
    )
    assert response.status_code == 403, response.text
    assert snapshot(data[0]) == before
    (tmp_path / "scope-and-upstream.json").write_text(
        json.dumps(
            dict(
                before=before,
                after=snapshot(data[0]),
                rejected=response.json(),
                foreign_project_rejected=True,
                original_single_gid_revoke_status=old.status_code,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


def test_metadata_atomic_withdraw_after_source_loss_and_late_replay_never_restores(env, tmp_path):
    data, _aid, _release, _instance, _bid, path, body = prepared(env)
    client = data[2]
    accepted = call(client, path, body)
    with data[0].tx() as c:
        original = (
            c.execute(
                select(grants).where(
                    grants.c.resource_id == data[6],
                    grants.c.principal_id == data[3],
                    grants.c.tool_ref == "resource.read",
                )
            )
            .mappings()
            .one()
        )
    r = client.post(
        "/api/grants/" + original["id"] + "/revoke",
        json=dict(command="revoke", version=original["revision"]),
    )
    assert r.status_code == 200, r.text
    before = snapshot(data[0])
    metadata = client.get(path + "/state")
    assert metadata.status_code == 200 and metadata.json()["content_access"] is False
    assert "source_hash" not in metadata.text and "goal_snapshot" not in metadata.text
    read = client.get(path + "/authorizations/" + body["request_key"])
    assert read.status_code == 200 and read.json()["upstream_available"] is False
    assert snapshot(data[0]) == before
    bad = client.post(
        path + "/revocations",
        json={**withdrawal(read.json()), "expected_app_grants_fingerprint": "0" * 64},
    )
    assert bad.status_code == 409 and snapshot(data[0]) == before
    stop_body = withdrawal(read.json())
    stop = client.post(path + "/revocations", json=stop_body)
    assert stop.status_code == 201, stop.text
    after = snapshot(data[0])
    assert [t for t in before if before[t] != after[t]] == ["delivery_graph_requests", "grants"]
    ids = {r["id"] for r in accepted["receipt"]["grants"]}
    stopped = [r for r in after["grants"] if r["id"] in ids]
    assert len(stopped) == 2 and all(r["revoked"] and r["revision"] == 2 for r in stopped)
    assert all(r in after["grants"] for r in before["grants"] if r["id"] not in ids)
    for endpoint, payload in [("/authorizations", body), ("/revocations", stop_body)]:
        response = client.post(path + endpoint, json=payload)
        assert response.status_code == 201 and response.json()["receipt_status"] == "REVOKED"
        assert snapshot(data[0]) == after
    replay = client.get(path + "/authorizations/" + body["request_key"])
    assert replay.status_code == 200 and replay.json()["receipt_status"] == "REVOKED"
    assert snapshot(data[0]) == after
    stale = client.post(
        path + "/authorizations", json={**body, "request_key": "late-stale-new-key"}
    )
    assert stale.status_code == 409 and snapshot(data[0]) == after
    (tmp_path / "withdraw-and-late-replay.json").write_text(
        json.dumps(
            dict(
                before=before,
                after=after,
                original_authorization=accepted,
                withdraw_request=stop_body,
                withdraw_response=stop.json(),
                late_response=replay.json(),
                metadata=metadata.json(),
                all_non_authority_history_preserved=True,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


def test_expiry_during_existing_App_proof_rolls_back_fresh_authorization(
    env, monkeypatch, tmp_path
):
    data, _aid, _release, _instance, bid, path, _body = prepared(env)
    client = data[2]
    now = time.time()
    with data[0].tx() as c:
        c.execute(
            update(grants)
            .where(grants.c.resource_id == bid, grants.c.tool_ref == "data.aggregate_csv")
            .values(expires_at=now + 5)
        )
    ctx = client.get(path).json()
    item = next(r for r in ctx["items"] if r["resource_id"] == bid)
    body = dict(
        request_key="expiry-window",
        resource_id=bid,
        expected_source_hash=item["source_hash"],
        expected_candidate_fingerprint=ctx["candidate_fingerprint"],
        expected_grant_version=ctx["grant_version"],
        expected_app_grants_fingerprint=item["app_grants_fingerprint"],
        consent="AUTHORIZE_ONLY_THIS_APP_ALL_INSTANCES_READ_SUM_THIS_CSV_FOR_24H",
    )
    clock = [now]
    original = apps.load_draft
    monkeypatch.setattr(database, "time", SimpleNamespace(time=lambda: clock[0]))

    def expired_after_proof(*args, **kwargs):
        result = original(*args, **kwargs)
        clock[0] = now + 10
        return result

    monkeypatch.setattr(apps, "load_draft", expired_after_proof)
    before = snapshot(data[0])
    response = client.post(path + "/authorizations", json=body)
    assert response.status_code == 403 and response.json()["error"]["code"] == "GRANT_REVOKED", (
        response.text
    )
    assert snapshot(data[0]) == before
    (tmp_path / "expiry-proof-boundary.json").write_text(
        json.dumps(
            dict(
                before=before,
                after=snapshot(data[0]),
                response=response.json(),
                clock_advance_seconds=10,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
