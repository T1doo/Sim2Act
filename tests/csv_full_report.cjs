'use strict';
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),requests=[],checks=[],assets=[],pending=new Map();let serial=0,dom,w,$,drop=false,swap=false,secondRunRevoke=null,hold=null,release=null;
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
 w.fetch=async(path,options={})=>{const request={method:options.method||'GET',path,body:options.body?JSON.parse(options.body):undefined};requests.push(request);if(secondRunRevoke&&request.method==='GET'&&path===`/api/runs/${secondRunRevoke.run}`){secondRunRevoke.count++;if(secondRunRevoke.count===2)await rpc({command:'revoke-output',resource:secondRunRevoke.resource});}const r=await rpc({...request,headers:options.headers});request.status=r.status;request.response=JSON.parse(r.text);
  if(drop&&request.method==='POST'&&path.endsWith('/csv-full-report-uses')){drop=false;assert.equal(r.status,202);request.delivery='ACTUAL_202_LOST';throw Error('Synthetic lost accepted response');}
  let delivered=r.text;if(swap&&request.method==='POST'&&path.endsWith('/csv-full-report-uses')){swap=false;assert.equal(r.status,202);delivered=JSON.stringify({...request.response,run_id:info.run});request.delivery='ACTUAL_202_SWAPPED_TO_OTHER_RUN';}
  if(hold===path){hold=null;await new Promise(resolve=>{release=resolve;});}return new Response(delivered,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
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
(async()=>{let delivery=null;try{
 await boot();
 if(info.case==='revoked-source'){
  await action('csv-full-report-options');check($('csv-full-report-save-proof').textContent.includes('source_report_hash'),'source proof is initially visible');await action('csv-full-report-save-ack');await rpc({command:'revoke-source'});await action('csv-full-report-save');
  check(saves().length===1&&saves()[0].status===403&&w.eval('activeRun===null')&&!$('csv-full-report-save-proof')&&!$('csv-report-preview')&&!$('run-artifacts'),'current source403 clears protected report proof and original Run canvas');
 }else{const aid=await save();
 if(info.case==='navigation'){
  hold=`/api/resources/${info.material}/csv-report-columns`;$('csv-full-report-material').value=info.material;const reading=action('csv-full-report-material','change');await wait(()=>release,'column response held');await nav('projects');await project(info.other);const done=release;release=null;done();await reading;
  check(!visible($('csv-full-report-use'))&&w.eval('activeApp===null'),'late material options cannot populate another project');
  await project(info.project);await nav('apps');let node=[...$('use-list').children].find(r=>r.dataset.appId===aid);await action(node.querySelector('button'));await configure();
  hold=`/api/apps/${aid}/csv-full-report-uses`;let sending=action('csv-full-report-prepare');await wait(()=>release,'actual use accepted response held');
  await nav('resources');await nav('apps');node=[...$('use-list').children].find(r=>r.dataset.appId===aid);await action(node.querySelector('button'));check($('csv-full-report-prepare').disabled,'same-owner reopened in-flight intent remains locked');let accepted=release;release=null;accepted();await sending;
  check(!$('csv-full-report-prepare').disabled&&$('csv-full-report-use-status').textContent.includes('原视图已离开'),'late original acceptance enables current same-owner original-key recovery without another POST');await action('csv-full-report-prepare');check(uses().length===1,'same-owner return recovers only GET');
  await action('csv-full-report-new-use');await configure();hold=`/api/apps/${aid}/csv-full-report-uses`;sending=action('csv-full-report-prepare');await wait(()=>release,'second actual use accepted response held');const run=uses()[1].response.run_id;

  await action('identity-switch');$('token').value='synthetic-test-B';await action('connect');const finish=release;release=null;finish();await sending;
  check(w.eval('activeApp===null&&activeRun===null')&&!visible($('csv-full-report-use')),'late actual accepted new Run cannot install under another account');check(uses().length===2,'two explicit uses produce exactly two POSTs');check(!requests.some(r=>r.method==='GET'&&r.path===`/api/apps/${aid}/csv-full-report-use-requests/${uses()[1].body.request_key}`),'late accepted response does not issue original account follow-up using another identity');delivery={aid,run};
 }else{
  await configure();if(info.case==='lost')drop=true;if(info.case==='misbound')swap=true;const button=$('csv-full-report-prepare'),sending=action(button);await button.onclick(new w.Event('click'));await sending;check(uses().length===1,'double click submits exactly one new contract');
  if(['lost','misbound'].includes(info.case)){
   check($('csv-full-report-use-status').textContent.includes('结果未知'),'lost or misbound actual202 cannot install a Run and remains UNKNOWN');check(w.eval('activeRun')===info.run,'wrong or lost receipt has not installed a different Run');await nav('resources');await nav('apps');const node=[...$('use-list').children].find(r=>r.dataset.appId===aid);await action(node.querySelector('button'));await action('csv-full-report-prepare');
   check(uses().length===1&&requests.some(r=>r.method==='GET'&&r.path.includes('/csv-full-report-use-requests/')),'return and explicit original-key GET recover without another POST');
  }
  const run=uses()[0].response.run_id;await action('csv-full-report-open-run');
  check(visible($('projects'))&&w.eval('activeRun')===run&&run!==info.run,'explicit open reaches same independent Run');
  check(visible($('csv-report-preview'))&&$('csv-report-preview').textContent.includes('精确合计：15')&&!$('csv-report-ack').checked,'new Run shows complete MD preview and fresh execution consent');
  check(!requests.some(r=>r.method==='POST'&&r.path===`/api/runs/${run}/confirm-csv-report`),'preparation has not executed or confirmed tools');
  await action('csv-report-ack');await wait(()=>!$('csv-report-confirm').disabled,'current contract acknowledgement readback');await action('csv-report-confirm');await rpc({command:'worker',run});await action('run-history-refresh');const node=[...$('runs').children].find(r=>r.textContent.includes(run.slice(0,16)));await action(node.querySelector('button'));
  check($('result').textContent.includes('PASS')&&$('result').textContent.includes('人工 PENDING'),'same Run reports contract PASS separately from pending human acceptance');
  const download=[...$('run-artifacts').querySelectorAll('button')].find(b=>b.textContent==='下载此成果');await action(download);
  const actual=requests.filter(r=>r.method==='GET'&&r.path===`/api/runs/${run}`&&r.status===200).at(-1).response,spec=actual.contract.snapshot.ordinary_csv_report,saved=actual.result.receipts.at(-1).data;
  const bytes=Buffer.from(await downloads[0].arrayBuffer()),hash=crypto.createHash('sha256').update(bytes).digest('hex');
  check(downloads.length===2&&bytes.equals(Buffer.from(spec.report_text,'utf8'))&&hash===spec.report_hash&&hash===saved.hash,'actual downloaded Blob bytes match this new Run frozen complete MD and saved receipt SHA');
  await wait(()=>revocations.includes(downloads[1].href),'download object URL revoked');
  check(downloads[1].name.includes(run)&&downloads[1].name.includes(saved.resource_id)&&downloads[1].name.endsWith('.md')&&revocations.includes(downloads[1].href),'download names the same Run and artifact and revokes object URL');
  fs.writeFileSync(info.output.replace('.json','.download.md'),bytes);
  const before=uses().length;await nav('apps');const reopened=[...$('use-list').children].find(r=>r.dataset.appId===aid);await action(reopened.querySelector('button'));check($('csv-full-report-history').textContent.includes(run)&&uses().length===before,'directory reopens persisted exact Run history without reexecution');delivery={aid,run};
  if(info.case==='deliver'){await rpc({command:'revoke-output',resource:saved.resource_id});await action($('csv-full-report-history').querySelector('button'));check(w.eval('activeApp===null&&activeRun===null')&&!$('csv-full-report-use')&&!$('app-manifest').textContent&&!$('run-artifacts'),'history open current output403 clears workflow definition, inputs and prior Run artifact canvas');}
  if(info.case==='misbound'){secondRunRevoke={run,resource:saved.resource_id,count:0};await action($('csv-full-report-history').querySelector('button'));
   await wait(()=>requests.filter(r=>r.method==='GET'&&r.path===`/api/runs/${run}`).every(r=>Number.isInteger(r.status)),'all actual Run replies during handoff settle');
   diagnostics.handoff={read_count:secondRunRevoke.count,active_app:w.eval('activeApp'),active_run:w.eval('activeRun'),manifest_empty:!$('app-manifest').textContent,artifact_canvas_empty:!$('run-artifacts'),run_http_statuses:requests.filter(r=>r.method==='GET'&&r.path===`/api/runs/${run}`).map(r=>r.status)};
   const h=diagnostics.handoff;check(h.read_count>=2&&h.run_http_statuses.includes(403)&&h.active_app===null&&h.active_run===null&&h.manifest_empty&&h.artifact_canvas_empty,'output revocation during project handoff clears old app and Run after actual subsequent GET403');
  }


 }
 }
 await wait(()=>requests.every(r=>Number.isInteger(r.status)),'all issued actual API replies settle');
 fs.writeFileSync(info.output,JSON.stringify({status:'PASS',case:info.case,browser:'JSDOM_NOT_NATIVE',checks,assets,requests,delivery,diagnostics,downloads:downloads.map(x=>({name:x.name,size:x.size})),revocations,real_model_requests:0},null,2));
 }catch(error){fs.writeFileSync(info.output,JSON.stringify({status:'FAIL',error:error.stack,checks,assets,requests,delivery,diagnostics},null,2));console.error(error.stack);process.exitCode=1;}finally{dom?.window.close();process.stdout.write(JSON.stringify({done:true})+'\n');}})();
