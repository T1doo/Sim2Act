from pathlib import Path
root=Path('/workspace/Sim2Act');out=Path('/tmp/csv-continuous-upgrade-draft-20261017');out.mkdir(exist_ok=True)
def edit(path,fn):
 old=(root/path).read_text();new=fn(old);assert new!=old,path
 target=out/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(new)
api='''@controlled
def derive_receipt(store, user, pid, aid, key, limits):
    """Only the exact accepted derive, after current authority and graph checks."""
    with store.tx() as c:
        saved = current(store,c,user,pid,aid,limits)
        row = lookup(c,user,aid,"derive",key)
        if row is None:
            conflict("Original derive receipt is not available")
        body,answer = checked_request(row)
        expected = {**metadata(saved),"graph":saved["graph"],"source_versions":saved["source_versions"]}
        if (body.request_key != key or body.expected_candidate_fingerprint != saved["candidate_fingerprint"]
                or fingerprint(answer) != fingerprint(expected)):
            conflict("Original derive receipt no longer matches the current graph")
        return dict(namespace="delivery-graph-derive-request.v1",principal_id=user,project_id=pid,app_id=aid,
            request_key=key,request=body.model_dump(),request_fingerprint=fingerprint(body.model_dump()),response=answer)


'''
edit('src/sim2act/delivery_graph_apps.py',lambda s:s.replace('@controlled\ndef history(',api+'@controlled\ndef history(').replace('    @app.post(base + "/plans", status_code=201)', '    @app.get(base + "/derive-requests/{key}")\n    def read_derive(pid: str, aid: str, key: str, user=dependency):\n        return derive_receipt(store,user,pid,aid,key,limits)\n\n    @app.post(base + "/plans", status_code=201)'))
old='''  // This explicit action saves a missing/stale graph with the existing bounded
  // derive controller. Its deterministic key also handles a lost derive reply.
  if(!entry.baselineAccepted){
   if(currentRelease){/* The current graph is checked by context GET. Reading a continuation must not derive a new anchor and invalidate its parent. */}
   else if(entry.baselineUnknown){const saved=await api(graphPath);if(!here())return;if(saved.derivation_key!==entry.baselineKey)throw Error("原图锚回执尚未确认");}
   else{entry.baselineUnknown=true;await api(graphPath+"/derive","POST",{request_key:entry.baselineKey,expected_candidate_fingerprint:v.app.fingerprint});if(!here())return;}
   entry.baselineAccepted=true;entry.baselineUnknown=false;
  }
'''
new='''  // This explicit action reuses the existing derive only for its exact stale
  // baseline conflict. A current parent anchor is read without mutation.
  if(!entry.baselineAccepted){
   let derive=!currentRelease||!!entry.steps.baseline;
   if(currentRelease&&!entry.steps.baseline){
    try{await api(graphPath);if(!here())return;}
    catch(error){if(!here())return;if(error.httpStatus!==409||error.message!=="VERSION_CONFLICT"||error.detail!=="Current graph baseline changed; explicitly derive a new anchor")throw error;derive=true;}
   }
   if(derive){
    const body=entry.steps.baseline?.body||{request_key:entry.baselineKey,expected_candidate_fingerprint:v.app.fingerprint};
    await request("baseline",graphPath+"/derive",body,graphPath+`/derive-requests/${entry.baselineKey}`,async(saved,b,hint)=>{
     const value=saved.response;
     if(saved.namespace!=="delivery-graph-derive-request.v1"||saved.principal_id!==v.principal||saved.project_id!==v.project||saved.app_id!==v.appId||saved.request_key!==entry.baselineKey||!same(saved.request,b)||saved.request_fingerprint!==await ownerHash(b)||value?.app_id!==v.appId||value.project_id!==v.project||value.runtime_id!==v.instance.runtime_id||value.candidate_fingerprint!==v.app.fingerprint)throw Error("原图锚回执尚未确认");
     if(hint){const {cached,...accepted}=hint;if(!same(value,accepted))throw Error("原图锚接受回执不匹配");}
     return value;
    },()=>{entry.baselineAccepted=true;});
    if(!here())return;
   }else entry.baselineAccepted=true;
  }
'''
edit('src/sim2act/web/csv-goal-revision.js',lambda s:s.replace(old,new).replace('const actions={preview:save,check,version:prepare,commit,adopt:adoptPrepare,adoptCommit:adopt};','const actions={baseline:read,preview:save,check,version:prepare,commit,adopt:adoptPrepare,adoptCommit:adopt};'))
edit('tests/test_csv_column_revisions.py',lambda s:s.replace('def test_visible_current_effective_revision_and_fenced_recovery(env,tmp_path,case):','def test_visible_current_effective_revision_and_fenced_recovery(env,tmp_path,monkeypatch,case):').replace('    data,aid,base,current,path,old_value,v2,goal,second=adopted(env)\n    other=', '''    if case=="same-navigation":
        from sim2act import delivery_graph_apps as graph
        logical=graph.logical
        def prior_registry(*args,**kwargs):
            keys,external=logical(*args,**kwargs)
            for definition in external.values():
                if "registry_versions" in definition:
                    definition["registry_versions"]={name:"0"*64 for name in definition["registry_versions"]}
            return keys,external
        # A valid saved v2 under a synthetic prior software registry. Restore
        # current software before ordinary-page entry; no product file changes.
        with monkeypatch.context() as previous_software:
            previous_software.setattr(graph,"logical",prior_registry)
            data,aid,base,current,path,old_value,v2,goal,second=adopted(env)
    else:
        data,aid,base,current,path,old_value,v2,goal,second=adopted(env)
    other='''))
oldjs=" const before=requests.length;await action('csv-goal-baseline');\n check(!requests.slice(before).some(x=>x.method==='POST'),'continuation baseline GET does not derive or mutate root graph');"
newjs=""" const before=requests.length;
 if(info.case==='same-navigation'){
  const graphPath=`/api/projects/${info.project}/apps/${info.app}/delivery-graph`;
  hold=graphPath+'/derive';dropBaseline=true;const sending=action('csv-goal-baseline');
  await wait(()=>release,'actual upgraded baseline derive201 held',90000);await nav('resources');await nav('apps');
  await wait(()=>visible($('csv-goal-revision')),'return retains original baseline intent',60000);
  const done=release;release=null;done();await sending;
  await wait(()=>visible($('csv-goal-recover'))&&!$('csv-goal-recover').disabled,'lost baseline exposes original GET recovery',60000);
  const mark=requests.length;await action('csv-goal-recover');
  check(requests.slice(mark).every(x=>x.method==='GET'),'lost baseline201 recovers original key using GET only');
  const sent=requests.filter(x=>x.method==='POST'&&x.path===graphPath+'/derive');
  check(sent.length===1&&sent[0].status===201&&sent[0].delivery==='ACTUAL_DERIVE_201_LOST','explicit baseline derives stale software anchor exactly once');
  check(requests.slice(before).some(x=>x.path===graphPath&&x.status===409&&x.response.error.message==='Current graph baseline changed; explicitly derive a new anchor'),'only exact actual stale software baseline conflict enables derive');
  check(requests.slice(mark).some(x=>x.method==='GET'&&x.path===graphPath+'/derive-requests/'+sent[0].body.request_key&&x.status===200),'recovery reads exact accepted derive request key');
 }else{
  await action('csv-goal-baseline');
  check(!requests.slice(before).some(x=>x.method==='POST'),'current baseline GET does not derive or mutate root graph');
 }"""
edit('tests/csv_column_revision.cjs',lambda s:s.replace('dropRelease=false,hold=null','dropRelease=false,dropBaseline=false,hold=null').replace("  if(dropRelease&&request.method", "  if(dropBaseline&&request.method==='POST'&&path.endsWith('/delivery-graph/derive')){dropBaseline=false;assert.equal(r.status,201);request.delivery='ACTUAL_DERIVE_201_LOST';throw Error('synthetic lost baseline derive response');}\n  if(dropRelease&&request.method").replace(oldjs,newjs))
print(out)
