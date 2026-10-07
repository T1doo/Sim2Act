'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const root=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(root,'info.json'))),checks=[];let dom,w,$,posts=[],mode='normal',release,page;const lifecycle=[];
const check=(ok,name)=>{assert(ok,name);checks.push(name);};
const wait=async(fn,name)=>{const end=Date.now()+6000;while(Date.now()<end){if(fn())return;await new Promise(r=>setTimeout(r,10));}throw Error('Timeout '+name);};
// Track each page separately: a JSDOM close destroys document while Node I/O may live on.
// Original setInterval=()=>0 remains: product interval timers stay disabled.
// Rejections remain test failures; no exception or original product assertion is suppressed.
async function idlePage(){
 if(!page)return;
 await wait(()=>page.requests===0&&page.actions.size===0,'page actions and HTTP drained');
 await new Promise(resolve=>setImmediate(resolve));
 if(page.errors.length)throw page.errors[0];
 assert.equal(page.requests,0);assert.equal(page.actions.size,0);
}
async function closePage(){
 if(!dom)return;
 await idlePage();
 lifecycle.push({requests:page.requests,actions:page.actions.size,errors:page.errors.length});
 dom.window.close();dom=null;
}
function trackHandlers(window,current){
 for(const name of ['onclick','onchange','onsubmit']){
  const descriptor=Object.getOwnPropertyDescriptor(window.HTMLElement.prototype,name);
  assert(descriptor?.set,'JSDOM handler descriptor required');
  Object.defineProperty(window.HTMLElement.prototype,name,{...descriptor,set(fn){
   descriptor.set.call(this,typeof fn==='function'?function(...args){
    const result=fn.apply(this,args);
    if(result&&typeof result.then==='function'){
     const action=Promise.resolve(result);current.actions.add(action);
     action.then(()=>current.actions.delete(action),error=>{current.errors.push(error);current.actions.delete(action);});
    }
    return result;
   }:fn);
  }});
 }
 window.addEventListener('error',event=>{current.errors.push(event.error||Error(event.message));});
}
async function setup(){
 await closePage();dom=new JSDOM(await(await fetch(info.base)).text(),{url:info.base,runScripts:'dangerously'});w=dom.window;$=id=>w.document.getElementById(id);page={requests:0,actions:new Set(),errors:[]};trackHandlers(w,page);w.setInterval=()=>0;w.crypto.randomUUID=require('node:crypto').randomUUID;
 const current=page;
 w.fetch=async(url,opts={})=>{current.requests++;try{const target=new URL(url,info.base);assert.equal(target.origin,info.base);const post=opts.method==='POST'&&target.pathname.endsWith('/runs');
  if(post)posts.push(JSON.parse(opts.body));const response=await fetch(target,opts);
  if(post&&mode==='lost'){mode='normal';assert.equal(response.status,202);throw TypeError('Synthetic lost acceptance');}
  if(target.pathname==='/api/internal/instances/'+info.instance&&mode==='read-lost'){mode='normal';throw TypeError('Synthetic lost read');}
  if(target.pathname==='/api/internal/instances/'+info.instance&&mode==='hold'){mode='normal';await new Promise(r=>{release=r;});release=null;}
  if(target.pathname==='/api/internal/instances/'+info.instance&&mode==='record-binding'){
   const value=await response.json();mode='normal';value.data[0].run_id='iapp_run_synthetic_unbound';
   return new Response(JSON.stringify(value),{status:response.status,headers:{'Content-Type':'application/json'}});
  }
  if(target.pathname.startsWith('/api/internal/releases/')&&mode.startsWith('evidence-')){
   const value=await response.json();const kind=mode;mode='normal';
   if(kind==='evidence-missing')delete value.snapshot.check_evidence;
   if(kind==='evidence-ref')value.snapshot.check_evidence.ref='synthetic.untrusted';
   if(kind==='evidence-binding')value.snapshot.check_evidence.candidate_fingerprint='0'.repeat(64);
   return new Response(JSON.stringify(value),{status:response.status,headers:{'Content-Type':'application/json'}});
  }
  const body=await response.arrayBuffer();
  return new Response(body,{status:response.status,headers:response.headers});
 }finally{current.requests--;}};
 for(const file of ['app.js','internal.js','protocol.js','use.js']){const script=w.document.createElement('script');script.textContent=await(await fetch(info.base+'/'+file)).text();w.document.body.append(script);}
 $('token').value='synthetic-test-A';$('connect').click();await wait(()=>$('use-list').textContent.includes('Saved synthetic sum'),'saved instance list');
 $('use-list').querySelector('button').click();await wait(()=>!$('use-form').hidden,'open business use');
}
const worker=async()=>{const r=await fetch(info.base+'/test-only-worker',{method:'POST',headers:{Authorization:'Bearer synthetic-test-A','Content-Type':'application/json'},body:'{}'});assert.equal(r.status,200);};
const state=()=>w.eval('applicationUseRequests.get(applicationUseKey(applicationUse))?.state');
const submit=column=>{$('use-column').value=column;$('use-form').dispatchEvent(new w.Event('submit',{cancelable:true}));};
(async()=>{try{
 await setup();await idlePage();check($('use-info').textContent.includes('未发布内部版本')&&$('use-info').textContent.includes('0模型请求'),'scope and publication boundary visible');
 check($('use-acceptance').textContent.includes('样本工具检查：PASS')&&$('use-acceptance').textContent.includes('尚未选择运行')&&$('use-acceptance').textContent.includes('NOT_RUN；用户确认：PENDING；正式发布：关闭'),'frozen technical sample remains distinct from semantic and user acceptance');
 for(const kind of ['evidence-missing','evidence-ref','evidence-binding']){
  const count=posts.length;await idlePage();mode=kind;await w.readApplicationUse(w.eval('applicationUse'));
  check($('use-acceptance').textContent.includes('样本工具检查：UNKNOWN')&&!$('use-acceptance').textContent.includes('样本工具检查：PASS')&&posts.length===count,kind+' cannot promote untrusted frozen evidence or write');
 }
 await w.readApplicationUse(w.eval('applicationUse'));
 check([...$('use-column').options].map(o=>o.value).join(',')==='amount,tax','only frozen material numeric columns selectable');
 submit('amount');submit('amount');await wait(()=>state()==='accepted','first accepted');check(posts.length===1,'double click sends one POST');
 check($('use-output').textContent.includes('QUEUED')&&!$('use-output').textContent.includes('合计 12'),'queued current run never displays an old successful result');
 await worker();$('use-refresh').click();await wait(()=>$('use-output').textContent.includes('合计 12'),'first result');
 check($('use-history').textContent.includes('历史结果 v1')&&$('use-output').textContent.includes('SUCCEEDED'),'normal worker creates durable first result');
 check($('use-acceptance').textContent.includes('本次技术执行：SUCCEEDED；结果核对：PASS · v1')&&$('use-acceptance').textContent.includes('用户确认：PENDING'),'real normal worker result v1 is technical only');
 await idlePage();const beforeBinding=posts.length;mode='record-binding';await w.readApplicationUse(w.eval('applicationUse'));
 check($('use-acceptance').textContent.includes('本次技术执行：SUCCEEDED')&&!$('use-acceptance').textContent.includes('结果核对：PASS')&&posts.length===beforeBinding,'unbound result record cannot promote technical result assessment or write');
 await w.readApplicationUse(w.eval('applicationUse'));
 await idlePage();mode='lost';submit('tax');await wait(()=>state()==='unknown','lost acceptance');
 check($('use-acceptance').textContent==='', 'unknown new acceptance clears prior result assessment');
 const frozen=posts[1];$('use-column').value='amount';$('use-recover').click();await wait(()=>state()==='accepted','same key accepted');
 check(JSON.stringify(posts[2])===JSON.stringify(frozen)&&posts[2].input.column==='tax','recovery preserves exact parameter revision release and key');
 check($('use-output').textContent.includes('QUEUED')&&!$('use-output').textContent.includes('合计 12'),'new queued run stays separate from prior success');
 await worker();$('use-refresh').click();await wait(()=>$('use-output').textContent.includes('合计 3'),'second result');
 check($('use-history').textContent.includes('历史结果 v1')&&$('use-history').textContent.includes('历史结果 v2'),'second numeric input appends independent result and retains v1');
 check($('use-acceptance').textContent.includes('结果核对：PASS · v2'),'second real result assessment bound to v2');
 await idlePage();mode='read-lost';$('use-refresh').click();await wait(()=>$('use-form').hidden,'read lost');
 check($('use-output').textContent===''&&$('use-history').textContent===''&&$('use-info').textContent.includes('读取失败不表示任务执行失败'),'read failure clears stale outcomes and controls');
 check($('use-acceptance').textContent==='', 'read failure clears all acceptance evidence');
 const before=posts.length;$('use-refresh').click();await wait(()=>!$('use-form').hidden,'manual GET restore');check(posts.length===before,'read restoration sends no POST');
 const option=new w.Option('synthetic invalid text column','memo');$('use-column').append(option);submit('memo');await wait(()=>state()==='accepted','invalid column accepted for real worker rejection');await worker();$('use-refresh').click();await wait(()=>$('use-output').textContent.includes('FAILED'),'failed new run');
 check(!$('use-output').textContent.includes('合计')&&$('use-history').textContent.includes('历史结果 v2'),'failed current run keeps old successful result historical only');
 check($('use-acceptance').textContent.includes('本次技术执行：FAILED')&&!$('use-acceptance').textContent.includes('结果核对：PASS'),'failed current run cannot borrow historical successful evidence');
 await idlePage();mode='hold';const late=w.readApplicationUse(w.eval('applicationUse'));await wait(()=>!!release,'held selected read');
 $('project-select').value=info.other;$('project-select').dispatchEvent(new w.Event('change'));await wait(()=>$('use-list').textContent.includes('暂无'),'other project');release();await late;
 check($('use-form').hidden&&$('use-output').textContent===''&&!$('use-list').textContent.includes('Saved synthetic sum'),'late detail cannot cross project boundary');
 check($('use-acceptance').textContent==='', 'project change and late detail cannot restore acceptance');
 const prior=posts.length;await setup();await idlePage();check(posts.length===prior,'cold reconnect and reopen send no POST');
 check($('use-output').textContent.includes('本页尚未选择')&&$('use-history').textContent.includes('历史结果 v1')&&$('use-history').textContent.includes('历史结果 v2'),'cold session recovers persisted versions without making history current');
 check($('use-acceptance').textContent.includes('尚未选择运行')&&!$('use-acceptance').textContent.includes('结果核对：PASS'),'cold read does not auto accept history');
 const coldPosts=posts.length;const priorRun=[...$('use-history').children].find(r=>r.textContent.includes('SUCCEEDED')&&r.textContent.includes('结果版本 1'));priorRun.querySelector('button').click();
 await wait(()=>$('use-acceptance').textContent.includes('所选历史技术执行：SUCCEEDED'),'selected historical assessment');
 check($('use-acceptance').textContent.includes('结果核对：PASS · v1')&&$('use-acceptance').textContent.includes('用户确认：PENDING')&&posts.length===coldPosts,'explicit historical review stays read-only and never becomes user confirmation');
 $('token').value='synthetic-test-B';$('connect').click();await wait(()=>$('project-select').selectedOptions[0]?.textContent==='Other identity project','new identity');
 check($('use-form').hidden&&$('use-output').textContent===''&&$('use-history').textContent===''&&!$('use-list').textContent.includes('Saved synthetic sum'),'identity change clears old business results');
 check($('use-acceptance').textContent==='', 'identity change clears acceptance');
 await closePage();check(lifecycle.length===2&&lifecycle.every(p=>p.requests===0&&p.actions===0&&p.errors===0),'both pages close after actions and requests settle without late errors');
 const result={status:'PASS',lifecycle,checks,posts:posts.length,real_model_requests:0,browser:'NOT_RUN',pixels:'NOT_RUN',runtime_scope:'same frozen CSV resource, column parameter only'};fs.writeFileSync(path.join(root,'results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}catch(error){console.error(error.stack);process.exitCode=1;}finally{try{await closePage();}catch(error){console.error(error.stack);process.exitCode=1;}}})();
