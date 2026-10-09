'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{JSDOM}=require('jsdom');
const root=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(root,'info.json'))),checks=[],requests=[],hashes={};let dom,w,$,mode='',release,page;
const check=(v,label)=>{assert(v,label);checks.push(label);};
const wait=async fn=>{const end=Date.now()+30000;while(Date.now()<end){if(fn())return;await new Promise(r=>setTimeout(r,10));}throw Error('bounded test wait expired');};
const box=()=>w.document.querySelector('.project-check-controls');
const button=name=>box().querySelector('.project-check-'+name);
async function idle(){await wait(()=>page.requests===0&&page.actions.size===0);await new Promise(r=>setImmediate(r));if(page.errors.length)throw page.errors[0];}
function track(window,current){for(const name of ['onclick','onchange','onsubmit']){const d=Object.getOwnPropertyDescriptor(window.HTMLElement.prototype,name);Object.defineProperty(window.HTMLElement.prototype,name,{...d,set(fn){d.set.call(this,typeof fn==='function'?function(...args){const result=fn.apply(this,args);if(result&&typeof result.then==='function'){const p=Promise.resolve(result);current.actions.add(p);p.then(()=>current.actions.delete(p),e=>{current.actions.delete(p);current.errors.push(e);});}return result;}:fn);}});}window.addEventListener('error',e=>current.errors.push(e.error||Error(e.message)));}
async function close(){if(dom){await idle();dom.window.close();dom=null;}}
async function setup(){await close();const html=await(await fetch(info.base)).text();hashes['index.html']=crypto.createHash('sha256').update(html).digest('hex');dom=new JSDOM(html,{url:info.base,runScripts:'dangerously'});w=dom.window;$=id=>w.document.getElementById(id);page={requests:0,actions:new Set(),errors:[]};track(w,page);const current=page;w.setInterval=()=>0;w.TextEncoder=TextEncoder;Object.defineProperty(w.crypto,'subtle',{value:crypto.webcrypto.subtle});
 w.fetch=async(url,opts={})=>{current.requests++;try{const target=new URL(url,info.base);assert.equal(target.origin,info.base);const r={path:target.pathname,method:opts.method||'GET',body:opts.body&&JSON.parse(opts.body)};requests.push(r);const response=await fetch(target,opts);if(mode==='lost'&&r.method==='POST'&&r.path.endsWith('/scope-checks')){mode='';assert.equal(response.status,201);throw Error('controlled accepted project check reply lost');}if(mode==='hold'&&r.method==='POST'&&r.path.endsWith('/scope-checks')){mode='';assert.equal(response.status,201);await new Promise(r=>release=r);release=null;}if(mode==='readback-422'&&r.method==='GET'&&/\/scope-checks\/[^/]+$/.test(r.path)){mode='';assert.equal(response.status,200);return new Response(JSON.stringify({detail:[{msg:'controlled accepted POST readback rejected'}]}),{status:422,headers:{'Content-Type':'application/json'}});}if(mode==='corrupt'&&r.method==='GET'&&r.path.endsWith('/scope-checks')){mode='';const data=await response.json();data.items[0].applications[0].declared_checks[0].status='FAIL';return new Response(JSON.stringify(data),{status:200,headers:{'Content-Type':'application/json'}});}return new Response(await response.arrayBuffer(),{status:response.status,headers:response.headers});}finally{current.requests--;}};
 for(const name of Array.from(w.document.querySelectorAll('script[src]')).map(s=>s.getAttribute('src').slice(1))){const code=await(await fetch(info.base+'/'+name)).text();hashes[name]=crypto.createHash('sha256').update(code).digest('hex');const script=w.document.createElement('script');script.textContent=code;w.document.body.append(script);}
 $('token').value='synthetic-test-A';$('connect').click();await wait(()=>$('project-select').value===info.project&&$('login').hidden);await idle();await w.showApp(info.app);await w.readDeliveryGraph();await idle();}
async function read(){await button('options').onclick();await idle();}
function confirm(){const select=box().querySelector('select option[value="quantity"]').parentNode;select.value='quantity';select.dispatchEvent(new w.Event('change'));button('confirmation').checked=true;button('confirmation').dispatchEvent(new w.Event('change'));}
(async()=>{try{
 await setup();check(!!box(),'actual current PROJECT plan exposes deterministic execution controls');
 check(button('submit').disabled,'current plan alone does not authorize checks');
 await read();check(box().querySelectorAll('select').length===2,'actual Report archive and CSV inputs cover all executable project peers');
 check(button('submit').disabled,'reading available inputs still requires exact confirmation');
 confirm();check(!button('submit').disabled,'explicit exact plan and per-app selection authorize checks');
 mode=info.scenario==='readback-422'?'readback-422':'lost';await button('submit').onclick();await idle();check(button('submit').textContent.includes('原键'),'ambiguous accepted check keeps original frozen recovery key');
 await button('submit').onclick();await idle();const posts=requests.filter(r=>r.method==='POST'&&r.path.endsWith('/scope-checks'));
 check(posts.length===2&&JSON.stringify(posts[0].body)===JSON.stringify(posts[1].body),'same body and key restore accepted project check');
 check(box().textContent.includes('列 quantity，合计 15'),'actual current CSV output is independently checked and rendered');
 check(box().textContent.includes('原材料有限规则 PASS')&&box().textContent.includes('解释文本 NOT_CHECKED'),'actual archived Report rules are rechecked without semantic explanation claims');
 check(box().textContent.includes('范围 PARTIAL')&&box().textContent.includes('PROJECT BLOCKED_PARTIAL')&&box().textContent.includes('BLOCKED_UNKNOWN'),'omissions and unknown dependencies remain blocked');
 check(!button('confirmation').checked,'verified acceptance resets explicit confirmation');
 const writes=requests.filter(r=>r.method==='POST').length;await setup();await read();
 check(requests.filter(r=>r.method==='POST').length===writes,'cold current plan and saved check readback make no writes');
 check(box().textContent.includes('合计 15')&&box().textContent.includes('有限检查执行 PASS'),'cold page reconstructs current sealed real-source results');
 if(info.scenario==='late-acceptance'){
  confirm();mode='hold';const late=button('submit').onclick();await wait(()=>release);
  const resume=release;$('project-select').value=info.other;w.clearApp();$('project-select').value=info.project;await w.showApp(info.app);await w.readDeliveryGraph();
  check(!box().textContent.includes('合计 15'),'old accepted response does not paint newly selected project page');
  resume();await late;await idle();check(button('submit').textContent.includes('原键'),'late accepted response preserves recoverable intent in new context');
  const count=requests.filter(r=>r.method==='POST').length;await read();check(requests.filter(r=>r.method==='POST').length===count&&!button('submit').textContent.includes('原键'),'verified new-context history resolves original acceptance without another write');
 }
 mode='corrupt';await read();check(!box().textContent.includes('合计 15')&&button('submit').disabled&&!button('confirmation').checked,'damaged HTTP200 history clears proof and exact confirmation');
 await idle();fs.writeFileSync(path.join(root,'results.json'),JSON.stringify({status:'PASS',checks,requests,loaded_source_sha256:hashes,model_requests:0,business_writes:0,native:'NOT_RUN'},null,2));console.log(JSON.stringify({status:'PASS',checks:checks.length}));
}catch(e){fs.writeFileSync(path.join(root,'failure.json'),JSON.stringify({status:'FAIL',checks,requests,error:e.message},null,2));console.error(e.stack);process.exitCode=1;}finally{await close();}})();
