"""Existing synthetic owned protocol; no models, approvals or worker execution."""

import hashlib
import json
import statistics
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import pytest
from test_cold_accounted_native import native_segment
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import sql_facts as sql_facts

from sim2act import _cold_graph_structure_guard as structure
from sim2act import natural_spec_runtime as r
from sim2act.errors import DomainError


@contextmanager
def counts():
    from sim2act._cold_accounted_native import _Frontier
    monitoring = sys.monitoring
    slot = next(i for i in (4, 3, 5) if monitoring.get_tool(i) is None)
    monitoring.use_tool_id(slot, 'complete projected check witness')
    seen = dict(encode=0, refresh=0)
    codes = {r._cold_graph_bytes.__code__: 'encode', _Frontier.values.__code__: 'refresh'}

    def called(code, offset):
        seen[codes[code]] += 1

    monitoring.register_callback(slot, monitoring.events.PY_START, called)
    for code in codes:
        monitoring.set_local_events(slot, code, monitoring.events.PY_START)
    try:
        yield seen
    finally:
        for code in codes:
            monitoring.set_local_events(slot, code, 0)
        monitoring.free_tool_id(slot)


def test_actual_owned_frontier_current_refresh_alias_and_complete_cost(sql_facts, monkeypatch, tmp_path):
    f = sql_facts
    def background(graph, source, generated, candidate):
        graph.add('synthetic-unaccounted-background', [
            dict(id=f'unit-{i}', nested=[dict(text=f'synthetic material {i} ' * 12, value=i)])
            for i in range(2000)
        ])

    with f.store.tx() as c, native_segment(f, c, before_choose=background) as s:
        assert s.mode is not None
        frontier = s.graph._accounted_frontier
        assert structure._qualified(s.graph, _frontier=frontier)
        assert structure._frontier_plain(frontier, s.graph)
        for _ in range(5):
            s.graph.check(f.store, c)
        assert vars(frontier)['_structure_state'].capsule is not None
        with counts() as seen:
            s.graph.check(f.store, c)
        assert seen == dict(encode=0, refresh=1)
        batches = []
        for batch in range(3):
            row = {}
            for name in ('fast', 'legacy') if batch % 2 == 0 else ('legacy', 'fast'):
                with monkeypatch.context() as patch:
                    if name == 'legacy':
                        patch.setattr(structure, 'select_frontier', lambda frontier: None)
                    start = time.perf_counter()
                    with counts() as seen:
                        for _ in range(30):
                            s.graph.check(f.store, c)
                    row[name] = dict(seconds=time.perf_counter() - start, **seen)
            batches.append(row)
        assert all(row['fast']['encode'] == 0 and row['fast']['refresh'] == 30
            and row['legacy']['encode'] == 30 and row['legacy']['refresh'] == 30 for row in batches)
        report = dict(classification='EXISTING_SYNTHETIC_NATIVE_OWNED_PROJECTED_CONTENT_NOT_FULL_CONTROLLER',
            batches=batches, median_fast=statistics.median(x['fast']['seconds'] for x in batches),
            median_legacy=statistics.median(x['legacy']['seconds'] for x in batches),
            native_sha256=hashlib.sha256(Path(structure.native.__file__).read_bytes()).hexdigest())
        (tmp_path / 'projected-cost.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report))
    assert '_structure_state' not in vars(frontier)


def test_actual_owned_frontier_unknown_destination_and_instance_shadow_deopt(sql_facts):
    f = sql_facts
    with f.store.tx() as c, native_segment(f, c) as s:
        frontier = s.graph._accounted_frontier
        for _ in range(5):
            s.graph.check(f.store, c)
        calls = []

        class Unknown(dict):
            def __len__(self):
                calls.append('len')
                raise ValueError('unknown projection callback')

        original = frontier.projected
        frontier.projected = Unknown(original)
        try:
            assert structure.select_frontier(frontier) is None
            assert calls == []
            with pytest.raises(ValueError, match='unknown projection callback'):
                frontier.check()
            assert calls == ['len']
        finally:
            frontier.projected = original
        calls.clear()
        frontier.key = lambda: calls.append('key')
        try:
            assert structure.select_frontier(frontier) is None
            assert calls == []
        finally:
            del frontier.key


def test_frontier_active_short_circuit_preserves_original_falsey_value(sql_facts):
    f = sql_facts
    with f.store.tx() as c, native_segment(f, c) as s:
        frontier = s.graph._accounted_frontier
        calls = []

        class Falsey:
            def __bool__(self):
                calls.append('active')
                return False

        s.mode.active = Falsey()
        frontier.key = lambda: calls.append('key')
        try:
            with pytest.raises(DomainError, match='Native mutable frontier changed'):
                frontier.check()
            assert calls == ['active', 'active']
        finally:
            s.mode.active = True
            del frontier.key


def test_frontier_fresh_content_rekey_and_owner_binding(sql_facts):
    f = sql_facts
    value = dict(items=[1])

    def background(graph, source, generated, candidate):
        graph.add('synthetic-mutable-projection', value)

    with f.store.tx() as c, native_segment(f, c, before_choose=background) as s:
        frontier = s.graph._accounted_frontier
        for _ in range(5):
            s.graph.check(f.store, c)
        old_capsule = vars(frontier)['_structure_state'].capsule
        value['items'].append(2)
        try:
            with pytest.raises(DomainError, match='Native mutable frontier changed'):
                frontier.check()
            assert '_structure_state' not in vars(frontier)
        finally:
            value['items'].pop()
        for _ in range(5):
            s.graph.check(f.store, c)
        previous = frontier.expected
        s.graph.add('commit:first:context', dict(synthetic_projection_only=True))
        assert frontier.expected != previous and '_structure_state' not in vars(frontier)
        for _ in range(5):
            s.graph.check(f.store, c)
        scope_ = (frontier, s.graph.nonce, frontier.expected, s.graph.epoch, s.graph.phase)
        current = structure._frontier_values(frontier, s.graph)
        assert structure.native.matches_fast(old_capsule, current, scope_) is structure.native.UNSUPPORTED
    assert '_structure_state' not in vars(frontier)


def test_native_class_configuration_compares_all_items_without_getters():
    class Meta(type):
        pass

    class Sample(metaclass=Meta):
        first = object()
        second = object()

    metas = tuple((kind, type.__getattribute__(kind, '__mro__'),
        tuple(type.__getattribute__(kind, '__dict__').items())) for kind in (Meta, type, object))
    classes = ((Sample, Meta, Sample.__mro__, tuple(vars(Sample).items())),)
    native = structure.native
    assert native.same_classes(metas, classes) is True
    Sample.extra = 1
    assert native.same_classes(metas, classes) is False
    del Sample.extra
    assert native.same_classes(metas, classes) is True
    value = Sample.first
    del Sample.first
    Sample.first = value
    assert native.same_classes(metas, classes) is False
    assert native.same_classes((), ((object(), Meta, (), ()),)) is False
