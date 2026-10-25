'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const dom=new JSDOM(fs.readFileSync('src/sim2act/web/index.html','utf8'),{runScripts:'dangerously'}),w=dom.window,d=w.document,$=id=>d.getElementById(id),calls=[],pending=[],checks=[];
w.setInterval=()=>0;w.fetch=()=>{throw Error('No HTTP');};const script=d.createElement('script');script.textContent=fs.readFileSync('src/sim2act/web/app.js','utf8');d.body.append(script);
$('project-select').append(new w.Option('A','a'),new w.Option('B','b'));w.eval("token='actor-a';");let hold=false,deny=false;w.api=async(url,method='GET')=>{calls.push({url,method});assert.equal(method,'GET');if(url.endsWith('/resources'))throw Error('Earlier material read failed');assert.equal(url,'/api/apps?metadata_only=true');if(hold)return new Promise((resolve,reject)=>pending.push({resolve,reject}));if(deny)throw Error('App list failed');return {items:[{id:'app-a',project_id:'a',name:'A private app',use_family:'CSV'},{id:'app-b',project_id:'b',name:'B private app',use_family:'CSV'}]};};
const check=(v,s)=>{assert(v,s);checks.push(s);};const names=()=>$('app-list').textContent;
(async()=>{try{
 await w.refreshApps();const oldA=$('app-list').querySelector('button');$('project-select').value='b';$('project-select').dispatchEvent(new w.Event('change'));await new Promise(r=>setImmediate(r));
 check(!names().includes('A private app')&&names().includes('未确认'),'project switch clears A catalog even when material read fails first');
 deny=true;await assert.rejects(w.refreshApps(),/App list failed/);check(!names().includes('A private app')&&names().includes('未确认'),'failed current catalog read has explicit unconfirmed recovery');
 const retry=$('app-list').querySelector('button');assert(retry&&retry.textContent.includes('只读'));deny=false;await retry.onclick();check(names().includes('B private app')&&!names().includes('A private app'),'read-only retry restores only selected project');
 let opened=0;w.showApp=async()=>opened++;await oldA.onclick();check(opened===0,'old A callback cannot open in B');
 hold=true;const older=w.refreshApps(),newer=w.refreshApps();pending[1].resolve({items:[{id:'app-b',project_id:'b',name:'Fresh B',use_family:'CSV'}]});await newer;pending[0].resolve({items:[{id:'app-b',project_id:'b',name:'Stale B',use_family:'CSV'}]});await older;check(names().includes('Fresh B')&&!names().includes('Stale B'),'late same-project list cannot overwrite newer result');
 const current=$('app-list').querySelector('button');w.clearApp();await current.onclick();check(opened===1,'opening selection does not disable other current catalog buttons');
 check(calls.every(c=>c.method==='GET'),'only finite synthetic GETs, no submission');console.log(JSON.stringify({status:'PASS',checks,calls,http:0,models:0},null,2));
}finally{for(const p of pending)p.reject(Error('cleanup'));dom.window.close();}})().catch(e=>{console.error(e.stack);process.exitCode=1;});
