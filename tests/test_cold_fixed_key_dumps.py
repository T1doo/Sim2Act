"""Three isolated new-pin storage/bridge boundaries, no Stage/permit proof.

Reuses exact synthetic Worker/typed models and real SQLite read-scope fixtures.
Unexecuted source supplied to the sole repository writer; no model or network.
"""

import warnings

import pytest
from test_cold_binding_fact_leaves import handoff
from test_cold_binding_fact_leaves import local_origin as local_origin
from test_cold_binding_fact_leaves import no_external_transport as no_external_transport
from test_cold_release_stages import read_scope

from sim2act import natural_live_admission as gate
from sim2act import pb_natural_specs as pb
from sim2act.contracts import AppManifest
from sim2act.errors import DomainError


def fixed_key_boundary(f, monkeypatch, which):
    """Only the selected one of the three new pins, over fresh local scopes."""
    calls, warning_calls, bridge_calls = [], [], []
    expected = AppManifest if which == 'origin-manifest' else gate.PBTrialContract
    model = f.origin[0] if expected is AppManifest else f.worker.pa_trial.contract
    original_dump = expected.model_dump
    assert type(model) is expected
    original_raw = gate._trial_typed_storage(expected, model)
    assert gate._trial_typed_equal(original_raw, original_dump(model, warnings=False))

    def fixed_dump(actual, *args, **kwargs):
        bridge_calls.append(actual)
        assert actual is model and kwargs == {'warnings': False}
        return original_dump(actual, *args, **kwargs)

    def shadow(*args, **kwargs):
        calls.append('instance-dump')
        return original_raw

    def warning(*args, **kwargs):
        warning_calls.append('warning')
        raise AssertionError('A new pin dispatched a warning hook')

    class Unknown:
        def __repr__(self):
            calls.append('repr')
            raise AssertionError('Unknown nested object formatted')

        def __eq__(self, other):
            calls.append('eq')
            raise AssertionError('Unknown nested object compared')

    monkeypatch.setattr(expected, 'model_dump', fixed_dump)
    monkeypatch.setattr(warnings, 'showwarning', warning)
    with f.store.tx() as c, pb._source_reads(f.store, c):
        context = (lambda: read_scope(f, c)) if which == 'cgr-contract' else (lambda: handoff(f, c))

        def check(pin):
            if which == 'cgr-contract':
                return pin.check(f.store, c)
            return pin.check(f.store, c, f.user, f.draft, f.limits)

        # The unchanged constructor requests its full initial bridge once.
        with context() as pin:
            assert bridge_calls == [model]
            check(pin)
            assert pin.input_key() == pin.key
            assert bridge_calls == [model] and calls == warning_calls == []
        assert not pin.active

        for changed in ('declared', 'shadow', 'unknown-nested'):
            bridge_before = len(bridge_calls)
            with pytest.raises(DomainError) as caught:
                with context() as pin:
                    assert len(bridge_calls) == bridge_before + 1
                    if changed == 'declared':
                        name = 'revision' if expected is AppManifest else 'trial_key'
                        old = getattr(model, name)
                        setattr(model, name, old + 1 if type(old) is int else old + '-changed')
                    elif changed == 'shadow':
                        object.__setattr__(model, 'model_dump', shadow)
                    elif expected is AppManifest:
                        model.input_schema['synthetic-unknown'] = Unknown()
                    else:
                        model.bindings[0].goal_snapshot.content.known.append(Unknown())
                    try:
                        if changed == 'declared':
                            assert pin.input_key() != pin.key
                        try:
                            check(pin)
                        except DomainError:
                            assert not pin.active and calls == warning_calls == []
                            assert len(bridge_calls) == bridge_before + 1
                            before = list(f.trace)
                            with pytest.raises(DomainError):
                                check(pin)
                            assert f.trace == before and calls == warning_calls == []
                            raise
                    finally:
                        if changed == 'declared':
                            setattr(model, name, old)
                        elif changed == 'shadow':
                            object.__delattr__(model, 'model_dump')
                        elif expected is AppManifest:
                            del model.input_schema['synthetic-unknown']
                        else:
                            model.bindings[0].goal_snapshot.content.known.pop()
            assert caught.value.code == 'VERSION_CONFLICT' and not pin.active
        bridge_before = len(bridge_calls)

        def mismatched_dump(actual, *args, **kwargs):
            raw = fixed_dump(actual, *args, **kwargs)
            field = 'revision' if expected is AppManifest else 'trial_key'
            raw[field] = raw[field] + 1 if type(raw[field]) is int else raw[field] + '-bridge-mismatch'
            return raw

        monkeypatch.setattr(expected, 'model_dump', mismatched_dump)
        with pytest.raises(DomainError) as bridge_error:
            with context():
                pytest.fail('A mismatched initial full storage/schema bridge was accepted')
        assert bridge_error.value.code == 'VERSION_CONFLICT'
        assert len(bridge_calls) == bridge_before + 1
    assert calls == warning_calls == []


def test_cgr_contract_storage_bridge_and_key_reentry(local_origin, monkeypatch):
    fixed_key_boundary(local_origin, monkeypatch, 'cgr-contract')


def test_origin_manifest_storage_bridge_and_key_reentry(local_origin, monkeypatch):
    fixed_key_boundary(local_origin, monkeypatch, 'origin-manifest')


def test_origin_contract_storage_bridge_and_key_reentry(local_origin, monkeypatch):
    fixed_key_boundary(local_origin, monkeypatch, 'origin-contract')
