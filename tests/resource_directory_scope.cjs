'use strict';
// Actual page/controller; finite synthetic adapter responses, never HTTP.
const fs=require('node:fs'),assert=require('node:assert/strict'),{JSDOM,VirtualConsole}=require('jsdom');
const checks=[],requests=[],held=[],actions=[],errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(fs.readFileSync('src/sim2act/web/index.html','utf8'),{runScripts:'dangerously',virtualConsole:vc}),w=dom.window,d=w.document,$=id=>d.getElementById(id);
w.setInterval=()=>0;w.fetch=()=>{throw Error('No network permitted');};
for(const name of ['onclick','onchange']){const descriptor=Object.getOwnPropertyDescriptor(w.HTMLElement.prototype,name);Object.defineProperty(w.HTMLElement.prototype,name,{...descriptor,set(fn){descriptor.set.call(this,typeof fn==='function'?function(...args){const value=fn.apply(this,args);if(value?.then){actions.push(value);value.catch(()=>{});}return value;}:fn);}});}
const script=d.createElement('script');script.textContent=fs.readFileSync(process.argv[2]||'src/sim2act/web/app.js','utf8');d.body.append(script);assert.deepEqual(errors,[]);
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
const names=()=>$('materials').textContent;
const material=id=>({id:'res-'+id,project_id:'project-'+id,name:'Material '+id,format:'txt',hash:id.repeat(64)});
function projects(selected){$('project-select').replaceChildren(...['a','b'].map(id=>new w.Option('Project '+id,'project-'+id)));$('project-select').value='project-'+selected;}
projects('a');w.eval("token='actor-a';identityConnectionGeneration=1;ordinarySubmissions.set(token,new Map([['project-a',{state:'unknown',body:{goal:'original task',resource_refs:['res-a'],request_key:'original-key-a'},message:'original unknown'}]]));");
const intents=()=>w.eval('JSON.stringify([...ordinarySubmissions].map(([actor,rows])=>[actor,[...rows]]))'),originalIntents=intents();
const originalGoalRead=w.refreshGoalCards;w.refreshGoalCards=async()=>{};w.refreshApps=async()=>{};
let hold=false,denyGoals=false;
w.api=(path,method='GET',body)=>{requests.push({path,method,...(body?{body}:{} )});assert.equal(method,'GET');
 const list=path.match(/^\/api\/projects\/project-([ab])\/resources$/);
 if(list){if(hold)return new Promise((resolve,reject)=>held.push({resolve,reject,id:list[1]}));return Promise.resolve([material(list[1])]);}
 if(path.includes('/runs?metadata_only=true')||path.endsWith('/grants'))return Promise.resolve([]);
 if(path==='/api/resources/res-b')return Promise.resolve({...material('b'),content:'Previously authorized B preview'});
 if(denyGoals&&path==='/api/projects/project-b/goal-cards')return Promise.reject(Error('Synthetic independent Goal list denied'));
 throw Error('Unexpected synthetic adapter path '+path);
};
function switchProject(id){$('project-select').value='project-'+id;$('project-select').dispatchEvent(new w.Event('change'));return actions.at(-1);}
const watchdog=setTimeout(()=>{console.error('Five-second local test deadline');process.exit(1);},5000);
(async()=>{try{
 await w.refresh();check(names().includes('Material a'),'initial successful read renders actual A directory');
 hold=true;const failedSwitch=switchProject('b');held[0].reject(Error('Synthetic B list denied'));await failedSwitch;
 check(!names().includes('Material a')&&names().includes('未确认'),'failed B selection removes A directory and clearly remains unconfirmed');
 const retry=$('materials').querySelector('button');check(retry&&retry.textContent.includes('只读'),'failure exposes explicit read-only list recovery');
 const beforeRetry=requests.length;retry.click();const retried=actions.at(-1);
 check(retry.disabled&&requests.length===beforeRetry+1,'retry locks its control and starts exactly one original GET');
 retry.click();check(requests.length===beforeRetry+1,'double click cannot repeat the pending read');
 held[1].resolve([material('b')]);await retried;
 check(names().includes('Material b')&&!names().includes('Material a')&&!names().includes('未确认'),'explicit successful recovery shows only B');
 check(intents()===originalIntents,'resource recovery preserves original task request body/key and UNKNOWN intent');

 const oldSwitch=switchProject('a');check(!names().includes('Material b'),'project change immediately invalidates previous directory before response');
 const newSwitch=switchProject('b');held[3].resolve([material('b')]);await newSwitch;
 const freshDirectory=names();held[2].resolve([material('a')]);await oldSwitch;
 check(names()===freshDirectory&&names().includes('Material b'),'late A success cannot repaint B after A/B navigation');
 const beforeOldClick=requests.length;await retry.onclick();check(requests.length===beforeOldClick,'detached old recovery callback cannot read or restore another generation');

 const oldActor=w.refresh();w.eval("identityConnectionGeneration++;clearIdentityView();token='actor-b';");projects('b');hold=false;await w.refresh();const actorDirectory=names();
 held[4].reject(Error('Late old actor failure'));await oldActor;
 check(names()===actorDirectory&&names().includes('Material b'),'old identity failure leaves newly read actor directory unchanged');
 const preview=$('materials').querySelector('button');preview.click();await actions.at(-1);check(!$('resource-preview').hidden&&$('resource-preview').textContent.includes('authorized B'),'original preview GET renders current B text');
 hold=true;const failedCurrent=w.refresh();held[5].reject(Error('Current B list denied'));await assert.rejects(failedCurrent,/Current B list denied/);
 check(!names().includes('Material b')&&names().includes('未确认')&&$('resource-preview').hidden&&!$('resource-preview').textContent,'current list failure invalidates directory and old preview without claiming task failure');
 hold=false;await switchProject('a');denyGoals=true;w.refreshGoalCards=originalGoalRead;
 await switchProject('b');
 check($('error').textContent.includes('Synthetic independent Goal list denied')&&names().includes('Material b')&&!names().includes('未确认')&&!$('materials').querySelector('[data-state="loading"]'),'successful resource GET finishes directory even when actual subsequent Goal read fails');
 check(intents()===originalIntents&&requests.every(r=>r.method==='GET')&&errors.length===0,'all original task intents unchanged, only finite adapter GETs, no script errors');
 console.log(JSON.stringify({status:'PASS',scope:'actual app.js and HTML / JSDOM synthetic responses, not native pixels or HTTP',checks,requests,models:0,actual_http:0,timer_polling:'disabled in harness only'},null,2));
}finally{clearTimeout(watchdog);for(const h of held)h.reject(Error('test cleanup'));dom.window.close();}})().catch(e=>{console.error(e.stack);process.exitCode=1;});
