'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict'),{JSDOM,VirtualConsole}=require('jsdom');
const errors=[],requests=[],checks=[],actions=[],held=[],opens=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(fs.readFileSync('src/sim2act/web/index.html','utf8'),{runScripts:'dangerously',virtualConsole:vc}),w=dom.window,d=w.document,$=id=>d.getElementById(id);
w.setInterval=()=>0;w.fetch=()=>{throw Error('No HTTP');};
for(const name of ['onclick','onchange']){const desc=Object.getOwnPropertyDescriptor(w.HTMLElement.prototype,name);Object.defineProperty(w.HTMLElement.prototype,name,{...desc,set(fn){desc.set.call(this,typeof fn==='function'?function(...args){const v=fn.apply(this,args);if(v?.then){actions.push(v);v.catch(()=>{});}return v;}:fn);}});}
const script=d.createElement('script');script.textContent=fs.readFileSync(process.argv[2]||'src/sim2act/web/app.js','utf8');d.body.append(script);
const check=(v,s)=>{assert(v,s);checks.push(s);};
function projects(){ $('project-select').replaceChildren(new w.Option('A','a'),new w.Option('B','b')); }
projects();w.eval("token='actor-a';");w.refreshApps=async()=>{};w.showGoalCard=async(id)=>opens.push(id);
let failResource=false,failGoals=false,hold=false;
const card=id=>({id:'goal-'+id,title:'Goal '+id,version:1});
w.api=(url,method='GET')=>{requests.push({url,method});assert.equal(method,'GET');if(url.endsWith('/resources'))return failResource?Promise.reject(Error('Resource denied')):Promise.resolve([]);if(url.endsWith('/goal-cards')){if(hold)return new Promise((resolve,reject)=>held.push({resolve,reject}));return failGoals?Promise.reject(Error('Goal denied')):Promise.resolve({items:[card($('project-select').value)]});}if(url.includes('/runs?')||url.endsWith('/grants'))return Promise.resolve([]);throw Error('unexpected '+url);};
function change(id){$('project-select').value=id;$('project-select').dispatchEvent(new w.Event('change'));return actions.at(-1);}
const names=()=>$('goal-card-list').textContent;
(async()=>{try{
 await w.refreshGoalCards('a');const oldA=$('goal-card-list').querySelector('button');failResource=true;await change('b');
 check(!names().includes('Goal a')&&names().includes('未确认'),'project switch with earlier material failure immediately clears old Goal directory');
 const before=requests.length;await oldA.onclick();check(requests.length===before&&!opens.length,'old project directory callback cannot open another project');
 failResource=false;failGoals=true;await change('a');
 check(!names().includes('Goal a')&&names().includes('未确认'),'current goal list failure clears stale cards and reports unconfirmed state');
 const retry=$('goal-card-list').querySelector('button');assert(retry&&retry.textContent.includes('只读'));hold=true;retry.click();const pending=actions.at(-1),count=requests.length;retry.click();check(retry.disabled&&requests.length===count,'read-only recovery locks double click to one GET');held[0].resolve({items:[card('a')]});await pending;check(names().includes('Goal a'),'explicit read-only retry restores only current directory');
 hold=true;const older=w.refreshGoalCards('a'),newer=w.refreshGoalCards('a');held[2].resolve({items:[{...card('a'),title:'Newest A'}]});await newer;held[1].resolve({items:[{...card('a'),title:'Stale A'}]});await older;check(names().includes('Newest A')&&!names().includes('Stale A'),'older same-project read cannot overwrite a newer directory');
 const lateFailure=w.refreshGoalCards('a'),fresh=w.refreshGoalCards('a');held[4].resolve({items:[{...card('a'),title:'Fresh after failure'}]});await fresh;held[3].reject(Error('late prior failure'));await lateFailure;check(names().includes('Fresh after failure')&&!names().includes('未确认'),'late prior failure cannot erase newer success');
 const oldRetryCount=requests.length;await retry.onclick();check(requests.length===oldRetryCount,'detached recovery callback cannot read after a newer generation');
 const oldButton=$('goal-card-list').querySelector('button');hold=false;failGoals=false;w.eval("identityConnectionGeneration++;clearIdentityView();token='actor-b';");projects();await w.refreshGoalCards('a');await oldButton.onclick();check(!opens.length,'detached prior identity button cannot open a card in reused project');
 const current=$('goal-card-list').querySelector('button');w.clearGoalCard();await current.onclick();check(opens.length===1&&opens[0]==='goal-a','opening or clearing a Goal does not invalidate other current directory buttons');
 check(requests.every(x=>x.method==='GET')&&!errors.length,'all operations are finite synthetic GETs with no script errors');
 console.log(JSON.stringify({status:'PASS',scope:'real template/app controller; synthetic API, no HTTP/native/model',checks,requests},null,2));
}finally{for(const p of held)p.reject(Error('cleanup'));dom.window.close();}})().catch(e=>{console.error(e.stack);process.exitCode=1;});
