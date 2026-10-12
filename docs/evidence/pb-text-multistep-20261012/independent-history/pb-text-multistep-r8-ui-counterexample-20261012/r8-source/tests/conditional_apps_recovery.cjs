'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{JSDOM}=require('jsdom');
const root=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(root,'info.json'))),requests=[],checks=[],sourceHashes={};
let dom,w,$,mode=info.fault;
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
(async()=>{try{
 const html=await(await fetch(info.base)).text();dom=new JSDOM(html,{url:info.base,runScripts:'dangerously'});w=dom.window;$=id=>w.document.getElementById(id);
 w.fetch=async(url,options={})=>{const target=new URL(url,info.base);assert.equal(target.origin,info.base);const response=await fetch(target,options);
  if(options.method==='POST'&&target.pathname.includes('/conditional-apps/')){const actual=await response.json(),entry={body:JSON.parse(options.body),server_status:response.status,actual_run_id:actual.run_id,actual_cached:actual.cached};requests.push(entry);
   if(mode==='lost'&&response.ok){mode='';throw TypeError('Synthetic accepted receipt loss');}
   if(mode==='malformed'&&response.ok){mode='';const damaged={...actual};delete damaged.phase;return {ok:true,json:async()=>damaged};}
   if(mode==='retry-422'&&response.ok){mode='';return {ok:false,status:422,json:async()=>({error:{code:'INVALID_INPUT',message:'Synthetic transport 422 after real cached acceptance'}})};}
   return {ok:response.ok,status:response.status,json:async()=>actual};}
  return response;};
 for(const name of ['app.js','internal.js','protocol.js','use.js','conditional-runs.js','conditional-apps.js']){const text=await(await fetch(info.base+'/'+name)).text();sourceHashes[name]=crypto.createHash('sha256').update(text).digest('hex');const script=w.document.createElement('script');script.textContent=text;w.document.body.append(script);}
 w.eval("token='synthetic-test-A'");$('project-select').replaceChildren(new w.Option('Isolated report project',info.project));await w.openReportApp(info.app);
 const facts=days=>{for(const[k,v]of Object.entries({trip:'true',receipt:'true',approved:'false',amount:'500',days}))$('report-app-'+k).value=v;};
 facts('1.5');await w.runReportApp();check(requests[0].server_status===422&&$('report-app-retry').hidden&&!$('report-app-submit').disabled,'first authoritative 422 permits correction without pending unknown');
 facts('2');await w.runReportApp();check(!$('report-app-retry').hidden&&$('report-app-submit').disabled,'accepted lost or malformed receipt creates unknown lock');
 const frozen=JSON.stringify(requests[1].body),originalRun=requests[1].actual_run_id;
 mode='retry-422';await w.runReportApp(true);check(requests[2].server_status===202&&requests[2].actual_cached===true&&requests[2].actual_run_id===originalRun,'retry really reobtains original accepted HTTP receipt before injected 422');
 check(!$('report-app-retry').hidden&&$('report-app-submit').disabled&&w.eval('reportIntents.size')===1,'later retry 422 preserves prior-unknown body/key lock');
 const before=requests.length;await assert.rejects(w.runReportApp(),/先恢复原回执/);check(requests.length===before,'new key cannot be submitted while earlier acceptance is unknown');
 await w.runReportApp(true);check(requests[3].actual_run_id===originalRun&&requests.slice(1).every(r=>JSON.stringify(r.body)===frozen),'explicit successful recovery still resolves same Run with exact original key/body');
 check($('report-app-retry').hidden&&!$('report-app-submit').disabled,'verified actual receipt alone clears unknown lock');
 const result={status:'PASS',fault:info.fault,checks,requests,actual_http_loaded_sha256:sourceHashes,native:'NOT_RUN',cold_provider_calls:0};fs.writeFileSync(path.join(root,'recovery-results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}catch(e){console.error(e.stack);process.exitCode=1;}finally{dom?.window.close();}})();
