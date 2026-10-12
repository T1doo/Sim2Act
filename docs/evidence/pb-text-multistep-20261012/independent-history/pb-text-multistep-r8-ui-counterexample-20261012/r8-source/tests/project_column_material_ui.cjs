'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),readline=require('node:readline'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),checks=[],requests=[],hashes={},pending=new Map();let serial=0,dom,w,$,mode='',resume=null;
readline.createInterface({input:process.stdin}).on('line',line=>{const r=JSON.parse(line),fn=pending.get(r.id);pending.delete(r.id);fn(r);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+'\n');});
const check=(value,label)=>{assert(value,label);checks.push(label);};
const wait=async fn=>{const end=Date.now()+15000;while(Date.now()<end){if(fn())return;await new Promise(r=>setTimeout(r,5));}throw Error('offline bounded wait');};
async function boot(app){if(dom)dom.window.close();const html=(await rpc({path:'/',method:'GET'})).text;hashes['index.html']=crypto.createHash('sha256').update(html).digest('hex');dom=new JSDOM(html,{url:'http://offline.test/',runScripts:'dangerously'});w=dom.window;$=id=>w.document.getElementById(id);w.TextEncoder=TextEncoder;Object.defineProperty(w.crypto,'subtle',{value:crypto.webcrypto.subtle});w.crypto.randomUUID=()=>crypto.randomUUID();w.setInterval=()=>0;
 w.fetch=async(url,options={})=>{const request={path:url,method:options.method||'GET',body:options.body&&JSON.parse(options.body),headers:options.headers};requests.push(request);const r=await rpc(request);if(mode==='lost'&&request.method==='POST'&&(url.endsWith('/material-plans')||url.endsWith('/csv-material-plans')||url.endsWith('/csv-logic-authorizations'))){mode='';assert.equal(r.status,201);throw Error('injected accepted response lost');}if(mode==='hold'&&request.method==='POST'&&url.endsWith('/material-plans')){mode='';await new Promise(resolve=>resume=resolve);}return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});};
 for(const script of [...w.document.querySelectorAll('script[src]')]){const name=script.getAttribute('src').slice(1),code=fs.readFileSync(path.join(info.web,name),'utf8');hashes[name]=crypto.createHash('sha256').update(code).digest('hex');const node=w.document.createElement('script');node.textContent=code;w.document.body.append(node);}
 $('token').value='synthetic-test-A';$('connect').click();await wait(()=>$('login').hidden&&$('project-select').value===info.project);if(app){await w.showApp(app);await w.readDeliveryGraph();await w.dagReuseHistory();}
}
const confirm=id=>{$(id).checked=true;$(id).dispatchEvent(new w.Event('change'));};
const posts=()=>requests.filter(r=>r.method==='POST').length;
(async()=>{try{
 await boot(info.app);$('dag-reuse-release').value=info.release;$('dag-reuse-release').dispatchEvent(new w.Event('change'));await w.dagReuseRead(w.eval('csvDagContext'),info.instance);
 check($('dag-reuse-column').value==='quantity','approved source overlay default remains quantity');
 const free=info.scenario!=='direct-lost';let saved;
 if(!free){
  check(!$('dag-material-options').disabled,'verified fixed family exposes finite new material entry');await $('dag-material-options').onclick();
  $('dag-material-target').value=info.target;$('dag-material-target').dispatchEvent(new w.Event('change'));
  check($('dag-material-column').value==='quantity'&&$('dag-material-column').options.length===1,'direct material freezes same approved column rather than first target column');
  check($('dag-material-plan').disabled,'material plan requires separate explicit confirmation');confirm('dag-material-confirm');mode='lost';await $('dag-material-plan').onclick();
  check(!$('dag-reuse-recover').hidden&&$('dag-material-plan').disabled,'lost accepted material response retains original intent');const n=posts();await $('dag-reuse-recover').onclick();check(posts()===n,'fixed material UNKNOWN recovery only original key GET');
  saved=JSON.parse($('dag-material-proof').textContent);check(saved.binding.column==='quantity'&&saved.plan.input.aggregate_column==='quantity','complete material receipt seals target default quantity');await $('dag-material-open').onclick();
 }else{
  confirm('csv-logic-authorize-confirm');if(info.scenario==='logic-mint-lost')mode='lost';await $('csv-logic-authorize').onclick();
  if(info.scenario==='logic-mint-lost'){check(!$('csv-logic-recover').hidden,'ambiguous authorization remains recoverable');const n=posts();await $('csv-logic-recover').onclick();check(posts()===n,'fixed logic authorization UNKNOWN reads exact original logic ID only');}
  const obj=JSON.parse($('csv-logic-proof').textContent),text=JSON.stringify(obj);
  check(obj.execution_version==='internal.project-csv-read-sum-report.v1'&&obj.recipe.nodes.length===3,'fixed family mints exact normalized three step logic');
  for(const forbidden of ['amount','quantity','column_overlay','default_column',info.old_resource])check(!text.includes(forbidden),'public logic excludes '+forbidden);
  await rpc({command:'retire'});const coldStart=requests.length;await boot(null);await $('csv-logic-history').onclick();check(requests.slice(coldStart).every(r=>r.method==='GET'),'cold logic registry restores without source app or mutation');
  check(!requests.slice(coldStart).some(r=>r.path.includes('/api/internal/releases/'+info.release)||r.path.includes('/api/resources/'+info.old_resource)),'cold logic registry never opens original Release or CSV');
  await $('csv-logic-options').onclick();$('csv-logic-target').value=info.target;$('csv-logic-target').dispatchEvent(new w.Event('change'));$('csv-logic-column').value='net';$('csv-logic-column').dispatchEvent(new w.Event('change'));confirm('csv-logic-confirm');
  if(info.scenario==='logic-late'){
   mode='hold';const action=$('csv-logic-plan').onclick();await wait(()=>resume);const finish=resume;w.clearApp();$('project-select').value=info.other;$('project-select').value=info.project;const n=requests.length;finish();await action;
   check(requests.length===n,'late target acceptance issues no old-context follow-up read');check(!$('csv-logic-proof').textContent,'project ABA cannot paint late target acceptance');const nposts=posts();await $('csv-logic-recover').onclick();check(posts()===nposts,'late known receipt recovery only original GET');
  }else{mode='lost';await $('csv-logic-plan').onclick();check(!$('csv-logic-recover').hidden,'ambiguous new target plan keeps exact original intent');const n=posts();await $('csv-logic-recover').onclick();check(posts()===n,'fixed logic target UNKNOWN recovery only original plan key GET');}
  saved=JSON.parse($('csv-logic-proof').textContent);check(saved.binding.column==='net'&&saved.plan.input.aggregate_column==='net','data free logic binds explicitly chosen target net');await $('csv-logic-open').onclick();
 }
 check($('csv-dag-run').disabled&&!$('csv-dag-confirm').checked,'opening new target requires separate execution consent');confirm('csv-dag-confirm');await $('csv-dag-run').onclick();await rpc({command:'worker'});await $('csv-dag-refresh').onclick();
 const actual=JSON.parse($('csv-dag-result').textContent),value=actual.result.output_by_step.report;
 check(actual.status==='SUCCEEDED'&&actual.steps.length===3&&value.resource_id===info.target_resource&&value.sum===(free?'8.75':'90'),'actual worker reads new target bytes and independent result');
 await $('dag-reuse-prepare').onclick();confirm('dag-reuse-confirm');await $('dag-reuse-commit').onclick();await $('dag-reuse-create').onclick();const iid=$('dag-reuse-instance').value;
 check(!!iid,'new target version and instance separately created');check($('dag-reuse-column').value===(free?'net':'quantity'),'new instance preserves proven target default despite different first numeric column');
 const n=posts();await boot(info.target);$('dag-reuse-instance').value=iid;await $('dag-reuse-read').onclick();check(posts()===n,'cold target version and instance read use GET only');check($('dag-reuse-column').value===(free?'net':'quantity'),'cold instance retains immutable target default');
 $('dag-reuse-column').value=free?'units':'amount';$('dag-reuse-column').dispatchEvent(new w.Event('change'));check($('dag-reuse-run').disabled,'unseen target input needs new explicit consent');confirm('dag-reuse-run-confirm');await $('dag-reuse-run').onclick();await rpc({command:'worker'});await $('dag-reuse-read').onclick();
 const detail=JSON.parse($('dag-reuse-proof').textContent).instance;check(detail.data_version===1&&detail.data[0].data.result.sum===(free?'13':'8.75'),'cold unseen target column writes its own actual result');check(detail.runs[0].run_id!==actual.id,'new instance Run is distinct from successful target source Run');
 fs.writeFileSync(info.output,JSON.stringify({status:'PASS',checks,requests,loaded_source_sha256:hashes,source_release:info.release,new_plan:saved,new_instance:detail},null,2));dom.window.close();process.stdout.write(JSON.stringify({done:true})+'\n');process.exit(0);
 }catch(error){fs.writeFileSync(info.output,JSON.stringify({status:'FAIL',checks,requests,text:dom?.window.document.body.textContent},null,2));dom?.window.close();process.stderr.write(error.stack+'\n');process.exit(1);}})();
