'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),readline=require('node:readline'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),checks=[],requests=[],loaded={},pending=new Map();let serial=0,dom,w,$,mode='',fakeApproval=null,gate=null,releaseGate=null;
readline.createInterface({input:process.stdin}).on('line',line=>{const r=JSON.parse(line),p=pending.get(r.id);pending.delete(r.id);p(r);});
const rpc=q=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...q})+'\n');});
const check=(v,name)=>{assert(v,name);checks.push(name);};
const wait=async f=>{const deadline=Date.now()+30000;while(Date.now()<deadline){if(f())return;await new Promise(r=>setTimeout(r,5));}throw Error('bounded offline wait');};
const b=id=>$('project-version-'+id),posts=()=>requests.filter(q=>q.method==='POST').length;
async function setup(){if(dom)dom.window.close();dom=new JSDOM((await rpc({path:'/',method:'GET'})).text,{url:'http://offline.test/',runScripts:'dangerously'});w=dom.window;$=id=>w.document.getElementById(id);w.TextEncoder=TextEncoder;Object.defineProperty(w.crypto,'subtle',{value:crypto.webcrypto.subtle});w.setInterval=()=>0;
 w.fetch=async(url,opt={})=>{const q={path:url,method:opt.method||'GET',body:opt.body&&JSON.parse(opt.body),headers:opt.headers};requests.push(q);const r=await rpc(q);
  if(mode==='lose-commit'&&q.method==='POST'&&url===info.base+'/commit'||mode==='lose-run'&&q.method==='POST'&&/\/instances\/.*\/runs$/.test(url)){mode='';check(r.status===201||r.status===202,'lost response followed real accepted HTTP mutation');throw Error('independent lost response');}
  if(mode.startsWith('attack-')&&q.method==='GET'&&url===info.base+'/definition'){
   const data=JSON.parse(r.text),attack=mode.slice(7),entry=data.entries[0];mode='';fakeApproval=null;
   if(attack==='expiry'){data.issued_at+=1;data.expires_at+=1;}
   else {const x=entry.snapshot.execution_source;if(attack==='version')x.version='internal.csv-read-sum-report.v1';if(attack==='runtime')entry.snapshot.draft.runtime_id+='-invalid';if(attack==='source')x.source_hash='0'.repeat(64);if(attack==='plan')x.plan_fingerprint='0'.repeat(64);if(attack==='fence')x.fence+=1;if(attack==='receipts')x.receipt_fingerprints[0]='0'.repeat(64);if(attack==='run-version')x.run_version+=1;if(attack==='accepted')x.accepted_fingerprint='bad';if(attack==='default')x.default_column='amount';
    entry.snapshot_fingerprint=await w.deliveryDigest(entry.snapshot);fakeApproval=JSON.parse(JSON.stringify(info.approvals[entry.approval.id]));fakeApproval.payload.snapshot=entry.snapshot;fakeApproval.fingerprint=await w.deliveryDigest(fakeApproval.payload);entry.approval.fingerprint=fakeApproval.fingerprint;
   }const {preview_fingerprint,cached,...body}=data;data.preview_fingerprint=await w.deliveryDigest(body);r.text=JSON.stringify(data);
  }
  if(fakeApproval&&q.method==='GET'&&url==='/api/internal/approvals/'+fakeApproval.id)r.text=JSON.stringify(fakeApproval);
  if(mode==='gate-source'&&q.method==='GET'&&url.includes('/csv-dag/')){mode='';gate=true;await new Promise(resolve=>releaseGate=resolve);}
  return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
 };
 for(const node of [...w.document.querySelectorAll('script[src]')]){const name=node.getAttribute('src').slice(1),code=fs.readFileSync(path.join(info.web,name),'utf8');loaded[name]=crypto.createHash('sha256').update(code).digest('hex');const s=w.document.createElement('script');s.textContent=code;w.document.body.append(s);}
 $('token').value='synthetic-test-A';$('connect').click();await wait(()=>$('login').hidden&&$('project-select').value===info.project);await w.showApp(info.app);await w.readDeliveryGraph();$('project-column-key').value='project-binding';await $('project-column-read').onclick();check(!!b('read'),'saved actual parent overlay opens group controls');
}
function confirm(){b('confirm').checked=true;b('confirm').dispatchEvent(new w.Event('change'));}
async function reopen(){fakeApproval=null;await w.showApp(info.app);await w.readDeliveryGraph();$('project-column-key').value='project-binding';await $('project-column-read').onclick();}
(async()=>{try{
 await setup();await b('read').onclick();confirm();check(!b('commit').disabled,'exact approval and actual source receipts permit confirmation');
 for(const field of ['version','runtime','source']){mode='attack-'+field;const n=posts();await b('read').onclick();confirm();check(b('commit').disabled,'re-signed preview and matching forged approval '+field+' rejected by independent source/time proof');check(posts()===n,'malicious '+field+' recovery uses GET only');await reopen();}
 fs.writeFileSync(info.output,JSON.stringify({status:'PASS',checks,requests,loaded_source_sha256:loaded},null,2));dom.window.close();process.stdout.write(JSON.stringify({done:true})+'\n');process.exit(0);
 }catch(error){fs.writeFileSync(info.output,JSON.stringify({status:'FAIL',checks,requests,loaded_source_sha256:loaded,error:error.stack},null,2));if(dom)dom.window.close();process.stderr.write(error.stack+'\n');process.exit(1);}})();
