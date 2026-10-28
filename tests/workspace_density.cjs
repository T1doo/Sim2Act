'use strict';
// Real template + real scope controller, isolated navigation signals; no browser/API.
const fs=require('node:fs'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const source=fs.readFileSync('src/sim2act/web/app.js','utf8'),html=fs.readFileSync('src/sim2act/web/index.html','utf8');
const block=source.match(/^function renderProjectContext\(\) \{[\s\S]*?(?=^function selectResourceCategory)/m)[0];
const dom=new JSDOM(html,{runScripts:'outside-only'}),w=dom.window,d=w.document;
let writes=0,changes=0;w.fetch=()=>{writes++;throw Error('No network allowed');};
d.getElementById('project-select').addEventListener('change',()=>changes++);
for(const form of d.forms)form.addEventListener('submit',e=>{e.preventDefault();writes++;});
w.eval('var token="";var $=id=>document.getElementById(id);var routes=[];function selectWorkspace(id){routes.push(id);}'+block+';window.scopeObserver=projectContextObserver;');
const click=()=>d.getElementById('project-context-open').click();
assert.equal(d.querySelectorAll('#project-select').length,1);
assert.equal(d.getElementById('project-select').closest('section').id,'project-context');
assert.equal(d.getElementById('project-create').open,false);
d.querySelector('.scope-note').open=true;click();
assert.equal(d.getElementById('login').hidden,false);assert.equal(d.activeElement.id,'token');
w.token='synthetic owner';w.renderProjectContext();click();
assert.equal(d.getElementById('project-create').open,true);assert.equal(d.activeElement.id,'project-name');
const option=d.createElement('option');option.value='project-synthetic';option.textContent='<img src=x onerror=bad()> · 项目';d.getElementById('project-select').append(option);w.renderProjectContext();
click();assert.equal(d.activeElement.id,'project-select');
assert.ok(d.getElementById('project-context-status').textContent.includes(option.textContent));assert.equal(d.querySelectorAll('#project-context img').length,0);
assert.equal(changes,0);assert.equal(writes,0);assert.deepEqual([...w.routes],['projects','projects','projects']);
assert.equal(d.getElementById('run-form').closest('details').id,'task-create');
assert.equal(d.getElementById('resource-form').closest('details').id,'resource-create');
assert.equal(d.getElementById('protocol-detail').closest('#task-result-panel').id,'task-result-panel');
assert.equal(d.getElementById('goal-card-form').parentElement.tagName,'SECTION');
console.log(JSON.stringify({status:'PASS',classification:'ISOLATED_REAL_TEMPLATE_SCOPE_CONTROLLER_NOT_NATIVE',cases:['no-token focus','no-project disclosure+focus','existing global selection focus only','untrusted name text-only','zero change/submit/network','original form/guard subtrees retained','section changes preserve cold-page trial recovery key'],network:0,submits:0,selection_changes:0}));w.scopeObserver.disconnect();dom.window.close();

// Use the real section controller with a persisted trial key; section navigation
// must preserve cold-page recovery without any network or submit.
const sections=source.match(/^function selectProjectSection\(id, focus=false\) \{[\s\S]*?^\}\)\(\);/m)[0];
for(const hash of ['#trial-project=project-synthetic&trial-key=original_key_17','#task-workbench']){
 const page=new JSDOM(html,{runScripts:'outside-only',url:'https://sim2act.invalid/'+hash}),v=page.window;
 v.matchMedia=()=>({matches:false});v.fetch=()=>{throw Error('No network allowed');};
 v.eval('var $=id=>document.getElementById(id);'+sections);
 const original=v.location.hash;
 for(const anchor of v.document.querySelectorAll('.section-links a')){
  anchor.click();
  assert.equal(v.location.hash,original);
  assert.equal(v.document.getElementById('projects').dataset.section,anchor.hash.slice(1));
 }
 if(hash.includes('trial-key'))assert.equal(new URLSearchParams(v.location.hash.slice(1)).get('trial-key'),'original_key_17');
 page.window.close();
}
