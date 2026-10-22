'use strict';
// Actual harness cancellation helpers, no VM/DOM/Edge qualification.
const assert=require('node:assert/strict'),{getEventListeners}=require('node:events');
const {stoppedWait,cleanupDeadlines}=require('../scripts/browser-ci/extract-completion.cjs');
async function main(){
 const missing=new AbortController(),budget=Error('GET 31 refused');
 let continued=false;
 const pending=stoppedWait(new Promise(()=>{}),missing.signal).then(()=>continued=true);
 missing.abort(budget);await assert.rejects(pending,error=>error===budget);
 assert.equal(continued,false);assert.equal(getEventListeners(missing.signal,'abort').length,0);
 // A held route and its consumer both leave on the same stop; late delivery
 // cannot resume actions. Attach all consumers before cancellation.
 const held=new AbortController();let release;
 const response=new Promise(resolve=>release=resolve);
 const waits=Promise.all([stoppedWait(response,held.signal),stoppedWait(new Promise(()=>{}),held.signal)]);
 held.abort(budget);await assert.rejects(waits,error=>error===budget);release('late');
 assert.equal(getEventListeners(held.signal,'abort').length,0);
 const failure=new AbortController(),delivery=Error('delivery failed');
 await assert.rejects(stoppedWait(Promise.reject(delivery),failure.signal),error=>error===delivery);
 assert.equal(getEventListeners(failure.signal,'abort').length,0);
 const simultaneous=new AbortController();
 const ready=stoppedWait(Promise.resolve('ready'),simultaneous.signal);
 simultaneous.abort(budget);await assert.rejects(ready,error=>error===budget);
 // Even already-aborted entry handles an independently rejected input.
 await assert.rejects(stoppedWait(Promise.reject(delivery),simultaneous.signal),error=>error===budget);
 const normal=new AbortController();assert.equal(await stoppedWait(Promise.resolve('delivered'),normal.signal),'delivered');
 assert.equal(getEventListeners(normal.signal,'abort').length,0);
 assert.deepEqual(cleanupDeadlines(1000,999999),{shared:11000,node:5000});
 assert.deepEqual(cleanupDeadlines(9990,1000),{shared:11000,node:11000});
 process.stdout.write(JSON.stringify({status:'PASS',scope:'private wait cancellation/deadline algebra only; no DOM',mock:0,business_http:0})+'\n');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
