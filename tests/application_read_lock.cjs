'use strict';
// Actual controller, deferred synthetic reads; no HTTP, business command or model.
const fs=require('node:fs'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const dom=new JSDOM(fs.readFileSync('src/sim2act/web/index.html','utf8'),{runScripts:'dangerously'}),w=dom.window,d=w.document,checks=[],requests=[],held=[];
w.$=id=>d.getElementById(id);w.safe=fn=>fn;
const install=text=>{const s=d.createElement('script');s.textContent=text;d.body.append(s);};
install(`let token='actor-a',identityConnectionGeneration=1,workspaceSelectionGeneration=1;`);
d.getElementById('project-select').append(new w.Option('project','project-a'));d.getElementById('project-select').value='project-a';
install(fs.readFileSync(process.argv[2]||'src/sim2act/web/use.js','utf8'));
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
const make=()=>w.eval(`applicationUse={id:'instance-a',appId:'app-a',identity:token,project:'project-a',generation:applicationUseGeneration,readGeneration:0,busy:false,selected:null};applicationUse`);
const controls=()=>['use-refresh','use-submit','use-column','use-recover'].every(id=>d.getElementById(id).disabled);
const start=view=>{w.testView=view;const promise=w.eval('readApplicationUse(testView)');promise.catch(()=>{});return promise;};
w.api=(path,method='GET')=>{requests.push({path,method});return new Promise((resolve,reject)=>held.push({resolve,reject}));};
const watchdog=setTimeout(()=>{console.error('Test exceeded five-second local deadline');process.exit(1);},5000);
(async()=>{try{
 const view=make();w.testView=view;
 w.eval(`applicationUseRequests.set(applicationUseKey(testView),{state:'unknown',body:{request_key:'original-key',input:{column:'amount'}},runId:null,uncertain:true});applicationUseButtons(testView);`);
 const intent=w.eval('JSON.stringify(applicationUseRequests.get(applicationUseKey(testView)))');
 check(!d.getElementById('use-recover').disabled,'original unknown intent has explicit recovery before read');
 const first=start(view);
 check(controls(),'all original controls including same-key recovery lock during read');
 w.eval('applicationUseButtons(testView)');
 check(controls(),'nested button reconciliation cannot release a pending read');
 await w.eval('submitApplicationUse(testView,true)');await d.getElementById('use-refresh').onclick();
 check(requests.length===1&&w.eval('JSON.stringify(applicationUseRequests.get(applicationUseKey(testView)))')===intent,'direct recovery/refresh handlers do not send or mutate original intent during read');
 const second=start(view);held[0].reject(Error('older read failed'));await first;
 check(controls(),'older read completion cannot release the newer read lock');
 held[1].reject(Error('current read denied'));await assert.rejects(second,/current read denied/);
 check(!d.getElementById('use-recover').disabled&&!d.getElementById('use-refresh').disabled&&d.getElementById('use-submit').disabled,'current failure releases recovery and read only, preserving UNKNOWN submit lock');
 check(w.eval('JSON.stringify(applicationUseRequests.get(applicationUseKey(testView)))')===intent&&d.getElementById('use-output').textContent==='','failure preserves exact intent and clears protected result');

 w.eval('applicationUseRequests.clear()');const ready=make();
 w.row=text=>{const e=d.createElement('div');e.textContent=text;return e;};w.renderApplicationAcceptance=()=>{};
 const success=start(ready);
 held[2].resolve({id:'instance-a',project_id:'project-a',source_app_id:'app-a',formal_publication_enabled:false,release_id:'release-a',release_fingerprint:'fingerprint',principal_id:'principal-a',runs:[],data:[]});await new Promise(setImmediate);
 held[3].resolve({id:'release-a',project_id:'project-a',fingerprint:'fingerprint',snapshot:{draft:{id:'app-a',fingerprint:'draft-fingerprint',candidate:{manifest:{data_bindings:[{resource_ref:'resource-a'}]}}}}});await new Promise(setImmediate);
 held[4].resolve({id:'app-a',project_id:'project-a',name:'Synthetic app',fingerprint:'draft-fingerprint',candidate:{manifest:{validation_suite_ref:'receipt.readback.v1'},actions:[{executor:{kind:'registered_tool',ref:'data.aggregate_csv'}}]},input_guidance:{columns:[{name:'amount',numeric:true}]}});await success;
 check(!d.getElementById('use-refresh').disabled&&!d.getElementById('use-submit').disabled&&!d.getElementById('use-column').disabled,'complete current success restores original ready controls');

 const old=start(ready);w.eval("clearApplicationUse();token='actor-b';identityConnectionGeneration++;");const fresh=make(),newRead=start(fresh);
 held[5].reject(Error('late old actor'));await old;
 check(controls()&&d.getElementById('use-info').dataset.readState==='loading','old actor return cannot unlock or repaint current actor pending view');
 held[6].reject(Error('new actor denied'));await assert.rejects(newRead,/new actor denied/);
 check(!d.getElementById('use-refresh').disabled&&d.getElementById('use-info').dataset.readState==='error','new actor owns its own failure release');
 install(fs.readFileSync(process.argv[3]||'src/sim2act/web/csv-owner.js','utf8'));
 w.safe=fn=>()=>{w.resumed=fn();w.resumed.catch(()=>{});return w.resumed;};
 for(const finishAway of [true,false]){
  const view=make(),offset=held.length,oldRead=start(view);w.eval('workspaceSelectionGeneration++');
  if(finishAway){held[offset].reject(Error('read finished away'));await oldRead;check(!view.reading,'invalidated read releases only its own object lock without repaint');}
  w.eval('workspaceSelectionGeneration++;resumeCsvOwnerReview()');const resumed=w.resumed;
  check(held.length===offset+2&&controls(),'return with no selected Run starts fresh GET and locks controls');
  if(!finishAway){held[offset].reject(Error('late away read'));await oldRead;check(controls()&&!!view.reading,'old workspace completion cannot release replacement read');}
  held[offset+1].reject(Error('fresh return denied'));await assert.rejects(resumed,/fresh return denied/);
  check(!view.reading&&!d.getElementById('use-refresh').disabled&&d.getElementById('use-info').dataset.readState==='error','fresh workspace failure leaves explicit read-only recovery reachable');
 }
 check(requests.length===11&&requests.every(r=>r.method==='GET'),'eleven finite synthetic adapter GETs, zero POST and no background timer retry');
 console.log(JSON.stringify({status:'PASS',scope:'actual controller / JSDOM deferred reads, not native rendering',checks,requests,actual_http:0,models:0},null,2));
}finally{clearTimeout(watchdog);for(const item of held)item.reject(Error('test cleanup'));dom.window.close();}})().catch(e=>{console.error(e.stack);process.exitCode=1;});
