"use strict";
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const base='/workspace/pa-page-root-cause-independent-20261018/wip-read-reuse-review/';
const internal=fs.readFileSync(base+'src/sim2act/web/internal.js','utf8'),app=fs.readFileSync('/workspace/Sim2Act/src/sim2act/web/app.js','utf8');
const start=internal.indexOf('async function openNaturalLogic('),end=internal.indexOf('\nasync function naturalLogicReadGraph(',start),open=internal.slice(start,end);
assert(start>=0&&end>start);
const current=internal.match(/function engineeringCurrent\(view\) \{[\s\S]*?\n\}/)[0];
const select=app.match(/function selectWorkspace\([^\n]*\) \{[\s\S]*?\n\}/)[0];
const cases=[];
async function probe(kind){
 let releaseHash;
 const nodes=new Map();const $=id=>{if(!nodes.has(id))nodes.set(id,{hidden:false,value:'',textContent:'',checked:false});return nodes.get(id);};$('project-select').value='project';
 const c={$,document:{querySelectorAll:()=>[]},token:'account',activeApp:'app',appSelectionGeneration:1,workspaceSelectionGeneration:10,identityConnectionGeneration:1,naturalFirstGuide:null,naturalLogicPending:new Map(),naturalLogicView:null,
  clearNaturalLogic(){c.naturalLogicView=null;$('natural-logic-panel').hidden=true;},clearNaturalFirstGuide(){},resumeOrdinaryOutcome(){},naturalLogicButtons(){},naturalLogicKey:()=>'',paHash:()=>new Promise(resolve=>releaseHash=resolve)};
 c.view={token:'account',project:'project',app:'app',appGeneration:1,instanceGeneration:1,instance:{id:'iid',release_id:'release',release_fingerprint:'same-hash'},draft:{candidate:{namespace:'pa-natural-spec-app.v1',spec_recipe:{steps:[{}, {operator:'model.spec.requirements'},{operator:'model.spec.qualifiers',inputs:{}},{},{},{}]}}}};c.engineering=c.view;
 vm.createContext(c);vm.runInContext(current+'\n'+select+'\n'+open,c);
 const pending=c.openNaturalLogic(c.view,{id:'release',fingerprint:'same-hash',snapshot:{}});assert.equal(typeof releaseHash,'function');assert.equal(c.naturalLogicView,null);
 if(kind==='workspace_ABA'){c.selectWorkspace('projects');c.selectWorkspace('apps');assert.equal(c.workspaceSelectionGeneration,12);assert.equal(c.engineeringCurrent(c.view),true);}
 else if(kind==='connection_ABA'){c.identityConnectionGeneration+=2;assert.equal(c.engineeringCurrent(c.view),true);}
 else if(kind==='same_instance_selection_generation'){c.view.instanceGeneration++;assert.equal(c.engineeringCurrent(c.view),true);}
 releaseHash('same-hash');await pending;
 const painted=!!c.naturalLogicView||!$('natural-logic-panel').hidden;
 assert.equal(painted,kind==='unchanged_current',kind);
 cases.push({case:kind,expected_paint:kind==='unchanged_current',painted,workspace:c.workspaceSelectionGeneration});
}
(async()=>{
 for(const kind of ['workspace_ABA','connection_ABA','same_instance_selection_generation','unchanged_current'])await probe(kind);
 const result={classification:'NON_AUTHOR_EXACT_POST_FIX_WIP_FUNCTION_CONTROLLED_CRYPTO_AWAIT_PROBE_NOT_ACTUAL_HTTP',source_function_sha256:crypto.createHash('sha256').update(open).digest('hex'),status:'PASS',cases,actual_product_function:'openNaturalLogic',actual_navigation_function:'selectWorkspace',workers:0,model_calls:0};
 fs.writeFileSync(base+'crypto-aba-result.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
