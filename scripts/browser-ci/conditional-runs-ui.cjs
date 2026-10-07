'use strict';
const assert=require('node:assert/strict');
// Actual served UI + API + normal Worker; caller retains protected browser ownership.
module.exports=async function boundedRuns({evaluate,reload,info,action}){
 const start=Date.now(),checks=[],timings=[],receipts=[],j=JSON.stringify;
 const check=(ok,name)=>{assert.ok(ok,name);checks.push({name,status:'PASS'});};
 const get=code=>evaluate(code),wait=async(fn,name)=>{const end=Date.now()+12000;while(Date.now()<end){if(await fn())return;await new Promise(r=>setTimeout(r,20));}throw Error('Timeout '+name);};
 const login=async()=>{await get(`$('token').value=${j(info.bearer)};$('connect').click()`);await wait(()=>get(`$('login').hidden&&$('project-select').value===${j(info.project)}`),'bounded login');};
 const watch=()=>get(`window.boundedObserved=[];window.boundedOutside=0;window.boundedHeld=null;window.boundedHold=false;window.boundedFetch=window.fetch;window.fetch=async(url,opts={})=>{const u=new URL(url,location.href);if(u.origin!==location.origin){window.boundedOutside++;throw Error('Outside origin');}window.boundedObserved.push({path:u.pathname,method:opts.method||'GET',body:opts.body?JSON.parse(opts.body):null});const r=await window.boundedFetch(url,opts);if(window.boundedHold&&u.pathname.endsWith('/checks')&&opts.method==='POST'){window.boundedHold=false;if(!r.ok)throw Error('Held real check failed');await new Promise(resolve=>window.boundedHeld=resolve);}return r;};`);
 const phase=async(name,fn)=>{const t=Date.now();await fn();timings.push({phase:name,durationMs:Date.now()-t});};
 const facts=(prefix,amount)=>get(`for(const [k,v]of Object.entries({trip:'true',receipt:'true',approved:'false',amount:${j(String(amount))},days:'2'}))$(${j(prefix)}+'-'+k).value=v;void 0`);
 const read=()=>get('boundedAction(boundedRead)');
 const work=async name=>{const receipt=await action('run-'+name);check(receipt.actual_mock_requests===(name==='source'?2:1)&&receipt.real_model_requests===0&&receipt.report_origin==='hand-authored-test-only',name+' uses normal Worker with bounded hand-authored MockTransport');receipts.push(receipt);};
 await reload();await watch();await login();
 const before=await action('snapshot');
 check(await get(`!window.boundedObserved.some(r=>r.path.includes('/conditional-runs'))`),'cold document never automatically creates reads or checks a bound Run');
 await get(`listConditionalSources()`);await get(`$('condition-resource').value=${j(info.source)};openConditionalSource()`);
 check(await get(`!$('condition-run-source-form').hidden`),'explicit authorized source opens separate actual Run form');
 await phase('source',async()=>{
  await facts('condition-run-source',680);await get(`$('condition-decision').value='ALLOW';$('condition-explanation').value='Unrelated manual Report';startBoundedSource()`);
  check(await get(`$('condition-run-output').textContent.includes('QUEUED')&&$('condition-run-check').hidden&&$('condition-run-extract').hidden`),'queued source cannot expose check or extraction eligibility');
  check(await get(`(()=>{const b=window.boundedObserved.find(r=>r.path.endsWith('/conditional-runs/source')).body;return b.resource_id===${j(info.source)}&&b.scenario.amount===680&&!('report'in b)&&!('candidate'in b)&&!('gold'in b);})()`),'source submission excludes manual Report candidate and gold');
  await work('source');await read();
  check(await get(`$('condition-run-output').textContent.includes('WAITING_APPROVAL')&&$('condition-run-output').textContent.includes('BLOCK')&&$('condition-run-output').textContent.includes('UNKNOWN')&&$('condition-run-output').textContent.includes('NOT_ACCEPTED')`),'actual source Report BLOCK remains semantic UNKNOWN and overall NOT_ACCEPTED');
  await get(`boundedAction(c=>checkBoundedRun(c,'source'))`);
  check(await get(`$('condition-run-check-output').textContent.includes('有限报告检查 PASS')&&!$('condition-run-extract').hidden`),'independent bound source finite PASS enables only extraction');
 });
 await phase('extract',async()=>{
  await get('extractBoundedCandidate()');await work('extract');await read();
  check(await get(`!$('condition-run-plan').hidden&&$('condition-run-plan-text').textContent.includes('candidate_receipt')&&$('condition-run-plan-text').textContent.includes('read_rules')&&$('condition-run-plan-text').textContent.includes('check_report')`),'actual sealed candidate receipt and registered finite DAG displayed');
  check(await get(`(()=>{const b=window.boundedObserved.find(r=>r.path.endsWith('/conditional-runs/extract')).body;return b.source_run_id===boundedRunContext.sourceRun.run_id&&b.expected_source_fingerprint===boundedRunContext.sourceRun.result_fingerprint&&!('candidate'in b);})()`),'extraction binds current source result rather than client invented candidate');
 });
 await phase('cold',async()=>{
  await facts('condition-run-cold',500);await get(`$('condition-run-cold-resource').value=${j(info.source)};startBoundedCold()`);await work('cold');await read();await get(`boundedAction(c=>checkBoundedRun(c,'cold'))`);
  check(await get(`$('condition-run-cold-output').textContent.includes('ALLOW')&&$('condition-run-cold-output').textContent.includes('NOT_ACCEPTED')&&$('condition-run-cold-check-output').textContent.includes('有限报告检查 PASS')`),'same-resource new-Scenario 500 cold ALLOW has independent finite PASS and stays NOT_ACCEPTED');
  check(await get(`(()=>{const b=window.boundedObserved.find(r=>r.path.endsWith('/conditional-runs/cold')).body;return b.resource_id===${j(info.source)}&&b.scenario.amount===500&&b.extraction_run_id===boundedRunContext.extractRun.run_id&&!('report'in b);})()`),'cold binds explicit scenario and sealed extraction without a supplied Report');
 });
 await get(`window.boundedHold=true;window.boundedLate=boundedAction(c=>checkBoundedRun(c,'cold'));void 0`);await wait(()=>get('!!window.boundedHeld'),'held actual cold check');
 await get(`$('condition-run-cold-amount').value='501';$('condition-run-cold-amount').dispatchEvent(new Event('input',{bubbles:true}));window.boundedHeld();window.boundedLate`);
 check(await get(`!$('condition-run-cold-output').textContent&&!$('condition-run-cold-check-output').textContent&&$('condition-run-cold-check').hidden`),'fact editing rejects late actual cold check evidence');
 await get(`window.boundedHold=true;window.boundedLate=boundedAction(c=>checkBoundedRun(c,'source'));void 0`);await wait(()=>get('!!window.boundedHeld'),'held actual source check');
 await get(`$('project-select').value=${j(info.other_project)};$('project-select').dispatchEvent(new Event('change'));$('project-select').value=${j(info.project)};$('project-select').dispatchEvent(new Event('change'));window.boundedHeld();window.boundedLate`);
 check(await get(`!$('condition-run-check-output').textContent&&$('condition-run-plan').hidden&&!$('condition-run-plan-text').textContent`),'project A-B-A cannot revive late source check or sealed candidate');
 const after=await action('snapshot');
 check(after.attempts_count-before.attempts_count===4&&after.resource_reads_count-before.resource_reads_count===2,'durable bound chain records exactly four attempts and two successful resource reads');
 check(before.principals===after.principals&&j(before.grants)===j(after.grants)&&before.tables.grants===after.tables.grants&&before.tables.resources===after.tables.resources,'bound chain creates no identity Grant or material mutation');
 check(await get(`window.boundedOutside===0&&!window.boundedObserved.some(r=>r.method==='POST'&&!r.path.includes('/conditional-runs/'))`),'bound UI performs only same-origin explicit conditional Run actions');
 await reload();await watch();await login();
 check(await get(`$('condition-run-plan').hidden&&!$('condition-run-check-output').textContent&&!window.boundedObserved.some(r=>r.path.includes('/conditional-runs'))`),'cold reload neither restores evidence nor creates a new Run');
 return {namespace:'conditional-bound-run-native.v1',status:'PASS',checks,timings,durationMs:Date.now()-start,receipts,actual_mock_requests:4,real_model_requests:0,semanticStatus:'UNKNOWN',overallAcceptance:'NOT_ACCEPTED',formalPublication:false,coldScope:'same-resource/new-Scenario',screenshots:[],durable:{before,after}};
};
