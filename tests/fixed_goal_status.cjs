'use strict';
// Actual existing fixed evaluator result and served page; JSDOM, not native browser.
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),requests=[],checks=[],assets=[],observations=[],pending=new Map();let serial=0,dom,w,$;
readline.createInterface({input:process.stdin}).on('line',line=>{const r=JSON.parse(line),resolve=pending.get(r.id);assert(resolve);pending.delete(r.id);resolve(r);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+'\n');});
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
async function action(id){const el=typeof id==='string'?$(id):id;assert(el?.isConnected&&!el.hidden&&!el.disabled);await el.onclick(new w.Event('click',{cancelable:true}));}
(async()=>{let status='FAIL',error;try{
 const load=async path=>{const r=await rpc({method:'GET',path});assert.equal(r.status,200);assets.push({path,sha256:crypto.createHash('sha256').update(r.text).digest('hex')});return r.text;};
 dom=new JSDOM(await load('/'),{url:'http://testserver/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);w.setInterval=()=>0;w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});
 w.fetch=async(path,options={})=>{const request={method:options.method||'GET',path};assert.equal(request.method,'GET');requests.push(request);const r=await rpc({...request,headers:options.headers});request.status=r.status;request.response=JSON.parse(r.text);return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});};
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 for(const tag of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(tag.getAttribute('src'));w.document.body.append(node);}
 $('token').value='synthetic-test-A';await action('connect');const row=[...$('runs').children].find(node=>node.textContent.includes(info.run.slice(0,16)));assert(row);await action(row.querySelector('button'));
 const actual=JSON.parse($('raw-result').textContent),progress=$('run-progress').textContent;observations.push({actual_run:actual,progress,canvas:$('result').textContent});
 check(actual.id===info.run&&actual.status==='SUCCEEDED'&&actual.result.goal_acceptance==='PASS_FIXED_CONTRACT','real existing evaluator has accepted this exact prospective fixed goal');
 check(progress.includes('固定合成目标契约 PASS')&&!progress.includes('当前普通任务尚未实现'),'progress states actual fixed-contract PASS without claiming no evaluator ran');
 check(progress.includes('通用语义 NOT_RUN')&&progress.includes('人工 PENDING')&&progress.includes('正式发布关闭'),'fixed goal success remains separate from general semantics, owner and publication');
 check($('natural-goal-plan').textContent.includes('限定整体 PASS')&&!$('result').textContent.includes('完整目标验收尚未执行'),'canvas and exact existing plan agree about scoped fixed acceptance');
 check(!w.document.querySelector('#run-artifacts'),'read-only preview/sum receipt is not presented as a saved artifact');
 check(requests.every(r=>r.method==='GET'),'status viewing only reads actual APIs, never submits a new goal or provider request');
 assert.equal((await rpc({command:'verify-readonly'})).status,200);status='PASS';
}catch(e){error=e.stack;process.stderr.write(error+'\n');process.exitCode=1;}finally{dom?.window.close();fs.writeFileSync(info.output,JSON.stringify({status,error,kind:info.kind,checks,requests,assets,observations,scope:'Actual existing prospective fixed synthetic evaluator + full served JS/authenticated ASGI/SQLite. One MockTransport provider request, no real model. General semantic NOT_RUN, owner PENDING; page read-only.'},null,2)+'\n');process.stdout.write(JSON.stringify({done:true})+'\n');}})();
