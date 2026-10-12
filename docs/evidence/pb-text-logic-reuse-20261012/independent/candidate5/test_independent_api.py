"""New authority/data integrity only; no cancelled installation probes."""
import copy
from pathlib import Path
import sys

sys.path.insert(0, '/workspace/Sim2Act/tests')
from conftest import env
from test_registered_text_extraction import prepared, snapshot
from test_text_logic_reuse import mint, binding, bind, revoke_source

import pytest
from sqlalchemy import select, update, delete
from sim2act.db import internal_approvals, delivery_graph_requests, fingerprint
from sim2act import text_logic_reuse as logic

@pytest.mark.parametrize('field,value', [
    ('model_requests', False),
    ('formal_publication_enabled', 0),
    ('max_lines', 64.0),
])
def test_single_resigned_authority_payload_does_not_match_original_double_seals(env, field, value):
    data, _, _, _, _, _, _, url = prepared(env)
    obj, _ = mint(data, url)
    with data[0].tx() as c:
        row = c.execute(select(internal_approvals).where(internal_approvals.c.id == obj['id'])).mappings().one()
        changed = copy.deepcopy(row['payload'])
        if field == 'max_lines':
            changed['recipe'][field] = value
        else:
            changed[field] = value
        c.execute(update(internal_approvals).where(internal_approvals.c.id == obj['id']).values(
            payload=changed, fingerprint=fingerprint(changed)))
    response = data[2].get(f"/api/internal/text-logics/{obj['id']}")
    assert response.status_code == 409, response.text

@pytest.mark.parametrize('field,value', [
    ('expected_proof_fingerprint', '0'*64),
    ('expected_release_fingerprint', '0'*64),
    ('consent', 'UNAUTHORIZED'),
    ('request_key', 'invalid/key'),
])
def test_source_authorization_body_rejected_without_new_rows(env, field, value):
    data, _, _, _, _, _, _, url = prepared(env)
    options = data[2].get(url+'/text-logic-options').json()
    body = dict(expected_proof_fingerprint=options['source_proof_fingerprint'],
                expected_release_fingerprint=options['release_fingerprint'],
                consent='AUTHORIZE_DATA_FREE_TEXT_LOGIC_IN_THIS_PROJECT', request_key='bad-mint')
    before = snapshot(data[0])
    response = data[2].post(url+'/text-logic-authorizations', json={**body, field:value})
    assert response.status_code in (409,422), response.text
    assert snapshot(data[0]) == before

@pytest.mark.parametrize('seal_kind', [logic.BIND, logic.BIND+'_seal'])
def test_either_new_binding_seal_missing_denies_new_app(env, seal_kind):
    data, _, _, _, _, target, _, url = prepared(env)
    obj, _ = mint(data, url)
    body = binding(data, obj, target)
    made = bind(data, obj, body)
    revoke_source(data)
    with data[0].tx() as c:
        c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.app_id == obj['id'],
            delivery_graph_requests.c.kind == seal_kind, delivery_graph_requests.c.request_key == body['request_key']))
    response = data[2].get('/api/apps/'+made['id'])
    assert response.status_code == 409, response.text
