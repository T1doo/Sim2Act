'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),trace=[],checks=[],hashes={};let dom,w,$,holdPost=false,releasePost,damage=false,releaseBad,badArrived=false;
const verify=(v,message)=>{assert(v,message);checks.push(message)};
const until=async predicate=>{const deadline=Date.now()+6000;while(Date.now()<deadline){if(predicate())return;await new Promise(resolve=>setTimeout(resolve,10))}throw Error('independent six-second idle budget exceeded')};
const proposal=()=>w.document.querySelector('.report-presentation-propose');
const confirm=()=>w.document.querySelector('.report-presentation-confirm');
const postCount=()=>trace.filter(x=>x.method==='POST').length;
const pending=()=>w.eval('[...presentationIntents.values()][0]');
async function connect(identity){$('token').value=identity;await $('connect').onclick()}
(async()=>{try{
 const html=await(await fetch(info.url)).text();hashes['index.html']=crypto.createHash('sha256').update(html).digest('hex');dom=new JSDOM(html,{url:info.url,runScripts:'dangerously'});w=dom.window;$=id=>w.document.getElementById(id);
 w.setInterval=()=>0;w.TextEncoder=TextEncoder;Object.defineProperty(w.crypto,'subtle',{value:crypto.webcrypto.subtle});
 w.fetch=async(url,options={})=>{
  const target=new URL(url,info.url);assert.equal(target.origin,info.url);
  const request={method:options.method||'GET',path:target.pathname,body:options.body?JSON.parse(options.body):null};trace.push(request);
  const response=await fetch(target,options);request.status=response.status;
  const suffix=info.phase==='definition'?'/report-presentations':'/checks';
  if(holdPost&&request.method==='POST'&&request.path.endsWith(suffix)){
   holdPost=false;verify(response.status===201,'target original API accepted actual immutable receipt before controlled reply loss');
   request.reply='held-then-lost-accepted';await new Promise(resolve=>releasePost=resolve);releasePost=null;throw Error('independent accepted receipt transport loss');
  }
  const canonical=request.path===`/api/projects/${info.project}/apps/${info.app}/history`;
  const presentation=request.path.endsWith('/report-presentations');
  if(damage&&request.method==='GET'&&(info.branch==='canonical'?canonical:presentation)){
   damage=false;verify(response.status===200,'damaged proof starts as successful real HTTP200 JSON response');
   const value=await response.json();
   if(info.branch==='canonical')value.runtime_id='appruntime_'+ '0'.repeat(32);
   else if(info.branch==='envelope')value.namespace='invalid-independent-history-envelope';
   else {verify(value.items.length>0,'accepted real history item exists before item proof corruption');value.items[0].patch.result_binding.run_id='run_'+'0'.repeat(32)}
   request.reply='controlled-valid-JSON-invalid-proof';
   if(info.navigation!=='current'){badArrived=true;await new Promise(resolve=>releaseBad=resolve);releaseBad=null}
   return new Response(JSON.stringify(value),{status:200,headers:{'Content-Type':'application/json'}});
  }
  return response;
 };
 for(const file of Array.from(w.document.querySelectorAll('script[src]')).map(s=>s.getAttribute('src').slice(1))){const code=await(await fetch(info.url+'/'+file)).text();hashes[file]=crypto.createHash('sha256').update(code).digest('hex');const element=w.document.createElement('script');element.textContent=code;w.document.body.append(element)}
 await connect('synthetic-test-A');verify($('project-select').value===info.project,'actual owner connection selects original project');await w.showApp(info.app);
 verify(!!proposal()&&!proposal().disabled,'actual archived Report page exposes original presentation proposal');
 if(info.phase==='checks'){await proposal().onclick();verify(!!confirm()&&!confirm().hidden&&!confirm().disabled,'actual proposal persisted and requires explicit version check')}
 holdPost=true;const action=(info.phase==='definition'?proposal():confirm()).onclick();await until(()=>!!releasePost);
 const accepted=trace.findLast(r=>r.method==='POST'&&r.reply==='held-then-lost-accepted');const frozen=JSON.stringify(accepted.body);
 await w.showApp(info.app);verify(!w.eval('manifestContext===null'),'same app reopened creates a fresh current manifest context');
 damage=true;releasePost();
 if(info.navigation!=='current'){
  await until(()=>badArrived&&!!releaseBad);
  if(info.navigation==='app'){await w.showApp(info.peer);verify(w.eval('activeApp')===info.peer,'real app navigation selects independent CSV peer')}
  else {await connect('synthetic-test-B');verify($('project-select').value===info.other&&w.eval('token')==='synthetic-test-B','real reconnect selects independent identity/project')}
  $('error').textContent='independent new-context sentinel';releaseBad();await action;
  verify($('error').textContent==='independent new-context sentinel','late invalid history cannot overwrite new context feedback');
  verify(info.navigation==='app'?w.eval('activeApp')===info.peer:w.eval('token')==='synthetic-test-B','late invalid history cannot clear or replace new app or identity');
 }else{
  await action;verify(w.eval('manifestContext===null&&activeApp===null')&&$('app-history').childElementCount===0,'invalid current history clears canonical and presentation evidence');
 }
 const intent=pending();verify(!!intent&&!intent.busy,'original UNKNOWN intent survives proof failure with busy released');
 verify(info.phase==='definition'?JSON.stringify(intent.body)===frozen:JSON.stringify({expected_patch_fingerprint:intent.patch.patch_fingerprint,request_key:intent.checkKey})===frozen,'original frozen accepted request key and body preserved');
 if(info.navigation==='current')verify($('error').textContent.includes('VERSION_CONFLICT')&&$('error').textContent.includes('当前展示回读失败'),'precise current self-cleared feedback visible after invalid successful JSON proof');
 const writes=postCount();if(info.navigation==='identity')await connect('synthetic-test-A');await w.showApp(info.app);
 verify(postCount()===writes,'normal authorized history restores immutable acceptance without any POST');
 verify(!!pending().patch&&pending().patch.request_key===pending().definitionKey,'history restores exact accepted presentation definition key');
 if(info.phase==='checks')verify(!!pending().checked&&pending().checked.request_key===pending().checkKey&&w.document.querySelector('.report-view-text')&&$('app-history').textContent.includes(info.explanation),'current history restores exact checked key and safe archived text');
 else verify(!!confirm()&&!confirm().hidden&&!confirm().disabled,'recovered definition still requires explicit version-check action');
 verify(postCount()===writes,'recovery leaves all business submission controls unexecuted');
 fs.writeFileSync(info.evidence,JSON.stringify({status:'PASS',checks,trace,hashes,native:'NOT_RUN',idle_budget_seconds:6},null,2));console.log(JSON.stringify({status:'PASS',checks:checks.length}));
 }catch(error){fs.writeFileSync(info.evidence,JSON.stringify({status:'FAIL',error:error.stack,checks,trace,hashes},null,2));console.error(error.stack);process.exitCode=1}
 finally{dom?.window.close()}
})();
