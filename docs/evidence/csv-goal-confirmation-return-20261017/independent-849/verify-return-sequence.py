from pathlib import Path
import json
out=Path(__file__).parent
original=Path('/tmp/csv-goal-confirmation-independent-776d7658-20261017')
page_dirs={}
for group in ['group-a','group-b']:
 for d in sorted({p.resolve() for p in (original/(group+'-data')).glob('test_visible_same_goal_revisio*') if p.is_dir()}):
  info=json.loads((d/'info.json').read_text());page=json.loads((d/'page-result.json').read_text());page_dirs[info['case']]=(d,info,page)
for d in sorted({p.resolve() for p in (out/'data').glob('test_visible_same_goal_revisio*') if p.is_dir()}):
 info=json.loads((d/'info.json').read_text());page=json.loads((d/'page-result.json').read_text());assert info['case']=='return-adoption' and page['status']=='PASS';page_dirs['return-adoption']=(d,info,page)
expected=['return-preview','return-release','return-adoption']
rows=[]
for case in expected:
 d,info,page=page_dirs[case]
 assert page['status']=='PASS'
 req=page['requests'];base='/api/internal/instances/'+info['instance']+'/csv-goal-revisions'
 stage={'return-preview':'preview','return-release':'release','return-adoption':'adoption'}[case]
 suffix={'preview':'/previews','release':'/version-approvals','adoption':'/adoption-approvals'}[stage]
 post_index=next(i for i,r in enumerate(req) if r['method']=='POST' and r['path']==base+suffix)
 hint=req[post_index]['response'];assert req[post_index]['status']==201
 accepted=hint
 if stage=='adoption':
  original_read=next(r for r in req[post_index+1:] if r['method']=='GET' and '/adoption-approvals/' in r['path'])
  assert original_read['status']==200
  accepted=original_read['response']
  assert accepted['id']==hint['id'] and accepted['fingerprint']==hint['fingerprint']
 contexts=[i for i,r in enumerate(req) if r['method']=='GET' and r['path']==base+'/context']
 assert len(contexts)>=2 and contexts[0]<post_index
 start=next(i for i in contexts if i>post_index);assert start==contexts[1]
 following=next(i for i in range(start+1,len(req)) if req[i]['method']=='POST')
 # The accepted stage and subsequent explicit next action bound the whole return.
 assert not any(r['method']=='POST' for r in req[post_index+1:following])
 segment=req[start:following];assert all(r['method']=='GET' and r['status']==200 for r in segment)
 def read(path):
  found=[r for r in segment if r['path']==path];assert len(found)==1,(case,path,found);return found[0]['response']
 ctx=read(base+'/context');assert ctx['instance_id']==info['instance'] and ctx['project_id']==info['project'] and ctx['app_id']==info['app']
 prev=next(r['response'] for r in req if r['method']=='POST' and r['path']==base+'/previews');key=prev['request_key']
 assert read(base+'/previews/'+key)==prev
 assert ctx==prev['context']
 if stage in ['release','adoption']:
  checked=read(base+'/checks/'+key);assert checked['status']=='PASS' and checked['request_key']==key
  approved=next(r['response'] for r in req if r['method']=='POST' and r['path']==base+'/version-approvals')
  assert read(base+'/version-approvals/'+key)==approved
  live=read('/api/internal/approvals/'+approved['id'])
  assert live['fingerprint']==approved['fingerprint'] and live['payload']['snapshot']==approved['snapshot']
  assert approved['snapshot']['csv_goal_revision_source']['check_fingerprint']==checked['check_fingerprint']
 if stage=='adoption':
  assert read(base+'/adoption-approvals/'+key)==accepted
  release=read('/api/internal/releases/'+accepted['payload']['target_release_id'])
  assert release['approval_id']==approved['id'] and release['fingerprint']==accepted['payload']['target_fingerprint']
  if following<len(req):assert req[following]['path']=='/api/internal/instances/'+info['instance']+'/switch-approvals/'+accepted['id']+'/commit'
  if following<len(req):assert req[following]['body']=={'fingerprint':accepted['fingerprint']}
 elif stage=='release':
  assert req[following]['path']=='/api/internal/approvals/'+accepted['id']+'/commit'
  assert req[following]['body']=={'fingerprint':accepted['fingerprint']}
 else:
  assert req[following]['path']==base+'/checks'
  assert req[following]['body']['request_key']==key and req[following]['body']['expected_preview_fingerprint']==prev['preview_fingerprint']
 rows.append({'source_sha':('849a931f7dbb8926ca9cbe166c3cfba3527dbf0a' if case=='return-adoption' else '776d76581c7f811f39af584283578d9b252a994b'),'page_result':str(d/'page-result.json'),'case':case,'accepted_stage_post_index':post_index,'baseline_context_index':contexts[0],'fresh_return_context_index':start,'next_explicit_post_index':following,'return_segment':segment,'navigation_and_revalidation_post_count':0,'exact_stage_payload_and_frozen_columns_assertions':[c for c in page['checks'] if c.startswith(stage+' ')]})
errors=[]
for case,(d,info,page) in page_dirs.items():
 for i,r in enumerate(page['requests']):
  if r.get('status',0)>=400:errors.append({'case':case,'index':i,'method':r['method'],'path':r['path'],'status':r['status'],'error':r.get('response',{}).get('error')})
(out/'strict-return-sequence-proof.json').write_text(json.dumps({'status':'PASS','cases':rows,'page_case_count':len(page_dirs),'all_page_http_error_responses':errors},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS','strict_return_cases':len(rows),'page_cases':len(page_dirs),'http_error_responses':errors},ensure_ascii=False))
