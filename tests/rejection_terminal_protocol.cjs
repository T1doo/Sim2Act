"use strict";
// Actual page scripts; synthetic HTTP and shared Storage/Web Locks adapter only.
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict"),crypto=require("node:crypto"),{JSDOM}=require("jsdom");
const browser=require("./durable_browser.cjs")(undefined,{storageEvents:false}),web=path.join(__dirname,"../src/sim2act/web"),windows=[],checks=[];
const id=(p,n)=>p+"_"+String(n).repeat(32),principal=id("user",1),project=id("proj",2),app=id("app",3),release=id("irelease",5),fp="a".repeat(64);
const canon=x=>Array.isArray(x)?x.map(canon):x&&typeof x==="object"?Object.fromEntries(Object.keys(x).sort().map(k=>[k,canon(x[k])])):x;
const hash=x=>crypto.createHash("sha256").update(JSON.stringify(canon(x))).digest("hex");
let posts=0,closes=0,gets=0,entered=false,unblock,phase="TX_ROLLED_BACK",failClose=false,badReceipt=false,holdGet=false,getEntered=false,unblockGet,loseClose=false,holdClose=false,closeEntered=false,unblockClose;let receiptOverrides={};const terminal=new Map();
function page(iid){
 const w=new JSDOM(fs.readFileSync(path.join(web,"index.html"),"utf8"),{url:"http://rejection.test",runScripts:"dangerously"}).window;windows.push(w);browser.install(w);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w.crypto,"subtle",{value:crypto.webcrypto.subtle});w.crypto.randomUUID=()=>crypto.randomUUID();w.setInterval=()=>0;
 w.fetch=async(url,config)=>{
  const response=(body,status=200)=>new Response(JSON.stringify(body),{status});
  if(config.method==="POST"&&url.endsWith("/close")){
   closes++;if(failClose)return response({error:{code:"OUTCOME_UNKNOWN"}},409);
   const body=JSON.parse(config.body),request=body.request;
   terminal.set(request.request_key,{namespace:"spec-run-terminal.v1",status:"CLOSED_NOT_ACCEPTED",principal_id:principal,project_id:project,app_id:app,instance_id:iid,release_id:release,request_key:request.request_key,request,wire_request_fingerprint:hash(request),new_model_requests:0,project_writes:0});
   if(holdClose){closeEntered=true;await new Promise(resolve=>unblockClose=resolve);}
   if(loseClose)throw TypeError("synthetic lost close response after commit");
   return response({closed:true});
  }
  if(config.method==="POST"){
   posts++;entered=true;const body=JSON.parse(config.body);await new Promise(resolve=>unblock=resolve);
   return response({error:{code:"VERSION_CONFLICT"},submission_rejection:{namespace:"internal-run-rejection.v1",endpoint:"runs",principal_id:principal,project_id:project,instance_id:iid,request_key:body.request_key,request_fingerprint:hash(body),acceptance:"NOT_ACCEPTED",previous_request:"ABSENT",phase}},409);
  }
  gets++;if(holdGet){getEntered=true;await new Promise(resolve=>unblockGet=resolve);}
  const value=terminal.get(url.split("/").at(-1));
  return value?response({...value,...receiptOverrides,...(badReceipt?{principal_id:id("user",9)}:{})}):response({error:{code:"OUTCOME_UNKNOWN"}},409);
 };
 for(const script of [...w.document.querySelectorAll("script[src]")]){const node=w.document.createElement("script");node.textContent=fs.readFileSync(path.join(web,script.getAttribute("src").slice(1)),"utf8");w.document.body.append(node);}
 w.fixture={principal,project,app,instance:iid,release,fp};
 w.eval(`token="synthetic-test-A";activeApp=fixture.app;document.getElementById("project-select").replaceChildren(new Option("Own",fixture.project));engineering={token,project:fixture.project,app:fixture.app,appGeneration:appSelectionGeneration,instanceGeneration:0,spec:true,draft:{},instance:{id:fixture.instance,principal_id:fixture.principal,release_id:fixture.release,revision:1,release_fingerprint:fixture.fp}};`);
 return w;
}
const attempt=(w,retry=false)=>w.eval(`submitPersistentSpecRun(engineering,engineering.instance,${retry})`);
const pending=w=>w.eval("!!engineeringPending.get(engineering.instance.id)");
const check=(yes,label)=>{assert(yes,label);checks.push(label);};
async function start(iid){entered=false;const a=page(iid),b=page(iid),work=attempt(a);work.catch(()=>{});while(!entered)await new Promise(r=>setTimeout(r,1));b.eval("specRecoveryRestore(engineering,engineering.instance)");return {a,b,work};}
(async()=>{try{
 for(const [n,p] of [[1,"TX_ROLLED_BACK"],[2,"VALIDATION_NOT_STARTED"]]){
  phase=p;const {a,b,work}=await start(id("iinstance",n));const before=closes;unblock();await work;
  check(closes===before+1,p+": strict transient proof requests server closure");
  check(!pending(a)&&pending(b),p+": A clears only after GET; B retains cached key without storage events");
  const beforePosts=posts;await attempt(b,true);check(!pending(b)&&posts===beforePosts,p+": B authenticated terminal GET clears cached key without POST");
 }
 failClose=true;const failed=await start(id("iinstance",3));unblock();await assert.rejects(failed.work);check(pending(failed.a)&&pending(failed.b),"close failure preserves both intents");failClose=false;
 const key=failed.b.eval("specRecoveryKey(engineering,engineering.instance)");failed.b.localStorage.removeItem(key);await assert.rejects(attempt(failed.b,true));check(pending(failed.b),"forged storage deletion alone cannot unlock cached key");
 const fresh=await start(id("iinstance",4));unblock();await fresh.work;badReceipt=true;await assert.rejects(attempt(fresh.b,true));check(pending(fresh.b),"wrong authenticated receipt scope retains cached intent");badReceipt=false;
 const realKey=fresh.b.eval("specRecoveryKey(engineering,engineering.instance)");
 const original=JSON.parse(fresh.b.eval("JSON.stringify(specRecoveryMetadata.get(engineeringPending.get(engineering.instance.id)).record)"));
 const replacement={...original,request_key:crypto.randomUUID()};
 holdGet=true;const late=attempt(fresh.b,true);while(!getEntered)await new Promise(r=>setTimeout(r,1));
 fresh.b.localStorage.setItem(realKey,JSON.stringify(replacement));fresh.b.document.getElementById("identity-switch").click();
 const beforeUI=fresh.b.document.getElementById("internal-run-status").textContent;
 unblockGet();await late;
 check(fresh.b.localStorage.getItem(realKey)===JSON.stringify(replacement),"identity-switch late terminal GET cannot delete a replacement at the exact original scope key");
 check(fresh.b.document.getElementById("internal-run-status").textContent===beforeUI,"identity-switch late terminal GET cannot repaint status");
 holdGet=false;getEntered=false;
 loseClose=true;const lost=await start(id("iinstance",5));unblock();await assert.rejects(lost.work);check(pending(lost.a)&&pending(lost.b),"lost close response after commit retains both original intents");loseClose=false;
 const beforeLost={posts,closes},restarted=page(id("iinstance",5));await attempt(restarted,true);await attempt(lost.b,true);
 check(!pending(restarted)&&!pending(lost.b)&&posts===beforeLost.posts&&closes===beforeLost.closes,"fresh DOM and cached B recover committed lost-close result with GET only");
 holdClose=true;const contended=await start(id("iinstance",6));unblock();while(!closeEntered)await new Promise(r=>setTimeout(r,1));
 await assert.rejects(attempt(contended.b,true),/RECOVERY_REQUEST_BUSY/);check(pending(contended.b),"B cannot consume or queue closure while A holds the scope Web Lock");
 holdClose=false;unblockClose();await contended.work;await attempt(contended.b,true);check(!pending(contended.b),"B explicitly recovers terminal after contention without execution POST");
 const checked=await start(id("iinstance",7));unblock();await checked.work;const beforeChecked=posts;
 for(const [field,value] of [["wire_request_fingerprint","b".repeat(64)],["status","UNKNOWN"],["release_id",id("irelease",9)],["project_id",id("proj",9)],["app_id",id("app",9)],["instance_id",id("iinstance",9)],["request_key",crypto.randomUUID()],["request",{}]]){
  receiptOverrides={[field]:value};await assert.rejects(attempt(checked.b,true));check(pending(checked.b)&&posts===beforeChecked,"terminal mismatch "+field+" preserves pending without execution POST");
 }
 receiptOverrides={};const compareKey=checked.b.eval("specRecoveryKey(engineering,engineering.instance)"),compareOriginal=JSON.parse(checked.b.eval("JSON.stringify(specRecoveryMetadata.get(engineeringPending.get(engineering.instance.id)).record)")),compareReplacement={...compareOriginal,request_key:crypto.randomUUID()};
 holdGet=true;getEntered=false;const compare=attempt(checked.b,true);compare.catch(()=>{});while(!getEntered)await new Promise(r=>setTimeout(r,1));checked.b.localStorage.setItem(compareKey,JSON.stringify(compareReplacement));unblockGet();await assert.rejects(compare);
 check(checked.b.localStorage.getItem(compareKey)===JSON.stringify(compareReplacement)&&pending(checked.b),"current-view terminal GET compares exact record and cannot erase a replacement intent");
 const proof={status:"PASS",checks,posts,closes,gets,platform:"JSDOM_SHARED_STORAGE_WEB_LOCKS_ADAPTER",http:"SYNTHETIC",native_browser:"NOT_RUN"};if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(proof,null,2));process.stdout.write(JSON.stringify(proof)+"\n");
 }catch(e){if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify({status:"FAIL",checks,error:e.stack},null,2));process.stderr.write(e.stack+"\n");process.exitCode=1;}finally{windows.forEach(w=>w.close());}})();
