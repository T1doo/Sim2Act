"""Independent canonical JSON adversarial test; synthetic test DB only."""
import copy
import json

from conftest import env as env
from sqlalchemy import event, select, update
from test_csv_goal_revisions import raw_trace as raw_trace
from test_csv_material_revisions import prepared, proposal
from test_spec_app_operations import snapshot

from sim2act import csv_goal_revisions as revision
from sim2act import delivery_graph_apps as graph
from sim2act.db import delivery_graph_requests as requests, fingerprint


def test_material_canonical_json_rejects_resigned_numeric_aliases_and_restores_original(env, tmp_path):
    seed = prepared(env)
    data, _, _, current, path, _, body, *_ = seed
    original = proposal(seed)
    store, _, client, user, *_ = data
    result = {'candidate': '805afe60cdd94d6d4679e0da9c1f7fde752f67d2', 'variants': [], 'real_model_requests': 0}
    query = select(requests).where(requests.c.app_id == current['id'], requests.c.principal_id == user,
        requests.c.kind.in_([revision.PREVIEW, revision.PREVIEW + '_seal']), requests.c.request_key == body['request_key'])
    with store.tx() as c:
        originals = [dict(row) for row in c.execute(query).mappings()]
    assert len(originals) == 2
    baseline = snapshot(store)
    try:
        for label in ('goal-version-float', 'material-revision-bool'):
            forged = copy.deepcopy(original)
            if label == 'goal-version-float':
                assert type(forged['context']['goal']['version']) is int and forged['context']['goal']['version'] == 2
                forged['context']['goal']['version'] = 2.0
            else:
                assert type(forged['material']['revision']) is int and forged['material']['revision'] == 1
                forged['material']['revision'] = True
            # These values compare equal under ordinary Python dict equality;
            # the canonical JSON identity must still distinguish them.
            without_fp = {key: value for key, value in original.items() if key != 'preview_fingerprint'}
            forged_without_fp = {key: value for key, value in forged.items() if key != 'preview_fingerprint'}
            assert without_fp == forged_without_fp
            assert fingerprint(without_fp) != fingerprint(forged_without_fp)
            forged['preview_fingerprint'] = fingerprint(forged_without_fp)
            payload = {'request': copy.deepcopy(body), 'response': forged}
            with store.tx() as c:
                for old in originals:
                    c.execute(update(requests).where(requests.c.app_id == old['app_id'],
                        requests.c.principal_id == old['principal_id'], requests.c.kind == old['kind'],
                        requests.c.request_key == old['request_key']).values(snapshot=payload,
                        fingerprint=fingerprint(payload), request_fingerprint=fingerprint(body)))
            with store.tx() as c:
                actual = [dict(row) for row in c.execute(query).mappings()]
                assert len(actual) == 2
                for row in actual:
                    assert graph.checked(row) == payload
                    assert row['fingerprint'] == fingerprint(payload)
                    assert row['request_fingerprint'] == fingerprint(body)
                assert fingerprint(actual[0]['snapshot']) == fingerprint(actual[1]['snapshot'])
            before = snapshot(store)
            sql = []
            def observe(conn, cursor, statement, parameters, context, many):
                if statement.lstrip().upper().startswith('SELECT'):
                    sql.append({'sql': statement, 'parameters': repr(parameters)})
            event.listen(store.engine, 'before_cursor_execute', observe)
            try:
                response = client.get(path + '/previews/' + body['request_key'])
            finally:
                event.remove(store.engine, 'before_cursor_execute', observe)
            after = snapshot(store)
            item = {'variant': label, 'forged_response': forged,
                'both_ordinary_seals_recomputed': True, 'status': response.status_code,
                'response': response.json(), 'before_database_fingerprint': fingerprint(before),
                'after_database_fingerprint': fingerprint(after), 'selects': sql}
            result['variants'].append(item)
            try:
                assert response.status_code == 409, response.text
                assert after == before
            finally:
                with store.tx() as c:
                    for old in originals:
                        c.execute(update(requests).where(requests.c.app_id == old['app_id'],
                            requests.c.principal_id == old['principal_id'], requests.c.kind == old['kind'],
                            requests.c.request_key == old['request_key']).values(snapshot=old['snapshot'],
                            fingerprint=old['fingerprint'], request_fingerprint=old['request_fingerprint']))
            restored_before = snapshot(store)
            restored = client.get(path + '/previews/' + body['request_key'])
            item['restored_original_status'] = restored.status_code
            item['restored_original_response'] = restored.json()
            assert restored.status_code == 200, restored.text
            assert fingerprint(restored.json()) == fingerprint(original)
            assert snapshot(store) == restored_before == baseline
        result['original_restored_without_product_writes'] = True
    finally:
        (tmp_path / 'actual-independent-canonical-json.json').write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
