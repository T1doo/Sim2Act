"""Coordinator-only synthetic proof. No software qualification or bound Worker run.

Positive tests replace only literal qualification, and stage tests explicitly
replace app enqueue/lineage with finite synthetic dependencies. Real approval,
transaction, original-key, claim, scope and rollback code remain under test.
"""

import copy
import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import delete, insert, select, update
from test_natural_trial_preparation import consent, prepared_data, scope  # noqa: F401

from sim2act import natural_live_admission as gate
from sim2act import natural_trial_runs as service
from sim2act import production_trial_admission as production
from sim2act.db import (
    attempts,
    delivery_graph_requests,
    grants,
    internal_instances,
    meta,
    new_id,
    runs,
)
from sim2act.errors import DomainError
from sim2act.pa_trial_dispatch import PATrialBinding
from sim2act.worker import Worker


@pytest.fixture
def controller(prepared_data):  # noqa: F811
    data, _, base, receipt = scope(prepared_data)
    assert data[2].post(base + "/consent", json=consent(receipt)).status_code == 200
    contract = gate.parse_contract(receipt["contract"])
    binding = PATrialBinding(contract, contract.stage_keys.generate + "_approval")
    return data, binding, base, receipt


@pytest.fixture
def synthetic(controller, monkeypatch):
    monkeypatch.setattr(production, "_qualified", lambda: None)
    return controller


def snapshot(store):
    with store.tx() as c:
        return {
            table.name: [dict(row) for row in c.execute(select(table)).mappings()]
            for table in meta.sorted_tables
        }


def accepted(synthetic):
    data, binding, _, _ = synthetic
    receipt = service.submit_generate(data[0], data[3], binding)
    return data, binding, receipt


def test_actual_strict_qualification_refusal_is_atomic(controller, tmp_path):
    data, binding, _, _ = controller
    before = snapshot(data[0])
    with pytest.raises(DomainError) as error:
        service.submit_generate(data[0], data[3], binding)
    assert error.value.code == "VERSION_CONFLICT"
    assert error.value.message == "Current software differs from the exact reviewed literal target"
    assert snapshot(data[0]) == before
    (tmp_path / "STRICT_REFUSAL.json").write_text(
        json.dumps(
            dict(
                code=error.value.code,
                message=error.value.message,
                database_unchanged=True,
                actual_model_requests=0,
            )
        )
    )


def test_generate_duplicate_concurrent_original_key_and_recovery(synthetic, tmp_path):
    data, binding, _, _ = synthetic
    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = list(
            pool.map(lambda _: service.submit_generate(data[0], data[3], binding), range(2))
        )
    assert receipts[0] == receipts[1]
    before = snapshot(data[0])
    assert service.recover(data[0], data[3], binding, "generate") == receipts[0]
    assert service.submit_generate(data[0], data[3], binding) == receipts[0]
    assert snapshot(data[0]) == before
    with data[0].tx() as c:
        jobs = c.execute(select(runs)).mappings().all()
        assert len(jobs) == 1 and jobs[0]["fence"] == 0 and jobs[0]["status"] == "QUEUED"
        assert not c.execute(select(attempts)).first()
        paired = c.execute(
            select(delivery_graph_requests).where(
                delivery_graph_requests.c.kind.in_(
                    [service.ASSOCIATION, service.ASSOCIATION + "_seal"]
                )
            )
        ).all()
        assert len(paired) == 4
    (tmp_path / "ATOMIC_RECEIPTS.json").write_text(json.dumps(receipts))


@pytest.mark.parametrize("fault", ["first_pair", "second_pair", "event", "late"])
def test_failed_acceptance_rolls_back_complete_run_and_both_pairs(synthetic, monkeypatch, fault):
    data, binding, _, _ = synthetic
    store = data[0]
    before = snapshot(store)
    original_save, original_event = gate._save, store.event

    def save(*args):
        original_save(*args)
        if args[3] == service.ASSOCIATION:
            is_run = args[2].startswith("run_")
            if (fault == "first_pair" and is_run) or (fault == "second_pair" and not is_run):
                raise DomainError("VERSION_CONFLICT", "Synthetic write failure")

    def event(*args):
        original_event(*args)
        if args[2] == "NATURAL_TRIAL_ASSOCIATED":
            if fault == "event":
                raise DomainError("VERSION_CONFLICT")
            if fault == "late":
                monkeypatch.setattr(time, "time", lambda: binding.contract.expires_at)

    monkeypatch.setattr(gate, "_save", save)
    monkeypatch.setattr(store, "event", event)
    with pytest.raises(DomainError):
        service.submit_generate(store, data[3], binding)
    assert snapshot(store) == before


def test_unbound_worker_cannot_claim_process_or_reserve(synthetic):
    data, binding, receipt = accepted(synthetic)
    before = snapshot(data[0])
    assert data[0].claim("ordinary", 30) is None
    with data[0].tx() as c:
        job = dict(c.execute(select(runs).where(runs.c.id == receipt["run_id"])).mappings().one())
    worker = Worker(data[0], data[1])
    for call in (
        lambda: worker.process(job),
        lambda: worker.reserve(job["id"], job["fence"], dict(job["context"])),
    ):
        with pytest.raises(DomainError):
            call()
    assert snapshot(data[0]) == before
    # A trial at the queue head does not block unrelated ordinary work.
    ordinary = data[0].submit(data[3], data[4], "unrelated", [], "unrelated-original-key")
    assert data[0].claim("ordinary", 30)["id"] == ordinary
    assert data[0].claim("ordinary", 30) is None


@pytest.mark.parametrize(
    "damage", ["marker", "run_seal", "trial_seal", "cancel", "revoke", "resource", "goal", "expiry"]
)
def test_damaged_or_stopped_association_never_claims(synthetic, monkeypatch, damage):
    data, binding, receipt = accepted(synthetic)
    store, client, user = data[0], data[2], data[3]
    if damage == "goal":
        card = data[6]
        changed = copy.deepcopy(card["content"])
        changed["goal"] += " changed"
        assert (
            client.put(
                "/api/goal-cards/" + card["id"],
                json=dict(changed, expected_version=card["version"]),
            ).status_code
            == 200
        )
    elif damage == "revoke":
        gate.revoke(
            store,
            user,
            binding.contract,
            gate.RevokeInput(
                expected_contract_fingerprint=binding.contract_fingerprint,
                request_key="withdraw",
                consent="REVOKE_ONLY_THIS_EXACT_NATURAL_TRIAL",
            ),
        )
    elif damage == "expiry":
        monkeypatch.setattr(time, "time", lambda: binding.contract.expires_at)
    else:
        with store.tx() as c:
            if damage == "marker":
                row = c.execute(select(runs).where(runs.c.id == receipt["run_id"])).mappings().one()
                context = dict(row["context"])
                context.pop(service.MARKER)
                c.execute(
                    update(runs).where(runs.c.id == receipt["run_id"]).values(context=context)
                )
            elif damage.endswith("seal"):
                eid = receipt["run_id"] if damage == "run_seal" else gate.entity(binding.contract)
                c.execute(
                    delete(delivery_graph_requests).where(
                        delivery_graph_requests.c.app_id == eid,
                        delivery_graph_requests.c.kind == service.ASSOCIATION + "_seal",
                    )
                )
            elif damage == "cancel":
                c.execute(
                    update(runs).where(runs.c.id == receipt["run_id"]).values(cancel_intent=True)
                )
            elif damage == "resource":
                c.execute(
                    update(grants).where(grants.c.resource_id == data[5]).values(revoked=True)
                )
    before = snapshot(store)
    assert store.claim("ordinary", 30) is None
    assert store.claim("synthetic-bound-claim", 30, trial_binding=binding) is None
    assert snapshot(store) == before
    if damage in ("goal", "expiry", "revoke"):
        assert service.recover(store, user, binding, "generate") == receipt
        assert snapshot(store) == before


def test_real_qualification_drift_after_synthetic_acceptance_blocks_claim(synthetic, monkeypatch):
    data, binding, receipt = accepted(synthetic)
    monkeypatch.undo()  # Restore literal software qualification, including fixture HTTP guards.
    before = snapshot(data[0])
    assert data[0].claim("bound", 30, trial_binding=binding) is None
    assert snapshot(data[0]) == before


def test_other_identity_key_and_changed_approval_cannot_recover(synthetic):
    data, binding, receipt = accepted(synthetic)
    other = data[0].user("other synthetic", "other synthetic token")
    before = snapshot(data[0])
    with pytest.raises(DomainError):
        service.recover(data[0], other, binding, "generate")
    wrong = PATrialBinding(binding.contract, "other-approval")
    for call in (
        lambda: service.recover(data[0], data[3], wrong, "generate"),
        lambda: service.submit_generate(data[0], data[3], wrong),
        lambda: service.recover(data[0], data[3], binding, "source"),
    ):
        with pytest.raises(DomainError):
            call()
    assert snapshot(data[0]) == before


def synthetic_stage(synthetic, monkeypatch, stage="source"):
    """Explicit finite stand-ins: NOT a real app lineage/full closure proof."""
    from sim2act import app_jobs

    data, binding, _, _ = synthetic
    store, user, contract = data[0], data[3], binding.contract
    iid = new_id("iinstance")
    with store.tx() as c:
        c.execute(
            insert(internal_instances).values(
                id=iid,
                project_id=contract.project_id,
                principal_id=user,
                source_app_id="synthetic-app",
                runtime_id=contract.runtime_id,
                release_id="synthetic-release",
                revision=1,
                data_version=0,
                history=[],
            )
        )

    def enqueue(store, user, iid, revision, release_fp, input_value, key, limits, **kwargs):
        assert kwargs["logic_tx"].in_transaction()
        rid = store.submit_tx(
            kwargs["logic_tx"], user, contract.project_id, "synthetic stage", [], key
        )
        return dict(run_id=rid, cached=False)

    def authority(store, c, user, contract, stage, rid):
        job = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
        previous = "run_" + "a" * 32
        return gate.StageAuthorityV2(
            contract_fingerprint=binding.contract_fingerprint,
            stage=stage,
            run_id=rid,
            accepted_fingerprint=job["fingerprint"],
            app_run_id="synthetic-app-run",
            instance_id=iid,
            instance_revision=1,
            runtime_id=contract.runtime_id,
            app_id="synthetic-app",
            candidate_fingerprint="a" * 64,
            recipe_fingerprint="b" * 64,
            release_id="synthetic-release",
            release_fingerprint="c" * 64,
            generation_run_id=previous,
            generation_candidate_fingerprint="d" * 64,
            target_goal_fingerprint=contract.bindings[0].goal_fingerprint,
            authorization_fingerprint=contract.authorization_fingerprint,
            predecessor_run_id=previous,
            predecessor_created_at=contract.prepared_at,
            stage_approval_expires_at=contract.prepared_at + 900,
        ), job

    monkeypatch.setattr(app_jobs, "enqueue", enqueue)
    monkeypatch.setattr(gate, "_stage_current", authority)
    pa_use = None
    if stage == "cold":
        from sim2act.pb_natural_uses import PA_CONSENT, PACommitInput, ReviewInput

        target = contract.bindings[1]
        pa_use = PACommitInput(
            review=ReviewInput(
                expected_revision=1,
                expected_release_fingerprint="c" * 64,
                expected_app_fingerprint="a" * 64,
                expected_recipe_fingerprint="b" * 64,
                resource_id=target.resource_id,
                card_id=target.card_id,
                expected_goal_version=target.goal_version,
                expected_goal_fingerprint=target.goal_fingerprint,
                expected_source_hash=target.source_hash,
                request_key=contract.stage_keys.cold,
            ),
            expected_review_fingerprint="d" * 64,
            consent=PA_CONSENT,
        )
    return service.StageInput(
        instance_id=iid, expected_revision=1, expected_release_fingerprint="c" * 64, pa_use=pa_use
    ), authority


@pytest.mark.parametrize("stage", ["source", "cold"])
def test_unapproved_stage_stays_queued_until_exact_phase_and_after_handoff(
    synthetic, monkeypatch, tmp_path, stage
):
    data, binding, _, _ = synthetic
    body, authority = synthetic_stage(synthetic, monkeypatch, stage)
    store, user = data[0], data[3]
    monkeypatch.setattr(time, "time", lambda: binding.contract.prepared_at + 850)
    receipt = service.submit_stage(store, user, binding, stage, body)
    assert service.submit_stage(store, user, binding, stage, body) == receipt
    before = snapshot(store)
    assert store.claim("ordinary", 30) is None
    assert store.claim("bound", 30, trial_binding=binding) is None
    assert snapshot(store) == before
    with store.tx() as c:
        auth, _ = authority(store, c, user, binding.contract, stage, receipt["run_id"])
    approval = gate.StageApproveInput(
        authority=auth,
        expected_authority_fingerprint=service.fingerprint(auth.model_dump()),
        approval_key=binding.approval_key,
        request_key="phase-" + stage,
        consent="BIND_ONLY_THIS_ACCEPTED_STAGE_RUN_APP_RELEASE_AND_COMPLETE_GOAL_TO_ORIGINAL_TRIAL",
    )
    assert gate.approve_stage(store, user, binding.contract, approval)["live_allowed"] is False
    # Approved immediately before handoff, then claim after handoff: execution
    # deadline remains, but approval review time is not reused as a dispatch TTL.
    monkeypatch.setattr(time, "time", lambda: binding.contract.prepared_at + 901)
    claimed = store.claim("bound", 30, trial_binding=binding)
    assert claimed["id"] == receipt["run_id"] and claimed["fence"] == 1
    with store.tx() as c:
        service.check_claim(store, c, claimed["id"], binding)
    assert service.recover(store, user, binding, stage) == receipt
    (tmp_path / "STAGE.json").write_text(
        json.dumps(
            dict(
                stage=stage,
                receipt=receipt,
                synthetic_lineage=True,
                phase=approval.model_dump(),
                claimed_id=claimed["id"],
            )
        )
    )


def test_changed_stage_input_and_late_lineage_roll_back(synthetic, monkeypatch):
    data, binding, _, _ = synthetic
    body, authority = synthetic_stage(synthetic, monkeypatch)
    before = snapshot(data[0])
    calls = []

    def drifting(*args):
        result = authority(*args)
        calls.append(1)
        if len(calls) > 1:
            return result[0].model_copy(update={"instance_revision": 2}), result[1]
        return result

    monkeypatch.setattr(gate, "_stage_current", drifting)
    with pytest.raises(DomainError):
        service.submit_stage(data[0], data[3], binding, "source", body)
    assert snapshot(data[0]) == before
    monkeypatch.setattr(gate, "_stage_current", authority)
    service.submit_stage(data[0], data[3], binding, "source", body)
    before = snapshot(data[0])
    with pytest.raises(DomainError):
        service.submit_stage(
            data[0], data[3], binding, "source", body.model_copy(update={"expected_revision": 2})
        )
    assert snapshot(data[0]) == before


def test_bound_claim_skips_earlier_ordinary_run_and_keeps_it_queued(synthetic):
    data, binding, _, _ = synthetic
    ordinary = data[0].submit(data[3], data[4], "earlier ordinary", [], "earlier-ordinary")
    receipt = service.submit_generate(data[0], data[3], binding)
    claimed = data[0].claim("synthetic-bound-claim", 30, trial_binding=binding)
    assert claimed["id"] == receipt["run_id"]
    with data[0].tx() as c:
        job = c.execute(select(runs).where(runs.c.id == ordinary)).mappings().one()
        assert job["status"] == "QUEUED" and job["fence"] == 0 and job["lease_until"] == 0
    assert data[0].claim("ordinary", 30)["id"] == ordinary


@pytest.mark.parametrize("offset", [299.999, 300])
def test_original_run_deadline_claim_boundary(synthetic, monkeypatch, offset):
    data, binding, receipt = accepted(synthetic)
    with data[0].tx() as c:
        created = c.execute(
            select(runs.c.created_at).where(runs.c.id == receipt["run_id"])
        ).scalar_one()
    monkeypatch.setattr(time, "time", lambda: created + offset)
    before = snapshot(data[0])
    claimed = data[0].claim("synthetic-bound-claim", 30, trial_binding=binding)
    if offset == 300:
        assert claimed is None and snapshot(data[0]) == before
    else:
        assert claimed["id"] == receipt["run_id"]


def test_original_ordinary_key_cannot_be_adopted(synthetic):
    data, binding, _, _ = synthetic
    data[0].submit(data[3], data[4], "ordinary exact key", [], binding.contract.stage_keys.generate)
    before = snapshot(data[0])
    with pytest.raises(DomainError):
        service.submit_generate(data[0], data[3], binding)
    assert snapshot(data[0]) == before


@pytest.mark.parametrize("fault", ["binding_removed", "pair_changed", "late_write"])
def test_final_write_rechecks_association_in_same_transaction_and_rolls_back(
    synthetic, monkeypatch, fault
):

    from sim2act import pa_trial_dispatch as dispatch

    data, binding, receipt = accepted(synthetic)
    claimed = data[0].claim("synthetic-bound-claim", 30, trial_binding=binding)
    worker = Worker(data[0], data[1])
    # This is only a final-write boundary test: no validated bound Worker,
    # account, provider or successful graph is asserted.
    worker.pa_trial = binding
    monkeypatch.setattr(
        dispatch,
        "_binding",
        lambda w: (
            w.pa_trial if w.pa_trial else (_ for _ in ()).throw(DomainError("VERSION_CONFLICT"))
        ),
    )
    monkeypatch.setattr(dispatch, "_account", lambda *args: None)
    monkeypatch.setattr(dispatch, "check_commit", lambda *args: None)
    before = snapshot(data[0])
    original = data[0].event

    def event(c, rid, kind, payload):
        original(c, rid, kind, payload)
        if kind == "STATE":
            if fault == "binding_removed":
                worker.pa_trial = None
            elif fault == "pair_changed":
                c.execute(
                    delete(delivery_graph_requests).where(
                        delivery_graph_requests.c.app_id == rid,
                        delivery_graph_requests.c.kind == service.ASSOCIATION + "_seal",
                    )
                )
            elif fault == "late_write":
                monkeypatch.setattr(time, "time", lambda: claimed["created_at"] + 300)

    monkeypatch.setattr(data[0], "event", event)
    with pytest.raises(DomainError):
        worker.finish(claimed["id"], claimed["fence"], "PARTIAL")
    assert snapshot(data[0]) == before


@pytest.mark.parametrize("where", ["last_proof", "last_scope", "claim_write", "created_tamper"])
def test_claim_proof_or_write_cannot_cross_or_extend_original_deadline(
    synthetic, monkeypatch, where
):
    from sim2act import goal_applications

    data, binding, receipt = accepted(synthetic)
    store = data[0]
    with store.tx() as c:
        created = c.execute(
            select(runs.c.created_at).where(runs.c.id == receipt["run_id"])
        ).scalar_one()
    before = snapshot(store)
    original_scope = service._scope
    calls = []

    def scope(*args, **kwargs):
        result = original_scope(*args, **kwargs)
        calls.append(1)
        if where == "last_proof" and len(calls) == 2:
            monkeypatch.setattr(time, "time", lambda: created + 300)
        return result

    monkeypatch.setattr(service, "_scope", scope)
    original_gate = goal_applications.source_scope_gate
    reads = []

    def gate_after(*args):
        result = original_gate(*args)
        reads.append(1)
        if where == "last_scope" and len(reads) == 4:
            monkeypatch.setattr(time, "time", lambda: created + 300)
        return result

    monkeypatch.setattr(goal_applications, "source_scope_gate", gate_after)
    original_event = store.event

    def event(*args):
        original_event(*args)
        if where == "claim_write" and args[2] == "CLAIMED":
            monkeypatch.setattr(time, "time", lambda: created + 300)

    monkeypatch.setattr(store, "event", event)
    if where == "created_tamper":
        with store.tx() as c:
            c.execute(
                update(runs).where(runs.c.id == receipt["run_id"]).values(created_at=created + 1)
            )
        before = snapshot(store)
    if where == "claim_write":
        with pytest.raises(DomainError):
            store.claim("bound", 30, trial_binding=binding)
    else:
        assert store.claim("bound", 30, trial_binding=binding) is None
    assert snapshot(store) == before


@pytest.mark.parametrize("stage,late_call", [("generate", 2), ("source", 3)])
def test_final_qualification_crossing_expiry_cannot_commit(
    synthetic, monkeypatch, stage, late_call
):
    data, binding, _, _ = synthetic
    calls = []
    body = None
    if stage == "source":
        body, _ = synthetic_stage(synthetic, monkeypatch)
    before = snapshot(data[0])

    def qualified():
        calls.append(1)
        if len(calls) == late_call:
            monkeypatch.setattr(time, "time", lambda: binding.contract.expires_at)

    monkeypatch.setattr(production, "_qualified", qualified)
    with pytest.raises(DomainError):
        if stage == "generate":
            service.submit_generate(data[0], data[3], binding)
        else:
            service.submit_stage(data[0], data[3], binding, stage, body)
    assert snapshot(data[0]) == before
