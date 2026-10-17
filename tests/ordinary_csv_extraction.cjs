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
const postCount=()=>requests.filter(r=>r.method==='POST').length;
const extracts=()=>requests.filter(r=>r.method==='POST'&&r.path.endsWith('/csv-sum-candidates'));
async function project(id){$('project-select').value=id;await action('project-select','change');}
async function nav(tab){await action(w.document.querySelector(`#workspace-nav [data-tab="${tab}"]`));}
async function source(){const row=[...$('runs').children].find(r=>r.textContent.includes(info.run.slice(0,16)));assert(row);await action(row.querySelector('button'));}
async function configure(){await action('csv-sum-read');$('csv-sum-target').value=info.target;await action('csv-sum-target','change');$('csv-sum-name').value='仅求和应用😀 <script>window.sumUnsafe=true</script>';$('csv-sum-name').oninput();check(!$('csv-sum-ack').checked&&$('csv-sum-submit').disabled,'sum-only consent starts unchecked and gates submission');await action('csv-sum-ack');}
async function boot(){
 const load=async path=>{const r=await rpc({method:'GET',path});assert.equal(r.status,200);assets.push({path,sha256:crypto.createHash('sha256').update(r.text).digest('hex')});return r.text;};
 dom=new JSDOM(await load('/'),{url:'http://testserver/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.setInterval=()=>0;
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{const request={method:options.method||'GET',path,body:options.body?JSON.parse(options.body):undefined};requests.push(request);const r=await rpc({...request,headers:options.headers});request.status=r.status;request.response=JSON.parse(r.text);
  if(drop&&request.method==='POST'&&path.endsWith('/csv-sum-candidates')){drop=false;assert.equal(r.status,201);request.delivery='ACTUAL_201_LOST';throw Error('Synthetic lost accepted response');}
  if(hold===path){hold=null;await new Promise(resolve=>{release=resolve;});}return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
 };
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(script.getAttribute('src'));w.document.body.append(node);}
 $('token').value='synthetic-test-A';await action('connect');await project(info.project);await source();
 check(visible($('csv-sum-extraction'))&&$('csv-sum-scope').textContent.includes('不包含原MD'),'successful ordinary Run has discoverable explicit sum-only entry');
 check(extracts().length===0,'opening success and options does not submit extraction');
}
async function deliver(){
 await action('csv-sum-open');check(visible($('apps'))&&$('app-origin').textContent.includes('不含原MD'),'explicit open hands off to app scope with honest source classification');
 const aid=w.eval('activeApp');$('app-column').value='quantity';await action('app-column','change');await action('app-preview-submit');
 check($('app-output').textContent.includes('合计 15'),'new target input independently computes15');check(w.sumUnsafe===undefined,'application name remains inert text');
 await action('internal-prepare');check(visible($('internal-approval'))&&!$('internal-approval-ack').checked,'existing version approval is actionable after handoff and requires confirmation');
 await action('internal-approval-ack');await action('internal-commit');const create=$('internal-releases').querySelector('button');await action(create);
 const iid=w.eval('engineering.instance.id');check(Boolean(iid),'existing version creates an independent instance through visible control');
 await nav('projects');await action('run-history-refresh');await nav('apps');
 const row=[...$('use-list').children].find(r=>r.dataset.appId===aid&&r.dataset.instanceId===iid);check(row?.dataset.useFamily==='CSV'&&row.textContent.includes('不含MD'),'unified directory classifies saved sum-only instance');await action(row.querySelector('button'));
 $('use-column').value='quantity';await action('use-column','change');await action('use-submit');const run=w.eval('applicationUse.selected');check(run&&run!==info.run,'explicit new-input submit creates its own Run');
 await rpc({command:'worker',run});await action('use-refresh');check($('use-output').textContent.includes('SUCCEEDED')&&$('use-output').textContent.includes('合计 15')&&$('use-output').textContent.includes('结果版本 1'),'same new Run shows fresh result version1 in existing use entry');
 check($('use-acceptance').textContent.includes('PENDING')||$('use-acceptance').textContent.includes('人工'),'same result retains separate human acceptance entry');
 const before=postCount();await nav('projects');await action('run-history-refresh');await nav('apps');const reopened=[...$('use-list').children].find(r=>r.dataset.appId===aid&&r.dataset.instanceId===iid);await action(reopened.querySelector('button'));check(postCount()===before,'navigation reopens persisted directory instance without another submission');
 return {aid,iid,run};
}
(async()=>{let delivery=null;try{
 await boot();
 if(info.case==='navigation'){
  const old=$('csv-sum-extraction');hold=`/api/runs/${info.run}/csv-sum-candidate-options`;const reading=action('csv-sum-read');await wait(()=>release,'options held');await project(info.other);const done=release;release=null;done();await reading;check(!visible($('csv-sum-extraction'))&&w.eval('activeApp===null'),'late options cannot populate another project');
  await project(info.project);await source();await configure();await action('csv-sum-submit');const aid=extracts().at(-1).response.id;hold=`/api/apps/${aid}`;const opening=action('csv-sum-open');await wait(()=>release,'candidate body held');await action('identity-switch');$('token').value='synthetic-test-B';await action('connect');const finish=release;release=null;finish();await opening;check(w.eval('activeApp===null&&activeRun===null')&&!visible($('csv-sum-extraction')),'late candidate cannot install under reconnected account');check(extracts().length===1,'navigation callbacks never create extra candidates');
 }else{
  await configure();const node=$('csv-sum-extraction'),name=$('csv-sum-name').value;await w.showRun(info.run,false);check($('csv-sum-extraction')===node&&$('csv-sum-ack').checked&&$('csv-sum-name').value===name&&$('csv-sum-target').value===info.target,'normal same-Run background redraw preserves explicit in-progress selection');
  if(info.case==='lost')drop=true;const button=$('csv-sum-submit'),sending=action(button);await button.onclick(new w.Event('click'));await sending;check(extracts().length===1,'double submit accepts exactly one extraction POST');
  if(info.case==='lost'){check($('csv-sum-status').textContent.includes('UNKNOWN'),'actual accepted lost response stays UNKNOWN');const key=$('csv-sum-key').value;await nav('resources');await nav('projects');await wait(()=>visible($('csv-sum-recover'))&&!$('csv-sum-recover').disabled,'workspace fresh read');await action('csv-sum-recover');check($('csv-sum-key').value===key&&extracts().length===1&&requests.some(r=>r.method==='GET'&&r.path.endsWith('/csv-sum-requests/'+key)),'workspace return recovers original accepted request with GET only');}
  delivery=await deliver();check(extracts()[0].body.consent==='EXTRACT_SUM_ONLY_WITHOUT_MD_REPORT','exact request freezes sum-only consent');
 }
 fs.writeFileSync(info.output,JSON.stringify({status:'PASS',case:info.case,browser:'JSDOM_NOT_NATIVE',checks,assets,requests,delivery,real_model_requests:0},null,2));
 }catch(error){fs.writeFileSync(info.output,JSON.stringify({status:'FAIL',error:error.stack,checks,assets,requests,delivery},null,2));console.error(error.stack);process.exitCode=1;}finally{dom?.window.close();process.stdout.write(JSON.stringify({done:true})+'\n');}})();
