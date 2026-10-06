'use strict';
// HTTP-backed jsdom functional checks. No layout, screenshot or real-browser claim.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {execFile}=require('node:child_process');
const execFileAsync=require('node:util').promisify(execFile);
const vm=require('node:vm');
const {JSDOM}=require('/workspace/browser-tools/node_modules/jsdom');
const root=process.argv[2],python=process.argv[3],repo=path.resolve(__dirname,'../..');
const info=JSON.parse(fs.readFileSync(path.join(root,'info.json'),'utf8')),base=`http://127.0.0.1:${info.port}`;
const result={kind:'HTTP-backed jsdom functional checks',browser:'NOT_RUN',visual:'NOT_RUN',providerRequests:0,checks:[]};
const calls=[];let dom,w,holdApproval=false,releaseApproval,dropRun=false;
function check(name,value){assert.ok(value,name);result.checks.push({name,status:'PASS'});}
async function action(name){return (await execFileAsync(python,['scripts/agent-ui/fixture.py','--root',root,'--action',name],{cwd:repo,env:{...process.env,PYTHONPATH:'src'},encoding:'utf8'})).stdout.trim();}
async function wait(fn){const deadline=Date.now()+10000;while(!fn()){assert.ok(Date.now()<deadline,'DOM wait timeout');await new Promise(r=>setTimeout(r,20));}}
async function create(){
 const html=fs.readFileSync(path.join(repo,'src/sim2act/web/index.html'),'utf8');
 dom=new JSDOM(html,{url:base,runScripts:'outside-only'});w=dom.window;
 w.structuredClone=structuredClone;w.TextEncoder=TextEncoder;w.crypto.randomUUID=require('node:crypto').randomUUID;
 w.fetch=async(url,options={})=>{
  calls.push({path:url,method:options.method||'GET'});
  let r;try{r=await fetch(new URL(url,base),options);}catch(error){result.transportFailures??=[];result.transportFailures.push({path:url,error:error.message,cause:error.cause?.message,code:error.cause?.code});throw error;}
  if(holdApproval && options.method==='POST' && /release-approvals$/.test(url)){holdApproval=false;await new Promise(resolve=>{releaseApproval=resolve;});}
  if(dropRun && options.method==='POST' && /\/runs$/.test(url)){dropRun=false;throw Error('synthetic receipt delivery lost after actual server acceptance');}
  return r;
 };
 vm.runInContext(fs.readFileSync(path.join(repo,'src/sim2act/web/app.js'),'utf8'),dom.getInternalVMContext());
 vm.runInContext(fs.readFileSync(path.join(repo,'src/sim2act/web/internal.js'),'utf8'),dom.getInternalVMContext());
 w.document.getElementById('token').value='synthetic-agent-ui-A';
 w.document.getElementById('connect').click();await wait(()=>w.document.getElementById('login').hidden);
 w.document.getElementById('project-select').value=info.project;
 await w.eval('refresh()');w.eval('selectWorkspace("apps")');
}
const $=id=>w.document.getElementById(id);
async function open(id){await w.eval(`showApp(${JSON.stringify(id)})`);}
function term(id,value){$(id).value=value;$(id).dispatchEvent(new w.Event('input'));}
async function load(file){const text=fs.readFileSync(path.join(root,file),'utf8');Object.defineProperty($('internal-replay-file'),'files',{configurable:true,value:[{size:Buffer.byteLength(text),text:()=>Promise.resolve(text)}]});await $('internal-replay-file').onchange();}
async function prepare(){await $('internal-prepare').onclick();}
(async()=>{
 try{
  await create();await open(info.derived_app);
  check('agent opens through existing authenticated app view without CSV columns crash',!$('internal-panel').hidden && !$('internal-agent').hidden && $('app-column-label').hidden);
  check('explicit offline and semantic UNKNOWN source labels',/OFFLINE_REPLAY_ONLY/.test($('app-origin').textContent)&&/UNKNOWN/.test($('internal-agent').textContent)&&/尚无真实模型自主生成/.test($('internal-agent').textContent));
  check('no Replay means no approval or run submission',$('internal-prepare').disabled&&$('internal-run-submit').disabled);
  const beforePreview=calls.length;$('app-preview-form').dispatchEvent(new w.Event('submit',{cancelable:true}));await new Promise(r=>setTimeout(r,30));
  check('agent Enter cannot submit old CSV preview',!calls.slice(beforePreview).some(c=>/\/previews$/.test(c.path)));
  term('app-agent-term',info.term_b);term('internal-term',info.term_b);await load('derived-replay.json');
  check('Replay loading is marked unverified until server inspection',!$('internal-prepare').disabled&&/尚未验证/.test($('internal-replay-status').textContent));
  await prepare();
  check('server approval exposes accepted Replay fingerprint and UNKNOWN',$('internal-approval-detail').textContent.includes('offline_replay_fingerprint')&&$('internal-approval-detail').textContent.includes('UNKNOWN'));
  check('manual acknowledgement required',$('internal-commit').disabled);
  $('internal-approval-ack').checked=true;$('internal-approval-ack').onchange();await $('internal-commit').onclick();
  const latest=w.eval('engineering.releases.at(-1).id');
  const releaseButton=Array.from($('internal-releases').querySelectorAll('button')).find(b=>b.parentNode.textContent.includes(latest));releaseButton.click();await wait(()=>w.eval('engineering && !engineering.busy && !!engineering.instance'));
  const iid=w.eval('engineering.instance.id');
  await w.eval('submitInternal(engineering)');await action('worker');await w.eval(`showInternalInstance(${JSON.stringify(iid)})`);
  check('new cold worker uses accepted frozen Replay and appends real result v1',$('internal-data').textContent.includes('历史结果 v1')&&$('internal-data').textContent.includes(info.term_b));
  check('server trusted citations render as text and semantic UNKNOWN',$('internal-data').querySelectorAll('blockquote').length>0&&$('internal-data').textContent.includes('语义 UNKNOWN'));
  const record=w.eval('internalResult({version:7,release_id:"synthetic",data:{result:{term:"x",semantic_status:"UNKNOWN",resource_id:"r",revision:1,source_hash:"h",citations:[{start_line:1,end_line:1,quote:"<img src=x onerror=alert(1)>"}]}}},engineering)');
  check('citation renderer never treats quoted text as HTML',record.querySelector('img')===null&&record.textContent.includes('<img'));
  // A genuinely accepted Run loses delivery; changing UI values must preserve original retry body.
  dropRun=true;await $('internal-run-form').onsubmit({preventDefault(){}});
  check('lost acceptance delivery retains frozen retry intention',w.eval('engineeringPending.size')===1);
  term('internal-term','other-input');await load('initial-replay.json');
  const pendingBefore=JSON.parse(await action('counts'));await $('internal-retry').onclick();
  const pendingAfter=JSON.parse(await action('counts'));
  check('retry retains old term/Replay/key despite form changes',pendingAfter.internal_app_runs===pendingBefore.internal_app_runs&&w.eval('engineeringPending.size')===0);
  await action('worker');await w.eval(`showInternalInstance(${JSON.stringify(iid)})`);await wait(()=>$('internal-data').textContent.includes('历史结果 v2'));
  check('fresh accepted intent becomes independent result version 2',$('internal-data').textContent.includes('历史结果 v2'));
  dom.window.close();await create();await open(info.derived_app);await w.eval(`showInternalInstance(${JSON.stringify(iid)})`);
  check('new UI session reopens persisted history without rerunning',$('internal-data').querySelectorAll('.agent-result').length===2);
  term('app-agent-term',info.term_b);term('internal-term',info.term_b);await load('derived-replay.json');await prepare();
  w.eval('engineering.approval.expires_at=Date.now()/1000-1');$('internal-approval-ack').checked=true;$('internal-approval-ack').onchange();
  const count=calls.filter(c=>/\/commit$/.test(c.path)).length;$('internal-commit').click();
  check('expired approval cannot confirm or issue mutation',$('internal-commit').disabled&&calls.filter(c=>/\/commit$/.test(c.path)).length===count);
  holdApproval=true;const preparing=prepare();await wait(()=>!!releaseApproval);term('app-agent-term','changed-term');releaseApproval();releaseApproval=null;await preparing;
  check('late approval after input generation change cannot render or enable confirmation',$('internal-approval').hidden&&w.eval('engineering.approval')===null);
  // File read completion is also bound to current selection, not merely its filename.
  let completeFile;Object.defineProperty($('internal-replay-file'),'files',{configurable:true,value:[{size:10,text:()=>new Promise(r=>{completeFile=r;})}]});
  const loading=$('internal-replay-file').onchange();await open(info.csv_app);completeFile(fs.readFileSync(path.join(root,'derived-replay.json'),'utf8'));await loading;
  check('late file read cannot attach agent Replay to CSV app',w.eval('engineering.offlineReplay')===null&&$('internal-agent').hidden);
  fs.writeFileSync(path.join(root,'delay-app'),'1');const first=open(info.initial_app);await open(info.derived_app);await first;fs.unlinkSync(path.join(root,'delay-app'));
  check('late source app response cannot replace current candidate',w.eval('activeApp')===info.derived_app);
  fs.writeFileSync(path.join(root,'delay-app'),'1');const other=open(info.initial_app);$('project-select').value=info.other_project;w.eval('clearGoalCard()');await other;fs.unlinkSync(path.join(root,'delay-app'));
  check('late previous-project response cannot reveal source or internal panel',$('internal-panel').hidden&&$('app-manifest').textContent==='');
  $('project-select').value=info.project;await w.eval('refresh()');await open(info.derived_app);await action('corrupt');await $('internal-refresh').onclick();
  check('coordinated candidate corruption clears protected history/snapshots',$('internal-data').textContent===''&&$('app-manifest').textContent===''&&$('internal-status').dataset.state==='error');
  await open(info.initial_app);await action('revoke');await $('internal-refresh').onclick();
  check('revocation clears protected history and disables new content use',$('internal-data').textContent===''&&$('app-manifest').textContent===''&&$('internal-run-form').hidden);
  check('all UI actions create no new Grant',JSON.parse(await action('counts')).grants===info.grant_count);
  result.status='PASS';
 }catch(error){result.status='FAIL';result.error=error.stack;result.safeFixtureDiagnostic={runStatus:$('internal-run-status').textContent,status:$('internal-status').textContent,data:$('internal-data').textContent,view:w.eval('engineering && ({app:engineering.app,iid:engineering.instance?.id,instanceGeneration:engineering.instanceGeneration,runGeneration:engineering.runGeneration,busy:engineering.busy})')};process.exitCode=1;}
 finally{dom?.window.close();fs.writeFileSync(path.join(root,'dom-results.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));}
})();
