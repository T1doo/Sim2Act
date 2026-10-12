"use strict";
// Controlled local-source JSDOM promises; real canonical SHA256, no HTTP/Worker/native.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{JSDOM}=require('jsdom');
const scenario=process.argv[2],sourcePath=process.argv[3],outputPath=process.argv[4],base=process.argv[5]||path.dirname(sourcePath);
const scenarios=['old-success-after-new-success','old-failure-after-new-success','initial-failure-after-edit-aba','initial-catch-edit-aba','initial-catch-new-read','refresh-catch-new-read','recover-catch-new-read','save-readback-catch-new-read','current-initial-failure','current-refresh-failure','success-after-edit-aba'];
assert(scenarios.includes(scenario));
const source=fs.readFileSync(sourcePath,'utf8'),internal=fs.readFileSync(path.join(base,'internal.js'),'utf8');
const dom=new JSDOM(fs.readFileSync(path.join(base,'index.html'),'utf8'),{runScripts:'outside-only',url:'http://controlled.invalid/'}),w=dom.window;
const canonical=v=>Array.isArray(v)?'['+v.map(canonical).join(',')+']':v&&typeof v==='object'?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}':JSON.stringify(v);
const hash=v=>crypto.createHash('sha256').update(canonical(v)).digest('hex');
w.$=id=>w.document.getElementById(id);w.safe=fn=>fn;w.token='synthetic';w.activeApp='controlled-app';w.appSelectionGeneration=9;w.workspaceSelectionGeneration=3;w.TextEncoder=TextEncoder;
Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.goalRunCanonical=canonical;
w.$('project-select').append(new w.Option('project','controlled-project'));w.$('project-select').value='controlled-project';
w.engineering={token:w.token,project:'controlled-project',app:w.activeApp,appGeneration:9,instance:null,draft:{runtime_id:'controlled-runtime',fingerprint:'a'.repeat(64),candidate:{task_proof:{proof:{kind:'authorized_data_free_text_logic.v1'}},manifest:{data_bindings:[{resource_ref:'controlled-resource'}]}}}};
w.pending=[];w.events=[];
w.eval("globalThis.api=(url,method='GET',body)=>new Promise((resolve,reject)=>{pending.push({resolve,reject,url,method,body});events.push(method+' '+pending.length);});");
w.eval(internal.match(/function engineeringCurrent\(view\) \{[\s\S]*?\n\}/)[0]+'\n'+source+'\n'+`globalThis.probe={initial:()=>openAppOwnGoal(engineering),read:()=>appOwnGoalRead(appOwnGoalView),generation:()=>appOwnGoalView.readGeneration,state:()=>appOwnGoalView.state,pending:()=>appOwnGoalPending.get(appOwnGoalKey(appOwnGoalView)),seed:()=>appOwnGoalPending.set(appOwnGoalKey(appOwnGoalView),{request_key:'original-key',intent:'preserve'}),edit:()=>appOwnGoalEdit};`);
const anchor={app_id:'controlled-app',owner_id:'controlled-principal',project_id:'controlled-project',runtime_id:'controlled-runtime',candidate_fingerprint:'a'.repeat(64),resource_id:'controlled-resource',source_hash:'b'.repeat(64),logic_id:'controlled-logic',logic_fingerprint:'c'.repeat(64)};
const receipts=[];
function state(version){while(receipts.length<version){const n=receipts.length+1,content={title:'Own title '+n,goal:'Own goal '+n,known:['known'],assumptions:['assumption'],unresolved:['semantic unknown'],constraints:['literal'],acceptance_checks:['inspect'],resource_refs:[anchor.resource_id]},snapshot={schema_version:'F2-goal-card.v1',content,resource_snapshots:[{resource_id:anchor.resource_id,hash:anchor.source_hash,format:'md'}]},receipt={namespace:'app-owned-text-goal.v1',anchor,card_id:'controlled-card',goal_version:n,goal_fingerprint:hash(snapshot),snapshot,applicability:['scope '+n],sequence:n,previous_binding_fingerprint:receipts.at(-1)?.binding_fingerprint||null,request_key:'goal-'+n,request_fingerprint:hash({goal:n})};receipt.binding_fingerprint=hash(receipt);receipts.push(receipt);}
 const latest=receipts[version-1];return {namespace:'app-owned-text-goal.v1',anchor,sequence:version,head:{card_id:latest.card_id,version,fingerprint:latest.goal_fingerprint,title:latest.snapshot.content.title},binding_fingerprint:latest.binding_fingerprint,current:latest,status:'CURRENT',history:receipts.slice(0,version).map(r=>Object.fromEntries(['request_key','sequence','card_id','goal_version','goal_fingerprint','binding_fingerprint'].map(k=>[k,r[k]]))),owner_acceptance:'PENDING',technical_semantic_status:'UNKNOWN',formal_publication_enabled:false,model_requests:0};}
const status=()=>w.$('app-own-goal-status').textContent;
const editABA=()=>{const el=w.$('app-own-goal-goal'),old=el.value;el.value='EDIT';el.dispatchEvent(new w.InputEvent('input',{bubbles:true,inputType:'insertText',data:'EDIT'}));el.value=old;el.dispatchEvent(new w.InputEvent('input',{bubbles:true,inputType:'historyUndo',data:null}));w.events.push('edit ABA');};
const tick=()=>new Promise(setImmediate);
(async()=>{let result='FAIL',error=null,checks={},expected,afterOld,oldGeneration,newGeneration,initialHash,pendingBefore;
 try{
  const opening=w.probe.initial();assert.equal(w.pending.length,1);assert.equal(w.pending[0].method,'GET');
  if(['old-success-after-new-success','old-failure-after-new-success'].includes(scenario)){
   assert.equal(w.$('app-own-goal-read').disabled,false,'initial read allows another explicit GET');
   const newer=w.$('app-own-goal-read').onclick();assert.equal(w.pending.length,2);w.pending[1].resolve(state(2));await newer;expected=status();initialHash=hash(w.probe.state());oldGeneration=1;
   if(scenario.startsWith('old-success'))w.pending[0].resolve(state(1));else w.pending[0].reject(Error('OLD ERROR'));
   await opening;afterOld=status();checks={new_current_status_kept:afterOld===expected,new_current_state_kept:hash(w.probe.state())===initialHash,read_generation_exact:w.probe.generation()===2,no_post:w.pending.every(p=>p.method==='GET')};
  }else if(['initial-failure-after-edit-aba','success-after-edit-aba','initial-catch-edit-aba','initial-catch-new-read','current-initial-failure'].includes(scenario)){
   expected=status();oldGeneration=w.probe.generation();const oldEdit=w.probe.edit();let newer;
   if(scenario.includes('after-edit'))editABA();
   if(scenario==='success-after-edit-aba')w.pending[0].resolve(state(1));else w.pending[0].reject(Error('OLD ERROR'));
   if(scenario==='initial-catch-edit-aba')queueMicrotask(editABA);
   if(scenario==='initial-catch-new-read')queueMicrotask(()=>{newer=w.probe.read();w.events.push('new GET between catches');});
   await opening;afterOld=status();checks={status_valid:scenario==='current-initial-failure'?afterOld.includes('OLD ERROR'):afterOld===expected,old_state_not_installed:w.probe.state()===null,edit_generation_exact:w.probe.edit()===oldEdit+(scenario.includes('edit-aba')?2:0),read_generation_exact:w.probe.generation()===oldGeneration+(newer?1:0),no_post:w.pending.every(p=>p.method==='GET')};
   if(newer){w.pending[1].resolve(state(2));await newer;checks.new_current_installed=w.probe.state()?.head.version===2;}
  }else{
   w.pending[0].resolve(state(1));await opening;expected=status();initialHash=hash(w.probe.state());let caller,index=1,newer;
   if(scenario==='recover-catch-new-read'){w.probe.seed();w.$('app-own-goal-key').value='original-key';caller=w.$('app-own-goal-recover').onclick();}
   else if(scenario==='save-readback-catch-new-read'){
    for(const f of ['title','goal','known','assumptions','unresolved','constraints','acceptance_checks','applicability'])w.$('app-own-goal-'+f).value='explicit '+f;
    w.$('app-own-goal-ack').checked=true;caller=w.$('app-own-goal-form').onsubmit({preventDefault(){}});assert.equal(w.pending[1].method,'POST');w.pending[1].resolve({accepted:true});
    for(let n=0;w.pending.length<3&&n<30;n++)await tick();assert.equal(w.pending.length,3);index=2;
   }else caller=w.$('app-own-goal-read').onclick();
   assert.equal(w.pending[index].method,'GET');pendingBefore=JSON.stringify(w.probe.pending());oldGeneration=w.probe.generation();
   const e=Error('OLD ERROR');if(scenario==='save-readback-catch-new-read')e.httpStatus=409;w.pending[index].reject(e);
   if(scenario!=='current-refresh-failure')queueMicrotask(()=>{newer=w.probe.read();w.events.push('new GET between catches');});
   await caller;afterOld=status();checks={status_valid:scenario==='current-refresh-failure'?afterOld.includes('OLD ERROR'):afterOld===expected,current_state_not_cleared:hash(w.probe.state())===initialHash,pending_identity_kept:JSON.stringify(w.probe.pending())===pendingBefore,read_generation_exact:w.probe.generation()===oldGeneration+(newer?1:0),post_count_exact:w.pending.filter(p=>p.method==='POST').length===(scenario==='save-readback-catch-new-read'?1:0)};
   if(newer){w.pending.at(-1).resolve(state(2));await newer;checks.new_current_installed=w.probe.state()?.head.version===2;checks.pending_after_new_get_kept=JSON.stringify(w.probe.pending())===pendingBefore;}
  }
  newGeneration=w.probe.generation();result=Object.values(checks).every(Boolean)?'PASS':'FAIL';
 }catch(e){error=e.stack;process.stderr.write(error+'\n');}
 const proof={status:result,scenario,checks,error,expected_status:expected,status_after_old:afterOld,final_status:status(),old_generation:oldGeneration,new_generation:newGeneration,events:w.events,requests:w.pending.map(p=>({url:p.url,method:p.method,body:p.body})),source_sha256:crypto.createHash('sha256').update(source).digest('hex'),classification:'CONTROLLED_LOCAL_SOURCE_JSDOM_REAL_SHA256',http:'NOT_RUN',worker:'NOT_RUN',native_browser:'NOT_RUN',native_undo:'NOT_RUN',real_model:'NOT_RUN',real_human_semantics:'NOT_RUN'};
 fs.writeFileSync(outputPath,JSON.stringify(proof,null,2)+'\n');dom.window.close();console.log(JSON.stringify({scenario,status:result,checks}));assert.equal(result,'PASS','late owned Goal read cannot overwrite qualified state/error summary');
})().catch(e=>{console.error(e.stack);dom.window.close();process.exitCode=1;});
