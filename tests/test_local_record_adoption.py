"""Original F2-T08/AT16: exact compatible adoption through actual API/Worker."""

import copy

from fastapi.testclient import TestClient
from record_test_store import reopen_record_test_store
from sqlalchemy import select, update
from test_local_record_apps import (
    DETAILS_B,
    TITLE_B,
    NoModel,
    commit,
    create_body,
    current,
    execute,
    ok,
    preview,
    ready,
    saved_rows,
    snapshot,
    write_json,
)
from test_local_record_content_edits import DETAILS, TITLE, edit_body

from sim2act import local_record_apps as r
from sim2act.api import create_app
from sim2act.db import fingerprint
from sim2act.worker import Worker


def new_release(env, data):
    app = data["app"]
    body = dict(request_key="v2-release", expected_definition_fingerprint=app["fingerprint"],
        consent="FREEZE_RECORD_FORM_AND_WRITE_BOUNDARY", content_edits="OPEN_RECORD_CONTENT_V1")
    path = f"/api/apps/{app['id']}/record-release-requests/{body['request_key']}"
    proposed = ok(env[2].post(f"/api/apps/{app['id']}/record-release-approvals", json=body), 201)
    result = ok(env[2].post(path + "/commit", json=dict(fingerprint=proposed["approval"]["fingerprint"])))
    assert result["approval"]["payload"]["snapshot"]["definition"]["typed_mapping_version"] == r.EDIT_MAPPING
    return result["release"]


def adoption_body(state, target, key="adopt-v2"):
    return dict(request_key=key, expected_revision=state["revision"], expected_data_version=state["data_version"],
        expected_release_fingerprint=state["release_fingerprint"], target_release_id=target["id"],
        target_release_fingerprint=target["fingerprint"], consent="ADOPT_V2_PRESERVE_RECORDS_AND_HISTORY")


def adopt(env, data, target, key="adopt-v2"):
    path = data["path"] + "/release-adoptions"
    proposed = ok(env[2].post(path, json=adoption_body(current(env, data), target, key)), 201)
    return ok(env[2].post(path + "/" + key + "/commit", json=dict(fingerprint=proposed["approval"]["fingerprint"])))


def test_adoption_preserves_exact_events_and_receipts_then_edits_same_iid_cold(env, tmp_path):
    data = ready(env)
    first = execute(env, data, create_body(current(env, data)))
    second = execute(env, data, create_body(current(env, data), "create-b", TITLE_B, DETAILS_B))
    old = current(env, data)
    immutable = saved_rows(env[0], [first, second])
    target = new_release(env, data)
    before = snapshot(env[0])
    result = adopt(env, data, target)
    after = snapshot(env[0])
    assert {k for k in before if before[k] != after[k]} == {
        "internal_instances", "internal_approvals", "delivery_graph_requests"}
    old_i = next(i for i in before["internal_instances"] if i["id"] == data["instance"]["id"])
    new_i = next(i for i in after["internal_instances"] if i["id"] == old_i["id"])
    assert new_i == dict(old_i, release_id=target["id"], revision=2)
    assert result["adoption"]["prefix_fingerprint"] == fingerprint(dict(records=old["records"], history=old["history"]))
    upgraded = current(env, data)
    assert upgraded["records"] == old["records"] and upgraded["history"] == old["history"]
    assert upgraded["data_version"] == 2 and upgraded["revision"] == 2
    changed = execute(env, data, edit_body(upgraded, upgraded["records"][0]))
    final = current(env, data)
    assert saved_rows(env[0], [first, second]) == immutable
    assert final["records"][1] == old["records"][1]
    # Independent fold, with exact source and target Release intervals.
    fold = {}
    for index, row in enumerate(final["history"], 1):
        event = row["event"]
        assert event["release_id"] == (data["release"]["id"] if index <= 2 else target["id"])
        assert event["collection_version"] == index
        fold[event["record_id"]] = (event["title"], event["details"], event["state"], event["record_revision"])
    assert list(fold.values()) == [(TITLE, DETAILS, "OPEN", 2), (TITLE_B, DETAILS_B, "OPEN", 1)]
    cold = reopen_record_test_store(env[0])
    try:
        with TestClient(create_app(cold, env[1])) as client:
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            before = snapshot(cold)
            assert ok(client.get(data["path"])) == final
            assert ok(client.get(data["path"] + "/runs/" + first["run"]["id"])) == first["run"]
            recovered = ok(client.get(data["path"] + "/release-adoptions/adopt-v2"))
            assert recovered["adoption"] == result["adoption"]
            assert snapshot(cold) == before
    finally:
        cold.engine.dispose()
    write_json(tmp_path / "actual-adoption.json", dict(old=old, adoption=result, changed=changed, final=final, oracle=fold))


def test_adoption_stale_pending_scope_private_downgrade_and_old_preview_no_writes(env, tmp_path):
    data = ready(env)
    execute(env, data, create_body(current(env, data)))
    target = new_release(env, data)
    state = current(env, data)
    old_preview = preview(env, data, create_body(state, "unaccepted-v1"))
    body = adoption_body(state, target)
    private = ok(env[2].post(f"/api/internal/record-releases/{data['release']['id']}/private-previews", json=dict(
        request_key="private", expected_release_fingerprint=data["release"]["fingerprint"],
        consent="CREATE_PRIVATE_WRITE_PREVIEW_NO_BUSINESS_PROMOTION")), 201)["instance"]
    paths = [(data["path"], dict(body, expected_revision=2)),
        (data["path"], dict(body, expected_data_version=0)),
        (data["path"], dict(body, target_release_fingerprint="0" * 64)),
        (f"/api/internal/record-instances/{private['id']}", dict(body, expected_data_version=0))]
    for path, bad in paths:
        before = snapshot(env[0])
        assert env[2].post(path + "/release-adoptions", json=bad).status_code == 409
        assert snapshot(env[0]) == before
    before = snapshot(env[0])
    assert env[2].post(data["path"] + "/release-adoptions", json=body,
        headers={"Authorization": "Bearer synthetic-test-B"}).status_code == 403
    assert snapshot(env[0]) == before
    queued, _ = commit(env, data, old_preview)
    before = snapshot(env[0])
    assert env[2].post(data["path"] + "/release-adoptions", json=body).status_code == 409
    assert snapshot(env[0]) == before
    rid = queued["run"]["run_id"]
    run = ok(env[2].get(data["path"] + "/runs/" + rid))
    ok(env[2].post(data["path"] + "/runs/" + rid + "/commands", json=dict(command="cancel", version=run["version"])))
    # A zero-result cancelled old Run must remain readable after the switch.
    still_old = preview(env, data, create_body(current(env, data), "never-accepted-v1"))
    adopt(env, data, target)
    assert ok(env[2].get(data["path"] + "/runs/" + rid))["status"] == "CANCELLED"
    before = snapshot(env[0])
    response = env[2].post(data["path"] + "/previews/never-accepted-v1/commit", json=dict(
        expected_preview_fingerprint=still_old["preview_fingerprint"], consent="WRITE_THIS_EXACT_LOCAL_RECORD_EVENT"))
    assert response.status_code == 409 and snapshot(env[0]) == before
    assert ok(env[2].get(data["path"] + "/record-requests/never-accepted-v1"))["preview"] == still_old["preview"]
    before = snapshot(env[0])
    assert env[2].post(data["path"] + "/release-adoptions", json=adoption_body(current(env, data), data["release"], "downgrade")).status_code == 409
    assert snapshot(env[0]) == before
    write_json(tmp_path / "actual-adoption-guards.json", dict(cancelled=rid, old_preview=still_old, final=current(env, data)))


def test_adoption_frozen_prefix_and_historical_worker_pointer_guard(env):
    data = ready(env)
    execute(env, data, create_body(current(env, data)))
    target = new_release(env, data)
    old_preview = preview(env, data, create_body(current(env, data), "cancelled-v1"))
    accepted, _ = commit(env, data, old_preview)
    rid = accepted["run"]["run_id"]
    run = ok(env[2].get(data["path"] + "/runs/" + rid))
    ok(env[2].post(data["path"] + "/runs/" + rid + "/commands", json=dict(command="cancel", version=run["version"])))
    adopt(env, data, target)
    # Synthetic privileged resurrection cannot turn the historical read view into write authority.
    with env[0].tx() as c:
        c.execute(update(r.runs).where(r.runs.c.id == rid).values(status="QUEUED", cancel_intent=False))
        c.execute(update(r.app_runs).where(r.app_runs.c.id == accepted["run"]["app_run_id"]).values(status="QUEUED"))
    before = snapshot(env[0], {"resources", "grants", "operations", "operation_intents", "local_effects", "internal_instance_data", "internal_instances"})
    assert Worker(env[0], env[1], NoModel()).once()
    assert snapshot(env[0], set(before)) == before
    assert ok(env[2].get(data["path"] + "/runs/" + rid))["status"] == "FAILED"
    with env[0].tx() as c:
        rows = c.execute(select(r.journal).where(r.journal.c.app_id == data["instance"]["id"],
            r.journal.c.kind.in_(["local-record-release-adoption.v1.prepare", "local-record-release-adoption.v1.prepare_seal"]))).mappings().all()
        approval_id = rows[0]["snapshot"]["response"]["id"]
        a = dict(c.execute(select(r.approvals).where(r.approvals.c.id == approval_id)).mappings().one())
        payload = copy.deepcopy(a["payload"])
        payload["snapshot"]["prefix_fingerprint"] = "0" * 64
        newfp = fingerprint(payload)
        c.execute(update(r.approvals).where(r.approvals.c.id == approval_id).values(payload=payload, fingerprint=newfp))
        # Even coherently resealed metadata cannot substitute for rechecking the real prefix.
        allrows = c.execute(select(r.journal).where(r.journal.c.app_id == data["instance"]["id"],
            r.journal.c.kind.like("local-record-release-adoption.v1.%"))).mappings().all()
        for row in allrows:
            saved = copy.deepcopy(row["snapshot"])
            if ".prepare" in row["kind"]:
                saved["response"]["fingerprint"] = newfp
            else:
                saved["request"]["fingerprint"] = newfp
                saved["response"]["fingerprint"] = newfp
                saved["response"]["snapshot"] = payload["snapshot"]
            c.execute(update(r.journal).where(r.journal.c.app_id == row["app_id"],
                r.journal.c.kind == row["kind"], r.journal.c.request_key == row["request_key"],
                r.journal.c.principal_id == row["principal_id"]).values(snapshot=saved,
                    fingerprint=fingerprint(saved), request_fingerprint=fingerprint(saved["request"])))
    before = snapshot(env[0])
    assert env[2].get(data["path"]).status_code == 409 and snapshot(env[0]) == before


def test_adoption_stale_approval_expired_read_and_changed_historical_release(env, monkeypatch):
    import time

    data = ready(env)
    execute(env, data, create_body(current(env, data)))
    target = new_release(env, data)
    path = data["path"] + "/release-adoptions"
    proposal = ok(env[2].post(path, json=adoption_body(current(env, data), target, "stale")), 201)
    execute(env, data, create_body(current(env, data), "another-original-write", TITLE_B, DETAILS_B))
    before = snapshot(env[0])
    assert env[2].post(path + "/stale/commit", json=dict(fingerprint=proposal["approval"]["fingerprint"])).status_code == 409
    assert snapshot(env[0]) == before
    assert ok(env[2].get(path + "/stale"))["adoption"] is None
    fresh = ok(env[2].post(path, json=adoption_body(current(env, data), target, "fresh")), 201)
    actual_time = time.time
    with monkeypatch.context() as patch:
        patch.setattr(time, "time", lambda: actual_time() + 600)
        before = snapshot(env[0])
        assert ok(env[2].get(path + "/fresh"))["approval"] == fresh["approval"]
        assert env[2].post(path + "/fresh/commit", json=dict(fingerprint=fresh["approval"]["fingerprint"])).status_code == 409
        assert snapshot(env[0]) == before
    committed = ok(env[2].post(path + "/fresh/commit", json=dict(fingerprint=fresh["approval"]["fingerprint"])))
    with monkeypatch.context() as patch:
        patch.setattr(time, "time", lambda: actual_time() + 600)
        before = snapshot(env[0])
        assert ok(env[2].get(path + "/fresh")) == committed
        assert snapshot(env[0]) == before
    # The old immutable Release remains checked; it is not grandfathered by a new pointer.
    with env[0].tx() as c:
        original = copy.deepcopy(c.execute(select(r.releases.c.snapshot).where(r.releases.c.id == data["release"]["id"])).scalar_one())
        original["software_fingerprint"] = "0" * 64
        c.execute(update(r.releases).where(r.releases.c.id == data["release"]["id"]).values(snapshot=original))
    before = snapshot(env[0])
    assert env[2].get(data["path"]).status_code == 409 and snapshot(env[0]) == before
