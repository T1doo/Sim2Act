'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const html=fs.readFileSync('src/sim2act/web/index.html','utf8'),source=fs.readFileSync('src/sim2act/web/app.js','utf8');
const code=source.match(/\(function currentProjectSection\(\)\{[\s\S]*?\n\}\)\(\);/)?.[0];assert(code);
const dom=new JSDOM(html,{runScripts:'dangerously',pretendToBeVisual:true}),w=dom.window,d=w.document,checks=[];w.$=id=>d.getElementById(id);
const targets=[...d.querySelectorAll('.section-links a')].map(a=>d.getElementById(a.hash.slice(1)));let top=[500,1500,2500,3500];targets.forEach((e,i)=>e.getBoundingClientRect=()=>({top:top[i]}));
const script=d.createElement('script');script.textContent=code;d.body.append(script);
const tick=()=>new Promise(r=>w.setTimeout(r,40)),selected=()=>d.querySelector('.section-links a[aria-current="location"]')?.hash;
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
(async()=>{try{
 await tick();check(selected()==='#task-workbench','initial project section is current');
 // Actual DOM order is tasks, maintenance, protocol, goal; link order differs.
 top=[-1000,24,1000,-500];w.dispatchEvent(new w.Event('scroll'));await tick();check(selected()==='#protocol-panel'&&d.querySelectorAll('.section-links [aria-current]').length===1,'actual unordered targets choose nearest current section, not last link');
 d.getElementById('projects').hidden=true;top=[-2000,-1000,24,-1500];w.dispatchEvent(new w.Event('hashchange'));await tick();check(selected()==='#protocol-panel','hidden workspace does not claim new visible location');
 d.getElementById('projects').hidden=false;await tick();check(selected()==='#goal-cards-panel','return uses current geometry rather than old selected presentation');
 console.log(JSON.stringify({status:'PASS',scope:'actual navigation script / synthetic DOM geometry; native scrolling tested separately',checks,requests:0},null,2));
}finally{dom.window.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
