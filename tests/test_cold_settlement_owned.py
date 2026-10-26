"""Isolated content representation, not seven-producer/runtime closure or G0."""

from contextlib import contextmanager

import pytest
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import sql_facts as sql_facts

from sim2act import _cold_settlement_owned as owned
from sim2act import natural_live_admission as gate
from sim2act import natural_spec_runtime as runtime
from sim2act import pb_natural_specs as pb
from sim2act._cold_accounted_budget import _Ledger, _Limits
from sim2act._cold_accounted_values import _Bounds, _Rejected
from sim2act.contracts import Limits
from sim2act.errors import DomainError

# Finite experimental allowance, never a product input limit or RSS promise.
BOUNDS = _Bounds(12000, 24000, 128, 1_000_000, 64_000_000)
LIMITS = _Limits(96_000_000, 900_000_000, 2_000_000_000, 4096)


def inventory(value):
    # Deliberately the SAME value for each inventory slot: this tests alias
    # preservation, and explicitly is NOT a witness of distinct fresh producers.
    return {name: {boundary: value for boundary in variants}
            for name, variants in owned._FAMILIES.items()}


@contextmanager
def capture(value):
    ledger = _Ledger(BOUNDS, LIMITS)
    builder = owned._Capture(ledger)
    try:
        yield builder.finish(value)
    finally:
        builder.close()
        assert not builder.done and not builder.nodes
        ledger.close()
        assert ledger.live == ledger.resident == 0


def test_complete_capture_keeps_model_raw_and_nested_hidden_row_aliases():
    model = Limits(max_requests=3, max_tools=4, max_repairs=1,
                   max_total_tokens=1000, max_output_tokens=100, run_seconds=300)
    raw = object.__getattribute__(model, '__dict__')
    shared = {'hidden': ['complete']}
    meta = SimpleResultMetaData(['visible'])
    keys = object.__getattribute__(meta, '_keys')
    row = RowMapping(meta, None, {'visible': 0, 'hidden_alias': 1}, ('ok', shared, shared))
    value = dict(model=model, raw=raw, row=row, keys=keys, shared=shared)
    with capture(value) as image:
        root = dict((image.nodes[k][1], v) for k, v in image.nodes[image.root][1])
        assert image.nodes[root['model']][1][1] == root['raw']
        storage = image.nodes[root['row']][1]
        assert storage[0] == root['keys']
        assert image.nodes[storage[1]][1][1] == root['shared']
        assert image.nodes[storage[1]][1][2] == root['shared']
        frozen = image.encoded
        raw['max_requests'] = 99
        shared['hidden'].append('changed')
        assert image.encoded == frozen
        assert image.nodes[dict((image.nodes[k][1], v) for k, v in
                               image.nodes[root['raw']][1])['max_requests']] == ('int', 3)


def test_cycle_nonfinite_and_foreign_row_callback_are_not_hidden():
    cyclic = []
    cyclic.append(cyclic)
    for value, message in [(cyclic, 'cycle'), (float('nan'), 'nonfinite')]:
        with pytest.raises(_Rejected, match=message), capture(value):
            pass

    class Foreign:
        armed = False

        def __hash__(self):
            assert not self.armed
            return 17

        def __eq__(self, other):
            pytest.fail('Foreign equality must never run')

    key = Foreign()
    index = {'visible': 0, key: 0}
    key.armed = True
    row = RowMapping(SimpleResultMetaData(['visible']), None, index, ('ok', b'hidden'))
    with capture({'nested': [row]}) as image:
        assert ('bytes', b'hidden') in image.nodes


def test_sqlite_handoff_is_private_owned_and_lifecycle_bound(sql_facts):
    f = sql_facts
    with f.store.tx() as c, pb._source_reads(f.store, c):
        roles = dict.fromkeys(('source', 'generate', 'platform', 'trial', 'per_use'))
        with runtime._cold_graph_read(f.worker, c, {'isolated': True}, roles, 'pre') as graph:
            model = gate._approved(f.store, c, f.user, f.contract, f.binding.approval_key)
            raw = gate._trial_typed_storage(gate.Approval, model)
            models = [(gate.Approval, model, raw)]
            graph.add('isolated-raw', raw)
            families = inventory(dict(approval=raw, saved=raw, strict=[True, 1, [1], (1,)]))
            graph.add(owned._ROOT, families)
            before = graph.input_bytes()
            selected = owned._select_complete(graph, families, models, BOUNDS, LIMITS)
            assert selected.route == 'OWNED'
            scope, handle = selected.scope, selected.handle
            first = scope.family(handle, 'authorities', 'first')
            second = scope.family(handle, 'authorities', 'second')
            assert first.same_node(second)
            assert type(first.field('strict').at(0).scalar()) is bool
            assert type(first.field('strict').at(1).scalar()) is int
            assert first.field('strict').at(2).tag == 'list'
            assert first.field('strict').at(3).tag == 'tuple'
            assert graph.input_bytes() == before  # private digest never enters old protocol
            old = model.approved_at
            try:
                model.approved_at = old - 1
                raw['approved_at'] = old - 2
                assert first.field('approval').field('approved_at').scalar() == old
                assert first.field('saved').field('approved_at').scalar() == old
            finally:
                model.approved_at = old
                raw['approved_at'] = old
            with pytest.raises(_Rejected, match='unissued'):
                scope.family(owned._Handle(), 'trial', 'base')
            forged = owned._View(scope, first._ref)
            with pytest.raises(_Rejected, match='unissued'):
                forged.field('approval')
            assert graph.input_bytes() == before
        with pytest.raises(DomainError):
            first.field('approval')
        assert not scope._active and scope._ledger.live == 0


def test_capacity_is_legacy_before_issuance_but_bad_inventory_is_not(sql_facts):
    f = sql_facts
    with f.store.tx() as c, pb._source_reads(f.store, c):
        roles = dict.fromkeys(('source', 'generate', 'platform', 'trial', 'per_use'))
        with runtime._cold_graph_read(f.worker, c, {'isolated': True}, roles, 'pre') as graph:
            families = inventory({'value': list(range(20))})
            graph.add(owned._ROOT, families)
            selected = owned._select_complete(graph, families, [],
                                              BOUNDS._replace(nodes=2), LIMITS)
            assert selected.route == 'LEGACY' and selected.scope is selected.handle is None
            assert graph.active
    with pytest.raises(DomainError, match='complete actual settlement inventory'), \
            f.store.tx() as c, pb._source_reads(f.store, c):
        with runtime._cold_graph_read(f.worker, c, {'isolated': True}, roles, 'pre') as graph:
            families = inventory({'value': 1})
            del families['source']['second']
            graph.add(owned._ROOT, families)
            owned._select_complete(graph, families, [], BOUNDS, LIMITS)


@pytest.mark.parametrize('drift', ['stop', 'settings', 'binding', 'write'])
def test_dynamic_frontier_still_rejects_after_handoff(sql_facts, drift):
    from sqlalchemy import update

    from sim2act.db import runs

    f = sql_facts
    selected = None
    try:
        with pytest.raises(DomainError), f.store.tx() as c, pb._source_reads(f.store, c):
            roles = dict.fromkeys(('source', 'generate', 'platform', 'trial', 'per_use'))
            with runtime._cold_graph_read(f.worker, c, {'isolated': True}, roles, 'pre') as graph:
                families = inventory({'value': 1})
                graph.add(owned._ROOT, families)
                selected = owned._select_complete(graph, families, [], BOUNDS, LIMITS)
                assert selected.route == 'OWNED'
                view = selected.scope.family(selected.handle, 'trial', 'base')
                if drift == 'stop':
                    f.worker.stop.set()
                elif drift == 'settings':
                    object.__setattr__(f.settings, 'max_output_tokens', f.settings.max_output_tokens + 1)
                elif drift == 'binding':
                    object.__setattr__(f.binding, 'version', 'changed')
                else:
                    c.execute(update(runs).where(runs.c.id == f.gen_id).values(error={'test': True}))
                view.field('value')
    finally:
        if drift == 'stop':
            f.worker.stop.clear()
        elif drift == 'settings':
            object.__setattr__(f.settings, 'max_output_tokens', f.settings.max_output_tokens - 1)
        elif drift == 'binding':
            from sim2act.spec_production import VERSION
            object.__setattr__(f.binding, 'version', VERSION)
    assert selected is not None and not selected.scope._active
    assert selected.scope._ledger.live == selected.scope._ledger.resident == 0


@pytest.mark.parametrize('failure', ['construct', 'finish'])
def test_whole_inventory_read_set_required_and_memory_error_never_falls_back(sql_facts, monkeypatch, failure):
    f = sql_facts
    roles = dict.fromkeys(('source', 'generate', 'platform', 'trial', 'per_use'))
    with pytest.raises(DomainError, match='original full graph read set'), \
            f.store.tx() as c, pb._source_reads(f.store, c):
        with runtime._cold_graph_read(f.worker, c, {'isolated': True}, roles, 'pre') as graph:
            owned._select_complete(graph, inventory({'unpinned': []}), [], BOUNDS, LIMITS)
    seen = []
    with pytest.raises(MemoryError), f.store.tx() as c, pb._source_reads(f.store, c):
        with runtime._cold_graph_read(f.worker, c, {'isolated': True}, roles, 'pre') as graph:
            families = inventory({'value': 1})
            graph.add(owned._ROOT, families)

            def fail(self, value):
                raise MemoryError('controlled construction failure')

            if failure == 'construct':
                def fail_constructor(self, ledger):
                    ledger.reserve(units=128)
                    seen.append(ledger)
                    raise MemoryError('controlled partial constructor failure')

                monkeypatch.setattr(owned._Capture, '__init__', fail_constructor)
            else:
                monkeypatch.setattr(owned._Capture, 'finish', fail)
            owned._select_complete(graph, families, [], BOUNDS, LIMITS)
            pytest.fail('MemoryError must not return LEGACY')
    assert not graph.active
    assert all(not b.active and b.live == b.resident == 0 for b in seen)


def test_wide_shared_dag_resident_edges_are_prepaid(sql_facts):
    f = sql_facts
    with f.store.tx() as c, pb._source_reads(f.store, c):
        roles = dict.fromkeys(('source', 'generate', 'platform', 'trial', 'per_use'))
        with runtime._cold_graph_read(f.worker, c, {'isolated': True}, roles, 'pre') as graph:
            shared = {'small': 1}
            families = inventory({'edges': [shared] * 2000})
            graph.add(owned._ROOT, families)
            result = owned._select_complete(graph, families, [], BOUNDS,
                                            LIMITS._replace(resident=100_000))
            assert result.route == 'LEGACY' and result.reason == 'resident'
            assert result.scope is None and graph.active


def test_model_schema_keys_are_gated_before_foreign_equality(monkeypatch):
    model = Limits(max_requests=3, max_tools=4, max_repairs=1,
                   max_total_tokens=1000, max_output_tokens=100, run_seconds=300)

    class Foreign:
        def __hash__(self):
            return 17

        def __eq__(self, other):
            pytest.fail('Unknown schema equality must not execute')

    fields = dict(type.__getattribute__(Limits, '__pydantic_fields__'))
    fields[Foreign()] = fields.pop('max_requests')
    monkeypatch.setattr(Limits, '__pydantic_fields__', fields)
    with pytest.raises(_Rejected, match='complete fixed settlement model'), capture(model):
        pass
