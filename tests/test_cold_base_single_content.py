"""Real issued SQLite fixed _base only. No Worker run/model/Mock/G0."""

import sys
from collections.abc import Mapping
from types import MappingProxyType

import pytest
from accounted_sqlite_fixture import seed_cold
from sqlalchemy import event, update
from test_cold_accounted_native import native_segment
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import sql_facts as sql_facts
from test_cold_base_cohort import trial

from sim2act import _cold_base_segment as segment
from sim2act import cold_accounted as owned
from sim2act import natural_live_admission as gate
from sim2act import natural_spec_runtime as rt
from sim2act.db import grants
from sim2act.errors import DomainError


def test_qualified_base_one_codec_same_predicates_dynamic_two_ends_zero_sql(sql_facts, monkeypatch):
    f = sql_facts
    seed_cold(f)
    with f.store.tx() as c, native_segment(f, c) as s:
        t = trial(s)
        assert segment.eligible(t)
        encode = rt._cold_graph_bytes
        codecs, sql, trace = [], [], []
        targets = {function.__code__: name for name, function in (
            ('family', owned._OwnedPrewriteMode._OwnedPrewriteMode__family_current),
            ('run', owned._OwnedPrewriteMode._OwnedPrewriteMode__run_current),
            ('hold', gate._trial_typed_hold), ('values', gate._trial_typed_values),
            ('dynamic', rt._ColdGraphRead._check_dynamic))}

        def profile(frame, kind, arg):
            if kind == 'call' and frame.f_code in targets:
                name = targets[frame.f_code]
                trace.append((name, frame.f_locals.get('role')))

        def encoded(value):
            codecs.append(1)
            return encode(value)

        def executed(*args):
            sql.append(1)

        monkeypatch.setattr(rt, '_cold_graph_bytes', encoded)
        event.listen(f.store.engine, 'before_cursor_execute', executed)
        observations = []
        try:
            for old in (True, False):
                codecs.clear()
                trace.clear()
                with monkeypatch.context() as patch:
                    if old:
                        patch.setattr(segment, 'eligible', lambda _: False)
                    sys.setprofile(profile)
                    try:
                        t._base()
                    finally:
                        sys.setprofile(None)
                observations.append((len(codecs), tuple(trace)))
        finally:
            event.remove(f.store.engine, 'before_cursor_execute', executed)
        assert [item[0] for item in observations] == [2, 1]
        assert observations[0][1] == observations[1][1]
        assert sum(name == 'dynamic' for name, _ in observations[1][1]) == 2
        assert sql == []


@pytest.mark.parametrize('damage', ['raw', 'raw-and-model', 'raw-and-stop', 'model'])
def test_entry_damage_never_returns_and_mixed_priority_matches_old(sql_facts, monkeypatch, damage):
    f = sql_facts
    seed_cold(f)
    errors = []
    for old in (True, False):
        # All damage is scoped to each independent real read epoch.
        with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
            t = trial(s)
            original = f.frozen.limits.run_seconds
            if damage.startswith('raw'):
                s.graph.inputs['cold-trial:complete']['source_proof']['entry-damage'] = True
            if damage in ('raw-and-model', 'model'):
                object.__setattr__(f.frozen.limits, 'run_seconds', original - 1)
            if damage == 'raw-and-stop':
                f.worker.stop.set()
            try:
                with monkeypatch.context() as patch:
                    if old:
                        patch.setattr(segment, 'eligible', lambda _: False)
                    with pytest.raises(DomainError) as rejected:
                        t._base()
                errors.append((rejected.value.code, rejected.value.message))
                assert not s.graph.active and not s.mode.active and t.phase == 'INVALID'
            finally:
                object.__setattr__(f.frozen.limits, 'run_seconds', original)
                f.worker.stop.clear()
            raise rejected.value
        f.proof.pop('entry-damage', None)
    assert errors[0] == errors[1]


@pytest.mark.parametrize('damage', ['raw', 'stop', 'settings', 'write', 'epoch', 'scope'])
def test_inside_fixed_segment_mutation_cannot_escape(sql_facts, damage):
    f = sql_facts
    seed_cold(f)
    fired = []
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
        t = trial(s)
        assert segment.eligible(t)
        code = gate._trial_typed_values.__code__

        def profile(frame, kind, arg):
            if frame.f_code is code and kind == 'return' and not fired:
                fired.append(True)
                if damage == 'raw':
                    s.graph.inputs['cold-trial:complete']['source_proof']['inside-damage'] = True
                elif damage == 'stop':
                    f.worker.stop.set()
                elif damage == 'settings':
                    object.__setattr__(f.settings, 'run_seconds', f.settings.run_seconds - 1)
                elif damage == 'write':
                    c.execute(update(grants).values(revoked=True))
                elif damage == 'epoch':
                    c.info['source_proof_write_epoch'] = s.graph.epoch + 1
                else:
                    s.graph.scope.clear()

        sys.setprofile(profile)
        try:
            with pytest.raises(DomainError) as rejected:
                t._base()
        finally:
            sys.setprofile(None)
        assert fired == [True] and not s.graph.active and not s.mode.active
        assert t.phase == 'INVALID'
        raise rejected.value


@pytest.mark.parametrize('damage', ['dump', 'schema', 'nested-serializer'])
def test_unknown_serialization_keeps_two_pins_before_callbacks(sql_facts, monkeypatch, damage):
    f = sql_facts
    seed_cold(f)
    with f.store.tx() as c, native_segment(f, c) as s:
        t = trial(s)
        calls, codecs = [], []
        original = gate.Approval.model_dump
        encode = rt._cold_graph_bytes

        def encoded(value):
            codecs.append(1)
            return encode(value)

        with monkeypatch.context() as patch:
            if damage == 'dump':
                kind = type(f.frozen)
                dump = kind.model_dump

                def replacement(value, **kwargs):
                    calls.append(len(codecs))
                    return dump(value, **kwargs)

                patch.setattr(kind, 'model_dump', replacement)
            elif damage == 'schema':
                patch.setitem(type(f.frozen).__pydantic_core_schema__, 'test_unknown_schema', True)
            else:
                from pydantic_core import SchemaSerializer
                schema = {'type': 'int'}
                patch.setattr(type(f.frozen.limits), '__pydantic_serializer__', SchemaSerializer(schema))
            patch.setattr(rt, '_cold_graph_bytes', encoded)
            t._base()
            assert len(codecs) == 2
            if damage == 'dump':
                assert calls and all(value == 1 for value in calls)
        assert original is gate.Approval.model_dump


@pytest.mark.parametrize('damage', ['trial-method', 'mode-method', 'inputs-key', 'issued-role',
    'active', 'header', 'foreign-proxy', 'foreign-binding'])
def test_unknown_members_choose_legacy_before_foreign_callbacks(sql_facts, monkeypatch, damage):
    f = sql_facts
    seed_cold(f)
    callbacks = []

    class Foreign:
        def __hash__(self):
            return hash('cold-trial:accounted-source')

        def __eq__(self, other):
            callbacks.append('eq')
            return False

        def __bool__(self):
            callbacks.append('bool')
            return True

    class ForeignMapping(Mapping):
        def __getitem__(self, key):
            callbacks.append('getitem')
            raise AssertionError('foreign mapping executed')

        def __iter__(self):
            callbacks.append('iter')
            return iter(())

        def __len__(self):
            callbacks.append('len')
            return 0

    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
        t = trial(s)
        if damage == 'trial-method':
            t._typed_parameter_models = lambda: callbacks.append('trial')
        elif damage == 'mode-method':
            s.mode._base_parameters_current = lambda _: callbacks.append('mode')
        elif damage == 'inputs-key':
            inputs = dict(s.mode._OwnedPrewriteMode__inputs)
            inputs[Foreign()] = None
            callbacks.clear()
            s.mode._OwnedPrewriteMode__inputs = inputs
        elif damage == 'issued-role':
            handle = s.source.handle
            s.mode.scope._issued[handle] = (Foreign(), s.mode.scope._issued[handle][1])
        elif damage == 'active':
            s.mode.scope._active = Foreign()
        elif damage == 'header':
            s.mode._OwnedPrewriteMode__binding_header = (Foreign(), 'a', 'b', 'c')
        elif damage == 'foreign-proxy':
            s.mode.complete = MappingProxyType(ForeignMapping())
        else:
            class ForeignBinding:
                @property
                def contract(self):
                    callbacks.append('contract')
                    raise AssertionError('foreign property executed')
            s.graph.binding = ForeignBinding()
        assert not segment.eligible(t) and callbacks == []
        s.graph.inputs['cold-trial:complete']['source_proof']['raw-before-callback'] = True
        with pytest.raises(DomainError) as rejected:
            t._base()
        assert callbacks == [] and not s.graph.active and t.phase == 'INVALID'
        raise rejected.value


def test_unknown_core_exception_preserved_scope_closed(sql_facts, monkeypatch):
    f = sql_facts
    seed_cold(f)
    error = RuntimeError('original unknown callback failure')
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
        t = trial(s)

        def fail(models):
            raise error

        monkeypatch.setattr(gate, '_trial_typed_values', fail)
        assert not segment.eligible(t)
        with pytest.raises(RuntimeError) as rejected:
            t._base()
        assert rejected.value is error and not s.mode.active and t.phase == 'INVALID'


@pytest.mark.parametrize('helper', ['_trial_typed_classes', '_trial_typed_nested_classes', '_schema_shape'])
def test_unknown_qualification_helper_restores_original_boundary(sql_facts, monkeypatch, helper):
    f = sql_facts
    seed_cold(f)
    calls = []
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
        t = trial(s)
        def callback(*args):
            calls.append(True)
            raise AssertionError('unknown qualification helper executed')
        module = segment.schema_code if helper == '_schema_shape' else gate
        monkeypatch.setattr(module, helper, callback)
        assert not segment.eligible(t) and calls == []
        s.graph.inputs['cold-trial:complete']['source_proof']['unknown-helper'] = True
        if helper != '_schema_shape':
            # Those class-list helpers are ALSO used by the original full
            # codec's storage gate. A dynamic refusal happens before either
            # original storage hook; do not claim old codec was callback-free.
            f.worker._journal_trial_drift = True
        with pytest.raises(DomainError) as rejected:
            t._base()
        assert calls == [] and not s.graph.active and not s.mode.active
        raise rejected.value


@pytest.mark.parametrize('damage', ['contract-caps', 'contract-model', 'caps-max', 'contract-extra'])
def test_missing_model_field_and_foreign_extra_never_dispatch_before_full_pin(sql_facts, damage):
    f = sql_facts
    seed_cold(f)
    callbacks = []

    class ForeignExtra(Mapping):
        def __getitem__(self, key):
            callbacks.append('getitem')
            raise AssertionError('foreign Pydantic extra dispatched')

        def __iter__(self):
            callbacks.append('iter')
            return iter(())

        def __len__(self):
            callbacks.append('len')
            raise AssertionError('foreign Pydantic extra truth dispatched')

    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
        t = trial(s)
        assert segment.eligible(t)
        contract = s.graph.binding.contract
        model = contract.caps if damage == 'caps-max' else contract
        raw = object.__getattribute__(model, '__dict__')
        if damage != 'contract-extra':
            raw.pop({'contract-caps': 'caps', 'contract-model': 'model',
                'caps-max': 'max_output_tokens'}[damage])
        object.__setattr__(model, '__pydantic_extra__', ForeignExtra())
        assert not segment.eligible(t) and callbacks == []
        with pytest.raises(DomainError) as rejected:
            t._base()
        assert callbacks == [] and not s.graph.active and not s.mode.active
        assert t.phase == 'INVALID'
        raise rejected.value
