'use strict';
// Delivered controller -> actual ASGI/storage. No worker or provider execution.
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),pending=new Map(),requests=[],checks=[];let serial=0;
readline.createInterface({input:process.stdin}).on('line',line=>{const answer=JSON.parse(line);pending.get(answer.id)(answer);pending.delete(answer.id);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+'\n');});
const check=(ok,name)=>{assert(ok,name);checks.push(name);};
(async()=>{
 const html=await rpc({method:'GET',path:'/'}),js=await rpc({method:'GET',path:'/app.js'});assert.equal(html.status,200);assert.equal(js.status,200);
 const dom=new JSDOM(html.text,{url:'http://testserver/',runScripts:'outside-only'}),w=dom.window,d=w.document;let lose=true;
 try{
  w.matchMedia=()=>({matches:false,addEventListener(){}});w.setInterval=()=>0;w.TextEncoder=TextEncoder;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.HTMLElement.prototype.scrollIntoView=function(){};
  w.fetch=async(path,options={})=>{const request={path,method:options.method||'GET',headers:options.headers,body:options.body&&JSON.parse(options.body)};requests.push(request);const answer=await rpc(request);request.status=answer.status;request.response=JSON.parse(answer.text);if(lose&&request.method==='POST'&&path.endsWith('/runs')){assert.equal(answer.status,202);lose=false;throw TypeError('Synthetic reply loss after durable API acceptance');}return new Response(answer.text,{status:answer.status,headers:{'Content-Type':answer.content_type||'application/json'}});};
  w.eval(js.text+`\nwindow.fragmentAPI={start(){token='synthetic-test-A';identityConnectionGeneration++;},api,updateOrdinaryRunMaterials,previewResource,resourceDownloadContext,submitOrdinaryRun,entry:runSubmissionEntry};`);
  await new Promise(r=>setTimeout(r,0));const api=w.fragmentAPI;api.start();d.getElementById('project-select').append(new w.Option('合成项目',info.project,true,true));
  const materials=await api.api('/api/projects/'+info.project+'/resources');api.updateOrdinaryRunMaterials(materials);const material=materials.find(m=>m.id===info.resource);await api.previewResource(material,api.resourceDownloadContext());
  const pre=d.getElementById('resource-preview'),range=d.createRange();range.setStart(pre.firstChild,1);range.setEnd(pre.firstChild,5);w.getSelection().addRange(range);d.querySelector('#frontend-fragment-source button').click();
  const posts=()=>requests.filter(r=>r.method==='POST');check(posts().length===0,'actual authorized source preview and fragment binding create no Run');d.getElementById('goal').value='只解释这段原文';await api.submitOrdinaryRun();
  check(posts().length===1&&api.entry().state==='unknown','durable API acceptance with lost reply remains UNKNOWN');const original=posts()[0].body;
  check(original.resource_refs.length===1&&original.resource_refs[0]===info.resource,'actual Run body keeps exact original source ID');
  check((await rpc({command:'verify',body:original})).status===200,'actual frozen contract binds exact source hash, range and text');
  await d.getElementById('run-submit-recover').onclick(new w.Event('click'));
  check(posts().length===2&&JSON.stringify(posts()[1].body)===JSON.stringify(original)&&posts()[1].response.run_id===posts()[0].response.run_id,'explicit original-key recovery returns same durable Run');
  check((await rpc({command:'verify',body:original})).status===200,'recovery leaves one queued Run and no worker attempts');
  fs.writeFileSync(info.output,JSON.stringify({status:'PASS',scope:'DELIVERED_UI_ACTUAL_ASGI_SYNTHETIC_SQLITE_NO_WORKER',checks,requests:requests.map(r=>({path:r.path,method:r.method,status:r.status})),live_model_requests:0,worker_executions:0,pg_operations:0},null,2));
 }finally{dom.window.close();}
 process.stdout.write(JSON.stringify({done:true})+'\n');
})().catch(error=>{console.error(error.stack);process.exitCode=1;process.stdout.write(JSON.stringify({done:true})+'\n');});
