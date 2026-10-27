'use strict';
// Full original HTML/controller, finite synthetic GETs. No HTTP/browser/model.
const fs=require('node:fs'),assert=require('node:assert/strict'),{JSDOM,VirtualConsole}=require('jsdom');
const errors=[],actions=[],requests=[],held=[],checks=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(fs.readFileSync('src/sim2act/web/index.html','utf8'),{runScripts:'dangerously',virtualConsole:vc}),w=dom.window,d=w.document,$=id=>d.getElementById(id);
w.setInterval=()=>0;w.fetch=()=>{throw Error('No network');};
for(const name of ['onclick','onchange']){const descriptor=Object.getOwnPropertyDescriptor(w.HTMLElement.prototype,name);Object.defineProperty(w.HTMLElement.prototype,name,{...descriptor,set(fn){descriptor.set.call(this,typeof fn==='function'?function(...args){const result=fn.apply(this,args);if(result?.then){actions.push(result);result.catch(()=>{});}return result;}:fn);}});}
const script=d.createElement('script');script.textContent=fs.readFileSync(process.argv[2]||'src/sim2act/web/app.js','utf8');d.body.append(script);
const check=(ok,label)=>{assert.ok(ok,label);checks.push(label);};
const until=async fn=>{for(let n=0;n<40;n++){if(fn())return;await new Promise(setImmediate);}throw Error('Finite adapter scheduling bound');};
function projects(selected){$('project-select').replaceChildren(...['a','b'].map(id=>new w.Option('Project '+id,'project-'+id)));$('project-select').value='project-'+selected;}
const grants=id=>[{id:'grant-'+id,tool_ref:'tool-'+id,principal_id:'user-'+id,revoked:false,expires_at:2000000000,revision:1}];
let deniedMaterials=null,deniedGrants=null,holdGrants=false;
w.refreshGoalCards=async()=>{};w.refreshApps=async()=>{};
w.api=(path,method='GET',body)=>{requests.push({path,method,...(body?{body}:{} )});assert.equal(method,'GET','this test must never submit');const m=path.match(/^\/api\/projects\/project-([ab])\/(.+)$/);assert.ok(m,path);const [,id,kind]=m;
 if(kind==='resources')return deniedMaterials===id?Promise.reject(Error('Synthetic '+id+' material read failed')):Promise.resolve([]);
 if(kind==='runs?metadata_only=true')return Promise.resolve([]);
 if(kind==='grants'){if(holdGrants)return new Promise((resolve,reject)=>held.push({id,resolve,reject}));if(deniedGrants===id)return Promise.reject(Error('Synthetic '+id+' grants read failed'));return Promise.resolve(grants(id));}
 throw Error('Unexpected path '+path);
};
function change(id){$('project-select').value='project-'+id;$('project-select').dispatchEvent(new w.Event('change'));return actions.at(-1);}
const intents=()=>w.eval('JSON.stringify([...ordinarySubmissions].map(([a,m])=>[a,[...m]]))');
const watchdog=setTimeout(()=>{console.error('Local five-second bound');process.exit(1);},5000);
(async()=>{try{
 projects('a');w.eval("token='actor-a';identityConnectionGeneration=1;ordinarySubmissions.set(token,new Map([['project-a',{state:'unknown',body:{goal:'original task',resource_refs:[],request_key:'keep-key'}}]]));");const original=intents();
 await w.refresh();check($('grants').textContent.includes('tool-a'),'A grant displayed after successful current read');const oldRevoke=$('grants').querySelector('button');
 deniedMaterials='b';const failed=change('b');
 check(!$('grants').textContent.includes('tool-a')&&$('grants').textContent.includes('未确认'),'project switch immediately removes A grant even before B material response');
 await failed;check(!$('grants').textContent.includes('tool-a'),'upstream failure cannot leave old project grants');
 const independent=$('grants').querySelector('button');const directStart=requests.length;independent.click();await actions.at(-1);check(requests.length===directStart+1&&requests.at(-1).path.endsWith('/grants')&&$('grants').textContent.includes('tool-b'),'grants recovery reads only grants even while material reads remain denied');
 const beforeOld=requests.length;await oldRevoke.onclick();check(requests.length===beforeOld,'detached A revoke cannot submit in B');
 deniedMaterials=null;deniedGrants='b';await change('b');
 check($('grants').textContent.includes('未确认')&&!$('grants').textContent.includes('tool-a'),'current grants read failure is neutral and clears prior records');
 const retry=$('grants').querySelector('button');check(retry?.textContent.includes('只读'),'explicit read-only grants recovery is available');
 deniedGrants=null;holdGrants=true;const beforeRetry=requests.length;retry.click();const retrying=actions.at(-1);await until(()=>held.length===1);
 const once=requests.length;retry.click();check(retry.disabled&&requests.length===once&&requests.slice(beforeRetry).every(x=>x.method==='GET'),'busy recovery cannot duplicate pending reads or send a command');
 held[0].resolve(grants('b'));await retrying;check($('grants').textContent.includes('tool-b')&&!$('grants').textContent.includes('tool-a'),'recovery renders only current B grants');
 const oldA=change('a');await until(()=>held.length===2);holdGrants=false;await change('b');const fresh=$('grants').textContent;held[1].resolve(grants('a'));await oldA;
 check($('grants').textContent===fresh,'late A grants cannot repaint B');
 holdGrants=true;const oldActor=w.refresh();await until(()=>held.length===3);w.eval("identityConnectionGeneration++;clearIdentityView();token='actor-b';");projects('b');holdGrants=false;await w.refresh();const actorFresh=$('grants').textContent;held[2].reject(Error('Old actor late grants error'));await oldActor;
 check($('grants').textContent===actorFresh,'old identity rejection cannot invalidate or replace new actor grants');
 holdGrants=true;const oldSame=w.refreshGrants();await until(()=>held.length===4);holdGrants=false;await w.refreshGrants();const newer=$('grants').textContent;held[3].resolve(grants('obsolete-b'));await oldSame;
 check($('grants').textContent===newer&&!$('grants').textContent.includes('obsolete'),'same-project older read cannot overwrite a newer read');
 holdGrants=true;const beforeABA=change('a');await until(()=>held.length===5);holdGrants=false;await change('b');await change('a');const currentA=$('grants').textContent;held[4].resolve(grants('obsolete-a'));await beforeABA;
 check($('grants').textContent===currentA&&!$('grants').textContent.includes('obsolete'),'A-B-A navigation rejects the original A response even with same identity and project');
 check(intents()===original&&requests.every(x=>x.method==='GET')&&!errors.length,'original UNKNOWN body/key unchanged; only synthetic GET and no script errors');
 console.log(JSON.stringify({status:'PASS',scope:'JSDOM original controller / synthetic adapter only',checks,requests,actual_http:0,models:0},null,2));
}finally{clearTimeout(watchdog);for(const h of held)h.reject(Error('Test cleanup'));dom.window.close();}})().catch(e=>{console.error(e.stack);process.exitCode=1;});
