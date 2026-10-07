import copy,json
from probe import candidate,m,versions,ids,ctx,ROOT,request
from sim2act.delivery_graph import derive_manifest_graph,plan_change
from sim2act.contracts import Limits
context=copy.deepcopy(ctx);context['graph_fingerprint']=None
context['unknown_dependencies']=[{'node_id':ids['action:report'],'scope':'PROJECT','reason':'Independent synthetic unknown query membership'}]
graph=derive_manifest_graph(m,candidate['actions'],versions,ids,context,Limits(**m['runtime_limits']));context['graph_fingerprint']=graph['graph_fingerprint']
view=next(n for n in graph['nodes'] if n['key']=='view:text:decision');req=copy.deepcopy(request);req['changes'][0]['expected_content_fingerprint']=view['content_fingerprint']
result=plan_change(graph,graph['graph_fingerprint'],req,context)
assert result['revalidation_scope']=='PROJECT'
assert set(result['revalidation_nodes'])=={n['id'] for n in graph['nodes']}
assert not result['patch_executed'] and not result['publishable']
(ROOT/'project-scope-result.json').write_text(json.dumps({'result':'PASS_SCOPE_SIGNAL_ONLY','scope':result['revalidation_scope'],'returned_nodes':len(result['revalidation_nodes']),'contains_other_project_app_nodes':False,'consumer_must_enumerate_authorized_other_apps':True},indent=2))
