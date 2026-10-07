'use strict';
const {execFile}=require('node:child_process'),execute=require('node:util').promisify(execFile),assert=require('node:assert/strict');
const python=process.argv[2],root=process.argv[3],sessionFactory=require('/workspace/Sim2Act-conditional-capture/scripts/browser-ci/conditional-fixture-session.cjs');
(async()=>{const results=[];let reference;
for(const mode of ['cli','session','session','cli']){
 const start=Date.now(),session=mode==='session'?sessionFactory({python,root}):null;const times=[];
 try{for(let i=0;i<7;i++){
 const at=Date.now();const reply=session?await session.action('snapshot'):JSON.parse((await execute(python,['scripts/conditional-ui/fixture.py','--root',root,'--action','snapshot'],{env:{...process.env,PYTHONPATH:'src'},encoding:'utf8',timeout:10000})).stdout);
 if(reference)assert.deepEqual(reply,reference);else reference=reply;times.push(Date.now()-at);
 }}finally{if(session)await session.close();}
 results.push({mode,durationMs:Date.now()-start,actions:7,actionMs:times});
}console.log(JSON.stringify({status:'PASS',scope:'same owned database, seven unchanged whole-table snapshot actions, no writes; includes process startup/close',results},null,2));
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
