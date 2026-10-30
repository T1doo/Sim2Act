"""One actual ordinary G3/Source2 prefix and a queued Cold, never a full P-B trial.

The dormant producer receives only an exact local synthetic read pin. No trial
approval, stage authority, account source, journal allowance or Cold send exists.
"""

import hashlib
import json
import threading
import time
from functools import partial

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_natural_spec_apps import material
from test_pa_spec_apps import instance
from test_pb_natural_specs import prepare, preview_commit
from test_pb_natural_uses import THIRD
from test_spec_app_operations import snapshot

from sim2act import app_jobs, apps, lifecycle, text_apps
from sim2act import goal_applications as ga
from sim2act import natural_live_admission as admission
from sim2act import natural_spec_runtime as runtime
from sim2act import natural_trial_budget as old_budget
from sim2act import pa_spec_apps as spec
from sim2act import pb_natural_specs as pb
from sim2act import pb_natural_uses as use
from sim2act import production_trial_journal as journal
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.contracts import Limits
from sim2act.db import Store, attempts, goal_application_candidates, runs
from sim2act.goals import inspect_card
from sim2act.production_trial_admission import canonical_quota_subject
from sim2act.spec_production import ProductionTrialBinding
from sim2act.worker import Worker


def dump(path, value):
    from sim2act._cold_source_image import View,plain
    def exported(item):
        return plain(item) if View is not None and type(item) is View else str(item)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=exported) + "\n")


def material_goal(store, user, resource, goal, content):
    inspected = inspect_card(store, user, goal["id"])
    saved = next(row for row in inspected["history"] if row["version"] == goal["version"])
    return dict(resource_id=resource, content=content,
        source_hash=hashlib.sha256(content.encode()).hexdigest(), card_id=goal["id"],
        goal_version=goal["version"], goal_fingerprint=goal["fingerprint"], goal_snapshot=saved["snapshot"])


def test_plain_pb_first_binding_producer_equals_public_complete_ancestry(tmp_path, monkeypatch):
    from test_natural_spec_apps import SOURCE

    mock_calls = []
    original_mock = httpx.MockTransport.handle_request
    original_mock_async = httpx.MockTransport.handle_async_request

    def real_io_forbidden(*args, **kwargs):
        pytest.fail("Plain P-B graph fixture must use only its finite explicit MockTransport")

    def observed_mock(transport, request):
        response = original_mock(transport, request)
        mock_calls.append(dict(request=request.content.decode(), status=response.status_code,
            response=response.content.decode()))
        return response

    async def observed_mock_async(transport, request):
        response = await original_mock_async(transport, request)
        mock_calls.append(dict(request=request.content.decode(), status=response.status_code,
            response=response.content.decode()))
        return response

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", real_io_forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", real_io_forbidden)
    monkeypatch.setattr(httpx.MockTransport, "handle_request", observed_mock)
    monkeypatch.setattr(httpx.MockTransport, "handle_async_request", observed_mock_async)
    url = "sqlite:///" + str(tmp_path / "plain-prefix.db")
    store = Store(url, test_only=True)
    store.initialize()
    user = store.user("Plain PB owner", "synthetic-test-A")
    other = store.user("Plain PB other", "synthetic-test-B")
    settings = Settings(url, tmp_path, mode="mock")
    try:
        with TestClient(create_app(store, settings)) as client:
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            made = client.post("/api/projects", json=dict(name="Dormant first-binding graph"))
            assert made.status_code == 201, made.text
            pid = made.json()["id"]
            # Existing ordinary helpers create real original generation, run its
            # two-node Source to success and save a new independent target Goal.
            prepared = prepare((store, settings, client, user, other, pid, None),
                style="parallel", edit=False)
            data, original_app, source_rid, _, _, path, _, _ = prepared
            try:
                extraction_review, extract = preview_commit(prepared)
                saved = data[2].post(path + "/extractions", json=extract)
                assert saved.status_code == 201, saved.text
                extraction_receipt = saved.json()
                target_app = data[2].get("/api/apps/" + extraction_receipt["id"])
                assert target_app.status_code == 200, target_app.text
                target_app = target_app.json()
                release, inst = instance(data, target_app["id"])
                third, goal = material(data[2], pid, THIRD, "Queued unseen Cold input")
                body = dict(expected_revision=inst["revision"], expected_release_fingerprint=release["fingerprint"],
                    expected_app_fingerprint=target_app["fingerprint"],
                    expected_recipe_fingerprint=target_app["candidate"]["spec_task"]["edited_recipe_fingerprint"],
                    resource_id=third, card_id=goal["id"], expected_goal_version=goal["version"],
                    expected_goal_fingerprint=goal["fingerprint"],
                    expected_source_hash=hashlib.sha256(THIRD.encode()).hexdigest(),
                    request_key="plain-cold-graph-queue")
                route = "/api/internal/instances/" + inst["id"]
                checked = data[2].post(route + "/pb-use-reviews", json=body)
                assert checked.status_code == 200, checked.text
                reviewed = checked.json()
                queued = data[2].post(route + "/pb-use-runs", json=dict(review=body,
                    expected_review_fingerprint=reviewed["review_fingerprint"], consent=use.CONSENT))
                assert queued.status_code == 202, queued.text
                cold_rid = queued.json()["run_id"]
                assert len(mock_calls) == 5  # G3 + Source2; Cold is never processed.
                full = Limits(**{k: getattr(data[1], k) for k in Limits.model_fields})
                with store.tx() as c:
                    current = dict(c.execute(select(runs).where(runs.c.id == cold_rid)).mappings().one())
                    source_job = dict(c.execute(select(runs).where(runs.c.id == source_rid)).mappings().one())
                    generation_rid = c.execute(select(goal_application_candidates.c.run_id)
                        .where(goal_application_candidates.c.app_id == original_app)).scalar_one()
                    generation_attempts = [dict(r) for r in c.execute(select(attempts)
                        .where(attempts.c.run_id == generation_rid)
                        .order_by(attempts.c.created_at, attempts.c.id)).mappings()]
                    source_attempts = [dict(r) for r in c.execute(select(attempts)
                        .where(attempts.c.run_id == source_rid)
                        .order_by(attempts.c.created_at, attempts.c.id)).mappings()]
                    assert len(generation_attempts) == 3 and all(r["status"] == "RECEIVED" for r in generation_attempts)
                    assert source_job["status"] == "SUCCEEDED" and len(source_attempts) == 2
                    assert all(r["status"] == "VERIFIED" for r in source_attempts)
                    assert current["status"] == "QUEUED" and current["fence"] == 0
                    assert c.execute(select(attempts.c.id).where(attempts.c.run_id == cold_rid)).first() is None
                    project_runtime = store.own_project(c, user, pid)["runtime_id"]
                # These values pin continuity only, never approval/source facts.
                trial = admission.PBTrialContract(trial_key="synthetic-first-binding-pin", project_id=pid,
                    principal_id=user, runtime_id=project_runtime,
                    quota_subject=canonical_quota_subject("synthetic-first-binding-account"),
                    software_fingerprint="b" * 64, authorization_fingerprint="c" * 64,
                    bindings=[material_goal(store, user, data[5], data[6], SOURCE),
                              material_goal(store, user, third, goal, THIRD)],
                    stage_keys=dict(generate="natural-generation", source="spec-actual", cold=body["request_key"]),
                    expires_at=time.time() + 3600, path="P-B",
                    extraction_request_key=extract["review"]["request_key"], extraction_recipe=extract["review"]["recipe"])
                binding = ProductionTrialBinding(trial, "synthetic-unapproved-read-pin", "synthetic-first-binding-account")
                worker = object.__new__(Worker)
                worker.store, worker.s, worker.pa_trial = store, data[1], binding
                worker.id, worker.stop, worker.goal_planner_transport = "synthetic-first-binding-reader", threading.Event(), None
                worker._journal_trial_store, worker._journal_trial_binding = store, binding
                worker._journal_trial_drift = False
                before = snapshot(store)
                assert not any(row["kind"].startswith((journal.KIND, old_budget.KIND))
                    for row in before["delivery_graph_requests"])

                # Compute the ordinary complete oracle before installing any
                # ancestry tripwire and outside the strict read scope/token.
                with store.tx() as c, pb._source_reads(store, c):
                    expected_cold = spec.bound(store, c, user, current, full)
                    expected_source, expected_source_proof = pb.source(store, c, user, pid, source_rid, full)
                    outputs, proved = spec.receipts(store, c, source_job, expected_source, allow_pending=True)
                    expected_native = spec._native_audit_facts(store, c, user, expected_source["draft"])
                    expected_source_audit = pb.source_audit(store, c, user, pid, source_rid)
                    base = expected_cold["release"]["snapshot"]["draft"]
                    expected_extraction_origin = pb.verify(store, c, user, base, full)
                    expected_extraction_audit = pb.audit_fingerprint(store, c, user, base)
                    expected_use = use.bound(store, c, user, current, expected_cold["snapshot"],
                        expected_cold["release"], full)
                assert snapshot(store) == before
                blocked = []

                def ancestry_forbidden(name, *args, **kwargs):
                    blocked.append(name)
                    pytest.fail("Dormant producer re-entered full ancestor " + name)

                # Pure predicates, fixed scope/SQL leaves and private producers
                # remain real. No fake result is returned for an ancestor.
                tripwires = [(ga, ("source", "initial_messages", "history", "_history", "verified_candidate", "_verified_candidate", "parse_candidate")),
                    (spec, ("bound", "_bound", "verify_job", "receipts", "verify_origin", "model_source", "audit_fingerprint", "from_response")),
                    (pb, ("source", "_source", "source_audit", "_source_audit", "review", "verify", "audit_fingerprint")),
                    (use, ("bound", "review", "audit")),
                    (runtime, ("counters", "prove_node", "prove_pending", "ledger_digest")),
                    (apps, ("validate_frozen_candidate",)), (lifecycle, ("read_release", "_read_release")),
                    (app_jobs, ("load_binding",)), (text_apps, ("verify_origin",))]
                with monkeypatch.context() as barrier:
                    for module, names in tripwires:
                        for name in names:
                            barrier.setattr(module, name, partial(ancestry_forbidden, module.__name__ + "." + name))
                    barrier.setattr(httpx.MockTransport, "handle_request", real_io_forbidden)
                    barrier.setattr(httpx.MockTransport, "handle_async_request", real_io_forbidden)
                    with store.tx() as c, pb._source_reads(store, c):
                        roles = dict(source=full.model_copy(deep=True), generate=None,
                            platform=full, trial=full.model_copy(deep=True), per_use=full.model_copy(deep=True))
                        with runtime._cold_graph_read(worker, c, dict(current=current), roles, "pre") as guard:
                            graph = runtime._cold_first_binding(worker, c, guard, current, full)
                            assert graph.guard is guard and guard.active and not blocked
                            assert graph.binding == expected_cold
                            assert graph.source_binding == expected_source
                            assert graph.source_outputs == outputs and graph.source_proved == proved
                            assert graph.source_facts.proof == expected_source_proof
                            assert graph.source_audit.digest == expected_source_audit
                            assert graph.native_audit == expected_native
                            assert graph.extraction_origin == expected_extraction_origin
                            assert graph.extraction_audit == expected_extraction_audit
                            assert graph.use_value == expected_use
                            assert graph.binding["source"]["resource_id"] == third
                            assert graph.source_binding["source"]["resource_id"] == data[5]
                            assert graph.binding["release"]["id"] == release["id"]
                            assert graph.source_binding["snapshot"]["run_id"] == source_rid
                            assert len(graph.generation_history[1]) == 3
                            # Compare the complete visible SQL protocol after the private
                            # reader transfers ownership; quoted_name keys remain
                            # trusted SQL labels in the independently queried rows.
                            from sim2act import _cold_source_image as generation_image
                            assert generation_image.compat(graph.generation_history[1]) == generation_attempts
                            assert graph.native_audit["attempts"] == sorted(generation_attempts, key=lambda row: row["id"])
                            assert dict(graph.source_facts.typed.typed) == next(row
                                for row in before["internal_instance_data"]
                                if row["instance_id"] == graph.source_binding["snapshot"]["instance_id"]
                                and row["run_id"] == graph.source_binding["snapshot"]["app_run_id"])
                            dump(tmp_path / "dormant-first-binding-proof.json", dict(
                                scope="ORDINARY_G3_SOURCE2_QUEUED_COLD_LOCAL_FACTS_ONLY",
                                trial_authority=False, cold_processed=False, blocked_ancestors=blocked,
                                mock_calls=mock_calls, generation_run=generation_rid,
                                source_run=source_rid, cold_run=cold_rid,
                                source_binding=graph.source_binding, cold_binding=graph.binding,
                                native_audit=graph.native_audit, source_proof=graph.source_facts.proof,
                                source_typed=dict(graph.source_facts.typed.typed),
                                source_audit=graph.source_audit.rows, source_outputs=graph.source_outputs,
                                source_proved=graph.source_proved,
                                extraction_review=graph.extraction_review.checked,
                                extraction_audit=graph.extraction_audit,
                                extraction_manifest=graph.extraction_origin[0].model_dump(),
                                use_candidate=graph.use_value[0], use_manifest=graph.use_value[1].model_dump(),
                                use_report=graph.use_value[2], use_source=graph.use_value[3], use_goal=graph.use_value[4]))
                        assert not guard.active
                    first_guard = guard
                    # A second independent transaction/token/guard collects the
                    # original audit edge before any complete binding producer.
                    # No prior graph/facts object is passed into this epoch.
                    with store.tx() as c, pb._source_reads(store, c):
                        roles = dict(source=full.model_copy(deep=True), generate=None,
                            platform=full, trial=full.model_copy(deep=True), per_use=full.model_copy(deep=True))
                        with runtime._cold_graph_read(worker, c, dict(current=current), roles, "post") as seed_guard:
                            assert seed_guard is not first_guard
                            assert seed_guard.transaction is not first_guard.transaction
                            assert seed_guard.token is not first_guard.token
                            audit_seed = runtime._cold_audit_seed(worker, c, seed_guard, expected_cold["draft"])
                            assert audit_seed.guard is seed_guard and seed_guard.active
                            assert audit_seed.native == expected_native
                            assert audit_seed.source_audit.digest == expected_source_audit
                            assert audit_seed.extraction_audit == expected_extraction_audit
                            assert audit_seed.audit == expected_cold["audit_fingerprint"]
                            assert not any(key.startswith("run-facts:") for key in seed_guard.inputs)
                            assert not any(key.startswith("generation:") for key in seed_guard.inputs)
                            seeded_graph = runtime._cold_first_binding(worker, c, seed_guard, current, full,
                                audit_seed=audit_seed)
                            assert seeded_graph.guard is seed_guard and seed_guard.active and not blocked
                            assert seeded_graph.binding == expected_cold
                            assert seeded_graph.source_binding == expected_source
                            assert seeded_graph.source_outputs == outputs and seeded_graph.source_proved == proved
                            assert seeded_graph.source_facts.proof == expected_source_proof
                            assert seeded_graph.source_audit.digest == expected_source_audit
                            assert seeded_graph.native_audit == expected_native
                            assert seeded_graph.extraction_origin == expected_extraction_origin
                            assert seeded_graph.extraction_audit == expected_extraction_audit
                            assert seeded_graph.use_value == expected_use
                            assert seeded_graph.binding["source"]["resource_id"] == third
                            assert seeded_graph.source_binding["source"]["resource_id"] == data[5]
                            assert seeded_graph.binding["release"]["id"] == release["id"]
                            assert seeded_graph.source_binding["snapshot"]["run_id"] == source_rid
                            assert len(seeded_graph.generation_history[1]) == 3
                            assert generation_image.compat(seeded_graph.generation_history[1]) == generation_attempts
                            assert seeded_graph.native_audit["attempts"] == sorted(generation_attempts, key=lambda row: row["id"])
                            assert dict(seeded_graph.source_facts.typed.typed) == next(row
                                for row in before["internal_instance_data"]
                                if row["instance_id"] == seeded_graph.source_binding["snapshot"]["instance_id"]
                                and row["run_id"] == seeded_graph.source_binding["snapshot"]["app_run_id"])
                            assert seeded_graph.source_counter_reader._raw_seed is audit_seed.source_seed
                            assert seeded_graph.generation_reader.raw_seed is audit_seed.generation_seed
                            assert seeded_graph.native_audit is audit_seed.native
                            assert seeded_graph.source_audit is audit_seed.source_audit
                            assert seeded_graph.extraction_audit_prefix is audit_seed.extraction_prefix
                            assert seeded_graph.use_audit_prefix is audit_seed.use_prefix
                            assert len(mock_calls) == 5 and not blocked
                            dump(tmp_path / "dormant-audit-seed-first-binding-proof.json", dict(
                                scope="FRESH_SECOND_EPOCH_AUDIT_FIRST_RAW_ONLY_G3_SOURCE2_QUEUED_COLD",
                                trial_authority=False, cold_processed=False, blocked_ancestors=blocked,
                                mock_calls=mock_calls, audit_seed=audit_seed.fields(),
                                source_binding=seeded_graph.source_binding, cold_binding=seeded_graph.binding,
                                source_outputs=seeded_graph.source_outputs, source_proved=seeded_graph.source_proved,
                                source_proof=seeded_graph.source_facts.proof,
                                source_typed=dict(seeded_graph.source_facts.typed.typed),
                                generation_history=seeded_graph.generation_history,
                                extraction_origin=[seeded_graph.extraction_origin[0].model_dump(),
                                    *seeded_graph.extraction_origin[1:]],
                                use_value=[seeded_graph.use_value[0], seeded_graph.use_value[1].model_dump(),
                                    *seeded_graph.use_value[2:]]))
                        assert not seed_guard.active
                after = snapshot(store)
                assert after == before and len(mock_calls) == 5
                assert next(row for row in after["runs"] if row["id"] == cold_rid) == current
                assert not [row for row in after["attempts"] if row["run_id"] == cold_rid]
                dump(tmp_path / "before-producer-55.json", before)
                dump(tmp_path / "after-producer-55.json", after)
                dump(tmp_path / "fixture-extraction.json", dict(review=extraction_review,
                    receipt=extraction_receipt, use_review=reviewed, queued=queued.json(),
                    generation_attempts=generation_attempts, source_attempts=source_attempts))
            finally:
                data[2].close()
    finally:
        store.engine.dispose()
