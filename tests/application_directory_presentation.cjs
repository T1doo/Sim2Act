'use strict';
// Actual directory renderer and DOM; no network, Worker, model or browser pixels.
const fs=require('node:fs'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const dom=new JSDOM(fs.readFileSync('src/sim2act/web/index.html','utf8'),{runScripts:'dangerously',url:'http://127.0.0.1/'}),w=dom.window,d=w.document,checks=[];
w.$=id=>d.getElementById(id);w.safe=fn=>fn;
const install=text=>{const s=d.createElement('script');s.textContent=text;d.body.append(s);};
install(`let token='identity-a',identityConnectionGeneration=1,workspaceSelectionGeneration=1;const row=(text,action,label)=>{const e=document.createElement('div');e.textContent=text;if(action){const b=document.createElement('button');b.textContent=label;b.onclick=action;e.append(b);}return e;};function renderNaturalFirstGuide(){}function clearApp(){}function renderCsvMaterialAccess(){}let opens=0;async function showApp(){opens++;}`);
d.getElementById('project-select').append(new w.Option('synthetic','project-a'));d.getElementById('project-select').value='project-a';
install(fs.readFileSync('src/sim2act/web/use.js','utf8'));
const app={id:'app-a',name:'<img src=x onerror=alert(1)>',use_family:'LOCAL_RECORDS'};w.testApps=[app];
function check(ok,label){assert(ok,label);checks.push(label);}
(async()=>{try{
 await w.eval('refreshApplicationUse(testApps)');let node=d.querySelector('.application-directory-item'),notes=node.querySelector('details');notes.open=true;
 check(node.querySelector('strong').textContent===app.name&&!node.querySelector('img'),'app name uses inert text');
 check(notes.textContent.includes('每次先预览，再单独确认写入')&&notes.textContent.includes('未发布'),'full original restrictions preserved');
 await w.eval('refreshApplicationUse(testApps)');node=d.querySelector('.application-directory-item');
 check(node.querySelector('details').open,'unchanged same-context refresh preserves disclosure');
 node.querySelector('button').click();await Promise.resolve();check(w.eval('opens')===1,'same original button action remains attached');
 const stale=node.querySelector('button');w.eval(`token='identity-b';`);stale.click();await Promise.resolve();check(w.eval('opens')===1,'stale original action still refuses identity change');
 await w.eval('refreshApplicationUse(testApps)');check(!d.querySelector('.application-directory-item details').open,'new identity cannot inherit previous disclosure');
 d.querySelector('.application-directory-item details').open=true;w.testApps=[{...app,name:'different current definition'}];await w.eval('refreshApplicationUse(testApps)');check(!d.querySelector('.application-directory-item details').open,'changed content closes old disclosure');
 d.getElementById('use-info').dataset.readState='error';w.eval('clearApplicationUse()');check(!d.getElementById('use-info').dataset.readState,'original clear removes old error projection');
 d.getElementById('use-info').dataset.readState='error';w.eval(`openApplicationMaterialAccess('app-a')`);check(!d.getElementById('use-info').dataset.readState&&d.getElementById('use-info').textContent.includes('仅管理'),'material management cannot inherit result-read error');
 console.log(JSON.stringify({status:'PASS',scope:'actual directory renderer / JSDOM, no HTTP or pixels',checks,requests:0},null,2));
}finally{dom.window.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
