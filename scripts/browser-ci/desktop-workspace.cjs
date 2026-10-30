'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{spawn,execFileSync}=require('node:child_process'),{chromium}=require('playwright-core');
const root=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(root,'info.json'))),checks=[],servers=[],outside=[];
const result={commit:info.commit,platform:'Windows Server 2025 / installed protected Edge',windows11:'NOT_RUN',webview2_exe:'NOT_RUN',fixture_mock_definition_calls:3,runtime_model_calls:0,checks};
let context,page,owned,accepted,originalKey,specPosts=0,cleanupPromise=null;
const workDeadline=Date.now()+155000;
const removedSecurityDefaults=[
 '--enable-unsafe-swiftshader','--unsafely-disable-devtools-self-xss-warnings','--disable-ipc-flooding-protection','--disable-client-side-phishing-detection','--password-store=basic','--use-mock-keychain',
 '--disable-features='+['AvoidUnnecessaryBeforeUnloadCheckSync','DestroyProfileOnBrowserClose','DialMediaRouteProvider','GlobalMediaControls','HttpsUpgrades','LensOverlay','MediaRouter','PaintHolding','ThirdPartyStoragePartitioning','BlockOriginHeaderModificationOnRedirect','Translate','AutoDeElevate','OptimizationHints','msForceBrowserSignIn','msEdgeUpdateLaunchServicesPreferredVersion'].join(',')];
const check=(yes,label)=>{assert(yes,label);checks.push(label);};
async function until(predicate,label,ms=25000,cleanup=false){
 const end=cleanup?Date.now()+ms:Math.min(Date.now()+ms,workDeadline);
 while(Date.now()<end){
  const ready=await predicate(end);
  if(Date.now()>=end)throw Error('Timeout '+label);
  if(ready)return;
  await new Promise(r=>setTimeout(r,Math.min(100,end-Date.now())));
 }
 throw Error('Timeout '+label);
}
async function start(){
 if(Date.now()>=workDeadline)throw Error('Work deadline before backend startup');
 const child=spawn(info.python,['-B','-m','sim2act.cli','synthetic-workspace','--data-dir',info.data_dir,'--control-stdin'],{windowsHide:true,stdio:['pipe','pipe','pipe']});
 const state={child,events:[],errors:'',ready:null,exit:null,lines:'',closed:false,stdoutEnded:false,stderrEnded:false,cleaned:false,spawnError:null};servers.push(state);
 child.stdout.setEncoding('utf8');child.stdout.on('data',chunk=>{state.lines+=chunk;assert(state.lines.length<131072);let end;while((end=state.lines.indexOf('\n'))>=0){const line=state.lines.slice(0,end);state.lines=state.lines.slice(end+1);if(line.startsWith('{')){const e=JSON.parse(line);state.events.push(e);if(e.event==='SYNTHETIC_WORKSPACE_READY')state.ready=e;}}});
 child.stdout.on('end',()=>state.stdoutEnded=true);child.stderr.on('end',()=>state.stderrEnded=true);child.stdin.on('error',error=>state.pipeError=error.code);
 child.stderr.setEncoding('utf8');child.stderr.on('data',s=>state.errors=(state.errors+s).slice(-65536));child.on('exit',code=>state.exit=code);child.on('close',()=>state.closed=true);child.on('error',error=>state.spawnError=error.code||error.message);
 await until(()=>{if(state.spawnError||state.exit!==null)throw Error('Owned backend stopped '+(state.spawnError||state.exit)+' '+state.errors);return state.ready;},'owned READY');return state;
}
async function stop(state){
 if(state.cleaned)return;
 if(state.exit===null&&!state.child.stdin.destroyed)state.child.stdin.end();
 await until(()=>state.closed&&(state.spawnError||(state.stdoutEnded&&state.stderrEnded)),'owned exit and both pipe EOFs',25000,true);state.cleaned=true;
 const receipt=state.events.find(e=>e.event==='SYNTHETIC_WORKSPACE_STOPPED');check(!state.spawnError&&state.exit===0&&receipt?.clean&&receipt.worker_stopped&&receipt.data_preserved,'owned backend STOPPED clean after both EOFs with preserved data');
}
async function cleanupAll(){
 if(cleanupPromise)await cleanupPromise;
 cleanupPromise=(async()=>{
  const active=context;context=null;
  for(const state of servers)if(!state.cleaned&&state.exit===null&&!state.child.stdin.destroyed)state.child.stdin.end();
  const failures=error=>{result.status='FAIL';result.cleanup_error=error.stack;process.exitCode=1;};
  const work=Promise.all([...(active?[closeContext(active).catch(failures)]:[]),...servers.map(state=>stop(state).catch(failures))]);
  let timer;try{await Promise.race([work,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Cleanup UNKNOWN after 25 seconds')),25000);})]);}catch(error){failures(error);result.cleanup_unknown=true;}finally{clearTimeout(timer);}
 })();
 try{await cleanupPromise;}finally{cleanupPromise=null;}
}
async function closeContext(active){let timer;try{await Promise.race([active.close(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Browser close UNKNOWN after 20 seconds')),20000);})]);}finally{clearTimeout(timer);}}
const workTimer=setTimeout(()=>{result.status='FAIL';result.deadline_exceeded=true;process.exitCode=1;void cleanupAll();},155000);
async function open(round){
 if(Date.now()>=workDeadline)throw Error('Work deadline before browser startup');
 context=await chromium.launchPersistentContext(path.join(root,'edge-profile'),{channel:'msedge',headless:true,chromiumSandbox:true,ignoreDefaultArgs:removedSecurityDefaults,acceptDownloads:true,bypassCSP:false,viewport:{width:1440,height:900},timeout:20000});
 if(Date.now()>=workDeadline)throw Error('Work deadline after browser startup');
 const base=owned.ready.url;
 await context.route('**/*',async route=>{const request=route.request();if(!request.url().startsWith(base+'/')){outside.push(request.url().split('?')[0]);return route.abort();}
  if(request.method()==='POST'&&new URL(request.url()).pathname===`/api/internal/instances/${info.spec_instance}/runs`){specPosts++;originalKey=request.postDataJSON().request_key;
   if(round===0){const response=await route.fetch({timeout:Math.max(1,Math.min(15000,workDeadline-Date.now())),maxRetries:0});check(response.status()===202,'real spec POST accepted before intentional response loss');accepted=await response.json();return route.abort('failed');}
  }return route.continue();});
 page=context.pages()[0]||await context.newPage();page.setDefaultTimeout(18000);page.on('pageerror',e=>{result.pageErrors??=[];result.pageErrors.push(e.message);});
 await page.goto(base);await page.locator('#token').fill(owned.ready.public_token);await page.locator('#connect').click();await page.locator('#login').waitFor({state:'hidden'});await page.locator('[data-tab="apps"]').click();
 const browser=context.browser();assert(browser);const cdp=await browser.newBrowserCDPSession();const processes=(await cdp.send('SystemInfo.getProcessInfo')).processInfo.filter(p=>['browser','renderer'].includes(p.type));
 const auditFile=path.join(root,'browser-pids.json');fs.writeFileSync(auditFile,JSON.stringify(processes));const audited=JSON.parse(execFileSync(info.python,['scripts/windows_browser_ci.py','--root',root,'--audit',auditFile],{encoding:'utf8',timeout:10000}));
 check(audited.length>0&&audited.every(p=>p.security_args_verified),'actual browser processes preserve sandbox arguments');const renderers=audited.filter(p=>p.type==='renderer');check(renderers.length>0&&renderers.every(p=>p.app_container||(p.restricted_token&&p.integrity_rid<=4096)),'actual Windows renderer tokens remain restricted');
 result.sandbox??=[];result.sandbox.push(audited);
}
async function app(name){await page.locator('#app-list .row').filter({hasText:name}).locator('button').click();await page.waitForFunction(()=>engineering?.historyReady&&!engineering.busy);}
async function instance(id){await page.locator('#internal-instances .row').filter({hasText:id}).locator('button').click();await page.waitForFunction(id=>engineering?.instance?.id===id&&!engineering.busy,id);}
async function readJSON(url,deadline=Date.now()+15000,kind='result'){
 // The HTTP response and its body share the observer's absolute deadline.
 const remaining=Math.min(deadline,workDeadline)-Date.now();if(remaining<=0)throw Error('Work deadline reached before read');
 const started=Date.now(),observation={kind,limit_ms:remaining};
 try{const response=await fetch(url,{headers:{Authorization:'Bearer '+owned.ready.public_token},signal:AbortSignal.timeout(remaining)});observation.http_status=response.status;assert.equal(response.status,200);return await response.json();}
 catch(error){observation.error=error.name;throw error;}
 finally{observation.elapsed_ms=Date.now()-started;(result.read_observations??=[]).push(observation);}
}
async function status(deadline){return (await readJSON(owned.ready.url+`/api/internal/instances/${info.spec_instance}/spec-run-requests/${originalKey}`,deadline,'spec-original-key')).status;}
async function layout(width,height){
 await page.setViewportSize({width,height});const measured=await page.evaluate(()=>({viewport:[innerWidth,innerHeight],width:document.documentElement.scrollWidth,font:parseFloat(getComputedStyle(document.body).fontSize),buttons:['internal-back','internal-refresh','internal-run-submit'].map(id=>{const r=document.getElementById(id).getBoundingClientRect();return {id,x:r.x,y:r.y,right:r.right,bottom:r.bottom,height:r.height};}),panes:['app-preview-pane','internal-version-pane','internal-operation-pane','internal-result-scroll'].map(id=>{const e=document.getElementById(id),before=[scrollX,scrollY,document.querySelector('main').scrollTop],old=e.scrollTop;e.scrollTop=0;e.scrollTop=e.scrollHeight;const moved=e.scrollTop,after=[scrollX,scrollY,document.querySelector('main').scrollTop];e.scrollTop=old;return {id,height:e.clientHeight,scroll_height:e.scrollHeight,actual_scroll_top:moved,overflow:getComputedStyle(e).overflowY,independent:JSON.stringify(before)===JSON.stringify(after)};})}));
 check(measured.width<=width+1&&measured.font>=14,'actual workspace fits width without shrinking body text '+width);
 check(measured.buttons.every(b=>b.height>=30&&b.x>=0&&b.y>=0&&b.right<=width+1&&b.bottom<=height+1),'common toolbar and Run button in initial viewport '+width);
 check(measured.panes.every(p=>p.height>0&&p.overflow==='auto'&&p.independent&&(p.scroll_height<=p.height+1||p.actual_scroll_top>0)),'actual overflowing work regions move independently '+width);
 result.layouts??=[];result.layouts.push(measured);await page.screenshot({path:path.join(root,`workspace-${width}x${height}.png`),fullPage:false});
}
(async()=>{try{
 owned=await start();await open(0);await app('Model chosen checklist');await instance(info.spec_instance);await page.locator('#internal-run-submit').click();await page.waitForFunction(()=>!engineering.busy&&engineeringPending.has(engineering.instance.id));check(specPosts===1&&!!accepted,'lost receipt remains one persistent original intent');await until(async deadline=>await status(deadline)==='SUCCEEDED','normal deterministic spec Worker',30000);
 const firstOrigin=owned.ready.url;await closeContext(context);context=null;await stop(owned);owned=null;
 owned=await start();check(owned.ready.url===firstOrigin,'fresh backend rebinds exact same origin');await open(1);await app('Model chosen checklist');await instance(info.spec_instance);check(await page.locator('#internal-run-submit').isDisabled(),'fresh actual browser profile restores old pending key');await page.locator('#internal-retry').click();await page.waitForFunction(id=>!engineering.busy&&engineering.run?.id===id,accepted.run_id);check(specPosts===1,'real browser restart recovers using GET without another POST');
 await app('Synthetic CSV desktop');await page.locator('#app-column').selectOption('amount');await page.locator('#internal-prepare').click();await page.waitForFunction(()=>!!engineering.approval&&!engineering.busy);await page.locator('#internal-approval-ack').check();await page.locator('#internal-commit').click();await page.waitForFunction(()=>!engineering.busy&&document.querySelector('#internal-releases button'));await page.locator('#internal-releases button').first().click();await page.waitForFunction(()=>engineering.instance&&!engineering.busy);
 const csvInstance=await page.evaluate(()=>engineering.instance.id),csvRuns=[];
 for(const [column,total,version]of [['amount','30',1],['tax','15',2]]){await page.locator('#internal-column').selectOption(column);await page.locator('#internal-run-submit').click();await page.waitForFunction(()=>!engineering.busy&&engineering.run?.id);const id=await page.evaluate(()=>engineering.run.id);await until(async deadline=>{const v=await readJSON(owned.ready.url+`/api/internal/instances/${csvInstance}/runs/${id}`,deadline);return v.status==='SUCCEEDED'&&v.result?.sum===total&&v.result_version===version;},'actual CSV worker result');await page.locator('#internal-refresh').click();await page.waitForFunction(()=>!engineering.busy);csvRuns.push(id);}
 await layout(1366,768);await layout(1440,900);
 await page.reload();await page.locator('#token').fill(owned.ready.public_token);await page.locator('#connect').click();await page.locator('#login').waitFor({state:'hidden'});await page.locator('[data-tab="apps"]').click();await page.locator(`#use-list [data-use-family="CSV"][data-instance-id="${csvInstance}"] button`).click();await page.locator('#use-history .row').filter({hasText:csvRuns[1].slice(0,18)}).locator('button').click();
 const download=page.waitForEvent('download');await page.locator('#use-output [data-download-format="json"]').click();const file=await download;await file.saveAs(path.join(root,'synthetic-result.json'));const value=JSON.parse(fs.readFileSync(path.join(root,'synthetic-result.json'),'utf8'));check(value.instance_id===csvInstance&&value.run_id===csvRuns[1]&&value.result_version===2&&value.result.sum==='15','native Edge download saves exact selected persistent CSV result');
 result.accepted_spec={run_id:accepted.run_id,app_run_id:accepted.app_run_id,posts:specPosts};result.csv={instance:csvInstance,runs:csvRuns,download_sha256:require('node:crypto').createHash('sha256').update(fs.readFileSync(path.join(root,'synthetic-result.json'))).digest('hex')};check(!(result.pageErrors?.length),'no page script errors');check(outside.length===0,'application made no external request');result.status='PASS';
}catch(error){result.status='FAIL';result.error=error.stack;process.exitCode=1;try{if(page)await page.screenshot({path:path.join(root,'failure.png'),fullPage:false});}catch{}}
finally{clearTimeout(workTimer);await cleanupAll();if(result.deadline_exceeded)result.status='FAIL';result.backend_receipts=servers.map(s=>({origin:s.ready?.url,worker:s.ready?.worker_id,exit:s.exit,closed:s.closed,stdout_eof:s.stdoutEnded,stderr_eof:s.stderrEnded,spawn_error:s.spawnError,stopped:s.events.find(e=>e.event==='SYNTHETIC_WORKSPACE_STOPPED')}));fs.writeFileSync(path.join(root,'desktop-results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify({status:result.status,checks:checks.length,error:result.error}));}})();
