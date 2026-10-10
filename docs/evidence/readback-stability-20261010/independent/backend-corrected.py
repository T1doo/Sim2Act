from common import *
results=[]
def ck(v,label,checks):assert v,label;checks.append(label)
for case in ['coherent-text','cross-definition','different-result-binding']:
 folder,store,settings,client,cfg=clone('api-corrected-'+case);checks=[];start=time.monotonic();pid,aid=cfg['project'],cfg['app']['id'];url=cfg['url'];sql=[]
 def audit(c,cur,statement,parameters,context,many):sql.append(statement)
 event.listen(store.engine,'before_cursor_execute',audit)
 try:
  if case in ['history-oracles','write-fresh-scope']:
   old_scope=presentation.scope;old_pure=presentation._readback_from_scope;scopes=[];pure=[];mark=[None]
   def fresh(*a,**kw):
    validated=old_scope(*a,**kw);entry={'body':a[5].model_dump(),'object':validated,'sql_after_scope':len(sql)};scopes.append(entry);mark[0]=entry;return validated
   def compute(body,patch,checkbody,validated):
    ck(mark[0]['object'] is validated,'pure uses immediate current definition scope',checks);ck(mark[0]['sql_after_scope']==len(sql),'no DB accesses between fresh scope and pure check',checks);n=len(sql);value=old_pure(body,patch,checkbody,validated);ck(len(sql)==n,'pure checker does zero SQL',checks);pure.append({'definition':body.request_key,'check':checkbody.request_key,'text':value['text'],'run':body.run_id});return value
   presentation.scope=fresh;presentation._readback_from_scope=compute
   try:
    if case=='history-oracles':
     before=fingerprint(state(store));scope_ids=[]
     for request_no in [1,2]:
      oldcount=len(scopes);pureold=len(pure);r=client.get(url);ck(r.status_code==200,'cold multidefinition history HTTP200 request'+str(request_no),checks);items=r.json()['items'];ck(len(items)==3,'three distinct definitions retained request'+str(request_no),checks)
      for item in items:
       name=item['patch']['request_key'];expected=cfg['expected'][name];got=item['checks'];ck([x['request_key'] for x in got]==expected['checks'],'exact matching check keys '+name,checks);ck(all(x['text']==expected['text'] and x['baseline_text']==expected['decision'] and x['result_binding']==item['patch']['result_binding'] and x['result_binding']['run_id']==expected['run_id'] for x in got),'actual independent output/binding oracle '+name,checks);ck(all(x['model_requests']==0 and x['business_writes']==0 and x['owner_acceptance']=='PENDING' and x['semantic_status']=='UNKNOWN' and x['overall_run_acceptance']=='NOT_ACCEPTED' for x in got),'conservative acceptance and zero effects '+name,checks)
      ck(len(scopes)-oldcount==3 and len(pure)-pureold==6,'one fresh scope per definition six pure matching checks',checks);scope_ids.extend(id(x['object']) for x in scopes[oldcount:]);ck(fingerprint(state(store))==before,'all DB tables cold history unchanged request'+str(request_no),checks)
     ck(len(set(scope_ids))==6,'no validated object reused across definition or HTTP requests',checks);ck(not any(s.lstrip().split()[0].upper() in ['INSERT','UPDATE','DELETE'] for s in sql),'history performs zero SQL writes',checks)
    else:
     before=state(store);r=client.post(url+'/independent-beta/checks',json={'expected_patch_fingerprint':cfg['patches']['beta']['patch_fingerprint'],'request_key':'independent-new-writer'});ck(r.status_code==201,'normal check write accepted',checks);ck(len(scopes)==2,'write check retains separate load and readback full fresh scopes',checks);ck(r.json()['text']==cfg['expected']['independent-beta']['text'],'write check uses actual second archived output',checks);after=state(store);ck(all(before[n]==after[n] for n in before if n!='delivery_graph_requests'),'check changes no canonical or other DB table',checks);ck(len(after['delivery_graph_requests'])-len(before['delivery_graph_requests'])==2,'check writes only exact independent two-row receipt pair',checks)
   finally:presentation.scope=old_scope;presentation._readback_from_scope=old_pure
   (folder/'scope-proof.json').write_text(json.dumps({'scopes':[{'body':r['body'],'sql_after_scope':r['sql_after_scope'],'output':r['object'][3]} for r in scopes],'pure':pure,'sql_count':len(sql)},indent=2))
  else:
   body=cfg['bodies']['alpha'];peer=cfg['peer']
   with store.tx() as c:
    if case in ['coherent-text','cross-definition','different-result-binding']:
     key='independent-alpha-1' if case!='cross-definition' else 'independent-beta-1'
     def forge(value):
      response=value['response']
      if case=='coherent-text':response['text']='自签双seal的伪造解释'
      elif case=='different-result-binding':response['result_binding']=cfg['patches']['beta']['result_binding']
      else:response['text']=cfg['expected']['independent-alpha']['text'];response['baseline_text']='ALLOW'
     mutate_pair(c,cfg,presentation.CHECK,key,forge)
    elif case=='definition-result-binding':mutate_pair(c,cfg,presentation.KIND,'independent-alpha',lambda value:value['response'].update(result_binding=cfg['patches']['beta']['result_binding']))
    elif case in ['source-bytes','peer-source']:
     rid=cfg['app']['candidate']['report_proof']['target_resource_id'] if case=='source-bytes' else peer['candidate']['manifest']['data_bindings'][0]['resource_ref'];row=c.execute(select(resources).where(resources.c.id==rid)).mappings().one();text=row['content']+'\nindependent changed source';c.execute(update(resources).where(resources.c.id==rid).values(content=text,hash=hashlib.sha256(text.encode()).hexdigest()))
    elif case in ['source-grant-revoked','source-grant-expired']:
     rid=cfg['app']['candidate']['report_proof']['source_resource_id'];changes={'revoked':True} if case.endswith('revoked') else {'expires_at':0};changed=c.execute(update(grants).where(grants.c.principal_id==cfg['owner'],grants.c.project_id==pid,grants.c.resource_id==rid).values(**changes));assert changed.rowcount>0
    elif case in ['run-version','run-fence','archived-owner']:
     values={'version':body['expected_run_version']+1} if case=='run-version' else {'fence':body['expected_run_fence']+1} if case=='run-fence' else {'principal_id':cfg['other']};c.execute(update(runs).where(runs.c.id==body['run_id']).values(**values))
   if case in ['report-lock','peer-lock']:
    target=aid if case=='report-lock' else peer['id'];r=client.get(f'/api/projects/{pid}/apps/{target}/delivery-graph');assert r.status_code==200,r.text;g=r.json();slot=next(n for n in g['graph']['nodes'] if n['kind']=='VIEW');graph.set_lock(store,cfg['owner'],pid,target,{'expected_graph_fingerprint':g['graph_fingerprint'],'request_key':'independent-current-lock','change':{'node_id':slot['id'],'expected_revision':slot['revision'],'expected_content_fingerprint':slot['content_fingerprint']},'locked':True},Limits(**{k:getattr(settings,k) for k in Limits.model_fields}))
   if case=='other-owner':client.headers['Authorization']='Bearer synthetic-test-B'
   if case=='other-project':
    other=store.project(cfg['owner'],'Independent other project');url=url.replace('/projects/'+pid+'/', '/projects/'+other+'/')
   before=fingerprint(state(store));n=len(sql);r=client.get(url);ck(r.status_code in [403,409],case+' cold history refused',checks);(folder/'history-response.json').write_text(json.dumps({'http':r.status_code,'body':r.json()},indent=2));ck(fingerprint(state(store))==before,'all DB tables unchanged on history denial',checks)
   r2=client.post(url+'/independent-'+('beta' if case=='cross-definition' else 'alpha')+'/checks',json={'expected_patch_fingerprint':cfg['patches']['beta' if case=='cross-definition' else 'alpha']['patch_fingerprint'],'request_key':key});ck(r2.status_code in [400,403,409],case+' write-side still refuses bad current scope/proof',checks);ck(fingerprint(state(store))==before,'write-side refusal no durable write',checks);(folder/'write-response.json').write_text(json.dumps({'http':r2.status_code,'body':r2.json()},indent=2));ck(not any(s.lstrip().split()[0].upper() in ['INSERT','UPDATE','DELETE'] for s in sql[n:]),'history/write refusal issue zero SQL mutations',checks)
  results.append({'case':case,'status':'PASS','checks':checks,'seconds':time.monotonic()-start})
 except Exception:
  err=traceback.format_exc();(folder/'failure.log').write_text(err);results.append({'case':case,'status':'FAIL','checks':checks,'error':err});print(err,flush=True)
 finally:
  event.remove(store.engine,'before_cursor_execute',audit);(folder/'database-evidence.json').write_text(json.dumps(state(store),indent=2,default=str));(folder/'sql.json').write_text(json.dumps(sql,indent=2));client.close();store.engine.dispose()
 print(case,results[-1]['status'],len(checks),flush=True)
(ROOT/'backend-corrected-results.json').write_text(json.dumps(results,indent=2));freeze('backend-corrected-after');assert all(r['status']=='PASS' for r in results)
