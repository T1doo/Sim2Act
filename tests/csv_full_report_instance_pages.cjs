'use strict';
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),requests=[],checks=[],assets=[],pending=new Map();let serial=0,dom,w,$,hold=null,release=null,dropPath=null,dropStage=null;
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
async function project(id){$('project-select').value=id;await action('project-select','change');}
async function nav(tab){await action(w.document.querySelector(`#workspace-nav [data-tab="${tab}"]`));}
async function source(){const node=[...$('runs').children].find(r=>r.textContent.includes(info.run.slice(0,16)));assert(node);await action(node.querySelector('button'));}
const saves=()=>requests.filter(r=>r.method==='POST'&&r.path.endsWith('/csv-full-report-workflows'));
const uses=()=>requests.filter(r=>r.method==='POST'&&r.path.endsWith('/csv-full-report-uses'));
async function boot(){
 const load=async path=>{const r=await rpc({method:'GET',path});assert.equal(r.status,200);assets.push({path,sha256:crypto.createHash('sha256').update(r.text).digest('hex')});return r.text;};
 dom=new JSDOM(await load('/'),{url:'http://testserver/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 w.Blob=Blob;w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.setInterval=()=>0;
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.URL.createObjectURL=blob=>{downloads.push(blob);return 'blob:synthetic-download';};w.URL.revokeObjectURL=url=>revocations.push(url);w.HTMLAnchorElement.prototype.click=function(){downloads.push({name:this.download,href:this.href});};
 w.fetch=async(path,options={})=>{const request={method:options.method||'GET',path,body:options.body?JSON.parse(options.body):undefined,started_ms:performance.now()};requests.push(request);
  const r=await rpc({...request,headers:options.headers});request.status=r.status;request.response=JSON.parse(r.text);request.http_finished_ms=performance.now();
  if(hold===path){hold=null;await new Promise(resolve=>{release=resolve;});}
  if(dropPath===path&&request.method==='POST'){dropPath=null;request.delivery=`ACTUAL_${r.status}_LOST:${dropStage}`;throw Error('Synthetic lost actual '+dropStage+' response');}
  request.delivered_ms=performance.now();return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
 };
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(script.getAttribute('src'));w.document.body.append(node);}
 $('token').value='synthetic-test-A';await action('connect');await project(info.project);await source();
 check(visible($('csv-full-report-extraction'))&&$('csv-full-report-extraction').textContent.includes('完整MD'),'completed original report exposes complete workflow extraction');
 check(saves().length===0&&uses().length===0,'opening source makes no workflow or use POST');
}
async function save(){
 await action('csv-full-report-options');check($('csv-full-report-save').disabled&&!$('csv-full-report-save-ack').checked,'saving requires explicit complete-workflow consent');
 $('csv-full-report-name').value='可复用完整MD <script>window.fullUnsafe=true</script>';$('csv-full-report-name').oninput();await action('csv-full-report-save-ack');
 hold=`/api/runs/${info.run}/csv-full-report-workflows`;const panel=$('csv-full-report-extraction'),button=$('csv-full-report-save'),sending=action(button);await button.onclick(new w.Event('click'));await wait(()=>release,'actual save response held');
 await w.showRun(info.run,false);check($('csv-full-report-extraction')===panel&&$('csv-full-report-save').disabled,'same Run background redraw preserves in-flight source view');const finish=release;release=null;finish();await sending;check(saves().length===1&&!$('csv-full-report-directory').hidden,'one saved recipe settles the current redraw and enables directory');
 await action('csv-full-report-directory');const aid=saves()[0].response.id;
 const node=[...$('use-list').children].find(r=>r.dataset.appId===aid);check(node?.dataset.useFamily==='CSV_FULL_REPORT'&&node.textContent.includes('完整MD'),'unified saved-use directory classifies complete report separately from sum');await action(node.querySelector('button'));
 check(visible($('csv-full-report-use'))&&$('app-origin').textContent.includes('受限内部Release'),'saved recipe opens usable input form with honest version scope');
 check(w.fullUnsafe===undefined,'saved name remains inert text');return aid;
}
async function configure(){
 $('csv-full-report-material').value=info.material;await action('csv-full-report-material','change');
 check([...$('csv-full-report-column').options].some(o=>o.value==='quantity'),'new material numeric columns are loaded from actual authorization');
 $('csv-full-report-column').value='quantity';await action('csv-full-report-column','change');check(!$('csv-full-report-use-ack').checked&&$('csv-full-report-prepare').disabled,'new material and column require explicit preparation consent');await action('csv-full-report-use-ack');
}
const downloads=[],revocations=[],diagnostics={};
let aid,root,firstRelease,firstInstance,run;
const postAt=path=>requests.filter(r=>r.method==='POST'&&r.path===path);
async function recipe(){
 if(!visible($('apps')))await nav('apps');
 const node=[...$('use-list').children].find(r=>r.dataset.appId===aid);assert(node);await action(node.querySelector('button'));
 check(visible($('csv-full-report-delivery')),'same saved workflow exposes visible internal delivery controls');
}
async function returnRecipe(){await nav('resources');await nav('apps');await recipe();}
async function readDelivery(){
 const mark=requests.length;await action('csv-full-report-delivery-read');
 check(requests.slice(mark).every(r=>r.method==='GET'),'delivery directory refresh is read-only');
}
async function selectRelease(id){$('csv-full-report-release-select').value=id;await action('csv-full-report-release-select','change');}
async function selectInstance(id){
 $('csv-full-report-instance-select').value=id;await action('csv-full-report-instance-select','change');
 check(w.eval('csvFullReportView.instance?.id')===id,'explicit instance selection reads and installs exact current instance');
 check(!$('csv-full-report-use-ack').checked&&$('csv-full-report-prepare').disabled,'instance selection clears old material consent and does not prepare a Run');
}
async function input(resource=info.material){
 $('csv-full-report-material').value=resource;await action('csv-full-report-material','change');
 check([...$('csv-full-report-column').options].some(o=>o.value==='quantity'),'actual selected fresh CSV supplies numeric quantity option');
 $('csv-full-report-column').value='quantity';await action('csv-full-report-column','change');
 check(!$('csv-full-report-use-ack').checked&&$('csv-full-report-prepare').disabled,'fresh CSV and column require explicit per-use consent');await action('csv-full-report-use-ack');
}
async function doubleClick(id){const b=$(id),sending=action(b);await b.onclick(new w.Event('click'));await sending;}
async function lost(id,path,status,stage,expectedGet,beforeRelease=null){
 const before=postAt(path).length;hold=path;dropPath=path;dropStage=stage;
 const button=$(id),sending=action(button);await button.onclick(new w.Event('click'));await wait(()=>release,'actual '+stage+' response held');
 const accepted=postAt(path).at(-1);check(accepted.status===status,'loss starts after actual '+stage+' accepted status');
 await returnRecipe();if(beforeRelease)await beforeRelease(accepted);
 const done=release;release=null;done();await sending;
 await wait(()=>visible($(id))&&!$(id).disabled,'current same-owner original-key '+stage+' recovery enabled');
 const mark=requests.length;await action(id);const recovery=requests.slice(mark);
 check(recovery.length>0&&recovery.every(r=>r.method==='GET'),'lost '+stage+' uses GET only and never automatically writes');
 check(recovery.some(r=>r.path===expectedGet(accepted)&&r.status===200),'lost '+stage+' reads exact original accepted key');
 check(postAt(path).length===before+1&&accepted.delivery===`ACTUAL_${status}_LOST:${stage}`,'double click/loss/navigation preserves one actual '+stage+' POST');
 (diagnostics.losses||=[]).push({stage,path,status,body:accepted.body,expected_get:expectedGet(accepted),recovery});return accepted;
}
async function releaseVersion(second=false){
 if(second){const count=postAt(root+'/release-approvals').length;await action('csv-full-report-release-new');check(postAt(root+'/release-approvals').length===count,'explicit next same-recipe intent does not automatically prepare or commit');}
 let posted;
 if(info.case==='lost'&&!second)posted=await lost('csv-full-report-release-prepare',root+'/release-approvals',201,'release-prepare',p=>root+'/release-requests/'+p.body.request_key);
 else{await doubleClick('csv-full-report-release-prepare');posted=postAt(root+'/release-approvals').at(-1);}
 check(postAt(root+'/release-approvals').length===(second?2:1),'one actual Release approval for each explicit request');
 const approval=posted.response;
 check(!$('csv-full-report-release-ack').checked&&$('csv-full-report-release-commit').disabled,'complete Release approval requires new visible commit consent');
 const shown=JSON.parse($('csv-full-report-delivery-proof').textContent);assert.deepEqual(shown.approval,approval);checks.push('visible Release proof equals complete actual server approval');
 await action('csv-full-report-release-ack');
 const path=`/api/internal/approvals/${approval.id}/commit`;
 if(info.case==='lost'&&!second)await lost('csv-full-report-release-commit',path,200,'release-commit',()=>root+'/release-requests/'+posted.body.request_key);
 else await doubleClick('csv-full-report-release-commit');
 check(postAt(path).length===1,'explicit internal Release commit sent once');
 const receipt=requests.filter(r=>r.method==='GET'&&r.path===root+'/release-requests/'+posted.body.request_key&&r.response.release).at(-1).response;
 check(receipt.release.approval_id===approval.id&&receipt.release.snapshot.definition_version===1,'saved Release is exact approved immutable v1 complete-MD recipe');
 return receipt.release;
}
async function createInstance(releaseValue){
 await selectRelease(releaseValue.id);check(!$('csv-full-report-instance-ack').checked&&$('csv-full-report-instance-create').disabled,'selected Release requires explicit instance creation consent');await action('csv-full-report-instance-ack');
 const path=`/api/internal/releases/${releaseValue.id}/instances`;let posted;
 if(info.case==='lost')posted=await lost('csv-full-report-instance-create',path,201,'instance-create',p=>root+'/instance-requests/'+releaseValue.id+'/'+p.body.request_key,async()=>{await readDelivery();await selectRelease(releaseValue.id);check($('csv-full-report-instance-create').disabled,'returned in-flight create intent remains locked');});
 else{await doubleClick('csv-full-report-instance-create');posted=postAt(path).at(-1);}
 check(postAt(path).length===1,'one visible create action creates exactly one instance');
 const iid=posted.response.id;check($('csv-full-report-instance-select').value===''&&w.eval('csvFullReportView.instance')===null,'creating an instance does not implicitly select or run it');return iid;
}
async function prepareUse(){
 const path=`/api/internal/instances/${firstInstance}/csv-full-report-uses`;let posted;
 await input();
 if(info.case==='lost')posted=await lost('csv-full-report-prepare',path,202,'instance-use',p=>`/api/internal/instances/${firstInstance}/csv-full-report-requests/${p.body.request_key}`,async()=>{await readDelivery();await selectInstance(firstInstance);check($('csv-full-report-prepare').disabled,'returned in-flight instance use remains locked');});
 else{await doubleClick('csv-full-report-prepare');posted=postAt(path).at(-1);}
 check(postAt(path).length===1,'double click queues one original ordinary CSV report contract');
 const receipt=posted.response;check(receipt.instance_id===firstInstance&&receipt.release_id===firstRelease.id&&receipt.revision===1&&receipt.request_fingerprint===await w.eval('ownerHash')(posted.body),'instance receipt binds exact original body fingerprint and selected Release');
 run=receipt.run_id;check(run!==info.run&&!requests.some(r=>r.method==='POST'&&r.path===`/api/runs/${run}/confirm-csv-report`),'new contract has not executed or confirmed tools');
 await action('csv-full-report-open-run');
 check(w.eval('activeRun')===run&&visible($('csv-report-preview'))&&$('csv-report-preview').textContent.includes('精确合计：15')&&!$('csv-report-ack').checked,'instance use opens same new ordinary Run with complete MD preview and fresh execution consent');
 const ordinary=requests.filter(r=>r.method==='GET'&&r.path===`/api/runs/${run}`&&r.status===200).at(-1).response;
 const old=ordinary.events.filter(e=>e.kind==='CSV_FULL_REPORT_USE'),instance=ordinary.events.filter(e=>e.kind==='CSV_FULL_REPORT_INSTANCE_USE');
 check(old.length===1&&instance.length===1&&old[0].data.workflow_id===aid&&instance[0].data.app_run_id===receipt.app_run_id&&instance[0].data.request_fingerprint===receipt.request_fingerprint,'actual ordinary Run keeps separate unchanged workflow and exact instance provenance events');return receipt;
}
async function finishAndDownload(){
 await action('csv-report-ack');await wait(()=>!$('csv-report-confirm').disabled,'exact complete contract consent reread');await doubleClick('csv-report-confirm');
 check(postAt(`/api/runs/${run}/confirm-csv-report`).length===1,'complete ordinary contract is confirmed once by explicit action');
 await rpc({command:'worker',run});await action('run-history-refresh');await action([...$('runs').children].find(r=>r.textContent.includes(run.slice(0,16))).querySelector('button'));
 check($('result').textContent.includes('PASS')&&$('result').textContent.includes('人工 PENDING'),'exact same Run distinguishes complete contract PASS from pending human acceptance');
 await action([...$('run-artifacts').querySelectorAll('button')].find(b=>b.textContent==='下载此成果'));
 const actual=requests.filter(r=>r.method==='GET'&&r.path===`/api/runs/${run}`&&r.status===200).at(-1).response,spec=actual.contract.snapshot.ordinary_csv_report,saved=actual.result.receipts.at(-1).data;
 const bytes=Buffer.from(await downloads[0].arrayBuffer()),hash=crypto.createHash('sha256').update(bytes).digest('hex');
 check(downloads.length===2&&bytes.equals(Buffer.from(spec.report_text,'utf8'))&&hash===spec.report_hash&&hash===saved.hash,'actual Blob equals exact new ordinary Run complete MD and saved resource hash');
 await wait(()=>revocations.includes(downloads[1].href),'MD object URL reclaimed');check(downloads[1].name.includes(run)&&downloads[1].name.includes(saved.resource_id),'MD filename binds same Run and result resource');fs.writeFileSync(info.output.replace('.json','.download.md'),bytes);
 return actual;
}
async function adoptSecond(){
 await recipe();await readDelivery();await selectInstance(firstInstance);
 const before=postAt(`/api/internal/instances/${firstInstance}/csv-full-report-uses`).length,second=await releaseVersion(true);
 check(second.id!==firstRelease.id&&second.fingerprint===firstRelease.fingerprint,'second internal Release is independently approved same immutable recipe, not a new definition version');
 $('csv-full-report-switch-target').value=second.id;await action('csv-full-report-switch-target','change');
 check(!$('csv-full-report-switch-prepare-ack').checked&&$('csv-full-report-switch-prepare').disabled,'target selection requires fresh separate adoption preparation consent');
 await action('csv-full-report-switch-prepare-ack');await doubleClick('csv-full-report-switch-prepare');
 const path=`/api/internal/instances/${firstInstance}/csv-full-report-switch-approvals`,approved=postAt(path).at(-1);check(postAt(path).length===1,'one adoption approval after explicit consent');
 const shown=JSON.parse($('csv-full-report-delivery-proof').textContent);assert.equal(shown.approval.id,approved.response.id);assert.deepEqual(shown.approval.payload,approved.response.payload);checks.push('visible adoption proof equals full exact server-frozen payload');
 check(!$('csv-full-report-switch-ack').checked&&$('csv-full-report-switch-commit').disabled,'adoption approval cannot automatically commit');await action('csv-full-report-switch-ack');await doubleClick('csv-full-report-switch-commit');
 const commit=`/api/internal/instances/${firstInstance}/csv-full-report-switch-requests/${approved.body.request_key}/commit`;check(postAt(commit).length===1,'explicit adoption commits original key once');
 check($('csv-full-report-instance-select').value===''&&w.eval('csvFullReportView.instance')===null&&!$('csv-full-report-use-ack').checked,'adoption fresh-read clears prior instance/use selection and consent');
 check(postAt(`/api/internal/instances/${firstInstance}/csv-full-report-uses`).length===before,'adoption does not automatically prepare another ordinary Run');
 await selectInstance(firstInstance);const value=JSON.parse($('csv-full-report-use-binding').textContent);
 check(value.instance.release_id===second.id&&value.instance.revision===2&&value.instance.data_version===1,'adopted current instance preserves saved result version');
 const old=[...$('csv-full-report-history').children].find(n=>n.textContent.includes(run));check(!!old,'old exact Run remains reachable from selected adopted instance history');await action(old.querySelector('button'));
 check(w.eval('activeRun')===run&&$('result').textContent.includes('PASS'),'historical Run still opens with its original Release and full MD');return second;
}
async function navigation(){
 const other=await rpc({command:'second-instance',release:firstRelease.id});const second=JSON.parse(other.text).id;
 await readDelivery();await selectInstance(firstInstance);
 hold=`/api/resources/${info.material}/csv-report-columns`;$('csv-full-report-material').value=info.material;const reading=action('csv-full-report-material','change');await wait(()=>release,'actual first-instance material GET held');
 await selectInstance(second);const finish=release;release=null;finish();await reading;
 check(w.eval('csvFullReportView.instance.id')===second&&$('csv-full-report-column').options.length===0&&!$('csv-full-report-use-ack').checked,'late material callback cannot install inputs into another selected instance');
 await selectInstance(firstInstance);await input();let path=`/api/internal/instances/${firstInstance}/csv-full-report-uses`;hold=path;let sending=action('csv-full-report-prepare');await wait(()=>release,'actual instance A use202 held');const first=postAt(path).at(-1);
 await nav('projects');await project(info.other);const projectMark=requests.length,done=release;release=null;done();await sending;
 check(!visible($('csv-full-report-use'))&&w.eval('activeApp===null'),'late actual accepted instance Run cannot populate another project');
 check(!requests.slice(projectMark).some(r=>r.method==='GET'&&r.path===`/api/internal/instances/${firstInstance}/csv-full-report-requests/${first.body.request_key}`),'late project acceptance makes no old-scope follow-up receipt GET');
 await project(info.project);await nav('apps');await recipe();await readDelivery();
 hold=root;$('csv-full-report-instance-select').value=second;const selecting=action('csv-full-report-instance-select','change');await wait(()=>release,'actual instance B directory selection held');
 check(w.eval('csvFullReportView.deliveryPending')&&$('csv-full-report-open-run').hidden&&$('csv-full-report-history').children.length===0,'pending instance authorization exposes neither old workflow history nor its open control');
 const selected=release;release=null;selected();await selecting;
 check(w.eval('csvFullReportView.instance.id')===second,'pending instance selection installs only its fresh exact instance');await input(info.next_material);
 path=`/api/internal/instances/${second}/csv-full-report-uses`;hold=path;sending=action('csv-full-report-prepare');await wait(()=>release,'actual instance B use202 held');const last=postAt(path).at(-1);
 await action('identity-switch');$('token').value='synthetic-test-B';await action('connect');const accountMark=requests.length,replied=release;release=null;replied();await sending;
 check(w.eval('activeApp===null&&activeRun===null')&&!visible($('csv-full-report-use')),'late accepted new instance Run cannot populate another account');
 check(!requests.slice(accountMark).some(r=>r.method==='GET'&&r.path===`/api/internal/instances/${second}/csv-full-report-requests/${last.body.request_key}`),'late account acceptance makes no follow-up GET using new identity');
 for(const [sent,iid]of [[first,firstInstance],[last,second]])check(sent.status===202&&sent.response.instance_id===iid&&sent.response.request_key===sent.body.request_key&&sent.response.request_fingerprint===await w.eval('ownerHash')(sent.body),'each actual accepted receipt binds its own instance and exact original body');
 check(first.body.resource_id!==last.body.resource_id&&first.body.request_key!==last.body.request_key&&first.response.run_id!==last.response.run_id,'instance/material/key/ordinary Run scopes stay independent');
 diagnostics.navigation={first,second:last};return {first:first.response.run_id,second:last.response.run_id};
}
(async()=>{let delivery=null;try{
 await boot();aid=await save();root=`/api/apps/${aid}/csv-full-report-delivery`;await readDelivery();
 check(!requests.some(r=>r.method==='POST'&&r.path.startsWith(root)),'opening and reading saved delivery does not approve, create or run');
 firstRelease=await releaseVersion();firstInstance=await createInstance(firstRelease);await selectInstance(firstInstance);
 if(info.case==='navigation')delivery=await navigation();else{
  const receipt=await prepareUse();
  if(info.case==='deliver'){const actual=await finishAndDownload(),secondRelease=await adoptSecond();delivery={aid,instance:firstInstance,release:firstRelease.id,second_release:secondRelease.id,run,receipt,actual};}
  else{check(!requests.some(r=>r.method==='POST'&&r.path===`/api/runs/${run}/confirm-csv-report`),'lost use recovery still leaves explicit ordinary execution unconfirmed');delivery={aid,instance:firstInstance,release:firstRelease.id,run,receipt};}
 }
 await wait(()=>requests.every(r=>Number.isInteger(r.status)),'all actual API replies settle');
 fs.writeFileSync(info.output,JSON.stringify({status:'PASS',case:info.case,browser:'JSDOM_NOT_NATIVE',checks,assets,requests,delivery,diagnostics,downloads:downloads.map(x=>({name:x.name,size:x.size})),revocations,real_model_requests:0},null,2));
 }catch(error){fs.writeFileSync(info.output,JSON.stringify({status:'FAIL',error:error.stack,checks,assets,requests,delivery,diagnostics},null,2));console.error(error.stack);process.exitCode=1;}finally{dom?.window.close();process.stdout.write(JSON.stringify({done:true})+'\n');}})();
