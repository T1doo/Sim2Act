'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {JSDOM,VirtualConsole}=require('jsdom');
const source=fs.readFileSync('/workspace/Sim2Act/tests/application_use.cjs','utf8');
const helper=source.slice(source.indexOf('// Track each page'),source.indexOf('async function setup()'));
(async()=>{
for(const kind of ['asyncReject','syncThrow']){
 const dom=new JSDOM('<button id="b">test</button>',{runScripts:'dangerously',virtualConsole:new VirtualConsole()});const page={requests:0,actions:new Set(),errors:[]};const originalError=Error('synthetic rejection');
 const ctx=vm.createContext({assert,page,w:dom.window,dom,lifecycle:[],setImmediate,wait:async(fn)=>{for(let i=0;i<100;i++){if(fn())return;await new Promise(r=>setTimeout(r,2));}throw Error('harness timeout');}});
 vm.runInContext(helper,ctx);ctx.trackHandlers(dom.window,page);
 dom.window.document.getElementById('b').onclick=kind==='asyncReject'?async()=>{throw originalError}:()=>{throw originalError};dom.window.document.getElementById('b').click();
 await assert.rejects(ctx.idlePage(),e=>e===originalError);assert.equal(page.actions.size,0);assert.equal(page.errors[0],originalError);dom.window.close();console.log(kind+' original rejection preserved: PASS');
}
})();
