'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),checks=[],trace=[],hashes={};
let dom,w,mode='',release=null;
const verify=(condition,label)=>{assert(condition,label);checks.push(label)};
const settle=async test=>{const until=Date.now()+20000;while(Date.now()<until){if(test())return;await new Promise(resolve=>setTimeout(resolve,10))}throw Error('independent wait timeout')};
const box=()=>w.document.querySelector('.project-check-controls');
const control=suffix=>box().querySelector('.project-check-'+suffix);
async function open(){
 const html=await (await fetch(info.url)).text();hashes['index.html']=crypto.createHash('sha256').update(html).digest('hex');
 dom=new JSDOM(html,{url:info.url,runScripts:'dangerously'});w=dom.window;
 w.setInterval=()=>0;w.TextEncoder=TextEncoder;Object.defineProperty(w.crypto,'subtle',{value:crypto.webcrypto.subtle});
 w.fetch=async (url,options={})=>{
  const target=new URL(url,info.url);assert.equal(target.origin,info.url);
  const item={path:target.pathname,method:options.method||'GET',body:options.body?JSON.parse(options.body):null};trace.push(item);
  if(mode==='readback422'&&item.method==='GET'&&/^.*\/scope-checks\/[^/]+$/.test(item.path)&&!item.path.endsWith('/options')){mode='';item.injected=422;return new Response(JSON.stringify({detail:[{msg:'controlled readback unavailable'}]}),{status:422})}
  const response=await fetch(target,options);item.status=response.status;
  if(item.method==='POST'&&item.path.endsWith('/scope-checks')){
   verify(response.status===201,'real scope-check POST accepted under current SQLite authority');
   if(mode==='lost'){mode='';item.reply='lost-after-accepted';throw Error('accepted response intentionally lost')}
   if(mode==='late'){mode='';await new Promise(resolve=>release=resolve);release=null}
  }
  if(mode==='corrupt'&&item.method==='GET'&&item.path.endsWith('/scope-checks')){
   mode='';const value=await response.json();value.items[0].executed_checks_status='FAIL';item.reply='invalid-200';return new Response(JSON.stringify(value),{status:200});
  }
  return response;
 };
 for(const file of Array.from(w.document.querySelectorAll('script[src]')).map(s=>s.getAttribute('src').slice(1))){
  const code=await(await fetch(info.url+'/'+file)).text();hashes[file]=crypto.createHash('sha256').update(code).digest('hex');
  const element=w.document.createElement('script');element.textContent=code;w.document.body.append(element);
 }
 w.document.getElementById('token').value='synthetic-test-A';await w.document.getElementById('connect').onclick();
 await settle(()=>w.document.getElementById('project-select').value===info.project);
 await w.showApp(info.app);await w.readDeliveryGraph();
 verify(!!box(),'real existing PROJECT plan exposes original page controls');
}
async function read(){await control('options').onclick()}
function acknowledge(){control('confirmation').checked=true;control('confirmation').dispatchEvent(new w.Event('change'))}
(async()=>{try{
 await open();verify(control('submit').disabled,'plan alone cannot send without precise options and consent');
 await read();verify(box().querySelectorAll('select').length===2,'original amount CSV and exact archived Report both offered');
 verify(box().querySelector('option[value="amount"]')&&!box().querySelector('option[value="quantity"]'),'independent original CSV source is amount-only');
 verify(control('submit').disabled,'options read alone does not authorize execution');acknowledge();verify(!control('submit').disabled,'explicit exact confirmation permits execution');
 if(info.scenario==='readback422'){
  mode='readback422';await control('submit').onclick();
  verify(control('submit').textContent.includes('原键'),'POST accepted then GET422 preserves original frozen body and key');
  verify(control('confirmation').disabled,'accepted but unverified receipt locks original input and confirmation');
  const before=trace.filter(x=>x.method==='POST'&&x.path.endsWith('/scope-checks')).length;
  await read();verify(!control('submit').textContent.includes('原键'),'exact matching current history resolves acceptance');
  verify(trace.filter(x=>x.method==='POST'&&x.path.endsWith('/scope-checks')).length===before,'history resolves without any new submission');
 }else{
  mode='lost';await control('submit').onclick();verify(control('submit').textContent.includes('原键'),'lost accepted response preserves original intent');
  await control('submit').onclick();const posts=trace.filter(x=>x.method==='POST'&&x.path.endsWith('/scope-checks'));
  verify(posts.length===2&&JSON.stringify(posts[0].body)===JSON.stringify(posts[1].body),'retry uses exact original body and key');
  verify(box().textContent.includes('列 amount，合计 4'),'actual original CSV result4 rendered');
  verify(box().textContent.includes('原材料有限规则 PASS')&&box().textContent.includes('解释文本 NOT_CHECKED'),'Report real-source bounded checks and explanation boundary shown');
  verify(box().textContent.includes('BLOCKED_PARTIAL')&&box().textContent.includes('BLOCKED_UNKNOWN'),'finite PASS leaves project partial and unknown');
  acknowledge();mode='late';const pending=control('submit').onclick();await settle(()=>release);
  w.clearApp();await w.showApp(info.app);await w.readDeliveryGraph();verify(!box().textContent.includes('合计 4'),'new context has no stale accepted result');
  release();await pending;verify(control('submit').textContent.includes('原键')&&!control('options').disabled,'late callback releases new control busy state and preserves unknown key');
  const before=trace.filter(x=>x.method==='POST'&&x.path.endsWith('/scope-checks')).length;await read();
  verify(!control('submit').textContent.includes('原键')&&box().textContent.includes('合计 4'),'new context reads exact current accepted history');
  verify(trace.filter(x=>x.method==='POST'&&x.path.endsWith('/scope-checks')).length===before,'late receipt history recovery causes no new submission');
  mode='corrupt';await read();verify(control('submit').disabled&&!control('confirmation').checked&&!box().textContent.includes('合计 4'),'invalid HTTP200 history clears evidence and confirmation');
 }
 fs.writeFileSync(info.evidence,JSON.stringify({status:'PASS',checks,trace,hashes,native:'NOT_RUN'},null,2));console.log(JSON.stringify({status:'PASS',checks:checks.length}));
 }catch(error){fs.writeFileSync(info.evidence,JSON.stringify({status:'FAIL',error:error.stack,checks,trace,hashes},null,2));console.error(error.stack);process.exitCode=1}
 finally{dom?.window.close()}
})();
