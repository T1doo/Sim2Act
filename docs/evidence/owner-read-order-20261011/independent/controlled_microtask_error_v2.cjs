"use strict";
// Explicit microtask scheduling of actual local-source ownerRead and its initial caller.
// No HTTP, Worker, live provider, real owner declaration, or native browser.
const fs=require('fs'),assert=require('assert/strict'),crypto=require('crypto'),{JSDOM}=require('jsdom');
const root='/tmp/owner-read-order-review-20261011/',base='/workspace/Sim2Act/src/sim2act/web/';
const source=fs.readFileSync(base+'owner-review.js','utf8'),internal=fs.readFileSync(base+'internal.js','utf8');
const engineeringCurrent=internal.match(/function engineeringCurrent\(view\) \{[\s\S]*?\n\}/)[0];
const dom=new JSDOM(fs.readFileSync(base+'index.html','utf8'),{runScripts:'outside-only',url:'http://controlled.invalid/'}),w=dom.window;
w.$=id=>w.document.getElementById(id);w.safe=fn=>fn;w.token='synthetic';w.activeApp='controlled-app';w.appSelectionGeneration=9;w.workspaceSelectionGeneration=3;
w.$('project-select').append(new w.Option('project','controlled-project'));w.$('project-select').value='controlled-project';
w.engineering={token:w.token,project:'controlled-project',app:w.activeApp,appGeneration:9,instanceGeneration:1,instance:{id:'controlled-instance',principal_id:'controlled-principal',runs:[]}};
w.pending=[];w.events=[];
w.eval("globalThis.api=path=>new Promise((resolve,reject)=>{pending.push({resolve,reject,path});events.push('api GET '+pending.length);});");
const pending=w.pending,events=w.events;
w.eval(engineeringCurrent+'\n'+source+'\nglobalThis.probe={initial(){return openOwnerReview(globalThis.engineering);},read(){return ownerRead(ownerView);},generation(){return ownerView.readGeneration;}};');
(async()=>{
 const initial=w.probe.initial();assert.equal(pending.length,1);
 pending[0].reject(Error('OLD INITIAL ERROR'));
 queueMicrotask(()=>{
  events.push('newer read starts between inner throw and outer caller catch');
  w.probe.read();w.$('owner-status').textContent='NEWER READ ACTIVE';
  events.push('newer generation='+w.probe.generation());
 });
 await initial;events.push('initial outer caller completed');
 const status=w.$('owner-status').textContent,staleErrorInstalled=status.includes('OLD INITIAL ERROR');
 const output={classification:'CONTROLLED_LOCAL_SOURCE_JSDOM_MICROTASK',source_sha256:crypto.createHash('sha256').update(source).digest('hex'),http:'NOT_RUN',native_browser:'NOT_RUN',live_model_requests:0,real_owner_semantic_signoff:'NOT_RUN',cases:[{name:'initial caller ignores old error after a newer read starts',expected:'NEWER READ ACTIVE preserved',actual_status:status,read_generation:w.probe.generation(),get_calls:pending.length,events,status:staleErrorInstalled?'FAIL':'PASS'}],status:staleErrorInstalled?'FAIL':'PASS'};
 fs.writeFileSync(root+'microtask-error-red-v2.json',JSON.stringify(output,null,2)+'\n');dom.window.close();
 console.log(JSON.stringify({status:output.status,actual_status:status,read_generation:output.cases[0].read_generation,get_calls:pending.length}));
 assert.equal(staleErrorInstalled,false,'older initial caller catch installed an error after newer read generation started');
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
