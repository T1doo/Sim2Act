"""One complete old/fresh-comparison pair, 7 Mock exchanges / 9 entries.

Explicit test clock; original SQL, sender, dynamic gates and final sample.
All selector/immutable projection/baseline creation costs are included. No
profiler and no real-clock G0 qualification. No retry/Cold2/W5/real HTTP.
"""

import hashlib
import json
import os
import threading
import time
import uuid
from dataclasses import replace
from pathlib import Path

import pytest
import test_cold_configured_semantic_tail as tail
import test_natural_spec_apps as apps
from cold_configured_tail_fixture import MockCap, build_prefix, close_case, config, restore_case
from cold_semantic_clock import SemanticClock
from sqlalchemy import event
from test_cold_configured_semantic_tail import TailStop, exact_output
from test_cold_final_frozen_pair import PairObservation
from test_cold_frontier_compare import BOUNDS


def test_one_complete_frontier_pair(tmp_path, monkeypatch):
    # Must use the existing bounded supervisor for this full synthetic pair.
    progress = Path(os.environ['COLD_MOCK_PROGRESS_PATH'])
    def record(value):
        pending = progress.with_suffix('.pending')
        pending.write_text(json.dumps(value) + '\n')
        pending.replace(progress)
    class RecordedCap(MockCap):
        def enter(self, exchange):
            super().enter(exchange)
            record(dict(mock_exchange_admissions=self.exchanges,
                mock_entry_admissions=self.methods, stage=self.stage, source_delegates=self.delegates))
    source_paths = [*sorted(Path('src/sim2act').glob('*.py')),
        *sorted(Path('src/sim2act').glob('*.c')), *sorted(Path('tests').glob('*.py'))]
    frozen = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths}
    clock, threads = SemanticClock(monkeypatch), set(threading.enumerate())
    cap = RecordedCap(monkeypatch)
    cap.exchange_limit, cap.method_limit = 7, 9
    record(dict(mock_exchange_admissions=0, mock_entry_admissions=0,
                stage=cap.stage, source_delegates=0))
    with monkeypatch.context() as patch:
        template = build_prefix(tmp_path / 'prefix', patch, clock, cap)
    observers, reports = [], {}
    for name, enabled in (('original', False), ('fresh-comparison', True)):
        with monkeypatch.context() as patch:
            clock.healthy()
            counter = iter(range(1_000_000, 1_100_000))
            patch.setattr(uuid, 'uuid4', lambda counter=counter: uuid.UUID(int=next(counter)))
            patch.setattr(tail, 'config', lambda enabled=enabled:
                replace(config(), frontier_compare=BOUNDS if enabled else None))
            case = restore_case(template, tmp_path / name, patch, clock)
            case.cold_id = template.cold_id
            cap.new_case()
            observer = PairObservation(case, clock)
            observer.install(patch)
            event.listen(case.store.engine, 'before_cursor_execute', observer.before_sql)
            try:
                worker = case.factory(case.store, case.data[1],
                    goal_planner_transport=apps.transport([], apps.COLD))
                cpu, wall = time.thread_time_ns(), time.monotonic_ns()
                with pytest.raises(TailStop) as stopped:
                    worker.once()
                cpu, wall = (time.thread_time_ns() - cpu) / 1e9, (time.monotonic_ns() - wall) / 1e9
                assert stopped.value.original is observer.original_error is None
                assert observer.prepared and observer.receipts and observer.scope_returned
                assert observer.commits == ['commit:first', 'commit:second']
                assert not observer.trial.guard.active and not observer.trial.accounted_prewrite.active
                assert observer.base_qualified == 275
                assert len(observer.receipt_records) == len(observer.final_samples) == 1
                final = observer.final_samples[0]
                assert final['scope_inactive'] and final['at'] < min(final['deadlines'])
                assert cap.case_exchanges == cap.case_methods == 1
                frontier = observer.trial.guard._accounted_frontier
                counts = dict(frontier.compare_counts)
                assert (counts['selected'] > 0) is enabled
                assert (frontier.compare_limits is BOUNDS) is enabled
                report = observer.report()
                report.update(worker_owner_cpu_seconds=cpu, worker_wall_seconds=wall,
                    comparison_counts=counts, comparison_limits=None if not enabled else BOUNDS._asdict(),
                    exact_receipt=observer.receipt_records, final_samples=observer.final_samples)
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
    assert reports['original']['context_business_fingerprints'] == reports['fresh-comparison']['context_business_fingerprints']
    assert reports['original']['source_business_fingerprints'] == reports['fresh-comparison']['source_business_fingerprints']
    clock.assert_closed()
    assert hashlib.sha256(template.path.read_bytes()).hexdigest() == template.sha256
    assert (cap.exchanges, cap.methods, cap.delegates) == (7, 9, 2)
    assert not any(thread.is_alive() for thread in threading.enumerate() if thread not in threads)
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == frozen[str(path)] for path in source_paths)
    result = dict(classification='CONFIGURED_SYNTHETIC_SEMANTIC_CLOCK_NOT_G0',
        frozen=frozen, reports=reports, exact_output_sql_receipt_final_gate=True,
        base_qualification_preserved=True, mock_exchanges=cap.exchanges, mock_entries=cap.methods,
        cleanup_threads_empty=True, real_models=0, cold2=False, w5=False)
    (tmp_path / 'frontier-pair.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print('frontier-pair', json.dumps({key: value for key, value in result.items() if key != 'frozen'}))
