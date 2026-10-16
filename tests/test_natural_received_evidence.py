"""Ordinary P-A actual Worker reception; no Trial/qualification replacement."""
import base64
import copy
import hashlib
import json

import httpx
import pytest
from sqlalchemy import delete, select, update
from test_natural_spec_apps import SOURCE, enqueue, ready, setup, transport

from sim2act import natural_source_archives as archive
from sim2act.db import (
    attempts,
    delivery_graph_requests,
    events,
    internal_instance_data,
    internal_run_bindings,
    operations,
    reservations,
    runs,
)
from sim2act.worker import Worker


@pytest.mark.parametrize('fault', ['missing_slot', 'moved_slot', 'request_archive',
                                   'cancel_missing_slot', 'prefix_missing_slot'])
def test_actual_received_damage_preserves_owned_fact_without_retry(env, tmp_path, fault):
    data = setup(env)
    store, settings, client = data[:3]
    origin, _, release, inst, _ = ready(data)
    rid = enqueue(data, release, inst, key='original-damaged-response')
    original = transport([], SOURCE)
    sent, held = [], {}

    class Prefix(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield held['body']
            raise httpx.ReadError('Explicit offline prefix after slot loss')

    def handler(request):
        sent.append(request.content)
        with store.tx() as c:
            row = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().one()
            held['attempt_id'] = row['id']
            held['reserved_tokens'] = row['reserved_tokens']
            held['parameters'] = copy.deepcopy(row['parameters'])
            if fault == 'moved_slot':
                # Preserve this foreign slot exactly; never repair it into this Run.
                c.execute(update(reservations).where(reservations.c.id == row['id'])
                    .values(run_id=origin))
                held['foreign_slot'] = dict(c.execute(select(reservations).where(
                    reservations.c.id == row['id'])).mappings().one())
            elif fault == 'request_archive':
                c.execute(delete(delivery_graph_requests).where(
                    delivery_graph_requests.c.app_id == rid,
                    delivery_graph_requests.c.kind == archive.REQUEST + '_seal'))
            else:
                c.execute(delete(reservations).where(reservations.c.id == row['id']))
                if fault == 'cancel_missing_slot':
                    c.execute(update(runs).where(runs.c.id == rid).values(cancel_intent=True))
        if fault == 'prefix_missing_slot':
            held['body'] = b'{"received":"partial"}'
            return httpx.Response(200, stream=Prefix())
        held['body'] = original.handle_request(request).content
        return httpx.Response(200, content=held['body'])

    assert Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler)).once()
    with store.tx() as c:
        row = dict(c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().one())
        job = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
        assert row['reserved_tokens'] == held['reserved_tokens'] > 0
        assert row['parameters'] == held['parameters']
        assert job['status'] != 'SUCCEEDED' and job['result'] is None
        app_run_id = c.execute(select(internal_run_bindings.c.app_run_id).where(
            internal_run_bindings.c.run_id == rid)).scalar_one()
        assert not c.execute(select(internal_instance_data).where(
            internal_instance_data.c.run_id == app_run_id)).first()
        assert not c.execute(select(operations.c.id).where(
            operations.c.run_id == rid, operations.c.tool_ref == 'artifact.save_text')).first()
        if fault == 'prefix_missing_slot':
            assert row['status'] == 'STARTED' and row['response'] is None
            assert row['usage'] == dict(status='unknown', tokens=None)
        else:
            assert row['status'] == 'REJECTED_KNOWN' and row['response']['received_raw']
            assert row['usage']['status'] == 'known'
            assert len(c.execute(select(events).where(events.c.run_id == rid,
                events.c.kind == 'NS_RECEIVED')).all()) == 1
        if fault == 'request_archive':
            assert c.execute(select(reservations).where(reservations.c.id == row['id'])).first()
            assert not c.execute(select(delivery_graph_requests).where(
                delivery_graph_requests.c.app_id == rid,
                delivery_graph_requests.c.kind == archive.RESPONSE)).first()
        else:
            slot = c.execute(select(reservations).where(reservations.c.id == row['id'])).mappings().first()
            if fault == 'moved_slot':
                assert dict(slot) == held['foreign_slot']
            else:
                assert slot is None
            body, _ = archive.pair(c, data[3], rid, archive.RESPONSE, row['id'], archive.BodyArchive)
            assert base64.b64decode(body.body_b64) == held['body']
            assert body.sha256 == hashlib.sha256(held['body']).hexdigest()
            assert body.received_complete == (fault != 'prefix_missing_slot')
    # Original-key inspection/duplicate submit and a fresh Worker may not resend.
    before_count = len(sent)
    response = client.get(f"/api/internal/instances/{inst['id']}/runs/{rid}")
    duplicate = client.post(f"/api/internal/instances/{inst['id']}/runs", json=dict(
        expected_revision=inst['revision'], expected_release_fingerprint=release['fingerprint'],
        input={}, request_key='original-damaged-response'))
    assert duplicate.status_code == 202 and duplicate.json()['run_id'] == rid, duplicate.text
    assert duplicate.json()['cached'] is True
    assert response.status_code in (200, 409), response.text
    if response.status_code == 200:
        assert response.json()['status'] != 'SUCCEEDED'
    assert not Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler)).once()
    with store.tx() as c:
        assert len(c.execute(select(attempts).where(attempts.c.run_id == rid)).all()) == 1
        assert len(c.execute(select(runs).where(runs.c.principal_id == job['principal_id'],
            runs.c.project_id == job['project_id'], runs.c.request_key == job['request_key'])).all()) == 1
    assert len(sent) == before_count == 1
    (tmp_path / 'RECEIVED_EVIDENCE.json').write_text(json.dumps(dict(fault=fault,
        attempt=row, run_status=job['status'], reserved_tokens_preserved=True,
        slot_not_recreated=fault != 'request_archive', model_dispatches=len(sent),
        original_key_read_status=response.status_code, duplicate_status=duplicate.status_code,
        duplicate_response=duplicate.json()), indent=2))
