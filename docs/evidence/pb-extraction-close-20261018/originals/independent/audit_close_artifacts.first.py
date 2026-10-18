"""Pure standard-library artifact audit. Imports no product or test modules; no HTTP/DB."""
import argparse
import collections
import datetime
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

P = argparse.ArgumentParser()
P.add_argument('--root', type=Path, required=True)
P.add_argument('--prefix', default='')
P.add_argument('--output', type=Path, required=True)
A = P.parse_args()
READS = {}

def raw(path):
    value = path.read_bytes()
    READS[str(path)] = {'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}
    return value

def obj(path):
    return json.loads(raw(path))

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()

def fp(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def dirs(path):
    return sorted(p for p in path.iterdir() if p.is_dir() and not p.is_symlink())

def http(folder):
    values = []
    for p in sorted((folder/'http').glob('*-metadata.json')):
        m = obj(p)
        b = raw(folder/m['response_file'])
        assert len(b) == m['response_bytes'] and hashlib.sha256(b).hexdigest() == m['response_sha256']
        req = obj(p.with_name(p.name.replace('-metadata', '-request-bytes')))
        request = raw(folder/req['file'])
        assert len(request) == req['bytes'] and hashlib.sha256(request).hexdigest() == req['sha256']
        assert (json.loads(request) if request else None) == m['request']
        try:
            response = json.loads(b)
        except ValueError:
            response = None
        values.append(dict(m, response=response, request_bytes_sha256=hashlib.sha256(request).hexdigest(),
            response_text=b.decode('utf-8'), metadata_file=str(p)))
    return values

def seeds(path):
    answer=[]
    for folder in dirs(path):
        if not folder.name.startswith('pb-extraction-close-fresh-source-seed'):
            continue
        proof=obj(folder/'seed-proof.json')
        provenance=obj(folder/'seed-copy-provenance.json')
        sealed=Path(provenance['sealed'])
        assert hashlib.sha256(raw(sealed)).hexdigest()==provenance['sealed_sha256']
        assert provenance['copy_row_mutations']==0 and provenance['all_owned_connections_closed']
        assert len(obj(folder/'model-wire.json'))==proof['generation_mock_requests']==3
        assert len(obj(folder/'runtime-wire.json'))==proof['source_mock_requests']==1
        claims=obj(folder/'source-worker-claims.json')
        assert claims['once_returned'] and claims['worker_calls']==1 and claims['lease_or_clock_mutations']==0
        assert claims['before']['clock']==claims['after']['clock']
        assert claims['before']['header']['created_at']==claims['after']['header']['created_at']
        assert claims['after']['header']['status']=='SUCCEEDED' and len(claims['after']['claims'])==1
        assert obj(folder/'source-before.json')==obj(folder/'source-after.json')
        answer.append(dict(folder=str(folder), sealed_sha256=provenance['sealed_sha256'],
            mock_requests=4, source_worker_claims=1, HTTP=len(http(folder)), rows=obj(folder/'seed-rows.json')))
    assert len(answer)==1
    return answer[0]

def xml(path):
    t=ET.fromstring(raw(path))
    cases=[]
    for c in t.iter('testcase'):
        tags=[child.tag for child in c]
        cases.append(dict(c.attrib, verdict=('ERROR' if 'error' in tags else 'FAIL' if 'failure' in tags
            else 'SKIP' if 'skipped' in tags else 'PASS') if c.get('name') else 'UNNAMED_NOT_PASS'))
    return cases

before_name='execution-inputs-before.json' if not A.prefix else A.prefix+'execution-inputs-before.json'
before=obj(A.root/before_name)
backend_path=A.root/(A.prefix+'backend-data')
ui_path=A.root/(A.prefix+'ui-data')
backend_xml=xml(A.root/(A.prefix+'backend-junit.xml'))
ui_xml=xml(A.root/(A.prefix+'ui-junit.xml'))
seed_b=seeds(backend_path)
seed_u=seeds(ui_path)
backend=[]
for folder in dirs(backend_path):
    if not folder.name.startswith('test_'):
        continue
    progress=obj(folder/'progress-summary.json')
    records=http(folder)
    errors=obj(folder/'errors.json')
    backend.append(dict(folder=str(folder), passed=progress['latest']['passed'], seconds=progress['elapsed_seconds'],
        HTTP=len(records), errors=errors,
        HTTP_error_receipts=[dict(path=m['path'], status=m['status'], response=m['response'],
            response_text=m['response_text'] if m['response'] is None else None,
            response_sha256=m['response_sha256']) for m in records if m['status']>=400]))
    assert not obj(folder/'model-wire.json') and not obj(folder/'runtime-wire.json')
    if (folder/'race-events.json').exists():
        events=obj(folder/'race-events.json')
        held=next(x for x in events if x['event']=='FIRST_PROJECT_LOCK_ACQUIRED')
        attempted=next(x for x in events if x['event']=='SECOND_BEGIN_IMMEDIATE_ATTEMPTED')
        assert held['thread_id']!=attempted['thread_id'] and held['dbapi_connection_id']!=attempted['dbapi_connection_id']
        assert any(x['event']=='OVERLAP_PROVED_FIRST_LOCK_HELD_SECOND_BEGIN_INCOMPLETE' for x in events)
        backend[-1]['race']=events
    for name in ['foreign-private-read-barrier.json','revoked-private-read-barrier.json','sibling-target-authority-before-pair.json','target-read-barrier.json']:
        p=folder/name
        if p.exists():
            d=obj(p); assert not d['blocked']; backend[-1].setdefault('barriers',{})[name]=dict(blocked=d['blocked'], evaluated_count=len(d.get('evaluated',[])))
ui=[]
fields=set('namespace principal_id project_id source_app_id source_instance_id source_run_id source_app_run_id source_release_id source_release_fingerprint source_result_version request_key request_fingerprint review_fingerprint candidate_fingerprint app_id runtime_id source_proof_fingerprint'.split())
for folder in dirs(ui_path):
    if not folder.name.startswith('test_'):
        continue
    page=obj(folder/'page-result.json');proof=obj(folder/'proof.json');actual=obj(folder/'actual-http.json');records=http(folder)
    assert page['status']==proof['status']=='PASS' and proof['node_exit_code']==0
    assert not page['page_errors'] and page['worker_calls']==proof['page_worker_calls']==proof['page_model_requests']==0
    assert obj(folder/'page-source-before.json')==obj(folder/'page-source-after.json')
    identity=proof['original_identity'];assert set(identity)==fields
    assert json.loads(page.get('closed_raw',page.get('original_raw')))==identity
    assert 'synthetic-test' not in page.get('closed_raw',page.get('original_raw'))
    # Every actual page request and served asset matches independent raw HTTP.
    have=collections.Counter((m['method'],m['path'],fp(m['request']),m['status']) for m in records)
    for m in actual:
        token=(m['method'],m['path'],fp(m['body']),m['status']);assert have[token]>0;have[token]-=1
        req=m.get('body_text');assert (json.loads(req) if req else None)==m['body']
        assert hashlib.sha256((req or '').encode()).hexdigest()==m['body_sha256']
        assert m['response']==(json.loads(m['response_text']) if m['response_text'] else None)
    for asset in page['static_resource_loads']:
        token=('GET',asset['path'],fp(None),asset['status']);assert have[token]>0;have[token]-=1
        assert before['inputs']['src/sim2act/web/'+('index.html' if asset['path']=='/' else asset['path'][1:])]['sha256']==asset['sha256']
    assert not +have
    assert len(page['static_resource_loads'])==27*page['boots']
    final=obj(folder/'page-final-rows.json');seed=seed_u['rows']
    for table,rows in seed.items():
        assert all(row in final[table] for row in rows),table
    delta={k:len(final[k])-len(seed[k]) for k in seed if len(final[k])!=len(seed[k])}
    expected=dict(app_drafts=1,delivery_graph_requests=6 if page['scenario']=='preaccept-close' else 4,grants=2,principals=1,task_extractions=1)
    assert delta==expected,(delta,expected)
    api=[m for m in actual if m['method']=='POST' and m['path'].endswith('/extractions')]
    accepted=[m for m in api if m['status']==201];assert len(accepted)==1
    saved=accepted[0]['response']; assert fp(accepted[0]['body'])==saved['request_fingerprint']
    app=next(row for row in final['app_drafts'] if row['id']==saved['id']);assert fp(app['candidate'])==saved['candidate_fingerprint']
    for suffix in ['', '_seal']:
        row=next(x for x in final['delivery_graph_requests'] if x['app_id']==saved['id'] and x['kind']=='pb_natural_spec_extract'+suffix)
        assert row['snapshot']['request']==accepted[0]['body'] and row['fingerprint']==fp(row['snapshot'])
        assert row['request_fingerprint']==fp(accepted[0]['body'])
    item=dict(folder=str(folder),scenario=page['scenario'],checks=len(page['checks']),actions=len(page['actions']),boots=page['boots'],
        page_API=len(page['requests']),assets=len(page['static_resource_loads']),actual_HTTP=len(records),delta=delta,
        accepted_extractions=1, page_Worker_calls=0, original_request_fingerprint=identity['request_fingerprint'])
    if page['scenario']=='preaccept-close':
        terminal=page['terminal'];assert terminal['identity']==identity and set(terminal)==set('namespace status acceptance principal_id project_id source_run_id request_key identity request_fingerprint close_request_fingerprint new_model_requests project_writes metadata_writes formal_publication_enabled receipt_fingerprint'.split())
        assert terminal['status']=='CLOSED_NOT_ACCEPTED' and terminal['acceptance']=='NOT_ACCEPTED'
        assert terminal['request_fingerprint']==identity['request_fingerprint']
        assert terminal['close_request_fingerprint']==fp(page['close_body'])
        unsigned={k:v for k,v in terminal.items() if k!='receipt_fingerprint'};assert fp(unsigned)==terminal['receipt_fingerprint']
        digest,=page['terminal_digest_observations'];assert digest['actual_result_computed_before_hold'] and digest['released'] and digest['delivered']
        assert bytes.fromhex(digest['input_utf8_hex'])==digest['input_utf8'].encode()==canonical(unsigned)
        assert hashlib.sha256(bytes.fromhex(digest['input_utf8_hex'])).hexdigest()==digest['actual_digest_hex']==terminal['receipt_fingerprint']
        assert digest['events']==['HOLD_ALREADY_COMPUTED_ACTUAL_SHA_RESULT','USER_EXPLICITLY_CLOSES_OLD_REVIEW_PANEL','RELEASE_ACTUAL_SHA_RESULT','DELIVER_UNMODIFIED_ACTUAL_SHA_RESULT']
        assert obj(folder/'page-result.json.terminal-digest.json')==[digest]
        captured=obj(folder/'page-result.json.deferred-wire.json')
        late,=[m for m in actual if m.get('transport_phase')]
        assert captured['body_text'].encode()==late['body_text'].encode()==bytes.fromhex(captured['body_text_utf8_hex'])
        assert captured['body']==late['body'] and fp(late['body'])==identity['request_fingerprint']
        assert captured['body_text_sha256']==late['body_sha256']==page['deferred_body_text_sha256']
        assert late['status']==409 and late['response']['error']['code']=='VERSION_CONFLICT'
        assert len(api)==2 and len([m for m in actual if m['method']=='POST' and m['path'].endswith('/close')])==1
        for suffix in ['', '_seal']:
            row=next(x for x in final['delivery_graph_requests'] if x['kind']=='pb_natural_spec_terminal'+suffix)
            assert row['snapshot']['response']==terminal and row['fingerprint']==fp(row['snapshot'])
        item.update(real_terminal_SHA_digest_hex=digest['actual_digest_hex'],actual_original_late_POST=1,closed_terminal_rows=2)
    else:
        assert len(api)==1 and not page['terminal_digest_observations']
        refused,=[m for m in actual if m['method']=='POST' and m['path'].endswith('/close')]
        assert refused['status']==409 and refused['response']['error']['code']=='VERSION_CONFLICT'
        assert fp(accepted[0]['body'])==identity['request_fingerprint']
        item.update(closed_terminal_rows=0,actual_original_late_POST=0)
    assert not obj(folder/'model-wire.json') and not obj(folder/'runtime-wire.json')
    ui.append(item)
# Scope only to completed batch. Do not open any SQLite DB, especially running final batch.
result=dict(classification='PURE_ORIGINAL_ARTIFACT_AUDIT_NO_PRODUCT_HTTP_WORKER_MODEL_OR_DB',recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    prefix=A.prefix,backend_junit=backend_xml,ui_junit=ui_xml,backend=backend,ui=ui,
    seeds=[{k:v for k,v in x.items() if k!='rows'} for x in [seed_b,seed_u]],mock_requests=8,
    source_worker_claims=2,real_model_requests=0,read_files_count=len(READS),read_files=READS)
A.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['backend','read_files']},ensure_ascii=False))
