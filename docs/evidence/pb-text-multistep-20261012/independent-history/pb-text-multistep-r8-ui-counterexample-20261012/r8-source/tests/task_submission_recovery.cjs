'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const [root,engine]=process.argv.slice(2), info=JSON.parse(fs.readFileSync(path.join(root,'info.json')));
const checks=[];let dom,browser,page,evaluate;
const removedSecurityDefaults=['--enable-unsafe-swiftshader','--unsafely-disable-devtools-self-xss-warnings','--disable-ipc-flooding-protection','--disable-client-side-phishing-detection','--password-store=basic','--use-mock-keychain','--disable-features='+['AvoidUnnecessaryBeforeUnloadCheckSync','DestroyProfileOnBrowserClose','DialMediaRouteProvider','GlobalMediaControls','HttpsUpgrades','LensOverlay','MediaRouter','PaintHolding','ThirdPartyStoragePartitioning','BlockOriginHeaderModificationOnRedirect','Translate','AutoDeElevate','OptimizationHints','msForceBrowserSignIn','msEdgeUpdateLaunchServicesPreferredVersion'].join(',')];
const check=(ok,name)=>{assert(ok,name);checks.push(name);};
const wait=async(fn,name)=>{const end=Date.now()+10000;while(Date.now()<end){if(await fn())return;await new Promise(r=>setTimeout(r,20));}throw Error('Timeout '+name);};
const js=value=>JSON.stringify(value);
async function setup(){
 if(engine==='dom'){
  const {JSDOM}=require('jsdom');dom=new JSDOM(await(await fetch(info.base)).text(),{url:info.base,runScripts:'dangerously',pretendToBeVisual:true});
  dom.window.fetch=(url,opts)=>fetch(new URL(url,info.base),opts);dom.window.Response=Response;dom.window.crypto.randomUUID=require('node:crypto').randomUUID;dom.window.setInterval=()=>0;
  for(const file of ['app.js','internal.js','protocol.js']){const el=dom.window.document.createElement('script');el.textContent=await(await fetch(info.base+'/'+file)).text();dom.window.document.body.append(el);}
  evaluate=async code=>await dom.window.eval(code);
 }else{
  const {chromium}=require('playwright-core');
  try{browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,chromiumSandbox:true,ignoreDefaultArgs:removedSecurityDefaults});}
  catch(error){const sandboxBlocked=error.message.includes('The SUID sandbox helper binary was found, but is not configured correctly');fs.writeFileSync(path.join(root,'browser-startup.json'),JSON.stringify({status:sandboxBlocked?'BLOCKED':'FAIL',error:error.message,security_lowered:false},null,2));if(!sandboxBlocked)throw error;console.error(error.message);process.exitCode=77;return false;}
  const cdp=await browser.newBrowserCDPSession();const commandLine=(await cdp.send('Browser.getBrowserCommandLine')).arguments;
  check(!commandLine.some(arg=>['--no-sandbox','--disable-setuid-sandbox','--disable-web-security','--ignore-certificate-errors','--single-process'].includes(arg)),'actual browser security switches intact');
  page=await browser.newPage({viewport:{width:1280,height:900},acceptDownloads:false,bypassCSP:false});
  await page.addInitScript(()=>{window.setInterval=()=>0;});await page.goto(info.base);evaluate=async code=>await page.evaluate(code);
 }
 await evaluate(`$('token').value='synthetic-test-A';$('connect').click()`);
 await wait(()=>evaluate(`$('login').hidden&&refs.includes(${js(info.resource)})`),'authenticated materials');
 await evaluate(String.raw`window.recoveryOriginalFetch=window.fetch;window.recoveryMode='normal';window.recoveryPosts=[];window.recoveryReads=0;window.recoveryAccepted=new Set();
 window.fetch=async(url,opts={})=>{
 const target=new URL(url,location.href);
 if(target.origin!==location.origin)throw Error('Outside origin');
 const post=opts.method==='POST'&&/\/api\/projects\/[^/]+\/runs$/.test(target.pathname);
 if(post){
   const payload=JSON.parse(opts.body);window.recoveryPosts.push({path:target.pathname,body:payload});
   if(window.recoveryMode==='forbidden')return window.recoveryOriginalFetch(url,{...opts,headers:{...opts.headers,Authorization:'Bearer invalid-test-identity'}});
   const response=await window.recoveryOriginalFetch(url,opts);
   if(response.ok)window.recoveryAccepted.add((await response.clone().json()).run_id);
   const mode=window.recoveryMode;if(mode!=='read-lost')window.recoveryMode='normal';
   if(mode==='lost')throw TypeError('Synthetic receipt lost after real durable acceptance');
   if(mode==='hold'||mode==='hold-lost'){await new Promise(resolve=>{window.recoveryRelease=resolve;});}
   if(mode==='hold-lost')throw TypeError('Late synthetic receipt loss');
   if(mode==='server-error')return new Response(JSON.stringify({error:{code:'SYNTHETIC_PROXY_FAILURE'}}),{status:502,headers:{'Content-Type':'application/json'}});
   return response;
 }
 if(/\/api\/runs\/[^/]+$/.test(target.pathname)){window.recoveryReads++;const response=await window.recoveryOriginalFetch(url,opts);if(window.recoveryMode==='read-lost'){window.recoveryMode='normal';throw TypeError('Synthetic read lost');}return response;}
 return window.recoveryOriginalFetch(url,opts);
 };`);
 return true;
}
const submit=async(goal,mode='normal')=>{await evaluate(`$('goal').value=${js(goal)};window.recoveryMode=${js(mode)};$('run-form').dispatchEvent(new Event('submit',{cancelable:true}));`);};
const state=()=>evaluate(`runSubmissionEntry()?.state`);
const switchProject=async(pid)=>{await evaluate(`$('project-select').value=${js(pid)};$('project-select').dispatchEvent(new Event('change'));`);await wait(()=>evaluate(`$('project-select').value===${js(pid)}&&!!document.querySelector('#runs')`),'project navigation');};
(async()=>{try{
 if(!await setup())return;
 await submit('Lost acceptance, preserve exact input','lost');
 await evaluate(`$('run-form').dispatchEvent(new Event('submit',{cancelable:true}))`);
 await wait(async()=>await state()==='unknown','lost acceptance');
 check(await evaluate(`window.recoveryPosts.length===1`),'double submit produces one real POST');
 check(await evaluate(`$('run-submit').disabled&&$('goal').readOnly&&!$('run-submit-recover').hidden`),'unknown acceptance freezes new task and exposes explicit recovery');
 const original=await evaluate(`window.recoveryPosts[0]`);
 await evaluate(`$('goal').value='changed by test';refs=[];window.recoveryMode='forbidden';$('run-submit-recover').click()`);
 await wait(async()=>await state()==='unknown','revoked identity recovery');
 check(await evaluate(`$('run-submit').disabled`),'recovery rejection cannot convert unknown accepted intent into a new one');
 await evaluate(`window.recoveryMode='normal';$('run-submit-recover').click()`);
 await wait(async()=>await state()==='accepted','same intent restored');
 check(await evaluate(`window.recoveryPosts.every(x=>JSON.stringify(x)===${js(JSON.stringify(original))})`),'manual recovery preserves original project/key/goal/materials');
 check(await evaluate(`window.recoveryAccepted.size===1`),'receipt recovery returns one existing durable Run');
 await wait(()=>evaluate(`activeRun===runSubmissionEntry().runId&&$('raw-result').textContent.includes(runSubmissionEntry().runId)`),'persistent result rendered');
 check(await evaluate(`activeRun===runSubmissionEntry().runId`),'accepted task opens persistent result');
 check(await evaluate(`$('raw-result').textContent.includes('QUEUED')`),'result readback shows actual queued status');
 // Create a real history entry for re-selection tests.
 await submit('History selection');await wait(async()=>await state()==='accepted','history task');
 const history=await evaluate(`runSubmissionEntry().runId`);
 await submit('Late accepted receipt','hold');await wait(()=>evaluate(`typeof window.recoveryRelease==='function'`),'hold accepted response');
 await evaluate(`showRun(${js(history)})`);await evaluate(`window.recoveryRelease();window.recoveryRelease=null`);
 await wait(async()=>await state()==='accepted','late accepted response');
 check(await evaluate(`activeRun===${js(history)}`),'late acceptance cannot steal explicitly selected history');
 await submit('Project bound unknown response','server-error');await wait(async()=>await state()==='unknown','ambiguous502');
 check(await evaluate(`$('run-submit').disabled`),'HTTP502 after acceptance stays unknown');
 await switchProject(info.other);
 check(await evaluate(`!$('run-submit').disabled&&$('run-submit-recover').hidden&&$('run-submit-status').textContent===''`),'other project does not inherit private recovery state');
 await switchProject(info.project);
 check(await evaluate(`$('run-submit').disabled&&$('goal').value==='Project bound unknown response'`),'returning project restores its frozen pending input');
 await evaluate(`window.recoveryMode='hold';$('run-submit-recover').click()`);await wait(()=>evaluate(`typeof window.recoveryRelease==='function'`),'held recovery');
 await switchProject(info.other);await evaluate(`window.recoveryRelease();window.recoveryRelease=null`);await wait(()=>evaluate(`ordinarySubmissions.get(token).get(${js(info.project)}).state==='accepted'`),'background accepted recovery');
 check(await evaluate(`activeRun===null&&$('run-submit-status').textContent===''`),'old-project response cannot overwrite current task canvas/status');
 await switchProject(info.project);
 check(await evaluate(`runSubmissionEntry().state==='accepted'&&!$('run-submit').disabled`),'accepted recovery can be reopened after project return');
 await submit('');await wait(async()=>await state()==='rejected','definite validation rejection');
 check(await evaluate(`!$('run-submit').disabled&&$('run-submit-recover').hidden`),'initial HTTP422 permits corrected fresh intent');
 const postsBeforeRead=await evaluate(`window.recoveryPosts.length`);
 await submit('Accepted task with lost read','read-lost');await wait(async()=>await state()==='accepted-read-error','lost result read');
 check(await evaluate(`!$('run-submit-read').hidden&&$('run-submit-recover').hidden`),'accepted read failure offers GET recovery, not POST');
 const readId=await evaluate(`runSubmissionEntry().runId`);
 await evaluate(`$('run-submit-read').click()`);await wait(()=>evaluate(`runSubmissionEntry().state==='accepted'&&$('raw-result').textContent.includes(${js(readId)})`),'persistent read restored');
 check(await evaluate(`window.recoveryPosts.length===${postsBeforeRead+1}`),'re-reading accepted task sends no new POST');
 check(await evaluate(`activeRun===${js(readId)}`),'read recovery returns same accepted task');
 await wait(()=>evaluate(`$('run-submit-status').textContent.includes('目标已验收')`),'read status complete');
 check(await evaluate(`$('run-submit-status').textContent.includes('目标已验收')`),'acceptance explicitly distinguished from semantic acceptance');
 check(await evaluate(`localStorage.length===0&&sessionStorage.length===0`),'no goals/keys/authentication persisted in browser storage');
 check(await evaluate(`document.querySelector('#run-submit-status').getAttribute('aria-live')==='polite'`),'status feedback accessible');
 await submit('Late failure stays in its original project','hold-lost');
 await wait(()=>evaluate(`typeof window.recoveryRelease==='function'`),'held late failure');
 await switchProject(info.other);await evaluate(`window.recoveryRelease();window.recoveryRelease=null`);
 await wait(()=>evaluate(`ordinarySubmissions.get(token).get(${js(info.project)}).state==='unknown'`),'original project retains late failure');
 check(await evaluate(`$('run-submit-status').textContent===''&&$('error').textContent===''`),'late failed receipt cannot overwrite other project feedback');
 await switchProject(info.project);await evaluate(`$('run-submit-recover').click()`);
 await wait(async()=>await state()==='accepted','late failure same-key recovery');
 check(await evaluate(`window.recoveryAccepted.size===6`),'six deliberate intents create exactly six durable Runs');
 const firstRun=await evaluate(`Array.from(window.recoveryAccepted)[0]`);
 fs.writeFileSync(path.join(root,'worker-once-request'),'run one Mock worker');
 await wait(async()=>{const response=await fetch(info.base+'/api/runs/'+firstRun,{headers:{Authorization:'Bearer synthetic-test-A'}});return (await response.json()).status==='PARTIAL';},'persistent Mock worker');
 await evaluate(`showRun(${js(firstRun)})`);
 check(await evaluate(`$('result').textContent.includes('部分完成')&&$('result').textContent.includes('MOCK 工程样例')`),'restored task reads real Mock partial result with honest mode');
 check(await evaluate(`$('raw-result').textContent.includes('VERIFIED')`),'persisted read receipt visible after worker completion');
 check(await evaluate(`$('run-progress').textContent.includes('任务已持久接受')&&$('run-progress').textContent.includes('后台已领取任务')&&$('run-progress').textContent.includes('工具效果已核验')`),'ordinary progress reads real persisted worker steps');
 check(await evaluate(`$('run-progress').textContent.includes('1 项已核验')&&$('run-progress').textContent.includes('NOT_RUN')`),'verified effect count remains separate from target acceptance');
 // Hold an actual persisted list; a subsequent deliberate intent supplies newer data.
 await evaluate(String.raw`window.historyOriginalFetch=window.fetch;window.historyHoldMode='none';window.fetch=async(url,opts)=>{
 const target=new URL(url,location.href);const response=await window.historyOriginalFetch(url,opts);
 if(target.pathname==='/api/projects/'+$('project-select').value+'/runs'&&opts.method==='GET'&&window.historyHoldMode!=='none'){
 const mode=window.historyHoldMode;window.historyHoldMode='none';await new Promise(resolve=>{window.historyRelease=resolve;});
 if(mode==='fail')throw TypeError('Late synthetic list loss');}
 return response;};window.historyHoldMode='hold';void refresh();`);
 await wait(()=>evaluate(`typeof window.historyRelease==='function'`),'held history response');
 await submit('Newest history <img src=x onerror=alert(1)>');await wait(async()=>await state()==='accepted','newest history intent');
 await wait(()=>evaluate(`$('runs').textContent.includes('Newest history')`),'newer persisted list');
 await evaluate(`window.historyRelease();window.historyRelease=null`);
 await new Promise(r=>setTimeout(r,80));
 check(await evaluate(`$('runs').textContent.includes('Newest history')`),'same-project older refresh cannot erase newer durable intent');
 check(await evaluate(`$('runs').textContent.includes('<img src=x onerror=alert(1)>')&&!$('runs').querySelector('img')`),'history summaries are text, never executable markup');
 check(await evaluate(`$('runs').textContent.includes('提交模式 MOCK')&&$('runs').textContent.includes('接受 ')`),'history shows persisted submission mode and accepted time');
 const acceptedRuns=await evaluate(`window.recoveryAccepted.size`);
 const acceptedPosts=await evaluate(`window.recoveryPosts.length`);
 await evaluate(`$('run-history-refresh').click()`);await wait(()=>evaluate(`$('run-history-status').textContent.includes('7 个')`),'manual list refresh');
 check(await evaluate(`window.recoveryPosts.length===${acceptedPosts}`),'history refresh sends no POST');
 // Late failed primary-project list must not leak into another project's feedback.
 await evaluate(`window.historyHoldMode='fail';void refresh()`);await wait(()=>evaluate(`typeof window.historyRelease==='function'`),'held failing list');
 await switchProject(info.other);await wait(()=>evaluate(`$('run-history-status').textContent.includes('暂无任务')`),'empty other project list');
 await evaluate(`window.historyRelease();window.historyRelease=null`);await new Promise(r=>setTimeout(r,80));
 check(await evaluate(`$('runs').textContent===''&&$('error').textContent===''`),'late history failure cannot change another project feedback');
 await switchProject(info.project);await wait(()=>evaluate(`$('runs').textContent.includes('Newest history')`),'return primary history');
 await evaluate(`window.historyHoldMode='hold';void refresh()`);await wait(()=>evaluate(`typeof window.historyRelease==='function'`),'held old identity list');
 await evaluate(`$('token').value='synthetic-test-B';$('connect').click()`);await wait(()=>evaluate(`$('project-select').selectedOptions[0]?.textContent==='Other identity project'&&$('run-history-status').textContent.includes('暂无任务')`),'new identity project');
 await evaluate(`window.historyRelease();window.historyRelease=null`);await new Promise(r=>setTimeout(r,80));
 check(await evaluate(`$('runs').textContent===''&&!$('runs').textContent.includes('Newest history')`),'late prior identity list cannot expose old summaries');
 // A real fresh document has no pending key/cache; existing server history is enough.
 if(engine==='dom'){
   dom.window.close();const {JSDOM}=require('jsdom');dom=new JSDOM(await(await fetch(info.base)).text(),{url:info.base,runScripts:'dangerously',pretendToBeVisual:true});
   dom.window.fetch=(url,opts)=>fetch(new URL(url,info.base),opts);dom.window.Response=Response;dom.window.crypto.randomUUID=require('node:crypto').randomUUID;dom.window.setInterval=()=>0;
   for(const file of ['app.js','internal.js','protocol.js']){const el=dom.window.document.createElement('script');el.textContent=await(await fetch(info.base+'/'+file)).text();dom.window.document.body.append(el);}
   evaluate=async code=>await dom.window.eval(code);
 }else{await page.reload();}
 await evaluate(`window.historyPostCount=0;window.historyFreshFetch=window.fetch;window.fetch=(url,opts)=>{if(opts?.method==='POST')window.historyPostCount++;return window.historyFreshFetch(url,opts);};$('token').value='synthetic-test-A';$('connect').click()`);
 await wait(()=>evaluate(`$('runs').textContent.includes('Newest history')`),'fresh document reconnect');
 check(await evaluate(`ordinarySubmissions.size===0`),'fresh document has no cached submission intent');
 check(await evaluate(`$('runs').textContent.includes('Lost acceptance, preserve exact input')&&$('runs').textContent.includes('提交模式 MOCK')`),'fresh page locates original accepted intent by persisted goal and mode');
 await evaluate(`Array.from($('runs').children).find(x=>x.textContent.includes('Lost acceptance, preserve exact input')).querySelector('button').click()`);
 await wait(()=>evaluate(`$('raw-result').textContent.includes(${js(firstRun)})`),'fresh document persistent result');
 check(await evaluate(`activeRun===${js(firstRun)}&&$('result').textContent.includes('部分完成')`),'fresh page opens original partial Run without pretending success');
 check(await evaluate(`window.historyPostCount===0`),'fresh document location and readback issue zero POST');
 await evaluate(`$('token').value='invalid-test-identity';$('connect').click()`);
 await wait(()=>evaluate(`$('error').textContent==='PERMISSION_DENIED'`),'failed identity connection');
 check(await evaluate(`activeRun===null&&refs.length===0&&$('result').textContent===''&&$('raw-result').textContent===''&&$('events').textContent===''&&$('commands').textContent===''&&$('runs').textContent===''`),'failed new identity connection clears all old task data');
 await evaluate(`$('token').value='synthetic-test-A';$('connect').click()`);await wait(()=>evaluate(`$('runs').textContent.includes('Newest history')`),'reconnect after failed identity');
 await evaluate(String.raw`window.historyDetailFetch=window.fetch;window.historyDetailHold=true;window.fetch=async(url,opts)=>{const response=await window.historyDetailFetch(url,opts);if(new URL(url,location.href).pathname===`+js('/api/runs/'+firstRun)+String.raw`&&window.historyDetailHold){window.historyDetailHold=false;await new Promise(resolve=>{window.historyDetailRelease=resolve;});}return response;};void showRun(`+js(firstRun)+`);`);
 await wait(()=>evaluate(`typeof window.historyDetailRelease==='function'`),'held old task detail');
 await evaluate(`$('token').value='synthetic-test-B';$('connect').click()`);await wait(()=>evaluate(`$('project-select').selectedOptions[0]?.textContent==='Other identity project'`),'ABA identity B');
 await evaluate(`$('token').value='synthetic-test-A';$('connect').click()`);await wait(()=>evaluate(`$('runs').textContent.includes('Newest history')`),'ABA identity A again');
 await evaluate(`window.historyDetailRelease();window.historyDetailRelease=null`);await new Promise(r=>setTimeout(r,80));
 check(await evaluate(`activeRun===null&&$('raw-result').textContent===''&&$('result').textContent===''`),'A to B to A cannot resurrect prior task selection from late detail');
 await evaluate(String.raw`window.historyConnectionFetch=window.fetch;window.historyHoldConnection=true;window.fetch=async(url,opts)=>{const response=await window.historyConnectionFetch(url,opts);if(new URL(url,location.href).pathname==='/api/projects'&&window.historyHoldConnection){window.historyHoldConnection=false;await new Promise(resolve=>{window.historyConnectionRelease=resolve;});}return response;};$('token').value='invalid-test-identity';$('connect').click();`);
 await wait(()=>evaluate(`typeof window.historyConnectionRelease==='function'`),'held denied connection');
 await evaluate(`$('token').value='synthetic-test-B';$('connect').click()`);await wait(()=>evaluate(`$('project-select').selectedOptions[0]?.textContent==='Other identity project'&&$('error').textContent===''`),'new connection success');
 await evaluate(`window.historyConnectionRelease();window.historyConnectionRelease=null`);await new Promise(r=>setTimeout(r,80));
 check(await evaluate(`$('error').textContent===''&&$('project-select').selectedOptions[0]?.textContent==='Other identity project'`),'late rejected connection cannot overwrite newer identity feedback');
 await evaluate(`$('token').value='synthetic-test-A';$('connect').click()`);await wait(()=>evaluate(`$('runs').textContent.includes('Newest history')`),'restore original identity after obsolete rejection');
 await evaluate(String.raw`window.historyFailureFetch=window.fetch;window.historyFailOnce=true;window.fetch=async(url,opts)=>{const response=await window.historyFailureFetch(url,opts);if(new URL(url,location.href).pathname.startsWith('/api/projects/')&&new URL(url,location.href).pathname.endsWith('/runs')&&opts.method==='GET'&&window.historyFailOnce){window.historyFailOnce=false;throw TypeError('Synthetic current list failure');}return response;};$('run-history-refresh').click();`);
 await wait(()=>evaluate(`$('run-history-status').textContent.includes('历史读取失败')`),'current list failure');
 check(await evaluate(`$('runs').textContent===''`),'current list failure clears stale history');
 await evaluate(`$('run-history-refresh').click()`);await wait(()=>evaluate(`$('runs').textContent.includes('Newest history')`),'manual history reread after failure');
 check(await evaluate(`window.historyPostCount===0`),'identity changes and history recovery still issue zero POST');
 if(engine==='chromium'){
  await page.screenshot({path:path.join(root,'desktop.png'),fullPage:true});await page.setViewportSize({width:390,height:844});
  check(await evaluate(`document.documentElement.scrollWidth===innerWidth`),'narrow layout has no horizontal overflow');
  await page.screenshot({path:path.join(root,'narrow.png'),fullPage:true});
 }
 const result={status:'PASS',engine,checks,accepted_runs:acceptedRuns,real_model_requests:0,mock_attempts:2};fs.writeFileSync(path.join(root,'results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }catch(error){console.error(error.stack);process.exitCode=1;}finally{dom?.window.close();await browser?.close();}})();
