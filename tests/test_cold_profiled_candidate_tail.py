"""One identity-preserving configured candidate tail; optional CPU profiler.

Explicit virtual business clock. Only the external context adapter selects the
test-only candidate and stops after its normal return, before W5. No core,
qualification, serializer, prepare/commit or receipt function is replaced.
"""

import copy
import hashlib
import json
import os
import pstats
import threading
import time
import uuid
from contextlib import contextmanager

import pytest
import test_natural_spec_apps as apps
from cold_configured_tail_fixture import (
    MockCap,
    build_prefix,
    close_case,
    config,
    restore_case,
)
from cold_cpu_profile import MainThreadCPUProfile
from cold_semantic_clock import SemanticClock
from sqlalchemy import event, select
from test_cold_configured_semantic_tail import TailStop, exact_output

from sim2act import natural_spec_runtime as runtime
from sim2act.db import attempts
from sim2act.errors import DomainError


def _profile_json(profile):
    stats = pstats.Stats(profile)
    rows = []
    for (filename, line, name), (primitive, calls, exclusive, inclusive, callers) in stats.stats.items():
        rows.append(dict(file=filename, line=line, name=name, primitive=primitive,
            calls=calls, exclusive_cpu=exclusive, inclusive_cpu=inclusive,
            callers=[dict(file=key[0], line=key[1], name=key[2], values=value)
                for key, value in callers.items()]))
    return sorted(rows, key=lambda row: row['exclusive_cpu'], reverse=True)


def test_one_complete_identity_preserving_candidate_tail(tmp_path, monkeypatch):
    profiled = os.environ.get('SIM2ACT_PROFILE_COLD') == '1'
    clock = SemanticClock(monkeypatch)
    cap = MockCap(monkeypatch)
    cap.exchange_limit, cap.method_limit = 6, 8
    before_threads = set(threading.enumerate())
    with monkeypatch.context() as patch:
        template = build_prefix(tmp_path / 'prefix', patch, clock, cap)
    originals = dict(core=runtime._COLD_BASE_CORE,
        eligible=runtime._base_segments.eligible,
        serializers=runtime._base_segments.fixed_serializers,
        base=runtime._ColdTrialGraph._base,
        prepare=runtime._ColdTrialGraph._prepare,
        commit=runtime._ColdTrialGraph.commit)
    profiler = MainThreadCPUProfile()
    profile = profiler.profile
    state, sql = {}, []
    with monkeypatch.context() as patch:
        counter = iter(range(1_000_000, 1_100_000))
        patch.setattr(uuid, 'uuid4', lambda: uuid.UUID(int=next(counter)))
        case = restore_case(template, tmp_path / 'candidate', patch, clock)
        cap.new_case()
        context = runtime._cold_model_before

        @contextmanager
        def selected(worker, c, current, inputs, platform):
            assert current['id'] == template.cold_id
            state['active'] = True
            process_started, thread_started = time.process_time(), time.thread_time()
            if profiled:
                profiler.enable()
            try:
                with context(worker, c, current, inputs, platform, _mock_accounted_config=config()) as trial:
                    state['trial'] = trial
                    yield trial
                assert not trial.guard.active and not trial.accounted_prewrite.active
                state['output_values'] = [trial.guard.inputs[f'commit:{key}:trial-output']
                    for key in ('first', 'second')]
                reader = trial.platform.counter_reader
                assert len(reader._receipt_proofs) == 1
                receipt = reader._raw[reader._receipt_proofs[0]]
                assert receipt['binding'] is reader._raw['receipt-binding:0']
                state['receipt_value'] = dict(outputs=receipt['outputs'], proved=receipt['proved'],
                    pending_id=receipt['pending_id'], allow_pending=receipt['allow_pending'],
                    binding_audit_fingerprint=receipt['binding']['audit_fingerprint'])
                with pytest.raises(DomainError):
                    trial.check()
                state['normal_scope_returned'] = True
                raise TailStop()
            finally:
                if profiled:
                    profiler.disable()
                state.update(process_cpu=time.process_time() - process_started,
                    owner_thread_cpu=time.thread_time() - thread_started)
                if profiled:
                    profile.dump_stats(str(tmp_path / 'cold-thread-cpu.prof'))
                    (tmp_path / 'profile.json').write_text(json.dumps(_profile_json(profile)))
                state['active'] = False

        def before_sql(c, cursor, statement, parameters, context, executemany):
            if state.get('active') and threading.current_thread() is threading.main_thread():
                sql.append((statement, copy.deepcopy(parameters)))

        patch.setattr(runtime, '_cold_model_before', selected)
        event.listen(case.store.engine, 'before_cursor_execute', before_sql)
        try:
            worker = case.factory(case.store, case.data[1], goal_planner_transport=apps.transport([], apps.COLD))
            with pytest.raises(TailStop) as stopped:
                worker.once()
            assert stopped.value.original is None and state['normal_scope_returned']
            assert (cap.case_exchanges, cap.case_methods) == (1, 1)
            with case.store.tx() as c:
                rows = c.execute(select(attempts).where(attempts.c.run_id == template.cold_id)).mappings().all()
                assert len(rows) == 1 and rows[0]['status'] == 'RECEIVED'
        finally:
            event.remove(case.store.engine, 'before_cursor_execute', before_sql)
            close_case(case, clock)
    assert originals == dict(core=runtime._COLD_BASE_CORE,
        eligible=runtime._base_segments.eligible, serializers=runtime._base_segments.fixed_serializers,
        base=runtime._ColdTrialGraph._base, prepare=runtime._ColdTrialGraph._prepare,
        commit=runtime._ColdTrialGraph.commit)
    assert not any(thread.is_alive() for thread in threading.enumerate() if thread not in before_threads)
    assert hashlib.sha256(template.path.read_bytes()).hexdigest() == template.sha256
    state.pop('trial')
    state['outputs'] = exact_output(state.pop('output_values'))
    state['receipt'] = exact_output(state.pop('receipt_value'))
    state.update(sql=exact_output(sql), mock_exchanges=cap.exchanges, mock_methods=cap.methods,
        source_delegates=cap.delegates, qualification_functions_unchanged=True,
        classification='CONFIGURED_SYNTHETIC_VIRTUAL_CLOCK_NOT_REAL_G0', profiler_thread_cpu=profiled,
        cleanup_threads_empty=True, w5_entered=False, cold2=False)
    if profiled:
        stats = pstats.Stats(profile).stats
        def calls(function):
            code = function.__code__
            return stats[(code.co_filename, code.co_firstlineno, code.co_name)][1]
        assert calls(originals['serializers']) == calls(runtime._ColdTrialGraph._typed_values_from_models) == 275
        assert calls(originals['base']) == 569
        assert calls(runtime._ColdTrialGraph._typed_parameters) == 293
        state['qualified_entries'] = 275
    (tmp_path / 'result.json').write_text(json.dumps(state))
