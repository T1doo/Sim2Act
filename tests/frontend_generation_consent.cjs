'use strict';
// Isolated real consent controller, synthetic API. No browser, worker or model.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const nodes=new Map(),calls=[];let current=true,lost=false;
const card={id:'goal_test',version:1,fingerprint:'fingerprint',snapshot:{content:{goal:'frozen'}}};
const node=id=>{if(!nodes.has(id))nodes.set(id,{value:'',checked:false});return nodes.get(id);};
node('project-select').value='project';
const context={console,Map,URLSearchParams,structuredClone,crypto:require('node:crypto').webcrypto,
 $:node,goalApplicationKey:()=> 'key',goalApplications:new Map(),generationConsents:new Map(),goalCardLoading:false,goalCardSaving:false,
 activeGoalCard:card,goalSpecFamily:()=>false,paContext:()=>({current:()=>current}),
 goalRunCanonical:JSON.stringify,paHash:async()=> 'seal'};
let prepared,approval;
context.api=async(path,method,body)=>{
 calls.push({path,method,body});
 if(method==='POST'&&path.endsWith('/approve')){approval={...prepared,activation:{approval_id:'aid'},deadline:123};if(lost)throw Error('lost response');return approval;}
 if(method==='POST')return prepared={approval_id:'aid',scope_fingerprint:'seal',scope:{version:'pa-intern-generation-approval.v3',execution_selection:'approved-run',metadata:{approval_id:'aid',project_id:'project'},request:body,source:{card_id:card.id,version:1,fingerprint:card.fingerprint,snapshot:card.snapshot}}};
 return path.includes('approval_request_key')?approval:prepared;
};
vm.createContext(context);
const source=fs.readFileSync('src/sim2act/web/goal-application.js','utf8');
vm.runInContext(source.slice(source.indexOf('// A consent intent is immutable.')),context);
(async()=>{
 await node('goal-provider-prepare').onclick();
 assert.equal(calls.length,1);
 await node('goal-provider-prepare').onclick();assert.equal(calls.length,1);
 await node('goal-provider-approve').onclick();assert.equal(calls.length,1,'unchecked consent sends nothing');
 node('goal-provider-approve-ack').checked=true;lost=true;
 await node('goal-provider-approve').onclick();assert.equal(calls.length,2);
 await node('goal-provider-approve').onclick();assert.equal(calls.length,2,'unknown POST never resends');
 await node('goal-provider-recover').onclick();assert.equal(calls.length,3);
 assert.equal(calls[2].method,undefined,'recovery is GET only');
 assert(calls[2].path.includes('approval_request_key='));
 assert(node('goal-provider-consent-status').textContent.includes('授权回执已恢复'));
 current=false;await node('goal-provider-recover').onclick();assert.equal(calls.length,3,'stale context sends nothing');
 // Simulate page memory loss while preserving only the user-copied original keys.
 current=true;context.generationConsents.clear();
 await node('goal-provider-cold-read').onclick();
 assert.equal(calls.length,4);assert.equal(calls[3].method,undefined);
 assert.equal(context.generationConsents.size,1);
 assert.equal(node('goal-provider-approve-ack').checked,false);
 assert.equal(node('goal-provider-approve').disabled,true,'restored approval cannot be reposted');
 assert.equal(context.generationConsents.get('key').prepared.deadline,123,'cold read retains original deadline');
 console.log(JSON.stringify({status:'PASS',cases:['prepare once','unchecked denied','lost approval retained','no POST retry','keyed GET recovery','stale context denied','cold keyed recovery','no renewed deadline or repeated consent'],real_model:'NOT_RUN'}));
})().catch(error=>{console.error(error);process.exitCode=1;});
