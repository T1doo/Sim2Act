'use strict';
const {spawn}=require('node:child_process'),{createInterface}=require('node:readline');
// Owned stdin/stdout control only: no listener, new service, authority or fixture preparation.
module.exports=function fixtureSession({python,root,cwd=process.cwd()}){
 const child=spawn(python,['scripts/conditional-ui/fixture.py','--root',root,'--session'],{cwd,env:{...process.env,PYTHONPATH:'src'},stdio:['pipe','pipe','pipe']});
 const lines=createInterface({input:child.stdout}),timings=[];let pending=null,ended=false,exitCode=null,failure=null;
 const diagnostics={lastRequestedAction:null,lastCompletedAction:null,exitCode:null,stderrBytes:0,stderrTruncated:false,exceptionClass:'UNKNOWN'};let stderrTail='';
 const fail=error=>{failure=error;if(pending){clearTimeout(pending.timer);pending.reject(error);pending=null;}};
 const processError=error=>fail(Error('Owned conditional fixture process error; category=PROCESS_ERROR; code='+(['ENOENT','EACCES','EPIPE'].includes(error.code)?error.code:'UNKNOWN')));
 child.on('error',processError);child.stdin.on('error',processError);child.stderr.on('data',data=>{
  diagnostics.stderrBytes+=data.length;stderrTail=(stderrTail+data.toString('utf8')).slice(-4096);diagnostics.stderrTruncated=diagnostics.stderrBytes>4096;
  const classes=['ValueError','RuntimeError','AssertionError','UnicodeDecodeError','ModuleNotFoundError','ImportError','OperationalError','DomainError','FileNotFoundError'];
  for(const name of classes)if(new RegExp('(?:^|\\n)(?:[A-Za-z_][A-Za-z0-9_]*\\.)*'+name+':').test(stderrTail))diagnostics.exceptionClass=name;
 });
 const exited=new Promise(resolve=>child.on('close',code=>{ended=true;exitCode=code;diagnostics.exitCode=code;if(pending)fail(Error(`Owned conditional fixture exited before reply; action=${diagnostics.lastRequestedAction}; exit=${code}; category=${diagnostics.exceptionClass}; stderrBytes=${diagnostics.stderrBytes}; truncated=${diagnostics.stderrTruncated}`));stderrTail='';resolve();}));
 lines.on('line',line=>{
  if(!pending){fail(Error('Unexpected conditional fixture reply'));child.kill();return;}
  const request=pending;pending=null;clearTimeout(request.timer);
  try{const reply=JSON.parse(line);if(reply.action!==request.name||reply.kind!=='owned-conditional-native-fixture.v1')throw Error('Wrong conditional fixture reply');diagnostics.lastCompletedAction=request.name;timings.push({action:request.name,durationMs:Date.now()-request.start});request.resolve(reply);}
  catch{const error=Error('Wrong conditional fixture reply');fail(error);request.reject(error);child.kill();}
 });
 return {timings,diagnostics,action(name){
  if(!['snapshot','change','restore','revoke','run-source','run-extract','run-cold'].includes(name)||pending||ended||failure)return Promise.reject(failure||Error('Invalid conditional fixture action or lifecycle'));
  diagnostics.lastRequestedAction=name;
  return new Promise((resolve,reject)=>{const start=Date.now();const timer=setTimeout(()=>{fail(Error('Conditional fixture action exceeded unchanged 10000ms limit'));child.kill();},10000);pending={name,start,timer,resolve,reject};child.stdin.write(JSON.stringify({action:name})+'\n');});
 },async close(){
  if(pending)fail(Error('Conditional fixture closed with pending action'));
  child.stdin.end();const timer=setTimeout(()=>child.kill(),10000);
  try{await exited;if(failure)throw failure;if(exitCode!==0)throw Error('Owned conditional fixture did not exit cleanly');}
  finally{clearTimeout(timer);lines.close();}
 }};
};
