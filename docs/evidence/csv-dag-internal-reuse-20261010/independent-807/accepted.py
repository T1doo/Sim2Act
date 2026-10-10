from common import *
import traceback
out=[]
for attack in ['delete-pair','strip-marker-pair']:
 folder=ROOT/('api-accepted-corrected-'+attack);e=env(folder);checks=[]
 try:
  aid,_,_,_,rel=make_release(e);i=make_instance(e,rel);a,_=enqueue(e,i,rel);work(e,a['run_id'])
  with e[0].tx() as c:
   rows=c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.kind.in_(['csv_dag_run','csv_dag_run_seal']))).mappings().all();rows=[r for r in rows if r['snapshot']['response'].get('run_id')==a['run_id']];assert len(rows)==2;checks.append('exact target accepted pair selected')
   for row in rows:
    match=[delivery_graph_requests.c.principal_id==row['principal_id'],delivery_graph_requests.c.app_id==row['app_id'],delivery_graph_requests.c.kind==row['kind'],delivery_graph_requests.c.request_key==row['request_key']]
    if attack=='delete-pair':c.execute(delete(delivery_graph_requests).where(*match))
    else:
     snap=copy.deepcopy(row['snapshot']);assert snap['response'].pop('internal_instance')['instance_id']==i['id'];c.execute(update(delivery_graph_requests).where(*match).values(snapshot=snap,fingerprint=fingerprint(snap)))
  before=fingerprint(snapshot(e));r=e[2].get('/api/internal/instances/'+i['id']);assert r.status_code==409,r.text;checks.append('both accepted independent marker rows removed or coherently stripped rejected');assert fingerprint(snapshot(e))==before;checks.append('read rejection no durable mutation');out.append({'case':attack,'status':'PASS','checks':checks})
 except Exception:
  err=traceback.format_exc();(folder/'failure.log').write_text(err);out.append({'case':attack,'status':'FAIL','checks':checks,'error':err});print(err)
 finally:(folder/'database-evidence.json').write_text(json.dumps(snapshot(e),indent=2,default=str));e[2].close();e[0].engine.dispose()
 print(out[-1],flush=True)
(ROOT/'accepted-results.json').write_text(json.dumps(out,indent=2));freeze('accepted-after');assert all(r['status']=='PASS' for r in out)
