// Node/jsdom DOM integration, explicitly NOT a real browser test.
// Run browser-fixture.py first, then NODE_PATH=/workspace/browser-tools/node_modules node this file.
const {JSDOM,VirtualConsole}=require('jsdom');
const fs=require('node:fs');
const results=[];
const check=(name,truth)=>{if(!truth)throw Error(name);results.push({name,status:'PASS'});};
async function wait(fn){for(let i=0;i<100;i++){if(fn())return;await new Promise(r=>setTimeout(r,25));}throw Error('DOM wait timeout');}
async function page(){
 const errors=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
 const dom=await JSDOM.fromURL('http://127.0.0.1:8071',{resources:'usable',runScripts:'dangerously',virtualConsole:vc,
 beforeParse(w){w.fetch=(url,options)=>fetch(new URL(url,'http://127.0.0.1:8071'),options);w.crypto.randomUUID=require('node:crypto').randomUUID;}});
 const w=dom.window,d=w.document;
 await wait(()=>d.getElementById('connect').onclick);
 d.getElementById('token').value='synthetic-pb-browser';d.getElementById('connect').click();
 await wait(()=>d.getElementById('app-list').children.length);
 return {dom,w,d,errors};
}
(async()=>{
 const {dom,w,d,errors}=await page();const $=id=>d.getElementById(id);
 w.eval('selectWorkspace("apps")');
 const project=$('project-select').value;
 const list=await w.eval('api("/api/apps")');const source=list.items.find(x=>x.name==='SYNTHETIC completed preview source');
 await w.eval(`showApp(${JSON.stringify(source.id)})`);
 check('source successful receipt only; failed history excluded',$('extraction-preview').options.length===1 && $('app-history').children.length===2);
 const target=Array.from($('extraction-resource').options).find(o=>o.textContent==='new.csv').value;
 $('extraction-resource').value=target;$('extraction-name').value='DOM extracted new material';
 $('extraction-form').requestSubmit();await wait(()=>$('app-origin').textContent.includes('独立数值'));
 const extracted=w.eval('activeApp');check('source PREVIEW namespace and target scope shown',$('app-origin').textContent.includes('PREVIEW') && $('app-origin').textContent.includes('column'));
 check('extracted candidate cannot recursively extract',$('extraction-form').hidden);
 $('app-column').value='amount';$('app-preview-form').requestSubmit();check('preview reports explicit loading state',$('app-output').dataset.state==='loading');await wait(()=>$('app-output').textContent.includes('合计 40'));
 check('new input computes 40 instead of cached 4',$('app-output').textContent.includes('合计 40'));
 // Invalid API input uses the same UI action runner and retained history.
 await w.eval(`api('/api/apps/${extracted}/previews','POST',{input:{column:'missing'},request_key:'dom-failure'})`);
 await w.eval(`showApp('${extracted}')`);check('failed new input remains in history',$('app-history').textContent.includes('FAILED'));
 $('app-history').querySelector('button').click();check('failed history does not display success',$('app-output').textContent.includes('预览失败'));check('failed history has error styling state',$('app-output').dataset.state==='error');
 await w.eval(`showApp('${source.id}')`);$('extraction-resource').value=target;$('extraction-name').value='DOM stale selection';
 const realFetch=w.fetch;
 // Delay response after server accepts; project navigation must invalidate selection.
 let accepted=false,release;const gate=new Promise(r=>release=r);
 w.fetch=async(url,opts)=>{const r=await realFetch(url,opts);if(String(url).endsWith('/extract')){accepted=true;await gate;}return r;};
 $('extraction-form').requestSubmit();await wait(()=>accepted);
 const other=Array.from($('project-select').options).find(o=>o.value!==project).value;
 $('project-select').value=other;$('project-select').dispatchEvent(new w.Event('change'));await wait(()=>w.eval('activeApp')===null);release();await wait(()=>!w.eval('extractionBusy'));
 check('accepted late response cannot reopen another project',w.eval('activeApp')===null && $('extraction-form').hidden);
 $('project-select').value=project;$('project-select').dispatchEvent(new w.Event('change'));await wait(()=>$('app-resource').options.length===3);
 await w.eval(`showApp('${source.id}')`);check('pending completion releases new selection button',!$('extraction-create').disabled);
 w.fetch=realFetch;$('extraction-resource').value=target;$('extraction-name').value='DOM duplicate';
 const prior=(await w.eval('api("/api/apps")')).items.length;
 $('extraction-form').requestSubmit();$('extraction-form').requestSubmit();await wait(()=>$('app-origin').textContent.includes('独立数值'));
 check('duplicate form submit creates one candidate',(await w.eval('api("/api/apps")')).items.length===prior+1);
 // Independent review's direct-create selection race, now guarded.
 await w.eval(`showApp('${source.id}')`);
 $('app-name').value='DOM direct delayed';$('app-goal').value='trusted direct sum';
 let directAccepted=false,directRelease;const directGate=new Promise(r=>directRelease=r);
 w.fetch=async(url,opts)=>{const r=await realFetch(url,opts);if(String(url).endsWith('/apps/csv-preview')){directAccepted=true;await directGate;}return r;};
 $('app-form').requestSubmit();await wait(()=>directAccepted);
 check('direct creation has loading status and blocks duplicate submit',$('app-create-status').dataset.state==='loading' && $('app-create-submit').disabled);
 await w.eval(`showApp('${extracted}')`);directRelease();await wait(()=>!w.eval('appCreateBusy'));
 check('late direct create does not steal selected app',w.eval('activeApp')===extracted && $('app-create-status').textContent==='');
 w.fetch=realFetch;$('app-name').value='DOM direct normal';$('app-form').requestSubmit();await wait(()=>$('app-create-status').dataset.state==='success');
 check('normal direct create reports success and releases button',!$('app-create-submit').disabled && w.eval('activeApp')!==extracted);
 await w.eval(`showApp('${source.id}')`);
 w.fetch=async(url,opts)=>{if(String(url).endsWith('/apps/csv-preview'))return new Response(JSON.stringify({error:{code:'GRANT_REVOKED'}}),{status:403,headers:{'Content-Type':'application/json'}});return realFetch(url,opts);};
 $('app-name').value='DOM direct error';$('app-form').requestSubmit();await wait(()=>$('app-create-status').dataset.state==='error');
 check('direct create failure preserves current selection and reports reason',w.eval('activeApp')===source.id && $('app-create-status').textContent.includes('GRANT_REVOKED'));
 w.fetch=realFetch;
 await w.eval(`showApp('${extracted}')`);$('app-column').value='quantity';
 let previewAccepted=false,previewRelease;const previewGate=new Promise(r=>previewRelease=r);
 w.fetch=async(url,opts)=>{const r=await realFetch(url,opts);if(String(url).endsWith('/previews')){previewAccepted=true;await previewGate;}return r;};
 $('app-preview-form').requestSubmit();await wait(()=>previewAccepted);
 await w.eval(`showApp('${extracted}')`);previewRelease();await wait(()=>w.eval('appPreviewRequests.size')===0);
 check('late preview does not overwrite reopened same-app selection',$('app-output').textContent==='' && !$('app-preview-submit').disabled);
 w.fetch=realFetch;
 check('stylesheet parsed without jsdom errors',d.styleSheets.length===1);
 check('no jsdom script errors',errors.length===0);dom.window.close();
 const cold=await page();await cold.w.eval(`showApp('${extracted}')`);
 check('cold DOM rereads provenance and persistent history',cold.d.getElementById('app-origin').textContent.includes('PREVIEW') && cold.d.getElementById('app-history').textContent.includes('FAILED'));
 check('cold page requires login again',cold.d.getElementById('token').value==='');cold.dom.window.close();
 fs.writeFileSync(__dirname+'/dom-results.json',JSON.stringify({kind:'NODE_JSDOM_NOT_BROWSER',results},null,2));console.log(JSON.stringify(results));
})().catch(e=>{console.error(e);process.exit(1);});
