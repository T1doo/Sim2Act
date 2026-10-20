"""Default signature binding only; no fixtures, DB, Worker or model execution."""

import pytest

from sim2act import pa_spec_apps as spec
from sim2act import pb_natural_uses as use
from sim2act.errors import DomainError


@pytest.mark.parametrize(('module', 'public', 'core', 'arity'), [
    (spec, 'scope_gate', '_scope_gate_core', 4),
    (spec, 'job_scope_gate', '_job_scope_gate_with_authorities', 4),
    (use, 'scope_gate', '_scope_gate', 5),
], ids=['spec-scope', 'spec-job', 'use-scope'])
@pytest.mark.parametrize('shape', ['missing', 'extra'])
def test_default_scope_argument_binding_keeps_original_controlled_error_before_core_body(
        monkeypatch, module, public, core, arity, shape):
    entered = []

    def four(store, c, user, entity, *, _graph_read=None):
        entered.append('core-body')
        pytest.fail('Wrong positional arity entered the four-argument scope core')

    def five(store, c, user, rid, header, *, _graph_read=None, _scope_role='audit'):
        entered.append('core-body')
        pytest.fail('Wrong positional arity entered the five-argument scope core')

    # Explicit same positional/keyword-only shapes preserve Python's real
    # pre-body TypeError; a variadic body spy would not exercise this boundary.
    monkeypatch.setattr(module, core, four if arity == 4 else five)
    args = (None,) * (arity - 1 if shape == 'missing' else arity + 1)
    with pytest.raises(DomainError) as caught:
        getattr(module, public)(*args)
    assert caught.value.code == 'VERSION_CONFLICT'
    assert caught.value.message == 'Malformed persisted DeliveryGraph binding'
    assert entered == []
