"""Complete original configured C1 semantics under an explicit test clock.

No real-clock G0/launcher acceptance: virtual business time pauses during pure
verification. Real supervision/diagnostic clocks do not. Stops before W5/Cold2.
"""

import copy
import hashlib
import json
import os
import threading
import uuid
from contextlib import contextmanager

import pytest
import test_natural_spec_apps as apps
from cold_configured_tail_fixture import (
    MockCap,
    build_prefix,
    close_case,
    config,
    load_prefix,
    restore_case,
)
from cold_semantic_clock import SemanticClock
from sqlalchemy import event, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.elements import quoted_name

from sim2act import natural_live_admission as gate
from sim2act import natural_spec_runtime as runtime
from sim2act import pa_spec_apps as spec
from sim2act.db import attempts, fingerprint
from sim2act.errors import DomainError


class TailStop(BaseException):
    def __init__(self, original=None):
        self.original = original


def exact_output(value):
    """Diagnostic encoding only, not a replacement business fingerprint."""
    kind = type(value)
    if kind is quoted_name:
        return ['quoted-name', str(value), value.quote]
    if kind is bytes:
        return ['bytes', value.hex()]
    if kind is tuple or kind is list:
        return [kind.__name__, [exact_output(item) for item in value]]
    if kind is dict:
        assert all(type(key) is str or type(key) is quoted_name for key in value)
        return ['dict', [[exact_output(key), exact_output(value[key])]
            for key in sorted(value, key=str)]]
    assert kind in (str, int, float, bool, type(None))
    return [kind.__name__, value]


class TailObservation:
    def __init__(self, case, clock, fault=None):
        self.case, self.clock, self.fault = case, clock, fault
        self.trial = None
        self.active = False
        self.prepared = self.receipts = self.scope_returned = False
        self.commits = []
        self.codec_calls = self.codec_bytes = 0
        self.sql = []
        self.required_rows = 0
        self.original_error = None
        self.outputs = []
        self.fault_applied = False
        self.first_write_returned = False
        self.base_calls = self.base_returned = self.base_rejected = 0
        self.base_qualified = self.base_dynamic_checks = 0
        self._in_base = 0

    def install(self, patch):
        context = runtime._cold_model_before
        prepare = runtime._ColdTrialGraph._prepare
        commit = runtime._ColdTrialGraph.commit
        receipts = spec._cold_receipts
        encode = runtime._cold_graph_bytes
        require_row = gate._require_run_context_row
        base = runtime._ColdTrialGraph._base
        dynamic = runtime._ColdGraphRead._check_dynamic
        serializers = runtime._base_segments.fixed_serializers

        def based(trial):
            counted = self.active and trial is self.trial
            if counted:
                self.base_calls += 1
                self._in_base += 1
            try:
                result = base(trial)
                if counted:
                    self.base_returned += 1
                return result
            except BaseException:
                if counted:
                    self.base_rejected += 1
                raise
            finally:
                if counted:
                    self._in_base -= 1

        def qualified(models):
            result = serializers(models)
            if self._in_base:
                self.base_qualified += int(result)
            return result

        def dynamic_checked(graph, store, connection):
            if self._in_base:
                self.base_dynamic_checks += 1
            return dynamic(graph, store, connection)

        def encoded(values):
            result = encode(values)
            if self.active and threading.current_thread() is threading.main_thread():
                self.codec_calls += 1
                self.codec_bytes += len(result)
            return result

        def prepared(trial, job):
            result = prepare(trial, job)
            if trial is self.trial:
                self.prepared = True
                assert type(trial.platform) is type(trial.trial) is runtime._ColdBindingGraph
                # This original pre path requires audit_seed=None; a post seed
                # is not fabricated to fill an inapplicable fixture attribute.
                assert trial.audit_seed is None and trial.guard.phase == 'pre'
            return result

        def committed(trial, prefix):
            result = commit(trial, prefix)
            if trial is self.trial:
                self.commits.append(prefix.key)
                self.outputs.append(copy.deepcopy(trial.authority_record))
                if len(self.commits) == 1:
                    if self.fault == 'mutation':
                        trial.guard.inputs['current']['fingerprint'] = 'f' * 64
                        self.fault_applied = True
                    elif self.fault == 'revocation':
                        self.case.fixture['revoked'] = True
                        self.fault_applied = True
                    elif self.fault == 'write-fault':
                        trial.c.execute(text('INSERT INTO semantic_rollback_probe VALUES (1)'))
                        self.first_write_returned = self.fault_applied = True
                        # A real SQLite constraint failure after one successful
                        # write, in the same original admission transaction.
                        trial.c.execute(text('INSERT INTO semantic_rollback_probe VALUES (2)'))
                elif self.fault == 'expired-final':
                    with self.clock.lock:
                        self.clock.value = min(trial.authority_record['deadlines']) + 1
                    self.fault_applied = True
            return result

        def received(*args, **kwargs):
            result = receipts(*args, **kwargs)
            if (self.active and self.trial is not None
                    and args[2]['id'] == self.case.cold_id
                    and args[4] is self.trial.platform.counter_reader
                    and kwargs.get('pending_id') == self.trial.guard.inputs['call']['meta']['operation_id']
                    and kwargs.get('allow_pending', False) is False):
                assert self.commits == ['commit:first']
                self.receipts = True
            return result

        def required(*args, **kwargs):
            if self.active:
                self.required_rows += 1
            return require_row(*args, **kwargs)

        @contextmanager
        def observed(worker, c, current, inputs, platform):
            if current['id'] != self.case.cold_id:
                with context(worker, c, current, inputs, platform) as trial:
                    yield trial
                return
            self.active = True
            self.clock.healthy()
            try:
                with context(worker, c, current, inputs, platform,
                        _mock_accounted_config=config()) as trial:
                    self.trial = trial
                    yield trial
                self.scope_returned = True
                self.clock.healthy()
                assert self.commits == ['commit:first', 'commit:second']
                assert self.prepared and self.receipts
                assert not trial.guard.active and not trial.accounted_prewrite.active
                with pytest.raises(DomainError):
                    trial.check()
                raise TailStop()
            except TailStop:
                raise
            except (DomainError, IntegrityError) as error:
                self.original_error = error
                raise TailStop(error) from error
            finally:
                self.active = False

        patch.setattr(runtime._ColdTrialGraph, '_base', based)
        patch.setattr(runtime._ColdGraphRead, '_check_dynamic', dynamic_checked)
        patch.setattr(runtime._base_segments, 'fixed_serializers', qualified)
        patch.setattr(runtime, '_cold_model_before', observed)
        patch.setattr(runtime, '_cold_graph_bytes', encoded)
        patch.setattr(runtime._ColdTrialGraph, '_prepare', prepared)
        patch.setattr(runtime._ColdTrialGraph, 'commit', committed)
        patch.setattr(spec, '_cold_receipts', received)
        patch.setattr(gate, '_require_run_context_row', required)

    def before_sql(self, c, cursor, statement, parameters, context, executemany):
        if self.active and threading.current_thread() is threading.main_thread():
            self.sql.append((statement, parameters))

    def report(self):
        error = self.original_error
        return dict(prepared=self.prepared, commits=self.commits, receipts=self.receipts,
            original_scope_returned=self.scope_returned, codec_calls=self.codec_calls,
            codec_returned_bytes=self.codec_bytes, run_predicate_calls=self.required_rows,
            sql_statements=len(self.sql), base_calls=self.base_calls,
            base_returned=self.base_returned, base_rejected=self.base_rejected,
            qualified_base_calls=self.base_qualified, base_dynamic_checks=self.base_dynamic_checks,
            fault=self.fault,
            fault_applied=self.fault_applied, first_write_returned=self.first_write_returned,
            error=None if error is None else dict(type=type(error).__name__,
                code=getattr(error, 'code', None), message=str(error)),
            diagnostic_output_digests=[fingerprint(exact_output(value)) for value in self.outputs],
            context_business_fingerprints=[fingerprint(value['context']) for value in self.outputs],
            source_business_fingerprints=[fingerprint(value['source']) for value in self.outputs],
            business_clock=self.clock.now(), real_clock_acceptance=False)


def test_complete_configured_old_candidate_tail_and_safety_cases(tmp_path, monkeypatch):
    clock = SemanticClock(monkeypatch)
    cap = MockCap(monkeypatch)
    before_threads = set(threading.enumerate())
    checkpoint = os.environ.get('SIM2ACT_SEMANTIC_TEST_TEMPLATE')
    if checkpoint is None:
        with monkeypatch.context() as patch:
            template = build_prefix(tmp_path / 'prefix', patch, clock, cap)
    else:
        template = load_prefix(checkpoint, clock, cap)
    reports, successes = {}, []
    for name, old, fault in (
        ('old', True, None), ('candidate', False, None),
        ('expired', False, 'expired-final'), ('mutation', False, 'mutation'),
        ('revocation', False, 'revocation'), ('write-fault', False, 'write-fault'),
    ):
        with monkeypatch.context() as patch:
            clock.healthy()
            counter = iter(range(1_000_000, 1_100_000))
            patch.setattr(uuid, 'uuid4', lambda counter=counter: uuid.UUID(int=next(counter)))
            case = restore_case(template, tmp_path / name, patch, clock)
            case.cold_id = template.cold_id
            cap.new_case()
            observer = TailObservation(case, clock, fault)
            if old:
                patch.setattr(runtime._base_segments, 'eligible', lambda trial: False)
            if fault == 'write-fault':
                with case.store.tx() as c:
                    c.execute(text('CREATE TABLE semantic_rollback_probe (value INTEGER CHECK(value=1))'))
            observer.install(patch)
            event.listen(case.store.engine, 'before_cursor_execute', observer.before_sql)
            try:
                worker = case.factory(case.store, case.data[1],
                    goal_planner_transport=apps.transport([], apps.COLD))
                with pytest.raises(TailStop) as stopped:
                    worker.once()
                assert stopped.value.original is observer.original_error
                assert cap.case_exchanges == cap.case_methods == 1
                assert observer.trial is not None and not observer.trial.guard.active
                assert not observer.trial.accounted_prewrite.active
                if fault is None:
                    assert observer.scope_returned and observer.original_error is None
                    successes.append(observer)
                else:
                    assert not observer.scope_returned and observer.original_error is not None
                    assert observer.fault_applied
                    if fault == 'expired-final':
                        assert observer.commits == ['commit:first', 'commit:second'] and observer.receipts
                        assert isinstance(observer.original_error, DomainError)
                        assert observer.original_error.message == 'Production admission expired after closing the Cold read scope'
                    if fault == 'write-fault':
                        assert observer.commits == ['commit:first'] and observer.first_write_returned
                        assert type(observer.original_error) is IntegrityError
                        assert observer.original_error.orig.sqlite_errorcode == 275
                        with case.store.tx() as c:
                            assert c.execute(text('SELECT count(*) FROM semantic_rollback_probe')).scalar_one() == 0
                    if fault in ('mutation', 'revocation'):
                        assert observer.commits == ['commit:first']
                        assert type(observer.original_error) is DomainError
                        if fault == 'mutation':
                            assert observer.original_error.code == 'VERSION_CONFLICT'
                            assert observer.original_error.message == 'Native mutable frontier changed'
                        else:
                            assert observer.original_error.code == 'LIVE_BLOCKED'
                            trace = observer.original_error.__traceback__
                            names = []
                            while trace is not None:
                                names.append(trace.tb_frame.f_code.co_name)
                                trace = trace.tb_next
                            assert 'check_source' in names
                with case.store.tx() as c:
                    cold = c.execute(select(attempts).where(attempts.c.run_id == case.cold_id)).mappings().all()
                    assert len(cold) == 1 and cold[0]['status'] == 'RECEIVED'
                reports[name] = observer.report()
                (case.root / 'tail-result.json').write_text(json.dumps(reports[name], indent=2))
                (case.root / 'complete-original-outputs.json').write_text(
                    json.dumps(exact_output(observer.outputs), indent=2))
            finally:
                event.remove(case.store.engine, 'before_cursor_execute', observer.before_sql)
                close_case(case, clock)
    left, right = successes
    assert left.outputs == right.outputs
    assert exact_output(left.outputs) == exact_output(right.outputs)
    assert left.sql == right.sql
    assert exact_output(left.sql) == exact_output(right.sql)
    assert left.required_rows == right.required_rows
    assert left.base_calls == right.base_calls and right.base_qualified > 0
    assert left.base_returned == right.base_returned
    assert left.base_rejected == right.base_rejected == 1  # Deliberate closed-scope refusal.
    assert left.base_dynamic_checks == right.base_dynamic_checks == 2 * right.base_returned + 1
    assert right.codec_calls < left.codec_calls and right.codec_bytes < left.codec_bytes
    assert hashlib.sha256(template.path.read_bytes()).hexdigest() == template.sha256
    expected = (11, 13) if checkpoint is None else (
        cap.checkpoint_prior[0] + 6, cap.checkpoint_prior[1] + 6)
    assert (cap.exchanges, cap.methods, cap.delegates) == (*expected, 2)
    assert not any(thread.is_alive() for thread in threading.enumerate() if thread not in before_threads)
    (tmp_path / 'complete-semantic-difference.json').write_text(json.dumps(dict(
        classification='CONFIGURED_SYNTHETIC_VIRTUAL_CLOCK_NOT_REAL_G0_ACCEPTANCE',
        shared_prefix=dict(mock_exchanges=5, methods=7, source_delegates=2,
            template_sha256=template.sha256, source_receipt=template.prefix_receipt),
        suite_mock_cap=dict(exchanges=cap.exchange_limit, methods=cap.method_limit), actual_mock_exchanges=cap.exchanges,
        actual_mock_methods=cap.methods, reports=reports, equal_complete_outputs=True,
        equal_full_sql_sequence=True, cross_scope_rejected=True, cleanup_threads_empty=True,
        real_models=0, w5_entered=False, cold2=False), indent=2))
