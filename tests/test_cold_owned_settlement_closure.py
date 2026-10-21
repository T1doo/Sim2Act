"""Closure counterexamples only, not a complete prepare/commit/G0 fixture.

Real SQLite approval + original typed producer inside the issued two-family
native scope. Shows why that issuance does not own later typed model/raw.
"""

import pytest
from test_cold_accounted_native import native_segment
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import sql_facts as sql_facts

from sim2act import natural_live_admission as gate
from sim2act.db import fingerprint
from sim2act.errors import DomainError


@pytest.mark.parametrize('changed', ['original_model', 'returned_raw'])
def test_later_typed_producer_is_not_owned_by_prior_two_family_issuance(sql_facts, changed):
    f = sql_facts
    witness = None
    graph = mode = None
    # The old lexical typed pin owns its sticky invalidation and the original
    # scope exit refuses that invalid scope. Nothing resets it for a pass.
    with pytest.raises(DomainError), f.store.tx() as c:
        with native_segment(f, c) as s:
            graph, mode = s.graph, s.mode
            assert s.cohort.route == 'OWNED' and mode is not None
            model = gate._approved(f.store, c, f.user, f.contract, f.binding.approval_key)
            models = []
            raw = gate._graph_trial_produced(graph, f.store, c, models, gate.Approval, model)
            assert len(models) == 1 and models[0][0] is gate.Approval
            assert models[0][1] is model and models[0][2] is raw
            assert type(model) is gate.Approval and type(raw) is dict
            assert fingerprint(model.model_dump()) == fingerprint(raw)
            gate._graph_trial_models_pin(graph, f.store, c, models)
            if changed == 'original_model':
                model.approved_at -= 1
            else:
                raw['approved_at'] -= 1
            # The independently issued Source/Generate packets and full graph
            # are still intact. A typed-PASS cache would miss this real alias.
            graph.check(f.store, c)
            assert fingerprint(model.model_dump()) != fingerprint(raw)
            with pytest.raises(DomainError, match='Typed trial storage changed') as caught:
                gate._graph_trial_models_pin(graph, f.store, c, models)
            witness = caught.value
            assert not graph.active and not mode.active and not mode.scope._active
    # An earlier fixture/producer error cannot masquerade as this counterexample.
    assert witness is not None and graph is not None and mode is not None
    assert witness.message == 'Typed trial storage changed after its complete raw proof'
    assert not graph.active and not mode.active and not mode.scope._active
