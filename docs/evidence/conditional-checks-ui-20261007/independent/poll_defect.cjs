'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const root=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(root,'info.json'))),checks=[],requests=[];
let dom,w,$,mode='normal',release;
const check=(ok,name)=>{assert(ok,name);checks.push(name);};
const wait=async(fn,name)=>{const end=Date.now()+6000;while(Date.now()<end){if(fn())return;await new Promise(r=>setTimeout(r,10));}throw Error('Timeout '+name);};
async function setup(){
 dom?.window.close();dom=new JSDOM(await(await fetch(info.base)).text(),{url:info.base,runScripts:'dangerously'});w=dom.window;$=id=>w.document.getElementById(id);
 w.fetch=async(url,opts={})=>{const target=new URL(url,info.base);assert.equal(target.origin,info.base);requests.push({path:target.pathname,method:opts.method||'GET'});
  if(mode==='failure'&&target.pathname.endsWith('/conditional-checks')){mode='normal';throw TypeError('Synthetic technical read failure');}
  const response=await fetch(target,opts);
  if(mode==='hold'&&target.pathname.endsWith('/conditional-checks')){mode='normal';await new Promise(r=>release=r);release=null;}
  return response;};
 for(const file of ['app.js','internal.js','protocol.js','use.js']){const script=w.document.createElement('script');script.textContent=file==='app.js'?fs.readFileSync('/tmp/conditional-ui-independent/pre-poll-fix-app.js','utf8'):await(await fetch(info.base+'/'+file)).text();w.document.body.append(script);}
 $('token').value='synthetic-test-A';$('connect').click();await wait(()=>$('project-select').value===info.project&&$('login').hidden&&$('run-history-status').textContent.includes('暂无'),'connect');
}
async function open(){await w.listConditionalSources();$('condition-resource').value=info.resource;await w.openConditionalSource();assert(!$('condition-form').hidden);}
function manual(unknown=false){
 const fields={trip:unknown?'':'true',amount:unknown?'':'680',receipt:unknown?'':'true',approved:unknown?'':'false',days:unknown?'':'2',R1:unknown?'UNKNOWN':'TRUE',R2:unknown?'UNKNOWN':'TRUE',R3:unknown?'UNKNOWN':'FALSE',decision:unknown?'UNKNOWN':'BLOCK',deadline:'10',date:'UNKNOWN',restart:'false',explanation:'人工报告；自由说明不评分。'};
 for(const [id,value]of Object.entries(fields))$('condition-'+id).value=value;
 for(const o of $('condition-actions').options)o.selected=o.value===(unknown?'clarify_facts':'obtain_prior_approval');
}
(async()=>{try{
 await setup();await open();manual();const start=$('condition-amount').value;
 await new Promise(r=>setTimeout(r,3000));
 const observed={form_hidden:$('condition-form').hidden,amount_before:start,amount_after:$('condition-amount').value,source_cleared:$('condition-source').textContent==='',status:$('condition-status').textContent};
 check(observed.form_hidden&&observed.source_cleared&&observed.amount_after==='','regular 2.5s poll erases user workflow');
 fs.writeFileSync(path.join(root,'results.json'),JSON.stringify({status:'PASS',meaning:'DEFECT_REPRODUCED_NOT_APPROVAL',observed,checks,real_model_requests:0},null,2));console.log(JSON.stringify(observed));
}catch(error){console.error(error.stack);process.exitCode=1;}finally{dom?.window.close();}})();
