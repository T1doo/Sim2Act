"""Fresh original P-A controllers, synthetic account facts and exact MockTransport.

The module prefix is generated once at real wall-clock 1 RPM. No old DB,
qualified association, private holdout, provider or semantic acceptance is used.
"""

import base64
import copy
import hashlib
import json
import time
from dataclasses import replace

import httpx
import pytest
import test_natural_spec_apps as apps
from fastapi.testclient import TestClient
from sqlalchemy import event, select, update
from test_natural_live_admission import frozen
from test_pa_trial_dispatch import enqueue_generation, first_response
from test_spec_app_operations import snapshot

from sim2act import natural_live_admission as gate
from sim2act import natural_trial_budget as old_budget
from sim2act import pa_trial_dispatch as bridge
from sim2act import pb_natural_uses as use
from sim2act import production_evidence as evidence
from sim2act import production_trial_admission as admission
from sim2act import production_trial_journal as journal
from sim2act import production_trial_sender as sender
from sim2act import production_trial_source as source
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, attempts, fingerprint, meta, runs
from sim2act.db import delivery_graph_requests as rows
from sim2act.errors import DomainError
from sim2act.worker import Worker


def write(path, value):
    path.write_text(json.dumps(value, indent=2, default=str) + "\n")


def prepare(env, out):
    data = apps.setup(env)
    account = "offline-pa-stages-account"
    subject = admission.canonical_quota_subject(account)
    data = (data[0], replace(data[1], quota_subject=subject), *data[2:])
    data[0].initialize(quota_subject=subject)
    original, approval = frozen(data, ttl=3600)
    at = time.time()
    contract = gate.TrialContractV2.model_validate(original.model_dump() | dict(
        namespace="natural-live-trial.v2", quota_subject=subject, prepared_at=at,
        review_expires_at=at + 300, execution_expires_at=at + 3600, expires_at=at + 3600))
    approval = approval.model_copy(update=dict(
        expected_contract_fingerprint=fingerprint(contract.model_dump())))
    gate.approve(data[0], data[3], contract, approval)
    binding = bridge.JournalTrialBinding(contract, approval.request_key, account)
    scope = evidence.requirements_for(data[3], contract, approval.request_key)
    common = dict(issuer=source.ISSUER, requirements_fingerprint=fingerprint(scope.model_dump()),
        account_id=account, provider=scope.provider, model=scope.model, endpoint=scope.endpoint,
        observed_at=at - 600, expires_at=scope.expires_at)
    bundle = dict(version="UNINSTALLED_SYNTHETIC_ACCOUNT_SOURCE_V1",
        identity=dict(common, role="identity", identity_confirmed=True),
        entitlement=dict(common, role="entitlement", legal_free_entitlement=True),
        enforcement=dict(common, role="enforcement", enforced_zero_charge=True, paid_cap=0,
                         billable_fallback_disabled=True),
        status=dict(common, role="status", revoked=False))
    raw = json.dumps(bundle, indent=1).encode()
    (out / "raw-synthetic-account-source.json").write_bytes(raw)
    with data[0].tx() as c:
        journal._cas_pair(c, data[3], data[4], source.KIND, contract.trial_key, None,
            journal._snapshot(source.request_for(scope, account), dict(
                provenance="UNINSTALLED_SYNTHETIC_FIXTURE",
                raw_b64=base64.b64encode(raw).decode("ascii"))))
    return data, binding


def approve_stage(data, binding, stage, rid):
    reviewed = gate.stage_review(data[0], data[3], binding.contract, binding.approval_key, stage, rid)
    consent = gate.StageApproveInput(
        authority=gate.StageAuthorityV2.model_validate(reviewed["authority"]),
        expected_authority_fingerprint=reviewed["authority_fingerprint"],
        approval_key=binding.approval_key, request_key=stage + "-new-journal-consent",
        consent="BIND_ONLY_THIS_ACCEPTED_STAGE_RUN_APP_RELEASE_AND_COMPLETE_GOAL_TO_ORIGINAL_TRIAL")
    gate.approve_stage(data[0], data[3], binding.contract, consent)
    return reviewed, consent


@pytest.fixture(scope="module")
def actual_prefix(tmp_path_factory):
    out = tmp_path_factory.mktemp("actual-prefix")
    url = "sqlite:///" + str(out / "fixture.db")
    store = Store(url, test_only=True)
    store.initialize()
    user = store.user("fixture A", "synthetic-test-A")
    other = store.user("fixture B", "synthetic-test-B")
    settings = Settings(url, out, mode="mock")
    with TestClient(create_app(store, settings)) as client:
        client.headers["Authorization"] = "Bearer synthetic-test-A"
        project = client.post("/api/projects", json=dict(name="Fresh stages synthetic fixture"))
        assert project.status_code == 201, project.text
        data, binding = prepare((store, settings, client, user, other, project.json()["id"], None), out)
        workers = []

        def factory(*args, **kwargs):
            transport = kwargs["goal_planner_transport"]

            def pretty(request):
                response = transport.handler(request)
                return httpx.Response(response.status_code,
                    content=json.dumps(json.loads(response.content), indent=1).encode())

            kwargs["goal_planner_transport"] = httpx.MockTransport(pretty)
            worker = Worker(*args, **kwargs, pa_trial=binding)
            workers.append(worker)
            return worker

        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(apps, "Worker", factory)
            generation, app, release, inst, generated = apps.ready(data, style="ordered")
        source_id = apps.enqueue(data, release, inst)
        reviewed, source_consent = approve_stage(data, binding, "source", source_id)
        source_sent = []
        assert factory(data[0], data[1], goal_planner_transport=apps.transport(source_sent)).once()
        source_result = apps.inspect(data, inst, source_id)
        assert source_result.status_code == 200, source_result.text
        assert source_result.json()["status"] == "SUCCEEDED", source_result.text
        target = binding.contract.bindings[1]
        current = data[2].get("/api/internal/instances/" + inst["id"]).json()
        review = dict(expected_revision=current["revision"],
            expected_release_fingerprint=release["fingerprint"],
            expected_app_fingerprint=reviewed["authority"]["candidate_fingerprint"],
            expected_recipe_fingerprint=reviewed["authority"]["recipe_fingerprint"],
            resource_id=target.resource_id, card_id=target.card_id,
            expected_goal_version=target.goal_version, expected_goal_fingerprint=target.goal_fingerprint,
            expected_source_hash=target.source_hash, request_key=binding.contract.stage_keys.cold)
        route = "/api/internal/instances/" + inst["id"]
        preview = data[2].post(route + "/pa-use-reviews", json=review)
        assert preview.status_code == 200, preview.text
        body = dict(review=review, expected_review_fingerprint=preview.json()["review_fingerprint"],
                    consent=use.PA_CONSENT)
        queued = data[2].post(route + "/pa-use-runs", json=body)
        assert queued.status_code == 202, queued.text
        cold = queued.json()["run_id"]
        _, cold_consent = approve_stage(data, binding, "cold", cold)
        cold_sent = []
        assert factory(data[0], data[1], goal_planner_transport=apps.transport(cold_sent, apps.COLD)).once()
        cold_result = apps.inspect(data, inst, cold)
        assert cold_result.status_code == 200, cold_result.text
        assert cold_result.json()["status"] == "SUCCEEDED", cold_result.text
        t = dict(data=data, binding=binding, generation=generation, source=source_id, cold=cold,
            app=app, release=release, instance=inst, generated=generated, source_sent=source_sent,
            cold_sent=cold_sent, source_result=source_result.json(), cold_result=cold_result.json(),
            source_consent=source_consent, cold_consent=cold_consent, workers=workers, out=out)
        yield t
        data[2].close()
    store.engine.dispose()


def test_actual_pa_three_two_two_reaches_existing_results_and_pending_owner(actual_prefix):
    t = actual_prefix
    data, binding = t["data"], t["binding"]
    accounting = journal.read(data[0], data[3], binding.contract, binding.approval_key, binding.account_id)
    slots = accounting.ledger.slots
    assert len(slots) == 7 and all(s.accepted for s in slots) and not accounting.ledger.halted
    assert len(t["generated"]) == 3 and len(t["source_sent"]) == len(t["cold_sent"]) == 2
    gaps = [b.reserved_at - a.reserved_at for a, b in zip(slots, slots[1:], strict=False)]
    assert all(g >= 60 for g in gaps)
    assert {s.identity.stage: s.identity.run_id for s in slots} == dict(
        generate=t["generation"], source=t["source"], cold=t["cold"])
    before = snapshot(data[0])
    results = {}
    for stage, text in (("source", apps.SOURCE), ("cold", apps.COLD)):
        result = t[stage + "_result"]
        checklist = result["result"]["checklist"]
        assert checklist["source_content"] == text
        assert [i["summary"] for i in checklist["items"]] == [i["summary"] for i in apps.facts(text)]
        assert checklist["owner_acceptance"] == "PENDING"
        assert checklist["semantic_goal_acceptance"] == "NOT_RUN"
        artifact = data[2].get(f"/api/internal/app-run-jobs/{t[stage]}/spec-artifact")
        assert artifact.status_code == 200, artifact.text
        assert json.loads(artifact.json()["resource"]["content"])["source_content"] == text
        owner = data[2].get(f"/api/internal/instances/{t['instance']['id']}/runs/{t[stage]}/spec-owner-review")
        assert owner.status_code == 200, owner.text
        assert owner.json()["owner_acceptance"] == "PENDING"
        history = gate.recover_stage(data[0], data[3], binding.contract, binding.approval_key,
                                     stage, t[stage + "_consent"].request_key)
        assert history["dispatch_authorized"] is False
        results[stage] = dict(run_id=t[stage], result=result, artifact=artifact.json(),
                             owner_review=owner.json(), history=history)
    assert snapshot(data[0]) == before
    with data[0].tx() as c:
        actual = c.execute(select(attempts).where(attempts.c.run_id.in_(
            [t["generation"], t["source"], t["cold"]]))).mappings().all()
        assert {a["id"] for a in actual} == {s.identity.attempt_id for s in slots}
        assert c.execute(select(rows.c.kind).where(rows.c.kind.in_(
            [old_budget.KIND, old_budget.KIND + "_seal", bridge.SENT, bridge.SENT + "_seal"]))).all() == []
        bodies = c.execute(select(rows).where(rows.c.kind.in_([bridge.REQUEST, bridge.RESPONSE])))
        bodies = [dict(r) for r in bodies.mappings()]
        assert len(bodies) == 14
        for row in bodies:
            body = row["snapshot"]["response"]
            payload = base64.b64decode(body["body_b64"], validate=True)
            assert hashlib.sha256(payload).hexdigest() == body["sha256"]
            assert len(payload) == body["byte_count"] and body["received_complete"]
            if row["kind"] == bridge.RESPONSE:
                assert body["sha256"] != body["canonical_sha256"]
        for stage, rid in (("generate", t["generation"]), ("source", t["source"]), ("cold", t["cold"])):
            bridge.journal_stage_accounted(data[0], c, data[3], binding.contract, binding.approval_key, rid, stage)
    write(t["out"] / "actual-pa-stages.json", dict(accounting=accounting.model_dump(mode="json"),
        gaps=gaps, actual_attempts=[dict(a) for a in actual], bodies=bodies, results=results,
        real_provider_calls=0, live_installed=False, semantic_acceptance="NOT_RUN"))


def test_fresh_actual_prefix_rejects_incomplete_mixed_or_changed_proof_without_writes(actual_prefix):
    t = actual_prefix
    data, b = t["data"], t["binding"]
    store = data[0]
    baseline = snapshot(store)
    observed = []
    from sim2act.goal_applications import verified_candidate
    from sim2act.pb_natural_specs import _source_reads
    with store.tx() as c:
        transaction = c.begin_nested()
        job = c.execute(select(runs).where(runs.c.id == t["generation"])).mappings().one()
        with _source_reads(store, c):
            first = verified_candidate(store, c, job, gate._limits(b.contract))
            token = c.info["pb_source_reads"]
            assert any(k[0] == "journal-trial-complete-generation" for k in token.results)
            second = verified_candidate(store, c, job, gate._limits(b.contract))
            assert first == second and first is not second
            aid = c.execute(select(attempts.c.id).where(attempts.c.run_id == job["id"])).scalars().first()
            c.execute(update(attempts).where(attempts.c.id == aid).values(status="FAILED"))
            before = {table.name: c.execute(select(table)).mappings().all() for table in meta.sorted_tables}
            with pytest.raises(DomainError):
                verified_candidate(store, c, job, gate._limits(b.contract))
            after = {table.name: c.execute(select(table)).mappings().all() for table in meta.sorted_tables}
            assert before == after
        transaction.rollback()
    assert snapshot(store) == baseline
    observed.append(dict(case="same-read-segment-then-write-invalidates", refused=True,
                         all_55_tables_unchanged_in_window=True))
    with store.tx() as c:
        original = c.execute(select(attempts).where(attempts.c.run_id == t["generation"]))
        original = dict(original.mappings().first())
    for kind in ("only-accounting", "mixed-backend", "canonical", "raw", "aid", "scope"):
        with store.tx() as c:
            transaction = c.begin_nested()
            if kind == "only-accounting":
                c.execute(update(attempts).where(attempts.c.id == original["id"]).values(status="FAILED"))
            elif kind == "mixed-backend":
                params = copy.deepcopy(original["parameters"])
                params["pa_trial_binding"]["version"] = "pa-trial-dispatch.v1"
                c.execute(update(attempts).where(attempts.c.id == original["id"]).values(parameters=params))
            else:
                row = c.execute(select(rows).where(rows.c.app_id == t["generation"],
                    rows.c.request_key == original["id"], rows.c.kind == bridge.RESPONSE)).mappings().one()
                changed = copy.deepcopy(row["snapshot"])
                field = dict(canonical="canonical_sha256", raw="sha256", aid="attempt_id", scope="runtime_id")[kind]
                changed["response"][field] = "0" * 64 if kind in ("canonical", "raw") else "changed-owned-field"
                c.execute(update(rows).where(rows.c.app_id == row["app_id"], rows.c.request_key == row["request_key"],
                    rows.c.kind.in_([bridge.RESPONSE, bridge.RESPONSE + "_seal"])).values(
                        snapshot=changed, fingerprint=fingerprint(changed),
                        request_fingerprint=fingerprint(changed["request"])))
            before = {table.name: c.execute(select(table)).mappings().all()
                      for table in meta.sorted_tables}
            with pytest.raises(DomainError):
                bridge.journal_stage_accounted(store, c, data[3], b.contract, b.approval_key,
                                               t["generation"], "generate")
            after = {table.name: c.execute(select(table)).mappings().all()
                     for table in meta.sorted_tables}
            assert before == after
            transaction.rollback()
        assert snapshot(store) == baseline
        observed.append(dict(case=kind, refused=True, all_55_tables_unchanged_in_window=True))
    write(t["out"] / "fresh-proof-rejections.json", dict(cases=observed,
        new_model_requests=0, source="THIS_ROUND_ACTUAL_PREFIX_ONLY", clones_or_old_db_used=False))


def test_known_accounting_cannot_accept_wrong_original_business_schema(env, tmp_path):
    data, b = prepare(env, tmp_path)
    rid = enqueue_generation(data, b)
    sent = []
    raw = apps.wire(dict(role="assistant", content="generic protocol, wrong original first step"), "stop")

    def handler(request):
        sent.append(request.content)
        return httpx.Response(200, json=raw)

    worker = Worker(data[0], data[1], pa_trial=b, goal_planner_transport=httpx.MockTransport(handler))
    assert worker.once() and not worker.once()
    account = journal.read(data[0], data[3], b.contract, b.approval_key, b.account_id)
    assert len(sent) == len(account.ledger.slots) == 1
    assert account.ledger.slots[0].accepted and account.ledger.slots[0].settlement.total_tokens == 1000
    result = data[2].get("/api/runs/" + rid)
    assert result.json()["status"] == "FAILED" and result.json()["result"] is None, result.text
    with data[0].tx() as c, pytest.raises(DomainError):
        gate._generation_accounted(data[0], c, data[3], b.contract, b.approval_key, rid)
    write(tmp_path / "business-schema-rejected.json", dict(run=result.json(),
        accounting=account.model_dump(mode="json"), actual_handler_calls=len(sent), no_resend=True))
    data[2].close()


def test_original_controller_store_is_fixed_through_late_body_and_failure(env, tmp_path):
    data, b = prepare(env, tmp_path)
    rid = enqueue_generation(data, b)
    foreign = Store(data[1].database_url, test_only=False)
    sql = []
    event.listen(foreign.engine, "before_cursor_execute", lambda *args: sql.append("SQL"))
    sent, refused = [], []
    worker = None

    def handler(request):
        sent.append(request.content)
        try:
            worker.store = foreign
        except DomainError as error:
            refused.append(error.code)
        return httpx.Response(200, json=first_response(data))

    worker = Worker(data[0], data[1], pa_trial=b, goal_planner_transport=httpx.MockTransport(handler))
    assert worker.once() and not worker.once()
    assert worker.store is data[0] and refused == ["VERSION_CONFLICT"] and sql == []
    account = journal.read(data[0], data[3], b.contract, b.approval_key, b.account_id)
    assert len(sent) == len(account.ledger.slots) == 1
    with data[0].tx() as c:
        a = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().one()
        assert a["usage"]["status"] == "known" and a["usage"]["tokens"]["total_tokens"] == 1000
        assert a["status"] == "FAILED"
        capture = sender._captured(c, data[3], account.ledger.slots[0].identity)
        assert capture.raw_bytes > 0 and capture.outcome.total_tokens == 1000
    result = data[2].get("/api/runs/" + rid)
    assert result.json()["status"] == "FAILED" and result.json()["result"] is None, result.text
    write(tmp_path / "late-store-refused.json", dict(run=result.json(),
        accounting=account.model_dump(mode="json"), original_attempt=dict(a),
        capture=capture.model_dump(mode="json"), foreign_engine_sql=len(sql), refused=refused,
        actual_handler_calls=len(sent), original_store_held=True, no_resend=True))
    foreign.engine.dispose()
    data[2].close()
