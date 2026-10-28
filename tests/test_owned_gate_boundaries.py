"""Reduced checks require fixed effects and an actual live writer, not a permit."""
import dis
import sys
import threading
import time
import types

import pytest
from sqlalchemy import select
from test_cold_accounted_sqlite import sql_facts  # noqa: F401
from test_model_settlement_interval import received  # noqa: F401
from test_owned_g0_candidate import prepared
import test_spec_production_controller as fixture_module

from sim2act import natural_spec_runtime as runtime
from sim2act import pa_spec_apps as spec
from sim2act import pb_natural_specs as pb
from sim2act import production_evidence as evidence
from sim2act import production_trial_policy as policy
from sim2act._immutable_settlement import UnsupportedPlan
from sim2act._owned_g0_candidate import MockCandidate, _codes, prewrite
from sim2act.contracts import Limits
from sim2act.db import Store, runs
from sim2act.errors import DomainError


def cell(value):
    return (lambda: value).__closure__[0]


def declared_fixture(qualname, values):
    code = next(code for code in _codes(fixture_module.configured.__code__)
                if code.co_qualname == qualname)
    return types.FunctionType(code, vars(fixture_module), code.co_name,
        closure=tuple(cell(values[name]) for name in code.co_freevars) or None)


def test_unknown_callback_is_rejected_even_when_not_installed():
    def unknown():
        pytest.fail("Unreviewed callback executed")
    with pytest.raises(UnsupportedPlan, match="Unreviewed"):
        MockCandidate(fixture_callbacks=(unknown,))


@pytest.mark.parametrize("damage", ["global_alias", "module_factory", "downstream_schema", "builtin_shadow"])
def test_preconstructor_fixture_effect_substitution_never_executes(monkeypatch, damage):
    source = declared_fixture("configured.<locals>.source",
        dict(binding=None, data=(), fixture={"revoked": False, "source_reads": 0}))
    def unknown(*args, **kwargs):
        pytest.fail("Unqualified effect executed")
    monkeypatch.setattr(evidence, "resolve_account", source)
    if damage == "global_alias":
        monkeypatch.setattr(fixture_module, "fingerprint", unknown)
    elif damage == "module_factory":
        monkeypatch.setattr(policy, "SourceVerificationResult", unknown)
    elif damage == "downstream_schema":
        monkeypatch.setattr(evidence, "EvidenceRequirements", unknown)
    else:
        monkeypatch.setattr(fixture_module, "getattr", unknown, raising=False)
    with pytest.raises(UnsupportedPlan):
        MockCandidate(fixture_callbacks=(source,))


def test_reviewed_fixture_cannot_be_reused_in_wrong_target_slot(monkeypatch):
    callback = declared_fixture("configured.<locals>.<lambda>", {})
    monkeypatch.setattr(Store, "guard", callback)
    with pytest.raises(UnsupportedPlan, match="wrong target"):
        MockCandidate(fixture_callbacks=(callback,))


@pytest.mark.parametrize("damage", ["schema", "default"])
def test_unknown_callee_aba_is_rejected_before_sql(sql_facts, damage):
    f = sql_facts
    candidate, plan, call, platform = prepared(f)
    with pytest.raises(DomainError):
        with f.store.tx() as c, pb._source_reads(f.store,c):
            with prewrite(candidate, plan, f.worker, c, f.cold_job, call, platform) as scope:
                def unknown():
                    if damage == "schema":
                        target = Limits.__pydantic_core_schema__["metadata"]
                        target["owned_aba_probe"] = True
                        try:
                            c.execute(select(runs.c.id)).all()
                        finally:
                            del target["owned_aba_probe"]
                    else:
                        target = spec.receipts.__wrapped__.__kwdefaults__
                        old = target["allow_pending"]
                        target["allow_pending"] = not old
                        try:
                            c.execute(select(runs.c.id)).all()
                        finally:
                            target["allow_pending"] = old
                scope.call(unknown)


@pytest.mark.parametrize("abort", [False, True])
def test_actual_writer_issues_lifetime_at_yield_and_erases_before_unlock(received, abort):
    worker, job, aid, deadline, state = received
    worker._owned_g0_candidate = object()  # Metadata issuance alone authorizes nothing.
    original_run = dict(job)
    key = (threading.get_ident(), id(worker))
    state["sync_contention_recovery"] = True
    try:
        with runtime._model_settlement_writer(worker, job, deadline, state,
                attempt_id=aid, _original_run=original_run) as token:
            assert runtime._OWNED_WRITER_LIFETIMES[key] is token
            assert token[:4] == (worker, job, original_run, state)
            assert token[1] is job and token[2] is original_run and token[1] is not token[2]
            assert token[4] is state["renewal_lock"] and token[4].locked()
            assert token[5] is worker._settlement_lock and token[5].locked()
            assert worker._settlement_interval is not None
            frame = token[7]
            assert frame.f_code is runtime._model_settlement_writer.__wrapped__.__code__
            assert dis.opname[frame.f_code.co_code[frame.f_lasti]] == "YIELD_VALUE"
            assert frame.f_locals["token"] is token
            if abort:
                raise RuntimeError("synthetic rollback boundary")
    except RuntimeError:
        assert abort
    assert key not in runtime._OWNED_WRITER_LIFETIMES
    assert not token[4].locked() and not token[5].locked()
    assert not hasattr(worker, "_settlement_interval")


def test_forged_registry_tuple_with_locked_native_locks_has_no_origin(sql_facts):
    f = sql_facts
    candidate, _, call, platform = prepared(f)
    call["call_run"] = f.cold_job
    plan = candidate.prepare(f.worker, f.cold_bound, call, platform)
    first, second = threading.Lock(), threading.Lock()
    first.acquire(); second.acquire()
    f.worker._settlement_lock = second
    f.worker._settlement_interval = (time.monotonic()+20,time.time()+20)
    key = (threading.get_ident(), id(f.worker))
    token = (f.worker, f.cold_job, f.cold_job, None, first, second,
        threading.get_ident(), sys._getframe())
    runtime._OWNED_WRITER_LIFETIMES[key] = token
    try:
        from sim2act import pb_natural_specs as pb
        with pytest.raises(DomainError, match="writer lifetime"):
            with f.store.tx() as c, pb._source_reads(f.store,c):
                with prewrite(candidate, plan, f.worker, c, f.cold_job, call, platform,
                        _writer_epoch=token):
                    pytest.fail("Forged origin selected")
    finally:
        runtime._OWNED_WRITER_LIFETIMES.pop(key,None)
        first.release(); second.release()
        del f.worker._settlement_interval


def test_fixed_callee_argument_roles_with_actual_writer_lifetime(received):
    """Check role selection without executing a SQL/model call or forging a token."""
    from sim2act._owned_g0_candidate import _Code, _Scope
    worker, job, aid, deadline, state = received
    worker._owned_g0_candidate = object()
    original_run = dict(job)
    state["sync_contention_recovery"] = True
    code = _Code(())
    with runtime._model_settlement_writer(worker, job, deadline, state,
            attempt_id=aid, _original_run=original_run) as token:
        view = object.__new__(_Scope)
        view.writer_epoch, view.writer_epochs = token, runtime._OWNED_WRITER_LIFETIMES
        view.worker, view.store, view.current = worker, worker.store, dict(job)
        view.thread, view.settlement_interval = threading.get_ident(), worker._settlement_interval
        view.candidate = types.SimpleNamespace(code=code)
        view.roots = {"call": {"call_run": original_run}}
        view.c = object()  # Identity carrier only; no SQL can execute in this unit test.
        view.private = {"call": {"call_run": original_run, "aid": aid,
            "meta": {"operation_id": "synthetic-op"}}}
        view.outputs = {"limits": object(), "binding": {}}
        args = (view.store, view.c, view.current["principal_id"], view.current, view.outputs["limits"])
        assert view.original_call(spec.bound, args, {})
        assert not view.original_call(spec.bound, (object(), *args[1:]), {})
        assert not view.original_call(spec.bound, (*args[:-1], object()), {})
        assert not view.original_call(spec.bound, args, {"unknown": True})
        assert not view.original_call(lambda: None, (), {})
    assert not view.writer_current()  # Same token cannot be reused after actual unlock.


def test_parent_sql_method_cannot_shadow_actual_dialect_dispatch(sql_facts):
    from sqlalchemy.engine.default import DefaultDialect
    f = sql_facts
    candidate, plan, call, platform = prepared(f)
    with pytest.raises(DomainError):
        with f.store.tx() as c, pb._source_reads(f.store,c):
            with prewrite(candidate, plan, f.worker, c, f.cold_job, call, platform) as scope:
                original = c.engine.dialect.__dict__.get("on_connect")
                assert original is None
                c.engine.dialect.__dict__["on_connect"] = DefaultDialect.on_connect
                try:
                    scope.check(full_code=True)
                finally:
                    del c.engine.dialect.__dict__["on_connect"]
