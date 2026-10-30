'use strict';
// Real page scripts, explicit synthetic HTTP. Not backend timing or pixels.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{JSDOM}=require('jsdom');
const web=path.join(__dirname,'../src/sim2act/web'),windows=[],checks=[];
const id=(prefix,n)=>prefix+'_'+String(n).repeat(32),iid=id('iinstance',1),rid=id('run',2),pid=id('proj',3),aid=id('app',4);
const check=(value,label)=>{assert(value,label);checks.push(label);};
const tick=()=>new Promise(r=>setTimeout(r,0));
async function wait(fn){for(let n=0;n<100;n++){if(fn())return;await tick();}throw Error('Fixture observation timed out');}
function page({lost=false,bad=false,heldProgress=false,unsupported=false,ack=null}={}){
 const w=new JSDOM(fs.readFileSync(path.join(web,'index.html'),'utf8'),{url:'http://synthetic-stop.test',runScripts:'dangerously'}).window;windows.push(w);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w.crypto,'subtle',{value:crypto.webcrypto.subtle});w.crypto.randomUUID=()=>crypto.randomUUID();w.setInterval=()=>0;
 const requests=[],details=[],pending={request_key:'original-user-intent',input:{column:'amount'}},state={namespace:'INTERNAL_ENGINEERING_ONLY',formal_publication_enabled:false,id:rid,instance_id:iid,status:'RUNNING',version:1,cancel_intent:false,content_access:false,consistency:'COMMITTED_METADATA_ONLY'};
 let resolveProgress;
 w.fetch=async(url,config)=>{
  const method=config?.method||'GET',body=config?.body?JSON.parse(config.body):null;requests.push({path:url,method,body});
  const response=value=>new Response(JSON.stringify(value),{status:200});
  if(url.endsWith('/control-progress')){if(heldProgress)await new Promise(r=>resolveProgress=r);if(unsupported)return new Response(JSON.stringify({error:{code:'UNSUPPORTED_CAPABILITY'}}),{status:400});return response(bad?{...state,result:{unsafe:true}}:{...state});}
  if(url.endsWith('/control-status')){const {consistency,...legacy}=state;return response(legacy);}
  if(url.endsWith('/commands')){assert.equal(body.command,'cancel');assert.equal(body.version,state.version);state.version++;state.status='RECONCILING';state.cancel_intent=true;if(lost)throw TypeError('Synthetic ACK lost after real fixture state change');return response({namespace:state.namespace,formal_publication_enabled:false,status:ack||state.status});}
  if(url===`/api/internal/instances/${iid}/runs/${rid}`)return new Promise(resolve=>details.push(value=>resolve(response(value))));
  throw Error('Unexpected UI request '+url);
 };
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=fs.readFileSync(path.join(web,script.getAttribute('src').slice(1)),'utf8');w.document.body.append(node);}
 w.fixture={iid,rid,pid,aid,pending};
 w.eval(`selectWorkspace('apps');token='synthetic-stop-owner';activeApp=fixture.aid;document.getElementById('project-select').replaceChildren(new Option('Own',fixture.pid));engineering={token,project:fixture.pid,app:fixture.aid,appGeneration:appSelectionGeneration,instanceGeneration:1,runGeneration:0,busy:true,historyReady:true,instance:{id:fixture.iid,runs:[{id:fixture.rid}]}};engineeringPending.set(fixture.iid,fixture.pending);document.getElementById('internal-panel').hidden=false;`);
 const run=w.eval('showInternalRun(fixture.rid)');
 return {w,$:id=>w.document.getElementById(id),requests,details,state,run,progress:()=>resolveProgress?.()};
}
(async()=>{try{
 const a=page();await wait(()=>a.details.length===1);
 check(a.w.eval('engineering.busy')&&!!a.$('internal-stop-read'),'independent stop entry exists before blocked full detail completes');
 await a.$('internal-stop-read').onclick();check(!a.$('internal-stop-cancel').disabled,'committed owner metadata enables explicit stop during full-detail busy');
 check(a.w.eval('engineering.run===null')&&a.$('internal-run-detail').textContent==='','metadata never becomes full Run detail');
 await a.$('internal-stop-cancel').onclick();await wait(()=>a.details.length===2);
 check(a.requests.filter(r=>r.method==='POST').length===1&&a.requests.filter(r=>r.method==='POST')[0].path.endsWith('/commands'),'one explicit original cancel, no new execution request');
 a.details[0]({id:rid,instance_id:iid,status:'SUCCEEDED',result:{unsafe:'STALE_DETAIL_SHOULD_NOT_APPEAR'}});await a.run;
 check(!a.$('internal-run-detail').textContent.includes('STALE_DETAIL'),'late pre-cancel full detail cannot overwrite confirmed control');
 check(a.w.eval('engineeringPending.get(fixture.iid)===fixture.pending'),'cancel ACK and metadata preserve original request intent');
 const b=page({lost:true});await wait(()=>b.details.length===1);await b.$('internal-stop-read').onclick();await b.$('internal-stop-cancel').onclick();
 check(b.$('internal-stop-status').textContent.includes('未确认')&&b.$('internal-stop-cancel').disabled,'lost ACK remains unknown and cannot automatically retry');
 check(b.requests.filter(r=>r.path.endsWith('/control-progress')).length===1,'lost ACK does not auto read or resend');
 await b.$('internal-stop-read').onclick();check(b.$('internal-stop-status').textContent.includes('RECONCILING')&&b.$('internal-stop-cancel').disabled,'explicit fresh read confirms recorded cancel without second POST');
 check(b.requests.filter(r=>r.method==='POST').length===1&&b.w.eval('engineeringPending.get(fixture.iid)===fixture.pending'),'lost-ACK recovery preserves key and exactly one command');
 const c=page({bad:true});await wait(()=>c.details.length===1);await c.$('internal-stop-read').onclick();
 check(c.$('internal-stop-cancel').disabled&&c.$('internal-stop-status').textContent.includes('绑定不一致'),'unexpected content in metadata is rejected before enabling control');
 const d=page({heldProgress:true});await wait(()=>d.details.length===1);const read=d.$('internal-stop-read').onclick();await wait(()=>d.requests.some(r=>r.path.endsWith('/control-progress')));
 d.w.selectWorkspace('resources');d.w.selectWorkspace('apps');d.progress();await read;await tick();
 check(d.$('internal-stop-cancel').disabled&&d.$('internal-stop-status').textContent.includes('已变化'),'workspace round trip rejects late metadata and visibly disables old stop');
 const e=page();await wait(()=>e.details.length===1);e.state.status='SUCCEEDED';e.state.version=2;await e.$('internal-stop-read').onclick();
 check(e.w.eval('engineering.run===null')&&e.$('internal-run-detail').textContent===''&&e.$('internal-stop-status').textContent.includes('成果待核'),'SUCCEEDED metadata is not a verified result or export authority');
 check(e.requests.every(r=>r.method==='GET')&&e.w.eval('engineeringPending.get(fixture.iid)===fixture.pending'),'metadata success neither submits nor clears recovery intent');
 const f=page({unsupported:true});await wait(()=>f.details.length===1);await f.$('internal-stop-read').onclick();
 check(!f.$('internal-stop-cancel').disabled&&f.requests.some(r=>r.path.endsWith('/control-status')),'unsupported local projection falls back to original full owner-control validation');
 for(const change of ['identity','workspace']){
  const g=page({unsupported:true,heldProgress:true});await wait(()=>g.details.length===1);const reading=g.$('internal-stop-read').onclick();await wait(()=>g.requests.some(r=>r.path.endsWith('/control-progress')));
  if(change==='identity')g.w.eval("token='different-synthetic-owner';identityConnectionGeneration++");else {g.w.selectWorkspace('resources');g.w.selectWorkspace('apps');}
  g.progress();await reading;
  check(!g.requests.some(r=>r.path.endsWith('/control-status')),change+' change prevents old-ID fallback request under changed scope');
 }
 for(const ack of ['RUNNING','SUCCEEDED','FAILED']){
  const h=page({ack});await wait(()=>h.details.length===1);await h.$('internal-stop-read').onclick();await h.$('internal-stop-cancel').onclick();
  check(h.$('internal-stop-status').textContent.includes('未确认')&&h.$('internal-stop-cancel').disabled&&h.requests.filter(r=>r.method==='POST').length===1&&h.details.length===1,ack+' 2xx ACK cannot confirm cancellation or auto reread');
 }
 const i=page();await wait(()=>i.details.length===1);i.details[0]({id:rid,instance_id:iid,status:'RUNNING',version:1,cancel_intent:false});await i.run;
 check(i.$('internal-controls').textContent==='暂停'&&i.w.document.querySelectorAll('#internal-stop-cancel').length===1,'complete detail has one cancel entry, preserving separate pause');
 await i.$('internal-stop-read').onclick();const cancelling=i.$('internal-stop-cancel').onclick();const duplicate=i.$('internal-stop-cancel').onclick();await Promise.all([cancelling,duplicate]);
 check(i.requests.filter(r=>r.method==='POST').length===1,'rapid duplicate cancel clicks send exactly one versioned command');
 const result={status:'PASS',classification:'JSDOM_REAL_PAGE_SYNTHETIC_HTTP_NOT_PIXELS_NOT_BACKEND_TIMING',checks};if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}catch(error){console.error(error.stack);process.exitCode=1;}finally{windows.forEach(w=>w.close());}})();
