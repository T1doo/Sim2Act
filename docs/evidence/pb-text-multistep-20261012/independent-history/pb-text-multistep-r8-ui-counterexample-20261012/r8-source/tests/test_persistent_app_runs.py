"""Synthetic internal AppRun worker reliability, including real PG child processes."""

import hashlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from sqlalchemy import func, insert, select, update
from test_internal_lifecycle import create, limits, release

from sim2act import app_jobs as jobs
from sim2act.db import (
    Store,
    attempts,
    events,
    grants,
    internal_app_runs,
    internal_instance_data,
    internal_run_bindings,
    new_id,
    operations,
    principals,
    run_contracts,
    runs,
)
from sim2act.errors import DomainError
from sim2act.lifecycle import commit_switch, inspect_instance, prepare_switch
from sim2act.worker import Worker


class NoModel:
    def request(self, *_):
        raise AssertionError("Internal fixed AppRun must never call a model")


def setup(env):
    r, aid, fp = release(env)
    i = create(env, r)
    return r, i, aid, fp


def enqueue(env, i, r, key="queue", column="amount"):
    return jobs.enqueue(
        env[0],
        env[3],
        i["id"],
        i["revision"],
        r["fingerprint"],
        {"column": column},
        key,
        limits(env),
    )


def worker(env, store=None, seconds=30):
    return Worker(store or env[0], replace(env[1], lease_seconds=seconds), NoModel())


def row(env, jid):
    with env[0].tx() as c:
        return dict(c.execute(select(runs).where(runs.c.id == jid)).mappings().one())


def quantities(env):
    with env[0].tx() as c:
        return {
            t.name: c.execute(select(func.count()).select_from(t)).scalar_one()
            for t in [
                runs,
                internal_app_runs,
                internal_instance_data,
                operations,
                principals,
                grants,
                attempts,
            ]
        }


def test_atomic_enqueue_reopen_existing_worker_fresh_result_no_model_no_grants(env):
    r, i, _, _ = setup(env)
    before = quantities(env)
    accepted = enqueue(env, i, r)
    old = enqueue(env, i, r)
    assert old["run_id"] == accepted["run_id"] and old["cached"]
    cold = Store(env[1].database_url, test_only=True)
    if not env[0].sqlite:
        cold.engine = cold.engine.execution_options(**env[0].engine.get_execution_options())
    try:
        assert cold.inspect(env[3], accepted["run_id"])["status"] == "QUEUED"
        assert worker(env, cold).once()
        result = cold.inspect(env[3], accepted["run_id"])
        assert result["status"] == "SUCCEEDED" and result["result"]["sum"] == "4.00"
        assert result["result_version"] == 1 and result["release_id"] == r["id"]
        assert result["known_effects"][0]["run_id"] == accepted["app_run_id"]
        assert not worker(env, cold).once()
    finally:
        cold.engine.dispose()
    after = quantities(env)
    assert after["internal_instance_data"] == before["internal_instance_data"] + 1
    for name in ["principals", "grants", "attempts"]:
        assert after[name] == before[name]
    with env[0].tx() as c:
        assert (
            c.execute(
                select(internal_app_runs.c.status).where(
                    internal_app_runs.c.id == accepted["app_run_id"]
                )
            ).scalar_one()
            == "SUCCEEDED"
        )
        assert (
            c.execute(
                select(operations.c.status).where(operations.c.run_id == accepted["run_id"])
            ).scalar_one()
            == "VERIFIED"
        )


def test_enqueue_failure_rolls_back_run_contract_and_apprun(env, monkeypatch):
    r, i, _, _ = setup(env)
    before = quantities(env)
    original = env[0].event

    def fail(c, rid, kind, data=None):
        if kind == "ACCEPTED":
            raise RuntimeError("synthetic enqueue fault before commit")
        return original(c, rid, kind, data)

    monkeypatch.setattr(env[0], "event", fail)
    with pytest.raises(RuntimeError):
        enqueue(env, i, r)
    assert quantities(env) == before
    with env[0].tx() as c:
        assert c.execute(select(func.count()).select_from(internal_run_bindings)).scalar_one() == 0
        assert c.execute(select(func.count()).select_from(run_contracts)).scalar_one() == 0


@pytest.mark.parametrize("command", ["pause", "cancel"])
def test_queued_control_then_claim_dispatch_denied_and_apprun_mirrored(env, command):
    r, i, _, _ = setup(env)
    a = enqueue(env, i, r)
    assert env[0].command(env[3], a["run_id"], command, 1) == (
        "PAUSED" if command == "pause" else "CANCELLED"
    )
    assert not worker(env).once()
    result = env[0].inspect(env[3], a["run_id"])
    assert result["result_version"] is None and not result["known_effects"]
    with env[0].tx() as c:
        assert (
            c.execute(
                select(internal_app_runs.c.status).where(internal_app_runs.c.id == a["app_run_id"])
            ).scalar_one()
            == result["status"]
        )
    assert quantities(env)["operations"] == 0
    if command == "pause":
        assert env[0].command(env[3], a["run_id"], "resume", 2) == "QUEUED"
        assert worker(env).once()
        assert env[0].inspect(env[3], a["run_id"])["result_version"] == 1
    else:
        with pytest.raises(DomainError):
            env[0].command(env[3], a["run_id"], "resume", 2)


@pytest.mark.parametrize("command", ["pause", "cancel"])
def test_claimed_control_before_dispatch_no_operation(env, command):
    r, i, _, _ = setup(env)
    a = enqueue(env, i, r)
    w = worker(env)
    claimed = env[0].claim(w.id, 30)
    env[0].command(env[3], a["run_id"], command, 1)
    w.process(claimed)
    assert env[0].inspect(env[3], a["run_id"])["status"] == (
        "PAUSED" if command == "pause" else "CANCELLED"
    )
    assert quantities(env)["operations"] == 0 and quantities(env)["internal_instance_data"] == 0


@pytest.mark.parametrize("control", ["pause", "cancel", "revoke"])
def test_compute_outside_transaction_controls_and_current_gateway_before_append(
    env, monkeypatch, control
):
    r, i, _, _ = setup(env)
    a = enqueue(env, i, r)
    w = worker(env, seconds=1)
    entered, proceed = threading.Event(), threading.Event()
    original = jobs.compute

    def wait(plan):
        entered.set()
        assert proceed.wait(8), "bounded synthetic calculation wait"
        return original(plan)

    monkeypatch.setattr(jobs, "compute", wait)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(w.once)
        try:
            assert entered.wait(4)
            # Separate transaction succeeds while computation is blocked: no long DB lock.
            if control == "revoke":
                with env[0].tx() as c:
                    c.execute(
                        update(grants)
                        .where(grants.c.principal_id == i["runtime_id"])
                        .values(revoked=True)
                    )
            else:
                env[0].command(env[3], a["run_id"], control, 1)
            time.sleep(1.2)
            assert env[0].claim("competitor", 1) is None
            assert row(env, a["run_id"])["lease_until"] > time.time()
        finally:
            proceed.set()
        assert future.result(timeout=8)
    state = row(env, a["run_id"])["status"]
    assert (
        state == {"pause": "PAUSED", "cancel": "CANCELLED", "revoke": "WAITING_RESOURCE"}[control]
    )
    assert quantities(env)["internal_instance_data"] == 0
    if control == "revoke":
        assert row(env, a["run_id"])["error"]["code"] == "GRANT_REVOKED"
        with pytest.raises(DomainError):
            env[0].command(env[3], a["run_id"], "resume", row(env, a["run_id"])["version"])
        # Revocation must not prevent the owner stopping a waiting job.
        assert (
            env[0].command(env[3], a["run_id"], "cancel", row(env, a["run_id"])["version"])
            == "CANCELLED"
        )


@pytest.mark.parametrize("who", ["user", "project", "app"])
@pytest.mark.parametrize("expired", [False, True])
def test_current_grants_before_dispatch_wait_and_never_add_result(env, who, expired):
    r, i, _, _ = setup(env)
    a = enqueue(env, i, r)
    with env[0].tx() as c:
        identity = (
            env[3]
            if who == "user"
            else env[0].own_project(c, env[3], env[5])["runtime_id"]
            if who == "project"
            else i["runtime_id"]
        )
        c.execute(
            update(grants)
            .where(grants.c.principal_id == identity, grants.c.resource_id == env[6])
            .values(**({"expires_at": 0} if expired else {"revoked": True}))
        )
    assert worker(env).once()
    assert row(env, a["run_id"])["status"] == "WAITING_RESOURCE"
    assert quantities(env)["internal_instance_data"] == 0 and quantities(env)["operations"] == 0
    with pytest.raises(DomainError):
        env[0].inspect(env[3], a["run_id"])
    assert env[0].command(env[3], a["run_id"], "cancel", 2) == "CANCELLED"


def test_failed_input_and_successful_history_separate_new_runs(env):
    r, i, _, _ = setup(env)
    bad = enqueue(env, i, r, "bad", "missing")
    good = enqueue(env, i, r, "good")
    w = worker(env)
    assert w.once() and w.once() and not w.once()
    failed = env[0].inspect(env[3], bad["run_id"])
    success = env[0].inspect(env[3], good["run_id"])
    assert (
        failed["status"] == "FAILED"
        and failed["error"]["code"] == "INVALID_INPUT"
        and failed["result_version"] is None
    )
    assert success["status"] == "SUCCEEDED" and success["result_version"] == 1
    assert len(inspect_instance(env[0], env[3], i["id"], limits(env))["data"]) == 1


def test_two_instances_and_concurrent_idempotency_and_result_versions(env):
    r, i, _, _ = setup(env)
    other = create(env, r)
    with ThreadPoolExecutor(max_workers=2) as pool:
        accepted = list(pool.map(lambda _: enqueue(env, i, r, "same"), range(2)))
    assert accepted[0]["run_id"] == accepted[1]["run_id"]
    second = enqueue(env, i, r, "second")
    separate = enqueue(env, other, r, "same")
    with ThreadPoolExecutor(max_workers=3) as pool:
        assert all(pool.map(lambda _: worker(env).once(), range(3)))
    versions = sorted(
        env[0].inspect(env[3], x["run_id"])["result_version"] for x in [accepted[0], second]
    )
    assert versions == [1, 2] and env[0].inspect(env[3], separate["run_id"])["result_version"] == 1
    assert quantities(env)["internal_instance_data"] == 3
    with pytest.raises(DomainError):
        enqueue(env, i, r, "same", "count")
    with pytest.raises(DomainError):
        jobs.inspect_job(env[0], env[4], separate["run_id"])
    with pytest.raises(DomainError):
        jobs.command_job(env[0], env[4], separate["run_id"], "cancel", 1)


def test_expired_lease_old_worker_cannot_append_recovery_single_receipt(env):
    r, i, _, _ = setup(env)
    a = enqueue(env, i, r)
    old = worker(env)
    first = env[0].claim(old.id, 30)
    plan = jobs.prepare_dispatch(old, first)
    output = jobs.compute(plan)
    with env[0].tx() as c:
        c.execute(update(runs).where(runs.c.id == first["id"]).values(lease_until=0))
    replacement = worker(env)
    new = env[0].claim(replacement.id, 30)
    assert new["fence"] > first["fence"]
    with pytest.raises(DomainError, match="Stale"):
        jobs.commit_result(old, first, plan, output)
    replacement.process(new)
    assert env[0].inspect(env[3], a["run_id"])["result_version"] == 1
    jobs.fail_job(old, first, DomainError("VERIFICATION_FAILED"))
    assert row(env, a["run_id"])["status"] == "SUCCEEDED"
    assert quantities(env)["operations"] == 1 and quantities(env)["internal_instance_data"] == 1
    with env[0].tx() as c:
        kinds = (
            c.execute(select(events.c.kind).where(events.c.run_id == first["id"])).scalars().all()
        )
        assert "WORKER_LOST" in kinds and "RECONCILED" in kinds


@pytest.mark.parametrize("tamper", ["binding", "contract", "input"])
def test_accepted_binding_or_contract_changes_fail_closed_no_model(env, tamper):
    r, i, _, _ = setup(env)
    a = enqueue(env, i, r)
    with env[0].tx() as c:
        if tamper == "binding":
            c.execute(
                update(internal_run_bindings)
                .where(internal_run_bindings.c.run_id == a["run_id"])
                .values(fingerprint="0" * 64)
            )
        elif tamper == "contract":
            c.execute(
                update(run_contracts)
                .where(run_contracts.c.run_id == a["run_id"])
                .values(fingerprint="0" * 64)
            )
        else:
            c.execute(
                update(internal_app_runs)
                .where(internal_app_runs.c.id == a["app_run_id"])
                .values(input={"column": "missing"})
            )
    assert worker(env).once()
    assert row(env, a["run_id"])["status"] == "FAILED"
    assert quantities(env)["internal_instance_data"] == 0
    with env[0].tx() as c:
        assert (
            c.execute(
                select(internal_app_runs.c.status).where(internal_app_runs.c.id == a["app_run_id"])
            ).scalar_one()
            == "FAILED"
        )


def test_accepted_release_pointer_change_rejected_not_rebound(env):
    r, i, aid, fp = setup(env)
    a = enqueue(env, i, r)
    target, _, _ = release(env, aid, fp)
    approval = prepare_switch(env[0], env[3], i["id"], target["id"], 1, limits(env))
    commit_switch(env[0], env[3], approval["id"], approval["fingerprint"], limits(env))
    assert worker(env).once()
    assert row(env, a["run_id"])["status"] == "FAILED"
    assert quantities(env)["internal_instance_data"] == 0
    with env[0].tx() as c:
        assert (
            c.execute(
                select(internal_app_runs.c.release_id).where(
                    internal_app_runs.c.id == a["app_run_id"]
                )
            ).scalar_one()
            == r["id"]
        )


@pytest.mark.parametrize("unknown", ["DISPATCHED", "OUTCOME_UNKNOWN", "RECEIPT_KNOWN"])
def test_other_unknown_operation_stops_dispatch_and_preserves_cancel_intent(env, unknown):
    r, i, _, _ = setup(env)
    a = enqueue(env, i, r)
    with env[0].tx() as c:
        c.execute(
            insert(operations).values(
                id=new_id("op"),
                run_id=a["run_id"],
                call_id="other_unknown",
                fingerprint="0" * 64,
                tool_ref="artifact.save_text",
                status=unknown,
            )
        )
    assert worker(env).once()
    assert row(env, a["run_id"])["status"] == "WAITING_RESOURCE"
    assert quantities(env)["internal_instance_data"] == 0 and quantities(env)["operations"] == 1
    with pytest.raises(DomainError, match="OUTCOME_UNKNOWN"):
        env[0].command(env[3], a["run_id"], "resume", 2)
    assert env[0].command(env[3], a["run_id"], "cancel", 2) == "RECONCILING"
    assert row(env, a["run_id"])["cancel_intent"]
    assert not worker(env).once()


def test_plan_source_rewrite_cannot_make_foreign_computed_result(env):
    r, i, _, _ = setup(env)
    enqueue(env, i, r)
    w = worker(env)
    claimed = env[0].claim(w.id, 30)
    plan = jobs.prepare_dispatch(w, claimed)
    plan["source"]["content"] = "amount\n99\n"
    plan["source"]["hash"] = hashlib.sha256(plan["source"]["content"].encode()).hexdigest()
    output = jobs.compute(plan)
    with pytest.raises(DomainError):
        jobs.commit_result(w, claimed, plan, output)
    assert quantities(env)["internal_instance_data"] == 0


@pytest.mark.parametrize("metadata", ["resource_id", "column", "source_hash"])
def test_output_source_metadata_forgery_rejected(env, metadata):
    r, i, _, _ = setup(env)
    enqueue(env, i, r)
    w = worker(env)
    claimed = env[0].claim(w.id, 30)
    plan = jobs.prepare_dispatch(w, claimed)
    output = jobs.compute(plan)
    output[metadata] = (
        "res_" + "0" * 32
        if metadata == "resource_id"
        else "other"
        if metadata == "column"
        else "0" * 64
    )
    with pytest.raises(DomainError):
        jobs.commit_result(w, claimed, plan, output)
    assert quantities(env)["internal_instance_data"] == 0


def child(env, runtime_role, fault, root):
    import os
    import subprocess
    import sys
    from pathlib import Path

    path = Path(__file__).parents[1]
    context = {
        "PATH": str(Path(sys.executable).parent),
        "PYTHONPATH": str(path / "src"),
        "SIM2ACT_SYNTHETIC_APP_URL": runtime_role,
        "SIM2ACT_SYNTHETIC_FAULT_DIR": str(root),
        "SIM2ACT_SYNTHETIC_FAULT": fault,
        "PYTHONUTF8": "1",
    }
    if os.name == "nt":
        context.update(
            {
                k: os.environ[k]
                for k in ("SystemRoot", "WINDIR", "COMSPEC", "TEMP", "TMP")
                if k in os.environ
            }
        )
    return subprocess.Popen(
        [sys.executable, str(path / "tests/fixtures/internal_app_worker.py")],
        cwd=path,
        env=context,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


@pytest.mark.parametrize("fault", ["before_commit", "after_commit"])
def test_real_pg_process_crash_reopen_recovers_without_duplicate_results(
    env, runtime_role, tmp_path, fault
):
    r, i, _, _ = setup(env)
    a = enqueue(env, i, r)
    p = child(env, runtime_role, fault, tmp_path)
    try:
        p.communicate(timeout=20)
        assert p.returncode == {"before_commit": 73, "after_commit": 74}[fault], (
            "Synthetic child fault did not reach expected window; values suppressed"
        )
        assert (tmp_path / "entered").exists()
        if fault == "before_commit":
            assert row(env, a["run_id"])["status"] == "RUNNING"
            assert quantities(env)["internal_instance_data"] == 0
            time.sleep(1.2)
        else:
            assert row(env, a["run_id"])["status"] == "SUCCEEDED"
        # Brand-new independent worker process, same owned synthetic minimum CRUD role.
        second = child(env, runtime_role, "normal", tmp_path)
        try:
            second.communicate(timeout=20)
            assert second.returncode == 0, "Synthetic recovery process failed; values suppressed"
        finally:
            if second.poll() is None:
                second.kill()
                second.communicate(timeout=5)
        reopened = Store(runtime_role)
        try:
            result = reopened.inspect(env[3], a["run_id"])
            assert (
                result["status"] == "SUCCEEDED"
                and result["result"]["sum"] == "4.00"
                and result["result_version"] == 1
            )
            assert len(result["known_effects"]) == 1
        finally:
            reopened.engine.dispose()
        assert (
            quantities(env)["operations"] == 1
            and quantities(env)["internal_instance_data"] == 1
            and quantities(env)["attempts"] == 0
        )
        with env[0].tx() as c:
            kinds = (
                c.execute(select(events.c.kind).where(events.c.run_id == a["run_id"]))
                .scalars()
                .all()
            )
            assert kinds.count("RESULT_COMMITTED") == 1
            if fault == "before_commit":
                assert "WORKER_LOST" in kinds and "RECONCILED" in kinds
    finally:
        if p.poll() is None:
            p.kill()
            p.communicate(timeout=5)


@pytest.mark.parametrize("command", ["pause", "cancel"])
def test_real_pg_process_compute_no_long_lock_control_and_heartbeat(
    env, runtime_role, tmp_path, command
):
    r, i, _, _ = setup(env)
    a = enqueue(env, i, r)
    p = child(env, runtime_role, "hold", tmp_path)
    try:
        until = time.monotonic() + 6
        while not (tmp_path / "entered").exists() and time.monotonic() < until and p.poll() is None:
            time.sleep(0.03)
        assert (tmp_path / "entered").exists(), (
            "Synthetic child never entered bounded compute window"
        )
        time.sleep(1.2)
        assert env[0].claim("competitor", 1) is None
        assert row(env, a["run_id"])["lease_until"] > time.time()
        assert env[0].command(env[3], a["run_id"], command, 1) == (
            "PAUSE_REQUESTED" if command == "pause" else "CANCEL_REQUESTED"
        )
        (tmp_path / "continue").write_text("Continue known pure calculation; commit rechecks stop")
        p.communicate(timeout=12)
        assert p.returncode == 0, "Synthetic controlled worker failed; values suppressed"
        result = env[0].inspect(env[3], a["run_id"])
        assert result["status"] == ("PAUSED" if command == "pause" else "CANCELLED")
        assert result["result_version"] is None and not result["known_effects"]
        assert quantities(env)["internal_instance_data"] == 0
    finally:
        if p.poll() is None:
            p.kill()
            p.communicate(timeout=5)


def test_expired_unknown_cancel_intent_remains_reconciling_no_redispatch(env):
    r, i, _, _ = setup(env)
    a = enqueue(env, i, r)
    w = worker(env)
    claimed = env[0].claim(w.id, 30)
    with env[0].tx() as c:
        c.execute(
            insert(operations).values(
                id=new_id("op"),
                run_id=a["run_id"],
                call_id="unknown",
                fingerprint="0" * 64,
                tool_ref="artifact.save_text",
                status="DISPATCHED",
            )
        )
        c.execute(
            update(runs)
            .where(runs.c.id == a["run_id"])
            .values(cancel_intent=True, lease_until=0, status="CANCEL_REQUESTED")
        )
    assert env[0].claim("replacement", 30) is None
    assert (
        row(env, a["run_id"])["status"] == "RECONCILING" and row(env, a["run_id"])["cancel_intent"]
    )
    jobs.fail_job(w, claimed, DomainError("VERIFICATION_FAILED"))
    assert row(env, a["run_id"])["status"] == "RECONCILING"
    assert quantities(env)["internal_instance_data"] == 0


def test_corrupt_failure_binding_does_not_modify_other_instance_history(env):
    from sim2act.lifecycle import run_instance

    r, i, _, _ = setup(env)
    other = create(env, r)
    completed = run_instance(
        env[0], env[3], other["id"], 1, r["fingerprint"], {"column": "amount"}, "sync", limits(env)
    )
    a = enqueue(env, i, r)
    with env[0].tx() as c:
        c.execute(
            update(internal_run_bindings)
            .where(internal_run_bindings.c.run_id == a["run_id"])
            .values(app_run_id=completed["id"])
        )
    assert worker(env).once()
    assert row(env, a["run_id"])["status"] == "FAILED"
    with env[0].tx() as c:
        foreign = (
            c.execute(select(internal_app_runs).where(internal_app_runs.c.id == completed["id"]))
            .mappings()
            .one()
        )
        assert (
            foreign["status"] == "SUCCEEDED"
            and foreign["result_version"] == 1
            and foreign["output"] == completed["output"]
        )
        assert (
            c.execute(
                select(internal_app_runs.c.status).where(internal_app_runs.c.id == a["app_run_id"])
            ).scalar_one()
            == "QUEUED"
        )
    # Lost/corrupt accepted link is rejected, not guessed or repaired by writing another Run.
    with pytest.raises(DomainError):
        env[0].inspect(env[3], a["run_id"])
    assert len(inspect_instance(env[0], env[3], other["id"], limits(env))["data"]) == 1


def test_expired_lease_same_fence_cannot_append_without_reclaim(env):
    r, i, _, _ = setup(env)
    a = enqueue(env, i, r)
    w = worker(env)
    claimed = env[0].claim(w.id, 30)
    plan = jobs.prepare_dispatch(w, claimed)
    output = jobs.compute(plan)
    with env[0].tx() as c:
        c.execute(update(runs).where(runs.c.id == a["run_id"]).values(lease_until=0))
    assert row(env, a["run_id"])["fence"] == claimed["fence"]
    with pytest.raises(DomainError, match="Stale"):
        jobs.commit_result(w, claimed, plan, output)
    jobs.fail_job(w, claimed, DomainError("VERIFICATION_FAILED"))
    assert (
        quantities(env)["internal_instance_data"] == 0
        and row(env, a["run_id"])["status"] == "RUNNING"
    )
    assert worker(env).once()
    assert env[0].inspect(env[3], a["run_id"])["result_version"] == 1


def test_wall_budget_exhaustion_stops_new_action_before_dispatch(env):
    r, i, _, _ = setup(env)
    a = enqueue(env, i, r)
    with env[0].tx() as c:
        c.execute(update(runs).where(runs.c.id == a["run_id"]).values(created_at=time.time() - 301))
    assert worker(env).once()
    assert (
        row(env, a["run_id"])["status"] == "FAILED"
        and row(env, a["run_id"])["error"]["code"] == "BUDGET_EXHAUSTED"
    )
    assert quantities(env)["operations"] == 0 and quantities(env)["internal_instance_data"] == 0


def test_minimum_pg_role_enqueue_binding_control_and_worker_business_crud(env, runtime_role):
    r, i, _, _ = setup(env)
    app = Store(runtime_role)
    before = quantities(env)
    role_env = (app, *env[1:])
    try:
        accepted = enqueue(role_env, i, r, "role")
        assert enqueue(role_env, i, r, "role")["cached"]
        assert app.inspect(env[3], accepted["run_id"])["status"] == "QUEUED"
        assert app.command(env[3], accepted["run_id"], "pause", 1) == "PAUSED"
        assert app.command(env[3], accepted["run_id"], "resume", 2) == "QUEUED"
        assert worker(role_env).once()
        result = app.inspect(env[3], accepted["run_id"])
        assert result["status"] == "SUCCEEDED" and result["result_version"] == 1
    finally:
        app.engine.dispose()
    after = quantities(env)
    for name in ["principals", "grants", "attempts"]:
        assert after[name] == before[name]
