import copy
import hashlib
import json
import socket
from pathlib import Path

from pydantic import ValidationError

from sim2act.db import fingerprint
from sim2act.errors import DomainError
from sim2act.one_shot_preparation import CAPS, CHECKLIST, assess, prepare

ROOT=Path('/workspace/Sim2Act-bounded-semantic-suite')
results=[]
def no_network(*args, **kwargs):
    raise AssertionError('Network disabled during independent preflight review')
socket.create_connection=no_network
socket.socket.connect=no_network

def blocked(result):
    assert result['live_ready'] is False
    assert type(result['effective_request_budget']) is int and result['effective_request_budget']==0
    assert result['network_requests']==0

prepared=prepare(ROOT)
blocked(prepared)
scope=prepared['scope']; fp=prepared['scope_fingerprint']
assert set(p['id'] for p in scope['public_packages'])=={'a-source','a-cold','b-source','b-cold'}
assert sum(len(p['resources']) for p in scope['public_packages'])==6
assert all('/gold/' not in r['path'] and 'rubric' not in r['path'] for p in scope['public_packages'] for r in p['resources'])
results.append({'name':'four_public_packages_six_resources_no_gold','status':'PASS'})
empty=assess(prepared,{},now=20)
blocked(empty); assert empty['state']=='BLOCKED_PENDING_NEW_FULL_APPROVAL_AND_EVIDENCE'
results.append({'name':'empty_input_blocked','status':'PASS'})
receipt={'artifact_sha256':'a'*64,'prepared_scope_fingerprint':fp}
full={'approval_receipt':receipt,'identity_fingerprint':'b'*64,
    'revoked_identity_fingerprints':['c'*64], 'previous_terminated_at':10.0,
    'approved_at':15.0,'expires_at':25.0,'approved_caps':copy.deepcopy(CAPS),
    'receipts':{name:copy.deepcopy(receipt) for group in CHECKLIST.values() for name in group
        if name not in {'fresh_full_approval','new_unrevoked_identity'}}}
complete=assess(prepared,full,now=20)
blocked(complete); assert complete['state']=='DECLARATIONS_COMPLETE_FOR_REVIEW'
assert all(c['status']=='DECLARED_NOT_AUTHORIZATION' for c in complete['checks'])
results.append({'name':'all_claimed_receipts_still_no_authorization','status':'PASS'})
for name, mutate in [
    ('expired_approval',lambda b:b.update(expires_at=20.0)),
    ('old_approval_before_termination',lambda b:b.update(approved_at=9.0)),
    ('future_approval',lambda b:b.update(approved_at=22.0)),
    ('same_revoked_identity',lambda b:b.update(identity_fingerprint='c'*64)),
    ('no_previous_identity_revocation',lambda b:b.update(revoked_identity_fingerprints=[])),
    ('missing_unknown_usage_stop',lambda b:b['receipts'].pop('unknown_usage_and_outcome_stop')),
    ('wrong_scope_receipt',lambda b:b['approval_receipt'].update(prepared_scope_fingerprint='0'*64)),
    ('smaller_budget_unapproved',lambda b:b['approved_caps'].update(requests=2)),
]:
    value=copy.deepcopy(full); mutate(value); result=assess(prepared,value,now=20)
    blocked(result); assert result['state']=='BLOCKED_PENDING_NEW_FULL_APPROVAL_AND_EVIDENCE'
    results.append({'name':name,'status':'PASS'})
for name, mutate in [
    ('bool_cap',lambda b:b['approved_caps'].update(repairs=False)),
    ('malformed_revoked_identity',lambda b:b.update(revoked_identity_fingerprints=['not-a-hash'])),
    ('unknown_extra_metadata',lambda b:b.update(token='caller private token forbidden')),
    ('unknown_gate',lambda b:b['receipts'].update(execute_live=receipt)),
]:
    value=copy.deepcopy(full); mutate(value)
    try: assess(prepared,value,now=20)
    except (DomainError,ValidationError): pass
    else: raise AssertionError(name)
    results.append({'name':name,'status':'PASS'})
for name, mutate in [
    ('caller_cap_rehash',lambda p:p['scope']['proposed_caps_not_approved'].update(requests=999)),
    ('caller_remove_checks_rehash',lambda p:p['scope']['checklist']['before'].clear()),
    ('caller_replace_source_rehash',lambda p:p['scope']['public_packages'][0]['resources'][0].update(sha256='0'*64)),
    ('caller_component_rehash',lambda p:p['scope']['components'].update({'src/sim2act/protocol_egress.py':'0'*64})),
    ('caller_enable_live',lambda p:p.update(live_ready=True)),
    ('caller_budget_bool',lambda p:p.update(effective_request_budget=False)),
]:
    value=copy.deepcopy(prepared); mutate(value); value['scope_fingerprint']=fingerprint(value['scope'])
    try: assess(value,{},now=20)
    except DomainError as error: assert error.code=='VERSION_CONFLICT'
    else: raise AssertionError(name)
    results.append({'name':name,'status':'PASS'})
for now in (True, float('inf'), float('nan')):
    try: assess(prepared,full,now=now)
    except DomainError as error: assert error.code=='INVALID_INPUT'
    else: raise AssertionError('invalid_clock')
    results.append({'name':'invalid_clock_'+repr(now),'status':'PASS'})
prepared['scope']['proposed_caps_not_approved']['requests']=999
prepared['scope']['checklist']['before'].clear()
assert CAPS['requests']==14 and len(CHECKLIST['before'])==10
assert prepare(ROOT)['scope']['proposed_caps_not_approved']['requests']==14
results.append({'name':'return_value_cannot_pollute_module_constants','status':'PASS'})
print(json.dumps({'count':len(results),'results':results,
    'hashes':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['src/sim2act/one_shot_preparation.py','scripts/prepare-one-shot-experiment.py']},
    'boundaries':['Metadata only; no receipts signatures validated','No actual wire measured','No LIVE/API executor, credentials or identity created','No real model semantic or owner acceptance']},indent=2))
