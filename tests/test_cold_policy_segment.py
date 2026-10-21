"""Fixed policy segments with real SQLite/native pins; no G0 or transport.

The synthetic upstream fixture is not a complete binding/prepare/commit run.
Both commit-facing result constructors and normal read-scope exit run here;
the original coordinator/SQL/receipt boundaries remain outside these segments.
"""

import json

import pytest
from accounted_sqlite_fixture import seed_cold
from pydantic_core import SchemaSerializer, SchemaValidator
from sqlalchemy import event, update
from test_cold_accounted_native import native_segment
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import sql_facts as sql_facts

from sim2act import _cold_policy_segment as segment
from sim2act import natural_live_admission as gate
from sim2act import natural_spec_runtime as runtime
from sim2act import production_trial_policy as policy
from sim2act.db import fingerprint, grants
from sim2act.errors import DomainError


def coordinator(s):
    f = s.f
    graph = object.__new__(runtime._ColdTrialGraph)
    graph.__dict__.update(worker=f.worker, c=s.c, guard=s.graph,
        accounted_prewrite=s.mode, platform=None, trial=None, audit_seed=None,
        journal=(s.state, s.cursor, s.revision), source_accounted=s.source,
        generate_accounted=s.generated, cold_stage_facts=s.cold_stage,
        source_stage_facts=s.stage, sealed_fields=s.mode.complete,
        source_proof=f.proof, original=f.contract, live_source=None,
        context_record=None, authority_record=None, authority_fields=None,
        phase='COMPLETE')
    return graph


def context_inputs(f, s):
    approval, phase, actual, at = gate._graph_run_context(
        s.graph, f.store, s.c, f.user, f.contract, f.binding.approval_key,
        'cold', f.cold_job['id'], 1, 1, s.cold_stage, _owned=s.mode)
    original, expected = policy._requirements(f.user, f.contract, f.binding.approval_key)
    return (original, expected, approval, phase, actual, at, 'cold',
            actual['id'], actual['version'], actual['fence'], f.worker.id)


def test_two_fixed_segments_full_pins_outputs_and_normal_scope(sql_facts, monkeypatch, tmp_path):
    f = sql_facts
    seed_cold(f)
    counts = []
    encode = runtime._cold_graph_bytes

    def observed(values):
        counts.append(1)
        return encode(values)

    monkeypatch.setattr(runtime, '_cold_graph_bytes', observed)
    results = []
    with f.store.tx() as c, native_segment(f, c) as s:
        graph = coordinator(s)
        args = context_inputs(f, s)
        queries = []

        def sql(*args):
            queries.append(1)

        event.listen(f.store.engine, 'before_cursor_execute', sql)
        try:
            # Fresh prepare-facing requirements and both commit-facing
            # constructors. This never reuses a PASS between calls.
            for boundary in ('prepare', 'second-commit-requirements'):
                start = len(counts)
                old = policy._requirements(f.user, f.contract,
                    f.binding.approval_key, _guard=graph.check)
                old_count = len(counts) - start
                start = len(counts)
                new = graph._requirements_value(f.user, f.contract,
                    f.binding.approval_key, graph.check)
                new_count = len(counts) - start
                assert [v.model_dump() for v in new] == [v.model_dump() for v in old]
                assert new[0] is not f.contract
                assert (old_count, new_count) == (12, 4)
                results.append(dict(boundary=boundary, old_codec=old_count, new_codec=new_count))
            for boundary in ('first-commit-context', 'second-commit-context'):
                start = len(counts)
                old = policy._run_check_from_facts(*args, _guard=graph.check)
                old_count = len(counts) - start
                start = len(counts)
                new = graph._run_check_value(*args, pin=graph.check)
                new_count = len(counts) - start
                assert new.model_dump() == old.model_dump()
                assert fingerprint(new.model_dump()) == fingerprint(old.model_dump())
                assert new.checked_at == args[5] and new.deadline == old.deadline
                assert (old_count, new_count) == (14, 4)
                results.append(dict(boundary=boundary, old_codec=old_count, new_codec=new_count))
            assert queries == []
        finally:
            event.remove(f.store.engine, 'before_cursor_execute', sql)
        assert s.graph.active and s.mode.active
    assert not s.graph.active and not s.mode.active
    (tmp_path / 'codec-difference.json').write_text(json.dumps(results, indent=2))


def test_snapshot_no_mutable_alias_escape_and_shared_dag(sql_facts):
    model = sql_facts.contract
    shared = [model, {'nested': [True, 1, 1.0, None, (b'bytes',)]}]
    source = (shared, shared)
    saved = segment._snapshot(source)
    assert saved is not segment._UNSUITABLE
    assert saved[0] is saved[1] and saved[0] is not shared
    copied = saved[0][0]
    assert copied is not model and type(copied) is type(model)
    assert copied.__dict__ is not model.__dict__
    assert copied.__pydantic_fields_set__ is not model.__pydantic_fields_set__
    assert copied.model_dump() == model.model_dump()
    assert copied.bindings is not model.bindings
    assert copied.bindings[0].goal_snapshot.content is not model.bindings[0].goal_snapshot.content
    shared[1]['nested'].append('changed')
    assert len(saved[0][1]['nested']) == 5
    cyclic = []
    cyclic.append(cyclic)
    assert segment._snapshot(cyclic) is segment._UNSUITABLE


@pytest.mark.parametrize('change', ['settings', 'stop', 'input', 'original-model', 'returned-raw', 'revoke'])
def test_between_calls_current_mutation_or_authorization_write_is_sticky(sql_facts, change):
    f = sql_facts
    seed_cold(f)
    witness = None
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
        graph = coordinator(s)
        models = []
        pin = gate._trial_typed_guard(graph.check, models)
        graph._requirements_value(f.user, f.contract, f.binding.approval_key, pin)
        approval = gate._approved(f.store, c, f.user, f.contract, f.binding.approval_key)
        raw = gate._graph_trial_produced(s.graph, f.store, c, models, gate.Approval, approval)
        if change == 'settings':
            object.__setattr__(f.worker.s, 'max_output_tokens', f.worker.s.max_output_tokens - 1)
        elif change == 'stop':
            f.worker.stop.set()
        elif change == 'input':
            s.graph.inputs['synthetic-native-candidate'] = False
        elif change == 'original-model':
            approval.approved_at -= 1
        elif change == 'returned-raw':
            raw['approved_at'] -= 1
        else:
            c.execute(update(grants).where(grants.c.principal_id == f.user).values(revoked=True))
        with pytest.raises(DomainError) as caught:
            graph._requirements_value(f.user, f.contract, f.binding.approval_key, pin)
        witness = caught.value
        assert not s.graph.active and not s.mode.active and graph.phase == 'INVALID'
    assert witness is not None


@pytest.mark.parametrize('change', ['raw', 'settings'])
def test_exit_full_pin_refuses_mutation_after_snapshot_before_publication(sql_facts, monkeypatch, change):
    f = sql_facts
    seed_cold(f)
    snapshot = segment._snapshot
    witness = None
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
        graph = coordinator(s)

        def mutate(values):
            private = snapshot(values)
            assert private is not segment._UNSUITABLE
            if change == 'raw':
                s.graph.inputs['synthetic-native-candidate'] = False
            else:
                object.__setattr__(f.worker.s, 'max_output_tokens', f.worker.s.max_output_tokens - 1)
            return private

        monkeypatch.setattr(segment, '_snapshot', mutate)
        with pytest.raises(DomainError) as caught:
            graph._requirements_value(f.user, f.contract, f.binding.approval_key, graph.check)
        witness = caught.value
        assert not s.graph.active and graph.phase == 'INVALID'
    assert witness is not None


def test_closed_scope_and_original_core_error_never_replay_or_publish(sql_facts, monkeypatch):
    f = sql_facts
    seed_cold(f)
    with f.store.tx() as c, native_segment(f, c) as s:
        graph = coordinator(s)
        graph._requirements_value(f.user, f.contract, f.binding.approval_key, graph.check)
    with pytest.raises(DomainError):
        graph._requirements_value(f.user, f.contract, f.binding.approval_key, graph.check)
    assert graph.phase == 'INVALID'

    calls = []
    original = segment._REQUIREMENTS
    sentinel = DomainError('LIVE_BLOCKED', 'original pure failure')

    def fail(*args, **kwargs):
        calls.append(kwargs)
        raise sentinel

    # Both names are deliberately replaced only to inject an exact core error;
    # replacing only the public policy function must instead select legacy.
    monkeypatch.setattr(segment, '_REQUIREMENTS', fail)
    monkeypatch.setattr(policy, '_requirements', fail)
    with pytest.raises(DomainError) as caught, f.store.tx() as c, native_segment(f, c) as s:
        graph = coordinator(s)
        graph._requirements_value(f.user, f.contract, f.binding.approval_key, graph.check)
    assert caught.value is sentinel and calls == [{}]
    assert not s.graph.active and graph.phase == 'INVALID'
    monkeypatch.setattr(segment, '_REQUIREMENTS', original)


@pytest.mark.parametrize('hook', ['serializer', 'validator', 'function'])
def test_unknown_hooks_choose_original_guarded_path_before_core(sql_facts, monkeypatch, hook):
    f = sql_facts
    calls = []
    old = policy._requirements

    def recorded(*args, **kwargs):
        calls.append(kwargs)
        return old(*args, **kwargs)

    if hook == 'serializer':
        original_dump = gate.PBTrialContract.model_dump
        monkeypatch.setattr(gate.PBTrialContract, 'model_dump',
            lambda self, **kwargs: original_dump(self, **kwargs))
        assert segment._snapshot((f.user, f.contract, f.binding.approval_key)) is segment._UNSUITABLE
    elif hook == 'validator':
        validate = gate.PBTrialContract.model_validate
        monkeypatch.setattr(gate.PBTrialContract, 'model_validate',
            classmethod(lambda cls, value, **kwargs: validate(value, **kwargs)))
        assert segment._snapshot((f.user, f.contract, f.binding.approval_key)) is segment._UNSUITABLE
    monkeypatch.setattr(policy, '_requirements', recorded)
    pins = []
    result = segment._requirements_value(f.user, f.contract, f.binding.approval_key,
        pin=lambda: pins.append(1))
    assert len(pins) == 7 and len(calls) == 1
    assert '_guard' in calls[0] and result[0].model_dump() == f.contract.model_dump()


@pytest.mark.parametrize('change', ['rebuilt-schema', 'in-place-schema', 'recompiled-validator', 'recompiled-serializer'])
def test_schema_code_witness_rejects_recompiled_or_modified_native_hooks(sql_facts, monkeypatch, change):
    kind = gate.PBTrialContract
    schema = kind.__pydantic_core_schema__
    if change == 'rebuilt-schema':
        replacement = dict(schema)
        monkeypatch.setattr(kind, '__pydantic_core_schema__', replacement)
        monkeypatch.setattr(kind, '__pydantic_validator__', SchemaValidator(replacement))
        monkeypatch.setattr(kind, '__pydantic_serializer__', SchemaSerializer(replacement))
    elif change == 'in-place-schema':
        monkeypatch.setitem(schema, 'unreviewed_callback', lambda value: value)
    elif change == 'recompiled-validator':
        monkeypatch.setattr(kind, '__pydantic_validator__', SchemaValidator(schema))
    else:
        monkeypatch.setattr(kind, '__pydantic_serializer__', SchemaSerializer(schema))
    assert segment._snapshot((sql_facts.contract,)) is segment._UNSUITABLE


def test_foreign_metaclass_cannot_escape_snapshot_or_run_equality():
    calls = []

    class Meta(type):
        def __eq__(self, other):
            calls.append('equality')
            return True

        def __hash__(self):
            calls.append('hash')
            return 1

    class Foreign(metaclass=Meta):
        pass

    assert segment._snapshot((Foreign(),)) is segment._UNSUITABLE
    assert calls == []


def test_original_expiry_predicate_remains_before_result_construction(sql_facts):
    f = sql_facts
    seed_cold(f)
    reached = False
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
        graph = coordinator(s)
        args = context_inputs(f, s)
        original, _, approval, phase, actual, _, *_ = args
        # Reuse supplied values and deliberately expired at. No time patch,
        # renewal, authorization bypass or result construction can rescue it.
        try:
            gate._require_run_context_row(f.user, original, 'cold', actual,
                actual['version'], actual['fence'], approval, phase,
                actual['lease_until'] + 1, _guard=graph.check)
        except DomainError as error:
            reached = True
            assert error.message == 'Run identity, cancellation, version or finite lease changed'
            raise
    assert reached and not s.graph.active


@pytest.mark.parametrize('which', ['requirements', 'run-check'])
def test_foreign_guard_entry_refusal_never_calls_foreign_cleanup(which):
    calls = []

    class Foreign:
        def __getattribute__(self, name):
            calls.append(name)
            raise AssertionError('Foreign guard attribute callback')

    graph = object.__new__(runtime._ColdTrialGraph)
    graph.guard = Foreign()
    graph.phase = 'COMPLETE'
    with pytest.raises(DomainError) as caught:
        if which == 'requirements':
            graph._requirements_value(None, None, None, graph.check)
        else:
            graph._run_check_value(*([None] * 11), pin=graph.check)
    assert caught.value.code == 'VERSION_CONFLICT'
    assert graph.phase == 'INVALID' and calls == []
