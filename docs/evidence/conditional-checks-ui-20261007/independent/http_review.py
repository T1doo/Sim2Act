import copy
import hashlib
import json
import socket
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select, update

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, grants, meta, projects, resources

ROOT = Path('/workspace/Sim2Act-bounded-semantic-suite')
POLICY = ROOT / 'docs/evidence/model-protocol-preparation-20261006/materials/a-source/policy.txt'
lines = POLICY.read_text().splitlines()
results = []

def deny_network(*args, **kwargs):
    raise AssertionError('External socket connection forbidden')

socket.create_connection = deny_network
socket.socket.connect = deny_network

with tempfile.TemporaryDirectory(prefix='bounded-review-') as temporary:
    store = Store('sqlite:///' + temporary + '/review.db', test_only=True)
    store.initialize()
    owner = store.user('independent synthetic reviewer', 'independent-offline-token')
    other = store.user('other synthetic owner', 'other-offline-token')
    pid = store.project(owner, 'independent finite checks')
    foreign = store.project(other, 'foreign finite checks')
    rid = store.resource(owner, pid, 'policy.txt', 'txt', POLICY.read_text())
    foreignrid = store.resource(other, foreign, 'policy.txt', 'txt', POLICY.read_text())
    with TestClient(create_app(store, Settings('sqlite:///' + temporary + '/review.db', Path(temporary), mode='mock'))) as client:
        client.headers['Authorization'] = 'Bearer independent-offline-token'
        url = f'/api/projects/{pid}/conditional-checks'
        public = client.get(url + '/contract').json()
        def snapshot():
            with store.tx() as c:
                return {t.name: [dict(row) for row in c.execute(select(t)).mappings()] for t in meta.sorted_tables}
        def payload(amount=500, days=10, trip=True, receipt=True, approval=None,
                    applies=('TRUE', 'FALSE', 'FALSE'), decision='ALLOW', actions=('submit_claim_and_receipt',)):
            return {'resource_id': rid, 'expected_source_hash': hashlib.sha256(POLICY.read_bytes()).hexdigest(),
                'expected_contract_fingerprint': public['fingerprint'],
                'scenario': {'kind': 'HYPOTHETICAL_EMPLOYEE', 'amount': amount, 'elapsed_days': days,
                    'trip_ended': trip, 'receipt_present': receipt, 'approved': approval},
                'report': {'findings': [{'rule_id': rule, 'applies': status, 'citation': {'line': line, 'quote': lines[line-1]}}
                    for rule, line, status in zip(('R1', 'R2', 'R3'), (3, 4, 5), applies)],
                    'decision': decision, 'next_actions': list(actions), 'deadline_days': 10,
                    'absolute_date': 'UNKNOWN', 'receipt_restarts_deadline': False,
                    'explanation': 'Independent handwritten finite hypothetical report.'}}
        def check(name, body, expected='PASS', http=200):
            before = snapshot()
            response = client.post(url, json=body)
            assert response.status_code == http, (name, response.status_code, response.text)
            if http == 200:
                value = response.json()
                assert value['check_status'] == expected, (name, value)
                assert value['semantic_status'] == 'UNKNOWN' and value['owner_acceptance'] == 'PENDING'
                assert value['run_approval'] is False and value['formal_publication_enabled'] is False
            assert snapshot() == before, name + ': unexpected persistent write'
            results.append({'name': name, 'status': 'PASS', 'http': http})
        def source_check(name, resource=rid, project=pid, http=200):
            before=snapshot(); response=client.get(f'/api/projects/{project}/conditional-checks/sources/{resource}')
            assert response.status_code==http,(name,response.status_code,response.text)
            if http==200:
                value=response.json();assert value['resource_id']==rid and value['hash']==hashlib.sha256(POLICY.read_bytes()).hexdigest()
                assert [(r['rule_id'],r['line'],r['quote']) for r in value['rules']]==[('R1',3,lines[2]),('R2',4,lines[3]),('R3',5,lines[4])]
                assert value['contract']['semantic_status']=='UNKNOWN' and value['contract']['owner_acceptance']=='PENDING'
            assert snapshot()==before
            results.append({'name':name,'status':'PASS','http':http})
        source_check('current_authorized_source_get')
        source_check('source_get_cross_project',project=foreign,http=403)
        source_check('source_get_foreign_resource',resource=foreignrid,http=403)
        source_check('source_get_malformed_rid',resource='res_INVALID',http=400)
        check('amount500_day10_approval_irrelevant', payload())
        check('amount501_requires_prior_approval', payload(amount=501, approval=False, applies=('TRUE','TRUE','FALSE'), decision='BLOCK', actions=('obtain_prior_approval',)))
        check('amount501_unknown_approval', payload(amount=501, applies=('TRUE','TRUE','FALSE'), decision='UNKNOWN', actions=('clarify_facts',)))
        check('approved_but_missing_receipt', payload(amount=501, approval=True, receipt=False, applies=('TRUE','TRUE','TRUE'), decision='BLOCK', actions=('obtain_receipt',)))
        check('receipt_restored_day11_still_unknown', payload(days=11, decision='UNKNOWN', actions=('clarify_late_policy',)))
        check('trip_unknown', payload(trip=None, days=None, applies=('UNKNOWN','FALSE','FALSE'), decision='UNKNOWN', actions=('clarify_facts',)))
        check('amount_unknown', payload(amount=None, applies=('TRUE','UNKNOWN','FALSE'), decision='UNKNOWN', actions=('clarify_facts',)))
        check('receipt_unknown', payload(receipt=None, applies=('TRUE','FALSE','UNKNOWN'), decision='UNKNOWN', actions=('clarify_facts',)))
        check('trip_not_ended', payload(trip=False, days=0, applies=('FALSE','FALSE','FALSE'), decision='BLOCK', actions=('wait_trip_end',)))
        check('contradictory_trip_elapsed_cannot_pass', payload(trip=False, days=2, applies=('FALSE','FALSE','FALSE'), decision='UNKNOWN', actions=('wait_trip_end','clarify_facts')), expected='FAIL')
        body = payload(); body['report']['findings'].reverse(); body['report']['explanation'] = 'A different arbitrary explanation, never semantically checked.'
        check('order_and_explanation_not_whole_json_equality', body)
        for name, mutate in [
            ('wrong_rule_quote', lambda b: b['report']['findings'][0]['citation'].update(quote=lines[5])),
            ('wrong_line', lambda b: b['report']['findings'][0]['citation'].update(line=6)),
            ('duplicate_rule', lambda b: b['report']['findings'][1].update(rule_id='R1')),
            ('reset_deadline', lambda b: b['report'].update(receipt_restarts_deadline=True)),
            ('wrong_500_operator', lambda b: b['report']['findings'][1].update(applies='TRUE')),
            ('invented_absolute_date', lambda b: b['report'].update(absolute_date='2026-10-17')),
            ('wrong_decision', lambda b: b['report'].update(decision='BLOCK')),
            ('duplicate_action', lambda b: b['report'].update(next_actions=['submit_claim_and_receipt']*2)),
        ]:
            body=payload(); mutate(body); check(name, body, expected='FAIL')
        for name, mutate in [
            ('bool_amount', lambda b: b['scenario'].update(amount=True)),
            ('bool_elapsed_days', lambda b: b['scenario'].update(elapsed_days=True)),
            ('numeric_boolean', lambda b: b['scenario'].update(trip_ended=1)),
            ('extra_caller_pass', lambda b: b.update(PASS=True)),
            ('missing_rule', lambda b: b['report']['findings'].pop()),
        ]:
            body=payload(); mutate(body); check(name, body, http=422)
        body=payload(); body['expected_source_hash']='0'*64; check('wrong_source_hash',body,http=409)
        body=payload(); body['expected_contract_fingerprint']='0'*64; check('wrong_contract',body,http=409)
        body=payload(); body['resource_id']=foreignrid; check('foreign_resource',body,http=403)
        client.headers['Authorization']='Bearer other-offline-token'
        check('foreign_owner_cannot_review',payload(),http=403)
        client.headers['Authorization']='Bearer independent-offline-token'
        changed=POLICY.read_text().replace('超过500元', '超过900元')
        with store.tx() as c:
            c.execute(update(resources).where(resources.c.id==rid).values(content=changed))
        check('stored_source_stale_hash',payload(),http=400)
        with store.tx() as c:
            c.execute(update(resources).where(resources.c.id==rid).values(hash=hashlib.sha256(changed.encode()).hexdigest()))
        check('stored_source_coherently_changed_hash',payload(),http=409)
        with store.tx() as c:
            c.execute(update(resources).where(resources.c.id==rid).values(content=POLICY.read_text(),hash=hashlib.sha256(POLICY.read_bytes()).hexdigest()))
        with store.tx() as c:
            c.execute(update(resources).where(resources.c.id==rid).values(format='csv'))
        check('same_pinned_bytes_csv_metadata_rejected',payload(),http=400)
        with store.tx() as c:
            c.execute(update(resources).where(resources.c.id==rid).values(format='txt'))
        with store.tx() as c:
            runtime=c.execute(select(projects.c.runtime_id).where(projects.c.id==pid)).scalar_one()
        for principal in (owner, runtime):
            with store.tx() as c:
                c.execute(update(grants).where(grants.c.project_id==pid, grants.c.principal_id==principal).values(revoked=True))
            check('revoked_'+('owner' if principal==owner else 'runtime'),payload(),http=403)
            source_check('source_get_revoked_'+('owner' if principal==owner else 'runtime'),http=403)
            with store.tx() as c:
                c.execute(update(grants).where(grants.c.project_id==pid, grants.c.principal_id==principal).values(revoked=False))
        with store.tx() as c:
            c.execute(update(grants).where(grants.c.project_id==pid).values(expires_at=0))
        check('expired_grants',payload(),http=403)
        source_check('source_get_expired',http=403)
    store.engine.dispose()

print(json.dumps({'base': 'd9fcdd8', 'mode': 'independent handwritten HTTP oracle; no network/model/gold',
    'count': len(results), 'results': results}, indent=2))
