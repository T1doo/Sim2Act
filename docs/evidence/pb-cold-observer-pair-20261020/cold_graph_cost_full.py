"""Opt-in passive full-PB cost observer. No new product reads/codec/hash calls.

Load only for a deliberately authorized test with ``-p cold_graph_cost_full``.
This module imports only stdlib until pytest_configure/install_current is called.
It never starts a Worker, HTTP request, model, fixture, account probe or test.
"""
from contextlib import contextmanager
from functools import wraps
import json
import os
from pathlib import Path
import sys
import threading
import time


OUTSIDE = 'OTHER'
PHASES = ('G0', 'W5', 'G1', 'finalguard')


class CostObserver:
    def __init__(self, folder, nodeid='stdlib-selftest'):
        self.folder = Path(folder)
        self.nodeid = nodeid
        self.local = threading.local()
        self.lock = threading.RLock()
        self.saved = []
        self.active = False
        self.started = time.monotonic()
        self.result = dict(
            classification='PASSIVE_OBSERVER_NOT_PRODUCT_OR_LIVE_EVIDENCE',
            nodeid=nodeid, scope='Actual loaded test call only; no fixture/test is started by this observer',
            metrics={}, phases={}, sql={}, returned_bytes={}, hash_inputs={},
            measured_labels=[], alias_bindings=[],
            verifier_calls={}, chain_calls=[], mock_calls=[], phase_transitions=[],
            secondary_observer_errors=[], installation=[], restoration=[],
            limits=dict(extra_product_db_reads=0, extra_product_serializations=0,
                        extra_product_hashes=0, product_return_objects_replaced=0),
            timing_definition='Thread CPU and wall inclusive; exclusive subtracts immediate instrumented child bodies only. Probe overhead remains.',
            hash_coverage='Actual hashlib.sha256 constructor input only; returned hash object unchanged. No proxy/update/hexdigest interception.',
        )
        self.row_type = None
        self.late_alias_targets = []

    def state(self):
        if not hasattr(self.local, 'state'):
            self.local.state = dict(stack=[], phase=OUTSIDE, phase_wall=time.monotonic(),
                                    phase_cpu=time.thread_time(), settlement=None,
                                    dispatch=None, mock_depth=0, settle_stack=[])
        return self.local.state

    def secondary(self, where, error):
        try:
            with self.lock:
                self.result['secondary_observer_errors'].append(
                    dict(where=where, type=type(error).__name__, message=str(error)))
        except BaseException:
            pass

    def observe(self, where, callback, *args):
        try:
            return callback(*args)
        except BaseException as error:
            self.secondary(where, error)
            return None

    def scalar(self, row, key):
        if type(row) is dict or (self.row_type is not None and type(row) is self.row_type):
            result = row.get(key)
            return result if type(result) in (str, int, float, bool, type(None)) else None
        return None

    def stage(self, worker, run):
        # Fixed scalar metadata already present on actual call arguments. No
        # model_dump, repr, dict(row), JSON decode, resource read or query.
        if worker is None or not (type(run) is dict or (self.row_type is not None and type(run) is self.row_type)):
            return 'UNCLASSIFIED'
        binding = getattr(worker, 'pa_trial', None)
        contract = getattr(binding, 'contract', None)
        if contract is None:
            return 'UNCLASSIFIED'
        if run.get('runtime_id') == contract.runtime_id:
            return 'generate'
        refs = run.get('resource_refs')
        if type(refs) is list and len(refs) == 1:
            if refs[0] == contract.bindings[0].resource_id:
                return 'source'
            if refs[0] == contract.bindings[1].resource_id:
                return 'cold'
        return 'UNCLASSIFIED'

    def phase(self, phase, boundary):
        state = self.state()
        wall, cpu = time.monotonic(), time.thread_time()
        prior = state['phase']
        with self.lock:
            item = self.result['phases'].setdefault(prior, dict(segments=0, wall=0.0, thread_cpu=0.0))
            item['segments'] += 1
            item['wall'] += wall - state['phase_wall']
            item['thread_cpu'] += cpu - state['phase_cpu']
            self.result['phase_transitions'].append(dict(
                thread=threading.get_ident(), wall=wall - self.started,
                previous=prior, phase=phase, boundary=boundary,
                completed_phase_elapsed_wall=wall - state['phase_wall'],
                completed_phase_elapsed_thread_cpu=cpu - state['phase_cpu'],
                parent_settlement_aid=(state['settlement'] or {}).get('aid')))
        state.update(phase=phase, phase_wall=wall, phase_cpu=cpu)

    def patch(self, target, name, replacement):
        original = getattr(target, name)  # Fail installation if this exact edge changed.
        self.saved.append((target, name, original, replacement))
        setattr(target, name, replacement)
        self.result['installation'].append(getattr(target, '__name__', type(target).__name__) + '.' + name)

    def measured(self, target, name, label, *, byte_return=False, hash_input=False, verifier=False):
        original = getattr(target, name)
        self.result['measured_labels'].append(dict(label=label, byte_return=byte_return,
                                                  hash_input=hash_input, verifier=verifier))
        @wraps(original)
        def call(*args, **kwargs):
            if not self.active:
                return original(*args, **kwargs)
            state = self.state()
            parent = state['stack'][-1] if state['stack'] else None
            frame = dict(label=label, child_wall=0.0, child_cpu=0.0)
            phase = state['phase']
            recursive = any(f['label'] == label for f in state['stack'])
            state['stack'].append(frame)
            start, cpu = time.monotonic(), time.thread_time()
            returned = None
            did_return = False
            try:
                returned = original(*args, **kwargs)
                did_return = True
                return returned  # Preserve identity, including bytes and HASH objects.
            finally:
                elapsed, elapsed_cpu = time.monotonic() - start, time.thread_time() - cpu
                def record():
                    state['stack'].pop()
                    if parent is not None:
                        parent['child_wall'] += elapsed
                        parent['child_cpu'] += elapsed_cpu
                    with self.lock:
                        key = phase + '::' + label
                        metric = self.result['metrics'].setdefault(key, dict(
                            count=0, recursive_reentries=0, returned=0, exceptions=0,
                            wall_inclusive=0.0, cpu_inclusive=0.0,
                            wall_instrumented_child_exclusive=0.0, cpu_instrumented_child_exclusive=0.0))
                        metric['count'] += 1
                        metric['recursive_reentries'] += int(recursive)
                        metric['returned'] += int(did_return)
                        metric['exceptions'] += int(not did_return)
                        metric['wall_inclusive'] += elapsed
                        metric['cpu_inclusive'] += elapsed_cpu
                        metric['wall_instrumented_child_exclusive'] += elapsed - frame['child_wall']
                        metric['cpu_instrumented_child_exclusive'] += elapsed_cpu - frame['child_cpu']
                        if verifier:
                            self.result['verifier_calls'][key] = self.result['verifier_calls'].get(key, 0) + 1
                        if byte_return and did_return:
                            count = self.result['returned_bytes'].setdefault(key, dict(calls=0, bytes=0, non_bytes=0))
                            count['calls'] += 1
                            if type(returned) is bytes:
                                count['bytes'] += len(returned)  # Tap only the original returned bytes.
                            else:
                                count['non_bytes'] += 1
                        if hash_input:
                            data = args[0] if args else kwargs.get('string', kwargs.get('data', b''))
                            labels = [f['label'] for f in state['stack']]
                            category = next((x for x in reversed(labels) if x in {
                                'cgr.input_key', 'cgr.validate_codec', 'model._model_inputs',
                                'model.binding_key', 'codec.inputs'}), 'other')
                            bucket = self.result['hash_inputs'].setdefault(phase + '::' + category,
                                dict(calls=0, bytes=0, unknown_buffer_calls=0,
                                     wall_inclusive=0.0, cpu_inclusive=0.0,
                                     wall_instrumented_child_exclusive=0.0,
                                     cpu_instrumented_child_exclusive=0.0))
                            bucket['calls'] += 1
                            bucket['wall_inclusive'] += elapsed
                            bucket['cpu_inclusive'] += elapsed_cpu
                            bucket['wall_instrumented_child_exclusive'] += elapsed - frame['child_wall']
                            bucket['cpu_instrumented_child_exclusive'] += elapsed_cpu - frame['child_cpu']
                            if type(data) in (bytes, bytearray):
                                bucket['bytes'] += len(data)
                            elif type(data) is memoryview:
                                bucket['bytes'] += data.nbytes
                            else:
                                bucket['unknown_buffer_calls'] += 1
                self.observe('metric-finally:' + label, record)
        self.patch(target, name, call)

    def model_contexts(self, runtime):
        original_before = runtime._cold_model_before
        @wraps(original_before)
        @contextmanager
        def before(worker, c, current, inputs, platform):
            if not self.active or self.stage(worker, current) != 'cold':
                with original_before(worker, c, current, inputs, platform) as result:
                    yield result
                return
            state = self.state()
            state['settlement'] = dict(aid=self.scalar(inputs, 'aid'), run_id=self.scalar(current, 'id'))
            self.observe('G0-enter', self.phase, 'G0', '_cold_model_before.enter')
            succeeded = False
            try:
                with original_before(worker, c, current, inputs, platform) as result:
                    yield result
                succeeded = True
            finally:
                self.observe('G0-exit', self.phase, 'W5' if succeeded else OUTSIDE,
                             '_cold_model_before.exit' if succeeded else '_cold_model_before.exception')
        self.patch(runtime, '_cold_model_before', before)

        original_after = runtime._model_settlement_read
        @wraps(original_after)
        @contextmanager
        def after(worker, c, inputs):
            current = inputs.get('current') if type(inputs) is dict else None
            if not self.active or self.stage(worker, current) != 'cold':
                with original_after(worker, c, inputs) as result:
                    yield result
                return
            self.state()['settlement'] = dict(aid=self.scalar(inputs, 'aid'), run_id=self.scalar(current, 'id'))
            self.observe('G1-enter', self.phase, 'G1', '_model_settlement_read.enter')
            try:
                with original_after(worker, c, inputs) as result:
                    self.observe('finalguard-enter', self.phase, 'finalguard', '_model_settlement_read.yield')
                    yield result
            finally:
                self.observe('finalguard-exit', self.phase, OUTSIDE, '_model_settlement_read.exit')
        self.patch(runtime, '_model_settlement_read', after)

        original_advance = runtime.advance_model
        @wraps(original_advance)
        def advance(*args, **kwargs):
            if not self.active:
                return original_advance(*args, **kwargs)
            try:
                return original_advance(*args, **kwargs)
            finally:
                self.observe('advance-finally', self.phase, OUTSIDE, 'advance_model.exit')
                self.state()['settlement'] = None
        self.patch(runtime, 'advance_model', advance)

    def journal(self, dispatch, runtime):
        for name, aid_position, run_position in [('_journal_chain', 4, 3), ('_graph_journal_chain', 5, 4)]:
            original = getattr(dispatch, name)
            def factory(original, name, aid_position, run_position):
                @wraps(original)
                def chain(*args, **kwargs):
                    if self.active:
                        def record():
                            state = self.state()
                            aid = args[aid_position] if len(args) > aid_position else kwargs.get('aid')
                            run = args[run_position] if len(args) > run_position else kwargs.get('run')
                            parent = state['settlement'] or {}
                            with self.lock:
                                self.result['chain_calls'].append(dict(
                                    function=name, phase=state['phase'], aid_argument_index=aid_position,
                                    actual_aid=aid if type(aid) is str else None,
                                    run_id=self.scalar(run, 'id'), parent_settlement_aid=parent.get('aid'),
                                    parent_settlement_run_id=parent.get('run_id'),
                                    nearest_settle_verified_aid=state['settle_stack'][-1] if state['settle_stack'] else None,
                                    matches_parent=(aid == parent.get('aid'))
                                        if type(aid) is str and type(parent.get('aid')) is str else None))
                        self.observe('journal-args:' + name, record)
                    return original(*args, **kwargs)
                return chain
            self.patch(dispatch, name, factory(original, name, aid_position, run_position))

        original_settle = dispatch.settle_verified
        @wraps(original_settle)
        def settle(*args, **kwargs):
            if not self.active:
                return original_settle(*args, **kwargs)
            state = self.state()
            aid = args[3] if len(args) > 3 else kwargs.get('aid')
            state['settle_stack'].append(aid if type(aid) is str else None)
            try:
                return original_settle(*args, **kwargs)
            finally:
                self.observe('settle-verified-pop', state['settle_stack'].pop)
        self.patch(dispatch, 'settle_verified', settle)

    def mock(self, dispatch, mock_type):
        original_exchange = dispatch._journal_exchange
        @wraps(original_exchange)
        def exchange(worker, run, aid, *args, **kwargs):
            if not self.active:
                return original_exchange(worker, run, aid, *args, **kwargs)
            state = self.state()
            previous = state['dispatch']
            state['dispatch'] = dict(stage=self.stage(worker, run), run_id=self.scalar(run, 'id'), aid=aid)
            try:
                return original_exchange(worker, run, aid, *args, **kwargs)
            finally:
                state['dispatch'] = previous
        self.patch(dispatch, '_journal_exchange', exchange)

        def entered(kind):
            state = self.state()
            outer = state['mock_depth'] == 0
            state['mock_depth'] += 1
            return state, outer
        def left(state, outer, kind, did_return, response):
            state['mock_depth'] -= 1
            if outer:
                context = state['dispatch'] or {}
                with self.lock:
                    self.result['mock_calls'].append(dict(
                        stage=context.get('stage', 'UNCLASSIFIED'), run_id=context.get('run_id'),
                        aid=context.get('aid'), transport=kind, did_return=did_return,
                        response_status=getattr(response, 'status_code', None) if did_return else None,
                        phase=state['phase']))
        for name, asynchronous in [('handle_request', False), ('handle_async_request', True)]:
            original = getattr(mock_type, name)
            def factory(original, name, asynchronous):
                if asynchronous:
                    @wraps(original)
                    async def call(*args, **kwargs):
                        if not self.active:
                            return await original(*args, **kwargs)
                        state, outer = entered(name)
                        response, did_return = None, False
                        try:
                            response = await original(*args, **kwargs)
                            did_return = True
                            return response
                        finally:
                            self.observe('mock-finally:' + name, left, state, outer, name, did_return, response)
                else:
                    @wraps(original)
                    def call(*args, **kwargs):
                        if not self.active:
                            return original(*args, **kwargs)
                        state, outer = entered(name)
                        response, did_return = None, False
                        try:
                            response = original(*args, **kwargs)
                            did_return = True
                            return response
                        finally:
                            self.observe('mock-finally:' + name, left, state, outer, name, did_return, response)
                return call
            self.patch(mock_type, name, factory(original, name, asynchronous))

    def sql(self, conn, cursor, statement, parameters, context, executemany):
        if self.active:
            def record():
                op = statement.lstrip().split(None, 1)[0].upper() if statement.strip() else 'EMPTY'
                key = self.state()['phase'] + '::' + op
                with self.lock:
                    self.result['sql'][key] = self.result['sql'].get(key, 0) + 1
            self.observe('sql-count', record)

    def install_current(self):
        import hashlib
        import httpx
        from sqlalchemy import event
        from sqlalchemy.engine import Engine, RowMapping
        from sim2act import app_jobs, apps, goal_applications as ga, lifecycle, text_apps
        from sim2act import natural_spec_runtime as runtime
        from sim2act import pa_spec_apps as spec, pa_trial_dispatch as dispatch
        from sim2act import pb_natural_specs as pb, pb_natural_uses as use
        self.row_type = RowMapping
        self.model_contexts(runtime)
        self.journal(dispatch, runtime)
        self.mock(dispatch, httpx.MockTransport)
        for target, name, label, byte_return in [
            (runtime._ColdGraphRead, 'check', 'cgr.check', False),
            (runtime._ColdGraphRead, 'input_key', 'cgr.input_key', False),
            (runtime._ColdGraphRead, 'input_bytes', 'cgr.input_bytes', True),
            (runtime, '_cold_graph_bytes', 'codec.bytes', True),
            (runtime, '_cold_graph_validate_inputs', 'cgr.validate_codec', False),
            (runtime, '_cold_graph_inputs', 'codec.inputs', False),
            (runtime, '_model_inputs', 'model._model_inputs', False),
            (runtime._ModelSettlementRead, 'check', 'model.check', False),
            (runtime._ModelSettlementRead, 'binding_key', 'model.binding_key', False),
            (runtime, '_cold_first_binding', 'cold.first_binding', False),
            (runtime, '_cold_binding_limits_facet', 'cold.limits_facet', False),
            (runtime, '_cold_audit_seed', 'cold.audit_seed', False),
        ]:
            self.measured(target, name, label, byte_return=byte_return)
        # Count and time actual recursive entry, rather than prohibiting or
        # replacing any verifier in the full product test.
        for target, names in [
            (ga, ('source', 'initial_messages', 'history', '_history', 'verified_candidate', '_verified_candidate', 'parse_candidate')),
            (spec, ('bound', '_bound', 'verify_job', 'receipts', 'verify_origin', 'model_source', 'audit_fingerprint', 'from_response')),
            (pb, ('source', '_source', 'source_audit', '_source_audit', 'review', 'verify', 'audit_fingerprint')),
            (use, ('bound', 'review', 'audit')),
            (apps, ('validate_frozen_candidate',)), (lifecycle, ('read_release', '_read_release')),
            (app_jobs, ('load_binding',)), (text_apps, ('verify_origin',)),
        ]:
            for name in names:
                self.measured(target, name, target.__name__ + '.' + name, verifier=True)
        self.bind_prebound_aliases(apps, lifecycle, app_jobs)
        self.measured(hashlib, 'sha256', 'hash.sha256_constructor', hash_input=True)
        event.listen(Engine, 'before_cursor_execute', self.sql)
        self.sql_remove = lambda: event.remove(Engine, 'before_cursor_execute', self.sql)
        self.active = True

    def bind_prebound_aliases(self, apps, lifecycle, app_jobs):
        # These exact current-source top-level imports predate observer install.
        # Bind to the SAME canonical observer wrapper, not another timer wrapper,
        # so the original callee runs once and its public entry is counted once.
        specs = [
            ('sim2act.lifecycle', 'validate_frozen_candidate', apps, 'validate_frozen_candidate'),
            ('sim2act.app_jobs', 'validate_frozen_candidate', apps, 'validate_frozen_candidate'),
            ('sim2act.app_jobs', 'read_release', lifecycle, 'read_release'),
            ('sim2act.registered_run_extraction', 'read_release', lifecycle, 'read_release'),
        ]
        for module_name, name, canonical, canonical_name in specs:
            wrapper = getattr(canonical, canonical_name)
            original = next(original for target, method, original, wrapped in reversed(self.saved)
                if target is canonical and method == canonical_name and wrapped is wrapper)
            owner = sys.modules.get(module_name)
            if owner is None:
                state = 'NOT_LOADED_FUTURE_IMPORT_USES_WRAPPED_CANONICAL'
                self.late_alias_targets.append((module_name, name, original, wrapper))
            elif getattr(owner, name) is original:
                self.patch(owner, name, wrapper)
                state = 'BOUND_TO_SAME_CANONICAL_WRAPPER'
            elif getattr(owner, name) is wrapper:
                state = 'ALREADY_CANONICAL_WRAPPER'
            else:
                # Do not overwrite a foreign/test replacement or invent a call.
                state = 'CURRENT_DIFFERENT_NOT_OVERWRITTEN'
            self.result['alias_bindings'].append(dict(module=module_name, name=name,
                canonical=canonical.__name__ + '.' + canonical_name, result=state))

    def finish_call(self, error=None):
        self.observe('finish-phase', self.phase, OUTSIDE, 'pytest.call.exit')
        self.active = False
        self.result['call_outcome'] = 'RAISED' if error is not None else 'RETURNED'
        self.result['primary_exception_type'] = type(error).__name__ if error is not None else None
        self.result['elapsed_wall'] = time.monotonic() - self.started
        counts = {}
        for item in self.result['mock_calls']:
            stage = item['stage']
            counts[stage] = counts.get(stage, 0) + 1
        self.result['actual_outer_mock_stage_counts'] = counts
        self.result['expected_full_pb_stage_counts_for_review_only'] = dict(generate=3, source=2, cold=2)
        aids = [r['aid'] for r in self.result['mock_calls'] if r['aid'] is not None]
        self.result['duplicate_outer_mock_aids'] = sorted({aid for aid in aids if aids.count(aid) > 1})
        for description in self.result['measured_labels']:
            for phase in (*PHASES, OUTSIDE):
                key = phase + '::' + description['label']
                self.result['metrics'].setdefault(key, dict(
                    count=0, recursive_reentries=0, returned=0, exceptions=0,
                    wall_inclusive=0.0, cpu_inclusive=0.0,
                    wall_instrumented_child_exclusive=0.0, cpu_instrumented_child_exclusive=0.0))
                if description['verifier']:
                    self.result['verifier_calls'].setdefault(key, 0)
        self.write()

    def restore(self):
        self.active = False
        if hasattr(self, 'sql_remove'):
            self.observe('sql-listener-remove', self.sql_remove)
        # A module imported during the call may have captured the already
        # wrapped canonical function; restore that alias after fixture teardown.
        for module_name, name, original, wrapper in self.late_alias_targets:
            owner = sys.modules.get(module_name)
            if owner is not None and getattr(owner, name) is wrapper:
                setattr(owner, name, original)
                self.result['restoration'].append(dict(target=module_name + '.' + name,
                    result='RESTORED_LATE_IMPORT_ALIAS'))
        for target, name, original, wrapper in reversed(self.saved):
            if getattr(target, name) is wrapper:
                setattr(target, name, original)
                state = 'RESTORED'
            else:
                state = 'CURRENT_DIFFERENT_NOT_OVERWRITTEN'
            self.result['restoration'].append(dict(target=getattr(target, '__name__', type(target).__name__) + '.' + name,
                                                   result=state))
        self.write()

    def write(self):
        # Only the observer's own scalar counters/records are serialized, after
        # the test call. Never serialize/hash product inputs for observation.
        self.folder.mkdir(parents=True, exist_ok=True)
        (self.folder / 'full-pb-cost.json').write_text(json.dumps(self.result, indent=2) + '\n')


def pytest_configure(config):
    # Deliberately lazy: stdlib fake-object selftests import no third-party module.
    import pytest
    directory = os.environ.get('COLD_GRAPH_METRICS_DIR')
    if not directory:
        raise RuntimeError('Opt-in observer requires an explicit COLD_GRAPH_METRICS_DIR')
    selected = os.environ.get('COLD_GRAPH_METRICS_NODE',
        'test_pb_production_original_source_extraction_explicit_use_and_cold')

    class Hooks:
        observer = None
        @pytest.hookimpl(wrapper=True, tryfirst=True)
        def pytest_runtest_call(self, item):
            if selected not in item.nodeid:
                return (yield)
            observer = self.observer = CostObserver(directory, item.nodeid)
            error = None
            try:
                observer.install_current()
                return (yield)
            except BaseException as exc:
                error = exc
                raise
            finally:
                observer.observe('finish-call-evidence', observer.finish_call, error)

        @pytest.hookimpl(wrapper=True, tryfirst=True)
        def pytest_runtest_teardown(self, item, nextitem):
            try:
                return (yield)
            finally:
                if self.observer is not None:
                    observer = self.observer
                    self.observer = None
                    observer.observe('restore-and-evidence', observer.restore)
    config.pluginmanager.register(Hooks(), 'passive-full-pb-cost-observer')
