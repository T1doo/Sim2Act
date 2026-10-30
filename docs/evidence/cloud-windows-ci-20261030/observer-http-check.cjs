'use strict';
// Real loopback HTTP verifies only observation budgets; this is not a product Run.
const assert=require('node:assert/strict'),http=require('node:http'),fs=require('node:fs'),crypto=require('node:crypto'),{execFileSync}=require('node:child_process');
const repo='/workspace/Sim2Act',candidate=fs.readFileSync(repo+'/scripts/browser-ci/desktop-workspace.cjs','utf8');
const baseline=execFileSync('git',['show','9bf5d6218dc3064b8beb6a031630bbad95fa23db:scripts/browser-ci/desktop-workspace.cjs'],{cwd:repo,encoding:'utf8'});
const counts={},timers=new Set(),results={scope:'Actual loopback observer HTTP only; no browser, model, product save or Windows acceptance',checks:[]};
const delay=(res,ms,body)=>{const timer=setTimeout(()=>{timers.delete(timer);res.end(body);},ms);timers.add(timer);res.on('close',()=>{clearTimeout(timer);timers.delete(timer);});};
const server=http.createServer((req,res)=>{
 const route=req.url;counts[route]=(counts[route]||0)+1;
 assert.equal(req.headers.authorization,'Bearer synthetic-local-observer');
 res.setHeader('Content-Type','application/json');
 if(route.includes('/spec-run-requests/'))return delay(res,16000,'{"status":"SUCCEEDED"}');
 if(route==='/slow'||route==='/global')return delay(res,350,'{"status":"SUCCEEDED"}');
 if(route==='/body'){res.writeHead(200);res.flushHeaders();return delay(res,350,'{"status":"SUCCEEDED"}');}
 if(route==='/denied'){res.statusCode=403;return res.end('{}');}
 if(route==='/bad-json')return res.end('{');
 if(route==='/pending')return res.end('{"status":"RUNNING"}');
 res.statusCode=404;res.end('{}');
});
function load(source,base,deadline=Date.now()+155000){
 const until=source.slice(source.indexOf('async function until('),source.indexOf('async function start('));
 const reads=source.slice(source.indexOf('async function readJSON('),source.indexOf('async function layout('));
 const result={};
 const api=new Function('assert','result','owned','workDeadline','info','originalKey',until+reads+';return {until,readJSON,status};')(assert,result,{ready:{url:base,public_token:'synthetic-local-observer'}},deadline,{spec_instance:'instance_synthetic'},'key_synthetic');
 return {...api,result};
}
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const base='http://127.0.0.1:'+server.address().port;
 try{
  const old=load(baseline,base),fixed=load(candidate,base),started=Date.now();
  const before=old.until(async()=>await old.status()==='SUCCEEDED','worker observation',30000).then(()=>({success:true}),e=>({success:false,error:e.name,elapsed_ms:Date.now()-started}));
  const after=fixed.until(async end=>await fixed.status(end)==='SUCCEEDED','worker observation',30000).then(()=>({success:true,elapsed_ms:Date.now()-started}));
  const [a,b]=await Promise.all([before,after]);
  assert.equal(a.success,false);assert.equal(a.error,'TimeoutError');assert(a.elapsed_ms>=14000&&a.elapsed_ms<18000);
  assert.equal(b.success,true);assert(b.elapsed_ms>=16000&&b.elapsed_ms<25000);
  assert.equal(counts['/api/internal/instances/instance_synthetic/spec-run-requests/key_synthetic'],2);
  results.slow_response={baseline:a,candidate:b,observations:fixed.result.read_observations};results.checks.push('16-second real HTTP response fails old15s but succeeds inside unchanged30s observation; one GET per version');
  let t=Date.now();await assert.rejects(fixed.until(async end=>(await fixed.readJSON(base+'/slow',end)).status==='SUCCEEDED','short observation',100));assert(Date.now()-t<1000);assert.equal(counts['/slow'],1);results.checks.push('Observation deadline aborts one slow GET; no retry');
  const global=load(candidate,base,Date.now()+80);t=Date.now();await assert.rejects(global.until(async end=>(await global.readJSON(base+'/global',end)).status==='SUCCEEDED','short global deadline',500));assert(Date.now()-t<1000);assert.equal(counts['/global'],1);results.checks.push('Shorter global deadline wins over observation deadline');
  await assert.rejects(fixed.until(async()=>{await new Promise(r=>setTimeout(r,80));return true;},'late success',20),/Timeout late success/);results.checks.push('Late true cannot pass after deadline');
  await assert.rejects(fixed.until(async end=>fixed.readJSON(base+'/denied',end),'denied',500));assert.equal(counts['/denied'],1);results.checks.push('Non200 fails without retry');
  await assert.rejects(fixed.until(async end=>fixed.readJSON(base+'/bad-json',end),'bad JSON',500));assert.equal(counts['/bad-json'],1);results.checks.push('Invalid JSON fails without retry');
  t=Date.now();await assert.rejects(fixed.until(async end=>fixed.readJSON(base+'/body',end),'body deadline',100));assert(Date.now()-t<1000);assert.equal(counts['/body'],1);results.checks.push('HTTP body parsing shares deadline after headers');
  await assert.rejects(fixed.until(async end=>(await fixed.readJSON(base+'/pending',end)).status==='SUCCEEDED','unfinished',150),/Timeout unfinished/);results.checks.push('RUNNING cannot pass completion assertion');
  results.status='PASS';results.candidate_sha256=crypto.createHash('sha256').update(candidate).digest('hex');results.requests=counts;
 }catch(error){results.status='FAIL';results.error=error.stack;process.exitCode=1;}
 finally{for(const timer of timers)clearTimeout(timer);server.closeAllConnections();await new Promise(resolve=>server.close(resolve));fs.writeFileSync('/workspace/scratch/desktop-observer-http-20261030.json',JSON.stringify(results,null,2));console.log(JSON.stringify(results));}
})().catch(e=>{console.error(e);process.exitCode=1;});
