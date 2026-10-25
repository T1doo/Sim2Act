'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict'),{JSDOM,VirtualConsole}=require('jsdom'),adapter=require('../../../scripts/browser-ci/goal-history-state.cjs');
const fixture=JSON.parse(fs.readFileSync('docs/evidence/goal-history-visual-candidate-20261025/fixture.json')),errors=[],calls=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(fs.readFileSync('src/sim2act/web/index.html','utf8'),{url:'http://synthetic.invalid',runScripts:'dangerously',virtualConsole:vc}),w=dom.window,d=w.document;
(async()=>{try{
 w.setInterval=()=>0;w.fetch=async(url,opts={})=>{const method=opts.method||'GET';assert.equal(method,'GET');calls.push({url,method});let value=adapter.responseFor(fixture,method,url);if(value===undefined){assert.equal(url,`/api/projects/${fixture.project}/natural-planning-status`);value={provider:'disabled',live_request_allowance:0,available:false,reason:'PROVIDER_DISABLED'};}return {ok:true,status:200,json:async()=>value};};
 for(const n of ['app.js','natural-goal.js']){const s=d.createElement('script');s.textContent=fs.readFileSync('src/sim2act/web/'+n,'utf8');d.body.append(s);}
 d.getElementById('project-select').append(new w.Option('Synthetic',fixture.project));w.eval("token='secret test token';");await w.refreshGoalCards(fixture.project);await d.querySelector('#goal-card-list button').onclick();
 assert(d.getElementById('goal-candidate-status').textContent.startsWith('本切片'));assert.equal(w.eval('activeGoalCard.version'),3);assert.equal(d.getElementById('goal-card-history').querySelectorAll('button').length,3);
 const count=calls.length;d.querySelector('#goal-card-history button').click();assert.equal(calls.length,count);assert(d.getElementById('goal-card-history-detail').textContent.includes('只读历史版本 v1'));assert.equal(w.eval('activeGoalCard.version'),3);
 w.fixture=fixture;w.eval("trialEntries.set(trialIndex(trialContext()),fixture.trial);renderTrialConsent();");assert(d.getElementById('trial-consent').disabled);assert(!d.getElementById('trial-recover').disabled);assert(d.getElementById('trial-status').textContent.includes('UNKNOWN'));assert.deepEqual(errors,[]);
 console.log(JSON.stringify({status:'PASS',classification:'NEW_ADAPTER_HANDSHAKE_DOM_ONLY_NOT_PIXELS',calls,historyExtraRequests:0,models:0,http:0}));
}finally{dom.window.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
