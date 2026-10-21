"""Offline native-storage and real SQLite core integration, never G0/Worker IO."""

import json

import pytest
from accounted_sqlite_fixture import segment
from sqlalchemy import update
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from test_cold_accounted_sqlite import (
    forbid_execution as forbid_execution,
)
from test_cold_accounted_sqlite import (
    resolve,
)
from test_cold_accounted_sqlite import (
    sql_facts as sql_facts,
)

from sim2act import _cold_accounted_budget as budget
from sim2act import cold_accounted as owned
from sim2act import pa_trial_dispatch as dispatch
from sim2act import production_trial_policy as policy
from sim2act._cold_accounted_values import _Bounds, _equal, _freeze, _Node, _node
from sim2act.contracts import Limits
from sim2act.db import grants, runs
from sim2act.errors import DomainError

# Explicit finite synthetic data allowance, NOT product settings or qualification.
BOUNDS = _Bounds(60000, 120000, 128, 8 * 1024**2, 64 * 1024**2)
LIMITS = budget._Limits(64 * 1024**2, 256 * 1024**2, 10000000000, 16000)


def test_projection_preserves_shared_hidden_data_and_ignores_foreign_callbacks():
    calls = []

    class Foreign:
        def __hash__(self):
            calls.append('hash')
            return 42
        def __eq__(self, other):
            calls.append('eq')
            raise AssertionError('foreign callback')

    shared = {'hidden': ['all']}
    foreign = Foreign()
    index = {'visible': 0, 'hidden_alias': 1, foreign: 0}
    calls.clear()
    row = RowMapping(SimpleResultMetaData(['visible']), None, index, ('ok', shared, shared))
    ledger = budget._Ledger(BOUNDS, LIMITS)
    with ledger.projection() as p:
        result = p.row(row, ('run',))
        keys, data, safe = p.sidecars[0][1]
        assert result == {'visible': 'ok'}
        assert data[1] is data[2] and data[1] is not shared
        assert safe == {'visible': 0, 'hidden_alias': 1}
        assert keys == ['visible'] and calls == []
        assert ledger.work >= len(index)
    assert ledger.live == 0 and ledger.work > 0
    ledger.close()


def test_foreign_index_scan_charged_before_lookup_and_oversize_hidden_stops():
    row = RowMapping(SimpleResultMetaData(['visible']), None,
                     {'visible': 0, **{object(): 0 for _ in range(1000)}}, ('ok',))
    ledger = budget._Ledger(BOUNDS, LIMITS._replace(work=100))
    with pytest.raises(budget._Capacity), ledger.projection() as p:
        p.row(row, ('run',))
    assert ledger.live == 0
    row = RowMapping(SimpleResultMetaData(['visible']), None, {'visible': 0},
                     ('ok', b'x' * 4096))
    ledger = budget._Ledger(BOUNDS._replace(leaf_bytes=1000), LIMITS)
    with pytest.raises(budget._Capacity), ledger.projection() as p:
        p.row(row, ('run',))
    assert ledger.live == 0


def test_preallocation_blocks_encoder_and_reservation_lifetimes(monkeypatch):
    ledger = budget._Ledger(BOUNDS, LIMITS._replace(peak=40000))
    monkeypatch.setattr(budget, '_freeze', lambda *args: pytest.fail('encoder before reservation'))
    with pytest.raises(budget._Capacity), ledger.projection() as p:
        copied = p.copy(b'abc' * 1000)
        ledger.encode(copied, p)
    assert ledger.live == 0
    before = ledger.work
    ticket = ledger.reserve(units=20)
    ticket.close()
    ticket.close()  # idempotent, cannot underflow or refund cumulative work
    assert ledger.work == before + 1
    ledger.close()
    assert ledger.live == ledger.resident == 0


def test_ledger_work_never_refunds_or_invokes_foreign_kind():
    ledger = budget._Ledger(BOUNDS, LIMITS)
    ledger.spend(5)
    for invalid in (-1, True, 0.5):
        with pytest.raises(DomainError):
            ledger.spend(invalid)
    assert ledger.work == 5
    class Foreign:
        def __eq__(self, other):
            pytest.fail('unknown reservation kind equality')
    with pytest.raises(ValueError):
        ledger.reserve(Foreign())
    assert ledger.work == 5


def test_copy_is_owned_and_pair_comparison_has_its_own_budget():
    ledger = budget._Ledger(BOUNDS, LIMITS)
    shared = ['before']
    value = [shared, shared]
    with ledger.projection() as p:
        prepared = p.copy(value)
        shared.append('later')
        assert prepared == [['before'], ['before']] and prepared[0] is prepared[1]
        packet, lease = ledger.encode(prepared, p, resident=True)
    assert ledger.resident > 0
    resident = ledger.live
    with ledger.snapshot([['before'], ['before']]) as other:
        assert ledger.equal(_node(packet), _node(other))
        assert ledger.live > resident
    assert ledger.live == resident
    assert _equal(_node(packet), _node(_freeze(prepared, BOUNDS)))
    lease.close()
    assert ledger.live == 0


@pytest.mark.parametrize('value,method', [([0] * 1000, 'sequence'),
                                         ({str(n): n for n in range(1000)}, 'items'),
                                         ({'x' * 10000: None}, 'items'),
                                         ('x' * 10000, 'scalar')])
def test_comparison_work_is_prepaid_before_wide_or_long_access(monkeypatch, value, method):
    a = _freeze(value, BOUNDS)
    long_key = type(value) is dict and len(value) == 1
    other = {(' ' + key)[1:]: item for key, item in value.items()} if long_key else value
    b = _freeze(other, BOUNDS)
    ledger = budget._Ledger(BOUNDS, LIMITS._replace(work=100 if long_key else 2))
    monkeypatch.setattr(_Node, method, lambda *args: pytest.fail('comparison before work reserve'))
    with pytest.raises(budget._Capacity):
        ledger.equal(_node(a), _node(b))
    assert ledger.live == 0


@pytest.mark.parametrize('value,method', [({'x'*10000: 1}, 'items'), ([0]*1000, 'sequence')])
def test_budgeted_consumer_access_prepays_width_and_key_content(monkeypatch, value, method):
    packet = _freeze(value, BOUNDS)
    ledger = budget._Ledger(BOUNDS, LIMITS)
    node = _node(packet, ledger)
    ledger.limits = ledger.limits._replace(work=ledger.work + 20)
    # The access must stop before it constructs descendant wrapper objects.
    from sim2act import _cold_accounted_values as values
    monkeypatch.setattr(values, '_node_ref',
                        lambda *a: pytest.fail('consumer view allocation before fuel'))
    with pytest.raises(budget._Capacity):
        getattr(node, method)()
    ledger.close()
    assert ledger.live == 0


def test_budgeted_missing_field_does_not_copy_external_name_into_error():
    packet = _freeze({}, BOUNDS)
    ledger = budget._Ledger(BOUNDS, LIMITS)
    with pytest.raises(DomainError) as error:
        _node(packet, ledger).get('x'*1000000)
    assert len(str(error.value)) < 200
    ledger.close()


@pytest.mark.parametrize('value', [float('nan'), float('inf')])
def test_nonfinite_is_not_capacity(value):
    ledger = budget._Ledger(BOUNDS, LIMITS)
    with pytest.raises(DomainError) as error, ledger.projection() as p:
        p.copy(value)
    assert not isinstance(error.value, budget._Capacity)


def test_cycle_and_unknown_have_different_error_classes():
    ledger = budget._Ledger(BOUNDS, LIMITS)
    cycle = []
    cycle.append(cycle)
    with pytest.raises(DomainError) as error, ledger.projection() as p:
        p.copy(cycle)
    assert not isinstance(error.value, budget._Capacity)
    with pytest.raises(budget._Unsupported), ledger.projection() as p:
        p.copy(object())


def test_shared_dag_has_bounded_work_and_longest_reused_path():
    ledger = budget._Ledger(BOUNDS, LIMITS)
    value = b'x'
    for _ in range(80):
        value = [value, value]
    with ledger.projection() as p:
        result = p.copy(value)
        assert p.nodes == 81 and p.edges == 160
        assert result[0] is result[1]
    tail = [['x']]
    with pytest.raises(budget._Capacity), budget._Ledger(
        BOUNDS._replace(depth=19), LIMITS
    ).projection() as p:
        p.copy([tail, [tail]])  # effective native depth3 after wrapper headroom


@pytest.mark.parametrize('change', ['extra', 'private', 'missing', 'selected'])
def test_fixed_model_storage_drift_is_never_capacity(change):
    value = policy.Outcome(outcome='UNKNOWN', response_sha256='0'*64, response_ascii_bytes=0)
    if change == 'extra':
        object.__setattr__(value, '__pydantic_extra__', {})
    elif change == 'private':
        object.__setattr__(value, '__pydantic_private__', {})
    elif change == 'missing':
        del value.__dict__['outcome']
    else:
        object.__getattribute__(value, '__pydantic_fields_set__').add('not_a_field')
    ledger = budget._Ledger(BOUNDS, LIMITS)
    with pytest.raises(DomainError) as error, ledger.projection() as p:
        p.copy(value, typed=True)
    assert not isinstance(error.value, budget._Capacity)


def test_raw_hidden_model_is_not_silently_normalized_or_memo_reused():
    value = policy.Outcome(outcome='UNKNOWN', response_sha256='0'*64, response_ascii_bytes=0)
    ledger = budget._Ledger(BOUNDS, LIMITS)
    with ledger.projection() as p:
        wrapped = [value]
        assert type(p.copy(wrapped, typed=True)[0]) is dict
        with pytest.raises(budget._Unsupported):
            p.copy(wrapped)  # same objects, distinct adaptation domain


def count_producers(monkeypatch):
    seen = []
    original = dispatch._graph_stage_accounted

    def counted(*args, **kwargs):
        seen.append(args[7])
        assert kwargs.get('_owned') is None
        return original(*args, **kwargs)
    monkeypatch.setattr(dispatch, '_graph_stage_accounted', counted)
    monkeypatch.setattr(owned._AccountedScope, 'issue',
                        lambda *a: pytest.fail('must not rerun original producer'))
    return seen


def test_real_sqlite_joint_owned_and_consumer_snapshots(sql_facts, monkeypatch, tmp_path):
    f = sql_facts
    # Baseline uses the explicit LEGACY cohort too: no additive issue() producer.
    with f.store.tx() as c, segment(f, c, cohort=(BOUNDS._replace(nodes=1), LIMITS)) as old:
        assert old.cohort.route == 'LEGACY'
        baseline = resolve(old)
    seen = count_producers(monkeypatch)
    result = None
    with f.store.tx() as c, segment(f, c, cohort=(BOUNDS, LIMITS)) as s:
        result = s.cohort
        assert result.route == 'OWNED' and seen == ['source', 'generate']
        assert len(s.source.actual) == 2 and len(s.generated.actual) == 3
        resident = result.ledger.resident
        candidate = resolve(s, _owned=s.mode)
        assert candidate == baseline
        dispatch._graph_pb_archive_chain(s.graph, f.store, c, f.binding,
                                        s.state, candidate, s.source, _owned=s.mode)
        # Returned Node/tuple views conservatively retain their charges until
        # scope close; temporary packet/parse/comparison tickets are released.
        assert result.ledger.live == result.ledger.resident >= resident
        assert result.ledger.peak > result.ledger.resident and result.ledger.work > 0
        assert seen == ['source', 'generate']
        cost = {
            'route': result.route, 'producer_calls': seen, 'receipt_equal': candidate == baseline,
            'resident_units': result.ledger.resident, 'peak_units': result.ledger.peak,
            'work_units': result.ledger.work,
            'source_encoded_bytes': len(s.scope._issued[s.source.handle][1].encoded),
            'generate_encoded_bytes': len(s.scope._issued[s.generated.handle][1].encoded),
            'units_are_not_RSS_or_process_memory_bound': True,
        }
    assert result.ledger.live == result.ledger.resident == 0
    assert not result.mode.active and not result.mode.scope._issued
    cost.update(work_units=result.ledger.work, peak_units=result.ledger.peak,
                resident_after_close=result.ledger.resident, live_after_close=result.ledger.live,
                issued_after_close=len(result.mode.scope._issued))
    (tmp_path / 'cohort-cost.json').write_text(json.dumps(cost, indent=2) + '\n')


@pytest.mark.parametrize('role', ['source', 'generate'])
def test_either_capacity_selects_single_legacy_without_half_issuance(sql_facts, monkeypatch, role):
    original = owned._capture_bounded
    seen = count_producers(monkeypatch)
    attempted = []

    def small(facts, current, *args):
        attempted.append(current)
        if current == role:
            raise budget._Capacity('test finite representation allowance')
        return original(facts, current, *args)
    monkeypatch.setattr(owned, '_capture_bounded', small)
    f = sql_facts
    with f.store.tx() as c, segment(f, c, cohort=(BOUNDS, LIMITS)) as s:
        assert s.cohort.route == 'LEGACY' and s.mode is None
        assert seen == ['source', 'generate']
        assert not s.cohort._probe.scope._issued
        assert s.cohort.ledger.live == 0
        assert type(s.source) is type(s.generated) is tuple
        assert resolve(s).public_receipt['source_run_id'] == f.source_id
    assert attempted == (['source'] if role == 'source' else ['source', 'generate'])


@pytest.mark.parametrize('role', ['source', 'generate'])
def test_real_hidden_storage_capacity_is_joint_legacy(sql_facts, monkeypatch, role):
    # Real original producer/query/guards, followed by a synthetic native hidden
    # sidecar carrier. A fixed select cannot naturally have the extra position.
    seen = count_producers(monkeypatch)
    original = dispatch._graph_stage_accounted
    injected = []

    def hidden(*args, **kwargs):
        facts = original(*args, **kwargs)
        if args[7] == role:
            row = facts[0]
            data = object.__getattribute__(row, '_data')
            carrier = RowMapping(object.__getattribute__(row, '_parent'), None,
                                 object.__getattribute__(row, '_key_to_index'),
                                 (*data, b'x' * 1024**2))
            facts = (carrier, *facts[1:])
            injected.append(carrier)
        return facts
    monkeypatch.setattr(dispatch, '_graph_stage_accounted', hidden)
    f = sql_facts
    with f.store.tx() as c, segment(f, c, cohort=(BOUNDS._replace(leaf_bytes=900000), LIMITS)) as s:
        assert s.cohort.route == 'LEGACY' and seen == ['source', 'generate']
        selected = s.source if role == 'source' else s.generated
        assert selected[0] is injected[0]  # same batch, no fallback reread/producer
        assert s.cohort.ledger.live == 0 and not s.cohort._probe.scope._issued
        assert resolve(s).public_receipt['source_run_id'] == f.source_id


def test_legacy_supported_hidden_limits_model_selects_representation_fallback(sql_facts, monkeypatch):
    seen = count_producers(monkeypatch)
    original = dispatch._graph_stage_accounted
    hidden = Limits(max_requests=4, max_tools=4, max_repairs=1, max_total_tokens=64000,
                    max_output_tokens=1024, run_seconds=300)
    def with_model(*args, **kwargs):
        facts = original(*args, **kwargs)
        if args[7] == 'source':
            row = facts[0]
            carrier = RowMapping(object.__getattribute__(row, '_parent'), None,
                                 object.__getattribute__(row, '_key_to_index'),
                                 (*object.__getattribute__(row, '_data'), hidden))
            return (carrier, *facts[1:])
        return facts
    monkeypatch.setattr(dispatch, '_graph_stage_accounted', with_model)
    f = sql_facts
    with f.store.tx() as c, segment(f, c, cohort=(BOUNDS, LIMITS)) as s:
        assert s.cohort.route == 'LEGACY' and seen == ['source', 'generate']
        assert object.__getattribute__(s.source[0], '_data')[-1] is hidden
        assert resolve(s).public_receipt['source_run_id'] == f.source_id


def test_failure_after_issuance_is_closed_without_fallback(sql_facts, monkeypatch):
    f = sql_facts
    with pytest.raises(budget._Capacity), f.store.tx() as c, segment(
        f, c, cohort=(BOUNDS, LIMITS)
    ) as s:
        ledger = s.cohort.ledger
        seen = s.cohort
        # A subsequent real comparison snapshot has insufficient remaining fuel.
        ledger.limits = ledger.limits._replace(work=ledger.work + 1)
        owned._same_native(s.source.run, {'grow': 'snapshot'})
    assert seen.route == 'OWNED' and not seen.mode.active
    assert ledger.live == ledger.resident == 0
    assert not seen.mode.scope._issued


def test_forged_view_cannot_bypass_scope_ledger(sql_facts):
    f = sql_facts
    calls = []
    class Foreign:
        def __getattr__(self, name):
            calls.append(name)
            raise AssertionError('foreign ledger callback')
    with f.store.tx() as c, segment(f, c, cohort=(BOUNDS, LIMITS)) as s:
        good = s.source.run._node
        for allocation in (None, Foreign()):
            node = _Node(good.packet, good.ref)
            object.__setattr__(node, 'allocation', allocation)
            with pytest.raises(DomainError):
                owned._Value(s.source, node)._check()
        with pytest.raises(DomainError):
            _node(good.packet, Foreign())
        assert calls == []


@pytest.mark.parametrize('field', ['reserved_at', 'identity', 'settlement'])
def test_budgeted_slot_comparison_covers_all_nested_fields(sql_facts, field):
    f = sql_facts
    with pytest.raises(DomainError), f.store.tx() as c, segment(
        f, c, cohort=(BOUNDS, LIMITS)
    ) as s:
        result = s.cohort
        slot = next(v for v in s.state.slots if v.identity.stage == 'source')
        value = (slot.reserved_at + 0.5 if field == 'reserved_at' else
                 slot.identity.model_copy(update={'fence': slot.identity.fence + 1})
                 if field == 'identity' else
                 slot.settlement.model_copy(update={'response_sha256': 'f'*64}))
        changed = slot.model_copy(update={field: value})
        state = s.state.model_copy(update={'slots': tuple(changed if v is slot else v
                                                        for v in s.state.slots)})
        owned._source_slot(s.source, state, slot.identity.attempt_id)
    assert not result.mode.active and not result.mode.scope._issued
    assert result.ledger.live == result.ledger.resident == 0


def test_mutation_after_preflight_does_not_fallback(sql_facts, monkeypatch):
    f = sql_facts
    original = budget._Ledger.encode
    seen = count_producers(monkeypatch)
    raw = []
    producer = dispatch._graph_stage_accounted

    def retained(*args, **kwargs):
        facts = producer(*args, **kwargs)
        raw.append(facts)
        return facts
    monkeypatch.setattr(dispatch, '_graph_stage_accounted', retained)

    def changed(self, prepared, projection, **kwargs):
        raw[0][2][0][0].identity.__dict__['fence'] += 1
        return original(self, prepared, projection, **kwargs)
    monkeypatch.setattr(budget._Ledger, 'encode', changed)
    with pytest.raises(DomainError), f.store.tx() as c, segment(f, c, cohort=(BOUNDS, LIMITS)):
        pytest.fail('drift must not yield either route')
    assert seen == ['source', 'generate']


def test_second_producer_failure_does_not_issue_or_retry(sql_facts, monkeypatch):
    seen = []
    probes = []
    initialize = owned._OwnedPrewriteMode.__init__
    def initialized(self, *args):
        initialize(self, *args)
        probes.append(self)
    monkeypatch.setattr(owned._OwnedPrewriteMode, '__init__', initialized)
    original = dispatch._graph_stage_accounted

    def failed(*args, **kwargs):
        seen.append(args[7])
        if args[7] == 'generate':
            raise DomainError('VERSION_CONFLICT', 'offline second producer failure')
        return original(*args, **kwargs)
    monkeypatch.setattr(dispatch, '_graph_stage_accounted', failed)
    f = sql_facts
    with pytest.raises(DomainError), f.store.tx() as c, segment(f, c, cohort=(BOUNDS, LIMITS)):
        pytest.fail('producer failure must not select legacy')
    assert seen == ['source', 'generate']
    assert len(probes) == 1 and not probes[0].active and not probes[0].scope._issued


@pytest.mark.parametrize('field', ['resident', 'peak'])
def test_bootstrap_capacity_is_legacy_after_both_original_producers(sql_facts, monkeypatch, field):
    seen = count_producers(monkeypatch)
    f = sql_facts
    limits = LIMITS._replace(**{field: 1})
    with f.store.tx() as c, segment(f, c, cohort=(BOUNDS, limits)) as s:
        assert s.cohort.route == 'LEGACY' and seen == ['source', 'generate']
        assert s.cohort.ledger.live == 0 and not s.cohort._probe.scope._issued


def test_bootstrap_capacity_does_not_hide_original_revoke(sql_facts, monkeypatch):
    f = sql_facts
    seen = count_producers(monkeypatch)
    with f.store.tx() as c:
        c.execute(update(grants).where(grants.c.principal_id == f.bound['draft']['runtime_id'])
                  .values(revoked=True))
    with pytest.raises(DomainError) as denied, f.store.tx() as c, segment(
        f, c, cohort=(BOUNDS, LIMITS._replace(resident=1, peak=1))
    ):
        pytest.fail('revoked Source cannot select legacy')
    assert denied.value.code == 'GRANT_REVOKED'
    assert seen == ['source']


@pytest.mark.parametrize('bounds', [BOUNDS, BOUNDS._replace(nodes=1)])
def test_original_infinite_result_rejection_precedes_capacity(sql_facts, monkeypatch, bounds):
    f = sql_facts
    seen = count_producers(monkeypatch)
    monkeypatch.setattr(owned, '_capture_bounded',
                        lambda *a: pytest.fail('original rejection must precede copy'))
    with f.store.tx() as c:
        c.execute(update(runs).where(runs.c.id == f.source_id).values(result={'unused': float('inf')}))
    # Original graph.add -> _cold_graph_validate_inputs -> fingerprint uses
    # allow_nan=False. Preserve its actual ValueError, even with tiny new caps.
    with pytest.raises(ValueError, match='Out of range float'), f.store.tx() as c, segment(
        f, c, cohort=(bounds, LIMITS)
    ):
        pytest.fail('original nonfinite rejection cannot select either route')
    assert seen == ['source']


@pytest.mark.parametrize('ending', ['rollback', 'commit', 'revoke'])
def test_owned_dynamic_failure_closes_both_and_releases(sql_facts, ending):
    f = sql_facts
    result = None
    with pytest.raises(DomainError), f.store.tx() as c, segment(f, c, cohort=(BOUNDS, LIMITS)) as s:
        result = s.cohort
        assert result.route == 'OWNED'
        if ending == 'revoke':
            c.execute(update(grants).where(grants.c.principal_id == f.bound['draft']['runtime_id'])
                      .values(revoked=True))
        else:
            getattr(c, ending)()
        result.assert_current()
    assert result is not None and not result.mode.active
    assert not result.mode.scope._issued
    assert result.ledger.live == result.ledger.resident == 0
