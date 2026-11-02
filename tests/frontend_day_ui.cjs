'use strict';
// Actual delivered template/controller + controlled DOM receipts. No model, PG or browser pixels.
const fs=require('fs'),assert=require('node:assert/strict'),{JSDOM,VirtualConsole}=require('jsdom');
const checks=[],errors=[],requests=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(fs.readFileSync('src/sim2act/web/index.html','utf8'),{url:'https://sim2act.invalid/#trial-key=kept',runScripts:'outside-only',virtualConsole:vc});
const w=dom.window,d=w.document;w.matchMedia=()=>({matches:false,addEventListener(){}});w.HTMLElement.prototype.scrollIntoView=function(){};
w.fetch=async(path,options={})=>{requests.push({path,method:options.method||'GET'});return {ok:false,status:503,json:async()=>({error:{code:'CONTROLLED_OFFLINE'}})};};
w.eval(fs.readFileSync('src/sim2act/web/app.js','utf8')+`\nwindow.frontendTest={setIdentity(){token='synthetic-ui';identityConnectionGeneration++;},clearFrontendRun,updateFrontendRun,resourceMaterialRow,applyFrontendMaterialFilter,frontendReadableDocument,frontendAttachReadable,openMaterialPicker,openLookup,selectWorkspace,refsSet(x){refs=x;},setGoalCard(c){activeGoalCard=c;},frontendPreviewGoalVersion,showRun,frontendRunCommand,frontendTextDiff,frontendPreviousAnswer,frontendCarryAnswer};`);
const api=w.frontendTest;const check=(condition,name)=>{assert(condition,name);checks.push(name);};const tick=()=>new Promise(r=>setTimeout(r,0));
(async()=>{
 await tick();const initial=requests.length;
 const input=d.getElementById('goal'),material=d.getElementById('run-materials');input.value='保留中文草稿';material.append(new w.Option('已读材料甲.md','r1',true,true),new w.Option('已读材料乙.csv','r2',false,false));
 api.setIdentity();d.getElementById('project-select').append(new w.Option('项目A','p1',true,true));
 for(const [id,value] of [['theme','dark'],['density','compact'],['theme','light'],['density','standard']]){const select=d.getElementById('frontend-pref-'+id);select.value=value;select.dispatchEvent(new w.Event('change'));}
 check(input.value==='保留中文草稿'&&material.selectedOptions[0].value==='r1','theme/density preserve original input and selected material');
 check(w.location.hash==='#trial-key=kept','appearance preserves original recovery address');
 const divider=d.getElementById('frontend-divider');divider.dispatchEvent(new w.KeyboardEvent('keydown',{key:'End',bubbles:true}));check(divider.getAttribute('aria-valuenow')==='420','keyboard separator reaches bounded maximum');divider.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Home',bubbles:true}));check(divider.getAttribute('aria-valuenow')==='280','keyboard separator reaches bounded minimum');
 check(d.querySelectorAll('[id]').length===new Set([...d.querySelectorAll('[id]')].map(n=>n.id)).size,'moved DOM subtrees keep globally unique identities');
 check(d.getElementById('task-workbench').firstElementChild===d.getElementById('task-list-panel'),'DOM reading order follows instruction then result');
 const res=d.getElementById('materials');res.replaceChildren(...['甲','乙'].map((name,i)=>api.resourceMaterialRow({id:'r'+(i+1),name:'材料'+name+'.md',format:'md',hash:'a'.repeat(64)})));
 const query=d.getElementById('frontend-material-query');query.value='不存在';api.applyFrontendMaterialFilter();check(!d.getElementById('frontend-material-empty').hidden&&[...res.children].every(n=>n.hidden),'query empty state keeps underlying rows and exposes clearing');
 [...d.querySelectorAll('[data-material-view]')].find(n=>n.dataset.materialView==='grid').click();check(query.value==='不存在'&&res.dataset.view==='grid','material grid preserves active query');
 query.value='';api.applyFrontendMaterialFilter();check([...res.children].every(n=>!n.hidden),'clearing query restores already-read material rows');
 api.selectWorkspace('resources');
 const menu=res.querySelector('.row-menu'),trigger=menu.querySelector('button');trigger.click();check(!menu.querySelector('[role=menu]').hidden&&d.activeElement.role==='menuitem','more command opens at adjacent row with focus');d.activeElement.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));check(menu.querySelector('[role=menu]').hidden&&d.activeElement===trigger,'Escape closes row menu and restores trigger');
 api.openMaterialPicker();let dialog=d.querySelector('dialog'),boxes=dialog.querySelectorAll('input[type=checkbox]');boxes[1].checked=true;dialog.querySelector('input:not([type=checkbox])').value='甲';dialog.querySelector('input:not([type=checkbox])').dispatchEvent(new w.Event('input'));check(boxes[1].checked,'material search retains hidden choices');[...dialog.querySelectorAll('button')].find(b=>b.textContent==='使用所选材料').click();check(material.selectedOptions.length===2&&!d.querySelector('dialog'),'explicit material apply changes draft only');
 api.openLookup(trigger);dialog=d.querySelector('dialog');check(dialog.textContent.includes('项目 · 项目A')&&dialog.textContent.includes('材料 · 材料甲'),'lookup uses only loaded project/material rows');dialog.querySelector('button').click();
 check(requests.length===initial,'all appearance, width, menu, lookup and material draft gestures send zero requests');
 const source='# 标题\n正文<img src=x onerror=bad()>\n\n| 名称 | 值 |\n| --- | --- |\n| 空 |  |\n| 零 | 0 |';const reader=api.frontendReadableDocument(source,'md');check(reader.querySelector('h2').textContent==='标题'&&reader.querySelectorAll('tbody tr').length===2,'text hierarchy and genuine table values render safely');check(!reader.querySelector('img')&&reader.textContent.includes('<img'),'untrusted HTML stays literal text without elements');check(reader.querySelectorAll('td')[1].textContent===''&&reader.querySelectorAll('td')[3].textContent==='0','empty cells remain distinct from zero');
 const csv=api.frontendReadableDocument('名称,说明\r\n甲,"一,二"\r\n乙,"分\n行"\r\n','csv');check(csv.querySelectorAll('tbody tr').length===2&&csv.textContent.includes('分\n行'),'CSV quoted commas/newlines preserve original content');
 api.selectWorkspace('projects');
 const result=d.getElementById('result');result.replaceChildren(d.createElement('div'));const answer=d.createElement('pre');answer.id='run-answer';answer.textContent=source;result.append(answer);api.frontendAttachReadable(answer,'md');let receipt={id:'run_synthetic',version:2,status:'RUNNING',result:{answer:source},events:[{type:'STARTED',message:'受控阶段'}]};api.updateFrontendRun(receipt,()=>true);
 d.querySelector('[data-inspection-open=calls]').click();check(d.getElementById('frontend-inspector-content').textContent.includes('受控阶段'),'inspection reads current run event rather than inventing progress');d.querySelector('[data-inspection-tab=versions]').click();check(d.getElementById('frontend-inspector-content').textContent.includes('2'),'version tab shows same run version');
 d.querySelector('#frontend-inspector button').click();check(d.getElementById('frontend-inspector').hidden,'nonmodal inspector closes without cancelling task');
 Object.defineProperty(w.navigator,'clipboard',{configurable:true,value:{writeText:async value=>{assert.equal(value,source);}}});const copy=d.getElementById('frontend-copy-result');await tick();copy.click();await tick();check(copy.textContent==='已复制','copy success appears only after actual clipboard promise resolves');
 Object.defineProperty(w.navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw Error('denied');}}});copy.click();await tick();check(copy.textContent==='复制失败'&&d.getElementById('frontend-copy-status').textContent.includes('未写入'),'clipboard rejection never reports success');
 let release;Object.defineProperty(w.navigator,'clipboard',{configurable:true,value:{writeText:()=>new Promise(r=>release=r)}});copy.click();api.clearFrontendRun();release();await tick();check(copy.textContent==='复制'&&!d.getElementById('frontend-copy-status').textContent,'late copy response cannot report success for cleared scope');
 receipt={...receipt,status:'UNKNOWN'};result.replaceChildren(d.createElement('div'));api.updateFrontendRun(receipt,()=>true);check(result.firstElementChild.dataset.running==='false','unknown state stops running animation');

 // Historical preview and local recovery preserve persisted version identity.
 const content={title:'当前名称',goal:'当前目标',known:[],assumptions:[],unresolved:[],constraints:[],acceptance_checks:[],resource_refs:['r1']};
 const historical={version:1,snapshot:{content:{...content,title:'历史名称',goal:'历史目标'},resource_snapshots:[]}};
 const card={id:'goal_synthetic',version:2,content};api.setGoalCard(card);d.getElementById('goal-card-resources').append(new w.Option('已读取材料','r1')); 
 api.frontendPreviewGoalVersion(card,historical,()=>true,trigger);
 const history=d.getElementById('goal-card-history-detail');check(history.textContent.includes('历史预览')&&input.value==='保留中文草稿','history preview is read-only and preserves current editor');
 const restore=[...history.querySelectorAll('button')].find(b=>b.textContent==='恢复到编辑草稿');check(restore.disabled,'history recovery requires a separate unchecked confirmation');
 const ack=history.querySelector('input[type=checkbox]');ack.checked=true;ack.dispatchEvent(new w.Event('change'));restore.click();check(d.getElementById('goal-card-goal').value==='历史目标'&&d.getElementById('goal-card-status').textContent.includes('尚未保存'),'confirmed recovery fills an unsaved draft without publishing or starting work');
 check(api.frontendTextDiff('核对时间安排','核对地点安排').querySelector('ins').textContent.includes('地点'),'word difference marks changed content in local detail only');
 api.selectWorkspace('apps');w.engineering={run:{id:'internal_synthetic',version:3,status:'SUCCEEDED',result_version:1},project:'p1',runGeneration:1,instanceGeneration:1,draft:{candidate:{manifest:{data_bindings:[{resource_ref:'r1'}]}}}};w.engineeringCurrent=v=>v===w.engineering;
 const appInspect=d.querySelector('.engineering-toolbar-actions button[aria-controls="frontend-inspector"]');check(!!appInspect,'application exposes shared inspection commands');appInspect.click();check(d.getElementById('frontend-inspector').parentElement.id==='apps'&&d.querySelectorAll('#frontend-inspector').length===1&&d.getElementById('frontend-inspector-content').textContent.includes('r1'),'application inspector reuses one node with its current actual bindings');
 w.engineering.runGeneration++;d.getElementById('internal-run-detail').textContent='new scoped detail';await tick();check(d.getElementById('frontend-inspector').hidden&&!d.getElementById('frontend-inspector-content').textContent,'changing application run clears stale inspection content');
 api.selectWorkspace('projects');
 check(requests.length===initial,'reading, inspection and copying send zero new requests');check(!errors.length,'delivered controller has no uncaught DOM errors');


 receipt={id:'run_retained',version:4,status:'RUNNING',result:{answer:'# 已有成果\n保留部分内容'},events:[]};api.updateFrontendRun(receipt,()=>true);
 await api.showRun('run_retained',false);check(d.getElementById('frontend-previous-outcome').textContent.includes('保留部分内容')&&d.getElementById('run-read-failure').textContent.includes('无法判断'),'transient same-run read failure retains last readable partial result with unknown status');
 w.fetch=async(path,options={})=>{requests.push({path,method:options.method||'GET'});return {ok:false,status:403,json:async()=>({error:{code:'PERMISSION_DENIED'}})};};
 await api.showRun('run_retained',false);check(!d.getElementById('frontend-previous-outcome')&&!d.getElementById('frontend-inspector-content').textContent,'permission denial clears retained readable content and inspector');
 w.fetch=async(path,options={})=>{requests.push({path,method:options.method||'GET'});return {ok:false,status:503,json:async()=>({error:{code:'CONTROLLED_OFFLINE'}})};};
 const commandHost=d.getElementById('commands');commandHost.replaceChildren();const cancel=api.frontendRunCommand('cancel',{id:'run_command_fixture',version:3},()=>true);commandHost.append(cancel);cancel.click();cancel.click();await tick();await tick();
 check(requests.length===initial+3&&requests.at(-1).method==='POST'&&cancel.disabled,'double cancel sends one explicit version-bound command');
 check(cancel.textContent==='结果待核实'&&commandHost.textContent.includes('不会自动重发')&&commandHost.textContent.includes('查询当前任务状态'),'uncertain cancel keeps outputs and offers only explicit state read');
 console.log(JSON.stringify({status:'PASS',classification:'CONTROLLED_DOM_INTERACTION_NOT_BROWSER_PIXELS',checks,readonly_gesture_requests:0,controlled_failure_reads:2,explicit_controlled_command_requests:1,model_requests:0,pg_operations:0,errors},null,2));dom.window.close();
})().catch(e=>{console.error(e.stack);dom.window.close();process.exitCode=1;});
