'use strict';
// Actual template and controllers; finite in-memory GET adapter, no HTTP/model/Worker.
const fs=require('node:fs'),assert=require('node:assert/strict'),{JSDOM,VirtualConsole}=require('jsdom');
const checks=[],requests=[],errors=[];let dom,w,$;
function boot(hash){if(dom)dom.window.close();const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));dom=new JSDOM(fs.readFileSync('src/sim2act/web/index.html','utf8'),{url:'http://synthetic.invalid/#'+hash,runScripts:'dangerously',virtualConsole:vc});w=dom.window;$=id=>w.document.getElementById(id);w.setInterval=()=>0;w.fetch=()=>{throw Error('HTTP forbidden');};w.TextEncoder=TextEncoder;for(const name of ['app.js','natural-goal.js']){const s=w.document.createElement('script');s.textContent=fs.readFileSync('src/sim2act/web/'+name,'utf8');w.document.body.append(s);}$('project-select').append(new w.Option('Project A','a'),new w.Option('Project B','b'));w.eval("token='synthetic-actor';");}
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
const denied=()=>Object.assign(Error('CONTROLLED_READ_DENIED'),{httpStatus:403});
function adapter(metadata=true){w.api=async(path,method='GET')=>{requests.push({path,method});assert.equal(method,'GET');if(path.endsWith('/goal-cards')||path.endsWith('/preparation'))throw denied();assert(path.endsWith('/consent-status'));if(!metadata)throw denied();return {status:'CONSENT_METADATA_ONLY_LIVE_BLOCKED',review_token:'a'.repeat(64),approved:true,revoked:false,expired:false,live_allowed:false,new_runs:0,new_slots:0,actual_model_requests:0};};}
(async()=>{try{
 boot('trial-project=a&trial-key=original-key');adapter();
 await assert.rejects(w.refreshTrialCards(),/CONTROLLED_READ_DENIED/);
 check($('trial-original-key').value==='original-key','cold URL original key restored even when goal catalog GET fails');
 check(w.eval("trialEntry().key==='original-key'&&trialEntry().state==='unknown'&&trialEntry().receipt===null"),'cold placeholder has no private receipt or claimed acceptance');
 check($('trial-prepare').disabled&&$('trial-new').disabled&&$('trial-consent').disabled&&!$('trial-recover').disabled,'UNKNOWN locks new/consent while original GET recovery remains enabled');
 const recover=$('trial-recover');await recover.onclick();
 check(requests.slice(-2).map(x=>x.path).join('|')==='/api/projects/a/natural-trials/original-key/preparation|/api/projects/a/natural-trials/original-key/consent-status','explicit recovery uses original key and existing metadata fallback');
 check($('trial-scope').textContent.includes('仅恢复同意元数据')&&!$('trial-scope').textContent.includes('undefined')&&$('trial-consent').disabled,'metadata-only recovery does not invent private scope or execution consent');
 boot('trial-project=a&trial-key=another-key');adapter(false);w.eval("trialEntries.set(trialIndex(trialContext()),{key:'pending-original',base:'/api/projects/a/natural-trials/pending-original',operation:0,state:'unknown',receipt:null,message:'UNKNOWN'});");
 await assert.rejects(w.refreshTrialCards(),/CONTROLLED_READ_DENIED/);
 check($('trial-original-key').value==='pending-original','existing unresolved entry wins over a different address key');
 await $('trial-recover').onclick();check(w.eval("trialEntry().state==='unknown'&&trialEntry().key==='pending-original'&&trialEntry().receipt===null")&&$('trial-new').disabled&&$('trial-consent').disabled,'failed original read preserves UNKNOWN and never unlocks a new key');
 boot('trial-project=b&trial-key=foreign-key');adapter();await assert.rejects(w.refreshTrialCards(),/CONTROLLED_READ_DENIED/);check(w.eval('trialEntry()===undefined')&&$('trial-original-key').value==='', 'foreign project address is not adopted');
 boot('trial-project=a&trial-key=bad%2Fkey');adapter();await assert.rejects(w.refreshTrialCards(),/CONTROLLED_READ_DENIED/);check(w.eval('trialEntry()===undefined'),'invalid original key is not adopted');
 boot('trial-project=a&trial-key=original-key');adapter();const originalApi=w.api;let release;w.api=(path,method='GET')=>path.endsWith('/goal-cards')?new Promise(resolve=>{requests.push({path,method});release=resolve;}):originalApi(path,method);
 const catalog=w.refreshTrialCards();check($('trial-original-key').value==='original-key','original key is available while directory GET is still pending');await $('trial-recover').onclick();const scope=$('trial-scope').textContent,receipt=w.eval('trialEntry().receipt');release({items:[]});await catalog;
 check($('trial-scope').textContent===scope&&w.eval('trialEntry().receipt')===receipt&&w.eval("trialEntry().state==='known'"),'late directory success cannot erase newer original-key metadata recovery');
 boot('');w.api=async(path,method='GET')=>{requests.push({path,method});assert.equal(method,'GET');assert(path.endsWith('/goal-cards'));return {items:[{id:'one',title:'First',version:1},{id:'two',title:'Second',version:1}]};};await w.refreshTrialCards();check(!$('trial-prepare').disabled&&$('trial-source').value==='one'&&$('trial-cold').value==='two','normal new preparation selection still becomes available after a successful catalog GET');
 check(requests.every(x=>x.method==='GET')&&!errors.length,'all requests are finite synthetic reads without page errors');
 console.log(JSON.stringify({status:'PASS',checks,requests,http:0,model:0,worker:0},null,2));
}finally{dom?.window.close();}})().catch(e=>{console.error(e.stack);process.exitCode=1;});
