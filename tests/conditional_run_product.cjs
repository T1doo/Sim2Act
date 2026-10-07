'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const root=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(root,'info.json'))),checks=[],requests=[];
let dom,w,$,mode='',release;
const check=(ok,name)=>{assert(ok,name);checks.push(name);};
const wait=async(fn,name)=>{const end=Date.now()+6000;while(Date.now()<end){if(fn())return;await new Promise(r=>setTimeout(r,10));}throw Error('Timeout '+name);};
async function setup(){
 dom?.window.close();dom=new JSDOM(await(await fetch(info.base)).text(),{url:info.base,runScripts:'dangerously'});w=dom.window;$=id=>w.document.getElementById(id);
 w.fetch=async(url,opts={})=>{const target=new URL(url,info.base);assert.equal(target.origin,info.base);const body=opts.body&&JSON.parse(opts.body);requests.push({path:target.pathname,method:opts.method||'GET',body});
  const response=await fetch(target,opts);
  if(mode==='bad-source'&&target.pathname.endsWith('/conditional-runs/source')){mode='';const bad=await response.json();bad.namespace='untrusted';return {ok:true,json:async()=>bad};}
  if(mode==='lost-source'&&target.pathname.endsWith('/conditional-runs/source')){mode='';throw TypeError('Synthetic accepted reply loss');}
  if(mode==='hold'&&target.pathname.includes('/conditional-runs/')&&opts.method==='POST'){mode='';await new Promise(r=>release=r);release=null;}
  return response;};
 for(const file of ['app.js','internal.js','protocol.js','use.js','conditional-runs.js']){const s=w.document.createElement('script');s.textContent=await(await fetch(info.base+'/'+file)).text();w.document.body.append(s);}
 $('token').value='synthetic-test-A';$('connect').click();await wait(()=>$('project-select').value===info.project&&$('login').hidden,'connect');
}
async function open(){await w.listConditionalSources();$('condition-resource').value=info.resource;await w.openConditionalSource();check(!$('condition-run-source-form').hidden,'explicit authorized source enables separate Run form');}
function facts(prefix,amount){for(const [id,value]of Object.entries({trip:'true',receipt:'true',approved:'false',amount:String(amount),days:'2'}))$(prefix+'-'+id).value=value;}
const work=phase=>fetch(info.base+'/test-only-bounded-work/'+phase,{method:'POST',body:'{}',headers:{'Content-Type':'application/json'}}).then(async r=>{assert(r.ok,await r.text());});
(async()=>{try{
 await setup();check(!requests.some(r=>r.path.includes('/conditional-runs')),'cold page creates no Run/check/model request');
 await open();facts('condition-run-source',680);$('condition-run-source-days').value='1.5';await w.startBoundedSource();check(!$('condition-run-start').disabled&&$('condition-run-retry').hidden,'first actual 422 rejection allows correction without unknown acceptance lock');facts('condition-run-source',680);
 // Deliberately wrong manual report fields cannot enter or replace actual source Run.
 $('condition-decision').value='ALLOW';$('condition-explanation').value='Manual invented unrelated answer';
 mode='lost-source';await w.startBoundedSource();check(!$('condition-run-retry').hidden&&$('condition-run-start').disabled,'unknown acceptance locks new creation and preserves explicit same-key recovery');
 const original=requests.filter(r=>r.path.endsWith('/conditional-runs/source')).at(-1).body;
 await w.boundedAction(c=>w.boundedSubmit(c,c.pending.phase,{},true));
 const posts=requests.filter(r=>r.path.endsWith('/conditional-runs/source')&&r.body.scenario.elapsed_days===2);check(posts.length===2&&JSON.stringify(posts[0].body)===JSON.stringify(posts[1].body),'explicit retry uses exact same frozen body/key');
 check(!('report' in original)&&!('candidate' in original)&&original.scenario.amount===680,'Run submission excludes manual Report/candidate/gold');
 check($('condition-run-check').hidden&&$('condition-run-output').textContent.includes('QUEUED'),'queued receipt cannot enable independent check');
 await work('source');await w.boundedAction(w.boundedRead);
 check($('condition-run-output').textContent.includes('WAITING_APPROVAL')&&$('condition-run-output').textContent.includes('UNKNOWN')&&$('condition-run-output').textContent.includes('NOT_ACCEPTED')&&$('condition-run-output').textContent.includes('BLOCK'),'actual hand-authored Mock Report BLOCK visible with overall UNKNOWN and NOT_ACCEPTED');
 await w.boundedAction(c=>w.checkBoundedRun(c,'source'));
 check($('condition-run-check-output').textContent.includes('有限报告检查 PASS')&&!$('condition-run-extract').hidden,'independent current real-Run finite check enables candidate only');
 const checksBefore=requests.filter(r=>r.path.endsWith('/checks')).length;
 await w.extractBoundedCandidate();check(requests.filter(r=>r.path.endsWith('/checks')).length===checksBefore+1,'extract freshly reads/rechecks source instead of trusting cached client eligible');
 await work('extract');await w.boundedAction(w.boundedRead);
 check(!$('condition-run-plan').hidden&&$('condition-run-plan-text').textContent.includes('candidate_receipt')&&$('condition-run-plan-text').textContent.includes('read_rules')&&$('condition-run-plan-text').textContent.includes('check_report'),'sealed actual candidate receipt and finite registered DAG visible');
 facts('condition-run-cold',500);$('condition-run-cold-resource').value=info.fresh;await w.startBoundedCold();await work('cold');await w.boundedAction(w.boundedRead);await w.boundedAction(c=>w.checkBoundedRun(c,'cold'));
 check($('condition-run-cold-output').textContent.includes('ALLOW')&&$('condition-run-cold-output').textContent.includes('NOT_ACCEPTED')&&$('condition-run-cold-check-output').textContent.includes('有限报告检查 PASS'),'new resource/500 cold Report ALLOW checked independently while overall unaccepted');
 mode='hold';const lateCold=w.boundedAction(c=>w.checkBoundedRun(c,'cold'));await wait(()=>release,'held cold check');$('condition-run-cold-amount').value='501';$('condition-run-cold-amount').dispatchEvent(new w.Event('input',{bubbles:true}));release();await lateCold;check($('condition-run-cold-output').textContent===''&&$('condition-run-cold-check-output').textContent===''&&$('condition-run-cold-check').hidden,'cold input epoch invalidates late checked Report');facts('condition-run-cold',500);$('condition-run-cold-resource').value=info.fresh;await w.startBoundedCold();
 const cold=requests.find(r=>r.path.endsWith('/conditional-runs/cold')).body;check(cold.resource_id===info.fresh&&cold.scenario.amount===500&&!('report' in cold),'cold only binds explicit new facts/material and sealed extraction');
 await w.boundedAction(w.boundedRead);check($('condition-run-check-output').textContent===''&&$('condition-run-extract').hidden,'read refresh drops cached check eligibility without automatic check/extract');
 await fetch(info.base+'/test-only-bounded-source-version/change',{method:'POST',body:'{}',headers:{'Content-Type':'application/json'}});w.eval('conditionalContext.source=null');
 const metadata=await(await fetch(info.base+'/api/projects/'+info.project+'/resources',{headers:{Authorization:'Bearer synthetic-test-A'}})).json();w.reconcileConditionalSources(metadata);
 check($('condition-run-plan').hidden&&$('condition-run-check-output').textContent===''&&$('condition-run-status').textContent.includes('版本已变化'),'real metadata version change clears bound candidate even after manual source context was cleared');
 await fetch(info.base+'/test-only-bounded-source-version/restore',{method:'POST',body:'{}',headers:{'Content-Type':'application/json'}});await open();facts('condition-run-source',680);await w.startBoundedSource();
 // ABA invalidates late check response even if identity/project return to same values.
 mode='hold';const late=w.boundedAction(c=>w.checkBoundedRun(c,'source'));await wait(()=>release,'held check');
 $('project-select').value=info.other;$('project-select').dispatchEvent(new w.Event('change'));await wait(()=>$('condition-run-source-form').hidden,'project clear');
 $('project-select').value=info.project;$('project-select').dispatchEvent(new w.Event('change'));release();await late;
 check($('condition-run-check-output').textContent===''&&$('condition-run-plan').hidden,'cross-project ABA late response cannot restore stale check/candidate');
 await setup();check($('condition-run-plan').hidden&&$('condition-run-check-output').textContent===''&&!requests.slice(-5).some(r=>r.method==='POST'&&r.path.includes('/conditional-runs')),'cold reload does not restore candidate/PASS or auto-submit');
 await open();facts('condition-run-source',501);mode='bad-source';await w.startBoundedSource();check($('condition-run-start').disabled&&!$('condition-run-retry').hidden,'malformed accepted HTTP200 receipt remains UNKNOWN and cannot unlock new submit');await w.boundedAction(c=>w.boundedSubmit(c,c.pending.phase,{},true));await work('no-provider');await w.boundedAction(w.boundedRead);
 check($('condition-run-output').textContent.includes('WAITING_RESOURCE')&&$('condition-run-check').hidden&&$('condition-run-extract').hidden,'actual default no-provider waits without fictitious completion/check');
 await fetch(info.base+'/test-only-bounded-revoke',{method:'POST',body:'{}',headers:{'Content-Type':'application/json'}});await w.boundedAction(w.boundedRead);
 check($('condition-run-plan').hidden&&$('condition-run-plan-text').textContent===''&&$('condition-run-output').textContent===''&&$('condition-run-cold-output').textContent===''&&$('condition-run-check-output').textContent===''&&$('condition-run-status').textContent.includes('不可核验'),'revoked source refresh clears protected candidate/check evidence');
 const result={status:'PASS',checks,requests,actual_mock_requests:4,live_requests:0,native:'NOT_RUN',pixels:'NOT_RUN'};fs.writeFileSync(path.join(root,'results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}catch(error){console.error(error.stack);process.exitCode=1;}finally{dom?.window.close();}})();
