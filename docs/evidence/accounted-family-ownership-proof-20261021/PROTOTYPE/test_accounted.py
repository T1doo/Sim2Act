"""Offline necessary ownership/compatibility counterexamples, no admission.

Archived bytes are real third-window evidence; rows/identities below are complete
synthetic stand-alone values, not recovered authorized Runs or an entire G0.
"""
import base64
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from sqlalchemy.sql.elements import quoted_name

from sim2act import natural_live_admission as gate
from sim2act import natural_source_archives as archive
from sim2act import pa_trial_dispatch as dispatch
from sim2act import production_trial_policy as policy
from sim2act import production_trial_sender as sender
from sim2act.contracts import strict_json
from sim2act.db import runs, attempts, fingerprint
from sim2act.errors import DomainError
from sim2act.goal_applications import response_archive
from sim2act.model import normalize_usage
from sim2act.natural_spec_runtime import _cold_graph_bytes
from accounted import capture_accounted
from owned_graph import Bounds, Packet, Rejected, View, freeze, resolve, materialize_oracle

ROOT = Path(__file__).resolve().parent
REPO = Path('/workspace/Sim2Act')
WIRE = REPO / 'docs/evidence/g0-monitored-third-20261021/RUN/mock-exchanges.jsonl'
# Test fixture limits only. These are NOT proposed new product allowances.
LIMITS = Bounds(20000, 50000, 128, 4 * 1024 * 1024, 8 * 1024 * 1024)
sha = lambda body: hashlib.sha256(body).hexdigest()


def native_row(value, hidden=None):
    keys = list(value)
    data = tuple(value[k] for k in keys)
    index = {k: i for i, k in enumerate(keys)}
    if hidden is not None:
        index['hidden_alias'] = len(data)
        data += (hidden,)
    return RowMapping(SimpleResultMetaData(keys), None, index, data)


def family(role):
    records = [json.loads(line) for line in WIRE.read_text().splitlines()]
    indexes = range(3) if role == 'generate' else range(3, 5)
    rid = 'run_' + ('1' if role == 'generate' else '2') * 32
    run = dict.fromkeys(runs.c.keys())
    run.update(id=rid, project_id='project', principal_id='user', runtime_id='runtime',
        goal='offline', resource_refs=[], status='SUCCEEDED', request_key='offline',
        fingerprint='a' * 64, created_at=1., fence=1, version=1, cancel_intent=False,
        context={'retained': ['all', {'columns': True}]}, result={}, error=None)
    actual, chains, ns = [], [], []
    for i in indexes:
        record = records[i]
        assert record['classification'] == 'SYNTHETIC_MOCK_TRANSPORT_NOT_REAL_HTTP'
        wire, payload = (base64.b64decode(record[k]) for k in ('request_b64', 'response_b64'))
        parsed = strict_json(payload, 32768)
        original, canonical = response_archive(parsed)
        usage = normalize_usage(parsed)
        aid = 'attempt_' + f'{i+1:032x}'
        identity = policy.ReservationIdentity(requirements_fingerprint='a'*64,
            approval_fingerprint='b'*64, stage=role, stage_fingerprint='c'*64,
            run_id=rid, runtime_id='runtime', version=1, fence=1, worker_id='worker',
            account_id='offline-account', quota_subject='offline-quota', attempt_id=aid,
            wire_sha256=sha(wire), wire_bytes=len(wire))
        outcome = policy.Outcome(outcome='RECEIVED', response_sha256=canonical['sha256'],
            response_ascii_bytes=canonical['bytes'], **usage['tokens'])
        slot = policy.Slot(identity=identity, reserved_at=100. + 60*i,
            attempted=True, settlement=outcome, accepted=True)
        capture = sender.Capture(raw_sha256=sha(payload), raw_bytes=len(payload),
            body_b64=base64.b64encode(payload).decode('ascii'), complete=True,
            received_response=True, omission='NONE', canonical_sha256=canonical['sha256'],
            canonical_ascii_bytes=canonical['bytes'], response_verdict='VALID_PROTOCOL', outcome=outcome)
        row = dict.fromkeys(attempts.c.keys())
        envelope = strict_json(wire, 32768)
        row.update(id=aid, run_id=rid, created_at=float(i+1), mode='MOCK',
            request_model=envelope['model'], response_model=envelope['model'],
            status='RECEIVED' if role == 'generate' else 'VERIFIED', usage=usage,
            reserved_tokens=100, parameters={'natural_spec_wire':dict(sha256=sha(wire),
                bytes=len(wire), characters=len(wire.decode('utf8')))},
            response=dict(received_raw=original, raw_evidence=canonical), elapsed=.01)
        actual.append(native_row(row))
        checked = native_row(copy.deepcopy(row))
        chains.append((slot, capture, parsed, checked, wire, payload))
        if role == 'source':
            request = archive._body(run, aid, wire, True, None, archive.REQUEST)
            response = archive._body(run, aid, payload, True, canonical['sha256'], archive.RESPONSE)
            ns.append((aid, request, wire, response, payload))
    return native_row(run), actual, tuple(chains), tuple(ns)


def raw_shape(facts):
    run, actual, chains, ns = facts
    return dict(run=dict(run), actual=tuple(dict(a) for a in actual),
        chains=tuple((s.model_dump(), c.model_dump(), p, dict(a), w, b) for s,c,p,a,w,b in chains),
        ns_reads=tuple((aid,q.model_dump(),w,r.model_dump(),b) for aid,q,w,r,b in ns))


def assert_only_immutable(value):
    # Recursively inspect actual stored objects, rather than merely trusting hash.
    seen = set()
    def visit(item):
        if id(item) in seen:
            return
        seen.add(id(item))
        assert type(item) in (Packet, tuple, str, bytes, int, bool, float, type(None))
        if type(item) in (Packet, tuple):
            for child in item:
                visit(child)
    visit(value)


def first_difference(a,b,path=()):
    if type(a) is not type(b):
        return path,type(a).__name__,type(b).__name__
    if type(a) is dict:
        if set(a)!=set(b):return path,'keys'
        for key in a:
            if type(key) is not str:return path,'key type',type(key).__name__
            found=first_difference(a[key],b[key],path+(key,))
            if found:return found
    elif type(a) in (list,tuple):
        if len(a)!=len(b):return path,'length'
        for i,(x,y) in enumerate(zip(a,b)):
            found=first_difference(x,y,path+(i,))
            if found:return found
    elif a!=b:return path,'value'
    return None


@pytest.mark.parametrize('role', ['generate', 'source'])
def test_complete_real_schema_owned_values_and_legacy_fingerprints(role):
    facts = family(role)
    packet = capture_accounted(facts, role, LIMITS)
    expected = raw_shape(facts)
    detached = materialize_oracle(packet)['value']
    # Old raw local pin retains quoted_name keys; the controlled business view
    # normalizes those keys exactly as the existing pure RowMapping helper.
    # The original key tags/data/index remain in the owned storage sidecar.
    assert expected == detached
    expected['run']=gate._trial_pure_mapping(facts[0])
    expected['actual']=tuple(gate._trial_pure_mapping(a) for a in facts[1])
    expected['chains']=tuple((s,c,p,gate._trial_pure_mapping(facts[2][i][3]),w,b)
        for i,(s,c,p,a,w,b) in enumerate(expected['chains']))
    assert gate._trial_typed_equal(expected, detached),first_difference(expected,detached)
    assert_only_immutable(packet)
    view = resolve(packet)['value']
    assert len(view['chains']) == (3 if role == 'generate' else 2)
    assert view['run']['id'] == facts[0]['id']
    assert len(materialize_oracle(packet)['row_storage']) == 1+2*len(facts[1])
    for i, chain in enumerate(facts[2]):
        slot,capture,parsed,checked,wire,payload = chain
        saved = detached['chains'][i]
        assert fingerprint(saved[0]) == fingerprint(slot.model_dump())
        assert fingerprint(saved[1]) == fingerprint(capture.model_dump())
        assert fingerprint(dict(namespace=sender.CAPTURE, identity=saved[0]['identity'])) == fingerprint(sender._capture_request(slot.identity))
        assert saved[4:] == (wire,payload)
        assert sha(saved[4]) == slot.identity.wire_sha256
        assert sha(saved[5]) == capture.raw_sha256
        dispatch._stage_usage_from_facts(detached['actual'][i],role,slot,saved[2],saved[3])
        dispatch._journal_capture_from_facts(slot,capture,saved[5])
    for i, read in enumerate(facts[3]):
        aid,request,wire,response,payload = read
        saved = detached['ns_reads'][i]
        for original, projected in ((request,saved[1]),(response,saved[3])):
            assert fingerprint(original.model_dump()) == fingerprint(projected)
            anchors=[dict(attempt_id=aid,archive_fingerprint=fingerprint(projected))]
            assert archive._body_payload_from_facts(original,anchors,aid) in (wire,payload)
        # Public receipt fields use identical raw/canonical bytes, no packet id.
        canonical=response_archive(strict_json(saved[4],32768))[1]
        public=dict(attempt_id=aid,request_bytes=len(saved[2]),request_sha256=sha(saved[2]),
            decoded_body_bytes=len(saved[4]),decoded_body_sha256=sha(saved[4]),
            canonical_ascii_bytes=canonical['bytes'],canonical_ascii_sha256=canonical['sha256'])
        assert public['request_sha256']==request.sha256
        assert public['decoded_body_sha256']==response.sha256
        assert public['canonical_ascii_sha256']==response.canonical_sha256


@pytest.mark.parametrize('role', ['generate', 'source'])
def test_every_aid_postseal_source_mutation_isolated_next_snapshot_reads_fresh(role):
    facts=family(role)
    packet=capture_accounted(facts,role,LIMITS)
    before=packet.encoded
    for i,chain in enumerate(facts[2]):
        slot,capture,parsed,checked,wire,payload=chain
        operations=[(slot.identity.__dict__,'worker_id','changed-worker'),
            (slot.settlement.__dict__,'total_tokens',None),
            (capture.__dict__,'raw_sha256','d'*64),
            (parsed,'new_nested_field',[i]),
            (checked['parameters'],'extra',{'aid':i}),
            (facts[1][i]['parameters'],'retained_extra',[i])]
        if role=='source':
            operations += [(facts[3][i][1].__dict__,'sha256','e'*64),
                (facts[3][i][3].__dict__,'received_complete',False)]
        for target,key,value in operations:
            absent=object();old=target.get(key,absent)
            target[key]=value
            assert packet.encoded==before
            assert capture_accounted(facts,role,LIMITS).encoded!=before
            if old is absent:del target[key]
            else:target[key]=old
    facts[0]['context']['retained'].append('changed')
    assert packet.encoded==before
    assert capture_accounted(facts,role,LIMITS).encoded!=before


def test_unknown_callbacks_and_typed_storage_drift_rejected_before_serializer():
    called=[]
    class Foreign:
        def __iter__(self):called.append('iter');raise AssertionError
        def __eq__(self,other):called.append('eq');raise AssertionError
        def __str__(self):called.append('str');raise AssertionError
        def __reduce__(self):called.append('reduce');raise AssertionError
    facts=family('generate')
    facts[2][2][0].identity.__dict__['worker_id']=Foreign()
    with pytest.raises(DomainError):capture_accounted(facts,'generate',LIMITS)
    with pytest.raises(Rejected):freeze({'hidden':Foreign()},LIMITS)
    view=resolve(freeze({'x':1},LIMITS))
    with pytest.raises(TypeError):view[Foreign()]
    assert called==[]
    facts=family('generate');facts[2][2][0].__dict__['extra_unmodelled']=1
    with pytest.raises(DomainError):capture_accounted(facts,'generate',LIMITS)


def test_flat_dag_memo_cycles_and_longest_path_bounds():
    data={'leaf':[1,True,1.,None,b'bytes']}
    sizes=[]
    for depth in range(41):
        packet=freeze(data,LIMITS)
        sizes.append((depth,len(packet.nodes),packet.edges,len(packet.encoded)))
        if depth<40:data=[data,data]
    assert sizes[-1][1]-sizes[0][1]==40
    assert sizes[-1][2]-sizes[0][2]==80
    assert sizes[-1][3]<sizes[0][3]+40*45
    ROOT.joinpath('DAG-MEASUREMENTS.json').write_text(json.dumps(dict(
        kind='representation sizes, not a timing benchmark',sizes=sizes),indent=2)+'\n')
    cycle=[];cycle.append(cycle)
    with pytest.raises(Rejected,match='cycle'):freeze(cycle,LIMITS)
    leaf=[0];shared=[leaf];root=[shared,[[shared]]]
    with pytest.raises(Rejected,match='depth'):freeze(root,LIMITS._replace(depth=4))
    assert freeze(root,LIMITS._replace(depth=5))
    for bound in ('nodes','edges','leaf_bytes','encoded_bytes'):
        with pytest.raises(Rejected):freeze({'x':[1,2,b'body']},LIMITS._replace(**{bound:1}))


def test_hidden_row_storage_cycle_foreign_values_and_duplicates():
    hidden={'not_visible':[1,2]}
    row=native_row({'visible':'v'},hidden)
    p=freeze(row,LIMITS)
    assert resolve(p)['visible']=='v'
    hidden['not_visible'].append(3)
    assert freeze(row,LIMITS).encoded!=p.encoded
    assert_only_immutable(p)
    hidden['back']=row
    with pytest.raises(Rejected,match='cycle'):freeze(row,LIMITS)
    with pytest.raises(Rejected):freeze(native_row({'visible':'v'},object()),LIMITS)
    duplicate=RowMapping(SimpleResultMetaData(['x',quoted_name('x',True)]),None,{'x':0},('v',))
    with pytest.raises(Rejected,match='duplicate'):freeze(duplicate,LIMITS)
    bad=RowMapping(SimpleResultMetaData(['x']),None,{'x':True},('v',))
    with pytest.raises(DomainError):freeze(bad,LIMITS)


def test_exact_scalar_sequence_types_and_alias_topology_not_business_version():
    packets=[freeze({'v':v},LIMITS) for v in (1,True,1.,-0.,0.,[1],(1,))]
    assert len({p.encoded for p in packets})==len(packets)
    for v in (float('inf'),float('nan')):
        with pytest.raises(Rejected,match='nonfinite'):freeze(v,LIMITS)
    shared={'x':[1]}
    a,b=freeze([shared,shared],LIMITS),freeze([copy.deepcopy(shared),copy.deepcopy(shared)],LIMITS)
    assert a.digest!=b.digest  # private shape, never a persisted business version
    assert fingerprint(materialize_oracle(a))==fingerprint(materialize_oracle(b))
    detached=materialize_oracle(a)
    assert detached[0] is detached[1]
    detached[0]['x'].append(2)
    assert resolve(a)[0]['x'][0]==1 and len(resolve(a)[0]['x'])==1


def test_existing_escaped_surrogate_string_domain_is_preserved():
    value=strict_json(b'{"unconsumed_extra":"\\ud800","low":"\\udfff"}',32768)
    assert _cold_graph_bytes(value)  # exact existing C implementation, no stand-in
    packet=freeze(value,LIMITS)
    assert gate._trial_typed_equal(materialize_oracle(packet),value)
    assert resolve(packet)['unconsumed_extra']=='\ud800'
    facts=family('source')
    facts[2][1][2]['unconsumed_extra']=value
    packet=capture_accounted(facts,'source',LIMITS)
    projected=materialize_oracle(packet)['value']['chains'][1][2]
    assert response_archive(projected)==response_archive(facts[2][1][2])


def test_shape_missing_extra_counts_and_role_rejected_without_issuing_authority():
    facts=family('generate')
    for role in ('source','cold'):
        with pytest.raises(Rejected):capture_accounted(facts,role,LIMITS)
    for changed in (facts[1][:2],facts[1]+[facts[1][0]]):
        with pytest.raises(Rejected):capture_accounted((facts[0],changed,facts[2],facts[3]),'generate',LIMITS)
    changed={str(k):v for k,v in dict(facts[0]).items()};del changed['context']
    with pytest.raises(Rejected):capture_accounted((changed,*facts[1:]),'generate',LIMITS)
    changed={str(k):v for k,v in dict(facts[0]).items()};changed['unexpected']='new'
    with pytest.raises(Rejected):capture_accounted((changed,*facts[1:]),'generate',LIMITS)


def test_legacy_rejections_remain_and_packet_is_not_semantic_authority():
    # A snapshot must retain bad/UNKNOWN facts, not normalize them into success.
    facts=family('source')
    slot,capture,parsed,checked,wire,payload=facts[2][1]
    original=checked['usage']['status'];checked['usage']['status']='unknown'
    packet=capture_accounted(facts,'source',LIMITS)
    saved=materialize_oracle(packet)['value']
    assert saved['chains'][1][3]['usage']['status']=='unknown'
    with pytest.raises(DomainError):dispatch._stage_usage_from_facts(facts[1][1],'source',slot,parsed,checked)
    with pytest.raises(DomainError):dispatch._stage_usage_from_facts(saved['actual'][1],'source',slot,saved['chains'][1][2],saved['chains'][1][3])
    checked['usage']['status']=original
    capture.__dict__['raw_sha256']='f'*64
    with pytest.raises(DomainError):dispatch._journal_capture_from_facts(slot,capture,payload)
    # Missing producer association proof is explicit: merely copying swapped
    # aids is possible and never creates an issued packet or execution permit.
    swapped=(facts[0],facts[1],tuple(reversed(facts[2])),facts[3])
    assert capture_accounted(swapped,'source',LIMITS)
    assert not hasattr(packet,'dispatch_authorized')
