'use strict';
// Actual template/controllers and CSS rules; synthetic reads only, no HTTP/browser.
const fs=require('node:fs'),zlib=require('node:zlib'),assert=require('node:assert/strict'),{JSDOM,VirtualConsole}=require('jsdom'),css=require('css-tree');
const root='docs/evidence/goal-card-hierarchy-20261025/',html=fs.readFileSync('src/sim2act/web/index.html','utf8');
const before=new JSDOM(zlib.gunzipSync(fs.readFileSync(root+'before-index.html.gz')).toString()),errors=[],checks=[],requests=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(html,{url:'http://synthetic.invalid/',runScripts:'dangerously',virtualConsole:vc}),w=dom.window,d=w.document,$=id=>d.getElementById(id),old=before.window.document;
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
const signature=e=>({tag:e.tagName,id:e.id,attributes:[...e.attributes].filter(a=>a.name!=='class').map(a=>[a.name,a.value]).sort(),text:e.matches('button,option')?e.textContent:null});
(async()=>{try{
 assert.deepEqual([...d.querySelectorAll('[id]')].map(e=>e.id).filter((id,i,all)=>all.indexOf(id)!==i),[]);
 assert.deepEqual([...old.querySelectorAll('input,textarea,select,button,form')].map(signature).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b))),[...d.querySelectorAll('input,textarea,select,button,form')].map(signature).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b))));
 check(true,'all original controls/forms/attributes and IDs preserved with no duplicate IDs');
 assert.equal($('trial-panel').outerHTML,old.getElementById('trial-panel').outerHTML);
 check(!!($('goal-card-form').compareDocumentPosition($('trial-panel'))&w.Node.DOCUMENT_POSITION_FOLLOWING)&&!$('trial-panel').closest('details,[hidden]'),'full trial subtree unchanged, after the editor and not hidden by a new disclosure');
 check(!!($('goal-card-list').compareDocumentPosition($('goal-candidate-form'))&w.Node.DOCUMENT_POSITION_FOLLOWING)&&!!($('goal-card-history').compareDocumentPosition($('goal-candidate-form'))&w.Node.DOCUMENT_POSITION_FOLLOWING),'saved goals and version navigation precede the fixed CSV candidate');
 for(const id of ['title','goal','known','assumptions','unresolved','constraints','acceptance_checks','resources'])assert.equal($('goal-card-'+id).closest('label').parentElement,$('goal-card-form'));
 check(true,'all eight goal field labels remain direct form children');
 const savedBefore=old.getElementById('goal-cards-panel'),savedAfter=$('goal-cards-panel');savedBefore.replaceWith(old.createComment('goal panel'));const marker=d.createComment('goal panel');savedAfter.replaceWith(marker);
 assert.equal(d.documentElement.outerHTML,old.documentElement.outerHTML);marker.replaceWith(savedAfter);
 check(true,'every DOM subtree outside this goal panel remains identical');
 w.setInterval=()=>0;w.TextEncoder=TextEncoder;w.fetch=()=>{throw Error('HTTP forbidden');};
 for(const file of ['app.js','natural-goal.js']){const script=d.createElement('script');script.textContent=fs.readFileSync('src/sim2act/web/'+file,'utf8');d.body.append(script);}
 $('project-select').append(new w.Option('Synthetic project','project-a'));w.eval("token='synthetic-actor';");
 const form=$('goal-card-form'),parent=form.parentNode,next=form.nextSibling,labels=[...form.children].filter(e=>e.tagName==='LABEL'),headings=[...form.querySelectorAll(':scope > .goal-editor-heading')],states=[...form.children].map(e=>[e,e.hidden]),controls=[...form.querySelectorAll('input,textarea,select,button')].map(e=>[e,e.disabled]);
 w.beginNaturalInputPreparation({firstCreation:{stage:'inputs',mode:'PA'}});
 check(form.parentElement.id==='natural-prep-goal-host'&&labels.every(e=>e.parentNode===form&&!e.hidden)&&headings.every(e=>e.hidden),'actual shared-form borrowing keeps direct label hidden flags clear and hides new headings');
 w.clearNaturalUsePreparation();
 check(form.parentNode===parent&&form.nextSibling===next&&states.every(([e,h])=>e.hidden===h)&&controls.every(([e,b])=>e.disabled===b)&&headings.every(e=>!e.hidden),'actual cancellation restores same form/node position, hidden and disabled states');
 // Current trial unknown state is still rendered and its original gates apply.
 w.eval("trialEntries.set(trialIndex(trialContext()),{key:'original-key',state:'unknown',receipt:null,message:'UNKNOWN · 原键只读恢复'});renderTrialConsent();");
 check($('trial-status').textContent.includes('UNKNOWN')&&!$('trial-panel').closest('details,[hidden]')&&$('trial-consent').disabled&&$('trial-withdraw').disabled&&!$('trial-recover').disabled,'UNKNOWN remains available with original consent/withdraw gates and read-only recovery');
 const tree=css.parse(fs.readFileSync('src/sim2act/web/app.css','utf8')),rules=[];
 function visit(nodes,media=''){for(const n of nodes){if(n.type==='Rule')rules.push({selector:css.generate(n.prelude),selectors:[...n.prelude.children].map(x=>css.generate(x)),media,decl:Object.fromEntries([...n.block.children].filter(x=>x.type==='Declaration').map(x=>[x.property,css.generate(x.value)+(x.important?'!important':'')]))});else if(n.type==='Atrule'&&n.block)visit(n.block.children,media+' '+css.generate(n.prelude||{type:'Raw',value:''}));}}visit(tree.children);
 const own=rules.filter(r=>r.selector.includes('#goal-cards-panel')&&(r.selector.includes('.goal-')||r.selector.includes('#goal-card-')||r.selector.includes('#trial-')));
 check(own.length>20&&own.every(r=>r.selectors.every(selector=>selector.startsWith('#goal-cards-panel')))&&own.some(r=>r.media.includes('max-width:750px')&&r.selector.includes('.goal-card-layout')&&r.decl['grid-template-columns']==='minmax(0,1fr)'),'scoped CSS declares narrow single-column layout with no forced width');
 check(own.some(r=>r.media.includes('max-width:1000px')&&r.selector.endsWith('#goal-card-form')&&r.decl['grid-template-columns']==='minmax(0,1fr)')&&own.every(r=>!('order' in r.decl)&&!('animation' in r.decl)&&!('position' in r.decl)),'field columns collapse before the narrow breakpoint, without visual order, overlay or animation changes');
 const cssDom=new JSDOM(html);try{const sheet=cssDom.window.document.createElement('style');sheet.textContent=fs.readFileSync('src/sim2act/web/app.css','utf8');cssDom.window.document.head.append(sheet);const cf=cssDom.window.document.getElementById('goal-card-form');assert.equal(cssDom.window.getComputedStyle(cf).display,'grid');cssDom.window.document.getElementById('apps').append(cf);assert.notEqual(cssDom.window.getComputedStyle(cf).display,'grid');}finally{cssDom.window.close();}
 check(true,'actual CSS cascade stops applying goal-page grid when form moves outside that page');
 assert.deepEqual(errors,[]);console.log(JSON.stringify({status:'PASS',scope:'JSDOM structure, actual form lifecycle/trial renderer and CSS declarations/cascade; NOT browser layout or pixels',checks,http:0,models:0},null,2));
}finally{before.window.close();dom.window.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
