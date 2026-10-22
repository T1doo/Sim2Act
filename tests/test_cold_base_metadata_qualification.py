"""Issued SQLite _base qualifier: no Worker/Mock/G0 or model calls."""

import json
import statistics
import sys
import time

import pytest
from accounted_sqlite_fixture import seed_cold
from test_cold_accounted_native import native_segment
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import sql_facts as sql_facts
from test_cold_base_cohort import trial

from sim2act import _cold_base_segment as segment
from sim2act import _cold_policy_segment as schema
from sim2act import natural_live_admission as gate
from sim2act import natural_spec_runtime as rt
from sim2act import production_trial_policy as policy
from sim2act._cold_typed_stream import _Comparison
from sim2act.errors import DomainError


def original_qualifier(models):
    comparison = _Comparison(gate._trial_typed_nested_classes())
    try:
        for _, model, _ in models:
            comparison.validate_model(model)
        kinds = {type(model) for model, _, _ in comparison.models.values()}
        return comparison.standard_serializers() and all(schema._fixed_schema(k) for k in kinds)
    except DomainError:
        return False


def test_complete_issued_cohort_original_qualifier_and_new_guard_cost(sql_facts, tmp_path):
    f = sql_facts
    seed_cold(f)
    with f.store.tx() as c, native_segment(f, c) as s:
        t = trial(s)
        models = t._typed_parameter_models()
        assert original_qualifier(models) and segment.fixed_serializers(models)
        calls = []
        code = _Comparison.validate_model.__code__

        def profile(frame, event, arg):
            if event == 'call' and frame.f_code is code:
                calls.append(1)

        sys.setprofile(profile)
        try:
            t._base()
        finally:
            sys.setprofile(None)
        assert len(calls) == len(models)  # Every original consumer actual gate remains.
        samples = [[], []]
        for turn in range(6):
            for index in ((0, 1) if turn % 2 == 0 else (1, 0)):
                begin = time.thread_time()
                for _ in range(10):
                    if index == 0:
                        assert original_qualifier(models)
                    else:
                        assert segment.fixed_serializers(models) and segment.serializers_current()
                samples[index].append(time.thread_time() - begin)
        (tmp_path / 'qualification-cpu.json').write_text(json.dumps(dict(
            scope='issued fixture qualifier only, not complete G0', models=len(models),
            kinds=len(segment._model_kinds(models)), iterations=10,
            old=samples[0], candidate_including_catalog_guard=samples[1],
            old_median=statistics.median(samples[0]),
            candidate_median=statistics.median(samples[1])), indent=2))


@pytest.mark.parametrize('damage', ['hidden-key', 'fields-set', 'replace-dict'])
def test_mutation_after_discovery_is_freshly_rejected(sql_facts, damage):
    f = sql_facts
    seed_cold(f)
    changed = []
    target = f.frozen
    raw = object.__getattribute__(target, '__dict__')
    fields = object.__getattribute__(target, '__pydantic_fields_set__')

    def profile(frame, event, arg):
        if frame.f_code is segment.fixed_serializers.__code__ and event == 'return' and arg is True and not changed:
            changed.append(1)
            if damage == 'hidden-key':
                raw['unexpected-hidden-key'] = True
            elif damage == 'fields-set':
                object.__setattr__(target, '__pydantic_fields_set__', {'foreign-field'})
            else:
                object.__setattr__(target, '__dict__', dict(raw, unexpected=True))

    try:
        with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
            t = trial(s)
            sys.setprofile(profile)
            try:
                with pytest.raises(DomainError) as rejected:
                    t._base()
            finally:
                sys.setprofile(None)
            assert changed == [1] and not s.graph.active and not s.mode.active
            assert t.phase == 'INVALID'
            raise rejected.value
    finally:
        raw.pop('unexpected-hidden-key', None)
        object.__setattr__(target, '__dict__', raw)
        object.__setattr__(target, '__pydantic_fields_set__', fields)


def test_new_kind_unknown_callback_after_discovery_has_full_entry_pin(sql_facts, monkeypatch):
    f = sql_facts
    seed_cold(f)
    model = policy.SourceVerificationResult(requirements_fingerprint='a'*64,
        account_id='account', quota_subject='subject', provider='intern-ai',
        model='intern-s2', endpoint='https://offline.invalid', evidence_fingerprint='b'*64,
        decision='ALLOW', legal_free_entitlement=True, enforced_non_chargeable=True,
        revoked=False, observed_at=1, expires_at=2)
    raw = model.model_dump()
    kind, dump = type(model), type(model).model_dump
    codecs, callbacks, changed = [], [], []
    encode = rt._cold_graph_bytes

    def encoded(value):
        codecs.append(1)
        return encode(value)

    def replacement(value, **kwargs):
        callbacks.append(len(codecs))
        return dump(value, **kwargs)

    def profile(frame, event, arg):
        if frame.f_code is segment.fixed_serializers.__code__ and event == 'return' and arg is True and not changed:
            models = frame.f_locals['models']
            assert all(k is not kind for k in segment._model_kinds(models))
            models.append((kind, model, raw))
            monkeypatch.setattr(kind, 'model_dump', replacement)
            changed.append(1)

    with f.store.tx() as c, native_segment(f, c) as s:
        t = trial(s)
        monkeypatch.setattr(rt, '_cold_graph_bytes', encoded)
        sys.setprofile(profile)
        try:
            t._base()
        finally:
            sys.setprofile(None)
        assert changed == [1] and len(codecs) == 2
        assert callbacks and all(n == 1 for n in callbacks)
        monkeypatch.setattr(kind, 'model_dump', dump)


def test_discovery_dag_cycle_and_foreign_keys_do_not_dispatch():
    class Key:
        pass
    key = Key()
    mapping = {key: None}

    def forbidden(*args):
        raise AssertionError('foreign hash/equality')

    Key.__hash__ = forbidden
    Key.__eq__ = forbidden
    class Foreign(dict):
        def values(self):
            raise AssertionError('foreign iterator')
    shared = []
    roots = [(list, [shared, shared, mapping], {})]
    assert segment._model_kinds(roots) == ()
    shared.append(shared)
    assert segment._model_kinds(roots) is None
    assert segment._model_kinds([(Foreign, Foreign(), {})]) is None
