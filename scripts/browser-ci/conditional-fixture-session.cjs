'use strict';
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
// Owned stdin/stdout control only: no listener, new service, authority or fixture preparation.
module.exports=function fixtureSession({python,root,cwd=process.cwd()}){
 const child=spawn(python,['scripts/conditional-ui/fixture.py','--root',root,'--session'],{cwd,env:{...process.env,PYTHONPATH:'src'},stdio:['pipe','pipe','pipe']});
 const lines=createInterface({input:child.stdout}),timings=[];let pending=null,ended=false,exitCode=null,failure=null;
 const fail=error=>{failure=error;if(pending){clearTimeout(pending.timer);pending.reject(error);pending=null;}};
 child.on('error',fail);child.stdin.on('error',fail);child.stderr.on('data',()=>{});
 const exited=new Promise(resolve=>child.on('close',code=>{ended=true;exitCode=code;if(pending)fail(Error('Owned conditional fixture exited before reply'));resolve();}));
 lines.on('line',line=>{
  if(!pending){fail(Error('Unexpected conditional fixture reply'));child.kill();return;}
  const request=pending;pending=null;clearTimeout(request.timer);
  try{const reply=JSON.parse(line);if(reply.action!==request.name||reply.kind!=='owned-conditional-native-fixture.v1')throw Error('Wrong conditional fixture reply');timings.push({action:request.name,durationMs:Date.now()-request.start});request.resolve(reply);}
  catch(error){fail(error);request.reject(error);child.kill();}
 });
 return {timings,action(name){
  if(!['snapshot','change','restore','revoke','run-source','run-extract','run-cold'].includes(name)||pending||ended||failure)return Promise.reject(failure||Error('Invalid conditional fixture action or lifecycle'));
  return new Promise((resolve,reject)=>{const start=Date.now();const timer=setTimeout(()=>{fail(Error('Conditional fixture action exceeded unchanged 10000ms limit'));child.kill();},10000);pending={name,start,timer,resolve,reject};child.stdin.write(JSON.stringify({action:name})+'\n');});
 },async close(){
  if(pending)fail(Error('Conditional fixture closed with pending action'));
  child.stdin.end();const timer=setTimeout(()=>child.kill(),10000);
  try{await exited;if(failure)throw failure;if(exitCode!==0)throw Error('Owned conditional fixture did not exit cleanly');}
  finally{clearTimeout(timer);lines.close();}
 }};
};
