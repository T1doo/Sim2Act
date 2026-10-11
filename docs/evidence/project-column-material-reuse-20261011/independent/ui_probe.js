'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),readline=require('node:readline'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),checks=[],failures=[],requests=[],loaded={},pending=new Map();let serial=0,dom,w,$,forged=null;
readline.createInterface({input:process.stdin}).on('line',line=>{const r=JSON.parse(line),p=pending.get(r.id);pending.delete(r.id);p(r);});
const rpc=q=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...q})+'\n');});
const check=(v,name)=>{if(v)checks.push(name);else failures.push({name,error:'assertion false'});};
const wait=async f=>{const deadline=Date.now()+30000;while(Date.now()<deadline){if(f())return;await new Promise(r=>setTimeout(r,5));}throw Error('bounded offline wait');};
async function setup(){if(dom)dom.window.close();forged=null;dom=new JSDOM((await rpc({path:'/',method:'GET'})).text,{url:'http://offline.test/',runScripts:'dangerously'});w=dom.window;$=id=>w.document.getElementById(id);w.TextEncoder=TextEncoder;Object.defineProperty(w.crypto,'subtle',{value:crypto.webcrypto.subtle});w.setInterval=()=>0;
 w.fetch=async(url,opt={})=>{const q={path:url,method:opt.method||'GET',body:opt.body&&JSON.parse(opt.body),headers:opt.headers};requests.push(q);const r=await rpc(q);
  if(forged&&q.method==='GET'&&url==='/api/internal/instances/'+info.instance){const data=JSON.parse(r.text);data.release_fingerprint=forged.fingerprint;r.text=JSON.stringify(data);}
  if(forged&&q.method==='GET'&&url==='/api/internal/releases/'+info.release.id)r.text=JSON.stringify(forged);
  return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
 };
 for(const node of [...w.document.querySelectorAll('script[src]')]){const name=node.getAttribute('src').slice(1),code=fs.readFileSync(path.join(info.web,name),'utf8');loaded[name]=crypto.createHash('sha256').update(code).digest('hex');const s=w.document.createElement('script');s.textContent=code;w.document.body.append(s);}
 $('token').value='synthetic-test-A';$('connect').click();await wait(()=>$('login').hidden&&$('project-select').value===info.project);await w.showApp(info.app);await w.readDeliveryGraph();await w.dagReuseHistory();$('dag-reuse-instance').value=info.instance;
}
(async()=>{try{
 await setup();await w.dagReuseRead();check($('dag-reuse-column').value==='quantity','cold actual adapted release selects quantity despite first amount');check(requests.some(q=>q.path.includes('/csv-dag/material-plan-'))&&requests.some(q=>q.path==='/api/csv-dag/runs/'+info.release.snapshot.execution_source.run_id),'cold default verified through real original target plan and successful worker proof');
 for(const mode of ['missing','null','wrong','missing-and-plan-key','wrong-and-plan-key','missing-and-existing-key','wrong-and-existing-key']){
  await setup();const n=requests.filter(q=>q.method==='POST').length;forged=JSON.parse(JSON.stringify(info.release));const e=forged.snapshot.execution_source;
  if(mode.startsWith('missing'))delete e.default_column;else e.default_column=mode==='null'?null:'amount';
  if(mode.endsWith('plan-key'))e.plan_key='ind-ordinary-looking-key';if(mode.endsWith('existing-key'))e.plan_key='ind-real-ordinary-plan';forged.fingerprint=await w.deliveryDigest(forged.snapshot);
  let error=null;try{await w.dagReuseRead();}catch(x){error=x.message;}
  check(error!==null,'coherent malicious HTTP200 '+mode+' default is rejected');check(requests.filter(q=>q.method==='POST').length===n,'malicious '+mode+' cold recovery uses reads only');
 }
 const result={status:failures.length?'FAIL':'PASS',checks,failures,requests,loaded_source_sha256:loaded};fs.writeFileSync(info.output,JSON.stringify(result,null,2));dom.window.close();process.stdout.write(JSON.stringify({done:true})+'\n');process.exit(failures.length?1:0);
 }catch(error){fs.writeFileSync(info.output,JSON.stringify({status:'FAIL',checks,failures:[...failures,{error:error.stack}],requests,loaded_source_sha256:loaded},null,2));if(dom)dom.window.close();process.stderr.write(error.stack+'\n');process.exit(1);}})();
