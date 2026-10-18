"use strict";
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const internal=fs.readFileSync('/workspace/Sim2Act/src/sim2act/web/internal.js','utf8'),app=fs.readFileSync('/workspace/Sim2Act/src/sim2act/web/app.js','utf8');
const open=internal.split('\n').find(l=>l.startsWith('async function openNaturalLogic('));
const current=internal.match(/function engineeringCurrent\(view\) \{[\s\S]*?\n\}/)[0];
const select=app.match(/function selectWorkspace\([^\n]*\) \{[\s\S]*?\n\}/)[0];
let releaseHash;
const nodes=new Map();const $=id=>{if(!nodes.has(id))nodes.set(id,{hidden:false,value:'',textContent:'',checked:false});return nodes.get(id);};
$('project-select').value='project';
const sourceHash=crypto.createHash('sha256').update(open).digest('hex');
const context={$,document:{querySelectorAll:()=>[]},token:'account',activeApp:'app',appSelectionGeneration:1,workspaceSelectionGeneration:10,identityConnectionGeneration:1,naturalFirstGuide:null,naturalLogicPending:new Map(),naturalLogicView:null,
 clearNaturalLogic(){context.naturalLogicView=null;$('natural-logic-panel').hidden=true;},clearNaturalFirstGuide(){},resumeOrdinaryOutcome(){},naturalLogicButtons(){},naturalLogicKey:()=>'',paHash:()=>new Promise(resolve=>releaseHash=resolve),
};
context.view={token:'account',project:'project',app:'app',appGeneration:1,instance:{id:'iid',release_id:'release',release_fingerprint:'same-hash'},draft:{candidate:{namespace:'pa-natural-spec-app.v1',spec_recipe:{steps:[{}, {operator:'model.spec.requirements'},{operator:'model.spec.qualifiers',inputs:{}},{},{},{}]}}}};
context.engineering=context.view;
vm.createContext(context);vm.runInContext(current+'\n'+select+'\n'+open,context);
(async()=>{
 const pending=context.openNaturalLogic(context.view,{id:'release',fingerprint:'same-hash',snapshot:{}});
 assert.equal(typeof releaseHash,'function');assert.equal(context.naturalLogicView,null);
 context.selectWorkspace('projects');context.selectWorkspace('apps');
 assert.equal(context.workspaceSelectionGeneration,12);assert.equal(context.engineeringCurrent(context.view),true);
 releaseHash('same-hash');await pending;
 const result={classification:'NON_AUTHOR_EXACT_WIP_FUNCTION_CONTROLLED_CRYPTO_AWAIT_PROBE_NOT_ACTUAL_HTTP',source_function_sha256:sourceHash,status:context.naturalLogicView&&$('natural-logic-panel').hidden===false?'REPRODUCED_STALE_PAINT':'NOT_REPRODUCED',opening_workspace:10,resumed_workspace:context.workspaceSelectionGeneration,painted_view_workspace:context.naturalLogicView?.workspace,panel_visible:!$('natural-logic-panel').hidden,actual_product_function:'openNaturalLogic',actual_navigation_function:'selectWorkspace',workers:0,model_calls:0};
 fs.writeFileSync('/workspace/pa-page-root-cause-independent-20261018/wip-read-reuse-review/crypto-aba-result.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
 assert.equal(result.status,'REPRODUCED_STALE_PAINT');
})().catch(e=>{console.error(e);process.exitCode=1;});
