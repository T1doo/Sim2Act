'use strict';
// Independent offline qualifications; actual index/CSS/18 JS, native intervals unchanged.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const repo='/workspace/Sim2Act',out='/tmp/text-continuation-ui-independent-20261012/final-freeze-1426utc',web=path.join(repo,'src/sim2act/web');
const canon=v=>Array.isArray(v)?'['+v.map(canon).join(',')+']':v&&typeof v==='object'?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canon(v[k])).join(',')+'}':JSON.stringify(v);
const hash=v=>crypto.createHash('sha256').update(canon(v)).digest('hex');
const project='proj_'+'1'.repeat(32),otherProject='proj_'+'2'.repeat(32),iid='iinstance_'+'3'.repeat(32),key='original_cold_key';
const selected={id:iid,source_app_id:'app_'+'4'.repeat(32),principal_id:'user_'+'5'.repeat(32),runtime_id:'appruntime_'+'6'.repeat(32),fingerprint:'a'.repeat(64),source_implementation:'b'.repeat(64),target_implementation:'c'.repeat(64),release_fingerprint:'d'.repeat(64),revision:1,data_version:1,name:'Controlled old literal instance',requires_explicit_preflight:true};
const options={version:'literal-software-continuation.v1',project_id:project,items:[selected]};
const currentError={error:{code:'CONTROLLED_CURRENT_ERROR',message:'Synthetic current error'}};
const response=(v,status=200)=>new Response(JSON.stringify(v),{status,headers:{'Content-Type':'application/json'}});
const tick=()=>new Promise(setImmediate);
async function wait(fn){for(let n=0;n<200;n++){if(fn())return;await tick();}throw Error('controlled pending request not observed');}
function prepared(requestKey,term='Gamma'){
 const p={version:options.version,instance_id:iid,project_id:project,app_id:selected.source_app_id,principal_id:selected.principal_id,runtime_id:selected.runtime_id,candidate_fingerprint:selected.fingerprint,source_implementation:selected.source_implementation,target_implementation:selected.target_implementation,source_release_fingerprint:selected.release_fingerprint,revision:1,data_version:1,input:{term},data_preserved:true,new_grants:false,model_requests:0,semantic_status:'UNKNOWN',formal_publication_enabled:false};
 const request={expected_revision:1,expected_release_fingerprint:p.source_release_fingerprint,expected_candidate_fingerprint:p.candidate_fingerprint,expected_source_implementation:p.source_implementation,input:p.input,request_key:requestKey};
 const approval_id='iapproval_'+'7'.repeat(32),expires_at=Date.now()/1000+600;
 return {kind:'PREPARED',request_key:requestKey,preflight:p,approval_id,expires_at,approval_fingerprint:hash({continuation:p,request,approval_id,principal_id:p.principal_id,project_id:project,kind:'text_software_prepare',expires_at})};
}
function rehashPrepared(value){
 const p=value.preflight,request={expected_revision:p.revision,expected_release_fingerprint:p.source_release_fingerprint,expected_candidate_fingerprint:p.candidate_fingerprint,expected_source_implementation:p.source_implementation,input:p.input,request_key:value.request_key};
 value.approval_fingerprint=hash({continuation:p,request,approval_id:value.approval_id,principal_id:p.principal_id,project_id:p.project_id,kind:'text_software_prepare',expires_at:value.expires_at});return value;
}
async function boot(scenario){
 const html=fs.readFileSync(path.join(web,'index.html'),'utf8');
 fs.mkdirSync(path.join(out,'loaded-assets'),{recursive:true});fs.writeFileSync(path.join(out,'loaded-assets/index.html'),html);
 const dom=new JSDOM(html,{runScripts:'dangerously',url:'http://offline-controlled.invalid/',pretendToBeVisual:true}),w=dom.window;
 const requests=[],pending=[],assets=[{path:'index.html',sha256:crypto.createHash('sha256').update(html).digest('hex')}];
 Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.TextEncoder=TextEncoder;w.Response=Response;
 const css=fs.readFileSync(path.join(web,'app.css'),'utf8'),style=w.document.createElement('style');fs.writeFileSync(path.join(out,'loaded-assets/app.css'),css);style.textContent=css;w.document.head.append(style);assets.push({path:'app.css',sha256:crypto.createHash('sha256').update(css).digest('hex')});
 w.fetch=(url,opt={})=>{
  const entry={url:String(url),method:opt.method||'GET',authorization:opt.headers?.Authorization,body:opt.body?JSON.parse(opt.body):null};requests.push(entry);
  if(entry.url.includes('/software-continuation')){
   if(entry.url.endsWith('/software-continuation-options'))return Promise.resolve(response(options));
   return new Promise((resolve,reject)=>pending.push({entry,resolve:v=>resolve(v instanceof Response?v:response(v)),reject}));
  }
  if(entry.url==='/api/projects')return Promise.resolve(response([{id:project,name:'P1'},{id:otherProject,name:'P2'}]));
  if(entry.url==='/api/capabilities')return Promise.resolve(response({tools:[],code_execution:'DISABLED',connection:{model:'intern-s2',mode:'MOCK',status:'MOCK_ENGINEERING'}}));
  if(entry.url==='/health')return Promise.resolve(response({mode:'MOCK',api:'OK',worker:'MOCK'}));
  if(entry.url.includes('/resources')||entry.url.includes('/runs?')||entry.url.endsWith('/grants')||entry.url.endsWith('/goal-cards'))return Promise.resolve(response([]));
  return Promise.resolve(response({items:[]}));
 };
 for(const script of [...w.document.querySelectorAll('script[src]')]){
  const name=script.getAttribute('src').replace(/^\//,''),source=fs.readFileSync(path.join(web,name),'utf8');
  fs.writeFileSync(path.join(out,'loaded-assets',name),source);assets.push({path:name,sha256:crypto.createHash('sha256').update(source).digest('hex')});const node=w.document.createElement('script');node.textContent=source+'\n//# sourceURL='+name;w.document.body.append(node);
 }
 const $=id=>w.document.getElementById(id);
 $('project-select').replaceChildren(new w.Option('P1',project),new w.Option('P2',otherProject));$('project-select').value=project;
 w.eval("token='synthetic-offline-A';identityConnectionGeneration=1;");
 w.eval('globalThis.ctProbe={state:()=>textContinuation,pending:(s)=>textContinuationIntents.get(s),scope:()=>tcScope(),submit:(kind,recover)=>tcSubmit(kind,recover)};');
 await $('text-continuation-list').onclick();
 $('text-continuation-term').value='Gamma';$('text-continuation-term').dispatchEvent(new w.Event('input',{bubbles:true}));
 const scope=w.ctProbe.scope();
 return {scenario,dom,w,$,requests,pending,assets,scope,status:()=>$('text-continuation-status').textContent,proof:()=>$('text-continuation-proof').textContent};
}
function editABA(b){const el=b.$('text-continuation-term'),old=el.value;el.value='EDIT';el.dispatchEvent(new b.w.InputEvent('input',{bubbles:true,inputType:'insertText',data:'EDIT'}));el.value=old;el.dispatchEvent(new b.w.InputEvent('input',{bubbles:true,inputType:'historyUndo',data:null}));}
async function changeContext(b,kind){
 if(kind==='identity'||kind==='connection'){b.$('token').value=kind==='identity'?'synthetic-offline-B':'synthetic-offline-A';await b.$('connect').onclick();}
 else if(kind==='project'){b.$('project-select').value=otherProject;await b.$('project-select').onchange();}
 else if(kind==='workspace'){b.w.document.querySelector('#workspace-nav [data-tab=apps]').onclick();}
 else editABA(b);
}
async function previewToGet(b){
 const call=b.$('text-continuation-preview').onclick();await wait(()=>b.pending.length===1);b.pending[0].resolve({accepted:true});await wait(()=>b.pending.length===2);return {call};
}
const scenarios=[...['identity','connection','project','workspace','edit'].map(k=>'late-post-'+k),'late-get-success-edit-aba','late-get-error-edit-aba','cold-wrong-key','cold-old-release-fp','current-post-error','current-get-error','valid-current-preflight'];
(async()=>{
 const results=[];
 for(const scenario of scenarios){let b,checks={},error=null,status='FAIL';
  try{
   b=await boot(scenario);assert.equal(b.assets.length,20);assert.equal(b.pending.length,0);
   if(scenario.startsWith('late-post-')){
    const call=b.$('text-continuation-preview').onclick();await wait(()=>b.pending.length===1);const intent=b.w.ctProbe.pending(b.scope),marker=b.requests.length;
    await changeContext(b,scenario.slice('late-post-'.length));const before={status:b.status(),proof:b.proof()};b.pending[0].resolve({accepted:true});await call;
    const follow=b.requests.slice(marker).filter(r=>r.url.includes(iid)&&r.method==='GET');
    checks={no_old_iid_key_followup_get:follow.length===0,no_get_with_new_global_identity:!follow.some(r=>r.authorization==='Bearer synthetic-offline-B'),pending_exact_object_retained:b.w.ctProbe.pending(b.scope)===intent,status_not_painted:b.status()===before.status,proof_not_painted:b.proof()===before.proof};
   }else if(scenario.startsWith('late-get-')){
    const {call}=await previewToGet(b),intent=b.w.ctProbe.pending(b.scope);
    editABA(b);const before={status:b.status(),proof:b.proof()};
    if(scenario==='late-get-success-edit-aba')b.pending[1].resolve(prepared(intent.key));else b.pending[1].resolve(response(currentError,409));await call;
    checks={old_success_or_error_not_painted:b.status()===before.status,proof_not_painted:b.proof()===before.proof,pending_exact_object_retained:b.w.ctProbe.pending(b.scope)===intent,no_preflight_installed:b.w.ctProbe.state()?.preflight===null,no_retry_post:b.requests.filter(r=>r.method==='POST').length===1};
   }else if(scenario.startsWith('cold-')){
    b.$('text-continuation-key').value=key;const call=b.$('text-continuation-recover').onclick();await wait(()=>b.pending.length===1);
    const value=prepared(scenario==='cold-wrong-key'?'other_key':key);
    if(scenario==='cold-old-release-fp'){value.preflight.source_release_fingerprint='e'.repeat(64);rehashPrepared(value);}
    b.pending[0].resolve(value);await call;
    checks={qualified_mismatch_rejected:b.status().includes('VERSION_CONFLICT'),preflight_not_installed:b.w.ctProbe.state()?.preflight===null,receipt_not_installed:b.w.ctProbe.state()?.receipt===null,no_post:b.requests.every(r=>r.method==='GET'),cold_key_retained:b.$('text-continuation-key').value===key};
   }else{
    const call=b.$('text-continuation-preview').onclick();await wait(()=>b.pending.length===1);const intent=b.w.ctProbe.pending(b.scope);
    if(scenario==='current-post-error')b.pending[0].resolve(response(currentError,409));
    else{b.pending[0].resolve({accepted:true});await wait(()=>b.pending.length===2);if(scenario==='current-get-error')b.pending[1].resolve(response(currentError,409));else b.pending[1].resolve(prepared(intent.key));}
    await call;
    checks=scenario==='valid-current-preflight'?{real_hash_preflight_installed:!!b.w.ctProbe.state()?.preflight,qualified_state_visible:b.status().includes('精确预检'),original_pending_cleared:b.w.ctProbe.pending(b.scope)===undefined,confirmation_still_required:b.$('text-continuation-commit').disabled}: {qualified_current_error_visible:b.status().includes('CONTROLLED_CURRENT_ERROR'),original_pending_retained:b.w.ctProbe.pending(b.scope)===intent,original_key_retained:b.$('text-continuation-key').value===intent.key,no_retry_post:b.requests.filter(r=>r.method==='POST').length===1};
   }
   status=Object.values(checks).every(Boolean)&&Object.keys(checks).length?'PASS':'FAIL';
  }catch(e){error=e.stack||String(e);}
  const result={scenario,status,checks,error,requests:b?.requests,assets:b?.assets,classification:'CONTROLLED_OFFLINE_ACTUAL_INDEX_CSS_ALL_18_SCRIPTS_REAL_CANONICAL_SHA256',http:'NOT_RUN',worker:'NOT_RUN',native:'NOT_RUN',native_undo:'NOT_RUN',product_intervals:'UNMODIFIED',real_model:'NOT_RUN',cancelled_install_goal:'PERMANENT_NOT_VERIFIED; NOT_RUN'};
  fs.writeFileSync(path.join(out,scenario+'.json'),JSON.stringify(result,null,2));results.push({scenario,status,error});b?.dom.window.close();
 }
 fs.writeFileSync(path.join(out,'controlled-results.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));if(results.some(r=>r.status!=='PASS'))process.exitCode=1;
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
