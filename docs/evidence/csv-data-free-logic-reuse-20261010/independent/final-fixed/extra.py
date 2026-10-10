from independent import *
start=len(checks)
for backend in ['sqlite','pg']:
 folder=ROOT/('extra-'+backend+'-corrected');e,schema=env(folder,backend);e.append(backend)
 try:
  src=release(e,True);obj,body=authorize(e,src)
  rid=req(e,'POST',f'/api/projects/{e[5]}/resources',{'name':'Explicitly new without rederive.csv','format':'csv','content':TARGET},201)['id'];app=req(e,'POST',f'/api/projects/{e[5]}/apps/csv-preview',{'name':'New app changes grant baseline','goal':'Valid new own target','resource_id':rid},201)
  denied(e,'registered-new-CSV-stale-source-no-late-mint','POST',f'/api/internal/releases/{src["release"]["id"]}/csv-logic-authorizations',{**body,'request_key':'late-after-new-registration'},403)
  ck(req(e,'GET',f'/api/internal/csv-logics/{obj["id"]}')==obj,'previously explicit authority survives new Grant baseline change')
  revoke={'expected_logic_fingerprint':obj['fingerprint'],'consent':'REVOKE_DATA_FREE_CSV_LOGIC','request_key':'irreversible-extra-revoke'};req(e,'POST',f'/api/internal/csv-logics/{obj["id"]}/revoke',revoke)
  with e[0].engine.begin() as c:c.execute(h.delete(h.delivery_graph_requests).where(h.delivery_graph_requests.c.kind.in_([logic.REVOKE,logic.REVOKE+'_seal']),h.delivery_graph_requests.c.request_key==obj['id']))
  g=req(e,'GET',f'/api/internal/csv-logics/{obj["id"]}');ck(g['status']=='REVOKED','consumed true remains irrevocably revoked when both revoke receipts stripped')
  denied(e,'revoke-receipts-stripped-consumed-still-deny','GET',f'/api/internal/csv-logics/{obj["id"]}/materials',expected=403)
  print(json.dumps({'backend':backend,'status':'PASS'}),flush=True)
 except Exception:
  (folder/'EXTRA_FAILURE.log').write_text(traceback.format_exc());raise
 finally:
  e[2].close()
  if schema:
   with e[0].engine.begin() as c:c.execute(text('DROP SCHEMA "'+schema+'" CASCADE'));assert c.execute(text('SELECT count(*) FROM pg_namespace WHERE nspname=:n'),{'n':schema}).scalar_one()==0
   (folder/'own-schema-cleanup.json').write_text(json.dumps({'schema':schema,'own_schema_absent':True,'parent_fixtures_untouched':True}))
  e[0].engine.dispose()
(ROOT/'EXTRA_RESULTS.json').write_text(json.dumps({'records':records,'checks':checks,'check_count':len(checks)},indent=2,ensure_ascii=False,default=str));freeze('final-after')
