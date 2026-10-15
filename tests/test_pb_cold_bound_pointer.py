"""SQLite metadata boundary tests; the original seven-slot test proves full P-B lineage.

The supplied verified row here is synthetic. These tests exercise the narrow
post-bound pointer/approval/read-segment checks, not a source or LIVE proof.
"""
import copy
import time
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, insert, select, update

from sim2act import lifecycle, natural_specs
from sim2act import natural_live_admission as gate
from sim2act.db import (
    fingerprint,
    internal_approvals,
    internal_instances,
    internal_releases,
    new_id,
)
from sim2act.errors import DomainError


@pytest.fixture
def pointer(env):
    store, _, _, user, other, project, _ = env
    with store.tx() as c:
        runtime = store.own_project(c, user, project)["runtime_id"]
        aid, rid, approval, iid = (new_id(k) for k in ("app", "release", "approval", "instance"))
        body = {"draft": {"id": aid, "runtime_id": runtime}, "metadata_boundary_fixture": True}
        payload = {"snapshot": body}
        c.execute(insert(internal_approvals).values(id=approval, principal_id=user,
            project_id=project, kind="release", payload=payload, fingerprint=fingerprint(payload),
            expires_at=time.time() + 1200, consumed=True))
        c.execute(insert(internal_releases).values(id=rid, principal_id=user,
            project_id=project, approval_id=approval, snapshot=body, fingerprint=fingerprint(body)))
        c.execute(insert(internal_instances).values(id=iid, principal_id=user,
            project_id=project, source_app_id=aid, runtime_id=runtime, release_id=rid,
            revision=1, data_version=0, history=[]))
        verified = copy.deepcopy(dict(c.execute(select(internal_releases).where(
            internal_releases.c.id == rid)).mappings().one()))
    return store, user, other, project, {"project_id": project, "runtime_id": runtime}, {"instance_id": iid}, verified


def rows(c):
    return {t.name: [dict(r) for r in c.execute(select(t).order_by(t.c.id)).mappings()]
            for t in (internal_instances, internal_releases, internal_approvals)}


def test_current_pointer_read_is_immutable_and_does_not_repeat_lineage(pointer, monkeypatch):
    store, user, _, project, job, snapshot, verified = pointer
    def no_second_proof(*args, **kwargs):
        raise AssertionError("Full lineage must already have been proved by bound")
    monkeypatch.setattr(lifecycle, "read_release", no_second_proof)
    with store.tx() as c:
        epoch = c.info.get("source_proof_write_epoch", 0)
        before = rows(c)
        inst, current = gate._stage_instance_after_bound(
            store, c, user, project, job, snapshot, verified, epoch)
        assert inst["revision"] == 1 and dict(current) == verified
        assert rows(c) == before and c.info.get("source_proof_write_epoch", 0) == epoch


@pytest.mark.parametrize("fault", ["missing", "foreign", "project", "source_app", "runtime",
    "release", "revision", "release_fingerprint", "release_snapshot", "release_owner",
    "release_project", "release_approval", "approval_unconsumed",
    "approval_payload", "write_before_pointer", "write_during_pointer"])
def test_pointer_drift_or_write_never_reuses_verified_release(pointer, monkeypatch, fault):
    store, user, other, project, job, snapshot, verified = pointer
    with store.tx() as c:
        iq = update(internal_instances).where(internal_instances.c.id == snapshot["instance_id"])
        rq = update(internal_releases).where(internal_releases.c.id == verified["id"])
        aq = update(internal_approvals).where(internal_approvals.c.id == verified["approval_id"])
        if fault == "missing":
            c.execute(delete(internal_instances).where(internal_instances.c.id == snapshot["instance_id"]))
        elif fault == "foreign":
            c.execute(iq.values(principal_id=other))
        elif fault in ("project", "source_app", "runtime", "release", "revision"):
            key = {"project": "project_id", "source_app": "source_app_id", "runtime": "runtime_id",
                   "release": "release_id", "revision": "revision"}[fault]
            c.execute(iq.values(**{key: 0 if fault == "revision" else "changed-pointer"}))
        elif fault == "release_fingerprint":
            c.execute(rq.values(fingerprint="f" * 64))
        elif fault in ("release_owner", "release_project", "release_approval"):
            key = {"release_owner": "principal_id", "release_project": "project_id",
                   "release_approval": "approval_id"}[fault]
            c.execute(rq.values(**{key: other if fault == "release_owner" else "changed-pointer"}))
        elif fault == "release_snapshot":
            body = {**verified["snapshot"], "changed": True}
            payload = {"snapshot": body}
            c.execute(rq.values(snapshot=body, fingerprint=fingerprint(body)))
            c.execute(aq.values(payload=payload, fingerprint=fingerprint(payload)))
        elif fault == "approval_unconsumed":
            c.execute(aq.values(consumed=False))
        elif fault == "approval_payload":
            c.execute(aq.values(payload={"snapshot": {}}, fingerprint=fingerprint({"snapshot": {}})))
        # For metadata faults use the current epoch, so the fresh pointer and
        # approval checks themselves must reject; only the write cases test epoch.
        epoch = c.info.get("source_proof_write_epoch", 0)
        if fault == "write_before_pointer":
            c.execute(iq.values(revision=1))
        elif fault == "write_during_pointer":
            original = lifecycle.immutable_release_pointer
            def change_after_approval(connection, principal, release):
                original(connection, principal, release)
                connection.execute(iq.values(revision=1))
            monkeypatch.setattr(lifecycle, "immutable_release_pointer", change_after_approval)
        if fault in ("missing", "foreign"):
            def no_foreign_body(*args, **kwargs):
                raise AssertionError("Foreign Release body must not be read")
            monkeypatch.setattr(lifecycle, "owned_release_pointer", no_foreign_body)
        before = rows(c)
        with pytest.raises(DomainError) as failure:
            gate._stage_instance_after_bound(store, c, user, project, job, snapshot, verified, epoch)
        assert failure.value.code == ("PERMISSION_DENIED" if fault in (
            "missing", "foreign", "release_owner", "release_project") else "VERSION_CONFLICT")
        assert rows(c) == before


def test_sqlalchemy_autobegin_without_sqlite_transaction_cannot_reuse(pointer):
    store, user, _, project, job, snapshot, verified = pointer
    with store.engine.connect() as c:
        c.execute(select(internal_instances.c.id))
        assert c.in_transaction() and not c.connection.driver_connection.in_transaction
        with pytest.raises(DomainError):
            gate._stage_instance_after_bound(store, c, user, project, job, snapshot, verified,
                c.info.get("source_proof_write_epoch", 0))


@pytest.mark.parametrize("branch", ["ordinary", "pa", "source", "production", "other_database",
    "human_correction", "logic_check", "pb_use", "pa_use", "natural_logic_source", "not_extracted"])
def test_complete_bound_precedes_reuse_and_all_other_branches_keep_full_instance(monkeypatch, branch):
    """Isolated dispatch test: stop at the chosen verifier, never return source authority."""
    from sim2act import pa_spec_apps
    seen = []
    class SelectedVerifier(Exception):
        pass
    def reuse(*args, **kwargs):
        seen.append("reuse")
        raise SelectedVerifier
    def full(*args, **kwargs):
        seen.append("full")
        raise SelectedVerifier
    snapshot = {"instance_id": "synthetic-instance"}
    if branch in ("human_correction", "logic_check", "pb_use", "pa_use"):
        snapshot[branch] = {}
    candidate = {"namespace": natural_specs.VERSION, "spec_task": {}}
    if branch == "not_extracted":
        candidate.pop("spec_task")
    release = {"snapshot": {}}
    if branch == "natural_logic_source":
        release["snapshot"]["natural_logic_source"] = {}
    def bound(*args, **kwargs):
        seen.append("full-bound")
        return {"snapshot": snapshot, "draft": {"candidate": candidate}, "release": release}
    row = {"id": "synthetic-run", "project_id": "project", "principal_id": "user"}
    connection = SimpleNamespace(info={}, execute=lambda *a, **k: SimpleNamespace(
        mappings=lambda: SimpleNamespace(first=lambda: row)))
    store = SimpleNamespace(test_only=branch != "production", sqlite=branch != "other_database")
    # Constructed contracts and source stubs only select a verifier. Its sentinel
    # always raises before the remaining proof; no permit or success is fabricated.
    kind = gate.TrialContract if branch == "pa" else gate.PBTrialContract
    contract = kind.model_construct(project_id="project")
    monkeypatch.setattr(pa_spec_apps, "job_scope_gate", lambda *a, **k: True)
    monkeypatch.setattr(pa_spec_apps, "bound", bound)
    monkeypatch.setattr(gate, "_stage_instance_after_bound", reuse)
    monkeypatch.setattr(lifecycle, "instance", full)
    with pytest.raises(SelectedVerifier):
        gate._stage_current(store, connection, "user", contract,
            "source" if branch == "source" else "cold", "synthetic-run")
    assert seen == ["full-bound", "reuse" if branch == "ordinary" else "full"]


def test_positive_revision_drift_is_rejected_by_original_stage_approval(pointer, monkeypatch):
    """Isolated approval handoff using real current SQLite metadata, not full lineage."""
    store, user, _, project, job, snapshot, verified = pointer
    authority = gate.StageAuthority(contract_fingerprint="a" * 64, stage="cold", run_id="run_" + "1" * 32,
        accepted_fingerprint="b" * 64, app_run_id="synthetic-app-run", instance_id=snapshot["instance_id"],
        instance_revision=1, runtime_id=job["runtime_id"], app_id=verified["snapshot"]["draft"]["id"],
        candidate_fingerprint="c" * 64, recipe_fingerprint="d" * 64, release_id=verified["id"],
        release_fingerprint=verified["fingerprint"], generation_run_id="run_" + "2" * 32,
        generation_candidate_fingerprint="e" * 64, target_goal_fingerprint="f" * 64,
        authorization_fingerprint="0" * 64)
    accepted = gate.StageApproveInput(authority=authority,
        expected_authority_fingerprint=fingerprint(authority.model_dump()), approval_key="approve",
        request_key="cold-consent",
        consent="BIND_ONLY_THIS_ACCEPTED_STAGE_RUN_APP_RELEASE_AND_COMPLETE_GOAL_TO_ORIGINAL_TRIAL")
    monkeypatch.setattr(gate, "_approved", lambda *a, **k: None)
    monkeypatch.setattr(gate, "_keys", lambda *a, **k: {"cold"})
    monkeypatch.setattr(gate, "_saved", lambda *a, **k: accepted)
    with store.tx() as c:
        c.execute(update(internal_instances).where(internal_instances.c.id == snapshot["instance_id"]).values(revision=2))
        epoch = c.info.get("source_proof_write_epoch", 0)
        def fresh_phase(*args, **kwargs):
            inst, _ = gate._stage_instance_after_bound(store, c, user, project, job, snapshot, verified, epoch)
            return authority.model_copy(update={"instance_revision": inst["revision"]}), job
        monkeypatch.setattr(gate, "_stage_current", fresh_phase)
        before = rows(c)
        with pytest.raises(DomainError) as failure:
            gate.admit(store, c, user, gate.PBTrialContract.model_construct(
                principal_id=user, project_id=project, trial_key="metadata-trial"),
                "approve", "cold", authority.run_id, 1, 1)
        assert failure.value.code == "VERSION_CONFLICT" and rows(c) == before
