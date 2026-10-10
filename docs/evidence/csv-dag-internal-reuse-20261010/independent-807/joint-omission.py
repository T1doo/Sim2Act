from common import *
folder=ROOT/'api-joint-marker-join-omission';e=env(folder)
try:
 aid,_,_,_,rel=make_release(e);i=make_instance(e,rel);a,_=enqueue(e,i,rel);work(e,a['run_id'])
 with e[0].tx() as c:
  rows=c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.kind.in_(['csv_dag_run','csv_dag_run_seal']))).mappings().all()
  for row in rows:
   if row['snapshot']['response'].get('run_id')==a['run_id']:
    snap=copy.deepcopy(row['snapshot']);snap['response'].pop('internal_instance');c.execute(update(delivery_graph_requests).where(delivery_graph_requests.c.principal_id==row['principal_id'],delivery_graph_requests.c.app_id==row['app_id'],delivery_graph_requests.c.kind==row['kind'],delivery_graph_requests.c.request_key==row['request_key']).values(snapshot=snap,fingerprint=fingerprint(snap)))
  c.execute(delete(internal_instance_data).where(internal_instance_data.c.instance_id==i['id']));c.execute(delete(internal_run_bindings).where(internal_run_bindings.c.run_id==a['run_id']));c.execute(delete(internal_app_runs).where(internal_app_runs.c.id==a['app_run_id']));c.execute(update(internal_instances).where(internal_instances.c.id==i['id']).values(data_version=0))
 before=fingerprint(snapshot(e));r=e[2].get('/api/internal/instances/'+i['id']);out={'status':r.status_code,'body':r.json(),'unchanged':fingerprint(snapshot(e))==before,'target_run':a,'remaining_run':request(e,'GET','/api/runs/'+a['run_id'])};(folder/'result.json').write_text(json.dumps(out,indent=2,default=str));print(json.dumps({'status':r.status_code,'data_version':r.json().get('data_version'),'runs':len(r.json().get('runs',[])),'unchanged':out['unchanged']}));assert r.status_code==409,'joint markers + joins + data omission must refuse existing accepted actual DAG history'
finally:
 (folder/'database-evidence.json').write_text(json.dumps(snapshot(e),indent=2,default=str));e[2].close();e[0].engine.dispose()
