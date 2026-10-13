"""Success provenance to editable task-origin recipe and actual cold Worker reuse."""

import copy
import hashlib
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from test_natural_spec_apps import COLD, SOURCE, enqueue, inspect, material, ready, setup, transport
from test_pa_spec_apps import instance
from test_spec_app_operations import snapshot

from sim2act import natural_specs as natural
from sim2act import pb_natural_specs as pb
from sim2act.api import create_app
from sim2act.db import (
    Store,
    app_drafts,
    attempts,
    fingerprint,
    grants,
    internal_instance_data,
    operations,
    runs,
)
from sim2act.worker import Worker


def drive_to_success(data, rid, backend):
    """Finite real worker claims; once() is progress, never a success receipt."""
    import time

    from sim2act.db import events, internal_run_bindings

    store, settings = data[:2]
    worker = Worker(store, settings, goal_planner_transport=backend)
    claims = []
    with store.tx() as c:
        header = dict(c.execute(select(runs.c.status, runs.c.fence, runs.c.lease_until,
            runs.c.created_at, runs.c.cancel_intent, runs.c.principal_id, runs.c.project_id)
            .where(runs.c.id == rid)).mappings().one())
        clock = c.execute(select(internal_run_bindings.c.snapshot["natural_spec_clock"])
            .where(internal_run_bindings.c.run_id == rid)).scalar_one()
    original = header["created_at"]
    assert header["principal_id"] == data[3] and header["project_id"] == data[4]
    deadline = min(clock["deadline"], original + settings.run_seconds)
    assert clock["created_at"] == original and header["status"] == "QUEUED"
    assert not header["cancel_intent"]
    try:
        for index in range(3):
            before = header
            if index:
                assert before["status"] == "RUNNING" and not before["cancel_intent"]
                assert time.time() >= before["lease_until"] and time.time() < deadline
                with store.tx() as c:
                    assert not store.has_unknown(c, rid)
            claimed = worker.once()
            with store.tx() as c:
                header = dict(c.execute(select(runs.c.status, runs.c.fence, runs.c.lease_until,
                    runs.c.created_at, runs.c.cancel_intent, runs.c.principal_id, runs.c.project_id)
                    .where(runs.c.id == rid)).mappings().one())
                claimed_events = c.execute(select(events.c.id).where(events.c.run_id == rid,
                    events.c.kind == "CLAIMED", events.c.data["fence"].as_integer() == header["fence"])).scalars().all()
                current_clock = c.execute(select(internal_run_bindings.c.snapshot["natural_spec_clock"])
                    .where(internal_run_bindings.c.run_id == rid)).scalar_one()
            claims.append(dict(before=before, after=header, claimed=claimed))
            assert claimed and header["created_at"] == original and current_clock == clock
            assert header["fence"] > before["fence"] and len(claimed_events) == 1
            assert header["principal_id"] == data[3] and header["project_id"] == data[4]
            if header["status"] == "SUCCEEDED":
                return claims
        raise AssertionError("Bounded worker claims did not produce a successful actual Run")
    finally:
        (settings.data_dir / ("worker-claims-" + rid + ".json")).write_text(json.dumps(dict(
            run_id=rid, accepted_clock=clock, settings_lease_seconds=settings.lease_seconds,
            max_claims=3, claims=claims), ensure_ascii=False, indent=2))


def prepare(env, style="single", edit=True):
    data = setup(env)
    _, aid, release, inst, _ = ready(data, style)
    rid = enqueue(data, release, inst)
    sent = []
    drive_to_success(data, rid, transport(sent))
    assert inspect(data, inst, rid).json()["status"] == "SUCCEEDED"
    target_rid, goal = material(data[2], data[4], COLD, "Independent P-B target")
    path = f"/api/projects/{data[4]}/natural-spec-task-runs/{rid}"
    before = snapshot(data[0])
    result = data[2].get(path + "/extraction-options")
    assert result.status_code == 200, result.text
    options = result.json()
    assert snapshot(data[0]) == before
    graph = copy.deepcopy(options["recipe"])
    if edit:
        if style == "single":
            graph["steps"][1]["step_id"] = "edited_inference"
            for step in graph["steps"]:
                step["depends_on"] = ["edited_inference" if ref == "infer_pick" else ref for ref in step["depends_on"]]
                for port in step["inputs"].values():
                    if port.get("ref") == "infer_pick":
                        port["ref"] = "edited_inference"
        else:
            step = graph["steps"][2]
            step["depends_on"] = [graph["steps"][0]["step_id"]]
            step["inputs"].pop("prior_items", None)
            step["inputs"].pop("prior_feedback", None)
    body = dict(source_run_id=rid, expected_source_proof_fingerprint=options["source_proof_fingerprint"],
        expected_source_recipe_fingerprint=options["recipe_fingerprint"], card_id=goal["id"],
        expected_goal_version=goal["version"], expected_goal_fingerprint=goal["fingerprint"],
        expected_source_hash=hashlib.sha256(COLD.encode()).hexdigest(),
        recipe=graph, name="Reviewed P-B checklist", request_key="pb-original-key")
    return data, aid, rid, target_rid, goal, path, body, options


def preview_commit(prepared):
    data, _, _, _, _, path, body, _ = prepared
    before = snapshot(data[0])
    reply = data[2].post(path + "/extraction-reviews", json=body)
    assert reply.status_code == 200, reply.text
    review = reply.json()
    assert snapshot(data[0]) == before
    assert review["review_fingerprint"] == fingerprint({k: v for k, v in review.items() if k != "review_fingerprint"})
    commit = dict(review=body, expected_review_fingerprint=review["review_fingerprint"],
                  consent=pb.CONSENT, artifact_write_consent=natural.CONSENT)
    return review, commit


@pytest.mark.parametrize("style", ["single", "sequential"])
def test_success_to_editable_task_origin_and_cold_new_material(env, tmp_path, style):
    prepared = prepare(env, style)
    data, origin_app, rid, target_rid, _, path, body, options = prepared
    checked, commit = preview_commit(prepared)
    assert checked["original_recipe"] == options["recipe"]
    assert checked["edited_recipe"] == body["recipe"] != options["recipe"]
    assert checked["edited_recipe_execution"] == "NOT_RUN"
    assert checked["sample_scope"] == "SUCCESSFUL_SOURCE_ONLY"
    assert checked["preview"]["status"] == "MODEL_EXECUTION_REQUIRED"
    with data[0].tx() as c:
        old_job = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
        old_rows = [dict(x) for x in c.execute(select(internal_instance_data)).mappings()]
    made = data[2].post(path + "/extractions", json=commit)
    assert made.status_code == 201, made.text
    result = made.json()
    assert result["reviewed"] == checked and result["id"] != origin_app
    draft = data[2].get(f"/api/apps/{result['id']}")
    assert draft.status_code == 200, draft.text
    value = draft.json()["candidate"]
    assert value["manifest"]["origin"] == "task_run" and value["manifest"]["source_run_ref"] == rid
    assert value["spec_task"]["kind"] == pb.KIND and value["spec_recipe"] == body["recipe"]
    assert SOURCE not in json.dumps(value) and value["manifest"]["data_bindings"][0]["resource_ref"] == target_rid
    with data[0].tx() as c:
        runtime_grants = c.execute(select(grants).where(grants.c.principal_id == result["runtime_id"])).mappings().all()
        assert {(r["resource_id"], r["tool_ref"]) for r in runtime_grants} == {(target_rid, natural.READ), (data[4], natural.SAVE)}
    before = snapshot(data[0])
    assert data[2].post(path + "/extractions", json=commit).json() == result
    assert data[2].get(path + "/extractions/by-key/pb-original-key").json() == result
    assert snapshot(data[0]) == before
    release, inst = instance(data, result["id"])
    cold = Store(data[1].database_url, test_only=True)
    try:
        with TestClient(create_app(cold, data[1])) as client:
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            current = (cold, data[1], client, *data[3:])
            job = enqueue(current, release, inst)
            sent = []
            drive_to_success(current, job, transport(sent, COLD))
            saved = inspect(current, inst, job)
            assert saved.status_code == 200 and saved.json()["status"] == "SUCCEEDED", saved.text
            checklist = saved.json()["result"]["checklist"]
            assert checklist["source_content"] == COLD and checklist["source"]["resource_id"] == target_rid
            assert len(checklist["human_unresolved"]) == 16
            assert checklist["owner_acceptance"] == "PENDING" and checklist["semantic_goal_acceptance"] == "NOT_RUN"
            assert SOURCE not in json.dumps(sent) and len(sent) == (1 if style == "single" else 2)
            # A new extraction cannot hide an unsupported recursive P-B chain.
            refused = client.get(f"/api/projects/{data[4]}/natural-spec-task-runs/{job}/extraction-options")
            assert refused.status_code == 409, refused.text
        with cold.tx() as c:
            assert dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one()) == old_job
            current_rows = {r["run_id"]: dict(r) for r in c.execute(select(internal_instance_data)).mappings()}
            assert all(current_rows[row["run_id"]] == row for row in old_rows)
        (tmp_path / "proof.json").write_text(json.dumps(dict(options=options, review=checked, receipt=result,
            result=saved.json(), wire=sent, real_model_requests=0), ensure_ascii=False, indent=2))
    finally:
        cold.engine.dispose()


@pytest.mark.parametrize("fault", ["source_grant", "source_artifact_grant", "target_grant", "other_user"])
def test_current_permissions_precede_protected_source_or_target_reads(env, tmp_path, fault):
    from sql_private_barrier import PrivateReadBarrier

    prepared = prepare(env)
    data, _, rid, target_rid, _, path, _, _ = prepared
    checked, commit = preview_commit(prepared)
    made = data[2].post(path + "/extractions", json=commit)
    assert made.status_code == 201, made.text
    with data[0].tx() as c:
        output_id = c.execute(select(operations.c.receipt).where(operations.c.run_id == rid,
            operations.c.tool_ref == natural.SAVE)).scalar_one()["data"]["resource_id"]
        if fault != "other_user":
            resource = target_rid if fault == "target_grant" else output_id if fault == "source_artifact_grant" else data[5]
            c.execute(update(grants).where(grants.c.resource_id == resource).values(revoked=True))
    if fault == "other_user":
        data[2].headers["Authorization"] = "Bearer synthetic-test-B"
    before = snapshot(data[0])
    protected_runs = set() if fault == "target_grant" else {rid}
    protected_resources = {target_rid} if fault == "target_grant" else {data[5], output_id}
    with PrivateReadBarrier(data[0], protected_runs, protected_resources) as barrier:
        paths = [path + "/extractions/by-key/pb-original-key", f"/api/apps/{made.json()['id']}"]
        if fault != "target_grant":
            paths.append(path + "/extraction-options")
        for request_path in paths:
            response = data[2].get(request_path)
            assert response.status_code == 403, response.text
        assert not barrier.blocked
        (tmp_path / "permission-barrier.json").write_text(json.dumps(dict(fault=fault,
            blocked=barrier.blocked, statements=barrier.statements), indent=2))
    assert snapshot(data[0]) == before


@pytest.mark.parametrize("fault", ["typed", "receipt", "attempt", "not_successful"])
def test_corrupt_or_incomplete_success_is_never_extracted(env, fault):
    prepared = prepare(env)
    data, _, rid, _, _, path, _, _ = prepared
    with data[0].tx() as c:
        if fault == "typed":
            row = c.execute(select(internal_instance_data).where(
                internal_instance_data.c.run_id == prepared[7]["source_proof"]["app_run_id"])).mappings().one()
            c.execute(update(internal_instance_data).where(
                internal_instance_data.c.instance_id == row["instance_id"], internal_instance_data.c.version == row["version"])
                .values(fingerprint="0" * 64))
        elif fault == "receipt":
            op = c.execute(select(operations).where(operations.c.run_id == rid,
                operations.c.tool_ref.in_(list(natural.MODEL_KINDS)))).mappings().one()
            changed = copy.deepcopy(op["receipt"])
            changed["data"]["items"][0]["summary"] = "altered source"
            c.execute(update(operations).where(operations.c.id == op["id"]).values(receipt=changed))
        elif fault == "attempt":
            c.execute(update(attempts).where(attempts.c.run_id == rid).values(usage={"total_tokens": 0}))
        else:
            c.execute(update(runs).where(runs.c.id == rid).values(status="RUNNING"))
    before = snapshot(data[0])
    response = data[2].get(path + "/extraction-options")
    assert response.status_code in {400, 409}, response.text
    assert snapshot(data[0]) == before


@pytest.mark.parametrize("fault", ["budget", "constant", "cycle", "focus"])
def test_edited_recipe_cannot_expand_budget_or_remove_checks(env, fault):
    from test_natural_spec_apps import recipe

    prepared = prepare(env)
    data, _, _, _, _, path, body, _ = prepared
    if fault == "budget":
        body["recipe"] = recipe("sequential")
    elif fault == "constant":
        body["recipe"]["steps"][0]["inputs"]["resource_id"] = dict(source="constant", value="old answer")
    elif fault == "cycle":
        body["recipe"]["steps"][0]["depends_on"] = [body["recipe"]["steps"][1]["step_id"]]
    else:
        body["recipe"]["steps"][1]["operator"] = "model.spec.requirements"
    before = snapshot(data[0])
    response = data[2].post(path + "/extraction-reviews", json=body)
    assert response.status_code in {400, 409, 422}, response.text
    if fault == "budget":
        assert response.json()["error"]["code"] == "BUDGET_EXHAUSTED"
    assert snapshot(data[0]) == before


@pytest.mark.parametrize("fault", ["review", "goal", "key", "marker"])
def test_stale_review_conflicting_key_or_removed_marker_rejected(env, fault):
    from sim2act.db import goal_cards

    prepared = prepare(env)
    data, _, _, _, goal, path, body, _ = prepared
    checked, commit = preview_commit(prepared)
    if fault in {"key", "marker"}:
        made = data[2].post(path + "/extractions", json=commit)
        assert made.status_code == 201, made.text
    if fault == "review":
        commit["review"]["name"] = "Different from reviewed name"
    elif fault == "goal":
        with data[0].tx() as c:
            c.execute(update(goal_cards).where(goal_cards.c.id == goal["id"]).values(version=2))
    elif fault == "key":
        body["name"] = "Another body for same key"
        _, commit = preview_commit(prepared)
    else:
        with data[0].tx() as c:
            app = c.execute(select(app_drafts).where(app_drafts.c.id == made.json()["id"])).mappings().one()
            value = copy.deepcopy(app["candidate"])
            value.pop("spec_task")
            c.execute(update(app_drafts).where(app_drafts.c.id == app["id"])
                      .values(candidate=value, fingerprint=fingerprint(value)))
    before = snapshot(data[0])
    result = data[2].get(f"/api/apps/{made.json()['id']}") if fault == "marker" else data[2].post(path + "/extractions", json=commit)
    assert result.status_code == 409, result.text
    assert snapshot(data[0]) == before


@pytest.mark.parametrize("fault", ["source_revoke", "target_revoke", "source_audit"])
def test_last_save_rechecks_and_rolls_back_every_created_object(env, monkeypatch, tmp_path, fault):
    prepared = prepare(env)
    data, _, rid, target_rid, _, path, _, _ = prepared
    _, commit = preview_commit(prepared)
    original = pb.remember
    triggered = []

    def remember(c, user, aid, kind, key, body, value):
        original(c, user, aid, kind, key, body, value)
        if kind == pb.EXTRACT:
            triggered.append(kind)
            if fault.endswith("revoke"):
                resource = data[5] if fault == "source_revoke" else target_rid
                c.execute(update(grants).where(grants.c.resource_id == resource).values(revoked=True))
            else:
                op = c.execute(select(operations.c.id).where(operations.c.run_id == rid)).scalars().first()
                c.execute(update(operations).where(operations.c.id == op).values(status="PREPARED"))

    monkeypatch.setattr(pb, "remember", remember)
    before = snapshot(data[0])
    response = data[2].post(path + "/extractions", json=commit)
    assert triggered == [pb.EXTRACT] and response.status_code in {403, 409}, response.text
    assert snapshot(data[0]) == before
    (tmp_path / "atomic-rollback.json").write_text(json.dumps(dict(fault=fault,
        triggered=triggered, error=response.json(), all_tables_equal=True,
        same_transaction_fault_injection=True), indent=2))


@pytest.mark.parametrize("fault", ["status", "effect_pointer", "effect_and_event", "current_goal"])
def test_source_gate_and_fresh_audit_close_review_blockers(env, tmp_path, fault):
    from sql_private_barrier import PrivateReadBarrier

    from sim2act.db import events, goal_cards, local_effects
    from sim2act.errors import DomainError

    prepared = prepare(env)
    data, _, rid, target_rid, _, _, _, options = prepared
    with data[0].tx() as c:
        baseline = pb.source_audit(data[0], c, data[3], data[4], rid)
        output_id = c.execute(select(local_effects.c.resource_id).join(operations,
            operations.c.id == local_effects.c.operation_id).where(operations.c.run_id == rid,
            operations.c.tool_ref == natural.SAVE)).scalar_one()
        if fault == "current_goal":
            gid = c.execute(select(goal_cards.c.id).where(goal_cards.c.project_id == data[4],
                goal_cards.c.id != prepared[4]["id"])).scalar_one()
            c.execute(update(goal_cards).where(goal_cards.c.id == gid).values(title="concurrent source Goal change"))
            assert pb.source_audit(data[0], c, data[3], data[4], rid) != baseline
        else:
            c.execute(update(grants).where(grants.c.resource_id == output_id).values(revoked=True))
            if fault == "status":
                c.execute(update(runs).where(runs.c.id == rid).values(status="RUNNING"))
            else:
                op = c.execute(select(operations.c.id).where(operations.c.run_id == rid,
                    operations.c.tool_ref == natural.SAVE)).scalar_one()
                c.execute(update(local_effects).where(local_effects.c.operation_id == op).values(resource_id=target_rid))
                if fault == "effect_and_event":
                    c.execute(update(events).where(events.c.run_id == rid,
                        events.c.kind == "SPEC_COMMITTED").values(data=dict(
                            artifact_resource=target_rid, result_version=options["source_proof"]["result_version"])))
    before = snapshot(data[0])
    if fault != "current_goal":
        with PrivateReadBarrier(data[0], {rid}, {data[5], output_id}) as barrier:
            with data[0].tx() as c, pytest.raises(DomainError):
                pb.source_audit(data[0], c, data[3], data[4], rid)
            assert barrier.blocked == []
        assert snapshot(data[0]) == before
    (tmp_path / "review-blocker-proof.json").write_text(json.dumps(dict(
        fault=fault, source_audit_changed=fault == "current_goal",
        protected_cell_evaluations=0 if fault != "current_goal" else None,
        failed_read_writes=0), indent=2))


def test_successful_pa_bound_source_has_closed_origin_audit_and_pb_cold_reuse(env, tmp_path):
    from sim2act import pa_spec_apps as spec
    from sim2act.db import delivery_graph_requests, goal_cards, task_extractions

    data = setup(env)
    generation, _, _, _, _ = ready(data)
    _, goal = material(data[2], data[4], COLD, "P-A bound source")
    route = f"/api/projects/{data[4]}/natural-spec-model-runs/{generation}"
    options = data[2].get(route + "/binding-options", params=dict(card_id=goal["id"])).json()
    binding_body = dict(card_id=goal["id"], expected_goal_version=goal["version"],
        expected_goal_fingerprint=goal["fingerprint"], expected_source_hash=options["source_hash"],
        expected_model_candidate_fingerprint=options["model_candidate_fingerprint"],
        expected_recipe_fingerprint=options["recipe_fingerprint"], name="Bound successful source",
        consent=natural.CONSENT, request_key="pb-bound-source")
    bound = data[2].post(route + "/bindings", json=binding_body)
    assert bound.status_code == 201, bound.text
    release, inst = instance(data, bound.json()["id"])
    rid = enqueue(data, release, inst)
    drive_to_success(data, rid, transport([], COLD))
    assert inspect(data, inst, rid).json()["status"] == "SUCCEEDED"
    target, target_goal = material(data[2], data[4], SOURCE, "Independent P-B reverse target")
    path = f"/api/projects/{data[4]}/natural-spec-task-runs/{rid}"
    reply = data[2].get(path + "/extraction-options")
    assert reply.status_code == 200, reply.text
    options = reply.json()
    body = dict(source_run_id=rid, expected_source_proof_fingerprint=options["source_proof_fingerprint"],
        expected_source_recipe_fingerprint=options["recipe_fingerprint"], card_id=target_goal["id"],
        expected_goal_version=target_goal["version"], expected_goal_fingerprint=target_goal["fingerprint"],
        expected_source_hash=hashlib.sha256(SOURCE.encode()).hexdigest(), recipe=options["recipe"],
        name="P-B from explicit P-A bound success", request_key="pb-from-bound")
    prepared = (data, bound.json()["id"], rid, target, target_goal, path, body, options)
    _, commit = preview_commit(prepared)
    made = data[2].post(path + "/extractions", json=commit)
    assert made.status_code == 201, made.text
    release, inst = instance(data, made.json()["id"])
    cold = Store(data[1].database_url, test_only=True)
    try:
        with TestClient(create_app(cold, data[1])) as client:
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            current = (cold, data[1], client, *data[3:])
            job = enqueue(current, release, inst)
            sent = []
            drive_to_success(current, job, transport(sent, SOURCE))
            result = inspect(current, inst, job)
            assert result.json()["status"] == "SUCCEEDED", result.text
            assert result.json()["result"]["checklist"]["source_content"] == SOURCE
            assert COLD not in json.dumps(sent)
        # Each origin record and current bound Goal affects a fresh audit in its
        # own transaction; injected changes are rolled back and never committed.
        from sim2act.errors import DomainError
        with cold.tx() as c:
            baseline = pb.source_audit(cold, c, data[3], data[4], rid)
            for table, predicate, values in [
                (task_extractions, task_extractions.c.app_id == bound.json()["id"], dict(request_fingerprint="0" * 64)),
                (delivery_graph_requests, (delivery_graph_requests.c.app_id == bound.json()["id"]) &
                    (delivery_graph_requests.c.kind == spec.BIND), dict(request_fingerprint="0" * 64)),
                (goal_cards, goal_cards.c.id == goal["id"], dict(title="changed bound Goal")),
            ]:
                savepoint = c.begin_nested()
                c.execute(update(table).where(predicate).values(**values))
                try:
                    assert pb.source_audit(cold, c, data[3], data[4], rid) != baseline
                except DomainError:
                    pass  # Stronger rejection also prevents a matching guard.
                finally:
                    savepoint.rollback()
            assert pb.source_audit(cold, c, data[3], data[4], rid) == baseline
        (tmp_path / "bound-origin-proof.json").write_text(json.dumps(dict(
            receipt=made.json(), cold_result=result.json(), marker_seal_goal_faults=3,
            real_model_requests=0), ensure_ascii=False, indent=2))
    finally:
        cold.engine.dispose()


@pytest.mark.parametrize("fault", ["source_revoke", "source_changed", "cancel", "bad_output"])
def test_pb_cold_runtime_rejects_late_source_or_output_without_typed_save(env, tmp_path, fault):
    prepared = prepare(env)
    data, _, source_run, _, _, path, _, _ = prepared
    _, commit = preview_commit(prepared)
    made = data[2].post(path + "/extractions", json=commit)
    assert made.status_code == 201, made.text
    release, inst = instance(data, made.json()["id"])
    rid = enqueue(data, release, inst)
    sent = []

    def mutate(raw, payload):
        if fault == "bad_output":
            content = json.loads(raw["choices"][0]["message"]["content"])
            content["items"][0]["citations"][0]["quote"] = "wrong source quote"
            raw["choices"][0]["message"]["content"] = json.dumps(content)
        else:
            with data[0].tx() as c:
                if fault == "source_revoke":
                    c.execute(update(grants).where(grants.c.resource_id == data[5]).values(revoked=True))
                elif fault == "source_changed":
                    c.execute(update(attempts).where(attempts.c.run_id == source_run).values(usage=12345))
                else:
                    c.execute(update(runs).where(runs.c.id == rid).values(cancel_intent=True))

    before = snapshot(data[0])
    assert Worker(data[0], data[1], goal_planner_transport=transport(sent, COLD, mutate)).once()
    with data[0].tx() as c:
        assert not c.execute(select(internal_instance_data).where(
            internal_instance_data.c.instance_id == inst["id"])).first()
        assert not c.execute(select(operations).where(operations.c.run_id == rid,
            operations.c.tool_ref == natural.SAVE)).first()
        job = c.execute(select(runs.c.status).where(runs.c.id == rid)).scalar_one()
        assert job != "SUCCEEDED"
        known = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().one()
        assert known["status"] == "REJECTED_KNOWN" and known["response"]["received_raw"]
    assert len(sent) == 1
    after = snapshot(data[0])
    assert before["app_drafts"] == after["app_drafts"]
    (tmp_path / "late-runtime-proof.json").write_text(json.dumps(dict(fault=fault,
        runtime_status=job, typed_saves=0, artifact_saves=0, attempt_status=known["status"],
        source_audit_or_permission_changed=fault.startswith("source"), real_model_requests=0), indent=2))
