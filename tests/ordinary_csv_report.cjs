'use strict';
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),requests=[],checks=[],assets=[],blobs=[],observations=[],pending=new Map();let serial=0,dom,w,$,hold=null,release=null,drop=null;
readline.createInterface({input:process.stdin}).on('line',line=>{const r=JSON.parse(line),resolve=pending.get(r.id);assert(resolve);pending.delete(r.id);resolve(r);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+'\n');});
const wait=async(fn,label)=>{const until=Date.now()+12000;while(Date.now()<until){if(fn())return;await new Promise(r=>setTimeout(r,5));}throw Error('bounded wait: '+label);};
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
function visible(el){if(!el?.isConnected)return false;for(let p=el;p;p=p.parentElement)if(p.hidden||w.getComputedStyle(p).display==='none')return false;return true;}
async function action(el,type='click'){
 if(typeof el==='string')el=$(el);assert(visible(el));assert(!el.matches(':disabled'));const work=[],restore=[];
 for(const [node,name]of [[el,type==='change'?'onchange':'onclick'],[type==='click'?el.form:null,'onsubmit']]){const fn=node?.[name];if(typeof fn!=='function')continue;const wrap=function(e){const p=fn.call(this,e);work.push(Promise.resolve(p));return p;};node[name]=wrap;restore.push(()=>{if(node[name]===wrap)node[name]=fn;});}
 try{if(type==='click')el.click();else el.dispatchEvent(new w.Event(type,{bubbles:true}));await Promise.all(work);}finally{restore.forEach(fn=>fn());}
}
async function project(id){$('project-select').value=id;await action('project-select','change');}
async function boot(){
 const load=async path=>{const r=await rpc({method:'GET',path});assert.equal(r.status,200);assets.push({path,sha256:crypto.createHash('sha256').update(r.text).digest('hex')});return r.text;};
 dom=new JSDOM(await load('/'),{url:'http://testserver/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.setInterval=()=>0;w.Blob=Blob;
 w.URL.createObjectURL=blob=>{const url='blob:synthetic-'+blobs.length;blobs.push({url,blob,revoked:false});return url;};w.URL.revokeObjectURL=url=>{blobs.find(b=>b.url===url).revoked=true;};
 w.HTMLAnchorElement.prototype.click=function(){blobs.find(b=>b.url===this.href).filename=this.download;};
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{
  const request={method:options.method||'GET',path,body:options.body?JSON.parse(options.body):undefined};requests.push(request);
  const r=await rpc({...request,headers:options.headers});request.status=r.status;request.response=JSON.parse(r.text);
  if(drop&&drop===path&&request.method==='POST'){drop=null;request.controlled_delivery='actual accepted reply lost';throw Error('Synthetic lost response after actual acceptance');}
  if(hold?.path===path&&request.method===(hold.method||'GET')){hold=null;await new Promise(resolve=>{release=resolve;});}
  return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
 };
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(script.getAttribute('src'));w.document.body.append(node);}
 $('token').value='synthetic-test-A';await action('connect');await project(info.project);
 $('goal').value='独立自然语言草稿：不得被有限CSV合同覆盖';
 check(visible($('csv-report-task'))&&$('csv-report-prepare').disabled,'finite task is discoverable and cannot prepare without explicit material/column');
 $('csv-report-source').value=info.material;await action('csv-report-source','change');
 check([...$('csv-report-column').options].some(o=>o.value==='amount'),'columns come from actual authorized CSV read');
 $('csv-report-column').value='amount';await action('csv-report-column','change');
 await w.refresh();check($('csv-report-column').value==='amount'&&!$('csv-report-prepare').disabled,'ordinary background refresh preserves explicit column for unchanged authorized source version');
}
async function workspaceRoundtrip(){
 await action(w.document.querySelector('#workspace-nav [data-tab="resources"]'));
 await action(w.document.querySelector('#workspace-nav [data-tab="projects"]'));
}
function observeContract(stage){observations.push({stage,requests:requests.length,visible:visible($('csv-report-contract')),ackChecked:$('csv-report-ack')?.checked,confirmDisabled:$('csv-report-confirm')?.disabled,readVisible:visible($('csv-report-confirm-read')),proof:$('csv-report-proof')?.textContent,status:$('csv-report-confirm-status')?.textContent});}
async function staleControlsSendNothing(ack,button,label){
 const count=requests.length;ack.checked=true;await ack.onchange(new w.Event('change'));await button.onclick(new w.Event('click'));
 check(requests.length===count,label+' old detached controls send no requests');
}
async function prepareReturn(rid){
 if(!['workspace-unconfirmed','scope-project','scope-identity'].includes(info.case))return;
 const oldAck=$('csv-report-ack'),oldButton=$('csv-report-confirm'),oldSection=$('csv-report-contract');
 if(info.case==='workspace-unconfirmed'){
  const count=requests.length;await workspaceRoundtrip();observeContract('unconfirmed workspace return');
  check(requests.length===count,'visible workspace return does not automatically read, acknowledge or confirm');
  // Exercise the returned visible controls before checking identity: this is the actual zero-request red.
  $('csv-report-ack').checked=true;await action('csv-report-ack','change');
  if($('csv-report-confirm').disabled)$('csv-report-confirm').click();
  observeContract('returned visible acknowledgement attempted');
  check(!$('csv-report-confirm').disabled&&requests.slice(count).some(r=>r.method==='GET'&&r.path===`/api/runs/${rid}`),'returned visible acknowledgement freshly verifies the Run and enables explicit confirmation');
  check($('csv-report-contract')!==oldSection,'workspace return creates a new confirmation view');
 }else{
  $('csv-report-ack').checked=true;await action('csv-report-ack','change');
  check(!$('csv-report-confirm').disabled,'original view has an explicit acknowledgement before scope change');
  if(info.case==='scope-project'){await project(info.other);await project(info.project);}
  else{await action('identity-switch');$('token').value='synthetic-test-B';await action('connect');await action('identity-switch');$('token').value='synthetic-test-A';await action('connect');await project(info.project);}
  check(!$('csv-report-contract'),'scope change removes the old protected confirmation');
  await staleControlsSendNothing(oldAck,oldButton,'scope change');
  await action('csv-report-open');observeContract('explicitly reopened under new owner scope');
  check(!$('csv-report-ack').checked&&$('csv-report-confirm').disabled,'new identity/project scope cannot inherit a previous checked acknowledgement');
 }
 await staleControlsSendNothing(oldAck,oldButton,'workspace/current-scope replacement');
}
async function main(){
 await boot();const route=`/api/projects/${info.project}/csv-report-runs`;
 if(info.case==='lost')drop=route;
 const preparing=action('csv-report-prepare');await preparing;
 if(info.case==='lost'){
  check(!$('csv-report-recover').hidden&&$('csv-report-prepare').disabled,'lost accepted preparation stays unknown and locks changed submissions');
  await action('csv-report-recover');
  const attempts=requests.filter(r=>r.path===route&&r.method==='POST');check(attempts.length===2&&JSON.stringify(attempts[0].body)===JSON.stringify(attempts[1].body)&&attempts[0].response.run_id===attempts[1].response.run_id,'manual preparation recovery uses exact original input/key and one Run');
 }
 const rid=requests.find(r=>r.path===route&&r.method==='POST').response.run_id;
 check($('csv-report-contract')&&$('csv-report-proof').textContent.includes(rid)&&$('csv-report-proof').textContent.includes('source_hash')&&$('csv-report-proof').textContent.includes('csv_rule')&&$('csv-report-proof').textContent.includes('numeric_rule')&&$('csv-report-proof').textContent.includes('report_hash'),'same-Run read-only contract visibly freezes source/version/hash, column/numeric/count/report/save rules');
 check($('csv-report-preview').textContent.includes('记录数：2')&&$('csv-report-preview').textContent.includes('精确合计：4.00')&&$('csv-report-confirm').disabled,'complete MD preview requires a separate unchecked explicit confirmation');
 check($('goal').value==='独立自然语言草稿：不得被有限CSV合同覆盖','structured task does not interpret or replace arbitrary Goal draft');
 assert.equal((await rpc({command:'before',run:rid})).status,200);
 await prepareReturn(rid);
 const ackStart=requests.length;$('csv-report-ack').checked=true;await action('csv-report-ack','change');
 if(['scope-project','scope-identity'].includes(info.case))check(requests.slice(ackStart).some(r=>r.method==='GET'&&r.path===`/api/runs/${rid}`),'new explicit acknowledgement rechecks the exact complete Run contract');
 const confirmRoute=`/api/runs/${rid}/confirm-csv-report`;
 if(info.case==='lost')drop=confirmRoute;
 if(info.case!=='lost')hold={path:confirmRoute,method:'POST'};
 const confirming=action('csv-report-confirm');
 if(info.case!=='lost'){
  await wait(()=>!!release,'actual confirm receipt held');const count=requests.length;const old=$('csv-report-confirm');
  await old.onclick(new w.Event('click'));check(requests.length===count,'duplicate click while confirmation is in flight sends no second POST');
  if(info.case==='workspace-pending'){
   const oldAck=$('csv-report-ack'),oldButton=$('csv-report-confirm'),oldSection=$('csv-report-contract'),count=requests.length;
   await workspaceRoundtrip();observeContract('workspace return with actual accepted confirmation response held');
   check(requests.length===count,'pending workspace return sends no automatic GET or duplicate POST');
   check($('csv-report-contract')!==oldSection&&!$('csv-report-ack').checked&&$('csv-report-confirm').disabled,'pending return rebuilds an unchecked locked confirmation view');
   await staleControlsSendNothing(oldAck,oldButton,'pending workspace return');
   check(visible($('csv-report-confirm-read')),'new pending view offers explicit original-Run readback');
   await action('csv-report-confirm-read');observeContract('current view read actual already-confirmed Run');
   check(!$('csv-report-confirm')&&$('raw-result').textContent.includes('QUEUED'),'explicit readback recovers actual accepted Run without a second confirmation');
  }
  if(info.case==='navigation'){
   await project(info.other);await project(info.project);
   check(!$('csv-report-contract'),'project away/back clears old contract selection');
  }
  const finish=release;release=null;finish();
 }
 await confirming;
 if(info.case==='workspace-pending'){observeContract('old accepted response released after current readback');check(!$('csv-report-confirm')&&$('raw-result').textContent.includes('QUEUED')&&requests.filter(r=>r.method==='POST'&&r.path===confirmRoute).length===1,'late old confirmation cannot overwrite current readback or add a POST');}
 if(info.case==='lost'){
  check($('csv-report-confirm')?.textContent==='恢复同一确认的回执','lost accepted confirmation offers exact original recovery');
  await action('csv-report-confirm');
  const attempts=requests.filter(r=>r.path===confirmRoute&&r.method==='POST');check(attempts.length===2&&JSON.stringify(attempts[0].body)===JSON.stringify(attempts[1].body),'manual confirmation recovery keeps original Run/version/contract/key');
 }
 if(info.case==='navigation'){
  check(!$('csv-report-contract')&&!$('raw-result').textContent.includes(rid),'late accepted confirmation does not take over current project selection');
  await action('csv-report-open');
 }
 const reply=await rpc({command:'worker',run:rid});assert.equal(reply.status,200);const actual=JSON.parse(reply.text);
 await w.showRun(rid);
 const noFingerprints=structuredClone(actual.run);delete noFingerprints.contract.fingerprint;delete noFingerprints.result.task_acceptance.contract_fingerprint;
 check(!w.csvReportPassed(noFingerprints),'pure display predicate refuses paired missing contract fingerprints');
 const noCheckers=structuredClone(actual.run);delete noCheckers.contract.snapshot.ordinary_csv_report.checker;delete noCheckers.result.task_acceptance.checker;
 check(!w.csvReportPassed(noCheckers),'pure display predicate refuses paired missing checker versions');
 check($('run-goal-acceptance').textContent.includes('合同 PASS')&&$('run-goal-acceptance').textContent.includes('0模型请求')&&$('run-goal-acceptance').textContent.includes('人工 PENDING'),'independent full contract PASS is visible with zero-model/general/human boundaries');
 check($('run-artifacts')?.textContent.includes(actual.artifact.id),'actual saved artifact is offered inside the same Run');
 const button=label=>[...$('run-artifacts').querySelectorAll('button')].find(b=>b.textContent===label);
 await action(button('查看此成果'));check($('run-artifacts').querySelector('pre').textContent===actual.artifact.content,'same-Run view reauthorizes and shows complete saved MD');
 await action(button('下载此成果'));await wait(()=>blobs[0]?.revoked,'Blob cleanup');const bytes=Buffer.from(await blobs[0].blob.arrayBuffer());
 check(bytes.equals(Buffer.from(actual.artifact.content))&&blobs[0].filename===`sim2act-${rid}-${actual.artifact.id}.md`,'download bytes and filename bind exact saved artifact and Run');
 fs.writeFileSync(info.output.replace('result.json','captured-report.md'),bytes);
 assert.equal((await rpc({command:'after',run:rid})).status,200);
 fs.writeFileSync(info.output,JSON.stringify({status:'PASS',case:info.case,checks,requests,assets,observations,actual},null,2));dom.window.close();process.stdout.write(JSON.stringify({done:true})+'\n');
}
main().catch(error=>{if(info?.output)fs.writeFileSync(info.output,JSON.stringify({status:'FAIL',error:String(error.stack),checks,requests,assets,observations},null,2));if(dom)dom.window.close();process.stderr.write(String(error.stack)+'\n');process.stdout.write(JSON.stringify({done:true})+'\n');process.exitCode=1;});
