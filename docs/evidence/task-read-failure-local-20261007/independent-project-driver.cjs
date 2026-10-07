'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {JSDOM}=require('jsdom');
const root=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(root,'info.json')));
const checks=[],requests=[];
const check=(ok,name)=>{assert(ok,name);checks.push(name);};
const wait=async(fn,name)=>{const end=Date.now()+5000;while(Date.now()<end){if(fn())return;await new Promise(r=>setTimeout(r,10));}throw Error('Timeout '+name);};
let dom;
(async()=>{try{
 dom=new JSDOM(await(await fetch(info.base)).text(),{url:info.base,runScripts:'dangerously'});
 const w=dom.window,$=id=>w.document.getElementById(id);
 let poll;
 w.setInterval=fn=>{poll=fn;return 0;};w.Response=Response;
 let mode='normal',release=null;
 w.fetch=async(url,opts={})=>{
  const target=new URL(url,info.base);assert.equal(target.origin,info.base);
  requests.push({path:target.pathname,method:opts.method||'GET'});
  const detail=target.pathname==='/api/runs/'+info.first;
  const held=mode;
  if(detail&&['hold','hold-fail'].includes(held)){
   mode='normal';const response=await fetch(target,opts);
   await new Promise(resolve=>{release=resolve;});release=null;
   if(held==='hold-fail')throw TypeError('Synthetic lost read after real response');return response;
  }
  if(detail&&held==='lost'){mode='normal';await fetch(target,opts);throw TypeError('Synthetic lost read after real response');}
  if(detail&&held==='waiting'){const response=await fetch(target,opts),data=await response.json();data.status='WAITING_RESOURCE';return new Response(JSON.stringify(data));}
  if(target.pathname==='/api/runs/'+info.first+'/unresolved-attempts'&&held==='waiting'){
   mode='normal';return fetch(target,{...opts,headers:{...opts.headers,Authorization:'Bearer synthetic-test-B'}});
  }
  return fetch(target,opts);
 };
 for(const file of ['app.js','internal.js','protocol.js']){const el=w.document.createElement('script');el.textContent=await(await fetch(info.base+'/'+file)).text();w.document.body.append(el);}
 const evaluate=code=>w.eval(code),open=id=>w.showRun(id);
 const empty=()=>!$('raw-result').textContent&&!$('events').textContent&&!$('commands').textContent&&$('reconcile-panel').hidden&&evaluate('unresolvedAttempts.length===0&&reconcileVersion===null');
 $('token').value='synthetic-test-A';$('connect').click();await wait(()=>$('runs').textContent.includes('Read recovery verified receipt'),'connect');
 await open(info.first);
 check($('result').textContent.includes('部分完成')&&$('raw-result').textContent.includes('VERIFIED'),'real normal Mock partial receipt visible');
 mode='hold';const held=open(info.first);await wait(()=>!!release,'held detail');
 check(empty()&&$('result').textContent==='正在读取任务…','explicit selection clears prior detail while read is pending');
 release();await held;
 check($('raw-result').textContent.includes(info.first),'held successful read restores same persisted task');
 mode='lost';await assert.rejects(open(info.first),/Synthetic lost read/);
 check(empty()&&evaluate('activeRun===null')&&$('run-read-failure').textContent.includes('读取失败不表示任务执行失败'),'lost read clears data without inventing task FAILED');
 const beforePoll=requests.filter(r=>r.path==='/api/runs/'+info.first).length;
 await poll();check(requests.filter(r=>r.path==='/api/runs/'+info.first).length===beforePoll,'failed detail is not automatically re-read by existing poll');
 const retry=$('run-read-failure').querySelector('button');retry.click();await wait(()=>$('raw-result').textContent.includes(info.first),'explicit read retry');
 check($('result').textContent.includes('部分完成')&&!$('run-read-failure'),'explicit retry restores real task status');
 await assert.rejects(open(info.foreign),/PERMISSION_DENIED/);
 check(empty()&&$('run-read-failure').textContent.includes('没有读取此任务或核对回执的权限')&&!$('result').textContent.includes('Foreign task'),'real cross-identity HTTP403 leaves no old or foreign receipt');
 await open(info.first);
 mode='waiting';await assert.rejects(open(info.first),/PERMISSION_DENIED/);
 check(empty()&&!$('run-progress')&&$('run-read-failure').textContent.includes('权限'),'real unresolved API403 after synthetic waiting projection clears entire detail');
 mode='normal';await open(info.first);
 mode='hold-fail';const late=open(info.first);await wait(()=>!!release,'held late failure');await open(info.second);release();await late;
 check($('raw-result').textContent.includes(info.second)&&!$('run-read-failure'),'late failed prior selection cannot clear newer queued task');
 const pendingOldCommand=$('commands').querySelector('button');
 $('project-select').value=info.other;$('project-select').dispatchEvent(new w.Event('change'));
 await wait(()=>$('run-history-status').textContent.includes('暂无任务'),'direct project switch from queued task');
 check(!$('commands').textContent,'direct project switch clears queued task commands');
 fs.writeFileSync(path.join(root,'results.json'),JSON.stringify({status:'PASS',checks,non_get_requests:requests.filter(r=>r.method!=='GET').length,real_model_requests:0}));return;
 const staleCommand=$('commands').querySelector('button');
 mode='lost';await assert.rejects(open(info.first));const writesBefore=requests.filter(r=>r.method!=='GET').length;staleCommand.click();await new Promise(r=>setTimeout(r,20));
 check(requests.filter(r=>r.method!=='GET').length===writesBefore,'detached old task command cannot mutate after failed new read');
 const obsoleteRetry=$('run-read-failure').querySelector('button');await open(info.second);const readsBefore=requests.length;obsoleteRetry.click();await new Promise(r=>setTimeout(r,20));
 check(requests.length===readsBefore&&$('raw-result').textContent.includes(info.second),'obsolete retry cannot replace a newer task');
 mode='hold-fail';const projectLate=open(info.first);await wait(()=>!!release,'held project failure');
 $('project-select').value=info.other;$('project-select').dispatchEvent(new w.Event('change'));
 await wait(()=>$('run-history-status').textContent.includes('暂无任务'),'other project');release();await projectLate;
 check(empty()&&$('result').textContent===''&&!$('run-read-failure'),'late read failure cannot leak feedback across project change');
 $('project-select').value=info.project;$('project-select').dispatchEvent(new w.Event('change'));await wait(()=>$('runs').textContent.includes('Read recovery'),'project return');
 mode='hold';const identityLate=open(info.first);await wait(()=>!!release,'held identity success');
 $('token').value='synthetic-test-B';$('connect').click();await wait(()=>$('runs').textContent.includes('Foreign task'),'identity B');
 $('token').value='synthetic-test-A';$('connect').click();await wait(()=>$('runs').textContent.includes('Read recovery'),'identity A return');release();await identityLate;
 check(empty()&&$('result').textContent===''&&evaluate('activeRun===null'),'A to B to A does not resurrect a delayed task receipt');
 await open(info.first);mode='lost';await w.showRun(info.first,false);
 check(empty()&&$('run-read-failure')&&evaluate('activeRun===null'),'background read failure is handled without mistaking healthy API for task failure');
 check(requests.every(r=>r.method==='GET'),'all user read/recovery and failure paths use GET only');
 const result={status:'PASS',checks,requests,non_get_requests:requests.filter(r=>r.method!=='GET').length,real_model_requests:0,browser:'NOT_RUN',pixels:'NOT_RUN',synthetic_state_projection:'WAITING_RESOURCE only; real unresolved rejection uses B identity'};
 fs.writeFileSync(path.join(root,'results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}catch(error){console.error(error.stack);process.exitCode=1;}finally{dom?.window.close();}})();
