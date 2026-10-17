"""Independent sequential-HTTP oracle for the three navigation confirmations."""
import hashlib
import json
from pathlib import Path
import sys

roots=[Path(x) for x in sys.argv[1:]]
records=[]
candidates={}
for root in roots:
    for p in sorted(root.glob('*/page-result.json')):
        if p.parent.name.endswith('current'):
            continue
        info=json.loads((p.parent/'info.json').read_text())
        if info['case'] in ('return-preview','return-release','return-adoption'):
            candidates[info['case']]=p
for case,p in sorted(candidates.items()):
    if p.parent.name.endswith('current'):
        continue
    info=json.loads((p.parent/'info.json').read_text())
    case=info['case']
    if case not in ('return-preview','return-release','return-adoption'):
        continue
    page=json.loads(p.read_text())
    assert page['status']=='PASS',p
    trace=page['requests']
    path='/api/internal/instances/'+info['instance']+'/csv-goal-revisions'
    context_indices=[i for i,r in enumerate(trace) if r['method']=='GET' and r['path']==path+'/context']
    assert len(context_indices)==2,(case,context_indices)
    start=context_indices[1]
    end=next(i for i in range(start+1,len(trace)) if trace[i]['method']=='POST')
    segment=trace[start:end]
    assert all(r['method']=='GET' and r['status']==200 for r in segment),(case,segment)
    original=next(r for r in trace if r['method']=='POST' and r['path']==path+'/previews')
    key=original['body']['request_key']
    preview=original['response']
    ctx=segment[0]['response']
    assert ctx==preview['context']
    assert (ctx['instance_id'],ctx['app_id'],ctx['project_id'])==(info['instance'],info['app'],info['project'])
    assert preview['baseline_input']['column']=='amount' and preview['input']['column']=='quantity'
    expected=[path+'/context',path+'/previews/'+key]
    if case in ('return-release','return-adoption'):
        approval=next(r['response'] for r in trace[:start] if r['method']=='POST' and r['path']==path+'/version-approvals')
        expected += [path+'/checks/'+key,path+'/version-approvals/'+key,'/api/internal/approvals/'+approval['id']]
    if case=='return-adoption':
        hint=next(r['response'] for r in trace[:start] if r['method']=='POST' and r['path']==path+'/adoption-approvals')
        accepted=next(r['response'] for r in trace[:start] if r['method']=='GET' and r['path']==path+'/adoption-approvals/'+key)
        assert accepted['id']==hint['id'] and accepted['fingerprint']==hint['fingerprint']
        expected += ['/api/internal/releases/'+accepted['payload']['target_release_id'],path+'/adoption-approvals/'+key]
    actual=[r['path'] for r in segment]
    assert actual==expected,(case,actual,expected)
    next_request=trace[end]
    if case=='return-preview':
        assert next_request['path']==path+'/checks' and next_request['body']['request_key']==key
    elif case=='return-release':
        assert next_request['path']=='/api/internal/approvals/'+approval['id']+'/commit'
        assert next_request['body']['fingerprint']==approval['fingerprint']
    else:
        assert next_request['path']=='/api/internal/instances/'+info['instance']+'/switch-approvals/'+accepted['id']+'/commit'
        assert next_request['body']['fingerprint']==accepted['fingerprint']
    records.append(dict(case=case,page=str(p),page_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source_key=key,returned_current_context_index=start,next_explicit_post_index=end,exact_fresh_gets=actual,navigation_posts=0,complete_confirmation_and_result_assertions=page['checks']))
assert {r['case'] for r in records}=={'return-preview','return-release','return-adoption'}
value=dict(status='PASS',scope='Three fresh GET sequences, bounded by second current-context read and next explicit POST; no pre-navigation requests can satisfy these assertions.',records=records)
print(json.dumps(value,ensure_ascii=False,indent=2))
