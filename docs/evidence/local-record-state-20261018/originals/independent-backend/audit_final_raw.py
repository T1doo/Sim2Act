"""Independent readback of author-run raw evidence; never invokes product or Worker."""
from pathlib import Path
import hashlib,json,subprocess,xml.etree.ElementTree as ET
BASE=Path('/workspace/local-record-state-evidence-20261018');OUT=Path(__file__).parent;REPO=Path('/workspace/Sim2Act')
FREEZE='d5eadc708ee2968bb574ec66e335c05451f66cf7'
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def fp(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
def load(p):return json.loads(p.read_text())
checks=[]
def check(v,label):
 assert v,label
 checks.append(label)
prod=load(OUT/'final-source-manifest.json')['files']
result={'classification':'NON_AUTHOR_RAW_EVIDENCE_READBACK_NOT_AUTHOR_QUALIFICATION_EXECUTION','freeze':FREEZE,'batches':{},'ui':[]}
for batch, basename in (('backend','backend-d5eadc70'),('ui','ui-d5eadc70'),('shared_completed_before_stop','shared-d5eadc70'),('shared_bounded','shared-bounded-final')):
 path=BASE/(basename+'.xml')
 if not path.exists():result['batches'][batch]={'status':'PENDING'};continue
 suite=next(ET.parse(path).getroot().iter('testsuite'));a=suite.attrib
 check(a['failures']==a['errors']==a['skipped']=='0',batch+' XML zero failures/errors/skips')
 named=[t.attrib['name'] for t in suite.iter('testcase') if 'name' in t.attrib]
 check(len(named)==int(a['tests']),batch+' named completed XML count exact')
 result['batches'][batch]={'completed_tests':int(a['tests']),'seconds':float(a['time']),'names':named}
 if batch=='shared_completed_before_stop':
  stop=load(BASE/'shared-bounded-stop.json');log=(BASE/'shared-d5eadc70.log').read_text()
  check('KeyboardInterrupt' in log and int(a['tests'])==2 and stop['action']=='SIGINT sole owned pytest process','original shared batch intentionally interrupted after exactly 2 completed positives')
  result['batches'][batch].update(full_batch_status='INTENTIONALLY_INTERRUPTED_NOT_ALL_GREEN',uncompleted_case='tests/test_pa_natural_spec_ui.py::test_natural_spec_page_actual_nodes_and_cold_material[valid]',uncompleted_case_status='NOT_VERIFIED',stop_elapsed_seconds=stop['elapsed_seconds'],pytest_total_seconds=float(a['time']),trailing_unnamed_xml_placeholder_count=len(list(suite.iter('testcase')))-len(named))
for p in sorted((BASE/'backend-d5eadc70').glob('*/local-record-proof.json')):
 if p.parent.name.endswith('current'):continue
 d=load(p);check(d['real_model_requests']==0,p.parent.name+' model0')
 if 'blocked' in d:
  check(d['blocked']==[] and d['full_binding_reads']==[],p.parent.name+' no historical private/body barrier violations')
for p in sorted((BASE/'ui-d5eadc70').glob('*/run-summary.json')):
 if p.parent.name.endswith('current'):continue
 d=load(p);page=load(p.parent/'page-result.json');check(d['status']=='PASS' and page['status']=='PASS' and d['real_model_requests']==0,p.parent.name+' actual page result PASS/model0')
 before=load(p.parent/'source-before.json');after=load(p.parent/'source-after.json');changes=load(p.parent/'source-changes.json')
 check(before==after and changes=={},p.parent.name+' source before/after unchanged')
 compared_prod=0;test_count=0
 for name,meta in before.items():
  if name in prod:
   check(meta=={'bytes':prod[name]['bytes'],'sha256':prod[name]['sha256']},p.parent.name+' frozen source '+name);compared_prod+=1
  else:
   check(name.startswith('tests/'),p.parent.name+' only test extra input '+name);test_count+=1
 check(compared_prod==130 and test_count==2 and len(prod)==132,p.parent.name+' source count 130 production plus 2 tests; full Git bridge separately includes 2 JSON anchors')
 for asset in page['static_resource_loads']:
  name='src/sim2act/web/'+(asset['path'].lstrip('/') or 'index.html')
  check(asset['status']==200 and asset['sha256']==prod[name]['sha256'],p.parent.name+' served frozen asset '+asset['path'])
 result['ui'].append({'scenario':d['scenario'],'checks':len(page['checks']),'page_http_actions':len(page['actions']),'served_assets':len(page['static_resource_loads']),'page_worker_calls':d['page_worker_calls'],'fixture_worker_calls':d['fixture_worker_calls'],'source_production_count':compared_prod,'source_test_count':test_count})
 if d['scenario']=='revocation':
  r=load(p.parent/'actual-revocation-proof.json');check(r['only_exact_known_grant_changed'] and r['all_other_rows_unchanged'] and r['original_run_rows_unchanged'] and r['page_worker_calls']==r['page_post_count']==0,'revocation exact fixture grant only, original Run unchanged, no page POST/Worker')
flow=load(BASE/'ui-d5eadc70/test_local_record_page_explici0/actual-page-delivery.json');cur=flow['current'];saved=flow['exact_saved_rows']
check(cur['data_version']==3 and len(cur['history'])==3 and len(cur['records'])==2,'page actual collection version3, 3 immutable events and 2 independent records')
fold={};prev=None
for n,h in enumerate(cur['history'],1):
 e=h['event'];check(h['version']==e['collection_version']==n and fp(e)==h['event_fingerprint']==h['artifact']['hash'] and e['previous_collection_fingerprint']==prev,'event '+str(n)+' exact canonical hash and collection chain')
 old=fold.get(e['record_id'])
 if e['kind']=='CREATE':check(old is None and e['record_revision']==1 and e['state']=='OPEN' and e['previous_event_fingerprint'] is None,'event '+str(n)+' genuine CREATE identity')
 else:check(e['kind']=='SET_STATE' and old and old['state']=='OPEN' and e['state']=='DONE' and e['record_revision']==old['record_revision']+1 and e['previous_event_fingerprint']==old['last_event_fingerprint'] and e['title']==old['title'] and e['details']==old['details'] and e['reason'].strip(),'event '+str(n)+' same-record OPEN to DONE revision and preserved fields')
 fold[e['record_id']]={k:e[k] for k in ('record_id','record_revision','title','details','state')}|{'last_event_fingerprint':fp(e)};prev=fp(e)
 resource=next(r for r in saved['resources'] if r['id']==h['artifact']['resource_id']);op=next(o for o in saved['operations'] if o['run_id']==h['run_id']);intent=next(x for x in saved['operation_intents'] if x['operation_id']==op['id']);effect=next(x for x in saved['local_effects'] if x['operation_id']==op['id']);typed=next(x for x in saved['internal_instance_data'] if x['version']==n);ar=next(x for x in saved['internal_app_runs'] if x['id']==h['app_run_id']);run=next(x for x in saved['runs'] if x['id']==h['run_id'])
 check(resource['format']=='json' and resource['content']==canonical(e) and hashlib.sha256(resource['content'].encode()).hexdigest()==resource['hash']==h['artifact']['hash'],'event '+str(n)+' actual JSON bytes/hash')
 check(op['tool_ref']=='artifact.save_text' and op['call_id']=='record_event' and op['status']=='VERIFIED' and op['receipt']['data']==h['artifact'] and intent['request']=={'tool':'artifact.save_text','args':{'text':canonical(e)}} and effect['resource_id']==resource['id'] and effect['content_hash']==resource['hash'],'event '+str(n)+' original save Operation/intent/receipt/effect')
 check(typed['data']=={'result':h['artifact'],'release_ref':cur['release_id']} and typed['run_id']==ar['id'] and typed['fingerprint']==fp(typed['data']) and ar['status']==run['status']=='SUCCEEDED' and ar['result_version']==n and ar['output']==h['artifact'] and run['result']['event_fingerprint']==fp(e),'event '+str(n)+' typed/AppRun/Run exact result')
check(sorted(fold.values(),key=lambda x:x['record_id'])==sorted(cur['records'],key=lambda x:x['record_id']),'independently recomputed current record projection')
check(sorted((r['state'],r['record_revision']) for r in cur['records'])==[('DONE',2),('OPEN',1)],'independent record states DONE2/OPEN1')
check(len(saved['grants'])==len(flow['derived_read_grants'])==6 and all(g['tool_ref']=='resource.read' and not g['revoked'] for g in saved['grants']),'exact 3 events each 2 existing-helper derived read grants; no write grant in saved effect rows')
owner=load(BASE/'shared-bounded-final/test_exact_goal_result_explici0/proof.json')
check(owner['receipt']['record']['status']==owner['state']['latest']['status']==owner['state']['owner_acceptance']=='ACCEPTED' and owner['receipt']['record']['run_id']==owner['state']['run_id']==owner['artifact']['run_id'],'bounded legacy natural PA exact same Run explicit owner acceptance')
csv=load(BASE/'shared-bounded-final/test_complete_md_internal_rele0/complete-delivery.json')
check(csv['first']['status']==csv['second']['status']=='SUCCEEDED' and csv['first']['id']!=csv['second']['id'],'bounded legacy complete CSV report two distinct successful Runs')
text_owner=load(BASE/'shared-d5eadc70/test_actual_two_inputs_same_in0/text-owner-proof.json')
check(text_owner['actual_complete_runs']==2 and text_owner['real_model_requests']==0 and text_owner['owner_history_preserved'] and text_owner['source_grants_unchanged'] and text_owner['no_additional_product_writes_from_declarations'],'completed legacy text-owner two actual Runs preserve owner history and source grants')
result['assertions']=len(checks);result['status']='PASS' if all(v.get('status')!='PENDING' for v in result['batches'].values()) else 'PARTIAL_BOUNDED_SHARED_PENDING';result['checks']=checks
(OUT/'final-raw-evidence-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='checks'},ensure_ascii=False,indent=2))
