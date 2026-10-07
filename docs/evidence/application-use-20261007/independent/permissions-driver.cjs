'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const root=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(root,'info.json'))),checks=[],denials=[];let dom,w,$,posts=[],mode='normal',release;
const check=(ok,name)=>{assert(ok,name);checks.push(name);};
const wait=async(fn,name)=>{const end=Date.now()+6000;while(Date.now()<end){if(fn())return;await new Promise(r=>setTimeout(r,10));}throw Error('Timeout '+name);};
async function setup(){
 dom?.window.close();dom=new JSDOM(await(await fetch(info.base)).text(),{url:info.base,runScripts:'dangerously'});w=dom.window;$=id=>w.document.getElementById(id);w.setInterval=()=>0;w.crypto.randomUUID=require('node:crypto').randomUUID;
 w.fetch=async(url,opts={})=>{const target=new URL(url,info.base);assert.equal(target.origin,info.base);const post=opts.method==='POST'&&target.pathname.endsWith('/runs');
  if(post)posts.push(JSON.parse(opts.body));const response=await fetch(target,opts);if(response.status===403)denials.push({path:target.pathname,status:response.status});
  if(post&&mode==='lost'){mode='normal';assert.equal(response.status,202);throw TypeError('Synthetic lost acceptance');}
  if(target.pathname==='/api/internal/instances/'+info.instance&&mode==='read-lost'){mode='normal';throw TypeError('Synthetic lost read');}
  if(target.pathname==='/api/internal/instances/'+info.instance&&mode==='hold'){mode='normal';await new Promise(r=>{release=r;});release=null;}
  if(target.pathname==='/api/internal/instances/'+info.instance&&mode==='version-mismatch'){mode='normal';const data=await response.json();data.release_fingerprint='0'.repeat(64);return new Response(JSON.stringify(data),{status:200,headers:{'Content-Type':'application/json'}});}return response;};
 for(const file of ['app.js','internal.js','protocol.js','use.js']){const script=w.document.createElement('script');script.textContent=await(await fetch(info.base+'/'+file)).text();w.document.body.append(script);}
 $('token').value='synthetic-test-A';$('connect').click();await wait(()=>$('use-list').textContent.includes('Saved synthetic sum'),'saved instance list');
 $('use-list').querySelector('button').click();await wait(()=>!$('use-form').hidden,'open business use');
}
const worker=async()=>{const r=await fetch(info.base+'/test-only-worker',{method:'POST',headers:{Authorization:'Bearer synthetic-test-A','Content-Type':'application/json'},body:'{}'});assert.equal(r.status,200);};
const state=()=>w.eval('applicationUseRequests.get(applicationUseKey(applicationUse))?.state');
const submit=column=>{$('use-column').value=column;$('use-form').dispatchEvent(new w.Event('submit',{cancelable:true}));};
(async()=>{try{
 await setup();check($('use-info').textContent.includes('未发布内部版本')&&$('use-info').textContent.includes('0模型请求'),'scope and publication boundary visible');
 check([...$('use-column').options].map(o=>o.value).join(',')==='amount,tax','only frozen material numeric columns selectable');
 submit('amount');submit('amount');await wait(()=>state()==='accepted','first accepted');check(posts.length===1,'double click sends one POST');
 check($('use-output').textContent.includes('QUEUED')&&!$('use-output').textContent.includes('合计 12'),'queued current run never displays an old successful result');
 await worker();$('use-refresh').click();await wait(()=>$('use-output').textContent.includes('合计 12'),'first result');
 check($('use-history').textContent.includes('历史结果 v1')&&$('use-output').textContent.includes('SUCCEEDED'),'normal worker creates durable first result');
 mode='lost';submit('tax');await wait(()=>state()==='unknown','lost acceptance');
 const frozen=posts[1];$('use-column').value='amount';$('use-recover').click();await wait(()=>state()==='accepted','same key accepted');
 check(JSON.stringify(posts[2])===JSON.stringify(frozen)&&posts[2].input.column==='tax','recovery preserves exact parameter revision release and key');
 check($('use-output').textContent.includes('QUEUED')&&!$('use-output').textContent.includes('合计 12'),'new queued run stays separate from prior success');
 await worker();$('use-refresh').click();await wait(()=>$('use-output').textContent.includes('合计 3'),'second result');
 check($('use-history').textContent.includes('历史结果 v1')&&$('use-history').textContent.includes('历史结果 v2'),'second numeric input appends independent result and retains v1');
 const fault=async(action)=>{const response=await fetch(info.base+'/test-only-authorization-fault/'+action,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});assert.equal(response.status,200);};
 await fault('revoke');$('use-refresh').click();await wait(()=>$('use-form').hidden,'real revoked authorization');check(denials.some(d=>d.path==='/api/internal/instances/'+info.instance&&d.status===403),'revoked instance read was actual HTTP403');check(!$('use-output').textContent&&!$('use-history').textContent&&!$('use-provenance').textContent,'actual authorization revocation clears all current and historical data');
 await fault('restore');$('use-refresh').click();await wait(()=>!$('use-form').hidden&&$('use-output').textContent.includes('合计 3'),'existing fixture exact authorization restored');
 mode='version-mismatch';$('use-refresh').click();await wait(()=>$('use-form').hidden,'synthetic mismatched version');check(!$('use-output').textContent&&!$('use-history').textContent&&!$('use-provenance').textContent,'actual instance reply version mismatch clears protected data');$('use-refresh').click();await wait(()=>!$('use-form').hidden&&$('use-output').textContent.includes('合计 3'),'untampered version read restored');
 mode='read-lost';$('use-refresh').click();await wait(()=>$('use-form').hidden,'read lost');
 check($('use-output').textContent===''&&$('use-history').textContent===''&&$('use-info').textContent.includes('读取失败不表示任务执行失败'),'read failure clears stale outcomes and controls');
 const before=posts.length;$('use-refresh').click();await wait(()=>!$('use-form').hidden,'manual GET restore');check(posts.length===before,'read restoration sends no POST');
 const option=new w.Option('synthetic invalid text column','memo');$('use-column').append(option);submit('memo');await wait(()=>state()==='accepted','invalid column accepted for real worker rejection');await worker();$('use-refresh').click();await wait(()=>$('use-output').textContent.includes('FAILED'),'failed new run');
 check(!$('use-output').textContent.includes('合计')&&$('use-history').textContent.includes('历史结果 v2'),'failed current run keeps old successful result historical only');
 mode='hold';const late=w.readApplicationUse(w.eval('applicationUse'));await wait(()=>!!release,'held selected read');
 $('project-select').value=info.other;$('project-select').dispatchEvent(new w.Event('change'));await wait(()=>$('use-list').textContent.includes('暂无'),'other project');release();await late;
 check($('use-form').hidden&&$('use-output').textContent===''&&!$('use-list').textContent.includes('Saved synthetic sum'),'late detail cannot cross project boundary');
 const prior=posts.length;await setup();check(posts.length===prior,'cold reconnect and reopen send no POST');
 check($('use-output').textContent.includes('本页尚未选择')&&$('use-history').textContent.includes('历史结果 v1')&&$('use-history').textContent.includes('历史结果 v2'),'cold session recovers persisted versions without making history current');
 $('token').value='synthetic-test-B';$('connect').click();await wait(()=>$('project-select').selectedOptions[0]?.textContent==='Other identity project','new identity');
 check($('use-form').hidden&&$('use-output').textContent===''&&$('use-history').textContent===''&&!$('use-list').textContent.includes('Saved synthetic sum'),'identity change clears old business results');
 const result={status:'PASS',checks,denials,posts:posts.length,real_model_requests:0,browser:'NOT_RUN',pixels:'NOT_RUN',runtime_scope:'same frozen CSV resource, column parameter only'};fs.writeFileSync(path.join(root,'results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}catch(error){console.error(error.stack);process.exitCode=1;}finally{dom?.window.close();}})();
