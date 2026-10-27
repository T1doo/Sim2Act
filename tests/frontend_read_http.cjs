'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{JSDOM,VirtualConsole}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),requests=[],checks=[],errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(fs.readFileSync('src/sim2act/web/index.html','utf8'),{url:'http://synthetic.invalid/',runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc}),w=dom.window,d=w.document,$=id=>d.getElementById(id);
w.setInterval=()=>0;w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});
let failNext=false;w.fetch=async(path,options)=>{assert.equal(options.method,'GET');if(failNext){failNext=false;requests.push({path,method:'GET',classification:'SYNTHETIC_TRANSPORT_REJECTION_BEFORE_SERVER'});throw Error('CONTROLLED_LOCAL_TRANSPORT_FAILURE');}const r=await fetch(info.base+path,options);requests.push({path,method:'GET',status:r.status,classification:'ACTUAL_LOOPBACK_HTTP'});return r;};
for(const script of [...d.querySelectorAll('script[src]')]){const node=d.createElement('script');node.textContent=fs.readFileSync('src/sim2act/web'+script.getAttribute('src'),'utf8');d.body.append(node);}
const check=(ok,label)=>{assert.ok(ok,label);checks.push(label);};
(async()=>{try{
 w.eval('token='+JSON.stringify(info.token)+';identityConnectionGeneration=1;');$('project-select').replaceChildren(new w.Option('Sealed synthetic CSV',info.project_id));
 const app=await w.api('/api/apps/'+info.app_id),instance=await w.api('/api/internal/instances/'+info.instance_id);
 w.auditApp=app;w.auditInstance=instance;w.eval("activeApp=auditApp.id;appSelectionGeneration=1;engineering={project:auditApp.project_id,token,app:activeApp,appGeneration:1,instanceGeneration:1,runGeneration:0,instance:auditInstance,run:null,draft:auditApp,agent:false,spec:false,workflow:false,literal:false,busy:false,releases:[],historyReady:false};");const view=w.eval('engineering');
 await w.refreshInternal(view);check(view.historyReady&&$('internal-releases').querySelector('button')&&$('internal-instances').querySelector('button'),'original authenticated app/release/instance history renders actual sealed records');
 await w.showInternalRun(info.run_id,view,instance);const actual=JSON.parse($('internal-run-detail').textContent);assert.deepEqual(actual.result,info.result.result);check(actual.status==='SUCCEEDED'&&$('internal-run-status').textContent.includes('"sum":"30"'),'real saved run result is shown without a new execution');
 failNext=true;await w.showInternalRun(info.run_id,view,instance);check(!$('internal-run-detail').textContent&&!$('internal-run-status').textContent.includes('"sum"')&&$('internal-run-status').textContent.includes('未确认'),'one explicitly synthetic transport rejection clears current protected result');
 await w.showInternalRun(info.run_id,view,instance);check(JSON.parse($('internal-run-detail').textContent).id===info.run_id,'explicit read-only retry restores exact original run');
 check(requests.filter(x=>x.classification==='ACTUAL_LOOPBACK_HTTP').length===7&&requests.filter(x=>x.classification.startsWith('SYNTHETIC')).length===1&&requests.every(x=>x.method==='GET')&&!errors.length,'seven actual GET plus one labelled transport fault, zero commands/model and no script errors');
 console.log(JSON.stringify({status:'PASS',scope:'original full page scripts / actual local readonly sealed CSV API / explicit historical test clock / not native or G0',checks,requests,models:0,business_post:0},null,2));
}finally{dom.window.close();}})().catch(e=>{console.error(e.stack);process.exitCode=1;});
