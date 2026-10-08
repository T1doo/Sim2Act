'use strict';
const fs=require('node:fs'),vm=require('node:vm'),crypto=require('node:crypto'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const src=process.argv[2],out=process.argv[3],dom=new JSDOM(fs.readFileSync(src+'/src/sim2act/web/index.html','utf8'),{runScripts:'outside-only'}),w=dom.window;
const sample=JSON.parse(fs.readFileSync(process.argv[4])),fp=sample.card.fingerprint,aid=sample.session_id,gid=sample.card.id,pid=sample.list.project_id,calls=[],checks=[];
w.TextEncoder=TextEncoder;Object.defineProperty(w.crypto,'subtle',{value:crypto.webcrypto.subtle});w.crypto.randomUUID=crypto.randomUUID;w.token='identityA';w.activeGoalCard=sample.card;w.goalCardLoading=false;w.goalCardSaving=false;w.activeRun=null;w.runSelectionGeneration=0;w.runUserSelectionGeneration=0;w.$=id=>w.document.getElementById(id);w.safe=fn=>fn;w.clearRunDetail=()=>{};w.goalRunCanonical=x=>JSON.stringify((function sort(v){return Array.isArray(v)?v.map(sort):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,sort(v[k])])):v;})(x));w.row=text=>{const n=w.document.createElement('p');n.textContent=text;return n;};
const select=w.$('project-select');select.append(new w.Option('current',pid),new w.Option('other','other'));select.value=pid;
let list=structuredClone(sample.list);
let held=null,hold=false;
w.api=async(path,method='GET',body)=>{calls.push({path,method,body});if(method==='POST'){const e=Error('owned lost or late422');if(calls.filter(c=>c.method==='POST').length>1)e.httpStatus=422;throw e;}if(hold){hold=false;return await new Promise(resolve=>held=()=>resolve(structuredClone(list)));}return structuredClone(list);};
vm.runInContext(fs.readFileSync(src+'/src/sim2act/web/natural-goal.js','utf8'),dom.getInternalVMContext());
function check(ok,label){assert.ok(ok,label);checks.push(label);}
(async()=>{try{
 await w.refreshNaturalActivations();w.$('natural-activation-select').value=aid;w.$('natural-activation-select').onchange();await w.generateNaturalGoal();const first=calls.find(c=>c.method==='POST');check(w.eval('naturalGoalRequests.get(naturalGoalKey()).state')==='unknown','lost acceptance stays UNKNOWN');
 w.$('natural-activation-select').value='';w.$('natural-activation-select').onchange();check(w.eval('naturalGoalAcknowledgements.size')===0&&w.activeRun===null,'selection change clears current confirmation/run');w.$('natural-activation-select').value=aid;w.$('natural-activation-select').onchange();await w.generateNaturalGoal(true);const second=calls.filter(c=>c.method==='POST')[1];check(JSON.stringify(first)===JSON.stringify(second),'recovery uses exact original activation endpoint/body/key');check(w.eval('naturalGoalRequests.get(naturalGoalKey()).state')==='unknown','late422 after UNKNOWN cannot unlock intent');const n=calls.length;await w.generateNaturalGoal();check(calls.length===n,'new send blocked while original unknown');
 hold=true;const p=w.refreshNaturalActivations();await Promise.resolve();select.value='other';w.clearNaturalGoal();held();await p;check(w.eval('naturalActivationSelection===null')&&!w.$('natural-activation-goals').textContent,'late list cannot restore prior project');
 select.value=pid;
 const variants=[['version',r=>r.scope.version='forged-scope'],['rpm',r=>r.scope.caps.rpm=30],['output',r=>r.scope.caps.output_tokens=4096],['goal-version-bool',r=>r.scope.goals[0].expected_version=true],['resource-id',r=>r.scope.goals[0].resource_id='resource_'+'a'.repeat(32)],['snapshot',r=>r.scope.goals[0].snapshot.content.goal='changed'],['scope-fp',r=>r.scope_fingerprint='a'.repeat(64)],['approval',r=>r.approval.expires_at+=1]];
 for(const [name,mutate]of variants){list=structuredClone(sample.list);mutate(list.items[0]);await w.refreshNaturalActivations();check(w.eval('naturalActivationBlocked')&&w.$('natural-activation-select').options.length===1&&!w.$('natural-activation-goals').textContent,'bad '+name+' rejected and clears selectable scope');}
 const forged={blocked:w.eval('naturalActivationBlocked'),selectable:false};

 fs.writeFileSync(out,JSON.stringify({status:'PASS_SHAPE_CORRECTION',checks,forged_scope_projection:forged,source_sha256:crypto.createHash('sha256').update(fs.readFileSync(src+'/src/sim2act/web/natural-goal.js')).digest('hex'),transport:'CONTROLLED_DOM_ONLY',network:0},null,2));
 }catch(e){console.error(e.stack);process.exitCode=1;}finally{dom.window.close();}})();
