import sys,json,copy,hashlib
from pathlib import Path
ROOT=Path('/tmp/delivery-graph-core-final-independent/source');sys.path.insert(0,str(ROOT/'src'))
from sim2act.apps import csv_candidate
from sim2act.contracts import Limits
from sim2act.delivery_graph import derive_manifest_graph,plan_change
from sim2act.errors import DomainError
import sim2act.delivery_graph as module
OUT=ROOT.parent
def fp(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def args(candidate):
 m=candidate['manifest'];ext={'goal:'+m['goal_ref']}
 ext|={'source:'+d['ref'] for d in m['dependency_lock'] if d['kind']=='resource'}
 ext|={'rule:'+d['kind']+':'+d['ref'] for d in m['dependency_lock'] if d['kind']!='resource'}
 ext|={'check:'+d['ref'] for d in m['dependency_lock'] if d['kind']=='check'}
 keys=ext|{'action:'+s['step_id'] for s in m['workflow']}|{'artifact:'+f for f in m['outputs']}|{'view:'+v['component_ref']+':'+v['output_field'] for v in m['views']}|{'manifest:'+m['app_id']}
 versions={k:{'revision':1,'content_fingerprint':fp({'trusted_synthetic_external':k})} for k in sorted(ext)}
 ids={k:'dg_'+format(i+1,'032x') for i,k in enumerate(sorted(keys))}
 ctx={'project_id':'proj_'+'1'*32,'app_id':m['app_id'],'authorization_revision':1,'authorized':True,'resource_ids':sorted(d['ref'] for d in m['dependency_lock'] if d['kind']=='resource'),'node_revisions':dict.fromkeys(sorted(keys),1),'locked_nodes':[],'source_versions':copy.deepcopy(versions),'dependency_edges':[],'unknown_dependencies':[]}
 return versions,ids,ctx
report_fixture=json.loads((ROOT/'docs/evidence/report-delivery-graph-adapter-preparation-20261007/canonical-report-fixture.json').read_text())
caps=Limits(max_requests=1,max_tools=1,max_repairs=0,max_total_tokens=1024,max_output_tokens=1024,run_seconds=30)
csv=csv_candidate('res_'+'b'*32,'f'*64,'independent finite CSV compatibility',caps)
results=[]
for kind,candidate,limits in [('CSV',csv,caps),('Report',report_fixture['candidate'],Limits(**report_fixture['platform_limits']))]:
 versions,ids,ctx=args(candidate);input_before=fp([candidate,versions,ids,ctx,limits.model_dump()])
 graph=derive_manifest_graph(candidate['manifest'],candidate['actions'],versions,ids,ctx,limits)
 assert input_before==fp([candidate,versions,ids,ctx,limits.model_dump()]);results.append({'family':kind,'case':'legal_integer_versions','decision':'PASS','nodes':len(graph['nodes']),'edges':len(graph['edges']),'all_inputs_immutable':True})
 key=next(k for k in versions if k.startswith('source:'))
 for value,expected in [(True,'INVALID_MANIFEST'),(1.0,'INVALID_MANIFEST'),(2,'VERSION_CONFLICT')]:
  changed=copy.deepcopy(versions);changed[key]['revision']=value;before=fp([candidate,changed,ids,ctx,limits.model_dump()])
  try:derive_manifest_graph(candidate['manifest'],candidate['actions'],changed,ids,ctx,limits);raise AssertionError((kind,type(value).__name__,'unexpected accept'))
  except DomainError as e:assert e.code==expected,(kind,type(value).__name__,e.code);code=e.code
  assert before==fp([candidate,changed,ids,ctx,limits.model_dump()]);results.append({'family':kind,'case':'raw_source_revision','value':value,'type':type(value).__name__,'decision':'REJECTED','code':code,'all_inputs_immutable':True})
 current=copy.deepcopy(ctx);current['graph_fingerprint']=graph['graph_fingerprint'];node=next(n for n in graph['nodes'] if n['kind']=='SOURCE');request={'project_id':ctx['project_id'],'app_id':ctx['app_id'],'request_key':'independent-legal-plan','changes':[{'node_id':node['id'],'expected_revision':node['revision'],'expected_content_fingerprint':node['content_fingerprint']}]}
 before=fp([graph,request,current]);receipt=plan_change(graph,graph['graph_fingerprint'],request,current);assert before==fp([graph,request,current]);assert receipt['patch_executed'] is False and receipt['business_write_performed'] is False;assert plan_change(graph,graph['graph_fingerprint'],request,current,receipt)==receipt
 results.append({'family':kind,'case':'legal_plan_and_saved_receipt_replay','decision':'PASS','scope':receipt['revalidation_scope'],'patch_executed':False,'business_write_performed':False,'all_inputs_immutable':True})
final={'source':'a62779342925866c8aebb8307721a66d1a7dd035','decision':'LIMITED_CORE_PASS','module_path':module.__file__,'module_sha256':hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest(),'cases':results,'bounds':'Pure CSV/Report finite declarations only; no DB, HTTP, scheduling, semantic acceptance, network, provider/Mock calls, identity, PG/full/CI/LIVE; prior9HTTP exact3f07 review retained'}
(OUT/'actual-result.json').write_text(json.dumps(final,indent=2));print(json.dumps(final,indent=2))
