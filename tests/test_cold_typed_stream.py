"""Differential tests of the actual fixed-model bridge; no trial/model run.

The reference is the unchanged pre-streaming four-stage algorithm. Complete
local typed values are used, not a substitute Pickler or fake equality method.
"""

import copy
import json
import random
import time
import tracemalloc

import pytest
from pydantic_core import SchemaSerializer, core_schema
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from sqlalchemy.sql.elements import quoted_name
from test_cold_accounted_native import native_segment
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import sql_facts as sql_facts
from test_cold_binding_fact_leaves import local_origin as local_origin
from test_cold_binding_fact_leaves import no_external_transport as no_external_transport

from sim2act import _cold_typed_stream as stream
from sim2act import natural_live_admission as gate
from sim2act import production_trial_policy as policy
from sim2act.contracts import AppManifest
from sim2act.errors import DomainError


def reference(expected, model, raw):
    actual = gate._trial_typed_storage(expected, model)
    gate.require(type(raw) is dict, 'Complete typed trial raw pin required')
    saved = gate._trial_pure_data(raw)
    gate.require(gate._trial_typed_equal(actual, saved),
        'Typed trial storage changed after its complete raw proof')
    value = expected.model_dump(model, warnings=False)
    gate.require(gate._trial_typed_equal(value, saved),
        'Typed trial fact changed after its complete raw proof')


def outcome(call):
    try:
        call()
    except DomainError as error:
        return error.public()
    return None


def same(model, raw):
    old = outcome(lambda: reference(type(model), model, raw))
    new = outcome(lambda: gate._trial_typed_values([(type(model), model, raw)]))
    assert new == old
    return new


def manifest(f):
    return f.origin[0].model_copy(deep=True)


@pytest.mark.parametrize('damage', [
    'none', 'bool-int', 'int-float', 'list-tuple', 'missing-field', 'extra-field',
    'fields-set', 'extra-storage', 'private-storage', 'typed-cycle', 'raw-cycle',
    'unknown-typed', 'unknown-raw', 'raw-key', 'mixed-errors',
])
def test_complete_header_storage_and_error_order_matches_reference(local_origin, damage):
    model, callbacks = manifest(local_origin), []
    model.input_schema = dict(number=1, sequence=[1, 2], later='ok')
    raw = model.model_dump()

    class Unknown:
        def __eq__(self, other):
            callbacks.append('eq')
            raise AssertionError('foreign equality')

        def __repr__(self):
            callbacks.append('repr')
            raise AssertionError('foreign formatting')

        def __hash__(self):
            callbacks.append('hash')
            return hash('input_schema')

    if damage == 'bool-int':
        model.input_schema['number'] = True
    elif damage == 'int-float':
        model.input_schema['number'] = 1.0
    elif damage == 'list-tuple':
        model.input_schema['sequence'] = (1, 2)
    elif damage == 'missing-field':
        del model.__dict__['revision']
    elif damage == 'extra-field':
        model.__dict__['foreign'] = 1
    elif damage == 'fields-set':
        object.__setattr__(model, '__pydantic_fields_set__', {'foreign'})
    elif damage == 'extra-storage':
        object.__setattr__(model, '__pydantic_extra__', {})
    elif damage == 'private-storage':
        object.__setattr__(model, '__pydantic_private__', {})
    elif damage == 'typed-cycle':
        model.input_schema['cycle'] = model.input_schema
    elif damage == 'raw-cycle':
        raw['input_schema']['cycle'] = raw
    elif damage == 'unknown-typed':
        model.input_schema['later'] = Unknown()
    elif damage == 'unknown-raw':
        raw['input_schema']['later'] = Unknown()
    elif damage == 'raw-key':
        raw = {Unknown(): 0}
        callbacks.clear()
    elif damage == 'mixed-errors':
        # Original actual gate must reject the late actual object before the
        # earlier raw mismatch/unknown has a chance to own the error.
        raw['input_schema']['number'] = Unknown()
        model.input_schema['later'] = Unknown()
    result = same(model, raw)
    assert (result is None) is (damage == 'none')
    assert callbacks == []


@pytest.mark.parametrize('number', [float('nan'), float('inf'), -float('inf'), -0.0, 0.0])
def test_original_nonfinite_and_signed_zero_rules(local_origin, number):
    model = manifest(local_origin)
    model.input_schema = dict(number=number)
    raw = model.model_dump()
    assert (same(model, raw) is None) is (number == number)
    if number == 0:
        raw['input_schema']['number'] = -number
        assert same(model, raw) is None


def test_dag_pair_memo_is_not_an_identity_or_single_node_pass(local_origin):
    model = manifest(local_origin)
    common = {'values': [1, True, (b'complete', None)]}
    model.input_schema = dict(a=common, b=common)
    raw = model.model_dump()
    raw['input_schema']['b'] = copy.deepcopy(raw['input_schema']['a'])
    assert same(model, raw) is None
    # Same actual node vs a distinct, damaged second raw node must be visited.
    raw['input_schema']['b']['values'][0] = True
    assert same(model, raw)['message'] == 'Typed trial storage changed after its complete raw proof'


def test_different_actual_nodes_against_same_raw_dag_are_compared(local_origin):
    model = manifest(local_origin)
    model.input_schema = dict(a=dict(values=[1, True]), b=dict(values=[1, True]))
    raw = model.model_dump()
    raw['input_schema']['b'] = raw['input_schema']['a']
    assert model.input_schema['a'] is not model.input_schema['b']
    assert same(model, raw) is None
    model.input_schema['b']['values'][0] = 2
    assert same(model, raw)['message'] == 'Typed trial storage changed after its complete raw proof'


def test_full_raw_gate_wins_over_early_value_difference(local_origin):
    model = manifest(local_origin)
    model.input_schema = dict(first=1, last=[])
    raw = model.model_dump()
    raw['input_schema']['first'] = 2
    raw['input_schema']['last'].append(raw)
    assert same(model, raw)['message'] == 'Cyclic trial raw data'


def test_rows_and_quoted_keys_keep_original_visible_projection(local_origin):
    model = manifest(local_origin)
    model.input_schema = dict(row=dict(x=1, y=[2, 3]))
    raw = model.model_dump()
    raw['input_schema']['row'] = RowMapping(SimpleResultMetaData(['x', 'y']), None,
        {quoted_name('x', True): 0, 'y': 1}, (1, [2, 3], object()))
    # Hidden storage remains the parent CGR's boundary, just as in the original
    # pure-data projection. This comparison must not invent a new hidden gate.
    assert same(model, raw) is None
    raw['input_schema']['row'] = {quoted_name('x', True): 1, 'y': [2, 3]}
    assert same(model, raw) is None


def test_both_none_omissions_nested_fields_and_random_native_data(local_origin):
    model = manifest(local_origin)
    # This complete original manifest contains WorkflowSteps; their `when=None`
    # omission, nested fixed models and the rest of every field remain checked.
    assert same(model, model.model_dump()) is None
    from sim2act.contracts import BranchCondition, FieldSource
    condition = BranchCondition(op='exists', source=FieldSource(source='input', field='value'))
    # BranchCondition is a nested-only fixed type. Put it into the same actual
    # model storage to exercise its second omission without conferring authority.
    model.input_schema = dict(condition=condition)
    assert same(model, model.model_dump()) is None
    rng = random.Random(5271)
    def data(depth):
        if depth == 0 or rng.randrange(3) == 0:
            return rng.choice((None, True, False, 0, 1, -3, 1.5, '完整\ud800', b'\x00wire'))
        children = [data(depth - 1) for _ in range(rng.randrange(4))]
        shape = rng.randrange(3)
        return (children if shape == 0 else tuple(children) if shape == 1
                else {str(i): value for i, value in enumerate(children)})
    for _ in range(128):
        model.input_schema = dict(value=data(4))
        assert same(model, model.model_dump()) is None


def test_raw_omitted_none_cannot_replace_another_actual_field(local_origin):
    from sim2act.contracts import BranchCondition, FieldSource
    model = manifest(local_origin)
    model.input_schema = dict(condition=BranchCondition(op='exists',
        source=FieldSource(source='input', field='value')))
    raw = model.model_dump()
    del raw['input_schema']['condition']['source']
    raw['input_schema']['condition']['value'] = None
    assert same(model, raw)['message'] == 'Typed trial storage changed after its complete raw proof'


@pytest.mark.parametrize('replacement', ['method', 'descriptor', 'same-extension'])
def test_modified_serializer_keeps_original_pre_dump_raw_snapshot(local_origin, monkeypatch, replacement):
    model = manifest(local_origin)
    raw = model.model_dump()
    original = AppManifest.__pydantic_serializer__
    old_revision, calls = raw['revision'], []
    def changed(value, **kwargs):
        calls.append('dump')
        result = original.to_python(value, warnings=False)
        raw['revision'] += 1
        result['revision'] += 1
        return result
    if replacement == 'method':
        monkeypatch.setattr(AppManifest, 'model_dump', changed)
    elif replacement == 'descriptor':
        class Descriptor:
            def __get__(self, instance, owner):
                calls.append('descriptor')
                return changed
        monkeypatch.setattr(AppManifest, 'model_dump', Descriptor())
    else:
        custom = SchemaSerializer(core_schema.any_schema(
            serialization=core_schema.plain_serializer_function_ser_schema(changed)))
        assert type(custom) is type(original)
        monkeypatch.setattr(AppManifest, '__pydantic_serializer__', custom)
    old = outcome(lambda: reference(AppManifest, model, raw))
    old_calls = tuple(calls)
    raw['revision'], calls[:] = old_revision, []
    new = outcome(lambda: gate._trial_typed_values([(AppManifest, model, raw)]))
    assert new == old and new['message'] == 'Typed trial fact changed after its complete raw proof'
    assert tuple(calls) == old_calls


def test_invalid_actual_rejects_before_dump_descriptor_dispatch(local_origin, monkeypatch):
    model = manifest(local_origin)
    raw, calls = model.model_dump(), []
    model.__dict__['unexpected'] = True
    class Descriptor:
        def __get__(self, instance, owner):
            calls.append('descriptor')
            pytest.fail('serializer lookup preceded the original actual storage gate')
    monkeypatch.setattr(AppManifest, 'model_dump', Descriptor())
    assert same(model, raw)['message'] == 'Complete fixed typed trial storage required'
    assert not calls


def test_nested_any_serializer_replacement_keeps_original_snapshot(local_origin, monkeypatch):
    from sim2act.contracts import BranchCondition, FieldSource
    model = manifest(local_origin)
    model.input_schema = dict(condition=BranchCondition(op='exists',
        source=FieldSource(source='input', field='value')))
    raw = model.model_dump()
    original, calls = BranchCondition.__pydantic_serializer__, []
    def changed(value):
        calls.append('nested')
        result = original.to_python(value, warnings=False)
        result['op'] = raw['input_schema']['condition']['op'] = 'eq'
        return result
    replacement = SchemaSerializer(core_schema.any_schema(
        serialization=core_schema.plain_serializer_function_ser_schema(changed)))
    monkeypatch.setattr(BranchCondition, '__pydantic_serializer__', replacement)
    old = outcome(lambda: reference(AppManifest, model, raw))
    assert calls == ['nested']
    raw['input_schema']['condition']['op'], calls[:] = 'exists', []
    new = outcome(lambda: gate._trial_typed_values([(AppManifest, model, raw)]))
    assert new == old and new['message'] == 'Typed trial fact changed after its complete raw proof'
    assert calls == ['nested']


def test_standard_path_never_constructs_actual_or_saved_copies(local_origin, monkeypatch):
    model = manifest(local_origin)
    raw = model.model_dump()
    def forbidden(*args, **kwargs):
        pytest.fail('standard stream invoked an old copy or copied-value comparator')
    for name in ('_trial_typed_storage', '_trial_pure_data', '_trial_typed_equal'):
        monkeypatch.setattr(gate, name, forbidden)
    gate._trial_typed_values([(AppManifest, model, raw)])
    # This is a new invocation, not a previous validation/PASS capability.
    raw['revision'] += 1
    with pytest.raises(DomainError, match='Typed trial storage changed'):
        gate._trial_typed_values([(AppManifest, model, raw)])


def test_pure_parent_order_and_original_exception_identity(local_origin):
    model = manifest(local_origin)
    models, calls = [(AppManifest, model, model.model_dump())], []
    failure = ValueError('original parent refusal')
    def parent():
        calls.append('parent')
        raise failure
    with pytest.raises(ValueError) as caught:
        gate._trial_typed_guard(parent, models)()
    assert caught.value is failure and calls == ['parent']
    assert stream._STANDARD_DUMP is AppManifest.model_dump


def test_fresh_source_unknown_and_runcheck_are_content_only(sql_facts):
    f = sql_facts
    # These values exercise the two remaining scalar schemas. UNKNOWN is
    # deliberately not a manufactured account ALLOW or a resolver override.
    source = policy.SourceVerificationResult(
        requirements_fingerprint='a' * 64, account_id=f.binding.account_id,
        quota_subject=f.requirements.quota_subject, provider=f.requirements.provider,
        model=f.requirements.model, endpoint=f.requirements.endpoint,
        evidence_fingerprint='b' * 64, decision='UNKNOWN', legal_free_entitlement=None,
        enforced_non_chargeable=None, revoked=None, observed_at=f.history_start,
        expires_at=f.contract.expires_at)
    context = policy.RunCheck(requirements_fingerprint='a' * 64,
        approval_fingerprint='b' * 64, stage='source', run_id=f.source_id,
        runtime_id=f.source_job['runtime_id'], version=1, fence=1,
        worker_id='synthetic-stream-only', checked_at=f.history_start,
        deadline=f.contract.expires_at)
    for value in (source, context):
        raw = value.model_dump()
        assert same(value, raw) is None
        key = 'revoked' if value is source else 'fence'
        raw[key] = False if value is source else True
        assert same(value, raw)['message'] == 'Typed trial storage changed after its complete raw proof'


def test_actual_sqlite_cohort_copy_cost_observation(sql_facts):
    """Finite local CPU/allocation observation, never a G0 prediction/test."""
    f = sql_facts
    with f.store.tx() as c, native_segment(f, c) as s:
        models = []
        gate._graph_trial_journal_models(s.graph, f.store, c, models, s.state, s.cursor)
        gate._graph_trial_stage_models_from_raw(models, s.stage, s.graph.inputs, _owned=s.mode)
        for value in (f.contract, f.requirements, f.approval, f.phase, f.phase.authority,
                      f.frozen, f.frozen.limits, f.extraction[1]):
            gate._trial_typed_hold(models, type(value), value, value.model_dump())
        def old():
            for expected, model, raw in models:
                reference(expected, model, raw)
        def new():
            gate._trial_typed_values(models)
        old()
        new()
        observations = []
        for name, run in (('old', old), ('stream', new), ('stream', new), ('old', old)):
            start = time.thread_time_ns()
            for _ in range(40):
                run()
            cpu = time.thread_time_ns() - start
            tracemalloc.start()
            try:
                run()
                _, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            observations.append(dict(name=name, iterations=40, cpu_ns=cpu, traced_peak_bytes=peak))
        print(json.dumps(dict(cohort_models=len(models),
            schemas=[kind.__name__ for kind, _, _ in models],
            raw_json_bytes=sum(len(json.dumps(raw, ensure_ascii=True)) for _, _, raw in models),
            observations=observations, mock_exchanges=0, g0_runs=0,
            scope='THIS_COMPLETE_SQLITE_TYPED_COHORT_ONLY_NOT_G0'), sort_keys=True))
