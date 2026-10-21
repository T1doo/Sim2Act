"""Local wiring only: no prefix, full prepare/commit, Worker, Mock or G0 run.

The real CGR/native context is exercised with first-binding/TrialGraph stand-ins.
Those stand-ins do not claim completed business proofs or bypass account gates.
"""

import ast
import importlib.util
import inspect
import time
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from accounted_sqlite_fixture import seed_cold
from test_cold_accounted_cohort import BOUNDS, LIMITS
from test_cold_accounted_sqlite import (
    forbid_execution as forbid_execution,
)
from test_cold_accounted_sqlite import (
    sql_facts as sql_facts,
)

from sim2act import _cold_accounted_native as native
from sim2act import natural_spec_runtime as runtime
from sim2act import pb_natural_specs as pb
from sim2act._cold_accounted_budget import _Capacity
from sim2act.errors import DomainError

ROOT = Path(__file__).resolve().parents[1]


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/diagnostics' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LocalStop(BaseException):
    pass


@pytest.mark.parametrize('selected', [False, True])
def test_real_pre_scope_wires_after_first_binding_and_closes_on_error(sql_facts, monkeypatch, selected):
    f, events, captured = sql_facts, [], {}
    seed_cold(f)
    completed = object()
    config = native._NativeConfig(BOUNDS, LIMITS)

    def first(worker, c, graph, current, platform):
        events.append('first_binding')
        assert graph.active and graph.phase == 'pre' and graph._accounted_frontier is None
        captured['graph'] = graph
        return completed

    original = native._native_candidate

    @contextmanager
    def candidate(graph, supplied):
        events.append('candidate')
        assert events == ['first_binding', 'candidate'] and supplied is config
        with original(graph, supplied) as value:
            captured['candidate'] = value
            yield value

    def trial(worker, c, graph, **kwargs):
        events.append('trial')
        assert kwargs['completed'] is completed
        if selected:
            assert kwargs['_accounted_candidate'] is captured['candidate']
            assert captured['candidate'].graph is graph and captured['candidate'].mode is None
        else:
            assert set(kwargs) == {'completed'} and 'candidate' not in captured
        return SimpleNamespace(guard=graph)

    monkeypatch.setattr(runtime, '_cold_first_binding', first)
    monkeypatch.setattr(runtime, '_ColdTrialGraph', trial)
    monkeypatch.setattr(native, '_native_candidate', candidate)
    options = {'_mock_accounted_config': config} if selected else {}
    with pytest.raises(LocalStop), f.store.tx() as c, pb._source_reads(f.store, c):
        with runtime._cold_model_before(f.worker, c, f.cold_job, {'local_wiring': True},
                                        f.frozen.limits, **options) as graph:
            assert graph.guard is captured['graph'] and graph.guard.active
            raise LocalStop()
    assert events == (['first_binding', 'candidate', 'trial'] if selected else ['first_binding', 'trial'])
    assert not captured['graph'].active
    if selected:
        assert captured['candidate'].completed == {} and captured['candidate'].result is None
        with pytest.raises(DomainError):
            captured['candidate'].stage('source', ())


def test_selection_cannot_supply_missing_second_business_guard(sql_facts, monkeypatch):
    f, captured = sql_facts, {}
    seed_cold(f)
    monkeypatch.setattr(runtime, '_cold_first_binding', lambda *args: object())

    def trial(worker, c, graph, **kwargs):
        captured['graph'] = graph
        return SimpleNamespace(guard=graph, authority_record=None, authority_record_key=None)

    monkeypatch.setattr(runtime, '_ColdTrialGraph', trial)
    with pytest.raises(DomainError, match='Complete second Cold guard'), f.store.tx() as c, pb._source_reads(f.store, c):
        with runtime._cold_model_before(f.worker, c, f.cold_job, {'local_wiring': True},
                f.frozen.limits, _mock_accounted_config=native._NativeConfig(BOUNDS, LIMITS)):
            pass
    assert not captured['graph'].active


@pytest.mark.parametrize('expired', [False, True])
def test_local_exit_shape_retains_original_scope_then_final_deadline(sql_facts, monkeypatch, expired):
    # A local record-shaped stand-in exercises context exit, not a completed
    # commit/authority. No _prepare/commit or accounted issuance is invoked.
    f, events, captured = sql_facts, [], {}
    seed_cold(f)
    original_read, original_candidate = runtime._cold_graph_read, native._native_candidate

    @contextmanager
    def read(*args):
        with original_read(*args) as graph:
            captured['graph'] = graph
            yield graph
        assert not graph.active
        events.append('original_scope_closed')

    @contextmanager
    def candidate(graph, config):
        with original_candidate(graph, config) as value:
            yield value
        assert graph.active
        events.append('candidate_exit')

    monkeypatch.setattr(runtime, '_cold_graph_read', read)
    monkeypatch.setattr(native, '_native_candidate', candidate)
    monkeypatch.setattr(runtime, '_cold_first_binding', lambda *args: object())
    monkeypatch.setattr(runtime, '_ColdTrialGraph', lambda worker, c, graph, **kwargs:
                        SimpleNamespace(guard=graph, authority_record=None, authority_record_key=None))

    def exercise(c):
        with runtime._cold_model_before(f.worker, c, f.cold_job, {'local_wiring': True},
                f.frozen.limits, _mock_accounted_config=native._NativeConfig(BOUNDS, LIMITS)) as trial:
            key = 'commit:second:trial-output'
            record = {'deadlines': (1.0 if expired else time.time() + 30,)}
            trial.guard.add(key, record)
            trial.authority_record, trial.authority_record_key = record, key

    with f.store.tx() as c, pb._source_reads(f.store, c):
        if expired:
            with pytest.raises(DomainError, match='expired after closing'):
                exercise(c)
        else:
            exercise(c)
    assert events == ['candidate_exit', 'original_scope_closed']
    assert not captured['graph'].active


@pytest.mark.parametrize('test_only,sqlite', [(False, True), (True, False), (False, False)])
def test_explicit_selection_rejects_non_synthetic_store_before_any_work(test_only, sqlite):
    worker = SimpleNamespace(store=SimpleNamespace(test_only=test_only, sqlite=sqlite))
    with pytest.raises(DomainError, match='test-only SQLite'):
        with runtime._cold_model_before(worker, object(), {}, {}, None,
                _mock_accounted_config=native._NativeConfig(BOUNDS, LIMITS)):
            pytest.fail('ineligible explicit selection yielded')


def test_explicit_selection_rejects_wrong_config_and_wrong_cold_route():
    worker = SimpleNamespace(store=SimpleNamespace(test_only=True, sqlite=True), pa_trial=None)
    with pytest.raises(DomainError, match='test-only SQLite'):
        with runtime._cold_model_before(worker, object(), {}, {}, None, _mock_accounted_config=object()):
            pytest.fail('foreign configuration yielded')
    with pytest.raises(DomainError, match='original PB Cold path'):
        with runtime._cold_model_before(worker, object(), {}, {}, None,
                _mock_accounted_config=native._NativeConfig(BOUNDS, LIMITS)):
            pytest.fail('wrong route yielded')
    with runtime._cold_model_before(worker, object(), {}, {}, None) as result:
        assert result is None


def test_prefix_selects_exact_private_config_without_grant_or_default_activation():
    prefix = script('g0_prefix')
    calls = []
    def original(*args, **kwargs):
        calls.append(kwargs)
        return kwargs
    config = native._NativeConfig(BOUNDS, LIMITS)
    assert prefix._mock_accounted_context(original, None) is original
    selected = prefix._mock_accounted_context(original, config)
    assert calls == []
    assert selected() == {'_mock_accounted_config': config}
    with pytest.raises(ValueError, match='Exact explicit Mock'):
        prefix._mock_accounted_context(original, object())
    assert inspect.signature(prefix.run_prefix).parameters['_mock_accounted_config'].default is None
    assert inspect.signature(runtime._cold_model_before).parameters['_mock_accounted_config'].default is None
    tree = ast.parse((ROOT / 'scripts/diagnostics/g0_bounded.py').read_text())
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == 'run_prefix']
    assert len(calls) == 1 and not calls[0].keywords
    tree = ast.parse((ROOT / 'src/sim2act/natural_spec_runtime.py').read_text())
    post = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_model_settlement_read')
    ctors = [n for n in ast.walk(post) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == '_ColdTrialGraph']
    assert len(ctors) == 1 and [k.arg for k in ctors[0].keywords] == ['audit_seed']


@pytest.mark.parametrize('capacity_error', [False, True])
def test_boundary_selects_only_after_exact_target_checks_with_local_standins(capacity_error):
    guard, prefix = script('g0_guard'), script('g0_prefix')
    events = []

    @contextmanager
    def original(worker, c, current, inputs, platform, **kwargs):
        events.append(('original', kwargs))
        yield object()

    selected = prefix._mock_accounted_context(original, native._NativeConfig(BOUNDS, LIMITS))
    mocks = guard.MockBudget()
    # Pure boundary stand-in state, not actual exchanges or a diagnostic run.
    mocks.exchanges, mocks.methods, mocks.source_sync = 6, 8, 2
    boundary = guard.StopBoundary(DomainError, mocks, lambda event: events.append(event['event']))
    worker = object()
    c = SimpleNamespace(connection=SimpleNamespace(driver_connection=SimpleNamespace(
        arm_g0=lambda: events.append('arm'))))
    current = dict(id='local-target', version=1)
    inputs = dict(call_run=dict(id='local-target'), meta=dict(run_version=1), aid='local-attempt')
    with boundary.wrap(original, worker, c, current, inputs, None, _target_context=selected):
        pass
    assert events == [('original', {})] and not boundary.entered
    boundary.bind(worker, current['id'])
    with boundary.wrap(original, object(), c, current, inputs, None, _target_context=selected):
        pass
    assert events == [('original', {}), ('original', {})]
    with pytest.raises(guard.Boundary, match='unexpected Cold context'):
        with boundary.wrap(original, worker, c, dict(current, id='wrong'), inputs, None,
                           _target_context=selected):
            pytest.fail('invalid target yielded')
    assert not boundary.entered and not mocks.closed and len(events) == 2
    original_error = _Capacity('local-only') if capacity_error else DomainError('VERSION_CONFLICT', 'local body rejection')
    with pytest.raises(guard.G0Stop) as stop:
        with boundary.wrap(original, worker, c, current, inputs, None, _target_context=selected):
            raise original_error
    assert stop.value.original is original_error and mocks.closed
    diagnostic = boundary.diagnostic(stop.value)
    assert diagnostic['classification'] == 'UNKNOWN'
    assert diagnostic['error_origin'] == 'UNDETERMINED_ORIGINAL_OR_CANDIDATE'
    assert 'selected_context_error' in diagnostic and 'original_error' not in diagnostic
    assert events[2:4] == ['g0_enter', 'arm']
    assert events[4][0] == 'original' and set(events[4][1]) == {'_mock_accounted_config'}
