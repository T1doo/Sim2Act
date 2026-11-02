'use strict';
// Actual delivered UI/controller; typed resource wire, no real model/PG/HTTP requests.
const fs=require('fs'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{JSDOM,VirtualConsole}=require('jsdom');
const source=fs.readFileSync('src/sim2act/web/app.js','utf8'),html=fs.readFileSync('src/sim2act/web/index.html','utf8'),checks=[];
const rid='res_'+'a'.repeat(32),content='A😀中文原文\r\n保留第二行。',hash=crypto.createHash('sha256').update(content).digest('hex'),material={id:rid,project_id:'p1',name:'片段原文.md',format:'md',hash,content};
const tick=()=>new Promise(r=>setTimeout(r,0));const check=(value,name)=>{assert(value,name);checks.push(name);};
async function page(){const errors=[],requests=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));const dom=new JSDOM(html,{url:'https://fragment.invalid/',runScripts:'outside-only',virtualConsole:vc}),w=dom.window,d=w.document;
 w.matchMedia=()=>({matches:false,addEventListener(){}});w.TextEncoder=TextEncoder;w.HTMLElement.prototype.scrollIntoView=function(){};w.setInterval=()=>0;Object.defineProperty(w.crypto,'subtle',{value:crypto.webcrypto.subtle});w.crypto.randomUUID=crypto.randomUUID;
 let fault='',hold=false,release,reached;
 w.fetch=async(path,options={})=>{const request={path,method:options.method||'GET',body:options.body&&JSON.parse(options.body)};requests.push(request);
  if(path==='/api/resources/'+rid){if(hold){hold=false;reached?.();await new Promise(r=>release=r);}if(fault==='403')return{ok:false,status:403,json:async()=>({error:{code:'PERMISSION_DENIED'}})};const data=fault==='hash'?{...material,content:content+'changed',hash:'b'.repeat(64)}:{...material};return{ok:true,status:200,json:async()=>data};}
  if(request.method==='POST'&&path==='/api/projects/p1/runs')return{ok:true,status:202,json:async()=>{throw Error('Controlled uncertain accepted response')}};
  return{ok:false,status:503,json:async()=>({error:{code:'CONTROLLED_OFFLINE'}})};};
 w.eval(source+`\nwindow.fragmentTest={start(){token='synthetic-fragment';identityConnectionGeneration++;},updateOrdinaryRunMaterials,previewResource,resourceDownloadContext,submitOrdinaryRun,downloadResource,clearFrontendRun,entry:runSubmissionEntry,fragment(){return frontendFragmentDraft;}};`);
 await tick();const api=w.fragmentTest;api.start();d.getElementById('project-select').append(new w.Option('项目','p1',true,true));api.updateOrdinaryRunMaterials([material]);await api.previewResource(material,api.resourceDownloadContext());
 const select=(start=1,end=5,cross=false)=>{const pre=d.getElementById('resource-preview'),range=d.createRange();range.setStart(pre.firstChild,start);if(cross){const other=d.createTextNode('other');d.body.append(other);range.setEnd(other,2);}else range.setEnd(pre.firstChild,end);const selection=w.getSelection();selection.removeAllRanges();selection.addRange(range);d.querySelector('#frontend-fragment-source button').click();};
 return{w,d,api,requests,errors,select,posts:()=>requests.filter(r=>r.method==='POST'),fault:v=>fault=v,hold:()=>{hold=true;return new Promise(r=>reached=r)},release:()=>release(),close:()=>dom.window.close()};}
(async()=>{
 for(const scenario of ['normal','goal-ABA','materials-ABA','version','revoke','revoke-ABA','cancel-pending','preview-revoke','download-revoke','cross-range','surrogate','too-long']){
  const p=await page();try{
   p.select(scenario==='surrogate'?2:1,scenario==='surrogate'?3:5,scenario==='cross-range');
   if(['cross-range','surrogate'].includes(scenario)){check(!p.api.fragment()&&p.posts().length===0,scenario+' never creates a bound draft or Run');continue;}
   p.api.clearFrontendRun();check(!p.api.fragment()||p.d.getElementById('frontend-object-context').textContent.includes(hash),scenario+' keeps bound context visible after result/history clearing');
   check(p.api.fragment()?.text===content.slice(1,5)&&p.api.fragment().hash===hash,scenario+' binds original ID/hash/exact UTF-16 slice');p.d.getElementById('goal').value=scenario==='too-long'?'长'.repeat(3990):'只解释选中原文';
   if(['preview-revoke','download-revoke'].includes(scenario)){
    p.fault('403');try{if(scenario==='preview-revoke')await p.api.previewResource(material,p.api.resourceDownloadContext());else await p.api.downloadResource(material,p.api.resourceDownloadContext(),p.d.createElement('button'));}catch(e){assert.equal(e.httpStatus,403);}
    check(!p.api.fragment()&&p.d.getElementById('resource-preview').hidden&&!p.d.getElementById('frontend-resource-reading'),scenario+' clears previously bound private source on a definite read denial');
    check(p.d.getElementById('goal').value==='只解释选中原文'&&p.posts().length===0,scenario+' preserves instruction and creates no Run');
   }else if(scenario==='cancel-pending'){
    const held=p.hold(),old=p.api.submitOrdinaryRun();await held;[...p.d.querySelectorAll('#frontend-object-context button')].find(b=>b.textContent==='移除此片段引用').click();
    check(!p.d.getElementById('run-submit').disabled&&!p.api.fragment(),'explicit removal unlocks a draft while the old readonly GET remains pending');
    await p.api.submitOrdinaryRun();check(p.posts().length===1&&!p.posts()[0].body.goal.includes('original_text'),'new ordinary intent can submit without the removed fragment');
    p.release();let failure;try{await old;}catch(e){failure=e;}check(!!failure&&p.posts().length===1&&p.api.entry().body.goal==='只解释选中原文','late invalidated preflight cannot submit or overwrite the newer intent');
   }else if(scenario==='normal'){
    const held=p.hold(),first=p.api.submitOrdinaryRun(),second=p.api.submitOrdinaryRun();await held;check(p.d.getElementById('run-submit').disabled&&p.posts().length===0,'preflight is readonly and duplicate submission stays blocked');p.release();await Promise.all([first,second]);
    check(p.posts().length===1&&p.posts()[0].body.resource_refs.length===1&&p.posts()[0].body.resource_refs[0]===rid,'one explicit original endpoint submission keeps the selected resource binding');
    const body=p.posts()[0].body;check(body.goal.includes(hash)&&body.goal.includes('UTF-16')&&body.goal.includes('original_text')&&body.goal.includes('😀中文')&&p.api.entry().state==='unknown','unknown acceptance preserves exact selected context in original frozen intent');const before=p.requests.length;p.d.getElementById('frontend-pref-theme').value='dark';p.d.getElementById('frontend-pref-theme').dispatchEvent(new p.w.Event('change'));check(p.requests.length===before&&p.api.entry().body.request_key===body.request_key,'appearance does not recreate a fragment submission or original key');
   }else{
    let work;
    if(scenario.endsWith('ABA')){const held=p.hold();work=p.api.submitOrdinaryRun();await held;if(scenario==='revoke-ABA')p.fault('403');if(scenario==='goal-ABA'||scenario==='revoke-ABA'){const input=p.d.getElementById('goal'),original=input.value;input.value='edited';input.dispatchEvent(new p.w.Event('input',{bubbles:true}));input.value=original;input.dispatchEvent(new p.w.Event('input',{bubbles:true}));}else{const option=p.d.getElementById('run-materials').options[0];option.selected=false;p.d.getElementById('run-materials').dispatchEvent(new p.w.Event('change',{bubbles:true}));option.selected=true;p.d.getElementById('run-materials').dispatchEvent(new p.w.Event('change',{bubbles:true}));}p.release();}
    else{if(scenario==='version')p.fault('hash');if(scenario==='revoke')p.fault('403');work=p.api.submitOrdinaryRun();}
    let failure;try{await work;}catch(e){failure=e;}
    check(!!failure&&p.posts().length===0,scenario+' preflight rejects before any Run mutation');
    check(p.d.getElementById('goal').value===(scenario==='too-long'?'长'.repeat(3990):'只解释选中原文'),scenario+' preserves the user instruction without truncation');
    if(scenario.startsWith('revoke'))check(!p.api.fragment()&&p.d.getElementById('resource-preview').hidden&&!p.d.getElementById('frontend-resource-reading'),'read revocation clears private fragment/raw projection');
   }
   check(!p.errors.length,scenario+' has no uncaught UI errors');
  }finally{p.close();}
 }
 console.log(JSON.stringify({status:'PASS',scope:'CONTROLLED_DELIVERED_FRAGMENT_UI_NO_REAL_HTTP_MODEL_OR_PG',checks,scenarios:12,live_model_requests:0,pg_operations:0},null,2));
})().catch(e=>{console.error(e.stack);process.exitCode=1});
