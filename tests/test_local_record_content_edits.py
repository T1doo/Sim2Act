"""Original F2-T06: explicit content corrections through actual API/NoModel Worker."""

import copy

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from test_local_record_apps import (
    DETAILS_A,
    DETAILS_B,
    TITLE_A,
    TITLE_B,
    NoModel,
    commit,
    create_body,
    current,
    done_body,
    execute,
    ok,
    preview,
    ready,
    saved_rows,
    snapshot,
    write_json,
)

from sim2act import local_record_apps as records
from sim2act.api import create_app
from sim2act.db import Store, runs
from sim2act.errors import DomainError
from sim2act.worker import Worker

TITLE = "A corrected title"
DETAILS = "A corrected complete content; B must remain unchanged."
REASON = "Correct an explicit data entry error."


def edit_body(state, record, key="correct-a", title=TITLE, details=DETAILS):
    return dict(command="EDIT_CONTENT", expected_revision=state["revision"],
        expected_data_version=state["data_version"], expected_release_fingerprint=state["release_fingerprint"],
        request_key=key, record_id=record["record_id"], expected_record_revision=record["record_revision"],
        title=title, details=details, reason=REASON)


def seeded(env, *, editable=True):
    data = ready(env, content_edits=editable)
    a = execute(env, data, create_body(current(env, data)))
    b = execute(env, data, create_body(current(env, data), "create-b", TITLE_B, DETAILS_B))
    return data, a, b


def test_content_edit_actual_worker_independent_fold_cold_read_and_explicit_revert(env, tmp_path):
    data, a, b = seeded(env)
    state = current(env, data)
    old_records = copy.deepcopy(state["records"])
    original = saved_rows(env[0], [a, b])
    # Oracle below uses fixed expected records and JSON events, never product apply_event.
    changed = execute(env, data, edit_body(state, old_records[0]))
    assert changed["run"]["event"]["namespace"] == "local-record-event.v2"
    assert changed["prepared"]["preview"]["typed_mapping_version"] == "local-record-input.v2"
    state = current(env, data)
    assert saved_rows(env[0], [a, b]) == original
    assert state["records"][1] == old_records[1]
    fold = {}
    for index, item in enumerate(state["history"], 1):
        e = item["event"]
        assert e["collection_version"] == index
        if index < 3:
            assert e["kind"] == "CREATE" and e["record_revision"] == 1
        else:
            assert e["kind"] == "EDIT_CONTENT" and e["record_revision"] == 2
            assert e["record_id"] == a["run"]["event"]["record_id"]
            assert (e["title"], e["details"], e["state"], e["reason"]) == (TITLE, DETAILS, "OPEN", REASON)
            assert e["previous_event_fingerprint"] == state["history"][0]["event_fingerprint"]
        fold[e["record_id"]] = (e["title"], e["details"], e["state"], e["record_revision"])
    assert list(fold.values()) == [(TITLE, DETAILS, "OPEN", 2), (TITLE_B, DETAILS_B, "OPEN", 1)]
    cold = Store(env[1].database_url, test_only=True)
    try:
        with TestClient(create_app(cold, env[1])) as client:
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            before = snapshot(cold)
            assert ok(client.get(data["path"])) == state
            assert snapshot(cold) == before
    finally:
        cold.engine.dispose()
    # Revert is another visible event; it never erases the correction or rewinds data.
    reverted = execute(env, data, edit_body(state, state["records"][0], "restore-a", TITLE_A, DETAILS_A))
    assert reverted["run"]["event"]["record_revision"] == 3
    state = current(env, data)
    execute(env, data, done_body(state, state["records"][0], "finish-corrected-a"))
    state = current(env, data)
    assert state["records"][0]["state"] == "DONE" and state["records"][0]["record_revision"] == 4
    before = snapshot(env[0])
    assert env[2].post(data["path"] + "/previews", json=edit_body(state, state["records"][0], "done-edit")).status_code == 409
    assert snapshot(env[0]) == before
    assert saved_rows(env[0], [a, b]) == original
    write_json(tmp_path / "actual-edit-and-revert.json", dict(final=state, deliveries=[a, b, changed, reverted], oracle=fold))


def test_content_edit_exact_keys_versions_scope_and_legacy_release(env, tmp_path):
    data, _, _ = seeded(env)
    state = current(env, data)
    body = edit_body(state, state["records"][0])
    bads = [dict(body, title=" "), dict(body, reason=" "),
        dict(body, title=TITLE_A, details=DETAILS_A), dict(body, expected_revision=2),
        dict(body, expected_data_version=1), dict(body, expected_record_revision=2),
        dict(body, target_state="DONE"), dict(body, record_id="record_" + "0" * 32)]
    for index, bad in enumerate(bads):
        bad["request_key"] = f"reject-{index}"
        before = snapshot(env[0])
        response = env[2].post(data["path"] + "/previews", json=bad)
        assert response.status_code in {400, 409, 422}, response.text
        assert snapshot(env[0]) == before
    before = snapshot(env[0])
    denied = env[2].post(data["path"] + "/previews", json=body,
        headers={"Authorization": "Bearer synthetic-test-B"})
    assert denied.status_code == 403 and snapshot(env[0]) == before
    legacy, _, _ = seeded_legacy(env)
    before = snapshot(env[0])
    old = current(env, legacy)
    denied = env[2].post(legacy["path"] + "/previews", json=edit_body(old, old["records"][0]))
    assert denied.status_code == 400 and denied.json()["error"]["code"] == "UNSUPPORTED_CAPABILITY"
    assert snapshot(env[0]) == before
    prepared = preview(env, data, body)
    accepted, submit = commit(env, data, prepared)
    again = ok(env[2].post(data["path"] + f"/previews/{body['request_key']}/commit", json=submit), 202)
    assert again["run"]["run_id"] == accepted["run"]["run_id"]
    assert env[2].post(data["path"] + "/previews", json=dict(body, title="another intent")).status_code == 409
    assert Worker(env[0], env[1], NoModel()).once()
    assert ok(env[2].get(data["path"] + "/record-requests/" + body["request_key"]))["run"]["run_id"] == accepted["run"]["run_id"]
    final = current(env, data)
    assert final["data_version"] == 3 and len(final["history"]) == 3
    write_json(tmp_path / "key-and-legacy-boundaries.json", dict(final=final, prepared=prepared, accepted=accepted))


def seeded_legacy(env):
    # Separate existing contract without the explicit editing capability.
    data = ready(env, key="legacy-local-form")
    a = execute(env, data, create_body(current(env, data)))
    return data, a, None


@pytest.mark.parametrize("failure", ["cancel", "after_save", "old_fence"])
def test_content_edit_cancel_failure_and_fence_preserve_original_collection(env, monkeypatch, failure, tmp_path):
    data, a, b = seeded(env)
    state = current(env, data)
    prepared = preview(env, data, edit_body(state, state["records"][0]))
    accepted, _ = commit(env, data, prepared)
    rid = accepted["run"]["run_id"]
    business = {"resources", "grants", "local_effects", "operations", "operation_intents", "internal_instance_data", "internal_instances"}
    before = snapshot(env[0], business)
    old_rows = saved_rows(env[0], [a, b])
    calls = []
    if failure == "cancel":
        run = ok(env[2].get(data["path"] + "/runs/" + rid))
        ok(env[2].post(data["path"] + "/runs/" + rid + "/commands", json=dict(command="cancel", version=run["version"])))
        assert Worker(env[0], env[1], NoModel()).once() is False
    else:
        original = records.write_text_artifact

        def fail_after_real_save(*args, **kwargs):
            result = original(*args, **kwargs)
            calls.append(result)
            if failure == "old_fence":
                args[1].execute(update(runs).where(runs.c.id == rid).values(fence=runs.c.fence + 1))
                return result
            raise DomainError("VERSION_CONFLICT", "Synthetic fault after actual save")

        monkeypatch.setattr(records, "write_text_artifact", fail_after_real_save)
        assert Worker(env[0], env[1], NoModel()).once()
        assert len(calls) == 1
    assert snapshot(env[0], business) == before
    assert saved_rows(env[0], [a, b]) == old_rows
    final = current(env, data)
    assert final["records"] == state["records"] and final["history"] == state["history"] and final["data_version"] == 2
    failed = ok(env[2].get(data["path"] + "/runs/" + rid))
    assert failed["status"] in {"CANCELLED", "FAILED", "RECONCILING"} and failed["output"] is None
    write_json(tmp_path / "actual-failure.json", dict(kind=failure, calls=calls, run=failed, final=final))


def test_private_content_edit_isolated_and_old_event_cannot_claim_edit(env):
    data, _, _ = seeded(env)
    business = current(env, data)
    private = ok(env[2].post(f"/api/internal/record-releases/{data['release']['id']}/private-previews", json=dict(
        expected_release_fingerprint=data["release"]["fingerprint"], request_key="private-edit",
        consent="CREATE_PRIVATE_WRITE_PREVIEW_NO_BUSINESS_PROMOTION")), 201)
    target = dict(data, instance=private["instance"], path=f"/api/internal/record-instances/{private['instance']['id']}")
    execute(env, target, create_body(current(env, target)))
    state = current(env, target)
    edited = execute(env, target, edit_body(state, state["records"][0]))
    assert current(env, data) == business
    final = current(env, target)
    assert final["records"][0]["title"] == TITLE and final["preview_scope"]
    old_event = edited["run"]["event"]
    original_record = state["records"][0]
    with pytest.raises(DomainError):
        records.apply_event({original_record["record_id"]: original_record}, old_event,
            old_event["previous_collection_fingerprint"], 2, target["instance"])
    with pytest.raises(DomainError):
        records.apply_event({original_record["record_id"]: original_record}, dict(old_event, namespace=records.EVENT_VERSION),
            old_event["previous_collection_fingerprint"], 2, target["instance"], allow_content_edit=True)
