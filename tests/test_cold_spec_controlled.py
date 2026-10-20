"""Isolated strict-error ownership; no model/Worker/full trial execution."""

import copy

import pytest
from sqlalchemy import event, insert
from test_cold_binding_fact_leaves import local_origin as local_origin
from test_cold_binding_fact_leaves import no_external_transport as no_external_transport
from test_cold_release_stages import read_scope

from sim2act import natural_spec_runtime as runtime
from sim2act import pa_spec_apps as spec
from sim2act import pb_natural_specs as pb
from sim2act.db import delivery_graph_requests, fingerprint, new_id
from sim2act.errors import DomainError


@pytest.mark.parametrize('name', ['scope_gate', 'job_scope_gate'])
def test_strict_scope_sql_guard_valueerror_is_original_before_next_lookup(
        local_origin, monkeypatch, name):
    f, sql, parsed = local_origin, [], []
    original = ValueError('synthetic original strict scope read pin')
    armed = [False]

    def after_sql(c, cursor, statement, params, context, executemany):
        if statement.lstrip().upper().startswith('SELECT'):
            sql.append(statement)
            armed[0] = True

    def forbidden_parser(value):
        parsed.append(value)
        pytest.fail('Persisted parser ran after the first SQL guard failed')

    monkeypatch.setattr(spec, '_persisted_scope_metadata', forbidden_parser)
    monkeypatch.setattr(spec, '_persisted_run_scope', forbidden_parser)
    event.listen(f.store.engine, 'after_cursor_execute', after_sql)
    try:
        with f.store.tx() as c, pb._source_reads(f.store, c):
            with pytest.raises(ValueError) as caught:
                with read_scope(f, c) as guard:
                    original_check = guard.check

                    def checked(store, connection):
                        if armed[0]:
                            raise original
                        return original_check(store, connection)

                    monkeypatch.setattr(guard, 'check', checked)
                    try:
                        getattr(spec, name)(f.store, c, f.user,
                            f.draft['id'] if name == 'scope_gate' else new_id('run'),
                            _graph_read=guard)
                    except ValueError as error:
                        assert error is original and not guard.active
                        raise
        assert caught.value is original and len(sql) == 1 and parsed == []
    finally:
        event.remove(f.store.engine, 'after_cursor_execute', after_sql)


@pytest.mark.parametrize('name', ['_cold_receipts', '_cold_verify_job_from_receipts'])
def test_strict_receipt_entry_guard_valueerror_is_original_and_reads_zero_sql(
        local_origin, monkeypatch, name):
    f, sql, consumed = local_origin, [], []
    job = dict(id=new_id('run'), principal_id=f.user)
    original = ValueError('synthetic original receipt facts pin')

    def after_sql(c, cursor, statement, params, context, executemany):
        if statement.lstrip().upper().startswith('SELECT'):
            sql.append(statement)

    def forbidden(*args, **kwargs):
        consumed.append('core')
        pytest.fail('Receipt core consumed facts after the entry guard failed')

    monkeypatch.setattr(spec, '_receipts', forbidden)
    monkeypatch.setattr(spec, '_verify_job_from_receipts', forbidden)
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(ValueError) as caught:
            with read_scope(f, c) as guard:
                facts = runtime._cold_run_facts(f.store, c, job, guard)

                def checked(store, connection):
                    raise original

                monkeypatch.setattr(guard, 'check', checked)
                event.listen(f.store.engine, 'after_cursor_execute', after_sql)
                try:
                    try:
                        if name == '_cold_receipts':
                            spec._cold_receipts(f.store, c, job, {}, facts)
                        else:
                            spec._cold_verify_job_from_receipts(f.store, c,
                                f.user, job, f.limits, {}, {}, [], facts)
                    except ValueError as error:
                        assert error is original and not guard.active
                        raise
                finally:
                    event.remove(f.store.engine, 'after_cursor_execute', after_sql)
    assert caught.value is original and not sql and not consumed


@pytest.mark.parametrize('run_scope', [False, True])
def test_fixed_owned_scope_parse_matches_original_paired_malformed_mapping(
        local_origin, monkeypatch, run_scope):
    f, parsed = local_origin, []
    rid = new_id('run')
    request = dict(app_id=f.draft['id'], principal_id=f.user,
        project_id=f.draft['project_id'], runtime_id=f.draft['runtime_id'],
        resource_id=f.origin[2]['resource_id'])
    if run_scope:
        request.update(run_id=rid, instance_id=new_id('instance'),
            app_run_id=new_id('apprun'), release_id=new_id('release'))
        model, kind, key, entity = spec.RunScopeInput, spec.RUN_META, 'accepted', rid
        parser_name = '_persisted_run_scope'
    else:
        request['source_run_id'] = rid
        model, kind, key, entity = spec.Metadata, spec.META, 'scope', f.draft['id']
        parser_name = '_persisted_scope_metadata'
    model.model_validate(request)
    del request['resource_id']
    snapshot = dict(request=request, response={})
    with f.store.tx() as c:
        for saved_kind in (kind, kind + '_seal'):
            c.execute(insert(delivery_graph_requests).values(app_id=entity,
                principal_id=f.user, kind=saved_kind, request_key=key,
                request_fingerprint=fingerprint(request), snapshot=snapshot,
                fingerprint=fingerprint(snapshot)))
    # This is exactly the old pair under the old outer controlled mapping,
    # without pretending that the malformed pair proves an application scope.
    old_pair = spec.controlled(spec.pair)
    with f.store.tx() as c, pytest.raises(DomainError) as old:
        old_pair(c, f.user, entity, kind, key, model)
    original_parser = getattr(spec, parser_name)

    def parser(value):
        parsed.append('owned-parse')
        return original_parser(value)

    monkeypatch.setattr(spec, parser_name, parser)
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError) as strict:
            with read_scope(f, c) as guard:
                try:
                    spec._cold_scope_pair(f.store, c, f.user, entity, guard,
                        run_scope=run_scope)
                except DomainError:
                    assert not guard.active
                    raise
    assert strict.value.public() == old.value.public()
    assert strict.value.message == 'Malformed persisted DeliveryGraph binding'
    assert parsed == ['owned-parse']


@pytest.mark.parametrize('receipt', [None, {}])
def test_owned_receipt_data_malformed_maps_before_output_validation_or_node_proof(
        local_origin, monkeypatch, receipt):
    f, calls = local_origin, []
    job = dict(id=new_id('run'), principal_id=f.user, runtime_id=f.draft['runtime_id'],
        project_id=f.draft['project_id'], context=dict(tools=1), fence=1)
    plan = spec._bound_plan_from_facts(f.draft, dict(input={}), f.origin[2])
    step, action = plan['definition']['manifest']['workflow'][0], plan['definition']['actions'][0]
    intent = spec.intent_for(step, action, plan, {}, [])
    op = dict(id=new_id('op'), call_id=step['step_id'], fingerprint=fingerprint(intent),
        tool_ref=intent['tool'], status='VERIFIED', receipt=copy.deepcopy(receipt))
    binding = dict(plan=plan, source=f.origin[2])

    @spec.controlled
    def original_data_expression():
        return op['receipt']['data']

    with pytest.raises(DomainError) as old:
        original_data_expression()
    original_data, original_validate = spec._receipt_data, spec.validate_value

    def data(value):
        calls.append('owned-data')
        return original_data(value)

    def validate(schema, value):
        if schema is action['output_schema']:
            pytest.fail('Malformed receipt reached output validation')
        calls.append('input-schema')
        return original_validate(schema, value)

    monkeypatch.setattr(spec, '_receipt_data', data)
    monkeypatch.setattr(spec, 'validate_value', validate)
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError) as strict:
            with read_scope(f, c) as guard:
                facts = runtime._cold_run_facts(f.store, c, job, guard)
                facts._put('receipt-operations', [op])
                facts._put('intent:' + op['id'], intent)

                def isolated_counter_precondition():
                    # Counter validation is independent of receipt.data shape.
                    # Isolate only that prerequisite; install no counter proof
                    # and never return a successful receipt proof/Authority.
                    facts.check(f.store, c, job)

                monkeypatch.setattr(facts, 'checked_counters', isolated_counter_precondition)
                try:
                    spec._cold_receipts(f.store, c, job, binding, facts)
                except DomainError:
                    assert not guard.active
                    raise
    assert strict.value.public() == old.value.public()
    assert calls == ['input-schema', 'owned-data']


def test_owned_receipt_output_malformed_maps_before_schema_consumer(
        local_origin, monkeypatch):
    f, calls = local_origin, []
    job = dict(id=new_id('run'), principal_id=f.user, status='SUCCEEDED', error=None,
        cancel_intent=False, result={}, fence=1)
    plan = spec._bound_plan_from_facts(f.draft, dict(input={}), f.origin[2])
    app = dict(id=new_id('apprun'), status='SUCCEEDED', error=None, output={}, result_version=1)
    snapshot = dict(instance_id=new_id('instance'), release_id=new_id('release'))
    binding = dict(app_run=app, snapshot=snapshot, plan=plan)
    outputs = {}
    proved = [{} for _ in plan['definition']['manifest']['workflow']]
    with pytest.raises(DomainError) as old:
        spec.controlled(spec.output_for)(plan, outputs)
    original_output = spec._receipt_output

    def output(saved_plan, saved_outputs):
        calls.append('owned-output')
        return original_output(saved_plan, saved_outputs)

    def forbidden(*args, **kwargs):
        pytest.fail('Missing output reached schema validation')

    def unknown(*args, **kwargs):
        calls.append('unknown-fixture')
        return False

    monkeypatch.setattr(spec, '_receipt_output', output)
    monkeypatch.setattr(spec, 'validate_value', forbidden)
    monkeypatch.setattr(f.store, 'has_unknown', unknown)
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError) as strict:
            with read_scope(f, c) as guard:
                facts = runtime._cold_run_facts(f.store, c, job, guard)
                facts._put('typed:' + snapshot['instance_id'] + ':' + app['id'], [{}])

                def isolated_receipts_precondition(*args):
                    # A malformed output is exercised at its original pure
                    # indexing point; no complete receipt proof is installed.
                    facts.check(f.store, c, job)

                monkeypatch.setattr(facts, 'checked_receipts', isolated_receipts_precondition)
                try:
                    spec._cold_verify_job_from_receipts(f.store, c, f.user, job,
                        f.limits, binding, outputs, proved, facts)
                except DomainError:
                    assert not guard.active
                    raise
    assert strict.value.public() == old.value.public()
    assert calls == ['unknown-fixture', 'owned-output']
