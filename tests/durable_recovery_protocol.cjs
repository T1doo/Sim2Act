"use strict";
// Fast protocol fault tests with actual page source, synthetic HTTP only.
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict"),crypto=require("node:crypto"),{JSDOM}=require("jsdom");
const browser=require("./durable_browser.cjs")(undefined,{storageEvents:false}),web=path.join(__dirname,"../src/sim2act/web"),checks=[],windows=[];
const id=(prefix,n)=>prefix+"_"+String(n).repeat(32),principal=id("user",1),project=id("proj",2),app=id("app",3),instance=id("iinstance",4),release=id("irelease",5),fp="a".repeat(64);
let posts=0,gets=0,holdPost=null,postEntered=false;const acceptedRequests=new Map();
function page(options={}){
 const dom=new JSDOM(fs.readFileSync(path.join(web,"index.html"),"utf8"),{url:"http://protocol.test",runScripts:"dangerously"}),w=dom.window;windows.push(w);browser.install(w);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w.crypto,"subtle",{value:crypto.webcrypto.subtle});w.crypto.randomUUID=()=>crypto.randomUUID();w.setInterval=()=>0;
 w.fetch=async(url,config)=>{
  if(config.method==="POST"){
   posts++;postEntered=true;acceptedRequests.set(JSON.parse(config.body).request_key,JSON.parse(config.body));
   const entries=browser.values(w.location.origin);assert(entries.length);const stored=JSON.parse(entries.at(-1)[1]);
   assert(!JSON.stringify(entries).includes("synthetic-test-A"));assert(!Object.hasOwn(stored,"input"));
   if(options.hold)await new Promise(resolve=>holdPost=resolve);
   return new Response(JSON.stringify({run_id:id("run",6),app_run_id:id("iapprun",7)}),{status:202});
  }
  gets++;
  if(options.success&&url.includes("/spec-run-requests/")){
   const key=url.split("/").at(-1),request=acceptedRequests.get(key),iid=options.instance||instance;
   const expected={instance_id:iid,expected_revision:request.expected_revision,expected_release_fp:request.expected_release_fingerprint,input:request.input};
   const canon=x=>Array.isArray(x)?x.map(canon):x&&typeof x==="object"?Object.fromEntries(Object.keys(x).sort().map(k=>[k,canon(x[k])])):x;
   const hash=crypto.createHash("sha256").update(JSON.stringify(canon(expected))).digest("hex");
   return new Response(JSON.stringify({namespace:"spec-run-request.v1",principal_id:principal,project_id:project,app_id:app,instance_id:iid,release_id:release,request_key:key,request_fingerprint:hash,request,run_id:id("run",6),app_run_id:id("iapprun",7),new_model_requests:0,project_writes:0}),{status:200});
  }
  return new Response(JSON.stringify({error:{code:"OUTCOME_UNKNOWN"}}),{status:409});
 };
 for(const script of [...w.document.querySelectorAll("script[src]")]){const node=w.document.createElement("script");node.textContent=fs.readFileSync(path.join(web,script.getAttribute("src").slice(1)),"utf8");w.document.body.append(node);}
 w.fixture={principal,project,app,instance,release,fp,...options};
 w.eval(`token="synthetic-test-A";activeApp=fixture.app;document.getElementById("project-select").replaceChildren(new Option("Own",fixture.project));engineering={token,project:fixture.project,app:fixture.app,appGeneration:appSelectionGeneration,instanceGeneration:0,spec:true,draft:{},instance:{id:fixture.instance,principal_id:fixture.principal,release_id:fixture.release,revision:1,release_fingerprint:fixture.fp}};`);
 return w;
}
const check=(yes,label)=>{assert(yes,label);checks.push(label);};
const attempt=(w,retry=false)=>w.eval(`submitPersistentSpecRun(engineering,engineering.instance,${retry})`);
async function rejects(work,label){await assert.rejects(work);checks.push(label);}
(async()=>{try{
 const first=page({hold:true}),second=page();
 const a=attempt(first);a.catch(()=>{});while(!postEntered)await new Promise(resolve=>setTimeout(resolve,1));
 const b=attempt(second);b.catch(()=>{});await new Promise(resolve=>setTimeout(resolve,5));
 check(posts===1&&gets===0,"same-origin second document cannot POST while first POST holds scope lock");
 holdPost();const unknownOutcomes=await Promise.allSettled([a,b]);check(unknownOutcomes[1].reason?.message==="RECOVERY_REQUEST_BUSY","busy second document is rejected without queueing");await rejects(attempt(second,true),"busy document later explicitly reads original unknown key");
 check(posts===1&&gets===2&&browser.values(first.location.origin).length===1,"both unknown receipts retain single original intent without duplicate POST");
 const raw=JSON.stringify(browser.values(first.location.origin));
 const fresh=page();await rejects(attempt(fresh),"fresh DOM UNKNOWN fails visibly");
 check(posts===1&&JSON.stringify(browser.values(first.location.origin))===raw,"new DOM manually submitted intent only GETs old key; UNKNOWN unchanged");
 const foreign=page({principal:id("user",8)});
 check(foreign.eval("specRecoveryRestore(engineering,engineering.instance)")===null,"different principal cannot restore this record");
 const foreignProject=page({project:id("proj",8)});
 check(foreignProject.eval("specRecoveryRestore(engineering,engineering.instance)")===null,"different project cannot restore this record");
 const foreignInstance=page({instance:id("iinstance",8)});
 check(foreignInstance.eval("specRecoveryRestore(engineering,engineering.instance)")===null,"different instance cannot restore this record");
 const noLock=page();Object.defineProperty(noLock.navigator,"locks",{value:undefined});
 const before=posts;await rejects(attempt(noLock),"missing Web Locks fails closed");check(posts===before,"missing lock cannot POST");
 const broken=page();broken.localStorage.getItem=()=>{throw Error("storage denied");};
 await rejects(attempt(broken),"storage access denial fails closed");check(posts===before,"unreadable storage cannot POST");
 const quota=page({instance:id("iinstance",9)});quota.localStorage.setItem=()=>{throw Error("quota");};
 await rejects(attempt(quota),"durable write failure aborts before POST");check(posts===before,"failed durable write cannot POST");
 const corrupt=page();const key=corrupt.eval("specRecoveryKey(engineering,engineering.instance)");corrupt.localStorage.setItem(key,'{"namespace":"wrong","body":"untrusted"}');
 await rejects(attempt(corrupt),"malformed or extra-field record fails closed");check(posts===before,"corrupt original scope is never silently replaced");
 corrupt.localStorage.setItem(key,JSON.parse(raw)[0][1]);
 const changed=page();changed.eval("specRecoveryRestore(engineering,engineering.instance)");
 const replacement=JSON.parse(JSON.parse(raw)[0][1]);replacement.request_key=crypto.randomUUID();changed.localStorage.setItem(key,JSON.stringify(replacement));
 assert.throws(()=>changed.eval("specRecoveryForget(engineering,engineering.instance,engineeringPending.get(engineering.instance.id))"));
 check(changed.localStorage.getItem(key)===JSON.stringify(replacement),"stale receipt cannot erase a different durable intent");
 changed.localStorage.setItem(key,JSON.parse(raw)[0][1]);
 postEntered=false;const late=page({instance:id("iinstance",0),hold:true});const action=attempt(late);action.catch(()=>{});while(!postEntered)await new Promise(resolve=>setTimeout(resolve,1));
 const prior=JSON.stringify(browser.values(late.location.origin)),oldGets=gets;
 late.document.getElementById("identity-switch").click();holdPost();await action;
 check(gets===oldGets&&JSON.stringify(browser.values(late.location.origin))===prior,"late POST acceptance after identity switch cannot GET or clear durable record");
 // Waiting for a lock is also a selection/identity boundary.
 postEntered=false;const held=page({instance:id("iinstance",1),hold:true}),waiting=page({instance:id("iinstance",1)});
 const heldWork=attempt(held);heldWork.catch(()=>{});while(!postEntered)await new Promise(resolve=>setTimeout(resolve,1));
 const waited=attempt(waiting);waited.catch(()=>{});waiting.document.getElementById("identity-switch").click();const oldPosts=posts;holdPost();await Promise.allSettled([heldWork,waited]);
 check(posts===oldPosts,"identity switch before busy acquisition callback cannot send a request");
 postEntered=false;const raceA=page({instance:id("iinstance",7),success:true,hold:true}),raceB=page({instance:id("iinstance",7),success:true});
 const raceBefore=posts,one=attempt(raceA);one.catch(()=>{});while(!postEntered)await new Promise(resolve=>setTimeout(resolve,1));const two=attempt(raceB);two.catch(()=>{});await new Promise(resolve=>setTimeout(resolve,5));holdPost();const outcomes=await Promise.allSettled([one,two]);check(outcomes[0].status==="fulfilled"&&outcomes[1].reason?.message==="RECOVERY_REQUEST_BUSY","successful receipt race rejects busy action without relying on storage events");
 check(posts-raceBefore===1,"successful first receipt must not turn concurrent action into second POST; observed="+(posts-raceBefore));
 check(!browser.values(raceA.location.origin).some(([key])=>key.includes(id("iinstance",7))),"successful exact receipt really removed first record in contention test");
 const proof={status:"PASS",checks,post_count:posts,get_count:gets,platform:"JSDOM_SHARED_STORAGE_WEB_LOCKS_ADAPTER",http:"SYNTHETIC_PROTOCOL_ONLY",native_browser:"NOT_RUN"};
 if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(proof,null,2));process.stdout.write(JSON.stringify(proof)+"\n");
 }catch(error){if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify({status:"FAIL",checks,error:error.stack},null,2));process.stderr.write(error.stack+"\n");process.exitCode=1;}finally{windows.forEach(w=>w.close());}})();
