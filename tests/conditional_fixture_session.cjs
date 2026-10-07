'use strict';
const assert=require('node:assert/strict'),cp=require('node:child_process'),originalSpawn=cp.spawn;
const python=process.argv[2],timers=[],originalTimer=global.setTimeout;
(async()=>{
 for(const mode of ['spawn','exit','wrong','timeout']){
  let child;
  cp.spawn=()=>{child=originalSpawn(mode==='spawn'?'missing-owned-fixture-executable':python,['-c',mode==='exit'?'raise SystemExit(3)':mode==='wrong'?"import sys; sys.stdin.readline(); print('{}',flush=True); sys.stdin.read()":"import sys; sys.stdin.read()"],{stdio:['pipe','pipe','pipe']});return child;};
  global.setTimeout=(fn,ms,...args)=>{timers.push(ms);return originalTimer(fn,mode==='timeout'?20:ms,...args);};
  delete require.cache[require.resolve('../scripts/browser-ci/conditional-fixture-session.cjs')];
  const fixture=require('../scripts/browser-ci/conditional-fixture-session.cjs')({python,root:'test-only-invalid'});
  await assert.rejects(fixture.action('snapshot'),mode==='spawn'?/ENOENT/:mode==='exit'?/exited/:mode==='wrong'?/Wrong conditional fixture reply/:/10000ms/);
  await assert.rejects(fixture.close());
  assert(mode==='spawn'?child.pid===undefined:(child.exitCode!==null||child.signalCode!==null),'owned process collected');
 }
 cp.spawn=originalSpawn;global.setTimeout=originalTimer;
 const safety=require('../scripts/browser-ci/conditional-checks-ui.cjs').assertSandboxSafety;
 const valid=[{type:'browser',security_args_verified:true,command_switches:[]},{type:'renderer',security_args_verified:true,app_container:true,restricted_token:true,integrity_rid:0}];
 safety(valid,(name,ok)=>assert.ok(ok,name),'capture');
 for(const fault of ['args','token','features','missing-renderer']){
  const observed=JSON.parse(JSON.stringify(valid));
  if(fault==='args')observed[1].security_args_verified=false;
  if(fault==='token'){observed[1].app_container=false;observed[1].restricted_token=false;}
  if(fault==='features')observed[0].command_switches=['--disable-features'];
  if(fault==='missing-renderer')observed.pop();
  assert.throws(()=>safety(observed,(name,ok)=>assert.ok(ok,name),'capture'));
 }
 assert(timers.every(ms=>ms===10000),'actual action and cleanup bounds remain10s');
 console.log(JSON.stringify({status:'PASS',cases:['early child exit','invalid reply','action timeout','finally collected owned child'],timeoutMs:10000}));
})().catch(error=>{console.error(error.stack);process.exitCode=1;}).finally(()=>{cp.spawn=originalSpawn;global.setTimeout=originalTimer;});
