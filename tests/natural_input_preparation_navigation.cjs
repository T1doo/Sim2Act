"use strict";
// Real shared form scripts, synthesized API and synthetic saved-view setup only.
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict"),crypto=require("node:crypto"),{JSDOM}=require("jsdom");
const root=process.cwd(),web=path.join(root,"src/sim2act/web"),durable=require(path.join(root,"tests/durable_browser.cjs"))();
const project="proj_"+"1".repeat(32),other="proj_"+"2".repeat(32),appId="app_"+"3".repeat(32),instanceId="instance_"+"4".repeat(32),resourceId="res_"+"5".repeat(32),goalId="goal_"+"6".repeat(32),releaseId="irelease_"+"7".repeat(32),fp="a".repeat(64);
const app={id:appId,project_id:project,name:"Synthetic saved app",fingerprint:fp,candidate:{namespace:"pa-natural-spec-app.v1",goal_application:{},manifest:{data_bindings:[]}},input_guidance:{mode:"MODEL_SPEC_CHECKLIST"}};
const instance={id:instanceId,project_id:project,source_app_id:appId,release_id:releaseId,release_fingerprint:fp,revision:1,data_version:1,runs:[],data:[]};
const result={classification:"ACTUAL_INDEX_APP_INTERNAL_USE_OWNER_SCRIPTS_SYNTHESIZED_API_NO_WORKER",checks:[],cases:[],real_model:"NOT_RUN",worker:"NOT_RUN",native_browser:"NOT_RUN"};
let dom,w,$,calls,hold,backend;
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function waitForGate(){const end=Date.now()+5000;while(!hold?.used){if(Date.now()>end)throw Error("synthetic API hold not reached: "+$("error").textContent);await tick();}}
const check=(condition,label)=>{assert(condition,label);result.checks.push(label);};
async function gesture(el,perform,bindings){assert(el?.isConnected,`connected ${el?.id}`);const work=[],restore=[];for(const [node,key] of bindings){const original=node?.[key];if(typeof original!=="function")continue;const wrapper=function(event){const value=original.call(this,event);work.push(Promise.resolve(value));return value;};node[key]=wrapper;restore.push(()=>{if(node[key]===wrapper)node[key]=original;});}try{perform();await Promise.all(work);}finally{restore.forEach(fn=>fn());}}
const click=value=>{const el=typeof value==="string"?$(value):value;return gesture(el,()=>el.click(),[[el,"onclick"],[el?.form,"onsubmit"]]);};
const edit=(id,value)=>{const el=$(id);return gesture(el,()=>{el.value=value;el.dispatchEvent(new w.Event("input",{bubbles:true}));el.dispatchEvent(new w.Event("change",{bubbles:true}));},[[el,"oninput"],[el,"onchange"]]);};
const nav=id=>click(w.document.querySelector(`#workspace-nav [data-tab=${id}]`));
const posts=()=>calls.filter(row=>row.method==="POST");
async function setup(preserveBackend=false){
 dom?.window.close();dom=new JSDOM(fs.readFileSync(path.join(web,"index.html"),"utf8"),{url:"http://synthetic.invalid/",runScripts:"dangerously",pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);calls=[];hold=null;if(!preserveBackend)backend={resources:[],goals:[]};
 durable.install(w);w.setInterval=()=>0;w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w,"crypto",{value:crypto.webcrypto});
 w.fetch=async(url,options={})=>{
  const method=options.method||"GET",body=options.body&&JSON.parse(options.body),request={url,method,body};calls.push(request);let value,status=200;
  const isResource=method==="POST"&&url===`/api/projects/${project}/resources`,isGoal=method==="POST"&&url===`/api/projects/${project}/goal-cards`;
  if(isResource){value={id:resourceId};status=201;backend.resources.push({id:resourceId,project_id:project,name:body.name,format:body.format,content:body.content,hash:fp});}
  else if(isGoal){value={id:goalId,version:1};status=201;backend.goals.push({id:goalId,project_id:project,title:body.title,version:1,fingerprint:fp,content:body,history:[{version:1,fingerprint:fp,snapshot:{schema_version:"F2-goal-card.v1",content:body,resource_snapshots:body.resource_refs.map(resource_id=>({resource_id,hash:fp}))}}]});}
  else if(method!=="GET")throw Error("unexpected synthetic write "+method+" "+url);
  else if(url==="/api/projects")value=options.headers?.Authorization?.includes("synthetic-B")?[{id:other,name:"Other identity project"}]:[{id:project,name:"Original project"},{id:other,name:"Other owned project"}];
  else if(url==="/api/capabilities")value={capabilities:[],connections:[]};
  else if(url.endsWith("/resources"))value=url.includes(project)?backend.resources:[];
  else if(url.endsWith("/goal-cards"))value={items:url.includes(project)?backend.goals:[]};
  else if(url===`/api/goal-cards/${goalId}`)value=backend.goals.at(-1);
  else if(url.endsWith("/candidate-options"))value={items:[],goal_version:1,materials:[],capabilities:[]};
  else if(url.startsWith("/api/apps"))value={items:[]};
  else if(url.endsWith("/conditional-apps"))value={items:[]};
  else value=[];
  request.status=status;request.response=structuredClone(value);
  if(hold&&!hold.used&&hold.url===url&&hold.method===method){hold.used=true;await new Promise(resolve=>hold.resolve=resolve);if(hold.lost){request.fault="SYNTHETIC_ACCEPTED_REPLY_LOST";throw Error("synthetic accepted reply lost");}}
  return new Response(JSON.stringify(value),{status,headers:{"Content-Type":"application/json"}});
 };
 for(const name of ["app.js","internal.js","use.js","owner-review.js"]){const node=w.document.createElement("script");node.textContent=fs.readFileSync(path.join(web,name),"utf8");w.document.body.append(node);}
 $("project-select").append(new w.Option("Original project",project),new w.Option("Other owned project",other));$("project-select").value=project;
 w.eval('token="synthetic-A";selectWorkspace("apps");');$("login").hidden=true;$("identity-switch").hidden=false;
}
function prepare(){
 const panel=w.document.createElement("section");panel.id="pb-use-panel";panel.innerHTML='<input id="pb-use-ack" type="checkbox"><pre id="pb-use-proof"></pre>';$("internal-panel").append(panel);
 w.__preparedApp=structuredClone(app);w.__preparedInstance=structuredClone(instance);
 w.eval('activeApp=__preparedApp.id;activeAppProject=__preparedApp.project_id;engineering={token,project:__preparedApp.project_id,app:__preparedApp.id,appGeneration:appSelectionGeneration,draft:__preparedApp,instance:__preparedInstance,instanceGeneration:1,busy:false};document.getElementById("internal-panel").hidden=false;beginNaturalUsePreparation({view:engineering,instance:engineering.instance,busy:false,edit:0,review:null,buttons:()=>{}},()=>true);');
 check(!!$("natural-use-preparation"),"synthetic saved view opens actual shared preparation panel");
 return w.eval("naturalUsePreparation");
}
async function material(){await edit("resource-name","new.txt");await edit("format","txt");await edit("content","New source with an unresolved decision.");await click("resource-save");if(w.eval("naturalUsePreparation?.step")==="material-saved"){w.renderResourceMaterial();check(["resource-name","format","content","resource-save"].every(id=>$(id).disabled),"background material renderer keeps saved preparation fields and Save disabled");}}
async function goal(){await click("natural-prep-goal-next");check(w.eval("naturalUsePreparation.material.id")===resourceId&&w.eval("naturalUsePreparation.material.body.content")==="New source with an unresolved decision."&&$("goal-card-resources").value===resourceId,"next step preserves exact saved material body and response ID");await edit("goal-card-title","New source goal");await edit("goal-card-goal","Review this new source");await edit("goal-card-unresolved","Human review pending");await edit("goal-card-acceptance_checks","Read and judge the original source");}
async function navigate(kind){
 if(kind==="project"){await nav("projects");await edit("project-select",other);await edit("project-select",project);await nav("apps");}
 else {await click("identity-switch");await edit("token","synthetic-B");await click("connect");await click("identity-switch");await edit("token","synthetic-A");await click("connect");await nav("apps");}
 $("app-title").textContent="CURRENT CLEAN";$("goal-card-title").value="current new context";
}
(async()=>{try{
 for(const stage of ["material","goal"])for(const kind of ["project","identity"]){
  await setup();const old=prepare();if(stage==="goal"){await material();await goal();}
  hold={url:`/api/projects/${project}/${stage==="material"?"resources":"goal-cards"}`,method:"POST",used:false};
  const saving=stage==="material"?material():click("goal-card-save");await waitForGate();const gate=hold;await navigate(kind);const before=calls.length;gate.resolve();await saving;
  check(!$("natural-use-preparation")&&w.eval("naturalUsePreparation")===null,`${stage}/${kind} ABA: accepted late reply does not revive old preparation`);
  check($("app-title").textContent==="CURRENT CLEAN"&&$("goal-card-title").value==="current new context",`${stage}/${kind} ABA: old reply does not replace current app or Goal editing context`);
  check(!old.goal&&calls.slice(before).every(row=>!(row.method==="GET"&&row.url===`/api/goal-cards/${goalId}`)),`${stage}/${kind} ABA: no late Goal read or return-to-app followup`);
  check(posts().length===(stage==="material"?1:2)&&!calls.some(row=>row.url.includes("-use-runs")||row.url.endsWith("/runs")&&row.method==="POST"),`${stage}/${kind} ABA: one original save only and no Run`);
  result.cases.push({stage,kind,calls:structuredClone(calls)});
 }
 await setup();const unknown=prepare();await material();await goal();hold={url:`/api/projects/${project}/goal-cards`,method:"POST",used:false,lost:true};const saving=click("goal-card-save");await waitForGate();hold.resolve();await saving;
 check(w.eval("naturalPreparationGoalRequests.get(naturalUsePreparation.key).state")==="unknown"&&$("natural-prep-goal-read").hidden===false,"unknown accepted Goal save preserves pending intent and offers read-only verification");
 const unknownPosts=posts().length;await gesture($("goal-card-form"),()=>$("goal-card-form").dispatchEvent(new w.Event("submit",{cancelable:true})),[[$("goal-card-form"),"onsubmit"]]);check(posts().length===unknownPosts,"pending unknown Goal rejects duplicate shared-form submission");
 await click("natural-prep-goal-read");check(posts().length===unknownPosts&&!unknown.goal&&$("natural-prep-return").hidden,"unknown Goal verification only GETs and never claims a matching list item or enables return");
 await click("natural-prep-goal-reset");check(!$("natural-use-preparation")&&posts().length===unknownPosts,"explicit unknown-intent reset restores shared forms without another save");
 result.unknown_goal={calls:structuredClone(calls),backend_goal_count:backend.goals.length};
 await setup();const resourceForm=$("resource-form"),goalForm=$("goal-card-form"),resourceParent=resourceForm.parentNode,goalParent=goalForm.parentNode,accept=$("resource-file").accept,formats=[...$("format").options].map(o=>[o.value,o.disabled]);prepare();await click("natural-prep-cancel");
 check(resourceForm.parentNode===resourceParent&&goalForm.parentNode===goalParent&&!$("natural-use-preparation"),"cancel returns the original shared form nodes to their original parents");
 check($("resource-file").accept===accept&&JSON.stringify([...$("format").options].map(o=>[o.value,o.disabled]))===JSON.stringify(formats)&&!$("goal-card-resources").disabled,"cancel restores original CSV/JSON file selection and generic Goal resource controls");
 check(posts().length===0,"preparation cancellation before Save performs zero writes");await nav("resources");await edit("resource-name","restored.csv");await edit("format","csv");await edit("content","amount\n3\n");await click("resource-save");check(posts().length===1&&posts()[0].body.format==="csv"&&posts()[0].body.content==="amount\n3\n","restored shared resource form retains normal CSV save body");
 await nav("projects");await edit("goal-card-title","Generic goal after cancel");await edit("goal-card-goal","Check generic saved material");const option=[...$("goal-card-resources").options].find(o=>o.value===resourceId);assert(option,"generic saved CSV option");option.selected=true;await click("goal-card-save");check(posts().length===2&&posts()[1].url===`/api/projects/${project}/goal-cards`&&JSON.stringify(posts()[1].body.resource_refs)===JSON.stringify([resourceId]),"restored generic Goal Save uses the existing API and explicit selected CSV");
 check(!calls.some(row=>row.method==="POST"&&row.url.endsWith("/runs")),"generic shared-form regression creates no automatic Run");result.restored_forms={calls:structuredClone(calls)};
 await setup(true);await edit("token","synthetic-A");await click("connect");check(posts().length===0&&!$("natural-use-preparation")&&w.eval("naturalUsePreparation")===null,"cold page only GETs saved metadata and does not resurrect preparation or execute");
 result.status="PASS";
 }catch(error){result.status="FAIL";result.error=error.stack;process.exitCode=1;}finally{
 result.assets=Object.fromEntries(["index.html","app.js","internal.js","use.js","owner-review.js"].map(name=>[name,crypto.createHash("sha256").update(fs.readFileSync(path.join(web,name))).digest("hex")]));fs.writeFileSync(process.argv[2],JSON.stringify(result,null,2));dom?.window.close();console.log(JSON.stringify({status:result.status,checks:result.checks.length,error:result.error}));
 }})();
