'use strict';
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),requests=[],checks=[],assets=[],pending=new Map();let serial=0,dom,w,$,drop=false,hold=null,release=null;
readline.createInterface({input:process.stdin}).on('line',line=>{const r=JSON.parse(line),resolve=pending.get(r.id);assert(resolve);pending.delete(r.id);resolve(r);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+'\n');});
const wait=async(fn,label)=>{const until=Date.now()+12000;while(Date.now()<until){if(fn())return;await new Promise(r=>setTimeout(r,5));}throw Error('bounded wait: '+label);};
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
function visible(el){if(!el?.isConnected)return false;for(let p=el;p;p=p.parentElement)if(p.hidden||w.getComputedStyle(p).display==='none')return false;return true;}
async function action(el,type='click'){
 if(typeof el==='string')el=$(el);assert(visible(el),'visible '+(el?.id||el?.textContent));assert(!el.matches(':disabled'),'enabled '+el.id);const work=[],restore=[];
 for(const [node,name]of [[el,type==='change'?'onchange':'onclick'],[type==='click'?el.form:null,'onsubmit']]){const fn=node?.[name];if(typeof fn!=='function')continue;const wrap=function(e){const p=fn.call(this,e);work.push(Promise.resolve(p));return p;};node[name]=wrap;restore.push(()=>{if(node[name]===wrap)node[name]=fn;});}
 try{if(type==='click')el.click();else el.dispatchEvent(new w.Event(type,{bubbles:true}));await Promise.all(work);}finally{restore.forEach(fn=>fn());}
}
async function nav(tab){await action(w.document.querySelector(`#workspace-nav [data-tab="${tab}"]`));}
async function boot(){
 const load=async path=>{const r=await rpc({method:'GET',path});assert.equal(r.status,200);assets.push({path,sha256:crypto.createHash('sha256').update(r.text).digest('hex')});return r.text;};
 dom=new JSDOM(await load('/'),{url:'http://testserver/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.setInterval=()=>0;
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{const request={method:options.method||'GET',path,body:options.body?JSON.parse(options.body):undefined};requests.push(request);const r=await rpc({...request,headers:options.headers});request.status=r.status;request.response=JSON.parse(r.text);
  if(drop&&request.method==='POST'&&path.endsWith('/csv-owner-review-requests')&&request.body.command==='DECIDE'){drop=false;assert.equal(r.status,201);request.delivery='ACTUAL_201_LOST';throw Error('Synthetic lost accepted response');}
  if(hold===path){hold=null;await new Promise(resolve=>{release=resolve;});}return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
 };
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(script.getAttribute('src'));w.document.body.append(node);}
 $('token').value='synthetic-test-A';await action('connect');$('project-select').value=info.project;await action('project-select','change');await nav('apps');
 const row=[...$('use-list').children].find(r=>r.dataset.instanceId===info.instance);assert(row);await action(row.querySelector('button'));
}
const posts=()=>requests.filter(r=>r.method==='POST'&&r.path.endsWith('/csv-owner-review-requests'));
async function runNew(){
 check(visible($('use-csv-review-optin'))&&!$('use-csv-review-optin').checked,'run scope opt-in starts unchecked');
 await action('use-csv-review-optin');$('use-column').value='quantity';await action('use-column','change');check(!$('use-csv-review-optin').checked,'first column change clears consent');await action('use-csv-review-optin');$('use-column').value='amount';await action('use-column','change');check(!$('use-csv-review-optin').checked&&$('use-csv-review-scope').textContent.includes('amount'),'second column change clears consent and updates exact preview');await action('use-csv-review-optin');await action('use-submit');const rid=w.eval('applicationUse.selected');
 check(requests.findLast(r=>r.method==='POST'&&r.path.endsWith('/runs')).body.csv_review==='FREEZE_SUM_ONLY_WITHOUT_MD','new Run explicitly freezes only sum scope before Worker');
 await rpc({command:'worker',run:rid});await action('use-refresh');check($('use-output').textContent.includes('SUCCEEDED'),'same Run technical success shown before human declaration');
 await action('csv-owner-read');check($('csv-owner-status').textContent.includes('PENDING')&&$('csv-owner-proof').textContent.includes(rid),'selected Run begins independent PENDING with exact evidence');
 await action('csv-owner-prepare');check(visible($('csv-owner-form'))&&!$('csv-owner-ack').checked,'prepare exposes explicit unselected human criteria');return rid;
}
async function fill(){for(const select of $('csv-owner-form').querySelectorAll('select')){check(select.value==='','no choice is preaccepted');select.value='ACCEPT';}for(const reason of $('csv-owner-form').querySelectorAll('textarea'))reason.value='Synthetic owner declaration, not real semantic validation';await action('csv-owner-ack');}
(async()=>{let rid;try{
 await boot();rid=await runNew();await fill();
 if(info.case==='navigation'){
  const path=`/api/internal/instances/${info.instance}/runs/${rid}/csv-owner-review`;
  hold=path;const submitting=action('csv-owner-decide');await wait(()=>release,'preflight held');await nav('resources');const finish=release;release=null;finish();await submitting;
  check(posts().filter(r=>r.body.command==='DECIDE').length===0,'workspace change during preflight prevents decision POST');await nav('apps');await wait(()=>visible($('csv-owner-read'))&&!$('csv-owner-read').disabled,'fresh workspace read');await action('csv-owner-read');check(visible($('csv-owner-form'))&&!$('csv-owner-ack').checked,'return restores prepared evidence without stuck unsent intent or acknowledgement');await fill();
  hold=path+'-requests';const sending=action('csv-owner-decide');await wait(()=>release,'actual accepted decision held');await action('identity-switch');$('token').value='synthetic-test-B';await action('connect');const done=release;release=null;done();await sending;
  check(w.eval('applicationUse===null')&&!visible($('csv-owner-review')),'late accepted declaration cannot install under another account');
 }else{
  if(info.case==='lost')drop=true;const button=$('csv-owner-decide');const sending=action(button);await button.form.onsubmit(new w.Event('submit'));await sending;
  check(posts().filter(r=>r.body.command==='DECIDE').length===1,'double click sends exactly one declaration POST');
  if(info.case==='lost'){
   check($('csv-owner-status').textContent.includes('未确认'),'actual201 loss preserves uncertain intent');await nav('resources');await nav('apps');await wait(()=>visible($('csv-owner-recover'))&&!$('csv-owner-recover').disabled,'original intent recovered on workspace return');await action('csv-owner-recover');
   check(requests.some(r=>r.method==='GET'&&r.path.includes('csv-owner-review?request_key='))&&posts().filter(r=>r.body.command==='DECIDE').length===1,'accepted lost receipt recovers by original key GET only');
  }
  check($('csv-owner-status').textContent.includes('ACCEPTED')&&$('use-output').textContent.includes('SUCCEEDED'),'human ACCEPTED remains separate from original technical status');
  check($('csv-owner-proof').textContent.includes('SUM_ONLY_WITHOUT_MD')&&$('csv-owner-proof').textContent.includes('"full_md_report_included": false'),'declared scope never includes source MD contract');
  if(info.case==='deliver'){
   await rpc({command:'revoke'});await action('csv-owner-read');check($('csv-owner-status').textContent.includes('STALE')&&!$('csv-owner-proof')&&!$('use-output').textContent&&!$('use-history').textContent&&visible($('csv-owner-stop')),'revocation clears protected results and keeps metadata stop');
   $('csv-owner-stop-reason').value='explicit synthetic revoke';await action('csv-owner-stop-ack');await action('csv-owner-stop');check($('csv-owner-status').textContent.includes('REVOKED'),'owner explicitly revokes declaration after material permission loss');
  }
 }
 fs.writeFileSync(info.output,JSON.stringify({status:'PASS',case:info.case,browser:'JSDOM_NOT_NATIVE',checks,assets,requests,rid,real_model_requests:0},null,2));
}catch(error){fs.writeFileSync(info.output,JSON.stringify({status:'FAIL',error:error.stack,checks,assets,requests,rid},null,2));console.error(error.stack);process.exitCode=1;}finally{dom?.window.close();process.stdout.write(JSON.stringify({done:true})+'\n');}})();
