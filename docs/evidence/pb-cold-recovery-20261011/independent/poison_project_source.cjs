"use strict";
// Two separate Node processes; actual HTTP via IPC and a fresh JSDOM. No native browser claim.
const fs=require('node:fs'),assert=require('node:assert/strict'),crypto=require('node:crypto'),readline=require('node:readline'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),checks=[],requests=[],responses=[],actions=[],assets=[],hashes={},pending=new Map(),storageAttempts=[];
let serial=0,dom,w,$,held=null,fault=info.phase==='first'?info.scenario:'',generated=null;
readline.createInterface({input:process.stdin}).on('line',line=>{const value=JSON.parse(line),resolve=pending.get(value.id);pending.delete(value.id);resolve(value);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+'\n');});
const check=(value,label)=>{assert(value,label);checks.push(label);};
const wait=async test=>{const end=Date.now()+15000;while(Date.now()<end){if(test())return;await new Promise(resolve=>setTimeout(resolve,5));}throw Error('bounded page wait');};
function visible(element){if(!element?.isConnected)return false;for(let node=element;node;node=node.parentElement){const style=w.getComputedStyle(node);if(node.hidden||node.hasAttribute('inert')||node.getAttribute('aria-hidden')==='true'||style.display==='none'||['hidden','collapse'].includes(style.visibility))return false;if(node.tagName==='DETAILS'&&!node.open&&!node.querySelector('summary')?.contains(element))return false;}return true;}
async function gesture(element,perform,bindings){assert(visible(element),`visible action ${element?.id||element?.textContent}`);assert(!element.matches(':disabled'),`enabled action ${element.id}`);element.focus();const work=[],restore=[];for(const [node,property] of bindings){const original=node?.[property];if(typeof original!=='function')continue;const wrapper=function(event){const value=original.call(this,event);work.push(Promise.resolve(value));return value;};node[property]=wrapper;restore.push(()=>{if(node[property]===wrapper)node[property]=original;});}actions.push({element:element.id||element.textContent,visible:true,enabled:true,event:'DOM dispatch'});try{perform();await Promise.all(work);}finally{restore.forEach(fn=>fn());}}
const click=value=>{const element=typeof value==='string'?$(value):value;return gesture(element,()=>element.click(),[[element,'onclick'],[element.form,'onsubmit']]);};
const edit=(id,value)=>{const element=$(id);return gesture(element,()=>{element.value=value;element.dispatchEvent(new w.Event('input',{bubbles:true}));element.dispatchEvent(new w.Event('change',{bubbles:true}));},[[element,'oninput'],[element,'onchange']]);};
const nav=id=>click(w.document.querySelector(`#workspace-nav [data-tab=${id}]`));
const appButton=name=>[...$('app-list').querySelectorAll('button')].find(button=>button.closest('.row').textContent.includes(name));
const extracting=()=>requests.filter(r=>r.method==='POST'&&r.path.endsWith('/extract'));
const preparing=()=>requests.filter(r=>r.method==='POST'&&r.path.endsWith('/extraction-requests'));
const indexRows=()=>[...$('registered-recovery-list').children];
const denyStorage=kind=>{storageAttempts.push(kind);throw Error('forbidden browser persistent storage '+kind);};
async function boot(){
 const load=async path=>{const result=await rpc({path,method:'GET'});assert.equal(result.status,200);const sha=crypto.createHash('sha256').update(result.text).digest('hex');assets.push({boot:1,path,status:result.status,content_type:result.content_type,bytes:Buffer.byteLength(result.text),sha256:sha});hashes[path.slice(1)||'index.html']=sha;return result.text;};
 dom=new JSDOM(await load('/'),{url:'http://offline.test/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w.crypto,'subtle',{value:crypto.webcrypto.subtle});w.crypto.randomUUID=crypto.randomUUID;w.setInterval=()=>0;
 w.Storage.prototype.setItem=()=>denyStorage('Storage.setItem');Object.defineProperty(w.document,'cookie',{get:()=>'',set:()=>denyStorage('cookie')});Object.defineProperty(w,'name',{get:()=>'',set:()=>denyStorage('window.name')});w.indexedDB={open:()=>denyStorage('indexedDB.open')};Object.defineProperty(w.navigator,'serviceWorker',{value:{register:()=>denyStorage('serviceWorker.register')}});
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{
  const request={path,method:options.method||'GET',body:options.body&&JSON.parse(options.body),headers:options.headers,cache:options.cache};requests.push(request);
  if(fault==='before-prepare'&&request.method==='POST'&&path.endsWith('/extraction-requests')){fault='';responses.push({path,not_dispatched:true});throw Error('controlled prepare failure before dispatch');}
  if(fault==='before-extract'&&request.method==='POST'&&path.endsWith('/extract')){fault='';responses.push({path,not_dispatched:true});throw Error('controlled extraction failure before dispatch');}
  const result=await rpc(request);responses.push({path,status:result.status,actual_text:result.text,cache_control:result.cache_control});
  if(request.method==='POST'&&path.endsWith('/extract')&&result.status===201)generated=JSON.parse(result.text).id;
  if(['lost-prepare','late-prepare-ABA','revoke-source','explicit-new-closed'].includes(fault)&&request.method==='POST'&&path.endsWith('/extraction-requests')){
   const kind=fault;fault='';assert.equal(result.status,201);if(kind==='late-prepare-ABA')await new Promise(resolve=>held=resolve);else throw Error('controlled lost prepared identity response');
  }
  if(fault&&request.method==='POST'&&path.endsWith('/extract')&&result.status===201){fault='';throw Error('controlled lost committed extraction response');}
  if(fault==='late-keyed-ABA'&&path.includes('/extraction-receipts?')){fault='';await new Promise(resolve=>held=resolve);}
  if(fault==='late-discovery-ABA'&&path.endsWith('/registered-text-requests')){fault='';await new Promise(resolve=>held=resolve);}
  if(['poison-journal-key','poison-journal-body'].includes(fault)&&path.includes('/extraction-requests?')&&result.status===200){
   const kind=fault;fault='';const value=JSON.parse(result.text);if(kind==='poison-journal-key'){value.request_key=crypto.randomUUID();value.request.request_key=value.request_key;}else value.request.name='CONTROLLED POISON BODY';const controlled=JSON.stringify(value);responses.push({path,status:result.status,controlled_text:controlled,fault:kind});return new Response(controlled,{status:200});
  }
  return new Response(result.text,{status:result.status,headers:{'Content-Type':result.content_type||'application/json','Cache-Control':result.cache_control||''}});
 };
 for(const script of [...w.document.querySelectorAll('script[src]')]){const path=script.getAttribute('src'),node=w.document.createElement('script');node.textContent=await load(path);w.document.body.append(node);}
 await edit('token',info.owner==='B'?'synthetic-test-B':'synthetic-test-A');await click('connect');await wait(()=>$('login').hidden);if($('project-select').value!==info.project)await edit('project-select',info.project);await nav('apps');
 check(w.eval('registeredExtractionRequests.size')===0,'fresh Node process has no original in-memory request Map');
 check(w.localStorage.length===0&&w.sessionStorage.length===0&&w.name===''&&w.document.cookie==='','fresh browser state contains no durable recovery body or secret');
}
async function openSource(){await click(appButton('source'));await click($('internal-instances').querySelector('button'));await click($('internal-runs').querySelector('button'));await click('registered-extraction-open');await edit('registered-extraction-target',info.target);await edit('registered-extraction-name','Extracted cold text');}
async function discover(){await click('registered-recovery-refresh');check(indexRows().length===1,'cold actual HTTP project index discovers one original identity');check(!$('registered-recovery-list').textContent.includes('Extracted cold text'),'opaque discovery index does not expose saved request name');}
async function openRecoveredSource(){await click(indexRows()[0].querySelector('button'));check(visible($('registered-extraction-open')),'visible opaque recovery row reopens actual authorized source');await click('registered-extraction-open');check(visible($('registered-extraction-retry'))&&$('registered-extraction-submit').disabled,'cold original identity blocks ordinary save and exposes GET-only recovery');}
async function newWorker(){
 await edit('app-agent-term','Alpha');await click('internal-prepare');await click('internal-approval-ack');await click('internal-commit');await click($('internal-releases').querySelector('button'));await edit('internal-term','Gamma');await click('internal-run-submit');const newRun=w.eval('engineering.run.id');const worked=await rpc({command:'worker'});assert.equal(worked.status,200);await click('internal-refresh');await click($('internal-runs').querySelector('button'));const actual=w.eval('engineering.run');check(actual.status==='SUCCEEDED'&&actual.id===newRun&&actual.id!==info.run&&actual.result_version===1,'cold normal Worker commits one actual new typed result');check(actual.result.resource_id===info.resource&&actual.result.term==='Gamma'&&actual.result.citations[0].quote==='Gamma new obligation'&&actual.result.citations[1].quote==='Gamma final note','cold recovered candidate computes new material and term');check($('owner-status').textContent.includes('PENDING'),'cold restored application owner remains PENDING');
}
(async()=>{let status='FAIL',error=null;try{
 await boot();
 if(info.phase==='first'){
  await openSource();
  if(info.scenario==='late-prepare-ABA'){
   const submitting=click('registered-extraction-submit');await wait(()=>held);const release=held;held=null;await nav('projects');await nav('apps');const focus=w.document.activeElement;release();await submitting;check(extracting().length===0&&w.document.activeElement===focus,'late prepare after workspace ABA cannot dispatch effect or move focus');
  }else await click('registered-extraction-submit');
  check(preparing().length===1,'one explicit prepare attempt; no prepare replay');
  check($('registered-extraction-submit').disabled&&visible($('registered-extraction-retry')),'unknown first-page outcome retains identity and blocks resubmit');
  check(!w.eval('activeApp')||w.eval('activeApp')===info.source,'unknown result does not install an unverified candidate');
 }else if(info.scenario==='poison-project-source'){
  await discover();await click(indexRows()[0].querySelector('button'));
  check(w.eval('activeApp')!==info.target,'misbound project recovery metadata must not install unrelated authorized target as the source preview');
  check(extracting().length===0&&preparing().length===0,'cold metadata corruption cannot trigger replay');
 }else if(info.scenario==='cross-owner'||info.scenario==='cross-project'){
  await click('registered-recovery-refresh');check(indexRows().length===0,'other owner or project has no original identity in visible index');check(preparing().length===0&&extracting().length===0,'cross-scope cold page does not replay or install');
  if(info.scenario==='cross-owner')check(![...$('project-select').options].some(o=>o.value===info.original_project),'foreign project is absent from authorized project options');
 }else if(info.scenario==='before-prepare'){
  await click('registered-recovery-refresh');check(indexRows().length===0,'failure before identity acceptance has no effect/request to recover');await openSource();await click('registered-extraction-submit');check(extracting().length===1&&preparing().length===1,'cold page starts a new explicit request only by manual save');check(w.eval('activeApp')===generated,'new explicit request after pre-acceptance failure installs its exact candidate');await newWorker();
 }else{
  if(info.scenario==='late-discovery-ABA'){
   fault='late-discovery-ABA';const discovering=click('registered-recovery-refresh');await wait(()=>held);const release=held;held=null;await nav('projects');await nav('apps');const focus=w.document.activeElement;release();await discovering;check(indexRows().length===0&&w.document.activeElement===focus,'late opaque index after workspace ABA cannot install rows or focus');
  }
  await discover();
  if(info.scenario==='revoke-source'){
   await click(indexRows()[0].querySelector('button'));check($('registered-recovery-status').textContent.includes('当前权限'),'cold revoked source refuses content restoration');await click(indexRows()[0].querySelectorAll('button')[1]);check($('registered-recovery-status').textContent.includes('明确关闭'),'visible metadata-only close works after source revoke');check(extracting().length===0&&preparing().length===0,'revoked cold close never repeats extraction');
  }else{
   if(info.scenario==='revoke-target'){
    await click(indexRows()[0].querySelector('button'));check(visible($('registered-extraction-open')),'source remains readable after target revoke');await click('registered-extraction-open');
    // Source may open while options reject the now unavailable target.
    check(w.eval('activeApp')===info.source&&extracting().length===0&&preparing().length===0,'target revoke cannot restore/install candidate or repeat effect');
   }else{
    await openRecoveredSource();
    const pendingOnly=['lost-prepare','before-extract','rolled-back','late-prepare-ABA','explicit-new-closed'].includes(info.scenario);
    if(info.scenario==='late-keyed-ABA'){
     fault='late-keyed-ABA';const recovering=click('registered-extraction-retry');await wait(()=>held);const release=held;held=null;await nav('projects');await nav('apps');const focus=w.document.activeElement;release();await recovering;check(w.eval('activeApp')===info.source&&w.document.activeElement===focus,'late original-key receipt after navigation ABA cannot install or move focus');await discover();await openRecoveredSource();
    }
    if(['poison-journal-key','poison-journal-body'].includes(info.scenario))fault=info.scenario;
    await click('registered-extraction-retry');
    if(['poison-journal-key','poison-journal-body'].includes(info.scenario)){check(w.eval('activeApp')===info.source&&$('registered-extraction-submit').disabled,'poisoned original-key identity/body cannot install or enable resend');check(visible($('registered-extraction-retry')),'original key remains visibly recoverable after rejected response');await click('registered-extraction-retry');}
    check(preparing().length===0&&extracting().length===0,'cold reconciliation uses GET only and never POST replays');
    if(pendingOnly){
     check(w.eval('activeApp')===info.source&&$('registered-extraction-submit').disabled&&$('registered-extraction-status').textContent.includes('不会自动重发'),'uncommitted original request remains explicit UNKNOWN barrier');
     if(info.scenario==='explicit-new-closed'){await click('registered-extraction-new');check($('registered-extraction-submit').disabled,'new request still requires a selected target');await edit('registered-extraction-target',info.target);await edit('registered-extraction-name','Extracted cold text');await click('registered-extraction-submit');check(extracting().length===1&&preparing().length===1,'explicit close followed by manual new save creates one new identity');check(w.eval('activeApp')===generated,'closed predecessor cannot be reinstalled; exact new candidate opens');await newWorker();}
    }else{
     const installed=w.eval('activeApp'),original=JSON.parse(responses.findLast(r=>r.path.endsWith('/registered-text-requests')&&r.actual_text).actual_text).items[0];check(installed===original.app_id&&installed!==info.source&&installed!==info.target,'cold original-key recovery installs exact independently checked app from actual persistent index');
     if(info.scenario==='explicit-new-committed'){
      await discover();await openRecoveredSource();await click('registered-extraction-new');await edit('registered-extraction-target',info.target);await edit('registered-extraction-name','Extracted cold text');await click('registered-extraction-submit');check(extracting().length===1&&preparing().length===1&&w.eval('activeApp')!==installed,'new explicit action after exact old-candidate GET creates distinct app');
     }
     await newWorker();
    }
   }
  }
 }
 check(storageAttempts.length===0&&w.localStorage.length===0&&w.sessionStorage.length===0,'browser attempted no sensitive persistent writes');check(requests.filter(r=>/extraction-requests|extraction-receipts|registered-text-requests/.test(r.path)).every(r=>r.cache==='no-store'),'all recovery request fetches disable HTTP caching');check(requests.every(r=>!r.path.includes('Extracted')&&!r.path.includes('CONTROLLED')),'request URLs contain no request body/name');status='PASS';
 }catch(exc){error=exc.stack||String(exc);process.stderr.write(error+'\n');process.exitCode=1;}
 finally{fs.writeFileSync(info.output,JSON.stringify({status,error,scenario:info.scenario,phase:info.phase,process_id:process.pid,classification:'ACTUAL_IPC_HTTP_NEW_NODE_PROCESS_NEW_JSDOM',checks,actions,requests,responses,static_resource_loads:assets,loaded_source_sha256:hashes,generated,active_app:w?.eval('activeApp'),expected_source:info.source,poison_source:info.target,storage_attempts:storageAttempts,real_model:'NOT_RUN',native_browser:'NOT_RUN'},null,2));if(dom)dom.window.close();process.stdout.write(JSON.stringify({done:true})+'\n');}
})();
