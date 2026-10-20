"""Isolated synthetic pure-cohort boundaries, never a complete trial or permit.

The existing real SQLite/CGR and exact typed-accounting fixtures are reused.
The coordinator is deliberately assembled without a completed binding or audit
seed; only its actual _base/check cohort path is exercised. No executor/model.
This is unexecuted source supplied for the root writer's short test run.
"""

import copy
from collections.abc import Mapping
from types import SimpleNamespace

import pytest
from sqlalchemy import Column, MetaData, Table, create_engine, insert, literal, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from sqlalchemy.sql.elements import quoted_name
from test_cold_binding_fact_leaves import local_origin as local_origin
from test_cold_binding_fact_leaves import no_external_transport as no_external_transport
from test_cold_release_stages import read_scope
from test_cold_trial_guard_delta import _typed_accounted_generate
from test_cold_trial_guard_delta import typed_trial_inputs as typed_trial_inputs

from sim2act import natural_live_admission as gate
from sim2act import natural_spec_runtime as runtime
from sim2act import pb_natural_specs as pb
from sim2act import production_trial_policy as policy
from sim2act.contracts import FrozenRunContract, GoalSpec
from sim2act.db import new_id, runs
from sim2act.errors import DomainError


def assembled_cohort(t, c, guard):
    """Complete continuity values; they establish no Stage/accounting proof."""
    f = t.f
    generated = _typed_accounted_generate(t)
    source_input = copy.copy(t)
    source_input.identity = t.identity.model_copy(update=dict(stage='source', run_id=new_id('run')))
    source_all = _typed_accounted_generate(source_input)
    source = (source_all[0], source_all[1][:2], source_all[2][:2], source_all[3])
    frozen = FrozenRunContract(run_id=t.identity.run_id, runtime_id=t.contract.runtime_id,
        contract_version='F1.3', goal=GoalSpec(goal_id=new_id('goal'),
            project_id=t.contract.project_id, owner_id=f.user, goal='Synthetic continuity only',
            constraints=[], acceptance_version='F1-tool-chain.v1', resource_refs=[], unresolved=[]),
        resources=[], limits=f.limits, mode='mock', request_model='intern-s2')
    extract = pb.ExtractInput(review=pb.ReviewInput(source_run_id=source[0]['id'],
        expected_source_proof_fingerprint='a' * 64, expected_source_recipe_fingerprint='b' * 64,
        card_id=f.origin[3]['card_id'], expected_goal_version=1,
        expected_goal_fingerprint=f.origin[3]['fingerprint'], expected_source_hash=f.origin[2]['hash'],
        recipe=t.contract.extraction_recipe, name='Synthetic continuity', request_key='pure-extract'),
        expected_review_fingerprint='c' * 64,
        consent='EXTRACT_THIS_SUCCESSFUL_NATURAL_SPEC_RUN_WITH_THIS_REVIEW_AND_TARGET',
        artifact_write_consent='ALLOW_ONLY_THIS_APP_TO_SAVE_VALIDATED_CHECKLIST_JSON_IN_THIS_PROJECT')
    extraction = (copy.deepcopy(f.draft), extract, copy.deepcopy(f.origin[2]), copy.deepcopy(f.origin[3]))
    gen_raw = gate._graph_trial_accounted_raw(guard, f.store, c, generated, [])
    source_raw = gate._graph_trial_accounted_raw(guard, f.store, c, source, [])
    guard.add('cold-trial:journal', dict(ledger=policy.Ledger.model_dump(t.ledger),
        cursor=policy.AccountQuotaCursor.model_dump(t.cursor), revision=1))
    guard.add('cold-trial:accounted-generate', gen_raw)
    guard.add('cold-trial:accounted-source', source_raw)
    guard.add('trial-generated-model-facet', dict(frozen=FrozenRunContract.model_dump(frozen)))
    candidate, metadata = {'all': b'complete candidate bytes'}, {'version': 1}
    bound, source_bound = {'kind': 'synthetic cold'}, {'kind': 'synthetic source'}
    job = {'id': new_id('run')}
    full = dict(binding=bound, source_binding=source_bound, cold_job=job,
        source=source_raw, generation=dict(raw=candidate, metadata=metadata, run=generated[0]),
        extraction=dict(draft=extraction[0], request=pb.ExtractInput.model_dump(extract),
            target=extraction[2], goal=extraction[3]), source_proof={'complete': b'proof bytes'})
    guard.add('cold-trial:complete', full)
    cold_stage = (job, bound, candidate, metadata, generated[0], frozen, generated, source, extraction)
    source_stage = (source[0], source_bound, candidate, metadata, generated[0], frozen, generated, None, None)
    context = policy.RunCheck(requirements_fingerprint='d' * 64, approval_fingerprint='e' * 64,
        stage='cold', run_id=job['id'], runtime_id=t.contract.runtime_id, version=1, fence=1,
        worker_id=f.worker.id, checked_at=t.contract.expires_at - 100, deadline=t.contract.expires_at)
    context_raw = policy.RunCheck.model_dump(context)
    guard.add('synthetic-pure-context', context_raw)
    guard.add('cold-trial:admission-prefix', dict(original=gate.PBTrialContract.model_dump(t.contract),
        expected=policy.evidence.EvidenceRequirements.model_dump(t.expected)))
    graph = object.__new__(runtime._ColdTrialGraph)
    graph.__dict__.update(dict(worker=f.worker, c=c, guard=guard, platform=None, trial=None,
        audit_seed=None, journal=(t.ledger, t.cursor, 1), source_accounted=source,
        generate_accounted=generated, cold_stage_facts=cold_stage, source_stage_facts=source_stage,
        sealed_fields=None, source_proof=full['source_proof'], original=t.contract, expected=t.expected,
        live_source=None, context=context, context_record=context_raw,
        context_record_key='synthetic-pure-context', authority_record=None,
        authority_fields=None, phase='EMPTY', authorities=set()))
    return SimpleNamespace(graph=graph, generated=generated, source=source, stage=cold_stage,
        full=full, frozen=frozen, extraction=extraction)


def test_actual_pure_cohort_shared_outputs_external_pin_and_two_coordinator_checks(typed_trial_inputs, monkeypatch):
    t, calls = typed_trial_inputs, []
    f, original_check = t.f, runtime._ColdGraphRead.check
    with f.store.tx() as c, pb._source_reads(f.store, c), read_scope(f, c) as guard:
        cohort = assembled_cohort(t, c, guard)
        row = c.execute(select(literal('complete-row').label('id'), literal(1).label('version'),
            literal(b'full bytes').label('body'))).mappings().one()
        assert type(row) is RowMapping
        assert gate._trial_pure_data(row) == dict(row)
        assert set(gate._trial_pure_mapping(row)) == set(row)

        def observed_check(actual, store, connection):
            calls.append('full-CGR-check')
            return original_check(actual, store, connection)

        monkeypatch.setattr(runtime._ColdGraphRead, 'check', observed_check)
        external, pure = [], []
        gate._graph_trial_stage_models(guard, f.store, c, external, cohort.stage)
        assert calls == ['full-CGR-check']
        calls.clear()
        gate._graph_trial_stage_models_from_raw(pure, cohort.stage, guard.inputs)
        gate._trial_typed_values(pure)
        assert calls == [] and len(pure) == len(external)
        assert all(a[0] is b[0] and a[1] is b[1] and a[2] is b[2]
            for a, b in zip(pure, external, strict=True))
        assert len(guard.inputs['cold-trial:accounted-generate']['actual']) == 3
        assert len(guard.inputs['cold-trial:accounted-source']['actual']) == 2
        cohort.graph.check()
        assert calls == ['full-CGR-check', 'full-CGR-check']
        assert guard.active


@pytest.mark.parametrize('changed', ['nested-int-bool', 'nested-int-float', 'nested-list-tuple'])
def test_pure_coordinator_complete_typed_drift_is_sticky_before_next_consumer(typed_trial_inputs, monkeypatch, changed):
    t, consumers = typed_trial_inputs, []
    f = t.f
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError) as caught:
            with read_scope(f, c) as guard:
                cohort = assembled_cohort(t, c, guard)
                cohort.graph.check()
                if changed == 'nested-int-bool':
                    object.__setattr__(cohort.generated[2][2][0].identity, 'version', True)
                elif changed == 'nested-int-float':
                    object.__setattr__(cohort.generated[2][2][0].identity, 'version', 1.0)
                else:
                    goal = t.contract.bindings[0].goal_snapshot.content
                    object.__setattr__(goal, 'acceptance_checks', tuple(goal.acceptance_checks))
                try:
                    cohort.graph.check()
                    consumers.append('must-not-consume')
                except DomainError:
                    assert not guard.active and cohort.graph.phase == 'INVALID'
                    with pytest.raises(DomainError):
                        cohort.graph.check()
                    assert consumers == []
                    raise
        assert caught.value.code == 'VERSION_CONFLICT'


@pytest.mark.parametrize('changed', ['mapping', 'collision-key', 'model-subclass', 'row-index'])
def test_unknown_nested_storage_rejects_without_mapping_equality_or_dump_callbacks(typed_trial_inputs, changed):
    t, calls = typed_trial_inputs, []
    f = t.f

    class UnknownMapping(Mapping):
        def __iter__(self):
            calls.append('iter')
            raise AssertionError('Unknown mapping iterated')

        def __len__(self):
            calls.append('len')
            raise AssertionError('Unknown mapping counted')

        def __getitem__(self, key):
            calls.append('getitem')
            raise AssertionError('Unknown mapping consumed')

    class Key:
        def __hash__(self):
            calls.append('hash')
            return hash('account_id')

        def __eq__(self, other):
            calls.append('eq')
            raise AssertionError('Unknown key compared')

    class CursorSubclass(policy.AccountQuotaCursor):
        def model_dump(self, *args, **kwargs):
            calls.append('dump')
            raise AssertionError('Unknown model serializer invoked')

    raw = policy.AccountQuotaCursor.model_dump(t.cursor)
    model = t.cursor
    if changed == 'mapping':
        raw = dict(raw, nested=UnknownMapping())
    elif changed == 'collision-key':
        raw = {Key(): 'unknown'}
        calls.clear()
    elif changed == 'model-subclass':
        model = CursorSubclass.model_construct(**raw)
    else:
        index = {Key(): 0}
        calls.clear()
        raw = dict(raw, nested=RowMapping(SimpleResultMetaData(['account_id']), None, index, ('unknown',)))
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with read_scope(f, c) as guard:
                try:
                    gate._graph_trial_models_pin(guard, f.store, c,
                        [(policy.AccountQuotaCursor, model, raw)])
                except DomainError:
                    assert not guard.active and calls == []
                    raise
    assert calls == []


def test_actual_full_native_row_dict_keeps_trusted_quoted_keys_and_every_field():
    """Full runs column metadata copy only; no Store, actual Run or Stage proof."""
    synthetic = Table('synthetic_trial_pure_full_row', MetaData(),
        *(Column(column.name, column.type) for column in runs.c))
    engine = create_engine('sqlite://')
    try:
        with engine.begin() as c:
            synthetic.create(c)
            values = {column.name: None for column in synthetic.c}
            values.update(id='synthetic-full-row', goal='complete Goal',
                context=dict(messages=[dict(content='complete body')],
                    usage=dict(input_tokens=1, output_tokens=2, total_tokens=3)),
                resource_refs=['synthetic-resource-A', 'synthetic-resource-A'])
            c.execute(insert(synthetic).values(values))
            row = c.execute(select(synthetic)).mappings().one()
            assert type(row) is RowMapping and set(row) == set(runs.c.keys())
            raw = dict(row)  # The real accounted_raw/_accounted_fields shape.
            assert type(raw) is dict and any(type(key) is quoted_name for key in raw)
            actual = gate._trial_pure_data(raw)
            expected = {str(key): value for key, value in row.items()}
            assert type(actual) is dict and all(type(key) is str for key in actual)
            assert len(actual) == len(raw) == len(runs.c)
            assert set(actual) == {str(key) for key in runs.c.keys()}
            assert gate._trial_typed_equal(actual, expected)
            assert actual['context']['messages'] == [{'content': 'complete body'}]
            assert actual['context']['usage'] == dict(input_tokens=1, output_tokens=2, total_tokens=3)
            assert actual['resource_refs'] == ['synthetic-resource-A', 'synthetic-resource-A']
    finally:
        engine.dispose()
