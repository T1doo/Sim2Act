"use strict";
// Actual first-guide/forms/generation gate scripts; synthesized API, no Worker.
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict"),crypto=require("node:crypto"),{JSDOM}=require("jsdom");
const root=process.cwd(),web=path.join(root,"src/sim2act/web"),durable=require(path.join(root,"tests/durable_browser.cjs"))();
const p="proj_"+"1".repeat(32),q="proj_"+"2".repeat(32),resourceId="res_"+"3".repeat(32),goalId="goal_"+"4".repeat(32),fp="a".repeat(64);
const files=["app.js","natural-goal.js","goal-application.js","internal.js","use.js","owner-review.js"],result={classification:"ACTUAL_FIRST_GUIDE_SHARED_FORMS_GENERATION_GATE_SCRIPTS_SYNTHESIZED_API",checks:[],cases:[],worker:"NOT_RUN",real_model:"NOT_RUN",native_browser:"NOT_RUN"};
let dom,w,$,calls,hold,backend,availability,lostGoal;
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function waitHold(){const end=Date.now()+5000;while(!hold?.used){if(Date.now()>end)throw Error("API hold not reached: "+$("error").textContent);await tick();}}
const check=(condition,label)=>{assert(condition,label);result.checks.push(label);};
async function gesture(el,perform,bindings){assert(el?.isConnected,`connected ${el?.id}`);const work=[],restore=[];for(const [node,key] of bindings){const original=node?.[key];if(typeof original!=="function")continue;const wrapper=function(event){const value=original.call(this,event);work.push(Promise.resolve(value));return value;};node[key]=wrapper;restore.push(()=>{if(node[key]===wrapper)node[key]=original;});}try{perform();await Promise.all(work);}finally{restore.forEach(fn=>fn());}}
const click=value=>{const el=typeof value==="string"?$(value):value;assert(el&&!el.disabled,"enabled "+(el?.id||value));return gesture(el,()=>el.click(),[[el,"onclick"],[el.form,"onsubmit"]]);};
const edit=(id,value)=>{const el=$(id);return gesture(el,()=>{el.value=value;el.dispatchEvent(new w.Event("input",{bubbles:true}));el.dispatchEvent(new w.Event("change",{bubbles:true}));},[[el,"oninput"],[el,"onchange"]]);};
const nav=id=>click(w.document.querySelector(`#workspace-nav [data-tab=${id}]`));
const generated=()=>calls.filter(row=>row.method==="POST"&&row.url.endsWith("/application-runs"));
async function setup(){
 dom?.window.close();dom=new JSDOM(fs.readFileSync(path.join(web,"index.html"),"utf8"),{url:"http://synthetic.invalid/",runScripts:"dangerously",pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);calls=[];hold=null;lostGoal=false;availability="OFFLINE_TEST_ONLY";backend={resources:[],goals:[]};durable.install(w);w.setInterval=()=>0;w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w,"crypto",{value:crypto.webcrypto});
 w.fetch=async(url,options={})=>{
  const method=options.method||"GET",body=options.body&&JSON.parse(options.body),record={url,method,body};calls.push(record);let value,status=200;
  if(method==="POST"&&url===`/api/projects/${p}/resources`){value={id:resourceId};status=201;backend.resources.push({id:resourceId,project_id:p,name:body.name,format:body.format,content:body.content,hash:fp});}
  else if(method==="POST"&&url===`/api/projects/${p}/goal-cards`){value={id:goalId,version:1};status=201;backend.goals.push({id:goalId,project_id:p,title:body.title,version:1,fingerprint:fp,content:body,history:[{version:1,fingerprint:fp,snapshot:{schema_version:"F2-goal-card.v1",content:body,resource_snapshots:body.resource_refs.map(resource_id=>({resource_id,hash:fp,format:"txt"}))}}]});}
  else if(method!=="GET"){status=409;value={error:{code:"VERSION_CONFLICT",message:"No synthetic generation or execution is allowed"}};}
  else if(url==="/api/projects")value=options.headers?.Authorization?.includes("synthetic-B")?[{id:q,name:"Other identity"}]:[{id:p,name:"Original project"},{id:q,name:"Other project"}];
  else if(url==="/api/capabilities")value={materials:["txt","md","csv","json"],tools:["resource.read"],connection:{model:"intern-s2",mode:"MOCK",status:"MOCK_ENGINEERING"},natural_spec_generation:{version:"natural-spec-generation-availability.v1",availability,provider:availability==="OFFLINE_TEST_ONLY"?"intern-s2":"disabled",live_request_allowance:0}};
  else if(url.endsWith("/resources"))value=url.includes(p)?backend.resources:[];
  else if(url.endsWith("/goal-cards"))value={items:url.includes(p)?backend.goals:[]};
  else if(url===`/api/goal-cards/${goalId}`)value=backend.goals.at(-1);
  else if(url.endsWith("/candidate-options"))value={items:[],goal_version:1,materials:[],capabilities:[]};
  else if(url.endsWith("/natural-planning-status"))value={provider:"disabled",live_request_allowance:0,available:false,reason:"PROVIDER_DISABLED"};
  else if(url.startsWith("/api/apps")||url.endsWith("/conditional-apps"))value={items:[]};
  else value=[];
  record.status=status;record.response=structuredClone(value);
  if(hold&&!hold.used&&hold.url===url&&hold.method===method){hold.used=true;await new Promise(resolve=>hold.resolve=resolve);}
  if(lostGoal&&method==="POST"&&url.endsWith("/goal-cards")){lostGoal=false;record.fault="SYNTHETIC_ACCEPTED_REPLY_LOST";throw Error("synthetic accepted Goal save reply lost");}
  return new Response(JSON.stringify(value),{status,headers:{"Content-Type":"application/json"}});
 };
 for(const name of files){const node=w.document.createElement("script");node.textContent=fs.readFileSync(path.join(web,name),"utf8");w.document.body.append(node);}
 $("project-select").append(new w.Option("Original project",p),new w.Option("Other project",q));$("project-select").value=p;w.eval('token="synthetic-A";selectWorkspace("apps");');$("login").hidden=true;$("identity-switch").hidden=false;await w.refreshApplicationUse([]);
}
async function saveFirstInputs({title="New first Goal",lost=false}={}){
 await click("natural-first-start");await edit("resource-name","first.txt");await edit("format","txt");await edit("content","The new source remains subject to human review.");await click("resource-save");await click("natural-prep-goal-next");await edit("goal-card-title",title);await edit("goal-card-goal","Review this source");await edit("goal-card-unresolved","Human meaning remains pending");await edit("goal-card-acceptance_checks","Read every source statement");lostGoal=lost;await click("goal-card-save");
}
async function toGeneration(options){await saveFirstInputs(options);await click("natural-prep-return");check(w.eval("activeGoalCard.id")===goalId&&$("goal-application-family").value==="natural_spec","first guide hands exact saved Goal to existing natural generation controller");}
async function navigate(kind){
 if(kind==="workspace")await nav("resources");
 else if(kind==="cancel")await click("natural-first-cancel");
 else if(kind==="project"){await nav("projects");await edit("project-select",q);await edit("project-select",p);}
 else {await click("identity-switch");await edit("token","synthetic-B");await click("connect");await click("identity-switch");await edit("token","synthetic-A");await click("connect");}
 $("goal-application-status").textContent="CURRENT CLEAN";
}
(async()=>{try{
 for(const kind of ["workspace","project","identity","cancel"]){
  await setup();await toGeneration();hold={url:"/api/capabilities",method:"GET",used:false};const action=click("goal-application-start");await waitHold();const gate=hold;await navigate(kind);const before=calls.length;gate.resolve();await action;
  check(generated().length===0&&w.eval("goalApplications.size")===0,`${kind}: late available capability response creates no generation intent or POST`);
  check(w.eval("naturalFirstGuide")===null&&$("natural-first-guide").hidden,`${kind}: late capability response cannot revive the cancelled first guide`);
  check(calls.slice(before).every(row=>row.method==="GET"),`${kind}: no late mutation follows the discarded capability read`);result.cases.push({kind,calls:structuredClone(calls)});
 }
 await setup();await toGeneration();hold={url:"/api/capabilities",method:"GET",used:false};const first=click("goal-application-start");await waitHold();const old=hold;await click("natural-first-cancel");await w.showGoalCard(goalId,p);await edit("goal-application-family","natural_spec");check($("goal-application-start").disabled,"same Goal reopened while old capability read is pending remains locked");old.resolve();await first;
 check(!$("goal-application-start").disabled&&generated().length===0,"same Goal ABA releases only the old read lock and re-enables a new explicit action");
 const beforeFresh=calls.filter(row=>row.url==="/api/capabilities").length;availability="BLOCKED";await click("goal-application-start");check(calls.filter(row=>row.url==="/api/capabilities").length===beforeFresh+1&&generated().length===0,"new explicit action freshly reads BLOCKED metadata and does not reuse old available response");result.same_goal_aba={calls:structuredClone(calls)};
 await setup();await saveFirstInputs({lost:true});const pending=w.eval("naturalPreparationGoalRequests.get(naturalUsePreparation.key)");check(pending?.state==="unknown"&&!$("natural-prep-goal-reset").hidden,"first Goal unknown accepted save retains bounded read/reset controls");const postCount=calls.filter(row=>row.method==="POST").length;await click("natural-prep-goal-reset");check(!$("natural-use-preparation")&&w.eval("naturalFirstGuide")===null&&$("natural-first-guide").hidden,"resetting first unknown Goal ends both preparation and first guide");check(calls.filter(row=>row.method==="POST").length===postCount&&!$("natural-first-start").disabled,"unknown reset creates no new write and permits a new explicit guide start");result.unknown_goal_reset={calls:structuredClone(calls)};
 await setup();const title="L".repeat(140);await toGeneration({title});check(Array.from($("goal-application-name").value).length===100&&$("goal-application-name").value===title.slice(0,100),"long valid Goal title produces a default application name within the existing 100-character bound");check(w.eval("activeGoalCard.snapshot.content.title")===title&&backend.goals[0].content.title===title,"bounded default application name does not truncate the complete saved Goal title");check(generated().length===0,"long-title default preparation performs zero generation or model calls");
 await setup();const resourceParent=$("resource-form").parentNode,goalParent=$("goal-card-form").parentNode,accept=$("resource-file").accept,formats=[...$("format").options].map(o=>[o.value,o.disabled]);await click("natural-first-start");await click("natural-first-cancel");check($("resource-form").parentNode===resourceParent&&$("goal-card-form").parentNode===goalParent,"first guide cancel restores the original shared form nodes");check($("resource-file").accept===accept&&JSON.stringify([...$("format").options].map(o=>[o.value,o.disabled]))===JSON.stringify(formats)&&!$("goal-card-resources").disabled,"first guide cancel preserves normal CSV/JSON and generic Goal controls");check(calls.every(row=>row.method==="GET"),"empty first guide cancellation performs zero writes");
 result.status="PASS";
 }catch(error){result.status="FAIL";result.error=error.stack;process.exitCode=1;}finally{result.assets=Object.fromEntries(["index.html",...files].map(name=>[name,crypto.createHash("sha256").update(fs.readFileSync(path.join(web,name))).digest("hex")]));fs.writeFileSync(process.argv[2],JSON.stringify(result,null,2));dom?.window.close();console.log(JSON.stringify({status:result.status,checks:result.checks.length,error:result.error}));}
})();
