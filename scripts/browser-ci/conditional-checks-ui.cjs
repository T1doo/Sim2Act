'use strict';
const assert=require('node:assert/strict');
// Shared actual served UI oracle. Caller owns browser protection, fixture and transport.
module.exports=async function conditionalChecks({evaluate,reload,info,action,capture}){
 const started=Date.now(),checks=[],json=JSON.stringify;
 const result={status:'NOT_RUN',checks,real_model_requests:0,semanticStatus:'UNKNOWN',ownerAcceptance:'PENDING',formalPublication:false,browser:'CALLER_OWNED',visualReview:'NOT_REVIEWED',screenshots:[]};
 const get=code=>evaluate(code),check=(ok,name)=>{assert.ok(ok,name);checks.push({name,status:'PASS'});};
 const wait=async(fn,name)=>{const end=Date.now()+12000;while(Date.now()<end){if(await fn())return;await new Promise(r=>setTimeout(r,20));}throw Error('Timeout '+name);};
 const watch=()=>get(String.raw`window.conditionObserved=[];window.conditionPosts=0;window.conditionOutside=0;window.conditionHeld=null;window.conditionHold=false;window.conditionFail=false;window.conditionOriginalFetch=window.fetch;
 window.fetch=async(url,opts={})=>{const u=new URL(url,location.href);if(u.origin!==location.origin){window.conditionOutside++;throw Error('Outside origin');}window.conditionObserved.push({path:u.pathname,method:opts.method||'GET'});
 if(u.pathname.endsWith('/conditional-checks')&&opts.method==='POST'){window.conditionPosts++;if(window.conditionFail){window.conditionFail=false;throw TypeError('Synthetic conditional transport read failure');}}
 const r=await window.conditionOriginalFetch(url,opts);if(window.conditionHold&&u.pathname.endsWith('/conditional-checks')&&opts.method==='POST'){window.conditionHold=false;if(r.status!==200)throw Error('Expected actual200 held');await new Promise(resolve=>window.conditionHeld=resolve);}return r;};`);
 const login=async()=>{await get(`$('token').value=${json(info.bearer)};$('connect').click()`);await wait(()=>get(`$('login').hidden&&$('token').value===''&&$('project-select').options.length>0`),'authenticated connection');await selectProject(info.project);await get(`document.querySelector('[data-tab="apps"]').click()`);};
 const selectProject=async id=>{await get(`$('project-select').value=${json(id)};$('project-select').dispatchEvent(new Event('change'))`);await wait(()=>get(`$('project-select').value===${json(id)}&&$('run-history-status').textContent!==''&&!$('run-history-status').textContent.includes('正在')`),'current project ready');};
 const open=async id=>{await get(`listConditionalSources()`);await get(`$('condition-resource').value=${json(id)};openConditionalSource()`);};
 const manual=async unknown=>get(`for(const [k,v] of Object.entries(${json({trip:unknown?'':'true',amount:unknown?'':'680',receipt:unknown?'':'true',approved:unknown?'':'false',days:unknown?'':'2',R1:unknown?'UNKNOWN':'TRUE',R2:unknown?'UNKNOWN':'TRUE',R3:unknown?'UNKNOWN':'FALSE',decision:unknown?'UNKNOWN':'BLOCK',deadline:'10',date:'UNKNOWN',restart:'false',explanation:'Hand-entered synthetic report; free prose is not graded.'})}))$('condition-'+k).value=v;for(const o of $('condition-actions').options)o.selected=o.value===${json(unknown?'clarify_facts':'obtain_prior_approval')};void 0`);
 const run=()=>get('runConditionalCheck()');
 const captureReport=async(label,decision)=>{
  if(!capture)return;
  const source=await get('({resource_id:conditionalContext.source.resource_id,hash:conditionalContext.source.hash,contract_id:conditionalContext.source.contract.id,contract_version:conditionalContext.source.contract.version,contract_fingerprint:conditionalContext.source.contract.fingerprint})');
  result.screenshots.push(await capture(label,{scope:'conditional-hand-report',source,checkStatus:'PASS',decision,semanticStatus:'UNKNOWN',ownerAcceptance:'PENDING',formalPublication:false}));
 };
 const tables=(before,after,allowed=[])=>Object.keys(before.tables).filter(k=>before.tables[k]!==after.tables[k]&&!allowed.includes(k));
 await reload();await watch();await login();
 const before=await action('snapshot');
 check(await get(`!window.conditionObserved.some(r=>r.path.includes('/conditional-checks/sources/'))`),'conditional content is never automatically read');
 await open(info.cold);check(await get(`$('condition-form').hidden&&$('condition-status').textContent.includes('VERSION_CONFLICT')&&!$('condition-source').textContent`),'unsupported source refused without substituting a gold answer');
 await open(info.source);check(await get(`!$('condition-form').hidden&&$('condition-source').textContent.includes(${json(info.source)})&&$('condition-source').textContent.includes('SHA256')&&$('condition-source').textContent.includes('第4行')`),'authorized actual source hash contract version and quotes displayed');
 await manual(false);await run();
 check(await get(`$('condition-results').textContent.includes('报告核对 PASS')&&$('condition-results').textContent.includes('决策 BLOCK')&&$('condition-results').textContent.includes('R2：不满足')&&$('condition-results').textContent.includes('未核查报销单和收据是否已实际提交')`),'valid unmet-condition report separates PASS from submission BLOCK and completed obligations');
 check(await get(`$('condition-results').textContent.includes('语义 UNKNOWN；用户确认 PENDING')&&$('condition-results').textContent.includes('NOT_CHECKED')`),'semantic owner and free prose are never promoted by a finite check');
 await captureReport('protocol-desktop','BLOCK');
 // Preserve actual interval, unlike the old history helper's isolated polling mode.
 const stable=await get(`$('condition-results').textContent`);await new Promise(r=>setTimeout(r,2700));
 check(await get(`$('condition-amount').value==='680'&&$('condition-results').textContent===${json(stable)}`),'actual 2500ms poll retains unchanged inputs and evidence');
 await get(`$('condition-amount').value='500';$('condition-amount').dispatchEvent(new Event('input',{bubbles:true}));void 0`);
 check(await get(`!$('condition-results').textContent&&$('condition-recheck').hidden`),'editing facts immediately invalidates the old report');
 await run();check(await get(`$('condition-results').textContent.includes('报告核对 FAIL')&&$('condition-results').textContent.includes('R2：不适用')&&$('condition-results').textContent.includes('语义 UNKNOWN；用户确认 PENDING')`),'incorrect hand report stays FAIL and never changes semantic or owner acceptance');
 await manual(true);await run();check(await get(`$('condition-results').textContent.includes('报告核对 PASS')&&$('condition-results').textContent.includes('决策 UNKNOWN')&&$('condition-results').textContent.includes('R1：未知')`),'unknown facts remain UNKNOWN despite structurally correct report');
 await captureReport('protocol-narrow','UNKNOWN');
 await get(`window.conditionFail=true;runConditionalCheck(true)`);check(await get(`!$('condition-results').textContent&&!$('condition-source').textContent&&$('condition-status').textContent.includes('请求失败不等于业务条件不满足')`),'technical failure clears evidence without declaring a business-rule failure');
 await open(info.source);await manual(false);await run();
 const readOnly=await action('snapshot');check(tables(before,readOnly).length===0,'all persistent tables unchanged by source reads and repeated check POSTs');
 const changed=await action('change');check(tables(readOnly,changed,['resources']).length===0&&readOnly.tables.resources!==changed.tables.resources,'controlled version change alters only existing source resource');
 await get('runConditionalCheck(true)');check(await get(`!$('condition-results').textContent&&!$('condition-source').textContent&&($('condition-status').textContent.includes('VERSION_CONFLICT')||$('condition-status').textContent.includes('旧证据失效'))`),'changed actual source version invalidates old PASS and quotes');
 const restored=await action('restore');check(tables(before,restored).length===0,'exact original public source restored with all other tables intact');
 await open(info.source);await manual(false);await get(`window.conditionHold=true;window.conditionLate=runConditionalCheck();void 0`);await wait(()=>get('!!window.conditionHeld'),'actual200 held');
 await selectProject(info.other_project);await selectProject(info.project);await get('window.conditionHeld();window.conditionLate');
 check(await get(`!$('condition-results').textContent&&!$('condition-source').textContent&&$('condition-form').hidden`),'project A-B-A cannot revive a held old report');
 await reload();await watch();await login();check(await get(`window.conditionPosts===0&&$('condition-form').hidden&&!$('condition-results').textContent`),'cold actual document never submits or revives a prior report');
 await open(info.source);await manual(false);await run();
 const prior=await action('snapshot');check(tables(before,prior).length===0,'cold reopened report still makes no persisted changes');
 const revoked=await action('revoke');check(tables(prior,revoked,['grants']).length===0&&prior.tables.grants!==revoked.tables.grants,'fixture revokes only an existing read grant and never creates authority');
 await get('runConditionalCheck(true)');check(await get(`!$('condition-results').textContent&&!$('condition-source').textContent&&($('condition-status').textContent.includes('GRANT_REVOKED')||$('condition-status').textContent.includes('旧证据失效'))`),'actual revocation hides quotes and old evidence');
 await get('listConditionalSources()');check(await get(`![...$('condition-resource').options].some(o=>o.value===${json(info.source)})`),'revoked source absent from authorized metadata choices');
 const after=await action('snapshot');check(tables(revoked,after).length===0&&before.principals===after.principals&&json(before.grants)===json(after.grants),'all other durable records and existing authority identities retained');
 check(await get(`window.conditionOutside===0&&!window.conditionObserved.some(r=>r.method==='POST'&&!r.path.endsWith('/conditional-checks'))`),'conditional UI creates no business Run Grant identity model or outside-origin request');
 result.status='PASS';result.durationMs=Date.now()-started;result.durable={before,after};
 result.expectedNegativeURLs=[`/api/projects/${info.project}/conditional-checks/sources/${info.cold}`,`/api/projects/${info.project}/conditional-checks`];
 result.mutations=['only existing synthetic source content/hash changed and exactly restored','only one existing source user-read grant revoked; no grant restored or created'];
 return result;
};

// Same actual protection oracle for before/after and the exact screenshot observation.
module.exports.assertSandboxSafety=function(observed,check,label){
 check(`${label} actual args preserve existing browser protections`,observed.length>0&&observed.every(p=>p.security_args_verified));
 const renderer=observed.filter(p=>p.type==='renderer');
 check(`${label} renderer tokens remain protected`,renderer.length>0&&renderer.every(p=>p.app_container||(p.restricted_token&&p.integrity_rid<=4096)));
 const main=observed.find(p=>p.type==='browser');
 check(`${label} SDK weakening absent`,!!main&&!main.command_switches.includes('--disable-features'));
};
