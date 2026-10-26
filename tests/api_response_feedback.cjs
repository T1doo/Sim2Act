'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const {JSDOM,VirtualConsole}=require('jsdom');
const errors=[],requests=[],checks=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(fs.readFileSync('src/sim2act/web/index.html','utf8'),{runScripts:'dangerously',virtualConsole:vc});
const w=dom.window;w.setInterval=()=>0;w.fetch=()=>{throw Error('Unexpected network');};
const script=w.document.createElement('script');script.textContent=fs.readFileSync(process.argv[2]||'src/sim2act/web/app.js','utf8');w.document.body.append(script);
const check=(v,text)=>{assert(v,text);checks.push(text);};
const response=(status,data,broken=false)=>({status,ok:status>=200&&status<300,headers:{get:()=>null},json:async()=>{if(broken)throw new SyntaxError('PRIVATE_HTML_BODY');return data;}});
(async()=>{try{
 w.eval("token='synthetic-response-actor'");
 let reply=response(502,null,true);w.fetch=async(path,options)=>{requests.push({path,method:options.method,body:options.body});return reply;};
 for(const method of ['GET','POST']){
  let error;try{await w.api('/synthetic-fault',method,method==='POST'?{request_key:'fixed-original-key',input:{term:'sample'}}:undefined);}catch(e){error=e;}
  check(error?.code==='API_RESPONSE_UNCONFIRMED',method+' malformed response is explicitly unconfirmed');
  check(error.transportStatus===502&&error.httpStatus===undefined&&!error.submissionRejection,method+' does not pretend malformed body is a confirmed business rejection');
  check(!error.message.includes('PRIVATE_HTML_BODY')&&(method==='GET'?error.message.includes('只读'):error.message.includes('原请求键')),method+' recovery feedback avoids body leakage and explains next action');
 }
 check(requests.length===2&&requests[1].body===JSON.stringify({request_key:'fixed-original-key',input:{term:'sample'}}),'no retry, added field, or replacement key');
 reply=response(403,{error:{code:'PERMISSION_DENIED',message:'denied',submission_rejection:'CONFIRMED'}});
 await assert.rejects(w.api('/synthetic-denial'),e=>e.message==='PERMISSION_DENIED'&&e.httpStatus===403&&e.detail==='denied'&&e.submissionRejection==='CONFIRMED');check(true,'existing structured rejection semantics unchanged');
 reply=response(200,{natural_deadline:123});reply.headers.get=()=> '42';const data=await w.api('/synthetic-ok');
 check(data.natural_deadline===123&&data.naturalServerTime===42,'valid result and original server clock metadata unchanged');
 if(process.argv[3]){
  const info=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));const actual=[];
  w.fetch=(path,options)=>{actual.push({path,method:options.method});return fetch(info.base+path,options);};
  const health=await w.api('/health');check(health&&typeof health==='object','actual local FastAPI health JSON consumed by real controller');
  const projects=await w.api('/api/projects');check(projects.length===1&&projects[0].id===info.project&&projects[0].name==='API feedback fixture','actual authenticated project directory returns the seeded project');
  w.eval("token='synthetic-invalid-actor'");
  await assert.rejects(w.api('/api/projects'),e=>e.httpStatus===403&&e.message==='PERMISSION_DENIED');check(true,'actual local backend authorization rejection preserved');
  check(actual.length===3&&actual.every(x=>x.method==='GET'),'actual backend checks are three read-only GETs');
 }
 check(!errors.length,'real template/controller has no jsdom script error');
 console.log(JSON.stringify({status:'PASS',checks,synthetic_requests:requests,actual_http:!!process.argv[3],native_browser:false,models:0},null,2));
}finally{w.close();}})().catch(e=>{console.error(e.stack);process.exitCode=1;});
