'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const dom=new JSDOM(fs.readFileSync('src/sim2act/web/index.html','utf8'),{runScripts:'dangerously'}),w=dom.window,d=w.document,checks=[];
w.$=id=>d.getElementById(id);w.goalRunCanonical=JSON.stringify;
const install=text=>{const s=d.createElement('script');s.textContent=text;d.body.append(s);};
install(`let identityConnectionGeneration=1,workspaceSelectionGeneration=1;`);
install(fs.readFileSync('src/sim2act/web/csv-owner.js','utf8'));install(fs.readFileSync('src/sim2act/web/csv-goal-revision.js','utf8'));
const option=new w.Option('amount','amount');d.getElementById('use-column').append(option);
w.view={identity:'synthetic',project:'project-a',id:'instance-a',instance:{revision:1},app:{candidate:{manifest:{data_bindings:[{resource_ref:'resource-a'}]},source_hash:'synthetic-hash'}}};
w.release={id:'release-a',fingerprint:'synthetic-fingerprint'};
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
try{
 w.eval('renderCsvReviewStart(view,release)');const ack=d.getElementById('use-csv-review-optin'),preview=d.getElementById('use-csv-review-scope'),details=preview.closest('details');
 check(!!details&&!details.open&&ack.closest('details')===null&&!ack.checked,'exact scope JSON is initially collapsed; original explicit opt-in stays visible and unchecked');
 const value=JSON.parse(preview.textContent);assert.deepEqual(value,{scope:'SUM_ONLY_WITHOUT_MD',release_id:'release-a',release_fingerprint:'synthetic-fingerprint',instance_id:'instance-a',revision:1,resource_id:'resource-a',source_hash:'synthetic-hash',column:'amount'});checks.push('all original scope fields and values remain unchanged');
 ack.checked=true;d.getElementById('use-column').dispatchEvent(new w.Event('change'));check(!ack.checked,'original input change still clears opt-in');
 const panel=d.createElement('section'),button=d.createElement('button');let calls=0;button.onclick=()=>calls++;panel.append(button);w.panel=panel;
 w.eval('mountCsvMaterialAccess({authOnly:false},panel)');check(d.getElementById('use-history').compareDocumentPosition(panel)&w.Node.DOCUMENT_POSITION_FOLLOWING,'optional permission controls follow selected result and history');
 check(d.getElementById('use-refresh').compareDocumentPosition(panel)&w.Node.DOCUMENT_POSITION_FOLLOWING,'original read-only recovery precedes permission controls');
 w.eval('mountCsvMaterialAccess({authOnly:true},panel)');check(d.getElementById('use-info').nextElementSibling===panel,'explicit authorization-only entry still opens directly on its controls');
 button.click();check(calls===1&&panel.firstChild===button,'moving the original panel does not clone or replace handlers');
 console.log(JSON.stringify({status:'PASS',scope:'actual scope renderer and placement / JSDOM; no native pixels',checks,requests:0,models:0},null,2));
}finally{dom.window.close();}
