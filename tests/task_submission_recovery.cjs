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
 await evaluate(`$('run-submit-read').click()`);await wait(async()=>await state()==='accepted','read restored');
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
 if(engine==='chromium'){
  await page.screenshot({path:path.join(root,'desktop.png'),fullPage:true});await page.setViewportSize({width:390,height:844});
  check(await evaluate(`document.documentElement.scrollWidth===innerWidth`),'narrow layout has no horizontal overflow');
  await page.screenshot({path:path.join(root,'narrow.png'),fullPage:true});
 }
 const result={status:'PASS',engine,checks,accepted_runs:await evaluate(`window.recoveryAccepted.size`),real_model_requests:0,mock_attempts:2};fs.writeFileSync(path.join(root,'results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }catch(error){console.error(error.stack);process.exitCode=1;}finally{dom?.window.close();await browser?.close();}})();
