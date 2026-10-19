"""Fresh original P-B prefix, then only its first Cold local read; no Cold model."""
import functools
import json
import threading
import time
from collections.abc import Mapping
from contextlib import contextmanager

import httpx
import test_natural_spec_apps as apps
from fastapi.testclient import TestClient
from sqlalchemy import event
from test_pb_spec_production_controller import approve_stage, configured, prepare_pb
from test_spec_production_controller import no_real_http as no_real_http

from sim2act import app_jobs
from sim2act import natural_live_admission as gate
from sim2act import natural_specs as natural
from sim2act import pa_spec_apps as spec
from sim2act import pa_trial_dispatch as trial
from sim2act import pb_natural_specs as pb
from sim2act import pb_natural_uses as use
from sim2act import production_trial_journal as journal
from sim2act import spec_production as controller
from sim2act.api import create_app
from sim2act.db import Store, fingerprint


class ColdReadProbe:
    """Passthrough observations; no replacement clock, proof or authority."""
    def __init__(self, store, run_id, *, stop_first):
        self.store, self.run_id, self.stop_first = store, run_id, stop_first
        self.main = threading.get_ident()
        self.local = threading.local()
        self.events, self.mutex = [], threading.Lock()
        self.active = True

    def record(self, kind, **values):
        row = dict(kind=kind, wall=time.time(), monotonic=time.monotonic(),
            cpu=time.thread_time(), thread=threading.get_ident(), **values)
        with self.mutex:
            self.events.append(row)

    def install(self, patch):
        old_tx, old_claim, old_beat = Store.tx, Store.claim, Store.heartbeat
        probe = self

        @contextmanager
        def tx(store, *args, **kwargs):
            watched = (store is probe.store and probe.active and
                (threading.get_ident() == probe.main or getattr(probe.local, 'heartbeat', False)))
            if not watched:
                with old_tx(store, *args, **kwargs) as c:
                    yield c
                return
            entry = dict(sql=0, writes=0)
            entry['transaction'] = id(entry)
            prior = getattr(probe.local, 'entry', None)
            probe.record('tx_attempt', transaction=entry['transaction'], options=kwargs)
            try:
                with old_tx(store, *args, **kwargs) as c:
                    probe.local.entry = entry
                    probe.record('tx_acquired', transaction=entry['transaction'],
                        connection=id(c), driver=id(c.connection.driver_connection))
                    try:
                        yield c
                    finally:
                        probe.record('tx_body_end', **entry)
                probe.record('tx_committed', transaction=entry['transaction'])
            except Exception as error:
                probe.record('tx_error', transaction=entry['transaction'], error_type=type(error).__name__)
                raise
            finally:
                probe.local.entry = prior

        def claim(store, *args, **kwargs):
            result = old_claim(store, *args, **kwargs)
            if store is probe.store and result and result['id'] == probe.run_id:
                probe.record('claim_return', actual={k: result[k] for k in
                    ('id', 'status', 'fence', 'version', 'worker_id', 'lease_until', 'created_at')})
            return result

        def heartbeat(store, worker_id, run_id=None, *args, **kwargs):
            if store is not probe.store or run_id != probe.run_id:
                return old_beat(store, worker_id, run_id, *args, **kwargs)
            probe.local.heartbeat = True
            probe.record('heartbeat_enter', worker_id=worker_id)
            try:
                result = old_beat(store, worker_id, run_id, *args, **kwargs)
                probe.record('heartbeat_committed_return', lease_until=result)
                return result
            except Exception as error:
                probe.record('heartbeat_error', error_type=type(error).__name__,
                    sqlite_errorcode=getattr(getattr(error, 'orig', None), 'sqlite_errorcode', None))
                raise
            finally:
                probe.local.heartbeat = False

        def sql(c, cursor, statement, parameters, context, executemany):
            entry = getattr(probe.local, 'entry', None)
            if entry is not None:
                entry['sql'] += 1
                if not statement.lstrip().upper().startswith('SELECT '):
                    entry['writes'] += 1
                    probe.record('write', sql_kind=statement.lstrip().split()[0],
                        epoch=c.info.get('source_proof_write_epoch', 0))

        def span(owner, name):
            original = getattr(owner, name)
            @functools.wraps(original)
            def observed(*args, **kwargs):
                if not probe.active or threading.get_ident() != probe.main:
                    return original(*args, **kwargs)
                c = next((arg for arg in args if hasattr(arg, 'info') and hasattr(arg, 'in_transaction')), None)
                token = None if c is None else c.info.get('pb_source_reads')
                entry = getattr(probe.local, 'entry', None)
                run_id = next((arg.get('id') for arg in args if isinstance(arg, Mapping)
                    and isinstance(arg.get('id'), str) and arg['id'].startswith('run_')), None)
                probe.record('span_enter', function=name,
                    run_id=run_id, transaction=None if entry is None else entry['transaction'],
                    sql=None if entry is None else entry['sql'],
                    epoch=None if c is None else c.info.get('source_proof_write_epoch', 0),
                    token=None if token is None else id(token))
                try:
                    return original(*args, **kwargs)
                finally:
                    entry = getattr(probe.local, 'entry', None)
                    probe.record('span_exit', function=name,
                        run_id=run_id, transaction=None if entry is None else entry['transaction'],
                        sql=None if entry is None else entry['sql'])
            patch.setattr(owner, name, observed)

        original_context = gate._run_context
        @functools.wraps(original_context)
        def run_context(*args, **kwargs):
            try:
                result = original_context(*args, **kwargs)
            except Exception as error:
                frame = error.__traceback__
                while frame:
                    if frame.tb_frame.f_code is original_context.__code__:
                        values = frame.tb_frame.f_locals
                        if values.get('run_id') == probe.run_id:
                            row = values.get('run')
                            probe.record('original_run_predicate_failure', at=values.get('at'),
                                expected_version=values.get('expected_version'), expected_fence=values.get('fence'),
                                actual=None if row is None else {k: row[k] for k in
                                    ('id', 'status', 'cancel_intent', 'version', 'fence', 'worker_id', 'lease_until', 'created_at')})
                    frame = frame.tb_next
                raise
            if args[6] == probe.run_id:
                probe.record('original_run_predicate_return', at=result[3], lease_until=result[2]['lease_until'])
            return result

        original_local = spec._advance_local
        @functools.wraps(original_local)
        def local_read(worker, c, run, job, b=None, checked=None):
            if run['id'] != probe.run_id:
                return original_local(worker, c, run, job, b, checked)
            probe.record('local_enter', actual={k: job[k] for k in
                ('id', 'status', 'version', 'fence', 'lease_until', 'created_at')})
            result = original_local(worker, c, run, job, b, checked)
            probe.record('local_return', original_result=result)
            # Only the directed test ends after the complete original first
            # local transaction. Full-flow verification uses stop_first=False.
            return False if probe.stop_first else result

        patch.setattr(Store, 'tx', tx)
        patch.setattr(Store, 'claim', claim)
        patch.setattr(Store, 'heartbeat', heartbeat)
        patch.setattr(gate, '_run_context', run_context)
        patch.setattr(spec, '_advance_local', local_read)
        for owner, name in ((app_jobs, 'lock_live'), (spec, 'bound'),
                            (spec, 'commit_guard'), (trial, '_pb_source')):
            span(owner, name)
        event.listen(self.store.engine, 'before_cursor_execute', sql)
        return sql


def test_fresh_pb_cold_first_local_read_keeps_original_lease(env, tmp_path, monkeypatch):
    data, binding, fixture, factory = configured(env, tmp_path, monkeypatch, prepare_case=prepare_pb)
    generation, _, release, source_instance, generated = apps.ready(data, style='ordered')
    assert len(generated) == 3
    source_id = apps.enqueue(data, release, source_instance, key=binding.contract.stage_keys.source)
    approve_stage(data, binding, 'source', source_id)
    normal = apps.transport([], apps.SOURCE)

    def source_response(request):
        raw = normal.handle_request(request).json()
        raw['archive_note'] = '合成原始正文；非真实模型'
        return httpx.Response(200, content=(json.dumps(raw, ensure_ascii=False, indent=2) + '\n').encode())

    assert factory(data[0], data[1], goal_planner_transport=httpx.MockTransport(source_response)).once()
    source = apps.inspect(data, source_instance, source_id)
    assert source.status_code == 200 and source.json()['status'] == 'SUCCEEDED', source.text
    assert len(fixture['sends']) == 5
    route = f'/api/projects/{data[4]}/natural-spec-task-runs/{source_id}'
    options = data[2].get(route + '/extraction-options')
    assert options.status_code == 200, options.text
    target = binding.contract.bindings[1]
    review = dict(source_run_id=source_id,
        expected_source_proof_fingerprint=options.json()['source_proof_fingerprint'],
        expected_source_recipe_fingerprint=options.json()['recipe_fingerprint'],
        card_id=target.card_id, expected_goal_version=target.goal_version,
        expected_goal_fingerprint=target.goal_fingerprint, expected_source_hash=target.source_hash,
        recipe=binding.contract.extraction_recipe.model_dump(exclude_none=True),
        name='Cold first local read fixture', request_key=binding.contract.extraction_request_key)
    preview = data[2].post(route + '/extraction-reviews', json=review)
    assert preview.status_code == 200, preview.text
    body = pb.ExtractInput(review=review, expected_review_fingerprint=preview.json()['review_fingerprint'],
        consent=pb.CONSENT, artifact_write_consent=natural.CONSENT)
    unexpected_model_calls = []
    def forbidden(request):
        unexpected_model_calls.append(True)
        raise AssertionError('No Cold model is part of the first local-read test')
    made = trial.extract_pb(factory(data[0], data[1], goal_planner_transport=httpx.MockTransport(forbidden)),
        data[3], source_id, body)
    release, inst = apps.instance(data, made['id'])
    cold_store = Store(data[1].database_url, test_only=True)
    cold_client = TestClient(create_app(cold_store, data[1]))
    cold_client.headers['Authorization'] = 'Bearer synthetic-test-A'
    cold_data = (cold_store, data[1], cold_client, *data[3:])
    original_environment = controller.environment
    def cold_environment(store, settings, transport):
        if store is cold_store:
            assert settings is data[1] and transport is None and store.test_only and store.sqlite
        else:
            original_environment(store, settings, transport)
    monkeypatch.setattr(controller, 'environment', cold_environment)
    probe, sql = None, None
    try:
        app = cold_client.get('/api/apps/' + made['id'])
        assert app.status_code == 200, app.text
        assert app.json()['fingerprint'] == made['candidate_fingerprint']
        base = '/api/internal/instances/' + inst['id']
        current = cold_client.get(base).json()
        use_review = dict(expected_revision=current['revision'],
            expected_release_fingerprint=release['fingerprint'], expected_app_fingerprint=app.json()['fingerprint'],
            expected_recipe_fingerprint=fingerprint(binding.contract.extraction_recipe.model_dump(exclude_none=True)),
            resource_id=target.resource_id, card_id=target.card_id, expected_goal_version=target.goal_version,
            expected_goal_fingerprint=target.goal_fingerprint, expected_source_hash=target.source_hash,
            request_key=binding.contract.stage_keys.cold)
        checked = cold_client.post(base + '/pb-use-reviews', json=use_review)
        assert checked.status_code == 200, checked.text
        queued = cold_client.post(base + '/pb-use-runs', json=dict(review=use_review,
            expected_review_fingerprint=checked.json()['review_fingerprint'], consent=use.CONSENT))
        assert queued.status_code == 202, queued.text
        cold_id = queued.json()['run_id']
        approve_stage(cold_data, binding, 'cold', cold_id)
        probe = ColdReadProbe(cold_store, cold_id, stop_first=True)
        sql = probe.install(monkeypatch)
        try:
            assert factory(cold_store, data[1], goal_planner_transport=httpx.MockTransport(forbidden)).once()
        finally:
            probe.active = False
        result = apps.inspect(cold_data, inst, cold_id)
        assert result.status_code == 200, result.text
        (tmp_path / 'cold-public-result.json').write_text(json.dumps(result.json(), indent=2) + '\n')
        assert result.json()['status'] == 'RUNNING' and len(fixture['sends']) == 5
        assert not unexpected_model_calls
        assert [step['step_id'] for step in result.json()['steps']] == ['read_pick'], result.text
        history = journal.read(cold_store, data[3], binding.contract, binding.approval_key, binding.account_id)
        assert len(history.ledger.slots) == 5 and all(slot.accepted for slot in history.ledger.slots)
        assert not history.ledger.halted
    finally:
        if probe is not None:
            probe.active = False
            if sql is not None:
                event.remove(cold_store.engine, 'before_cursor_execute', sql)
            (tmp_path / 'cold-local-read-probe.json').write_text(json.dumps(dict(
                scope='FRESH_ORIGINAL_PB_PREFIX_AND_FIRST_COLD_LOCAL_TRANSACTION_ONLY',
                generation=generation, source=source_id, cold=probe.run_id,
                real_models=0, mock_transport_invocations=len(fixture['sends']),
                received_mock_exchanges=len((tmp_path / 'mock-exchanges.jsonl').read_text().splitlines()),
                unexpected_local_model_calls=len(unexpected_model_calls),
                original_expiry=binding.contract.expires_at, events=probe.events,
                limits='Observation overhead exists; no clock/deadline/guard/proof replacement'), indent=2) + '\n')
        cold_client.close()
        cold_store.engine.dispose()
        data[2].close()
