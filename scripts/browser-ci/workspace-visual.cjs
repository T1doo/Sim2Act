'use strict';
// This fixture is presentation-only. It neither creates projects nor accepts commands.
const assert=require('node:assert/strict');
const product='c797f9482b52cf1f9c70f3aa39ff4617c7d94e01';
const hashes={"index.html":"475393d089cd4de947b08f7c79bb2793efb1322e3dde2de9e6a49edefee8c2b3","app.css":"2ee9b73ddfc5b9bede4bf09fc4c6643ef5c3316b4a7951ad04e1477fa1d3df09","app.js":"13f31733f4001ca357c9e55625f8a9d352dbd4cfdb6c96c2817da152b38e3356","natural-goal.js":"7b15942eecfc256dea39cb158fbdac0b923faad7f4530b8d71d3479f694f8a03"};
let denyResources=false,denyDirectory=null,hold=null;
const second='synthetic_directory_project_b';
function items(info,family,project){const label=project===info.project?'A':'B';return family==='goal'?{items:[{id:`synthetic_goal_${label}`,title:`${label} 项目 · 合成目标目录`,version:1}]}:{items:[{id:`synthetic_app_${label}`,project_id:project,name:`${label} 项目 · 合成应用草案`,use_family:'CSV',csv_instance_candidate:false}]};}
async function responseFor(info,method,pathname){
 assert.equal(method,'GET');
 if(pathname==='/api/projects')return {body:[{id:info.project,name:'A · 合成目录核查'},{id:second,name:'B · 合成目录核查'}]};
 const match=pathname.match(/^\/api\/projects\/([^/]+)\/(.+)$/),project=match?.[1];
 if(pathname==='/api/apps'||(match&&[info.project,second].includes(project)&&match[2]==='goal-cards')){
  const family=pathname==='/api/apps'?'app':'goal';
  const body=family==='app'?{items:[...items(info,'app',info.project).items,...items(info,'app',second).items]}:items(info,'goal',project);
  if(hold?.family===family){const pending=hold;hold=null;pending.reached();await pending.gate;return {body,held:pending};}
  if(denyDirectory===family)return {status:403,body:{error:{code:'CONTROLLED_SYNTHETIC_DIRECTORY_READ_FAILURE'}}};
  return {body};
 }
 if(match&&[info.project,second].includes(project)){
  if(match[2]==='resources')return denyResources?{status:403,body:{error:{code:'CONTROLLED_SYNTHETIC_MATERIAL_READ_FAILURE'}}}:{body:[]};
  if(['runs','grants'].includes(match[2]))return {body:[]};
  if(['protocol/contracts','conditional-apps'].includes(match[2]))return {body:{items:[]}};
 }
 return undefined;
}
async function runWorkspaceVisual({page,info,result,check,shot,until,wait}){
 for(const [name,hash] of Object.entries(hashes))assert.equal(info.visual_source.asset_lf_sha256['src/sim2act/web/'+name],hash);
 result.visual={product,execution:info.visual_source.commit,capture_revision:'directory-recovery-four-frame-v1',classification:'SYNTHETIC_PRESENTATION_ONLY_NO_PERSISTED_DIRECTORY_FACT'};
 const snapshot=()=>page.evaluate(()=>({goal:activeGoalCard,app:activeApp,run:activeRun,trial:[...trialEntries],goalKeys:[...goalRunRequests]}));
 // Each family gets a real project-select event, controlled early failure,
 // current-directory failure, actual retry click and late A response delivery.
 result.directoryRecovery={families:[],status:'NOT_PROVEN'};
 for(const family of ['goal','app']){
  const id=family==='goal'?'goal-card-list':'app-list';
  await page.locator(`#workspace-nav [data-tab="${family==='goal'?'projects':'apps'}"]`).click();
  denyResources=false;denyDirectory=null;
  await page.selectOption('#project-select',info.project);
  await page.evaluate(async()=>{await refresh();});
  await until(({id})=>document.getElementById(id).textContent.includes('A 项目'),{id});
  let release,reached,finished;const arrived=new Promise(r=>reached=r),gate=new Promise(r=>release=r),done=new Promise(r=>finished=r);hold={family,gate,reached,finished,id:`directory-${family}-A`};
  await page.evaluate(f=>{window.directoryPending=(f==='goal'?refreshGoalCards(document.getElementById('project-select').value):refreshApps()).catch(e=>{throw e;});},family);
  try{
   await wait(arrived);denyResources=true;
   await page.selectOption('#project-select',second);
   await until(({id})=>document.getElementById('materials').textContent.includes('当前项目材料列表读取失败')&&document.getElementById(id).textContent.includes('未确认'),{id});
   check(`${family}: switch invalidates old catalog even before directory GET`,!(await page.locator('#'+id).textContent()).includes('A 项目'));
   denyDirectory=family;
   await page.evaluate(async f=>{try{if(f==='goal')await refreshGoalCards(document.getElementById('project-select').value);else await refreshApps();}catch(e){window.directoryControlledError=e.message;}},family);
   const retry=page.locator('#'+id).getByRole('button',{name:family==='goal'?'重新读取目标卡目录（只读）':'重新读取应用草案目录（只读）',exact:true});
   await retry.waitFor();const before=await snapshot();
   await page.setViewportSize({width:390,height:844});await retry.scrollIntoViewIfNeeded();await page.evaluate(()=>document.fonts.ready);await page.waitForTimeout(220);
   await shot(`${family}-directory-failed-390.png`);
   denyDirectory=null;await retry.click();
   await until(({id})=>document.getElementById(id).textContent.includes('B 项目'),{id});
   assert.deepEqual(await snapshot(),before);
   release();await wait(done);await page.evaluate(()=>window.directoryPending);
   await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
   check(`${family}: late A response cannot restore A and retry changes no task intent`,(await page.locator('#'+id).textContent()).includes('B 项目')&&!(await page.locator('#'+id).textContent()).includes('A 项目'));
   await page.setViewportSize({width:1366,height:900});await page.locator('#'+id).scrollIntoViewIfNeeded();await page.waitForTimeout(220);
   await shot(`${family}-directory-recovered-1366.png`);
   result.directoryRecovery.families.push({family,selected_project:second,unchanged_task_intents:true,late_response_ignored:true,held_request_finished:true});
  }finally{release();hold=null;}
 }
 check('four frames and GET-only closed window',result.screenshots===4&&result.counts.business_post===0&&result.counts.blocked===0&&!result.pageErrors.length);
 result.directoryRecovery.status='PROVED';result.receipts=[];result.status='PASS';
}
module.exports={responseFor,runWorkspaceVisual};
