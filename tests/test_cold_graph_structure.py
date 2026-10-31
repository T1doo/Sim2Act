"""Complete structure/alias, lifecycle and original-path fallback regressions."""

import copyreg
import itertools
import struct
import sys
import time
from contextlib import contextmanager

import pytest
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from sqlalchemy.sql.elements import quoted_name
from test_cold_binding_fact_leaves import graph_origin as local_origin
from test_cold_extract_parse import no_external_transport as no_external_transport
from test_loaded_raw_segment import scope

from sim2act import _cold_graph_structure as native
from sim2act import _cold_graph_structure_guard as guard_code
from sim2act import natural_spec_runtime as r
from sim2act import pb_natural_specs as pb
from sim2act.contracts import Limits
from sim2act.errors import DomainError


def arguments():
    return (RowMapping, Limits, quoted_name, r._cold_graph_row_storage, r._cold_graph_limit_values)


def check_change(value, change):
    identity = (object(), object(), "synthetic-key", 0, "post")
    key = r._cold_graph_bytes(value)
    saved = native.snapshot(value, *arguments(), identity)
    assert saved is not native.UNSUPPORTED
    assert native.matches_fast(saved, value, identity) is True
    change(value)
    wanted = r._cold_graph_bytes(value) == key
    assert native.matches_fast(saved, value, identity) is wanted


def test_alias_split_merge_swap_matrix():
    identity = (object(), object(), "synthetic-key", 0, "post")
    for string in (False, True):
        values = [bytes(bytearray(b"synthetic alias " * 8)) for _ in range(3)]
        if string:
            values = [value.decode() for value in values]
        assert len({id(value) for value in values}) == 3
        for before in itertools.product(range(3), repeat=3):
            original = [values[i] for i in before]
            saved = native.snapshot(original, *arguments(), identity)
            key = r._cold_graph_bytes(original)
            for after in itertools.product(range(3), repeat=3):
                current = [values[i] for i in after]
                assert native.matches_fast(saved, current, identity) is (
                    r._cold_graph_bytes(current) == key)


@pytest.mark.parametrize("change", [
    lambda v: v["nested"][0].append(2),
    lambda v: v.__setitem__("signed", -0.0),
    lambda v: v.__setitem__("signed", False),
    lambda v: v.__setitem__("nested", tuple(v["nested"])),
    lambda v: v.__setitem__("ordered", {"b": 2, "a": 1}),
    lambda v: v.__setitem__("nan", struct.unpack('>d', bytes.fromhex('7ff8000000000002'))[0]),
])
def test_complete_content_type_order_float_bits(change):
    check_change(dict(nested=[[1]], signed=0.0, ordered=dict(a=1, b=2),
        nan=struct.unpack('>d', bytes.fromhex('7ff8000000000001'))[0]), change)


def limit():
    return Limits(max_requests=2, max_tools=4, max_repairs=0,
        max_total_tokens=64000, max_output_tokens=1024, run_seconds=300)


def test_limits_generated_fields_reducer_labels_and_global_aliases():
    full = limit()
    fields = [key for key, _ in r._cold_graph_limit_values(full)]
    labels = [value for value in r._ColdGraphPickler.reducer_override.__code__.co_consts
        if type(value) is str and value in ('limits-v1', 'quoted-name-v1', 'row-storage-v2')]
    globals_ = [r._cold_graph_pickle_marker.__module__, r._cold_graph_pickle_marker.__qualname__]
    row = RowMapping(SimpleResultMetaData(['id']), None, {'id': 0}, ('synthetic',))
    for key in fields + labels + globals_:
        value = [full, quoted_name('synthetic_key', None), row, {key: 1}]
        check_change(value, lambda v, k=key: v.__setitem__(3, {k.encode().decode(): 1}))


def test_row_hidden_data_and_metadata_cross_aliases():
    hidden = [1]
    keys = ['id', 'visible']
    meta = SimpleResultMetaData(keys)
    meta._keys = keys
    data = ('synthetic', 'shown', hidden)
    row = RowMapping(meta, None, {'id': 0, 'visible': 1}, data)
    check_change(dict(row=row, keys=keys, data=data), lambda v: hidden.append(2))
    hidden.clear()
    check_change(dict(row=row, keys=keys, data=data), lambda v: v.__setitem__('keys', list(keys)))


def test_scope_binding_and_bounded_unsupported():
    identity = (object(), object(), "synthetic-key", 0, "post")
    value = dict(a=[1])
    saved = native.snapshot(value, *arguments(), identity)
    assert native.matches_fast(saved, value, (object(), *identity[1:])) is native.UNSUPPORTED
    assert native.matches_fast(saved, value, (*identity[:4], 'pre')) is native.UNSUPPORTED
    assert native.snapshot(dict(a=1 << 100), *arguments(), identity) is native.UNSUPPORTED
    deep = []
    for _ in range(70):
        deep = [deep]
    assert native.snapshot(deep, *arguments(), identity) is native.UNSUPPORTED
    cyclic = []
    cyclic.append(cyclic)
    assert native.snapshot(cyclic, *arguments(), identity) is native.UNSUPPORTED


def warm(f, c, graph):
    assert guard_code._qualified(graph)
    for _ in range(5):
        graph.check(f.store, c)
    assert vars(graph)['_structure_state'].capsule is not None


@pytest.mark.parametrize('producer',['compile_preview','validate_source_family'])
def test_replaced_production_function_still_rejects_before_callback(local_origin,monkeypatch,producer):
    from sim2act import apps
    f=local_origin
    calls=[]
    def foreign(*args,**kwargs):
        calls.append(producer)
        pytest.fail('Changed production code must not run')
    monkeypatch.setattr(apps,producer,foreign)
    with f.store.tx() as c,pb._source_reads(f.store,c):
        with pytest.raises(DomainError,match='Complete Source code changed'):
            with scope(f,c):
                pytest.fail('Changed production code cannot open a graph')
    assert calls==[]


@contextmanager
def rejecting_scope(f, c):
    finished = False
    with pytest.raises(DomainError):
        with scope(f, c) as graph:
            yield graph
            finished = True
    assert finished, "The body must reach its own rejection assertions"
    assert not graph.active and '_structure_state' not in vars(graph)


def test_complete_graph_match_drops_encoding_but_dynamic_is_live(local_origin):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c), rejecting_scope(f, c) as graph:
        graph.add('structure-content', dict(deep=[[1]]))
        warm(f, c, graph)
        start = graph._diagnostic_counts[1]
        graph.check(f.store, c)
        assert graph._diagnostic_counts[1] == start
        graph.inputs['structure-content']['deep'][0].append(2)
        with pytest.raises(DomainError):
            graph.check(f.store, c)
        assert not graph.active and '_structure_state' not in vars(graph)


@pytest.mark.parametrize('change', ['stop', 'epoch', 'scope', 'role', 'contract'])
def test_current_dynamic_or_content_changes_still_reject(local_origin, change):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c), rejecting_scope(f, c) as graph:
        # A synthetic unit token exercises the original active-interval stop gate.
        f.worker._settlement_interval = (time.monotonic() + 120, time.time() + 120)
        warm(f, c, graph)
        if change == 'stop':
            f.worker.stop.set()
        elif change == 'epoch':
            c.info['source_proof_write_epoch'] = graph.epoch + 1
        elif change == 'scope':
            graph.scope[0] = object()
        elif change == 'role':
            graph.role_limits['source'].max_requests -= 1
        else:
            graph.binding.contract.caps.run_seconds -= 1
        with pytest.raises(DomainError):
            graph.check(f.store, c)
        assert not graph.active and '_structure_state' not in vars(graph)


def test_add_rebuilds_and_unknown_configuration_uses_original_sha(local_origin, monkeypatch):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c), scope(f, c) as graph:
        warm(f, c, graph)
        graph.add('structure-next', [1])
        assert '_structure_state' not in vars(graph)
        warm(f, c, graph)
        with monkeypatch.context() as patch:
            patch.setattr(r._cold_graph_pickle_marker, '__name__', '__newobj__')
            assert not guard_code._qualified(graph)
        defaults = r._ColdGraphRead.input_bytes.__kwdefaults__
        try:
            defaults['_snapshot_values'] = True
            assert not guard_code._qualified(graph)
            with pytest.raises(TypeError):
                graph.input_key()
        finally:
            defaults['_snapshot_values'] = False
        old_registry = dict(copyreg._extension_registry)
        try:
            copyreg._extension_registry[('synthetic', 'never_serialized')] = 123
            assert not guard_code._qualified(graph)
            start = graph._diagnostic_counts[1]
            graph.check(f.store, c)
            assert graph._diagnostic_counts[1] == start + 1
        finally:
            copyreg._extension_registry.clear()
            copyreg._extension_registry.update(old_registry)
        assert '_structure_state' not in vars(graph)


def test_native_original_reducer_error_is_not_replayed(local_origin):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c), rejecting_scope(f, c) as graph:
        row = RowMapping(SimpleResultMetaData(['id']), None, {'id': 0}, ('synthetic',))
        value = dict(row=row)
        graph.add('structure-row', value)
        warm(f, c, graph)
        value['row'] = RowMapping(object(), None, {'id': 0}, ('synthetic',))
        start = graph._diagnostic_counts[1]
        with pytest.raises(DomainError):
            graph.check(f.store, c)
        assert graph._diagnostic_counts[1] == start
        assert not graph.active and '_structure_state' not in vars(graph)


def test_unknown_graph_binding_and_row_lookup_getters_deopt_before_callbacks(local_origin, monkeypatch):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c), scope(f, c) as graph:
        warm(f, c, graph)
        calls = []
        with monkeypatch.context() as patch:
            patch.setattr(r._ColdGraphRead, 'key', property(lambda self: calls.append(1)), raising=False)
            assert guard_code.select(graph) is None
            assert calls == []

        with monkeypatch.context() as patch:
            patch.setattr(type(graph.binding), 'account_id', property(lambda self: calls.append(1)), raising=False)
            assert guard_code.select(graph) is None
            assert calls == []
        with monkeypatch.context() as patch:
            def callback(*args):
                calls.append(1)
            patch.setattr(r, '_COLD_ROW_LOOKUP', callback)
            patch.setattr(r._row_native_code, '_RAW_ROW_LOOKUP', callback)
            assert guard_code.select(graph) is None
            assert calls == []


def test_pre_scope_fresh_complete_walk_and_original_frontier_selection(local_origin):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c), r._cold_graph_read(
        f.worker, c, f.inputs, f.roles, 'pre'
    ) as graph:
        graph.add('pre-structure', [[1]])
        warm(f, c, graph)
        saved = vars(graph)['_structure_state'].capsule
        scope_ = (graph, graph.nonce, graph.key, graph.epoch, graph.phase)
        assert native.matches_fast(saved, graph.input_bytes(_snapshot_values=True),
            (*scope_[:4], 'post')) is native.UNSUPPORTED
        start = graph._diagnostic_counts[1]
        graph.check(f.store, c)
        assert graph._diagnostic_counts[1] == start
        # Qualification does not consume or validate an accounted frontier.
        # Only the original Graph.check frontier branch may handle one.
        vars(graph)['_accounted_frontier'] = object()
        try:
            assert guard_code.select(graph) is None
            assert '_structure_state' not in vars(graph)
        finally:
            vars(graph)['_accounted_frontier'] = None
        vars(graph)['_typed_native_candidate'] = object()
        try:
            assert guard_code.select(graph) is None
        finally:
            vars(graph)['_typed_native_candidate'] = None
        warm(f, c, graph)


def test_pre_scope_content_change_still_invalidates(local_origin):
    f = local_origin
    finished = False
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with r._cold_graph_read(f.worker, c, f.inputs, f.roles, 'pre') as graph:
                graph.add('pre-structure', [[1]])
                warm(f, c, graph)
                graph.inputs['pre-structure'][0].append(2)
                with pytest.raises(DomainError):
                    graph.check(f.store, c)
                assert not graph.active and '_structure_state' not in vars(graph)
                finished = True
        assert finished


def test_frontier_branch_clears_snapshot_and_keeps_original_rejection(local_origin):
    from sim2act._cold_accounted_native import _Frontier

    f = local_origin
    finished = False
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with r._cold_graph_read(f.worker, c, f.inputs, f.roles, 'pre') as graph:
                warm(f, c, graph)
                # Deliberately unissued: the ORIGINAL frontier must reject it.
                # It supplies no mock check method, permit or accepted result.
                frontier = object.__new__(_Frontier)
                frontier.graph, frontier.mode = graph, object()
                vars(graph)['_accounted_frontier'] = frontier
                monitoring = sys.monitoring
                slot = next(i for i in (4, 3, 5) if monitoring.get_tool(i) is None)
                monitoring.use_tool_id(slot, 'original frontier branch witness')
                calls = []

                def entered(*args):
                    calls.append('_structure_state' not in vars(graph))

                monitoring.register_callback(slot, monitoring.events.PY_START, entered)
                monitoring.set_local_events(slot, _Frontier.check.__code__, monitoring.events.PY_START)
                try:
                    with pytest.raises(DomainError):
                        graph.check(f.store, c)
                finally:
                    monitoring.set_local_events(slot, _Frontier.check.__code__, 0)
                    monitoring.free_tool_id(slot)
                # The newer complete receipt gate rejects this unissued mode
                # before dispatching _Frontier.check; no authority is inferred.
                assert calls == []
                assert not graph.active and '_structure_state' not in vars(graph)
                finished = True
        assert finished


@pytest.mark.parametrize('mode',['absent','foreign','missing-candidate'])
def test_malformed_frontier_fails_controlled_before_foreign_attribute(mode):
    from sim2act._cold_accounted_native import _Frontier
    from sim2act._cold_accounted_receipts import _receipt_for_frontier
    from sim2act.cold_accounted import _OwnedPrewriteMode
    frontier=object.__new__(_Frontier)
    calls=[]
    class Foreign:
        @property
        def _native(self):
            calls.append('foreign descriptor')
            raise AssertionError('Must reject the type before reading a foreign mode')
    if mode=='foreign':frontier.mode=Foreign()
    elif mode=='missing-candidate':frontier.mode=object.__new__(_OwnedPrewriteMode)
    with pytest.raises(DomainError) as failed:_receipt_for_frontier(frontier)
    assert failed.value.code=='VERSION_CONFLICT'
    assert calls==[]


@pytest.mark.parametrize('owner',['frontier','mode'])
def test_frontier_storage_subclass_rejects_before_iteration(owner):
    from sim2act._cold_accounted_native import _Frontier
    from sim2act._cold_accounted_receipts import _receipt_for_frontier
    from sim2act.cold_accounted import _OwnedPrewriteMode
    frontier=object.__new__(_Frontier)
    frontier.mode=object.__new__(_OwnedPrewriteMode)
    calls=[]
    class Foreign(dict):
        def __iter__(self):
            calls.append('foreign iteration')
            raise AssertionError('Must reject foreign storage before iteration')
    target=frontier if owner=='frontier' else frontier.mode
    target.__dict__=Foreign(vars(target))
    with pytest.raises(DomainError) as failed:_receipt_for_frontier(frontier)
    assert failed.value.code=='VERSION_CONFLICT'
    assert calls==[]
