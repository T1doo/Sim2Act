'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const root=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(root,'info.json'))),checks=[],requests=[];
let dom,w,$,mode='normal',release;
const check=(ok,name)=>{assert(ok,name);checks.push(name);};
const wait=async(fn,name)=>{const end=Date.now()+6000;while(Date.now()<end){if(fn())return;await new Promise(r=>setTimeout(r,10));}throw Error('Timeout '+name);};
async function setup(){
 dom?.window.close();dom=new JSDOM(await(await fetch(info.base)).text(),{url:info.base,runScripts:'dangerously'});w=dom.window;$=id=>w.document.getElementById(id);w.setInterval=()=>0;
 w.fetch=async(url,opts={})=>{const target=new URL(url,info.base);assert.equal(target.origin,info.base);requests.push({path:target.pathname,method:opts.method||'GET'});
  if(mode==='failure'&&target.pathname.endsWith('/conditional-checks')){mode='normal';throw TypeError('Synthetic technical read failure');}
  const response=await fetch(target,opts);
  if(mode==='hold'&&target.pathname.endsWith('/conditional-checks')){mode='normal';await new Promise(r=>release=r);release=null;}
  return response;};
 for(const file of ['app.js','internal.js','protocol.js','use.js']){const script=w.document.createElement('script');script.textContent=await(await fetch(info.base+'/'+file)).text();w.document.body.append(script);}
 $('token').value='synthetic-test-A';$('connect').click();await wait(()=>$('project-select').value===info.project&&$('login').hidden&&$('run-history-status').textContent.includes('暂无'),'connect');
}
async function open(){await w.listConditionalSources();$('condition-resource').value=info.resource;await w.openConditionalSource();assert(!$('condition-form').hidden);}
function manual(unknown=false){
 const fields={trip:unknown?'':'true',amount:unknown?'':'680',receipt:unknown?'':'true',approved:unknown?'':'false',days:unknown?'':'2',R1:unknown?'UNKNOWN':'TRUE',R2:unknown?'UNKNOWN':'TRUE',R3:unknown?'UNKNOWN':'FALSE',decision:unknown?'UNKNOWN':'BLOCK',deadline:'10',date:'UNKNOWN',restart:'false',explanation:'人工报告；自由说明不评分。'};
 for(const [id,value]of Object.entries(fields))$('condition-'+id).value=value;
 for(const o of $('condition-actions').options)o.selected=o.value===(unknown?'clarify_facts':'obtain_prior_approval');
}
(async()=>{try{
 await setup();check(!requests.some(r=>r.path.includes('/conditional-checks/sources/')),'no automatic source content read');
 await w.listConditionalSources();check($('condition-resource').textContent.includes('public-synthetic-policy')&&!requests.some(r=>r.path.includes('/conditional-checks/sources/')),'explicit authorized metadata list without content');
 $('condition-resource').value=info.unsupported;await w.openConditionalSource();check($('condition-form').hidden&&$('condition-status').textContent.includes('VERSION_CONFLICT'),'unsupported material refused without hypothetical gold substitution');
 await open();check($('condition-source').textContent.includes(info.resource)&&$('condition-source').textContent.includes('第4行')&&$('condition-source').textContent.includes('SHA256'),'authorized source content hash contract version and citations visible');
 manual();await w.runConditionalCheck();check($('condition-results').textContent.includes('报告核对 PASS')&&$('condition-results').textContent.includes('决策 BLOCK')&&$('condition-results').textContent.includes('R2：不满足')&&$('condition-results').textContent.includes('尚未取得'),'valid report of unmet condition is PASS while decision remains BLOCK');
 check($('condition-results').textContent.includes('语义 UNKNOWN；用户确认 PENDING')&&$('condition-results').textContent.includes('NOT_CHECKED'),'structural semantic prose and user states separate');
 $('condition-amount').value='500';$('condition-amount').dispatchEvent(new w.Event('input',{bubbles:true}));check($('condition-results').textContent===''&&$('condition-recheck').hidden,'edited facts invalidate old evidence');
 await w.runConditionalCheck();check($('condition-results').textContent.includes('报告核对 FAIL')&&$('condition-results').textContent.includes('R2：不适用'),'wrong manual proposal gets FAIL without auto-correcting it');
 manual(true);await w.runConditionalCheck();check($('condition-results').textContent.includes('报告核对 PASS')&&$('condition-results').textContent.includes('R1：未知')&&$('condition-results').textContent.includes('R2：未知')&&$('condition-results').textContent.includes('决策 UNKNOWN'),'unknown facts preserved with reasons');
 const unchanged=await(await fetch(info.base+'/test-only-unchanged')).json();check(unchanged.unchanged,'all persisted rows unchanged by listings source reads and repeated check POSTs');
 const before=requests.length;await w.runConditionalCheck(true);check(requests.slice(before).length===1&&requests.at(-1).method==='POST','explicit recheck goes through fresh server authorization only once');
 mode='failure';await w.runConditionalCheck(true);check($('condition-results').textContent===''&&$('condition-source').textContent===''&&$('condition-form').hidden&&$('condition-status').textContent.includes('请求失败不等于业务条件不满足'),'technical request failure clears prior evidence without asserting rule failure');

 await open();manual();mode='hold';let editedLate=w.runConditionalCheck();await wait(()=>!!release,'independent held edit');
 $('condition-amount').value='500';$('condition-amount').dispatchEvent(new w.Event('input',{bubbles:true}));release();await editedLate;
 check($('condition-results').textContent===''&&$('condition-recheck').hidden&&!$('condition-submit').disabled,'independent edited facts deny delayed PASS and re-enable explicit submit');
 await w.runConditionalCheck();check($('condition-results').textContent.includes('报告核对 FAIL'),'independent fresh check reflects edited amount rather than delayed old result');
 await open();manual();mode='hold';let abaLate=w.runConditionalCheck();await wait(()=>!!release,'independent project ABA held');
 $('project-select').value=info.other;$('project-select').dispatchEvent(new w.Event('change'));await wait(()=>$('condition-source').textContent==='','independent ABA leave');
 $('project-select').value=info.project;$('project-select').dispatchEvent(new w.Event('change'));release();await abaLate;
 check($('condition-results').textContent===''&&$('condition-form').hidden,'independent project ABA denies prior generation result');
 await open();manual();mode='hold';let identityLate=w.runConditionalCheck();await wait(()=>!!release,'independent identity ABA held');
 $('token').value='synthetic-test-A';$('connect').click();await wait(()=>$('condition-source').textContent==='','independent identity reconnect clear');release();await identityLate;
 await wait(()=>$('project-select').value===info.project,'independent reconnect complete');
 check($('condition-results').textContent===''&&$('condition-form').hidden,'independent same identity reconnect denies prior generation result');
 await open();manual();await w.runConditionalCheck();await fetch(info.base+'/test-only-source-change',{method:'POST'});await w.runConditionalCheck(true);
 check($('condition-results').textContent===''&&$('condition-source').textContent===''&&$('condition-status').textContent.includes('VERSION_CONFLICT'),'coherent content version change invalidates old evidence: '+$('condition-status').textContent);
 await fetch(info.base+'/test-only-source-restore',{method:'POST'});await open();manual();mode='hold';const late=w.runConditionalCheck();await wait(()=>!!release,'held check');
 $('project-select').value=info.other;$('project-select').dispatchEvent(new w.Event('change'));await wait(()=>$('condition-source').textContent==='','project clear');release();await late;
 check($('condition-results').textContent===''&&$('condition-form').hidden,'late source verdict cannot cross project');
 const previousChecks=requests.filter(r=>r.method==='POST'&&r.path.endsWith('/conditional-checks')).length;
 await setup();check($('condition-results').textContent===''&&$('condition-form').hidden&&requests.filter(r=>r.method==='POST'&&r.path.endsWith('/conditional-checks')).length===previousChecks,'cold session does not restore old PASS or automatically check');
 await open();manual();await w.runConditionalCheck();await w.listConditionalSources();check($('condition-results').textContent===''&&$('condition-source').textContent==='','explicit refresh invalidates evidence');
 await open();manual();await w.runConditionalCheck();await fetch(info.base+'/test-only-source-revoke',{method:'POST'});await w.runConditionalCheck(true);check($('condition-results').textContent===''&&$('condition-source').textContent===''&&$('condition-status').textContent.includes('GRANT_REVOKED'),'actual grant revocation hides source and old verdict');
 await w.listConditionalSources();check(![...$('condition-resource').options].some(o=>o.value===info.resource),'revoked source removed from authorized choices');
 check(!requests.some(r=>r.method==='POST'&&!r.path.endsWith('/conditional-checks')),'UI sends no business execution grant identity or model mutation');
 const result={status:'PASS',checks,request_count:requests.length,real_model_requests:0,native:'NOT_RUN',pixels:'NOT_RUN'};fs.writeFileSync(path.join(root,'results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}catch(error){console.error(error.stack);process.exitCode=1;}finally{dom?.window.close();}})();
