'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const root=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(root,'info.json'))),checks=[];let dom,w,$,posts=[],mode='normal',release,page;const lifecycle=[];
const check=(ok,name)=>{assert(ok,name);checks.push(name);};
const wait=async(fn,name)=>{const end=Date.now()+6000;while(Date.now()<end){if(fn())return;await new Promise(r=>setTimeout(r,10));}throw Error('Timeout '+name);};
// Track each page separately: a JSDOM close destroys document while Node I/O may live on.
// Original setInterval=()=>0 remains: product interval timers stay disabled.
// Rejections remain test failures; no exception or original product assertion is suppressed.
async function idlePage(){
 if(!page)return;
 await wait(()=>page.requests===0&&page.actions.size===0,'page actions and HTTP drained');
 await new Promise(resolve=>setImmediate(resolve));
 if(page.errors.length)throw page.errors[0];
 assert.equal(page.requests,0);assert.equal(page.actions.size,0);
}
async function closePage(){
 if(!dom)return;
 await idlePage();
 lifecycle.push({requests:page.requests,actions:page.actions.size,errors:page.errors.length});
 dom.window.close();dom=null;
}
function trackHandlers(window,current){
 for(const name of ['onclick','onchange','onsubmit']){
  const descriptor=Object.getOwnPropertyDescriptor(window.HTMLElement.prototype,name);
  assert(descriptor?.set,'JSDOM handler descriptor required');
  Object.defineProperty(window.HTMLElement.prototype,name,{...descriptor,set(fn){
   descriptor.set.call(this,typeof fn==='function'?function(...args){
    const result=fn.apply(this,args);
    if(result&&typeof result.then==='function'){
     const action=Promise.resolve(result);current.actions.add(action);
     action.then(()=>current.actions.delete(action),error=>{current.errors.push(error);current.actions.delete(action);});
    }
    return result;
   }:fn);
  }});
 }
 window.addEventListener('error',event=>{current.errors.push(event.error||Error(event.message));});
}

(async()=>{
 const checks=[];
 const fresh=()=>{dom=new JSDOM('<button id="b">b</button>');w=dom.window;page={requests:0,actions:new Set(),errors:[]};trackHandlers(w,page);return w.document.getElementById('b');};
 let b=fresh(),e=Error('independent async rejection');b.onclick=async()=>{throw e;};b.click();await new Promise(r=>setImmediate(r));assert.equal(page.actions.size,0);assert.equal(page.errors[0],e);await assert.rejects(idlePage,x=>x===e);checks.push('async rejection original object fails drain');dom.window.close();dom=null;
 b=fresh();e=Error('independent sync rejection');b.onclick=()=>{throw e;};b.click();await assert.rejects(idlePage,x=>x===e);checks.push('synchronous handler error original object fails drain');dom.window.close();dom=null;
 b=fresh();e=Error('independent window error');w.dispatchEvent(new w.ErrorEvent('error',{error:e,message:e.message}));await assert.rejects(idlePage,x=>x===e);checks.push('window error fails drain');dom.window.close();dom=null;
 b=fresh();let resolveAction,closed=0;const realClose=dom.window.close.bind(dom.window);dom.window.close=()=>{closed++;realClose();};page.requests=1;b.onclick=()=>new Promise(r=>{resolveAction=r;});b.click();assert.equal(page.actions.size,1);const closing=closePage();await new Promise(r=>setTimeout(r,25));assert.equal(closed,0);resolveAction();await new Promise(r=>setTimeout(r,25));assert.equal(page.actions.size,0);assert.equal(closed,0);page.requests=0;await closing;assert.equal(closed,1);assert.equal(dom,null);assert.deepEqual(lifecycle.at(-1),{requests:0,actions:0,errors:0});checks.push('close waits independently for event and HTTP before destroy');
 console.log(JSON.stringify({status:'PASS',checks,network_requests:0,product_execution:false}));
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
