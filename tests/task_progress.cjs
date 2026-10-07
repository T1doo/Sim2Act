'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const {JSDOM}=require('jsdom');
const fixture=JSON.parse(fs.readFileSync(process.argv[2]));
const dom=new JSDOM(fs.readFileSync('src/sim2act/web/index.html','utf8'),{runScripts:'dangerously'});
dom.window.setInterval=()=>0;
const script=dom.window.document.createElement('script');script.textContent=fs.readFileSync('src/sim2act/web/app.js','utf8');dom.window.document.body.append(script);
const render=(r,attempts=[])=>{dom.window.document.getElementById('result').replaceChildren();dom.window.renderOrdinaryProgress(r,attempts);return dom.window.document.getElementById('run-progress');};
const checks=[];const check=(ok,name)=>{assert(ok,name);checks.push(name);};
let section=render(fixture);
check(section.textContent.includes('任务已持久接受')&&section.textContent.includes('后台已领取任务')&&section.textContent.includes('工具效果已核验'),'actual normal Mock ledger steps visible');
check(section.textContent.includes('1 项已核验')&&section.textContent.includes('NOT_RUN'),'actual verified effects do not sign semantic acceptance');
check(section.textContent.includes('不表示已发送或成功'),'reservation never presented as successful send');
for(const [code,text] of [['GRANT_REVOKED','授权已撤回'],['RESOURCE_UNAVAILABLE','资源当前不可用'],['RATE_LIMITED','额度或速率受限'],['OUTCOME_UNKNOWN','请求或工具效果结果未知']]){
 section=render({...fixture,status:'WAITING_RESOURCE',error:{code}});check(section.textContent.includes(text),code+' has bounded concrete waiting reason');
}
section=render({...fixture,status:'WAITING_RESOURCE',error:null},[{attempt_id:'synthetic',status:'STARTED'}]);check(section.textContent.includes('模型尝试结果未知')&&section.textContent.includes('不会自动重发'),'unknown attempt stays uncertain and explicit');
section=render({...fixture,status:'RECONCILING',error:null});check(section.textContent.includes('具体原因尚未记录')&&!section.textContent.includes('模型尝试结果未知'),'unrecorded reconcile reason not invented');
section=render({...fixture,status:'FAILED',known_effects:[{status:'EFFECT_KNOWN_INVALID'},null,{status:'UNKNOWN'}]});check(section.textContent.includes('0 项已核验；1 项效果已知但核验失败'),'known invalid effect never counted verified');
const attack='<img src=x onerror=alert(1)>';
section=render({...fixture,events:[null,{kind:attack,created_at:1},{kind:'STATE',created_at:1e100,data:{status:attack,private_reason:attack}},{kind:'TOOL_VERIFIED',created_at:1,data:{private_reason:attack}}]});
check(section.querySelectorAll('img').length===0&&!section.textContent.includes(attack),'unknown type and private payload never rendered');
check(section.textContent.includes('时间未知'),'invalid timestamp not invented');
section=render({...fixture,events:Array.from({length:25},(_,i)=>({kind:'ACCEPTED',created_at:1700000000+i}))});check(section.querySelectorAll('li').length===20,'recent ledger steps bounded at twenty');
section=render({...fixture,events:[],known_effects:[]});check(section.textContent.includes('尚无可展示')&&!section.querySelector('li'),'legacy missing steps stay absent');
let outbound=0;dom.window.fetch=()=>{outbound++;throw Error('summary must not fetch')};render({...fixture,status:'WAITING_RESOURCE',error:{code:'OUTCOME_UNKNOWN'}});check(outbound===0,'summary creates no fetch or execution');
fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',checks,real_model_requests:0},null,2));
dom.window.close();
