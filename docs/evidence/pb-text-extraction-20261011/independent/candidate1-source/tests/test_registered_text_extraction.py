"""Synthetic provenance, actual authenticated API and durable literal Worker; LIVE0."""

import copy
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert, select, update
from test_goal_text_applications import (
    fixture_candidate,
    release_instance,
    run_input,
    setup,
    wire,
)

from sim2act.api import create_app
from sim2act.db import (
    Store,
    app_drafts,
    attempts,
    fingerprint,
    grants,
    internal_app_runs,
    internal_instance_data,
    meta,
    new_id,
    operation_intents,
    operations,
    principals,
    resources,
    runs,
    task_extractions,
)
from sim2act.worker import Worker

FRESH = "# Different source\nGamma new obligation\nAlpha new evidence\nGamma final note\n"


def make_app(data, name):
    store, settings, client, _, pid, resource, card = data
    sent = []

    def handler(request):
        payload = json.loads(request.content)
        sent.append(payload)
        initial = json.loads(payload["messages"][1]["content"])
        if len(sent) == 1:
            message = {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "actual-source-read",
                        "type": "function",
                        "function": {
                            "name": "resource.read",
                            "arguments": json.dumps({"resource_id": resource}),
                        },
                    }
                ],
            }
            return httpx.Response(200, json=wire(message, "tool_calls"))
        receipt = json.loads(next(m["content"] for m in payload["messages"] if m["role"] == "tool"))
        assert receipt["status"] == "VERIFIED" and receipt["data"]["resource_id"] == resource
        value = fixture_candidate(initial)
        value["source_hash"] = receipt["data"]["hash"]
        return httpx.Response(200, json=wire({"role": "assistant", "content": json.dumps(value)}))

    queued = client.post(
        f"/api/projects/{pid}/goal-cards/{card['id']}/application-runs",
        json={
            "expected_version": card["version"],
            "expected_fingerprint": card["fingerprint"],
            "request_key": "pb-fixture-generation-" + name,
        },
    )
    assert queued.status_code == 202, queued.text
    rid = queued.json()["run_id"]
    assert Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler)).once()
    result = client.get(f"/api/runs/{rid}").json()
    reply = client.post(
        f"/api/runs/{rid}/confirm-application-candidate",
        json={
            "expected_version": result["version"],
            "candidate_fingerprint": result["result"]["candidate_fingerprint"],
            "request_key": "confirm-pb-" + name,
            "name": name,
        },
    )
    assert reply.status_code == 200, reply.text
    aid = reply.json()["id"]
    # The accepted name is a display detail only; no candidate rewrites.
    assert client.get(f"/api/apps/{aid}").status_code == 200
    return aid


def prepared(env, format="md"):
    data = setup(env)
    aid = make_app(data, "source")
    release, instance = release_instance(data, aid)
    source_run = run_input(data, release, instance, {"term": "Beta"}, "pb-source")
    assert source_run["status"] == "SUCCEEDED"
    client, pid = data[2], data[4]
    response = client.post(
        f"/api/projects/{pid}/resources",
        json={
            "name": "different." + format,
            "format": format,
            "content": FRESH,
        },
    )
    assert response.status_code == 201, response.text
    resource = response.json()["id"]
    goal = copy.deepcopy(data[6]["content"])
    goal["resource_refs"] = [resource]
    made = client.post(f"/api/projects/{pid}/goal-cards", json=goal)
    assert made.status_code == 201, made.text
    card = client.get(f"/api/goal-cards/{made.json()['id']}").json()
    target_data = (*data[:5], resource, card)
    target = make_app(target_data, "target")
    url = f"/api/internal/instances/{instance['id']}/runs/{source_run['id']}"
    return data, aid, release, instance, source_run, target, resource, url


def request(data, url, target):
    response = data[2].get(url + "/extraction-options")
    assert response.status_code == 200, response.text
    values = response.json()
    selected = next(t for t in values["targets"] if t["id"] == target)
    return values, {
        "expected_proof_fingerprint": values["source_proof_fingerprint"],
        "target_app_id": target,
        "expected_target_draft_fingerprint": selected["fingerprint"],
        "name": "Extracted literal task",
        "request_key": "text-extraction",
    }


def authority(store):
    with store.tx() as c:
        return {
            t.name: [dict(r) for r in c.execute(select(t).order_by(t.c.id)).mappings()]
            for t in (principals, grants)
        }


@pytest.mark.parametrize("format", ["txt", "md"])
def test_completed_text_apprun_extracts_new_material_cold_worker(env, format):
    data, aid, source_release, source_instance, source_run, target, resource, url = prepared(
        env, format
    )
    from test_owner_acceptance import choice_body, prepare

    review, _ = prepare(data, source_release, source_instance, source_run)
    decision = data[2].post(
        f"/api/internal/instances/{source_instance['id']}/owner-review-requests",
        json=choice_body(review),
    )
    assert decision.status_code == 201, decision.text
    options, body = request(data, url, target)
    assert options["proof"]["kind"] == "completed_registered_text_apprun.v1"
    before = authority(data[0])
    old_rows = snapshot(data[0])
    made = data[2].post(url + "/extract", json=body)
    assert made.status_code == 201, made.text
    result = made.json()
    assert result["id"] not in {aid, target}
    assert result["model_requests"] == 0 and result["formal_publication_enabled"] is False
    assert result["owner_acceptance"] == "PENDING"
    assert authority(data[0]) == before
    assert_old_rows(data[0], old_rows)
    recovered = data[2].get(
        url + "/extraction-receipts", params={"request_key": body["request_key"]}
    )
    assert recovered.status_code == 200 and recovered.json()["id"] == result["id"]
    assert recovered.json()["cached"] is True
    assert data[2].post(url + "/extract", json=body).json()["id"] == result["id"]
    assert data[2].post(url + "/extract", json={**body, "name": "changed"}).status_code == 409
    assert_old_rows(data[0], old_rows)
    cold = Store(data[1].database_url, test_only=True)
    try:
        with TestClient(create_app(cold, data[1])) as client:
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            cold_data = (cold, data[1], client, *data[3:])
            draft = client.get("/api/apps/" + result["id"])
            assert draft.status_code == 200, draft.text
            candidate = draft.json()["candidate"]
            assert "goal_application" not in candidate
            assert candidate["manifest"]["origin"] == "task_run"
            assert candidate["manifest"]["source_run_ref"] == source_run["id"]
            assert candidate["manifest"]["data_bindings"][0]["resource_ref"] == resource
            release, instance = release_instance(cold_data, result["id"])
            assert instance["id"] != source_instance["id"]
            actual = run_input(cold_data, release, instance, {"term": "Gamma"}, "fresh-gamma")
            assert actual["status"] == "SUCCEEDED", actual
            assert actual["id"] != source_run["id"] and actual["result_version"] == 1
            assert actual["result"]["resource_id"] == resource
            assert actual["result"]["citations"] == [
                {"start_line": 2, "end_line": 2, "quote": "Gamma new obligation"},
                {"start_line": 4, "end_line": 4, "quote": "Gamma final note"},
            ]
            assert actual["result"] != source_run["result"]
            review = client.get(f"/api/internal/instances/{instance['id']}/owner-review").json()
            assert review["owner_acceptance"] == "PENDING" and review["history"] == []
            missing = run_input(cold_data, release, instance, {"term": "Unseen absent"}, "no-hit")
            assert missing["status"] == "SUCCEEDED" and missing["result"]["citations"] == []
            invalid = run_input(cold_data, release, instance, {"term": " Gamma "}, "wrong-term")
            assert invalid["status"] == "FAILED" and invalid["result"] is None
            # Recursive extraction and old owner declarations cannot become this app's source.
            new_url = f"/api/internal/instances/{instance['id']}/runs/{actual['id']}"
            assert client.get(new_url + "/extraction-options").status_code == 400
    finally:
        cold.engine.dispose()
    assert authority(data[0]) == before


def snapshot(store):
    with store.tx() as c:
        return {
            table.name: [dict(row) for row in c.execute(select(table)).mappings()]
            for table in meta.sorted_tables
        }


def assert_old_rows(store, before):
    after = snapshot(store)
    for table, rows in before.items():
        if table in {"app_drafts", "task_extractions"}:
            for row in rows:
                assert row in after[table], table
        else:
            assert rows == after[table], table


@pytest.mark.parametrize(
    "fault",
    [
        "PARTIAL",
        "FAILED",
        "QUEUED",
        "RUNNING",
        "cancel",
        "error",
        "attempt",
        "unknown",
        "extra-operation",
        "record",
        "receipt",
        "intent",
        "typed-output",
        "context",
        "source-bytes",
        "generation-attempt",
    ],
)
def test_polluted_source_rejects_new_cached_and_keyed_read(env, fault):
    data, _, _, _, source, target, _, url = prepared(env)
    _, body = request(data, url, target)
    made = data[2].post(url + "/extract", json=body)
    assert made.status_code == 201, made.text
    with data[0].tx() as c:
        job = c.execute(select(runs).where(runs.c.id == source["id"])).mappings().one()
        op = (
            c.execute(select(operations).where(operations.c.run_id == source["id"]))
            .mappings()
            .one()
        )
        if fault in {"PARTIAL", "FAILED", "QUEUED", "RUNNING"}:
            c.execute(update(runs).where(runs.c.id == source["id"]).values(status=fault))
        elif fault in {"cancel", "error", "context"}:
            values = (
                {"cancel_intent": True} if fault == "cancel" else {"error": {"code": "polluted"}}
            )
            if fault == "context":
                values = {"context": {**job["context"], "requests": 1}}
            c.execute(update(runs).where(runs.c.id == source["id"]).values(**values))
        elif fault == "attempt":
            c.execute(
                insert(attempts).values(
                    id=new_id("attempt"), run_id=source["id"], status="RECEIVED"
                )
            )
        elif fault == "generation-attempt":
            draft = c.execute(select(app_drafts).where(app_drafts.c.id == target)).mappings().one()
            c.execute(
                update(attempts)
                .where(attempts.c.run_id == draft["candidate"]["goal_application"]["run_id"])
                .values(response={"unexpected": "pollution"})
            )
        elif fault == "unknown":
            c.execute(
                update(operations)
                .where(operations.c.id == op["id"])
                .values(status="OUTCOME_UNKNOWN")
            )
        elif fault == "extra-operation":
            c.execute(
                insert(operations).values(**{**dict(op), "id": new_id("op"), "call_id": "extra"})
            )
        elif fault == "record":
            row = (
                c.execute(
                    select(internal_instance_data).where(
                        internal_instance_data.c.run_id == source["app_run_id"]
                    )
                )
                .mappings()
                .one()
            )
            polluted = {"result": {**row["data"]["result"], "term": "unexpected"}}
            c.execute(
                update(internal_instance_data)
                .where(internal_instance_data.c.run_id == row["run_id"])
                .values(data=polluted, fingerprint=fingerprint(polluted))
            )
        elif fault == "receipt":
            c.execute(
                update(operations)
                .where(operations.c.id == op["id"])
                .values(receipt={**op["receipt"], "artifact_refs": ["unexpected"]})
            )
        elif fault == "intent":
            intent = {"tool": "resource.read", "args": {"resource_id": data[5], "term": "Beta"}}
            c.execute(
                update(operation_intents)
                .where(operation_intents.c.operation_id == op["id"])
                .values(request=intent)
            )
            c.execute(
                update(operations)
                .where(operations.c.id == op["id"])
                .values(fingerprint=fingerprint(intent))
            )
        elif fault == "typed-output":
            output = copy.deepcopy(source["result"])
            output["citations"] = []
            c.execute(
                update(internal_app_runs)
                .where(internal_app_runs.c.id == source["app_run_id"])
                .values(output=output)
            )
        else:
            c.execute(
                update(resources).where(resources.c.id == data[5]).values(content="changed source")
            )
    before = snapshot(data[0])
    for path, method, payload in [
        (url + "/extract", "POST", body),
        (url + "/extract", "POST", {**body, "request_key": "different"}),
        (url + "/extraction-receipts?request_key=" + body["request_key"], "GET", None),
        ("/api/apps/" + made.json()["id"], "GET", None),
    ]:
        response = data[2].request(method, path, json=payload)
        assert response.status_code in {400, 403, 409}, (fault, response.text)
    assert snapshot(data[0]) == before


@pytest.mark.parametrize("domain", ["source", "target"])
def test_actual_grant_revoke_rejects_cached_receipt_and_queued_commit(env, domain):
    data, source_app, _, _, _, target, _, url = prepared(env)
    _, body = request(data, url, target)
    made = data[2].post(url + "/extract", json=body).json()
    release, instance = release_instance(data, made["id"])
    queued = data[2].post(
        f"/api/internal/instances/{instance['id']}/runs",
        json={
            "expected_revision": instance["revision"],
            "expected_release_fingerprint": release["fingerprint"],
            "input": {"term": "Gamma"},
            "request_key": "queued-revoke",
        },
    )
    assert queued.status_code == 202, queued.text
    app = data[2].get("/api/apps/" + (source_app if domain == "source" else target)).json()
    grant = next(
        g
        for g in data[2].get(f"/api/projects/{data[4]}/grants").json()
        if g["principal_id"] == app["runtime_id"] and not g["revoked"]
    )
    denied = data[2].post(
        f"/api/grants/{grant['id']}/revoke",
        json={"command": "revoke", "version": grant["revision"]},
    )
    assert denied.status_code == 200, denied.text
    before = snapshot(data[0])
    assert data[2].post(url + "/extract", json=body).status_code == 403
    assert (
        data[2]
        .get(url + "/extraction-receipts", params={"request_key": body["request_key"]})
        .status_code
        == 403
    )
    assert snapshot(data[0]) == before
    assert Worker(data[0], data[1]).once()
    with data[0].tx() as c:
        job = c.execute(select(runs).where(runs.c.id == queued.json()["run_id"])).mappings().one()
        assert job["status"] == "WAITING_RESOURCE" and job["error"]["code"] == "GRANT_REVOKED"
        assert (
            list(
                c.execute(
                    select(internal_instance_data).where(
                        internal_instance_data.c.instance_id == instance["id"]
                    )
                )
            )
            == []
        )


def test_extraction_scope_versions_recovery_and_concurrency(env):
    from concurrent.futures import ThreadPoolExecutor

    data, _, _, _, _, target, _, url = prepared(env)
    _, body = request(data, url, target)
    before = snapshot(data[0])
    assert data[2].get(url + "/extraction-receipts?request_key=unknown").status_code == 400
    assert snapshot(data[0]) == before
    for field in ("expected_proof_fingerprint", "expected_target_draft_fingerprint"):
        assert data[2].post(url + "/extract", json={**body, field: "0" * 64}).status_code == 409
    for field in (
        "candidate",
        "runtime",
        "provider",
        "offline_replay",
        "permissions",
        "owner_acceptance",
    ):
        assert data[2].post(url + "/extract", json={**body, field: {}}).status_code == 422
    assert snapshot(data[0]) == before
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda _: data[2].post(url + "/extract", json=body), range(2)))
    assert all(r.status_code == 201 for r in replies)
    assert replies[0].json()["id"] == replies[1].json()["id"]
    assert sum(r.json()["cached"] for r in replies) == 1
    assert_old_rows(data[0], before)
    data[2].headers["Authorization"] = "Bearer synthetic-test-B"
    assert data[2].get(url + "/extraction-options").status_code == 403
    assert (
        data[2]
        .get(url + "/extraction-receipts", params={"request_key": body["request_key"]})
        .status_code
        == 403
    )
    assert data[2].post(url + "/extract", json=body).status_code == 403


@pytest.mark.parametrize("fault", ["marker", "remove", "executor", "term-wiring", "runtime"])
def test_resigned_text_candidate_does_not_replace_independent_origin(env, fault):
    data, _, _, _, _, target, _, url = prepared(env)
    _, body = request(data, url, target)
    made = data[2].post(url + "/extract", json=body).json()
    with data[0].tx() as c:
        draft = c.execute(select(app_drafts).where(app_drafts.c.id == made["id"])).mappings().one()
        candidate = copy.deepcopy(draft["candidate"])
        if fault == "marker":
            row = (
                c.execute(select(task_extractions).where(task_extractions.c.app_id == made["id"]))
                .mappings()
                .one()
            )
            c.execute(
                update(task_extractions)
                .where(task_extractions.c.app_id == made["id"])
                .values(snapshot={**row["snapshot"], "kind": "registered_csv_source.v1"})
            )
        elif fault == "remove":
            candidate.pop("task_proof")
            candidate["manifest"].update(origin="goal", source_run_ref=None)
        elif fault == "executor":
            candidate["actions"][0]["executor"]["ref"] = "data.aggregate_csv"
        elif fault == "term-wiring":
            candidate["manifest"]["workflow"][0]["inputs"]["term"] = {
                "source": "literal",
                "value": "Beta",
            }
        else:
            c.execute(
                update(app_drafts)
                .where(app_drafts.c.id == made["id"])
                .values(runtime_id="appruntime_unbound")
            )
        c.execute(
            update(app_drafts)
            .where(app_drafts.c.id == made["id"])
            .values(candidate=candidate, fingerprint=fingerprint(candidate))
        )
    before = snapshot(data[0])
    assert data[2].get("/api/apps/" + made["id"]).status_code in {400, 403, 409}
    assert data[2].get(
        url + "/extraction-receipts", params={"request_key": body["request_key"]}
    ).status_code in {400, 403, 409}
    assert snapshot(data[0]) == before


def test_text_extraction_rolls_back_both_inserts_and_rejects_foreign_target(env):
    from sqlalchemy import event

    from sim2act.errors import DomainError

    data, _, _, _, _, target, _, url = prepared(env)
    _, body = request(data, url, target)
    before = snapshot(data[0])

    def reject_second_insert(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO task_extractions"):
            raise DomainError("VERSION_CONFLICT", "Controlled second-insert failure")

    event.listen(data[0].engine, "before_cursor_execute", reject_second_insert)
    try:
        assert data[2].post(url + "/extract", json=body).status_code == 409
    finally:
        event.remove(data[0].engine, "before_cursor_execute", reject_second_insert)
    assert snapshot(data[0]) == before
    assert (
        data[2]
        .get(url + "/extraction-receipts", params={"request_key": body["request_key"]})
        .status_code
        == 400
    )
    other = data[2].post("/api/projects", json={"name": "foreign target project"}).json()["id"]
    material = (
        data[2]
        .post(
            f"/api/projects/{other}/resources",
            json={
                "name": "foreign.csv",
                "format": "csv",
                "content": "amount\n7\n",
            },
        )
        .json()["id"]
    )
    target_app = (
        data[2]
        .post(
            f"/api/projects/{other}/apps/csv-preview",
            json={
                "name": "foreign domain",
                "resource_id": material,
                "goal": "foreign",
            },
        )
        .json()["id"]
    )
    fingerprint_value = data[2].get("/api/apps/" + target_app).json()["fingerprint"]
    before = snapshot(data[0])
    rejected = data[2].post(
        url + "/extract",
        json={
            **body,
            "target_app_id": target_app,
            "expected_target_draft_fingerprint": fingerprint_value,
        },
    )
    assert rejected.status_code == 403, rejected.text
    assert snapshot(data[0]) == before


@pytest.mark.parametrize("fault", ["cancel", "revoke", "source-version"])
def test_actual_late_compute_cannot_commit_after_invalidation(env, monkeypatch, fault):
    from sim2act import app_jobs

    data, _, _, _, source, target, _, url = prepared(env)
    _, body = request(data, url, target)
    made = data[2].post(url + "/extract", json=body).json()
    release, instance = release_instance(data, made["id"])
    queued = data[2].post(
        f"/api/internal/instances/{instance['id']}/runs",
        json={
            "expected_revision": instance["revision"],
            "expected_release_fingerprint": release["fingerprint"],
            "input": {"term": "Gamma"},
            "request_key": "late-frozen-compute",
        },
    )
    assert queued.status_code == 202, queued.text
    rid = queued.json()["run_id"]
    original = app_jobs.compute
    delivered = []

    def late_compute(plan, *args, **kwargs):
        value = original(plan, *args, **kwargs)
        delivered.append(value)
        if fault == "cancel":
            current = data[2].get(f"/api/internal/instances/{instance['id']}/runs/{rid}").json()
            reply = data[2].post(
                f"/api/runs/{rid}/commands",
                json={"command": "cancel", "version": current["version"]},
            )
            assert reply.status_code == 200, reply.text
        elif fault == "revoke":
            app = data[2].get("/api/apps/" + target).json()
            grant = next(
                g
                for g in data[2].get(f"/api/projects/{data[4]}/grants").json()
                if g["principal_id"] == app["runtime_id"] and not g["revoked"]
            )
            reply = data[2].post(
                f"/api/grants/{grant['id']}/revoke",
                json={"command": "revoke", "version": grant["revision"]},
            )
            assert reply.status_code == 200, reply.text
        else:
            with data[0].tx() as c:
                c.execute(
                    update(runs)
                    .where(runs.c.id == source["id"])
                    .values(version=source["version"] + 1)
                )
        return value

    monkeypatch.setattr(app_jobs, "compute", late_compute)
    assert Worker(data[0], data[1]).once()
    assert len(delivered) == 1 and delivered[0]["citations"]
    with data[0].tx() as c:
        job = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert job["status"] in {"CANCELLED", "WAITING_RESOURCE", "FAILED"}, dict(job)
        assert job["result"] is None
        assert (
            c.execute(
                select(internal_instance_data).where(
                    internal_instance_data.c.instance_id == instance["id"]
                )
            ).first()
            is None
        )


def test_text_cold_worker_never_reads_unrelated_private_history(env, tmp_path):
    from sql_private_barrier import PrivateReadBarrier
    from test_run_private_read_scope import historical

    data, _, _, _, _, target, _, url = prepared(env)
    _, body = request(data, url, target)
    old, old_row = historical(env)
    # This synthetic unrelated history is a read barrier, not a completed extraction source.
    barrier = PrivateReadBarrier(data[0], {old}, {env[6]})
    with barrier:
        made = data[2].post(url + "/extract", json=body)
        assert made.status_code == 201, made.text
        release, instance = release_instance(data, made.json()["id"])
        cold = Store(data[1].database_url, test_only=True)
        barrier.attach(cold)
        try:
            with TestClient(create_app(cold, data[1])) as client:
                client.headers["Authorization"] = "Bearer synthetic-test-A"
                result = run_input(
                    (cold, data[1], client, *data[3:]),
                    release,
                    instance,
                    {"term": "Gamma"},
                    "private-cold-text",
                )
                assert result["status"] == "SUCCEEDED", result
                assert result["result"]["citations"][0]["quote"] == "Gamma new obligation"
        finally:
            cold.engine.dispose()
    assert not barrier.blocked
    with data[0].tx() as c:
        assert dict(c.execute(select(runs).where(runs.c.id == old)).mappings().one()) == old_row
    (tmp_path / "unrelated-private-read-proof.json").write_text(
        json.dumps(
            {
                "blocked": barrier.blocked,
                "sql": barrier.statements,
                "scope": "unrelated synthetic Run/CSV cells only; related original provenance audit is allowed",
            },
            indent=2,
        )
    )
