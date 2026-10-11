"use strict";
// Controlled field-handler/fence coverage only; no HTTP, Worker, or semantic signoff.
const fs=require("fs"),assert=require("assert/strict"),crypto=require("crypto");
const {JSDOM}=require("jsdom");
const base="/workspace/Sim2Act/src/sim2act/web/";
const source=fs.readFileSync(base+"owner-review.js","utf8"),internal=fs.readFileSync(base+"internal.js","utf8");
const actualEngineeringCurrent=internal.match(/function engineeringCurrent\(view\) \{[\s\S]*?\n\}/)[0];
const items=["goal","known:0","assumptions:0","unresolved:0","constraints:0","constraints:1","acceptance_checks:0"].map(id=>({id,text:"CONTROLLED fixture criterion; semantic NOT_RUN"}));
const controls=["owner-run","owner-ack","owner-stop-reason","owner-key",...items.flatMap(i=>["owner-choice-"+i.id,"owner-reason-"+i.id])];
const output={transport:"CONTROLLED local-source JSDOM field handlers, no HTTP",semantic_owner_signoff:"NOT_RUN",live_models:0,native_browser:"NOT_RUN",native_os_undo:"NOT_RUN",source_sha256:{"owner-review.js":crypto.createHash("sha256").update(source).digest("hex"),"internal.js":crypto.createHash("sha256").update(internal).digest("hex")},cases:[]};
function boot(){
 const dom=new JSDOM(fs.readFileSync(base+"index.html","utf8"),{runScripts:"outside-only",url:"http://sim2act.invalid/"}),w=dom.window;
 w.$=id=>w.document.getElementById(id);w.safe=fn=>fn;
 w.api=()=>{throw Error("HTTP NOT_RUN in controlled field probe");};
 w.token="synthetic-controlled";w.activeApp="controlled-app";w.appSelectionGeneration=9;w.workspaceSelectionGeneration=3;
 w.$("project-select").append(new w.Option("controlled project","controlled-project"));w.$("project-select").value="controlled-project";
 w.engineering={token:w.token,project:"controlled-project",app:w.activeApp,appGeneration:9,instanceGeneration:1,instance:{id:"controlled-instance"}};
 w.fakeView={engineering:w.engineering,instanceGeneration:1,token:w.token,project:"controlled-project",iid:"controlled-instance",state:null,busy:false};
 w.fakeState={instance_id:"controlled-instance",owner_acceptance:"PENDING",sequence:1,content_access:true,history:[],latest:{kind:"PREPARE"},record:{id:"controlled-record",kind:"PREPARE",payload:{contract:{items}}}};
 w.eval(actualEngineeringCurrent+"\n"+source+"\nglobalThis.ownerProbe={init(){ownerView=globalThis.fakeView;ownerRender(ownerView,globalThis.fakeState);},fence(){return ownerFence(ownerView);},edit(){return ownerEditGeneration;},clearRestore(){clearOwnerReview();ownerView=globalThis.fakeView;}};");
 w.$("owner-run").replaceChildren(new w.Option("A","A"),new w.Option("B","B"));w.$("owner-run").value="A";
 w.ownerProbe.init();return {dom,w};
}
for(const id of controls)for(const eventName of ["input","change"]){
 const {dom,w}=boot(),el=w.$(id),before=el.type==="checkbox"?el.checked:el.value,guard=w.ownerProbe.fence(),generation=w.ownerProbe.edit();
 assert.equal(guard(),true);
 if(el.type==="checkbox")el.checked=!before;else el.value=el.tagName==="SELECT"?(id==="owner-run"?"B":"ACCEPT"):"CONTROLLED B";
 const first=eventName==="input"?new w.InputEvent("input",{bubbles:true,inputType:"insertText",data:"CONTROLLED B"}):new w.Event("change",{bubbles:true});
 el.dispatchEvent(first);
 if(el.type==="checkbox")el.checked=before;else el.value=before;
 const undo=eventName==="input"?new w.InputEvent("input",{bubbles:true,inputType:"historyUndo",data:null}):new w.Event("change",{bubbles:true});
 el.dispatchEvent(undo);
 assert.equal(el.type==="checkbox"?el.checked:el.value,before);
 assert.equal(w.ownerProbe.edit(),generation+2);assert.equal(guard(),false);
 output.cases.push({id,event:eventName,restored_value:true,edit_generation_delta:2,prior_fence_current:false,isTrusted:[first.isTrusted,undo.isTrusted],status:"PASS"});dom.window.close();
}
for(const generation of ["workspaceSelectionGeneration","appSelectionGeneration","instanceGeneration","ownerGeneration"]){
 const {dom,w}=boot(),guard=w.ownerProbe.fence();assert.equal(guard(),true);
 if(generation==="instanceGeneration"){w.engineering.instanceGeneration++;w.engineering.instanceGeneration++;}
 else if(generation==="ownerGeneration"){w.ownerProbe.clearRestore();}
 else {w[generation]++;w[generation]++;}
 assert.equal(guard(),false);output.cases.push({generation,prior_fence_current:false,status:"PASS"});dom.window.close();
}
output.status="PASS";output.control_count=controls.length;output.case_count=output.cases.length;
fs.writeFileSync("/tmp/owner-version-acceptance-review-20261011/controlled-owner-fields.json",JSON.stringify(output,null,2)+"\n");
process.stdout.write(JSON.stringify({status:output.status,controls:controls.length,cases:output.cases.length})+"\n");
