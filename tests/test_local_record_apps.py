"""Actual local record transactions; synthetic engineering data, never a model.

The exact API contract is versioned separately by root. This draft is isolated
from the sole writer's checkout and awaits frozen-source actual execution.
"""

import hashlib
import json
import re

import pytest
from fastapi.testclient import TestClient
from sql_private_barrier import PrivateReadBarrier
from sqlalchemy import select, update

from sim2act.api import create_app
from sim2act.db import (
    Store,
    attempts,
    delivery_graph_requests,
    fingerprint,
    grants,
    internal_app_runs,
    internal_instance_data,
    internal_run_bindings,
    local_effects,
    meta,
    operation_intents,
    operations,
    reservations,
    resources,
    runs,
)
from sim2act.errors import DomainError
from sim2act.worker import Worker

TITLE_A = "A 合成工作项"
DETAILS_A = "Synthetic A: collect a local record; meaning not evaluated."
TITLE_B = "B 合成工作项"
DETAILS_B = "Synthetic B: independent OPEN record."
DONE_REASON = "Synthetic explicit reason: owner marked only A complete."


class NoModel:
    def request(self, *args, **kwargs):
        raise AssertionError("Local records must never request a real or mock model")


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def snapshot(store, only=None):
    """Privileged synthetic fixture inspection outside product authorization."""
    tables = [table for table in meta.sorted_tables if only is None or table.name in only]
    with store.tx() as c:
        return {table.name: sorted((dict(row) for row in c.execute(select(table)).mappings()),
            key=lambda row: json.dumps(row, sort_keys=True, default=str)) for table in tables}


class RecordPrivateBarrier(PrivateReadBarrier):
    """Guard actual historical row cells, including private typed/input bodies."""

    def __init__(self, store, run_ids, app_run_ids, resource_ids):
        super().__init__(store, run_ids, resource_ids)
        self.full_binding_reads = []
        self.identifier_cells = set()
        self.identifier_projection_reads = []
        self.rules.update({
            "internal_instance_data": (internal_instance_data, "run_id", set(app_run_ids), {"data"}),
            "internal_app_runs": (internal_app_runs, "id", set(app_run_ids), {"input", "output", "error"}),
            "delivery_graph_requests": (delivery_graph_requests, "kind", {
                "local-record-app.v1.preview", "local-record-app.v1.preview_seal"}, {"snapshot"}),
        })

    def _trace(self, conn, cursor, statement, parameters, context, many):
        self.identifier_cells = set()
        sql = " ".join(statement.split())
        typed_ids = ("SELECT JSON_EXTRACT(JSON_QUOTE(JSON_EXTRACT(internal_instance_data.data, ?)), ?) AS anon_1 "
            "FROM internal_instance_data WHERE internal_instance_data.instance_id = ?")
        output_ids = ("SELECT JSON_EXTRACT(internal_app_runs.output, ?) AS anon_1 "
            "FROM internal_app_runs WHERE internal_app_runs.instance_id = ?")
        if not many and sql == typed_ids and len(parameters) == 3 and tuple(parameters[:2]) == ('$."result"', '$."resource_id"'):
            self.identifier_cells = {("internal_instance_data", "data")}
        elif not many and sql == output_ids and len(parameters) == 2 and parameters[0] == '$."resource_id"':
            self.identifier_cells = {("internal_app_runs", "output")}
        projection = statement.split("\nFROM", 1)[0]
        if re.search(r"(?:SELECT |, )internal_run_bindings\.snapshot(?:,|\s|$)", projection):
            self.full_binding_reads.append(dict(sql=statement, parameters=repr(parameters)))
        return super()._trace(conn, cursor, statement, parameters, context, many)

    def _cell(self, table, rid, column, value):
        if (table, column) in self.identifier_cells:
            self.identifier_projection_reads.append(dict(table=table, row_id=rid, column=column,
                classification="EXACT_IDENTIFIER_ONLY_SQL_PROJECTION_UNDERLYING_JSON_EVALUATED"))
            return value
        return super()._cell(table, rid, column, value)


@pytest.fixture
def evidence(env, tmp_path):
    raw = []
    proof = dict(real_model_requests=0, real_semantic_acceptance="NOT_RUN",
        native_browser="NOT_RUN", pg="NOT_RUN")

    def record(response):
        response.read()
        request = response.request
        body = request.content.decode("utf-8") if request.content else None
        raw.append(dict(method=request.method, url=str(request.url),
            request=json.loads(body) if body else None, status=response.status_code,
            response=response.text))

    env[2].event_hooks["response"].append(record)
    try:
        yield proof, record
    finally:
        env[2].event_hooks["response"].remove(record)
        write_json(tmp_path / "local-record-http.json", raw)
        write_json(tmp_path / "local-record-proof.json", proof)


def ok(response, status=200):
    assert response.status_code == status, response.text
    return response.json()


def ready(env, pid=None, key="local-form"):
    client, pid = env[2], pid or env[5]
    app = ok(client.post(f"/api/projects/{pid}/record-apps", json=dict(
        name="Synthetic local collection", goal="Collect independent work items and explicitly mark one DONE",
        request_key=key, consent="SAVE_LOCAL_RECORD_FORM")), 201)
    public = ok(client.get(f"/api/apps/{app['id']}"))
    assert public["namespace"] == "local-record-app.v1"
    assert public["project_id"] == pid and public["principal_id"] == env[3]
    delivery = ok(client.get(f"/api/apps/{app['id']}/record-delivery"))
    approval = ok(client.post(f"/api/apps/{app['id']}/record-release-approvals", json=dict(
        expected_definition_fingerprint=delivery["definition_fingerprint"],
        request_key="freeze-form", consent="FREEZE_RECORD_FORM_AND_WRITE_BOUNDARY")), 201)
    assert approval["release"] is None
    committed = ok(client.post(f"/api/apps/{app['id']}/record-release-requests/freeze-form/commit",
        json=dict(fingerprint=approval["approval"]["fingerprint"])))
    release = committed["release"]
    created = ok(client.post(f"/api/internal/record-releases/{release['id']}/instances", json=dict(
        expected_release_fingerprint=release["fingerprint"], request_key="explicit-instance")), 201)
    inst = created["instance"]
    path = f"/api/internal/record-instances/{inst['id']}"
    return dict(app=public, release=release, instance=inst, path=path, project=pid)


def current(env, data):
    return ok(env[2].get(data["path"]))


def create_body(state, key="create-a", title=TITLE_A, details=DETAILS_A):
    return dict(command="CREATE", expected_revision=state["revision"],
        expected_data_version=state["data_version"],
        expected_release_fingerprint=state["release_fingerprint"], request_key=key,
        title=title, details=details)


def done_body(state, record, key="complete-a"):
    return dict(command="SET_STATE", expected_revision=state["revision"],
        expected_data_version=state["data_version"],
        expected_release_fingerprint=state["release_fingerprint"], request_key=key,
        record_id=record["record_id"], expected_record_revision=record["record_revision"],
        target_state="DONE", reason=DONE_REASON)


def preview(env, data, body):
    value = ok(env[2].post(data["path"] + "/previews", json=body), 201)
    assert value["instance_id"] == data["instance"]["id"]
    assert value["request_key"] == body["request_key"] and value["request_fingerprint"] == fingerprint(body)
    assert value["preview"]["input"] == body and value["run"] is None
    assert value["preview"]["event_fingerprint"] == fingerprint(value["preview"]["event"])
    return value


def commit(env, data, prepared):
    body = dict(expected_preview_fingerprint=prepared["preview_fingerprint"],
        consent="WRITE_THIS_EXACT_LOCAL_RECORD_EVENT")
    response = env[2].post(data["path"] + f"/previews/{prepared['request_key']}/commit", json=body)
    return ok(response, 202), body


def execute(env, data, body):
    prepared = preview(env, data, body)
    accepted, submitted = commit(env, data, prepared)
    assert accepted["run"]["status"] == "QUEUED"
    assert Worker(env[0], env[1], NoModel()).once()
    run = ok(env[2].get(data["path"] + "/runs/" + accepted["run"]["run_id"]))
    assert run["status"] == "SUCCEEDED", run
    assert run["event"] == prepared["preview"]["event"]
    return dict(prepared=prepared, accepted=accepted, submitted=submitted, run=run)


def saved_rows(store, deliveries):
    rids = {value["run"]["id"] for value in deliveries}
    aids = {value["run"]["app_run_id"] for value in deliveries}
    files = {value["run"]["output"]["resource_id"] for value in deliveries}
    with store.tx() as c:
        ids = set(c.execute(select(operations.c.id).where(operations.c.run_id.in_(rids))).scalars())
        filters = [
            (runs, runs.c.id.in_(rids)), (operations, operations.c.run_id.in_(rids)),
            (operation_intents, operation_intents.c.operation_id.in_(ids)),
            (local_effects, local_effects.c.operation_id.in_(ids)),
            (internal_app_runs, internal_app_runs.c.id.in_(aids)),
            (internal_instance_data, internal_instance_data.c.run_id.in_(aids)),
            (resources, resources.c.id.in_(files)), (grants, grants.c.resource_id.in_(files)),
        ]
        return {table.name: sorted((dict(row) for row in c.execute(select(table).where(where)).mappings()),
            key=lambda row: json.dumps(row, sort_keys=True, default=str)) for table, where in filters}


def assert_saved(env, data, delivery, version):
    run, prepared = delivery["run"], delivery["prepared"]
    event, artifact = run["event"], run["output"]
    assert set(event) == {"namespace", "app_id", "instance_id", "release_id", "principal_id", "kind",
        "collection_version", "record_id", "record_revision", "previous_event_fingerprint",
        "previous_collection_fingerprint", "title", "details", "state", "reason"}
    assert event["namespace"] == "local-record-event.v1"
    assert event["app_id"] == data["app"]["id"] and event["principal_id"] == env[3]
    assert event["instance_id"] == data["instance"]["id"] and event["release_id"] == data["release"]["id"]
    assert event["collection_version"] == run["result_version"] == version
    assert event == prepared["preview"]["event"] and fingerprint(event) == prepared["preview"]["event_fingerprint"]
    assert set(artifact) == {"resource_id", "hash"}
    assert run["receipt"]["data"] == artifact and run["receipt"]["artifact_refs"] == [artifact["resource_id"]]
    with env[0].tx() as c:
        resource = dict(c.execute(select(resources).where(resources.c.id == artifact["resource_id"])).mappings().one())
        assert resource["format"] == "json" and resource["project_id"] == data["project"]
        assert json.loads(resource["content"]) == event
        assert hashlib.sha256(resource["content"].encode()).hexdigest() == resource["hash"] == artifact["hash"]
        ops = c.execute(select(operations).where(operations.c.run_id == run["id"])).mappings().all()
        assert len(ops) == 1
        operation = ops[0]
        assert operation["status"] == "VERIFIED" and operation["tool_ref"] == "artifact.save_text"
        assert operation["receipt"] == run["receipt"]
        intent = c.execute(select(operation_intents.c.request).where(
            operation_intents.c.operation_id == operation["id"])).scalar_one()
        assert intent["tool"] == "artifact.save_text" and intent["args"] == {"text": resource["content"]}
        assert fingerprint(intent) == operation["fingerprint"]
        effect = c.execute(select(local_effects).where(local_effects.c.operation_id == operation["id"])).mappings().one()
        assert effect["resource_id"] == artifact["resource_id"] and effect["content_hash"] == artifact["hash"]
        typed = c.execute(select(internal_instance_data).where(
            internal_instance_data.c.instance_id == data["instance"]["id"],
            internal_instance_data.c.run_id == run["app_run_id"])).mappings().one()
        assert typed["data"] == dict(result=artifact, release_ref=data["release"]["id"])
        assert typed["fingerprint"] == fingerprint(typed["data"]) and typed["version"] == version
        binding = c.execute(select(internal_run_bindings).where(internal_run_bindings.c.run_id == run["id"])).mappings().one()
        assert binding["app_run_id"] == run["app_run_id"]
        derived = c.execute(select(grants).where(grants.c.resource_id == artifact["resource_id"])).mappings().all()
        assert len(derived) == 2 and {g["tool_ref"] for g in derived} == {"resource.read"}
        assert {g["principal_id"] for g in derived} == {env[3], data["app"]["runtime_id"]}
        assert not c.execute(select(attempts.c.id)).first() and not c.execute(select(reservations.c.id)).first()


def guarded(store, deliveries):
    return RecordPrivateBarrier(store, {value["run"]["id"] for value in deliveries},
        {value["run"]["app_run_id"] for value in deliveries},
        {value["run"]["output"]["resource_id"] for value in deliveries})


def test_actual_a_b_and_done_fold_independent_records_preserve_immutable_events(env, evidence):
    proof, trace = evidence
    identities = snapshot(env[0], {"principals", "grants"})
    data = ready(env)
    assert snapshot(env[0], {"principals", "grants"}) == identities
    assert data["app"]["input_guidance"]["mode"] == "LOCAL_RECORDS"
    assert [action["executor"] for action in data["app"]["candidate"]["actions"]] == [
        dict(kind="registered_tool", ref="artifact.save_text", version="1")]
    catalog = ok(env[2].get("/api/apps", params={"metadata_only": "true"}))
    entry = next(row for row in catalog["items"] if row["id"] == data["app"]["id"])
    assert entry["use_family"] == "LOCAL_RECORDS" and entry["csv_instance_candidate"] is False
    assert entry["definition_version"] == "local-record-app.v1"
    first = execute(env, data, create_body(current(env, data)))
    assert_saved(env, data, first, 1)
    original_a = saved_rows(env[0], [first])
    second = execute(env, data, create_body(current(env, data), "create-b", TITLE_B, DETAILS_B))
    assert_saved(env, data, second, 2)
    before_done = current(env, data)
    record_a = next(record for record in before_done["records"] if record["title"] == TITLE_A)
    third = execute(env, data, done_body(before_done, record_a))
    assert_saved(env, data, third, 3)
    assert saved_rows(env[0], [first]) == original_a
    events = [value["run"]["event"] for value in (first, second, third)]
    assert [(event["title"], event["state"], event["record_revision"]) for event in events] == [
        (TITLE_A, "OPEN", 1), (TITLE_B, "OPEN", 1), (TITLE_A, "DONE", 2)]
    assert events[0]["record_id"] == events[2]["record_id"] != events[1]["record_id"]
    assert events[0]["previous_event_fingerprint"] is None and events[1]["previous_event_fingerprint"] is None
    assert events[2]["previous_event_fingerprint"] == fingerprint(events[0])
    assert [event["previous_collection_fingerprint"] for event in events] == [None, fingerprint(events[0]), fingerprint(events[1])]
    assert events[0]["reason"] == events[1]["reason"] == "" and events[2]["reason"] == DONE_REASON
    cold = Store(env[1].database_url, test_only=True)
    try:
        with TestClient(create_app(cold, env[1])) as client:
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            client.event_hooks["response"].append(trace)
            before = snapshot(cold)
            state = ok(client.get(data["path"]))
            assert state["data_version"] == 3 and state["revision"] == 1
            records = {record["title"]: record for record in state["records"]}
            assert set(records) == {TITLE_A, TITLE_B}
            assert (records[TITLE_A]["state"], records[TITLE_A]["record_revision"]) == ("DONE", 2)
            assert (records[TITLE_B]["state"], records[TITLE_B]["record_revision"]) == ("OPEN", 1)
            assert records[TITLE_A]["details"] == DETAILS_A and records[TITLE_B]["details"] == DETAILS_B
            assert [row["event"] for row in state["history"]] == events
            assert snapshot(cold) == before
    finally:
        cold.engine.dispose()
    assert snapshot(env[0], {"principals"}) == {"principals": identities["principals"]}
    with env[0].tx() as c:
        writes = [dict(row) for row in c.execute(select(grants).where(grants.c.tool_ref != "resource.read")).mappings()]
    assert sorted(writes, key=lambda row: row["id"]) == sorted(
        [row for row in identities["grants"] if row["tool_ref"] != "resource.read"], key=lambda row: row["id"])
    proof.update(deliveries=[first, second, third], cold_projection=state,
        old_a_exact_rows=original_a, actual_no_model_runs=3, independent_record_states=True,
        catalog_entry=entry)


def test_preview_is_readonly_business_and_strict_typed_commands(env, evidence):
    proof, _ = evidence
    data = ready(env)
    before = snapshot(env[0])
    body = create_body(current(env, data))
    prepared = preview(env, data, body)
    after = snapshot(env[0])
    changed = [name for name in before if before[name] != after[name]]
    assert changed == ["delivery_graph_requests"], changed
    for wrong in [{**body, "request_key": "blank-title", "title": " "},
            {**body, "request_key": "raw-text-bypass", "text": "{\"arbitrary\":true}"}]:
        response = env[2].post(data["path"] + "/previews", json=wrong)
        assert response.status_code in (400, 422), response.text
    assert snapshot(env[0]) == after
    assert current(env, data)["records"] == [] and current(env, data)["data_version"] == 0
    proof.update(preview=prepared, only_metadata_table_changed=changed,
        business_artifacts_grants_runs_unchanged=True)


def test_original_key_cold_get_and_exact_replay_never_duplicate_effect(env, evidence):
    proof, trace = evidence
    data = ready(env)
    body = create_body(current(env, data))
    first = execute(env, data, body)
    before = snapshot(env[0])
    cold = Store(env[1].database_url, test_only=True)
    try:
        with TestClient(create_app(cold, env[1])) as client:
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            client.event_hooks["response"].append(trace)
            path = data["path"] + "/record-requests/" + body["request_key"]
            recovered = ok(client.get(path))
            assert recovered["preview"] == first["prepared"]["preview"]
            assert recovered["preview_fingerprint"] == first["prepared"]["preview_fingerprint"]
            assert recovered["run"]["run_id"] == first["run"]["id"]
            duplicate_preview = ok(client.post(data["path"] + "/previews", json=body), 201)
            assert duplicate_preview["preview_fingerprint"] == recovered["preview_fingerprint"]
            duplicate = ok(client.post(data["path"] + f"/previews/{body['request_key']}/commit",
                json=first["submitted"]), 202)
            assert duplicate["run"]["run_id"] == recovered["run"]["run_id"]
            assert duplicate["run"]["app_run_id"] == recovered["run"]["app_run_id"]
            assert duplicate["run"]["cached"]
            assert client.post(data["path"] + "/previews", json={**body, "title": "different intent"}).status_code == 409
            unknown = client.get(data["path"] + "/record-requests/unknown-never-accepted")
            assert unknown.status_code == 400 and unknown.json()["error"]["code"] == "OUTCOME_UNKNOWN"
            assert snapshot(cold) == before
    finally:
        cold.engine.dispose()
    proof.update(original=first, recovered=recovered, replay=duplicate, actual_no_model_runs=1,
        exact_original_request_recovery=True, additional_business_effects=0)


@pytest.mark.parametrize("stale", ["data_version", "record_revision"])
def test_authentic_record_current_scope_stale_cas_refuses_before_any_effect(env, evidence, stale):
    proof, _ = evidence
    data = ready(env)
    first = execute(env, data, create_body(current(env, data)))
    execute(env, data, create_body(current(env, data), "create-b", TITLE_B, DETAILS_B))
    state = current(env, data)
    record = next(record for record in state["records"] if record["title"] == TITLE_A)
    if stale == "record_revision":
        execute(env, data, done_body(state, record))
        state = current(env, data)
    body = done_body(state, record, "precise-stale-" + stale)
    if stale == "data_version":
        body["expected_data_version"] = 1
    assert body["record_id"] == first["run"]["event"]["record_id"]
    assert body["expected_record_revision"] == 1
    before = snapshot(env[0])
    response = env[2].post(data["path"] + "/previews", json=body)
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "VERSION_CONFLICT"
    assert snapshot(env[0]) == before
    proof.update(stale=stale, current=state, rejected_request=body, rejection=response.json(),
        authentic_record=True, no_business_or_journal_write=True)


def test_account_project_instance_and_legacy_family_scope_before_private_bodies(env, evidence):
    proof, _ = evidence
    data = ready(env)
    first = execute(env, data, create_body(current(env, data)))
    other_iid = ok(env[2].post(f"/api/internal/record-releases/{data['release']['id']}/instances", json=dict(
        expected_release_fingerprint=data["release"]["fingerprint"], request_key="other-local-instance")), 201)["instance"]
    pid = ok(env[2].post("/api/projects", json=dict(name="Other owned record project")), 201)["id"]
    other_project = ready(env, pid, "other-project-form")
    csv = ok(env[2].post(f"/api/projects/{env[5]}/apps/csv-preview", json=dict(
        name="Existing CSV family", resource_id=env[6], goal="Exact synthetic sum")), 201)
    csv_app = ok(env[2].get(f"/api/apps/{csv['id']}"))
    approval = ok(env[2].post(f"/api/internal/apps/{csv['id']}/release-approvals", json=dict(
        expected_draft_fingerprint=csv_app["fingerprint"], sample_input={"column": "amount"})), 201)
    release = ok(env[2].post(f"/api/internal/approvals/{approval['id']}/commit", json=dict(fingerprint=approval["fingerprint"])))
    csv_iid = ok(env[2].post(f"/api/internal/releases/{release['id']}/instances", json=dict(
        expected_release_fingerprint=release["fingerprint"], request_key="legacy-instance")), 201)
    other_paths = [f"/api/internal/record-instances/{other_iid['id']}", other_project["path"]]
    other_states = []
    for path in other_paths:
        empty = ok(env[2].get(path))
        assert empty["records"] == [] and empty["history"] == []
        other_states.append(empty)
    before = snapshot(env[0])
    original = env[2].headers["Authorization"]
    denied = []
    with guarded(env[0], [first]) as barrier:
        for path, empty in zip(other_paths, other_states, strict=True):
            response = env[2].get(path + "/record-requests/create-a")
            assert response.status_code == 400 and response.json()["error"]["code"] == "OUTCOME_UNKNOWN", response.text
            denied.append(dict(path=path, status=response.status_code))
            foreign_record = {"record_id": first["run"]["event"]["record_id"], "record_revision": 1}
            response = env[2].post(path + "/previews", json=done_body(empty, foreign_record, "wrong-scoped-record"))
            assert response.status_code in (403, 409), response.text
            response = env[2].get(path + "/runs/" + first["run"]["id"])
            assert response.status_code in (403, 409), response.text
        response = env[2].get(f"/api/internal/record-instances/{csv_iid['id']}")
        assert response.status_code in (400, 403, 409), response.text
        response = env[2].get(f"/api/internal/instances/{data['instance']['id']}")
        assert response.status_code in (400, 403, 409), response.text
        response = env[2].post(f"/api/internal/instances/{data['instance']['id']}/runs", json=dict(
            expected_revision=data["instance"]["revision"], expected_release_fingerprint=data["release"]["fingerprint"],
            input={"column": "amount"}, request_key="create-a"))
        assert response.status_code in (400, 403, 409), response.text
        try:
            env[2].headers["Authorization"] = "Bearer synthetic-test-B"
            for method, path, body in [("GET", data["path"], None),
                    ("GET", data["path"] + "/record-requests/create-a", None),
                    ("POST", data["path"] + "/previews", create_body({
                        **data["instance"], "release_fingerprint": data["release"]["fingerprint"]}, "foreign-account"))]:
                response = env[2].request(method, path, **({"json": body} if body else {}))
                assert response.status_code == 403, response.text
                denied.append(dict(path=path, method=method, status=response.status_code))
        finally:
            env[2].headers["Authorization"] = original
        assert not barrier.blocked and not barrier.full_binding_reads
        proof.update(denied=denied, blocked=barrier.blocked,
            full_binding_reads=barrier.full_binding_reads, statements=barrier.statements,
            identifier_projection_reads=barrier.identifier_projection_reads)
    assert snapshot(env[0]) == before


def test_project_write_revoke_rejects_before_historical_private_bodies(env, evidence):
    proof, _ = evidence
    data = ready(env)
    first = execute(env, data, create_body(current(env, data)))
    body = create_body(current(env, data), "before-write-revoke", TITLE_B, DETAILS_B)
    prepared = preview(env, data, body)
    with env[0].tx() as c:
        victims = c.execute(select(grants).where(grants.c.principal_id == data["app"]["runtime_id"],
            grants.c.project_id == env[5], grants.c.resource_id == env[5],
            grants.c.tool_ref == "artifact.save_text")).mappings().all()
        assert victims
        for row in victims:
            c.execute(update(grants).where(grants.c.id == row["id"]).values(revoked=True, revision=row["revision"] + 1))
    before = snapshot(env[0])
    with guarded(env[0], [first]) as barrier:
        response = env[2].post(data["path"] + "/previews", json={**body, "request_key": "after-write-revoke"})
        assert response.status_code == 403, response.text
        commit_response = env[2].post(data["path"] + f"/previews/{prepared['request_key']}/commit", json=dict(
            expected_preview_fingerprint=prepared["preview_fingerprint"], consent="WRITE_THIS_EXACT_LOCAL_RECORD_EVENT"))
        assert commit_response.status_code == 403, commit_response.text
        assert not barrier.blocked and not barrier.full_binding_reads
        proof.update(preview_rejected=response.json(), commit_rejected=commit_response.json(),
            blocked=barrier.blocked, full_binding_reads=barrier.full_binding_reads, statements=barrier.statements,
            identifier_projection_reads=barrier.identifier_projection_reads)
    assert snapshot(env[0]) == before


def test_referenced_json_read_revoke_blocks_current_recovery_and_commit_before_bodies(env, evidence):
    proof, _ = evidence
    data = ready(env)
    first = execute(env, data, create_body(current(env, data)))
    prepared = preview(env, data, create_body(current(env, data), "pending-before-read-revoke", TITLE_B, DETAILS_B))
    accepted, commit_body = commit(env, data, prepared)
    with env[0].tx() as c:
        victim = c.execute(select(grants).where(grants.c.principal_id == env[3],
            grants.c.resource_id == first["run"]["output"]["resource_id"],
            grants.c.tool_ref == "resource.read")).mappings().one()
        c.execute(update(grants).where(grants.c.id == victim["id"]).values(revoked=True, revision=victim["revision"] + 1))
    business_before = snapshot(env[0], {"resources", "grants", "local_effects", "operations", "operation_intents", "internal_instance_data"})
    with guarded(env[0], [first]) as barrier:
        denied = []
        for path in [data["path"], data["path"] + "/record-requests/create-a",
                data["path"] + "/runs/" + first["run"]["id"]]:
            response = env[2].get(path)
            assert response.status_code == 403, response.text
            denied.append(dict(path=path, response=response.json()))
        response = env[2].post(data["path"] + f"/previews/{prepared['request_key']}/commit", json=commit_body)
        assert response.status_code == 403, response.text
        stop = ok(env[2].post(data["path"] + "/runs/" + accepted["run"]["run_id"] + "/commands",
            json=dict(command="cancel", version=accepted["run"]["version"])))
        assert stop["status"] == "CANCELLED" and stop["content_access"] is False
        assert not barrier.blocked and not barrier.full_binding_reads
        proof.update(denied=denied, cached_commit_rejected=response.json(), metadata_stop=stop,
            blocked=barrier.blocked, full_binding_reads=barrier.full_binding_reads, statements=barrier.statements,
            identifier_projection_reads=barrier.identifier_projection_reads)
    assert snapshot(env[0], set(business_before)) == business_before


def test_real_json_helper_fault_rolls_back_business_effect_and_keeps_failed_run(env, evidence, monkeypatch):
    from sim2act import local_record_apps as records

    proof, _ = evidence
    data = ready(env)
    prepared = preview(env, data, create_body(current(env, data)))
    accepted, _ = commit(env, data, prepared)
    business = {"resources", "grants", "local_effects", "operations", "operation_intents", "internal_instance_data", "internal_instances"}
    before = snapshot(env[0], business)
    original = records.write_text_artifact
    calls = []

    def saved_then_fail(*args, **kwargs):
        artifact = original(*args, **kwargs)
        calls.append(artifact)
        raise DomainError("VERSION_CONFLICT", "Synthetic failure after actual JSON helper before commit")

    monkeypatch.setattr(records, "write_text_artifact", saved_then_fail)
    assert Worker(env[0], env[1], NoModel()).once()
    assert len(calls) == 1
    assert snapshot(env[0], business) == before
    failed = ok(env[2].get(data["path"] + "/runs/" + accepted["run"]["run_id"]))
    assert failed["status"] == "FAILED" and failed["output"] is None and failed["event"] is None
    assert failed["result_version"] is None and failed["error"]["code"] == "VERSION_CONFLICT"
    state = current(env, data)
    assert state["data_version"] == 0 and state["records"] == [] and state["history"] == []
    proof.update(real_helper_calls=calls, failed_run=failed, current=state,
        business_transaction_fully_rolled_back=True, actual_no_model_runs=1)
