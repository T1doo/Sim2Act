'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),vm=require('node:vm'),crypto=require('node:crypto'),{JSDOM}=require('jsdom');
const root=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(root,'info.json'))),checks=[],requests=[],loaded={};let dom,w,drop=true;
const check=(ok,label)=>{assert.ok(ok,label);checks.push(label);};
const $=id=>w.document.getElementById(id);
async function click(id){await $(id).onclick({preventDefault(){}});}
async function load(){dom?.window.close();dom=new JSDOM(await(await fetch(info.base)).text(),{url:info.base,runScripts:'outside-only'});w=dom.window;w.setInterval=()=>0;w.structuredClone=structuredClone;w.TextEncoder=TextEncoder;Object.defineProperty(w.crypto,'subtle',{value:crypto.webcrypto.subtle});w.crypto.randomUUID=crypto.randomUUID;
 w.fetch=async(url,opts={})=>{const u=new URL(url,info.base);assert.equal(u.origin,info.base);requests.push({path:u.pathname,method:opts.method||'GET',body:opts.body});const r=await fetch(u,opts);if(drop&&opts.method==='POST'&&u.pathname.endsWith('/receipt-candidates')){drop=false;assert.equal(r.status,201);const made=await r.clone().json();if(info.fake==='wrong_id')return new Response(JSON.stringify({...made,id:info.target}),{status:201,headers:{'Content-Type':'application/json'}});if(info.fake==='wrong_type')return new Response(JSON.stringify({...made,whole_task_accepted:0}),{status:201,headers:{'Content-Type':'application/json'}});throw Error('Owned receipt loss after accepted candidate');}return r;};
 for(const tag of w.document.querySelectorAll('script[src]')){const name=tag.getAttribute('src'),text=await(await fetch(info.base+name)).text();loaded[name]=crypto.createHash('sha256').update(text).digest('hex');vm.runInContext(text,dom.getInternalVMContext());}
 $('token').value='synthetic-test-A';await click('connect');}
const posts=()=>requests.filter(x=>x.method==='POST').length;
(async()=>{try{
 await load();const before=posts();await w.showRun(info.run);
 check(posts()===before,'history and receipt options readonly zero POST');
 check($('natural-receipt-candidate').textContent.includes('Run PARTIAL')&&$('natural-receipt-candidate').textContent.includes('完整 P-B 未验收'),'partial source and whole-task nonacceptance visible');
 check($('natural-receipt-candidate').textContent.includes('column')&&$('natural-receipt-candidate').textContent.includes('aggregate_csv@1'),'variable and stable step explicit');
 $('natural-receipt-target').value=info.target;$('natural-receipt-target').onchange();$('natural-receipt-name').value='UI provisional candidate';$('natural-receipt-name').oninput();
 await click('natural-receipt-extract');check($('natural-receipt-extract').textContent.includes('恢复原候选'),'lost or invalid accepted receipt retains original UNKNOWN recovery');await click('natural-receipt-extract');
 const extraction=requests.filter(x=>x.method==='POST'&&x.path.endsWith('/receipt-candidates'));check(extraction.length===2&&extraction[0].body===extraction[1].body,'same frozen extraction key/body after receipt loss');
 await click('natural-receipt-extract');const aid=w.eval('activeApp');
 check($('app-origin').textContent.includes('来源 Run PARTIAL')&&$('app-origin').textContent.includes('完整 P-B 未验收'),'saved candidate never labels whole source successful');
 $('app-column').value='quantity';await $('app-preview-form').onsubmit({preventDefault(){}});
 check($('app-output').textContent.includes('15'),'new input computes actual15 not copied19');
 const count=posts();await load();await w.showApp(aid);check(posts()===count,'cold candidate and history read zero POST');
 check($('app-origin').textContent.includes('未验收'),'cold candidate limitation persists');
 $('app-column').value='bad';await $('app-preview-form').onsubmit({preventDefault(){}});check($('app-output').dataset.state==='error','bad nonnumeric input is current failure not previous success');
 assert.equal((await fetch(info.base+'/test-only-receipt-revoke',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).status,200);const protectedBefore=posts();let denied=false;try{await w.showApp(aid);}catch(e){denied=true;}
 check(denied&&w.eval('activeApp===null'),'source revocation rejects cold candidate and clears active app');check(posts()===protectedBefore,'revocation read does not resubmit');
 const result={status:'PASS',browser:'JSDOM_NOT_NATIVE',api:'ACTUAL_LOOPBACK_HTTP',checks,loaded_source_sha256:loaded,model_network:0,derived_app:aid};fs.writeFileSync(path.join(root,'results.json'),JSON.stringify(result,null,2));
 }catch(e){console.error(e.stack);process.exitCode=1;}finally{dom?.window.close();}})();
