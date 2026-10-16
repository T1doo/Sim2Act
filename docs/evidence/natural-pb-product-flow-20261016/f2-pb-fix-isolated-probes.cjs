"use strict";
const fs=require("node:fs"),vm=require("node:vm"),assert=require("node:assert/strict"),crypto=require("node:crypto");
const root=process.cwd(),internal=fs.readFileSync(root+"/src/sim2act/web/internal.js","utf8"),app=fs.readFileSync(root+"/src/sim2act/web/app.js","utf8");
const cut=(s,start,end)=>{const a=s.indexOf(start),b=s.indexOf(end,a);assert(a>=0&&b>a,start);return s.slice(a,b);};
const result={classification:"ISOLATED_ACTUAL_PRODUCTION_FUNCTIONS_SYNTHESIZED_API_AND_DOM_NODES_NO_WORKER",checks:[],cases:[],worker:"NOT_RUN",real_model:"NOT_RUN",full_dom:"NOT_RUN",assets:{"app.js":crypto.createHash("sha256").update(app).digest("hex"),"internal.js":crypto.createHash("sha256").update(internal).digest("hex")}};
const check=(v,label)=>{assert(v,label);result.checks.push(label);};
async function gateRace(){
 let release;const posts=[],pending=new Map(),defaults=new Map(),s={busy:false,edit:0,review:{request:{request_key:"synthetic-key"},review_fingerprint:"fp",consent:"synthetic"}},view={busy:false};
 const c={s,view,current:()=>true,pbUsePending:pending,scope:"scope",instance:{id:"instance"},isPB:true,pbUseUnknown:()=>false,engineeringPending:defaults,ack:{checked:true},buttons:()=>{},api:async(url,method)=>{if(url==="/api/capabilities")return new Promise(r=>release=r);posts.push({url,method});return{};},status:{textContent:""},mode:{route:"pb-use"},receipt:async()=>{},$:()=>({disabled:false}),structuredClone};
 const source=cut(internal,"  const action=async commit=>","\n  submit.onclick=");const action=vm.runInNewContext(source+"\naction",c),work=action(true);defaults.set("instance",{request_key:"other-default"});view.busy=true;release({natural_spec_generation:{version:"natural-spec-generation-availability.v1",availability:"OFFLINE_TEST_ONLY",provider:"intern-s2",live_request_allowance:0},connection:{mode:"MOCK",model:"intern-s2"}});await work;
 check(posts.length===0&&pending.size===0&&defaults.size===1,"after capability await, another default intent blocks PB POST and preserves that intent");check(c.status.textContent.includes("未提交本次 Run"),"post-await mutual exclusion has an explicit stopped status");
}
async function returnNull(){
 let cleared=false;const c={naturalUsePreparation:{returning:true,firstCreation:{mode:"PB"}},engineering:null,clearNaturalUsePreparation:()=>{cleared=true;c.naturalUsePreparation=null;},clearNaturalLogic:()=>{},clearPBUse:()=>{},clearNaturalTaskExtraction:()=>{},engineeringCurrent:()=>false};
 const fn=vm.runInNewContext(cut(internal,"async function showInternalInstance(","\nasync function showInternalRun(")+"\nshowInternalInstance",c);await fn("other-instance",{});check(cleared,"first-creation PB returning state safely clears before instance navigation without reading missing instance");
}
async function opening(kind){
 const nodes=new Map();const node=id=>{if(!nodes.has(id))nodes.set(id,{id,value:id==="project-select"?"project":"",dataset:{},textContent:"",hidden:false,disabled:false,append(){},replaceChildren(){},focus(){}});return nodes.get(id);};
 const candidate={namespace:"pa-natural-spec-app.v1",spec_task:{kind:"pb_natural_spec_task.v1",source_run_id:"source-run"},manifest:{origin:"task_run"},goal:{},spec_recipe:{steps:[]}},saved={id:"PB",candidate_fingerprint:"candidate-fp",reviewed:{candidate}},draft={id:"PB",project_id:"project",name:"Saved PB",fingerprint:"candidate-fp",candidate,input_guidance:{mode:"MODEL_SPEC_CHECKLIST"}},calls=[];
 const s={saved,busy:false,sourceConnected:true,open:{},view:{project:"project",app:"source-app",appGeneration:0,token:"identity"}},g={mode:"PB",stage:"extract",extraction:s,identity:"identity",connection:0,project:"project",workspace:0,appGeneration:0};
 let release;
 const c={s,view:s.view,rid:"source-run",token:"identity",identityConnectionGeneration:0,workspaceSelectionGeneration:0,appSelectionGeneration:0,engineeringGeneration:0,activeApp:"source-app",activeAppProject:"project",engineering:s.view,naturalFirstGuide:g,naturalTaskExtraction:s,appPreviewRequests:new Map(),$:node,goalRunCanonical:JSON.stringify,naturalTaskCurrent:x=>x===c.naturalTaskExtraction&&x.sourceConnected,naturalTaskButtons:()=>{},renderNaturalFirstGuide:()=>{},clearInternalRunReread:()=>{},engineeringButtons:()=>{},engineeringStatus:()=>{},invalidateInternalContent:v=>{v.invalidated=true;}};
 c.clearApp=preserve=>{if(c.naturalFirstGuide!==preserve)c.naturalFirstGuide=null;s.sourceConnected=false;c.naturalTaskExtraction=null;c.engineering=null;c.appSelectionGeneration++;c.activeApp=null;c.activeAppProject=null;};
 c.clearNaturalFirstGuide=()=>{const old=c.naturalFirstGuide;c.naturalFirstGuide=null;if(old?.opening||old?.view===c.engineering)c.clearApp();};
 c.api=async(url,method="GET")=>{calls.push({url,method});if(url==="/api/apps/PB"){
   if(kind==="403")throw Error("GRANT_REVOKED");
   if(kind==="late-workspace")await new Promise(resolve=>release=resolve);
   return kind==="candidate-conflict"?{...draft,fingerprint:"bad"}:draft;
  }
  if(url.endsWith("/releases")){if(kind==="history-failure")throw Error("GRANT_REVOKED");if(kind==="late-selection")await new Promise(resolve=>release=resolve);return {items:[]};}
  if(url.endsWith("/instances"))return{items:[]};throw Error("unexpected API "+url);
 };
 const ctx=vm.createContext(c);
 vm.runInContext(cut(internal,"function engineeringCurrent(","\nfunction engineeringStatus("),ctx);
 vm.runInContext(cut(internal,"async function refreshInternal(","\nasync function showInternalInstance("),ctx);
 vm.runInContext(cut(internal,"async function openInternal(","\nasync function refreshInternal("),ctx);
 vm.runInContext(cut(app,"async function showApp(","\n$(\"extraction-form\").onsubmit"),ctx);
 vm.runInContext(cut(app,"function naturalFirstGuideCurrent(","\nfunction clearNaturalFirstGuide("),ctx);
 const a=internal.indexOf("  s.open.onclick=async()=>{"),b=internal.indexOf("\n  };\n}",a);assert(a>=0&&b>a);vm.runInContext(internal.slice(a,b+5),ctx);
 const work=s.open.onclick();
 if(kind.startsWith("late-")){
  for(let i=0;!release&&i<20;i++)await new Promise(r=>setImmediate(r));assert(release,"held API");node("app-create-status").textContent="NEW VIEW";c.naturalFirstGuide=null;
  if(kind==="late-workspace")c.workspaceSelectionGeneration++;
  else {c.appSelectionGeneration++;c.activeApp="other-app";c.engineering={app:"other-app",marker:"NEW"};}
  const before=calls.length;release();await work;
  check(node("app-create-status").textContent==="NEW VIEW",kind+": late old opening cannot replace current status");
  check(calls.length===before,kind+": no chained API read after stale opening response");
  if(kind==="late-selection")check(c.engineering?.marker==="NEW",kind+": failed old opening cannot clear new engineering view");
 }else{
  await work;
  if(kind==="success")check(c.naturalFirstGuide===g&&g.stage==="internal"&&g.view===c.engineering&&c.engineering.selectionCurrent===null&&c.engineering.historyReady===true,"success: full app/history chain releases exact temporary fence and advances same guide");
  else {check(c.naturalFirstGuide===null&&c.engineering===null,kind+": failed current opening ends own guide/view");check(node("app-create-status").textContent.includes("已保存的 P-B 应用保留")&&node("app-create-status").dataset.state==="error",kind+": failure states saved content retained and directory reselection");}
 }
 check(calls.every(x=>x.method==="GET"),kind+": opening performs zero mutations");result.cases.push({kind,calls,status:node("app-create-status").textContent});
}
(async()=>{try{await gateRace();await returnNull();for(const kind of ["403","candidate-conflict","history-failure","late-workspace","late-selection","success"])await opening(kind);result.status="PASS";}catch(e){result.status="FAIL";result.error=e.stack;process.exitCode=1;}finally{fs.writeFileSync(process.argv[2],JSON.stringify(result,null,2));console.log(JSON.stringify({status:result.status,checks:result.checks.length,error:result.error}));}})();
