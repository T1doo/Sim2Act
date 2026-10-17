'use strict';
// Deterministic slow synthesized API/scheduler; not HTTP, PG, or native evidence.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const root=process.argv[2],source=process.argv[3],web='/workspace/Sim2Act/src/sim2act/web',checks=[],requestTimeline=[],phaseTimeline=[];const origin=process.hrtime.bigint(),ms=()=>Number(process.hrtime.bigint()-origin)/1e6;let scene=0;let dom,w,$,tick,requests,gate;
const pid='proj_'+'1'.repeat(32),other='proj_'+'2'.repeat(32),rid='run_'+'3'.repeat(32);
const check=(v,label)=>{assert(v,label);checks.push(label);};
const settle=()=>new Promise(r=>setImmediate(r));
async function setup(){dom?.window.close();dom=new JSDOM(fs.readFileSync(path.join(web,'index.html'),'utf8'),{url:'http://synthetic.invalid',runScripts:'dangerously'});w=dom.window;$=id=>w.document.getElementById(id);requests=[];gate=null;scene++;
 w.setInterval=(fn,delay)=>{assert.equal(delay,2500);tick=fn;return 1;};w.crypto.randomUUID=()=>crypto.randomUUID();
 w.fetch=async(url,opts={})=>{const method=opts.method||'GET',record={scene,started_ms:ms(),path:url,method,body:opts.body&&JSON.parse(opts.body)};requests.push(record);requestTimeline.push(record);let body;try{
 if(gate&&!gate.used&&gate.path===url){gate.used=true;body=await new Promise((resolve,reject)=>{gate.resolve=resolve;gate.reject=reject;});}
 if(method==='POST')throw Error('synthesized lost acceptance, not actual HTTP');
 if(body===undefined){if(url==='/health')body={mode:'MOCK',api:'UP',worker:'UP'};else if(url==='/api/apps'||url.endsWith('/goal-cards'))body={items:[]};else if(url.startsWith('/api/runs/'))body={id:rid,status:'SUCCEEDED',namespace:'INTERNAL_APPRUN',version:1,events:[],result:null};else body=[];}
 record.response=body;record.completed_ms=ms();return {ok:true,status:200,json:async()=>body};}catch(error){record.error=error.message;record.completed_ms=ms();throw error;}};
 const script=w.document.createElement('script');script.textContent=fs.readFileSync(source,'utf8');w.document.body.append(script);$('project-select').append(new w.Option('A',pid),new w.Option('B',other));$('project-select').value=pid;w.eval('token="synthetic-A";');
}
function arm(phase){phaseTimeline.push({event:'arm',scene,phase,ms:ms()});gate={path:phase==='health'?'/health':phase==='refresh'?`/api/projects/${pid}/resources`:`/api/runs/${rid}`,used:false};if(phase==='showRun')w.eval(`activeRun=${JSON.stringify(rid)}`);}
function value(phase){return phase==='health'?{mode:'MOCK',api:'UP',worker:'UP'}:phase==='refresh'?[]:{id:rid,status:'SUCCEEDED',namespace:'INTERNAL_APPRUN',version:1,events:[],result:null};}
async function pending(phase){arm(phase);const p=tick();for(let i=0;i<50&&!gate.used;i++)await settle();phaseTimeline.push({event:'gate-check',scene,phase,used:gate.used,ms:ms(),health:$('health').textContent,error:$('error').textContent,latch:w.eval('backgroundRefreshInFlight'),requests:requests.length});assert(gate.used,'phase reached');return {promise:p};}
(async()=>{try{await setup();await tick();fs.writeFileSync(path.join(root,'one-tick.json'),JSON.stringify({kind:'DIAGNOSTIC_ONLY',health:$('health').textContent,error:$('error').textContent,latch:w.eval('backgroundRefreshInFlight'),requestTimeline,phaseTimeline},null,2));}finally{dom?.window.close();}})();
