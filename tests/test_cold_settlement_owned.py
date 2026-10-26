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


@contextmanager
def native_copy(value):
    ledger = _Ledger(BOUNDS, LIMITS)
    copier = owned._NativeCopy(ledger)
    try:
        yield copier.copy(value)
    finally:
        copier.close()
        ledger.close()
        assert ledger.live == ledger.resident == 0


def test_direct_native_copy_preserves_exact_old_bytes_and_cross_root_aliases():
    model = Limits(max_requests=3, max_tools=4, max_repairs=1,
                   max_total_tokens=1000, max_output_tokens=100, run_seconds=300)
    hidden = {'value': [True, 1, (1,), [1]]}
    meta = SimpleResultMetaData(['visible'])
    keys = object.__getattribute__(meta, '_keys')
    row = RowMapping(meta, None, {'visible': 0, 'hidden': 1}, ('ok', hidden, hidden))
    source = (model, model.__dict__, row, keys, hidden)
    before = runtime._cold_graph_bytes(source)
    with native_copy(source) as copied:
        assert runtime._cold_graph_bytes(copied) == before
        assert type(copied[0]) is Limits and copied[0].__dict__ is copied[1]
        assert copied[1] is not model.__dict__
        rowkeys, data, _ = runtime._cold_graph_row_storage(copied[2])
        assert rowkeys is copied[3] and data[1] is data[2] is copied[4]
        assert copied[4] is not hidden
        hidden['value'].append('changed')
        model.max_requests = 99
        assert runtime._cold_graph_bytes(copied) == before


@pytest.mark.parametrize('bad', ['cycle', 'nan', 'unknown'])
def test_direct_native_copy_rejects_without_retry_or_live_tickets(bad):
    value = []
    if bad == 'cycle':
        value.append(value)
    elif bad == 'nan':
        value = float('nan')
    else:
        value = object()
    with pytest.raises(DomainError), native_copy(value):
        pass


def test_real_approval_producer_rebinds_model_and_raw_but_default_stays_original(sql_facts):
    f = sql_facts
    roles = dict.fromkeys(('source', 'generate', 'platform', 'trial', 'per_use'))
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with runtime._cold_graph_read(f.worker, c, {'isolated': True}, roles, 'pre') as graph:
            # Exercise the real original SQL producer and the real CTR method;
            # do not run _prepare/commit, Worker or any model transport.
            trial = object.__new__(runtime._ColdTrialGraph)
            trial.worker, trial.c, trial.guard = f.worker, c, graph
            approval = gate._approved(f.store, c, f.user, f.contract, f.binding.approval_key)
            cohort = []
            assert trial._produced(cohort, gate.Approval, approval) is approval
            owner = owned._NativeModels(graph, BOUNDS, LIMITS)
            trial._owned_models = owner
            try:
                owned_cohort = []
                copied = trial._produced(owned_cohort, gate.Approval, approval)
                kind, actual, raw = owned_cohort[0]
                assert kind is gate.Approval and actual is copied and copied is not approval
                assert gate.Approval.model_dump(copied) == gate.Approval.model_dump(approval)
                gate._trial_typed_values(owned_cohort)
                old = approval.approved_at
                approval.approved_at = old - 1
                assert copied.approved_at == old
                gate._trial_typed_values(owned_cohort)
                fresh_cohort = []
                newer = trial._produced(fresh_cohort, gate.Approval, approval)
                assert newer.approved_at == old - 1 and copied.approved_at == old
                assert newer is not copied and owner.version == 2
                approval.approved_at = old
            finally:
                owner.close()
            assert not owner.active and owner.ledger.live == owner.ledger.resident == 0


@pytest.mark.parametrize('fault', ['capacity', 'partial_constructor', 'write'])
def test_native_issued_failure_closes_no_fallback(sql_facts, monkeypatch, fault):
    f = sql_facts
    roles = dict.fromkeys(('source', 'generate', 'platform', 'trial', 'per_use'))
    owner = None
    with pytest.raises((DomainError, MemoryError)), f.store.tx() as c, pb._source_reads(f.store, c):
        with runtime._cold_graph_read(f.worker, c, {'isolated': True}, roles, 'pre') as graph:
            owner = owned._NativeModels(graph, BOUNDS, LIMITS)
            approval = gate._approved(f.store, c, f.user, f.contract, f.binding.approval_key)
            raw = gate.Approval.model_dump(approval)
            owner.produced(gate.Approval, approval, raw)
            if fault == 'capacity':
                owner.ledger.limits = LIMITS._replace(work=owner.ledger.work + 1)
            elif fault == 'partial_constructor':
                def fail(self, ledger):
                    ledger.reserve(units=10)
                    raise MemoryError('partial native constructor')
                monkeypatch.setattr(owned._NativeCopy, '__init__', fail)
            else:
                from sqlalchemy import update

                from sim2act.db import runs
                c.execute(update(runs).where(runs.c.id == f.gen_id).values(error={'native': True}))
            owner.produced(gate.Approval, approval, raw)
    assert owner is not None and not owner.active
    assert owner.ledger.live == owner.ledger.resident == 0


def test_native_serializer_change_closes_before_owned_model_can_escape(sql_facts, monkeypatch):
    f = sql_facts
    roles = dict.fromkeys(('source', 'generate', 'platform', 'trial', 'per_use'))
    owner = None
    calls = []
    with pytest.raises(DomainError, match='native_fixed_serializers'), \
            f.store.tx() as c, pb._source_reads(f.store, c):
        with runtime._cold_graph_read(f.worker, c, {'isolated': True}, roles, 'pre') as graph:
            owner = owned._NativeModels(graph, BOUNDS, LIMITS)
            approval = gate._approved(f.store, c, f.user, f.contract, f.binding.approval_key)
            raw = gate.Approval.model_dump(approval)
            owner.produced(gate.Approval, approval, raw)
            def unknown(self, **kwargs):
                calls.append(self)
                return raw
            monkeypatch.setattr(gate.Approval, 'model_dump', unknown)
            owner.produced(gate.Approval, approval, raw)
    assert not calls and not owner.active and owner.ledger.live == 0


def test_native_quote_cannot_keep_a_mutable_external_attribute():
    from sqlalchemy.sql.elements import quoted_name

    value = quoted_name('column', None)
    value.quote = []
    with pytest.raises(DomainError, match='native_quote_layout'), native_copy(value):
        pass


def test_real_accounted_batch_keeps_aliases_and_original_pure_archive_consumer(sql_facts):
    from accounted_sqlite_fixture import segment
    from test_cold_accounted_sqlite import resolve

    from sim2act import pa_trial_dispatch as dispatch

    f = sql_facts
    with f.store.tx() as c, segment(f, c) as s:
        # The actual SQL-backed producers ran once in segment. Only their
        # content is copied; dynamic readers/authority/SQL gates stay original.
        result = resolve(s)
        original = (s.state, s.source, s.generated, s.stage, f.extraction)
        with native_copy(original) as copied:
            state, source, generated, stage, extraction = copied
            dispatch._archive_chain_from_facts(f.binding, state, result, source)
            assert source[0] is stage[0] and generated is stage[6]
            assert type(state) is type(s.state) and state is not s.state
            assert source[2][0][0] is next(slot for slot in state.slots
                if slot.identity.attempt_id == source[2][0][0].identity.attempt_id)
            # Original raw protocol bytes, including all nested row storage.
            assert runtime._cold_graph_bytes((source[0], generated[0])) == \
                runtime._cold_graph_bytes((s.source[0], s.generated[0]))
            assert type(extraction) is type(f.extraction)


def test_real_base_source_and_context_adopt_one_pair_without_second_source_copy(sql_facts):
    from accounted_sqlite_fixture import seed_cold
    from test_cold_accounted_native import native_segment
    from test_cold_base_cohort import trial

    from sim2act import production_trial_policy as policy

    f = sql_facts
    seed_cold(f)
    with f.store.tx() as c, native_segment(f, c) as s:
        t = trial(s)
        t._owned_models = owner = owned._NativeModels(s.graph, BOUNDS, LIMITS)
        t.current_boundary = 'commit:first'
        # Synthetic producer result interface only, not provider attestation.
        source = policy.SourceVerificationResult(
            requirements_fingerprint='a' * 64, account_id='isolated-account',
            quota_subject='isolated-subject', provider='synthetic', model='synthetic',
            endpoint='https://synthetic.invalid', evidence_fingerprint='b' * 64,
            decision='UNKNOWN', legal_free_entitlement=None, enforced_non_chargeable=None,
            revoked=None, observed_at=1, expires_at=2)
        try:
            cohort = []
            copied = t._produced(cohort, policy.SourceVerificationResult, source)
            assert t._source_value(copied) is copied is t.live_source
            assert t.source_record is cohort[0][2] and owner.version == 1
            check = policy.RunCheck(requirements_fingerprint='a' * 64,
                approval_fingerprint='b' * 64, stage='cold', run_id=f.cold_job['id'],
                runtime_id=f.contract.runtime_id, version=1, fence=1,
                worker_id=f.worker.id, checked_at=1, deadline=2)
            t._context('commit:first', check)
            assert owner.version == 2 and t.context is not check
            assert t.context_record is s.graph.inputs['commit:first:context']
            t._base()
        finally:
            owner.close()
        assert not owner.active and owner.ledger.live == 0


@pytest.mark.parametrize('entry', ['issued_pair', 'original_producer'])
def test_native_full_entry_exception_releases_owner(sql_facts, entry):
    f = sql_facts
    roles = dict.fromkeys(('source', 'generate', 'platform', 'trial', 'per_use'))
    owner = None
    with pytest.raises(DomainError), f.store.tx() as c, pb._source_reads(f.store, c):
        with runtime._cold_graph_read(f.worker, c, {'isolated': True}, roles, 'pre') as graph:
            t = object.__new__(runtime._ColdTrialGraph)
            t.worker, t.c, t.guard = f.worker, c, graph
            t._owned_models = owner = owned._NativeModels(graph, BOUNDS, LIMITS)
            value = gate._approved(f.store, c, f.user, f.contract, f.binding.approval_key)
            models = []
            copied = t._produced(models, gate.Approval, value)
            if entry == 'issued_pair':
                models[0][2]['approved_at'] -= 1
                owner.issued_pair(gate.Approval, copied)
            else:
                t._produced(models, gate.Approval, object())
    assert not owner.active and not graph.active
    assert owner.ledger.live == owner.ledger.resident == 0


@pytest.mark.parametrize('exit_kind', ['normal', 'check_error', 'scope_error'])
def test_original_cgr_scope_always_closes_registered_native_owner(sql_facts, exit_kind):
    from contextlib import nullcontext

    f = sql_facts
    roles = dict.fromkeys(('source', 'generate', 'platform', 'trial', 'per_use'))
    owner = None
    error = pytest.raises(DomainError) if exit_kind != 'normal' else nullcontext()
    with error, f.store.tx() as c, pb._source_reads(f.store, c):
        with runtime._cold_graph_read(f.worker, c, {'isolated': True}, roles, 'pre') as graph:
            owner = owned._NativeModels(graph, BOUNDS, LIMITS)
            approval = gate._approved(f.store, c, f.user, f.contract, f.binding.approval_key)
            owner.produced(gate.Approval, approval, gate.Approval.model_dump(approval))
            assert owner.ledger.resident > 0
            if exit_kind == 'check_error':
                graph.inputs['isolated'] = False
                graph.check(f.store, c)
            elif exit_kind == 'scope_error':
                raise DomainError('VERSION_CONFLICT', 'synthetic body failure')
        assert not owner.active
    assert owner is not None and not owner.active and not graph.active
    assert graph._settlement_owned_models is None
    assert owner.ledger.live == owner.ledger.resident == 0 and owner._owned == []


def test_native_owner_cannot_be_replaced_on_the_same_live_graph(sql_facts):
    f = sql_facts
    roles = dict.fromkeys(('source', 'generate', 'platform', 'trial', 'per_use'))
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with runtime._cold_graph_read(f.worker, c, {'isolated': True}, roles, 'pre') as graph:
            first = owned._NativeModels(graph, BOUNDS, LIMITS)
            with pytest.raises(DomainError, match='one native handoff owner'):
                owned._NativeModels(graph, BOUNDS, LIMITS)
            assert first.active and graph._settlement_owned_models is first
            first.close()
            with pytest.raises(DomainError, match='one native handoff owner'):
                owned._NativeModels(graph, BOUNDS, LIMITS)
            assert graph.active and graph._settlement_owned_models is None
        assert not first.active
