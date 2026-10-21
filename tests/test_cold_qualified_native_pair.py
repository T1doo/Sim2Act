"""One frozen PYTHON/C pair; shared configured prefix, 7 Mock / 9 entries.

Semantic test clock only. No profiling or helper-identity monkeypatch for C
selection; real HTTP is denied by MockCap, and both C1 cases stop before W5.
"""

import hashlib
import json
import os
import sysconfig
import threading
import time
import uuid
from pathlib import Path

import pytest
import test_natural_spec_apps as apps
from cold_configured_tail_fixture import MockCap, build_prefix, close_case, restore_case
from cold_semantic_clock import SemanticClock
from sqlalchemy import event
from test_cold_configured_semantic_tail import TailStop, exact_output
from test_cold_final_frozen_pair import PairObservation

from sim2act import _cold_typed_native_candidate as native
from sim2act import natural_live_admission as gate
from sim2act import natural_spec_runtime as runtime


def test_final_qualified_native_pair(tmp_path, monkeypatch):
    directory = os.environ.get('COLD_NATIVE_TEST_DIR')
    if directory is None:
        pytest.skip('Explicit native build required')
    backend = native.load_candidate(Path(directory) /
        ('_cold_typed_native_impl' + sysconfig.get_config_var('EXT_SUFFIX')))
    assert backend is not None
    source_paths = [Path(runtime.__file__), Path(gate.__file__), Path(native.__file__),
        Path(native.__file__).with_name('_cold_typed_native_impl.c')]
    frozen = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths}
    original_storage = gate._trial_typed_storage
    clock, before_threads = SemanticClock(monkeypatch), set(threading.enumerate())
    cap = MockCap(monkeypatch)
    cap.exchange_limit, cap.method_limit = 7, 9
    with monkeypatch.context() as patch:
        template = build_prefix(tmp_path / 'prefix', patch, clock, cap)
    observers, reports = [], {}
    for name, use_native in (('python', False), ('qualified-c', True)):
        with monkeypatch.context() as patch:
            clock.healthy()
            counter = iter(range(1_000_000, 1_100_000))
            patch.setattr(uuid, 'uuid4', lambda counter=counter: uuid.UUID(int=next(counter)))
            case = restore_case(template, tmp_path / name, patch, clock)
            case.cold_id = template.cold_id
            cap.new_case()
            observer = PairObservation(case, clock)
            observer.install(patch)
            event.listen(case.store.engine, 'before_cursor_execute', observer.before_sql)
            try:
                worker = case.factory(case.store, case.data[1],
                    goal_planner_transport=apps.transport([], apps.COLD))
                if use_native:
                    worker._cold_typed_native_candidate = backend
                start_cpu, start_wall = time.thread_time_ns(), time.monotonic_ns()
                with pytest.raises(TailStop) as stopped:
                    worker.once()
                cpu = (time.thread_time_ns() - start_cpu) / 1e9
                wall = (time.monotonic_ns() - start_wall) / 1e9
                assert stopped.value.original is observer.original_error is None
                assert observer.prepared and observer.receipts and observer.scope_returned
                assert observer.commits == ['commit:first', 'commit:second']
                assert not observer.trial.guard.active and not observer.trial.accounted_prewrite.active
                assert len(observer.receipt_records) == len(observer.final_samples) == 1
                assert observer.final_samples[0]['scope_inactive']
                assert observer.final_samples[0]['at'] < min(observer.final_samples[0]['deadlines'])
                assert cap.case_exchanges == cap.case_methods == 1
                assert observer.base_qualified > 0
                assert gate._trial_typed_storage is original_storage
                report = observer.report()
                report.update(worker_owner_cpu_seconds=cpu, worker_wall_seconds=wall,
                    native_calls=backend.native_calls, python_selections=backend.python_calls,
                    native_reasons=dict(backend.reasons), last_selection=backend.last,
                    exact_receipt=observer.receipt_records, final_samples=observer.final_samples)
                if use_native:
                    assert observer.trial.guard._typed_native_candidate is backend
                    assert backend.native_calls > 0
                else:
                    assert backend.native_calls == backend.python_calls == 0
                    assert observer.trial.guard._typed_native_candidate is None
                reports[name] = report
                for filename, value in [('report.json', report),
                        ('strict-output.json', exact_output(observer.outputs)),
                        ('strict-sql.json', exact_output(observer.sql)),
                        ('strict-receipt.json', observer.receipt_records)]:
                    (case.root / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2))
                observers.append(observer)
            finally:
                event.remove(case.store.engine, 'before_cursor_execute', observer.before_sql)
                close_case(case, clock)
    old, new = observers
    assert exact_output(old.outputs) == exact_output(new.outputs)
    assert exact_output(old.sql) == exact_output(new.sql)
    assert old.receipt_records == new.receipt_records
    assert exact_output(old.final_samples) == exact_output(new.final_samples)
    assert old.required_rows == new.required_rows
    assert old.base_calls == new.base_calls and old.base_returned == new.base_returned
    assert old.base_qualified == new.base_qualified == 275
    assert old.base_dynamic_checks == new.base_dynamic_checks
    assert old.codec_calls == new.codec_calls and old.codec_bytes == new.codec_bytes
    assert hashlib.sha256(template.path.read_bytes()).hexdigest() == template.sha256
    assert (cap.exchanges, cap.methods, cap.delegates) == (7, 9, 2)
    assert not any(thread.is_alive() for thread in threading.enumerate() if thread not in before_threads)
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == frozen[str(path)] for path in source_paths)
    result = dict(classification='CONFIGURED_SYNTHETIC_SEMANTIC_CLOCK_NOT_G0',
        frozen=frozen, reports=reports, backend_identity=backend.identity,
        exact_output_sql_receipt_final_gate=True, base_qualification_preserved=True,
        mock_exchanges=cap.exchanges, mock_entries=cap.methods,
        cleanup_threads_empty=True, real_models=0, cold2=False, w5=False)
    (tmp_path / 'qualified-pair.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print('qualified-pair', json.dumps(result, ensure_ascii=False))
