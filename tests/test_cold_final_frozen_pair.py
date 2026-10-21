"""Exactly two complete normal configured tails on the final frozen source.

One new shared prefix (5 exchanges/7 entries), two isolated C1 copies (1/1
each), explicit virtual business clock, real HTTP forbidden, no retries/W5.
"""

import hashlib
import json
import sys
import threading
import uuid

import pytest
import test_natural_spec_apps as apps
from cold_configured_tail_fixture import MockCap, build_prefix, close_case, restore_case
from cold_semantic_clock import SemanticClock
from sqlalchemy import event, select
from test_cold_configured_semantic_tail import TailObservation, TailStop, exact_output

from sim2act import natural_spec_runtime as runtime
from sim2act import pa_spec_apps as spec
from sim2act.db import attempts, fingerprint


class PairObservation(TailObservation):
    """Add exact receipt storage and the ORIGINAL final clock sample only."""

    def __init__(self, case, clock):
        super().__init__(case, clock)
        self.receipt_records = []
        self.final_samples = []

    def install(self, patch):
        original_context_code = runtime._cold_model_before.__wrapped__.__code__
        super().install(patch)
        received = spec._cold_receipts
        sampled = runtime.time.time

        def receipt(*args, **kwargs):
            matched = (self.active and self.trial is not None
                and args[2]['id'] == self.case.cold_id
                and args[4] is self.trial.platform.counter_reader
                and kwargs.get('pending_id') == self.trial.guard.inputs['call']['meta']['operation_id']
                and kwargs.get('allow_pending', False) is False)
            if matched:
                reader, binding = args[4], args[3]
                index = len(reader._receipt_proofs)
            result = received(*args, **kwargs)
            if matched:
                name = f'receipts:{index}'
                assert reader._receipt_proofs[-1] == name
                assert len(reader._receipt_proofs) == index + 1
                assert reader._raw[f'receipt-binding:{index}'] is binding
                stored = reader._raw[name]
                assert stored['binding'] is binding and stored['outputs'] is result[0]
                assert stored['proved'] is result[1]
                assert stored['pending_id'] == kwargs['pending_id']
                assert stored['allow_pending'] is False
                self.receipt_records.append(exact_output(dict(run_id=self.case.cold_id,
                    reader_key=reader.key, proof_index=index, result=result,
                    binding_is_original=True, binding_audit_fingerprint=binding['audit_fingerprint'],
                    stored_receipt_fields=dict(outputs=stored['outputs'], proved=stored['proved'],
                        pending_id=stored['pending_id'], allow_pending=stored['allow_pending']))))
            return result

        def clock_sample():
            at = sampled()  # Exactly the original call, no second clock sample.
            frame = sys._getframe(1)
            if self.active and frame.f_code is original_context_code:
                deadlines = frame.f_locals['deadlines']
                guard = frame.f_locals['guard']
                assert type(deadlines) is tuple
                # time.time is the RHS of `not stop.is_set() and ...` here:
                # reaching this call proves that original stop test passed.
                self.final_samples.append(dict(at=at, deadlines=deadlines,
                    original_stop_operand_passed=True, scope_inactive=not guard.active))
            return at

        patch.setattr(spec, '_cold_receipts', receipt)
        patch.setattr(runtime.time, 'time', clock_sample)


def test_final_frozen_source_two_complete_normal_chains(tmp_path, monkeypatch):
    clock = SemanticClock(monkeypatch)
    cap = MockCap(monkeypatch)
    # Narrow existing test-only limits BEFORE any prefix or Mock invocation.
    cap.exchange_limit, cap.method_limit = 7, 9
    before_threads = set(threading.enumerate())
    with monkeypatch.context() as patch:
        template = build_prefix(tmp_path / 'prefix', patch, clock, cap)
    results, observations = {}, []
    for name, old in (('old-double-pin', True), ('final-candidate', False)):
        with monkeypatch.context() as patch:
            clock.healthy()
            counter = iter(range(1_000_000, 1_100_000))
            patch.setattr(uuid, 'uuid4', lambda counter=counter: uuid.UUID(int=next(counter)))
            case = restore_case(template, tmp_path / name, patch, clock)
            case.cold_id = template.cold_id
            cap.new_case()
            observer = PairObservation(case, clock)
            if old:
                patch.setattr(runtime._base_segments, 'eligible', lambda trial: False)
            observer.install(patch)
            event.listen(case.store.engine, 'before_cursor_execute', observer.before_sql)
            try:
                worker = case.factory(case.store, case.data[1],
                    goal_planner_transport=apps.transport([], apps.COLD))
                with pytest.raises(TailStop) as stopped:
                    worker.once()
                assert stopped.value.original is observer.original_error is None
                assert cap.case_exchanges == cap.case_methods == 1
                assert observer.prepared and observer.receipts and observer.scope_returned
                assert observer.commits == ['commit:first', 'commit:second']
                assert observer.trial is not None and not observer.trial.guard.active
                assert not observer.trial.accounted_prewrite.active
                assert len(observer.receipt_records) == len(observer.final_samples) == 1
                final = observer.final_samples[0]
                assert final['scope_inactive'] and final['at'] < min(final['deadlines'])
                assert exact_output(final['deadlines']) == exact_output(observer.outputs[-1]['deadlines'])
                with case.store.tx() as c:
                    rows = c.execute(select(attempts).where(attempts.c.run_id == case.cold_id)).mappings().all()
                    assert len(rows) == 1 and rows[0]['status'] == 'RECEIVED'
                report = observer.report()
                report.update(exact_cold_receipt=observer.receipt_records,
                    original_final_clock_sample=observer.final_samples,
                    attempts_preserved_before_w5='RECEIVED')
                results[name] = report
                for filename, value in (
                    ('complete-original-outputs.json', exact_output(observer.outputs)),
                    ('complete-sql-and-parameters.json', exact_output(observer.sql)),
                    ('exact-cold-receipt.json', observer.receipt_records),
                    ('original-final-clock-sample.json', exact_output(observer.final_samples)),
                    ('tail-result.json', report),
                ):
                    (case.root / filename).write_text(json.dumps(value, ensure_ascii=False))
                observations.append(observer)
            finally:
                event.remove(case.store.engine, 'before_cursor_execute', observer.before_sql)
                close_case(case, clock)
    left, right = observations
    assert exact_output(left.outputs) == exact_output(right.outputs)
    assert exact_output(left.sql) == exact_output(right.sql)
    assert left.receipt_records == right.receipt_records
    assert exact_output(left.final_samples) == exact_output(right.final_samples)
    assert left.required_rows == right.required_rows
    assert left.base_calls == right.base_calls
    assert left.base_returned == right.base_returned
    assert left.base_rejected == right.base_rejected == 1
    assert left.base_dynamic_checks == right.base_dynamic_checks == 2 * right.base_returned + 1
    assert left.base_qualified == 0 and right.base_qualified > 0
    # No expected old benefit is inherited: these are this execution's totals.
    assert left.codec_calls > 0 and right.codec_calls > 0
    assert hashlib.sha256(template.path.read_bytes()).hexdigest() == template.sha256
    assert (cap.exchanges, cap.methods, cap.delegates) == (7, 9, 2)
    assert not any(thread.is_alive() for thread in threading.enumerate() if thread not in before_threads)
    (tmp_path / 'final-frozen-pair.json').write_text(json.dumps(dict(
        classification='FINAL_FROZEN_CONFIGURED_SYNTHETIC_VIRTUAL_CLOCK_NOT_REAL_G0',
        product_commit='6ae62ae20ecff3550001c746ebb88af5d340713b', reports=results,
        shared_prefix=dict(template_sha256=template.sha256, source_receipt=template.prefix_receipt),
        exact_outputs_equal=True, exact_sql_and_parameters_equal=True,
        exact_cold_receipts_equal=True, original_final_clock_and_deadlines_equal=True,
        context_business_fingerprints_equal=(left.report()['context_business_fingerprints']
            == right.report()['context_business_fingerprints']),
        source_business_fingerprints_equal=(left.report()['source_business_fingerprints']
            == right.report()['source_business_fingerprints']),
        suite_mock_cap=dict(exchanges=7, methods=9), actual_mock_exchanges=cap.exchanges,
        actual_mock_methods=cap.methods, source_delegates=cap.delegates,
        cleanup_threads_empty=True, real_models=0, w5_entered=False, cold2=False,
        exact_receipt_digests=[fingerprint(item.receipt_records) for item in observations]),
        ensure_ascii=False, indent=2))
