"""One bounded synthetic old/new vertical C1 pair, through five writes/tail.

Business time is explicitly virtual; this is NOT a real-clock G0 window.
At most seven Mock exchanges/nine entries; no Cold2, browser or real transport.
"""

import copy
import hashlib
import json
import threading
import time
import uuid
from contextlib import contextmanager

import pytest
import test_natural_spec_apps as apps
from cold_configured_tail_fixture import MockCap, build_prefix, close_case, config, restore_case
from cold_semantic_clock import SemanticClock
from sqlalchemy import event, select
from test_cold_configured_semantic_tail import TailStop, exact_output

from sim2act import natural_spec_runtime as runtime
from sim2act._cold_producer_segment import _ProducerSegment
from sim2act.db import attempts, operations


def test_complete_vertical_old_candidate_pair(tmp_path, monkeypatch):
    clock = SemanticClock(monkeypatch)
    cap = MockCap(monkeypatch)
    cap.exchange_limit, cap.method_limit = 7, 9
    threads_before = set(threading.enumerate())
    with monkeypatch.context() as patch:
        template = build_prefix(tmp_path / 'prefix', patch, clock, cap)
    reports = []
    for enabled in (False, True):
        name = 'candidate' if enabled else 'old'
        with monkeypatch.context() as patch:
            ids = iter(range(1_000_000, 1_100_000))
            patch.setattr(uuid, 'uuid4', lambda ids=ids: uuid.UUID(int=next(ids)))
            case = restore_case(template, tmp_path / name, patch, clock)
            cap.new_case()
            state = {'active': False, 'normal_pre': False, 'normal_post': False}
            modes, sql, outputs = [], [], []
            scope = runtime._cold_graph_read
            before = runtime._cold_model_before
            after = runtime._model_settlement_read
            advance = runtime.advance_model
            encode = runtime._cold_graph_bytes
            codec = [0, 0]

            @contextmanager
            def scoped(*args, scope=scope, enabled=enabled, modes=modes, **kwargs):
                with scope(*args, **kwargs) as graph:
                    if enabled:
                        modes.append(_ProducerSegment(graph))
                    yield graph

            @contextmanager
            def selected(worker, c, current, inputs, platform, *,
                         state=state, before=before, outputs=outputs):
                assert current['id'] == template.cold_id
                state.update(active=True, cpu_start=time.thread_time(), wall_start=time.monotonic())
                with before(worker, c, current, inputs, platform,
                            _mock_accounted_config=config()) as trial:
                    yield trial
                assert not trial.guard.active and not trial.accounted_prewrite.active
                outputs.extend(copy.deepcopy(trial.guard.inputs[f'commit:{key}:trial-output'])
                               for key in ('first', 'second'))
                state['normal_pre'] = True

            @contextmanager
            def settled(*args, after=after, state=state, **kwargs):
                with after(*args, **kwargs) as result:
                    proof = result[2]
                    assert proof is not None and proof.state == 'READY'
                    yield result
                assert proof.state == 'CLOSED' and not proof.active
                state['normal_post'] = True

            def advanced(*args, advance=advance, state=state, **kwargs):
                result = advance(*args, **kwargs)
                if state['normal_post']:
                    state.update(active=False, cpu=time.thread_time()-state['cpu_start'],
                                 wall=time.monotonic()-state['wall_start'])
                    assert state['normal_pre'] and result is True
                    # The original transaction has COMMITTED before this return.
                    # Stop before a second Cold exchange, not before five writes.
                    raise TailStop()
                return result

            def encoded(value, encode=encode, state=state, codec=codec):
                raw = encode(value)
                if state['active'] and threading.current_thread() is threading.main_thread():
                    codec[0] += 1
                    codec[1] += len(raw)
                return raw

            def executed(c, cursor, statement, parameters, context, executemany,
                         state=state, sql=sql):
                if state['active'] and threading.current_thread() is threading.main_thread():
                    sql.append((statement, copy.deepcopy(parameters)))

            patch.setattr(runtime, '_cold_graph_read', scoped)
            patch.setattr(runtime, '_cold_model_before', selected)
            patch.setattr(runtime, '_model_settlement_read', settled)
            patch.setattr(runtime, 'advance_model', advanced)
            patch.setattr(runtime, '_cold_graph_bytes', encoded)
            event.listen(case.store.engine, 'before_cursor_execute', executed)
            try:
                worker = case.factory(case.store, case.data[1],
                                      goal_planner_transport=apps.transport([], apps.COLD))
                with pytest.raises(TailStop):
                    worker.once()
                assert state['normal_pre'] and state['normal_post'] and not state['active']
                assert (cap.case_exchanges, cap.case_methods) == (1, 1)
                with case.store.tx() as c:
                    rows = [dict(r) for r in c.execute(select(attempts)
                        .where(attempts.c.run_id == template.cold_id)).mappings()]
                    ops = [dict(r) for r in c.execute(select(operations)
                        .where(operations.c.run_id == template.cold_id)
                        .order_by(operations.c.id)).mappings()]
                assert len(rows) == 1 and rows[0]['status'] == 'VERIFIED'
                assert any(op['status'] == 'VERIFIED' and op['receipt'] is not None for op in ops)
                report = dict(name=name, owner_cpu=state['cpu'], wall=state['wall'],
                    codec_calls=codec[0], codec_bytes=codec[1],
                    outputs=exact_output(outputs), sql=exact_output(sql),
                    attempts=exact_output(rows), operations=exact_output(ops),
                    scopes=[dict(phase=m.phase, qualified=m.qualified,
                                 fallback=m.fallback, active=m.graph.active) for m in modes],
                    normal_pre=state['normal_pre'], normal_post=state['normal_post'],
                    writes=sum(s.lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE'))
                               for s, _ in sql),
                    mock_exchanges=cap.case_exchanges, mock_entries=cap.case_methods)
                reports.append(report)
                (tmp_path / (name + '.json')).write_text(json.dumps(report))
            finally:
                state['active'] = False
                event.remove(case.store.engine, 'before_cursor_execute', executed)
                close_case(case, clock)
    old, candidate = reports
    assert all(candidate[key] == old[key] for key in
               ('outputs', 'sql', 'attempts', 'operations', 'writes'))
    assert candidate['writes'] >= 5
    assert sum(m['qualified'] for m in candidate['scopes']) > 0
    assert all(not m['active'] for m in candidate['scopes'])
    assert (cap.exchanges, cap.methods) == (7, 9)
    assert hashlib.sha256(template.path.read_bytes()).hexdigest() == template.sha256
    assert not any(t.is_alive() for t in threading.enumerate() if t not in threads_before)
    (tmp_path / 'summary.json').write_text(json.dumps(dict(
        classification='CONFIGURED_VIRTUAL_BUSINESS_CLOCK_NOT_G0',
        cpu_ratio=candidate['owner_cpu']/old['owner_cpu'],
        wall_ratio=candidate['wall']/old['wall'],
        codec_difference=candidate['codec_calls']-old['codec_calls'],
        exact_outputs_sql_receipts_equal=True, mocks=cap.exchanges, entries=cap.methods,
        new_real_models=0, cleanup_threads_empty=True, cold2=False)))
