'use strict';
// All human clicks below are synthetic test actions; never a real owner signoff.
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),requests=[],checks=[],assets=[],pending=new Map();
let serial=0,dom,w,$,hold=null,release=null,drop=false,run;
readline.createInterface({input:process.stdin}).on('line',line=>{const r=JSON.parse(line),resolve=pending.get(r.id);assert(resolve);pending.delete(r.id);resolve(r);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+'\n');});
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
const wait=async(fn,label)=>{const until=Date.now()+10000;while(Date.now()<until){if(fn())return;await new Promise(r=>setTimeout(r,5));}throw Error(label);};
function visible(el){if(!el?.isConnected)return false;for(let p=el;p;p=p.parentElement)if(p.hidden||w.getComputedStyle(p).display==='none')return false;return true;}
async function action(el,type='click'){
 if(typeof el==='string')el=$(el);assert(visible(el),typeof el==='object'?el?.id:el);assert(!el.matches(':disabled'));const work=[],restore=[];
 for(const [node,name] of [[el,type==='change'?'onchange':'onclick'],[type==='click'?el.form:null,'onsubmit']]){const fn=node?.[name];if(typeof fn!=='function')continue;const wrap=function(e){const p=fn.call(this,e);work.push(Promise.resolve(p));return p;};node[name]=wrap;restore.push(()=>{if(node[name]===wrap)node[name]=fn;});}
 try{if(type==='click')el.click();else el.dispatchEvent(new w.Event(type,{bubbles:true}));await Promise.all(work);}finally{restore.forEach(fn=>fn());}
}
async function tick(id){$(id).checked=true;await action(id,'change');}
async function project(id){$('project-select').value=id;await action('project-select','change');}
async function selectRun(){await action('run-history-refresh');const row=[...$('runs').children].find(r=>r.textContent.includes(run.slice(0,16)));assert(row);await action(row.querySelector('button'));}
const posts=()=>requests.filter(r=>r.method==='POST'&&r.path.endsWith('/owner-review-requests'));
async function read(){await action('ordinary-owner-read');await wait(()=>!!$('ordinary-owner-proof')||$('ordinary-owner-status').textContent.includes('STALE'),'current review read');}
async function prepare(){await read();await action('ordinary-owner-prepare');check(!!$('ordinary-owner-form'),'explicit preparation exposes same-Run frozen criteria');}
async function choices(reject=false){for(const [n,s] of [...$('ordinary-owner-form').querySelectorAll('select')].entries()){check(s.value==='','each criterion starts without an ACCEPT default');s.value=reject&&n===0?'REJECT':'ACCEPT';}for(const t of $('ordinary-owner-form').querySelectorAll('textarea'))t.value='SIMULATED user declaration, not real human signoff';await tick('ordinary-owner-ack');}
async function boot(){
 const load=async path=>{const r=await rpc({method:'GET',path});assert.equal(r.status,200);assets.push({path,sha256:crypto.createHash('sha256').update(r.text).digest('hex')});return r.text;};
 dom=new JSDOM(await load('/'),{url:'http://testserver/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.setInterval=()=>0;
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{const request={method:options.method||'GET',path,body:options.body?JSON.parse(options.body):undefined};requests.push(request);const h=hold&&hold.path===path&&hold.method===request.method?hold:null;if(h)hold=null;
  const r=await rpc({...request,headers:options.headers});request.status=r.status;request.response=JSON.parse(r.text);
  if(h)await new Promise(resolve=>{release=resolve;});
  if(drop&&request.method==='POST'&&path.endsWith('/owner-review-requests')){drop=false;throw Error('Synthetic response lost AFTER actual server commit');}
  return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});};
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(script.getAttribute('src'));w.document.body.append(node);}
 $('token').value='synthetic-test-A';await action('connect');await project(info.project);
 const card=[...$('goal-card-list').children].find(r=>r.textContent.includes('按完整条件执行'));assert(card);await action(card.querySelector('button'));
 check($('ordinary-rubric-preview').textContent.includes('不能签收语义')&&$('ordinary-rubric-preview').textContent.includes('不把旧成功当本次结果'),'visible full saved rubric and unresolved items before execution');
 check($('ordinary-rubric-run').disabled&&!$('ordinary-rubric-start-ack').checked,'starting a new reviewable Run requires an explicit unchecked confirmation');
 $('goal-card-acceptance_checks').value='UNSAVED MUST NOT REPLACE THE FROZEN STANDARD';
 await tick('ordinary-rubric-start-ack');await action('ordinary-rubric-run');
 const sent=requests.find(r=>r.method==='POST'&&r.path.endsWith('/reviewable-runs'));check(sent?.status===202,'visible dedicated control creates a prospective ordinary Run');run=sent.response.run_id;
 assert.equal((await rpc({command:'worker'})).status,200);await selectRun();
 check($('result').textContent.includes('PARTIAL')&&$('result').textContent.includes('NOT_RUN')&&visible($('ordinary-owner-review')),'same ordinary result canvas exposes manual review alongside PARTIAL/NOT_RUN');
 check($('ordinary-owner-frozen').textContent.includes('不把旧成功当本次结果')&&!$('ordinary-owner-frozen').textContent.includes('UNSAVED'),'frozen saved standards, not unsaved editor content, bind the exact Run');
 check(posts().length===0,'opening the result never prepares or declares acceptance automatically');
}
async function normal(reject){await prepare();check(!$('ordinary-owner-ack').checked&&$('ordinary-owner-decide').disabled,'explicit user acknowledgement required after choosing all criteria');await choices(reject);await action('ordinary-owner-decide');
 const expected=reject?'REJECTED':'ACCEPTED';check($('ordinary-owner-status').textContent.includes(expected),'actual appended synthetic declaration is visibly '+expected);
 check(posts().length===2&&posts()[1].body.choices.length>2,'one preparation and one explicit complete ordered declaration');
 const r=await rpc({method:'GET',path:`/api/runs/${run}`,headers:{Authorization:'Bearer synthetic-test-A'}});const actual=JSON.parse(r.text);check(actual.status==='PARTIAL'&&actual.result.goal_acceptance==='NOT_RUN','manual declaration never promotes automatic acceptance or technical state');
 $('ordinary-owner-stop-reason').value='Synthetic explicit withdrawal';await tick('ordinary-owner-stop-ack');await action('ordinary-owner-stop');check($('ordinary-owner-status').textContent.includes('REVOKED'),'explicit withdrawal appends history without deleting prior declaration');
}
async function navigation(){await prepare();await choices();const detached=$('ordinary-owner-decide');
 for(const [label,change] of [['workspace',async()=>{w.selectWorkspace('resources');w.selectWorkspace('projects');}],['Run',async()=>{await selectRun();}],['project',async()=>{await project(info.other);await project(info.project);await selectRun();}],['identity',async()=>{await action('identity-switch');$('token').value='synthetic-test-B';await action('connect');await action('identity-switch');$('token').value='synthetic-test-A';await action('connect');await project(info.project);await selectRun();}]]){
  const old=$('ordinary-owner-read'),before=posts().length;hold={path:`/api/runs/${run}/owner-review`,method:'GET'};const pendingRead=action(old);await wait(()=>!!release,'old review read held');await change();const finish=release;release=null;finish();await pendingRead;
  check(!$('ordinary-owner-form')&&posts().length===before,label+' return discards late callback and does not inherit choices or submit');await read();check(!$('ordinary-owner-ack').checked,label+' fresh read requires new user acknowledgement');
 }
 const count=posts().length;await detached.form.onsubmit(new w.Event('submit'));check(posts().length===count,'detached old user form cannot submit');
 await choices();drop=true;hold={path:`/api/runs/${run}/owner-review-requests`,method:'POST'};const sending=action('ordinary-owner-decide');await wait(()=>!!release,'accepted POST reply held');
 const form=$('ordinary-owner-form'),beforeDuplicate=posts().length;await form.onsubmit(new w.Event('submit'));check(posts().length===beforeDuplicate,'duplicate explicit submit while request is pending sends no second POST');
 w.selectWorkspace('resources');w.selectWorkspace('projects');const finish=release;release=null;finish();await sending;
 check(!visible($('ordinary-owner-form')),'late POST callback does not repaint the returned workspace');
 await action('ordinary-owner-read');check(posts().at(-1).status===201&&!$('ordinary-owner-recover').hidden,'lost response after actual commit remains UNKNOWN without claiming signoff');
 const original=JSON.stringify(posts().at(-1).body),committed=posts().length;
 w.selectWorkspace('resources');w.selectWorkspace('projects');check(posts().length===committed&&!$('ordinary-owner-retry-ack').checked,'UNKNOWN return does not auto replay or inherit acknowledgement');
 await action('ordinary-owner-recover');check($('ordinary-owner-status').textContent.includes('ACCEPTED')&&posts().length===committed,'explicit original-key GET recovers committed receipt without another declaration');
 check(JSON.stringify(posts().at(-1).body)===original,'original immutable request body retained throughout UNKNOWN recovery');
}
async function lateIntent(){
 await read();hold={path:`/api/runs/${run}/owner-review-requests`,method:'POST'};const preparing=action('ordinary-owner-prepare');await wait(()=>!!release,'accepted PREPARE held');const finishPrepare=release;release=null;
 w.selectWorkspace('resources');w.selectWorkspace('projects');await action('ordinary-owner-recover');check(!!$('ordinary-owner-form')&&posts().length===1,'new workspace can explicitly GET recover committed pending preparation without retrying POST');
 await choices();hold={path:`/api/runs/${run}/owner-review-requests`,method:'POST'};const deciding=action('ordinary-owner-decide');await wait(()=>!!release,'accepted DECIDE held');const finishDecide=release;release=null;
 const key=posts().at(-1).body.request_key;finishPrepare();await preparing;
 check(w.eval(`ordinaryOwnerIntents.get(ordinaryOwnerKey(${JSON.stringify(run)}))?.body.request_key`)===key,'late original PREPARE receipt cannot erase the next in-flight explicit declaration');
 w.selectWorkspace('resources');w.selectWorkspace('projects');check(!$('ordinary-owner-recover').hidden,'next declaration recovery remains available after the late earlier receipt');
 await action('ordinary-owner-recover');check($('ordinary-owner-status').textContent.includes('ACCEPTED')&&posts().length===2,'next declaration GET recovers its own exact accepted record with no duplicate POST');finishDecide();await deciding;
 check(posts().length===2&&$('ordinary-owner-status').textContent.includes('ACCEPTED'),'late declaration response preserves current same-Run recovered state');
}
async function revoked(){await prepare();await choices();assert.equal((await rpc({command:'revoke'})).status,200);await action('ordinary-owner-decide');check(posts().length===1&&!$('ordinary-owner-form'),'fresh authorization check blocks DECIDE before POST after actual Grant revoke');check(!$('run-answer')&&$('raw-result').textContent===''&&!$('result').textContent.includes('item,amount'),'failed DECIDE clears protected result immediately, before any subsequent read');w.selectWorkspace('resources');w.selectWorkspace('projects');check(!$('run-answer')&&$('ordinary-owner-frozen').textContent===''&&$('raw-result').textContent==='','workspace return cannot revive revoked answer or frozen Goal cache');await action('ordinary-owner-read');
 check($('ordinary-owner-status').textContent.includes('STALE')&&!$('run-answer')&&$('raw-result').textContent==='','revoked content clears protected result and retains metadata-only STALE history');
 await selectRun();check(!!$('ordinary-owner-metadata-open')&&!$('run-answer'),'denied full Run from durable history exposes explicit metadata-only signoff entry');await action('ordinary-owner-metadata-open');check(!!$('ordinary-owner-stop')&&$('ordinary-owner-frozen').textContent==='','metadata-only entry reaches exact pending STOP without protected source body');
 $('ordinary-owner-stop-reason').value='Cancel after source revoke';await tick('ordinary-owner-stop-ack');await action('ordinary-owner-stop');check($('ordinary-owner-status').textContent.includes('CANCELLED'),'owner can explicitly cancel exact pending preview after source access withdrawal');
}
(async()=>{try{await boot();if(info.case==='accept'||info.case==='reject')await normal(info.case==='reject');else if(info.case==='navigation-unknown')await navigation();else if(info.case==='late-intent')await lateIntent();else await revoked();fs.writeFileSync(info.output,JSON.stringify({status:'PASS',case:info.case,checks,assets,requests,run,real_human_signoff:'NOT_RUN',real_model_requests:0},null,2));}catch(error){fs.writeFileSync(info.output,JSON.stringify({status:'FAIL',case:info.case,checks,assets,requests,error:error.stack},null,2));console.error(error.stack);process.exitCode=1;}finally{dom?.window.close();process.stdout.write(JSON.stringify({done:true})+'\n');}})();
