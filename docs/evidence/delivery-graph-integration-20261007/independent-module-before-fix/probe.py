import copy,json,hashlib
from pathlib import Path
from sim2act.delivery_graph import derive_manifest_graph,plan_change
from sim2act.contracts import Limits
from sim2act.errors import DomainError
ROOT=Path('/tmp/delivery-graph-integration-independent');REPO=Path('/workspace/Sim2Act-delivery-graph-integration')
f=json.loads((REPO/'docs/evidence/report-delivery-graph-adapter-preparation-20261007/canonical-report-fixture.json').read_text());candidate=f['candidate'];m=candidate['manifest']
external={'goal:'+m['goal_ref']}
external|={'source:'+d['ref'] for d in m['dependency_lock'] if d['kind']=='resource'}
external|={'rule:'+d['kind']+':'+d['ref'] for d in m['dependency_lock'] if d['kind']!='resource'}
external|={'check:'+m['validation_suite_ref']}
keys=external|{'action:report','view:text:decision','manifest:'+m['app_id']}|{'artifact:'+k for k in m['outputs']}
versions={key:{'revision':1,'content_fingerprint':hashlib.sha256(key.encode()).hexdigest()} for key in external}
ids={key:'dg_'+format(i+1,'032x') for i,key in enumerate(sorted(keys))}
ctx={'project_id':f['adapter_context']['project_id'],'app_id':m['app_id'],'authorization_revision':7,'authorized':True,'resource_ids':f['adapter_context']['current_authorized_resource_refs'],'node_revisions':dict.fromkeys(keys,1),'locked_nodes':[],'source_versions':versions,'dependency_edges':[],'unknown_dependencies':[]}
graph=derive_manifest_graph(m,candidate['actions'],versions,ids,ctx,Limits(**m['runtime_limits']));ctx['graph_fingerprint']=graph['graph_fingerprint']
node=next(n for n in graph['nodes'] if n['key']=='view:text:decision')
request={'request_key':'independent-view','project_id':ctx['project_id'],'app_id':ctx['app_id'],'changes':[{'node_id':node['id'],'expected_revision':1,'expected_content_fingerprint':node['content_fingerprint']}]}
receipt=plan_change(graph,graph['graph_fingerprint'],request,ctx)
results={'compatibility':'PASS','graph_nodes':len(graph['nodes']),'graph_edges':len(graph['edges']),'view_impact':[n['key'] for n in graph['nodes'] if n['id'] in receipt['revalidation_nodes']],'cases':[]}
for name,mutate in [('patch_bool_to_int',lambda r:r.update(patch_executed=0)),('retained_revision_int_to_bool',lambda r:r['retained_objects'][0].update(revision=True))]:
 bad=copy.deepcopy(receipt);mutate(bad)
 try:
  returned=plan_change(graph,graph['graph_fingerprint'],request,ctx,bad)
  result={'name':name,'result':'ACCEPTED_TAMPERED_STORED_RECEIPT','returned_original':returned==receipt}
 except DomainError as e:result={'name':name,'result':'REJECTED','code':e.code}
 results['cases'].append(result)
for name,mutate in [('authorization_revision',lambda c:c.update(authorization_revision=8)),('current_source_hash',lambda c:c['source_versions'][next(k for k in external if k.startswith('source:'))].update(content_fingerprint='0'*64)),('missing_saved_anchor',lambda c:c.update(graph_fingerprint=None))]:
 changed=copy.deepcopy(ctx);mutate(changed)
 try:plan_change(graph,graph['graph_fingerprint'],request,changed);result={'name':name,'result':'UNEXPECTED_ACCEPT'}
 except DomainError as e:result={'name':name,'result':'REJECTED','code':e.code}
 results['cases'].append(result)
(ROOT/'result.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
