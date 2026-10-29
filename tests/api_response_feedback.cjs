'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const {JSDOM,VirtualConsole}=require('jsdom');
const errors=[],requests=[],checks=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(fs.readFileSync('src/sim2act/web/index.html','utf8'),{runScripts:'dangerously',virtualConsole:vc});
const w=dom.window;w.setInterval=()=>0;w.fetch=()=>{throw Error('Unexpected network');};
const script=w.document.createElement('script');script.textContent=fs.readFileSync(process.argv[2]||'src/sim2act/web/app.js','utf8');w.document.body.append(script);
const protocolMode=process.argv[4]==='protocol';
assert(!(protocolMode&&process.argv[3]),'Protocol mode is synthetic-only; no HTTP combination is supported');
if(protocolMode){const protocol=w.document.createElement('script');protocol.textContent=fs.readFileSync('src/sim2act/web/protocol.js','utf8');w.document.body.append(protocol);}
const request=(...args)=>protocolMode?w.protocolRequest({token:'synthetic-response-actor'},...args):w.api(...args);
const check=(v,text)=>{assert(v,text);checks.push(text);};
const response=(status,data,broken=false)=>({status,ok:status>=200&&status<300,headers:{get:()=>null},json:async()=>{if(broken)throw new SyntaxError('PRIVATE_HTML_BODY');return data;}});
(async()=>{try{
 w.eval("token='synthetic-response-actor'");
 let reply=response(502,null,true);w.fetch=async(path,options)=>{requests.push({path,method:options.method,body:options.body});return reply;};
 for(const method of ['GET','POST']){
  let error;try{await request('/synthetic-fault',method,method==='POST'?{request_key:'fixed-original-key',input:{term:'sample'}}:undefined);}catch(e){error=e;}
  check(error?.code==='API_RESPONSE_UNCONFIRMED',method+' malformed response is explicitly unconfirmed');
  check(error.transportStatus===502&&error.httpStatus===undefined&&!error.submissionRejection,method+' does not pretend malformed body is a confirmed business rejection');
  check(!error.message.includes('PRIVATE_HTML_BODY')&&(method==='GET'?error.message.includes('只读'):error.message.includes('原请求键')),method+' recovery feedback avoids body leakage and explains next action');
 }
 check(requests.length===2&&requests[1].body===JSON.stringify({request_key:'fixed-original-key',input:{term:'sample'}}),'no retry, added field, or replacement key');
 reply=response(403,{error:{code:'PERMISSION_DENIED',message:'denied',submission_rejection:'CONFIRMED'}});
 await assert.rejects(request('/synthetic-denial'),e=>e.message==='PERMISSION_DENIED'&&e.httpStatus===403&&e.detail==='denied'&&(protocolMode?e.submissionRejection===undefined:e.submissionRejection==='CONFIRMED'));check(true,'existing structured rejection semantics unchanged');
 if(!protocolMode){
  const reason='Configured Intern credential missing: set the existing SIM2ACT_INTERN_TOKEN or INTERN_API_TOKEN';
  reply=response(403,{error:{code:'PERMISSION_DENIED',message:reason}});
  await w.eval('safe')(async()=>{await w.api('/synthetic-configuration-denial');})();
  check(w.document.getElementById('error').textContent==='PERMISSION_DENIED：'+reason,'visible feedback includes the actual configuration reason without changing machine error semantics');
  reply=response(409,{error:{code:'VERSION_CONFLICT',message:'<img src=x onerror="throw 1">'}});
  await w.eval('safe')(async()=>{await w.api('/synthetic-text-denial');})();
  check(w.document.getElementById('error').textContent==='VERSION_CONFLICT：<img src=x onerror="throw 1">'&&!w.document.getElementById('error').querySelector('img'),'server reason is text only, never HTML');
  reply=response(403,{error:{code:'PERMISSION_DENIED',message:{private:'not a public reason'}}});
  await w.eval('safe')(async()=>{await w.api('/synthetic-invalid-reason');})();
  check(w.document.getElementById('error').textContent==='PERMISSION_DENIED','nonstring reason is not serialized into visible feedback');
 }
 reply=response(200,{natural_deadline:123});reply.headers.get=()=> '42';const data=await request('/synthetic-ok');
 check(data.natural_deadline===123&&(protocolMode?data.naturalServerTime===undefined:data.naturalServerTime===42),'valid result and original server clock metadata unchanged');
 if(process.argv[3]){
  const info=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));const actual=[];
  let catalogReply;w.fetch=async(path,options)=>{actual.push({path,method:options.method});const response=await fetch(info.base+path,options);if(path==='/api/capabilities')catalogReply=await response.clone().json();return response;};
  const health=await request('/health');check(health&&typeof health==='object','actual local FastAPI health JSON consumed by real controller');
  const projects=await request('/api/projects');check(projects.length===1&&projects[0].id===info.project&&projects[0].name==='API feedback fixture','actual authenticated project directory returns the seeded project');
  if(info.catalog){
   w.document.getElementById('login').hidden=true;
   await w.refreshResourceCatalog();
   const catalog=catalogReply;
   check(w.document.getElementById('connection-summary').textContent.includes(catalog.connection.model)&&w.document.getElementById('connection-summary').textContent.includes(catalog.connection.status),'actual authenticated catalog populates model and exact technical status');
   check(JSON.stringify([...w.document.querySelectorAll('#capability-summary .catalog-tools code')].map(n=>n.textContent))===JSON.stringify(catalog.tools),'actual registered tool IDs render without filtering or invented tools');
   const readCount=actual.length;await w.document.getElementById('resource-catalog-refresh').onclick();
   check(actual.length===readCount+1&&actual.at(-1).path==='/api/capabilities'&&!w.document.getElementById('resource-catalog-refresh').disabled,'actual read-only refresh control sends one new GET and releases its busy state');
  }
  w.eval("token='synthetic-invalid-actor'");
  await assert.rejects(request('/api/projects'),e=>e.httpStatus===403&&e.message==='PERMISSION_DENIED');check(true,'actual local backend authorization rejection preserved');
  check(actual.length===(info.catalog?5:3)&&actual.every(x=>x.method==='GET'),'actual backend checks remain read-only GETs');
 }
 check(!errors.length,'real template/controller has no jsdom script error');
 console.log(JSON.stringify({status:'PASS',controller:protocolMode?'protocolRequest':'api',checks,synthetic_requests:requests,actual_http:!!process.argv[3],native_browser:false,models:0},null,2));
}finally{w.close();}})().catch(e=>{console.error(e.stack);process.exitCode=1;});
