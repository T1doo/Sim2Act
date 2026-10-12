'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{JSDOM}=require('jsdom');
const root=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(root,'info.json'))),checks=[],requests=[],hashes={};let dom,w,$,mode='',release,page,acceptedPlan;const lifecycle=[];
const check=(v,label)=>{assert(v,label);checks.push(label);};
const wait=async fn=>{const end=Date.now()+6000;while(Date.now()<end){if(fn())return;await new Promise(r=>setTimeout(r,10));}throw Error('bounded wait expired');};
async function idlePage(){
 if(!page)return;
 await wait(()=>page.requests===0&&page.actions.size===0,'page actions and HTTP drained');
 await new Promise(resolve=>setImmediate(resolve));
 if(page.errors.length)throw page.errors[0];
 assert.equal(page.requests,0);assert.equal(page.actions.size,0);
}
(async()=>{try{
 await setup();
 if(info.scenario==='unknown-plan'){await unknownPlan();return;}
 check(!$('manual-lock-panel').hidden,'existing canonical Report exposes manual edit protection');
 check(w.document.querySelector('.report-view-text').textContent==='ALLOW','actual archived decision remains the original display');
 const selectView=()=>{$('manual-lock-node').value=[...$('manual-lock-node').options].find(o=>o.textContent.startsWith('view:text:decision')).value;};
 await w.readDeliveryGraph();await w.manualRead();selectView();
 check(!!$('delivery-proof').textContent&&!requests.some(r=>r.path.endsWith('/column-patches')),'Report graph stays verified without unrelated CSV history');
 check($('manual-lock-submit').disabled,'Report lock requires explicit exact confirmation');
 $('manual-lock-confirm').checked=true;$('manual-lock-confirm').dispatchEvent(new w.Event('change'));
 check(!$('manual-lock-submit').disabled,'exact Report view may be explicitly confirmed');
 mode='lost';await w.manualSubmit();
 check(!$('manual-lock-retry').hidden&&$('manual-lock-status').textContent.includes('UNKNOWN'),'lost Report lock acceptance retains original frozen intent');
 await w.manualSubmit(true);
 const posts=requests.filter(r=>r.method==='POST'&&r.path.endsWith('/manual-locks'));
 check(posts.length===2&&JSON.stringify(posts[0].body)===JSON.stringify(posts[1].body),'Report lock restores the same accepted key and body');
 check($('manual-lock-retry').hidden&&!$('manual-lock-confirm').checked&&!$('delivery-proof').textContent,'accepted Report lock clears stale graph and confirmation');
 await w.submitDeliveryGraph('derive');await w.readDeliveryGraph();await w.manualRead();selectView();
 check($('manual-lock-node').selectedOptions[0].textContent.includes('已锁定'),'rederived Report view displays actual durable lock');
 w.document.querySelector('.report-presentation-propose').click();await idlePage();
 check(w.document.querySelector('.report-presentation-controls').textContent.includes('LOCK_CONFLICT'),'original Report presentation plan refuses locked view');
 check(!requests.some(r=>r.method==='POST'&&r.path.endsWith('/report-presentations')),'blocked plan never proceeds to a Report presentation write');
 await w.readDeliveryGraph();await w.manualRead();selectView();
 $('manual-lock-target').value='false';$('manual-lock-target').dispatchEvent(new w.Event('change'));
 check(!$('manual-lock-confirm').checked,'Report unlock selection clears previous confirmation');
 $('manual-lock-confirm').checked=true;$('manual-lock-confirm').dispatchEvent(new w.Event('change'));
 await w.manualSubmit();await w.submitDeliveryGraph('derive');
 await w.readDeliveryGraph();await w.manualRead();
 check($('manual-lock-history').textContent.includes('SUPERSEDED'),'same Report page distinguishes historical lock from current unlock');
 w.document.querySelector('.report-presentation-propose').click();await idlePage();
 const confirm=w.document.querySelector('.report-presentation-confirm');
 check(!confirm.hidden&&!confirm.disabled,'same page new exact Report plan permits explanation check after unlock');
 confirm.click();await idlePage();
 check([...w.document.querySelectorAll('.report-view-text')].some(e=>e.textContent===info.explanation)&&!w.reportExecuted,'actual archived explanation safely renders after original finite readback');
 check(w.document.querySelector('.report-presentation-controls').textContent.includes('PROJECT BLOCKED_PARTIAL'),'Report project revalidation and whole acceptance remain blocked');
 const writes=requests.filter(r=>r.method==='POST').length;
 await setup();await w.readDeliveryGraph();await w.manualRead();
 check(requests.filter(r=>r.method==='POST').length===writes,'cold Report graph, locks and presentation history read without writes');
 if(info.scenario==='aba'){
  $('manual-lock-confirm').checked=true;mode='hold';const late=w.manualRead();await wait(()=>release);
  const resume=release;$('project-select').value=info.other;w.clearApp();$('project-select').value=info.project;await w.showApp(info.app);resume();await late;
  check(!$('manual-lock-confirm').checked&&!$('manual-lock-history').textContent,'same Report project ABA rejects delayed old lock state');
  await w.readDeliveryGraph();await w.manualRead();check($('manual-lock-history').textContent.includes('SUPERSEDED'),'explicit current Report read restores authorized durable history');
 }
 await idlePage();fs.writeFileSync(path.join(root,'results.json'),JSON.stringify({status:'PASS',checks,requests,loaded_source_sha256:hashes,model_requests:0,business_writes:0,native:'NOT_RUN'},null,2));console.log(JSON.stringify({status:'PASS',checks:checks.length}));
}catch(e){fs.writeFileSync(path.join(root,'failure.json'),JSON.stringify({status:'FAIL',checks,error:e.message,requests},null,2));console.error(e.stack);process.exitCode=1;}finally{await closePage();}})();
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
async function unknownPlan(){
 const propose=()=>w.document.querySelector('.report-presentation-propose');
 mode='lost-plan';propose().click();await idlePage();
 check(!!acceptedPlan&&acceptedPlan.receipt.patch_executed===false,'actual server accepted and sealed Report plan before its response was lost');
 check(w.eval('presentationIntents.size')===1&&propose().textContent.includes('原键'),'lost accepted plan retains original recoverable intent');
 const first=requests.find(r=>r.method==='POST'&&r.path.endsWith('/plans'));
 const peerBase=`/api/projects/${info.project}/apps/${info.peer.id}/delivery-graph`;
 const call=async(p,method='GET',body)=>{const r=await fetch(info.base+p,{method,headers:{Authorization:'Bearer synthetic-test-A','Content-Type':'application/json'},body:body&&JSON.stringify(body)});const value=await r.json();assert(r.ok,JSON.stringify(value));return value;};
 const graph=await call(peerBase),node=graph.graph.nodes.find(n=>n.kind==='VIEW');
 const locked=await call(peerBase+'/manual-locks','POST',{expected_graph_fingerprint:graph.graph_fingerprint,expected_graph_revision:graph.graph_revision,change:{node_id:node.id,expected_revision:node.revision,expected_content_fingerprint:node.content_fingerprint},expected_lock_revision:0,locked:true,request_key:'unknown-peer-lock',consent:'CONFIRM_EXACT_PROJECT_EDIT_LOCK'});
 check(locked.lock.locked===true,'another existing app in actual PROJECT is publicly locked');
 const derived=await call(peerBase+'/derive','POST',{expected_candidate_fingerprint:info.peer.fingerprint,request_key:'unknown-peer-locked-derive'});
 check(derived.graph.nodes.find(n=>n.id===node.id).locked===true,'peer lock participates in newly verified project expansion');
 propose().click();await idlePage();
 const plans=requests.filter(r=>r.method==='POST'&&r.path.endsWith('/plans'));
 check(plans.length===2&&JSON.stringify(plans[0].body)===JSON.stringify(plans[1].body),'later lock rejection uses exact original accepted plan body and key');
 check(w.document.querySelector('.report-presentation-controls').textContent.includes('LOCK_CONFLICT'),'real later PROJECT lock rejects same-key plan replay');
 check(w.eval('presentationIntents.size')===1&&propose().textContent.includes('原键'),'later rejection preserves earlier UNKNOWN instead of releasing intent');
 check(!requests.some(r=>r.method==='POST'&&r.path.endsWith('/report-presentations')),'UNKNOWN recovery never advances to a presentation write');
 const lockedNode=derived.graph.nodes.find(n=>n.id===node.id);
 const unlocked=await call(peerBase+'/manual-locks','POST',{expected_graph_fingerprint:derived.graph_fingerprint,expected_graph_revision:derived.graph_revision,change:{node_id:lockedNode.id,expected_revision:lockedNode.revision,expected_content_fingerprint:lockedNode.content_fingerprint},expected_lock_revision:1,locked:false,request_key:'unknown-peer-unlock',consent:'CONFIRM_EXACT_PROJECT_EDIT_LOCK'});
 check(unlocked.lock.locked===false,'actual peer unlock is separately confirmed and persisted');
 await call(peerBase+'/derive','POST',{expected_candidate_fingerprint:info.peer.fingerprint,request_key:'unknown-peer-unlocked-derive'});
 propose().click();await idlePage();
 check(requests.filter(r=>r.method==='POST'&&r.path.endsWith('/plans')).every(r=>JSON.stringify(r.body)===JSON.stringify(first.body))&&w.eval('presentationIntents.size')===1,'changed project expansion still retains original UNKNOWN key for explicit recovery');
 fs.writeFileSync(path.join(root,'results.json'),JSON.stringify({status:'PASS',checks,requests,accepted_plan:acceptedPlan,loaded_source_sha256:hashes,model_requests:0,business_writes:0,native:'NOT_RUN'},null,2));
 console.log(JSON.stringify({status:'PASS',checks:checks.length}));
}
async function setup(){await closePage();const html=await(await fetch(info.base)).text();hashes['index.html']=crypto.createHash('sha256').update(html).digest('hex');dom=new JSDOM(html,{url:info.base,runScripts:'dangerously'});w=dom.window;$=id=>w.document.getElementById(id);page={requests:0,actions:new Set(),errors:[]};trackHandlers(w,page);w.setInterval=()=>0;const current=page;w.TextEncoder=TextEncoder;Object.defineProperty(w.crypto,'subtle',{value:crypto.webcrypto.subtle});w.crypto.randomUUID=()=>crypto.randomUUID();
 w.fetch=async(url,opts={})=>{current.requests++;try{const target=new URL(url,info.base);assert.equal(target.origin,info.base);const r={path:target.pathname,method:opts.method||'GET',body:opts.body&&JSON.parse(opts.body)};requests.push(r);const response=await fetch(target,opts);if(mode==='lost'&&r.method==='POST'&&r.path.endsWith('/manual-locks')){mode='';throw Error('controlled lost accepted response');}if(mode==='lost-plan'&&r.method==='POST'&&r.path.endsWith('/plans')){mode='';assert.equal(response.status,201);acceptedPlan=await response.json();throw Error('controlled lost accepted plan response');}if(mode==='hold'&&r.path.endsWith('/manual-locks')&&r.method==='GET'){mode='';await new Promise(r=>release=r);release=null;}const bytes=await response.arrayBuffer();return new Response(bytes,{status:response.status,headers:response.headers});}finally{current.requests--;}};
 for(const name of Array.from(w.document.querySelectorAll('script[src]')).map(s=>s.getAttribute('src').slice(1))){const code=await(await fetch(info.base+'/'+name)).text();hashes[name]=crypto.createHash('sha256').update(code).digest('hex');const script=w.document.createElement('script');script.textContent=code;w.document.body.append(script);}
 $('token').value='synthetic-test-A';$('connect').click();await wait(()=>$('project-select').value===info.project&&$('login').hidden);await idlePage();await w.showApp(info.app);
}
