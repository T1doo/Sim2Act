'use strict';
// Full served page / authenticated ASGI / real tools; scripted Mock, synthetic SQLite.
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),requests=[],checks=[],assets=[],observations=[],blobs=[],anchors=[],pending=new Map();
let serial=0,active=0,dom,w,$,hold=null,release=null,mutation=null,actual;
readline.createInterface({input:process.stdin}).on('line',line=>{const r=JSON.parse(line),resolve=pending.get(r.id);assert(resolve);pending.delete(r.id);resolve(r);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+'\n');});
const wait=async(fn,label)=>{const until=Date.now()+12000;while(Date.now()<until){if(fn())return;await new Promise(r=>setTimeout(r,5));}throw Error('bounded wait: '+label);};
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
function visible(el){if(!el?.isConnected)return false;for(let p=el;p;p=p.parentElement)if(p.hidden||w.getComputedStyle(p).display==='none')return false;return true;}
async function action(el,type='click'){
 if(typeof el==='string')el=$(el);assert(visible(el));assert(!el.matches(':disabled'));const work=[],restore=[];
 for(const [node,name]of [[el,type==='change'?'onchange':'onclick'],[type==='click'?el.form:null,'onsubmit']]){const fn=node?.[name];if(typeof fn!=='function')continue;const wrap=function(e){const p=fn.call(this,e);work.push(Promise.resolve(p));return p;};node[name]=wrap;restore.push(()=>{if(node[name]===wrap)node[name]=fn;});}
 try{if(type==='click')el.click();else el.dispatchEvent(new w.Event(type,{bubbles:true}));await Promise.all(work);}finally{restore.forEach(fn=>fn());}
}
const project=async id=>{$('project-select').value=id;await action('project-select','change');};
const selectRun=async id=>{await action('run-history-refresh');const row=[...$('runs').children].find(row=>row.textContent.includes(id.slice(0,16)));assert(row);await action(row.querySelector('button'));};
const artifactButton=label=>[...($('run-artifacts')?.querySelectorAll('button')||[])].find(b=>b.textContent===label);
async function boot(){
 const load=async path=>{const r=await rpc({method:'GET',path});assert.equal(r.status,200);assets.push({path,sha256:crypto.createHash('sha256').update(r.text).digest('hex')});return r.text;};
 dom=new JSDOM(await load('/'),{url:'http://testserver/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.setInterval=()=>0;w.Blob=Blob;
 w.URL.createObjectURL=blob=>{const url='blob:synthetic-'+blobs.length;blobs.push({url,blob,revoked:false});return url;};
 w.URL.revokeObjectURL=url=>{const record=blobs.find(b=>b.url===url);assert(record);record.revoked=true;};
 w.HTMLAnchorElement.prototype.click=function(){anchors.push({url:this.href,filename:this.download});};
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{active++;const request={method:options.method||'GET',path,body:options.body?JSON.parse(options.body):undefined};requests.push(request);
  try{const h=hold&&hold.path===path&&request.method==='GET'?hold:null;if(h)hold=null;
   if(h?.before)await new Promise(resolve=>{release=resolve;});
   const r=await rpc({...request,headers:options.headers});request.status=r.status;request.response=JSON.parse(r.text);
   if(h&&!h.before)await new Promise(resolve=>{release=resolve;});
   let body=r.text;if(mutation&&path===mutation.path){const m=mutation;mutation=null;const value=JSON.parse(body);m.change(value);request.controlled_delivery=m.label;body=JSON.stringify(value);}
   return new Response(body,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
  }finally{active--;}};
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(script.getAttribute('src'));w.document.body.append(node);}
 $('token').value='synthetic-test-A';await action('connect');await project(info.project);
 for(const option of $('run-materials').options)option.selected=option.value===info.material;await action('run-materials','change');
 $('goal').value='合成工程目标：汇总所选CSV的amount，记录条数并保存可核查的报告；不声称语义验收';await action('run-submit');
 const sent=requests.find(r=>r.method==='POST'&&r.path===`/api/projects/${info.project}/runs`);
 check(sent?.status===202&&JSON.stringify(sent.body.resource_refs)===JSON.stringify([info.material]),'visible explicit material and Goal submit one exact accepted input');
 const reply=await rpc({command:'worker',run:sent.response.run_id});assert.equal(reply.status,200);actual=JSON.parse(reply.text);
 await selectRun(actual.run.id);
 observations.push({actual_run:actual.run,visible_result:$('result').textContent,answer_visible:!!$('run-answer'),artifact_controls:!!$('run-artifacts')});
 check($('run-answer')?.textContent===info.answer,'persisted final answer is directly visible in the result canvas');
 check(!$('run-answer').querySelector('img')&&!w.answerExecuted,'answer is literal text rather than active HTML');
 check($('result').textContent.includes('PARTIAL')&&$('result').textContent.includes('MOCK')&&$('result').textContent.includes('NOT_RUN'),'actual partial/mock/not-run acceptance boundaries remain visible');
 check($('run-artifacts')?.textContent.includes(actual.artifact.id)&&artifactButton('查看此成果')&&artifactButton('下载此成果'),'artifact exact ID has same-Run view and download controls');
 check(!$('run-artifacts').textContent.includes(info.material)&&!$('result').textContent.includes('UNSELECTED_SAME_NAME_NOT_THE_RESULT'),'read resource is not mistaken for an artifact or same-name decoy');
}
async function capture(index){
 await wait(()=>blobs[index]?.revoked,'Blob cleanup');const bytes=Buffer.from(await blobs[index].blob.arrayBuffer());assert.deepEqual(bytes,Buffer.from(info.report));
 check(anchors[index].filename===`sim2act-${actual.run.id}-${actual.artifact.id}.md`,'download filename identifies exact Run and artifact');
 fs.writeFileSync(info.output.replace('result.json',`captured-${index}.md`),bytes);
 check(true,'captured Blob equals actual saved UTF-8 report bytes including CRLF/emoji/markup');
}
async function deliver(){
 const before=requests.length;await action(artifactButton('查看此成果'));
 check($('run-artifacts').querySelector('pre')?.textContent===info.report&&!$('run-artifacts').querySelector('script')&&!w.artifactExecuted,'view reads exact saved report as inert text within this Run');
 check(requests.length===before+2&&requests[before].path===`/api/runs/${actual.run.id}`&&requests[before+1].path===`/api/resources/${actual.artifact.id}`,'view freshly authorizes exact Run then resource without catalog lookup');
 const count=requests.length;hold={path:`/api/runs/${actual.run.id}`};const downloading=action(artifactButton('下载此成果'));await wait(()=>!!release,'fresh Run GET held');
 artifactButton('下载此成果').dispatchEvent(new w.MouseEvent('click',{bubbles:true}));await new Promise(r=>setImmediate(r));
 check(requests.length===count+1,'duplicate click shares one in-flight Run verification');const finish=release;release=null;finish();await downloading;await capture(0);
 await action(artifactButton('下载此成果'));await capture(1);check(blobs.length===2,'a later explicit download reads and saves anew');
 const number=blobs.length;mutation={path:`/api/resources/${actual.artifact.id}`,label:'Synthetic content change after actual authorized GET200',change:r=>r.content+='changed'};await action(artifactButton('下载此成果'));
 check(blobs.length===number&&$('run-artifacts').textContent.includes('未下载'),'changed content digest blocks file delivery');
 await action(artifactButton('下载此成果'));await capture(2);check(!w.document.querySelector('a[download]'),'temporary download anchors removed');
}
async function navigation(){
 for(const [label,change]of [
  ['Run',async()=>{await selectRun(actual.other_run);await selectRun(actual.run.id);}],
  ['workspace',async()=>{w.selectWorkspace('resources');w.selectWorkspace('projects');await selectRun(actual.run.id);}],
  ['project',async()=>{await project(info.other);await project(info.project);await selectRun(actual.run.id);}],
  ['identity',async()=>{await action('identity-switch');$('token').value='synthetic-test-B';await action('connect');await action('identity-switch');$('token').value='synthetic-test-A';await action('connect');await project(info.project);await selectRun(actual.run.id);}],
 ]){
  const count=blobs.length;hold={path:`/api/resources/${actual.artifact.id}`};const downloading=action(artifactButton('下载此成果'));await wait(()=>!!release,'old authorized resource GET held');
  await change();const finish=release;release=null;finish();await downloading;check(blobs.length===count,`${label} away/back discards late authorized bytes before Blob`);
 }
 await action(artifactButton('下载此成果'));await capture(0);check(true,'current selected Run still supports a new explicit download after isolation');
}
async function revocation(){
 await action(artifactButton('查看此成果'));const detached=artifactButton('下载此成果');
 hold={path:`/api/runs/${actual.run.id}`,before:true};const downloading=action(detached);await wait(()=>!!release,'read held before actual authorization');
 assert.equal((await rpc({command:'revoke-artifact'})).status,200);const finish=release;release=null;finish();await downloading;
 check(requests.at(-1).status===403&&blobs.length===0,'actual artifact Grant revocation refuses fresh Run GET and creates no Blob');
 check(!$('run-answer')&&!$('run-artifacts')&&$('raw-result').textContent===''&&!$('result').textContent.includes(info.report),'current denial clears protected answer, report, controls and raw detail');
 const count=requests.length;await detached.onclick(new w.Event('click'));check(requests.length===count,'detached denied control sends no further request');
}
(async()=>{let status='FAIL',error;try{
 await boot();const postCount=requests.filter(r=>r.method==='POST').length;
 if(info.case==='deliver')await deliver();else if(info.case==='navigation')await navigation();else await revocation();
 check(requests.filter(r=>r.method==='POST').length===postCount&&postCount===1,'all result use is read-only; only the original visible Run submission POST');
 assert.equal((await rpc({command:'verify-readonly'})).status,200);check(w.eval('ordinaryArtifactRequests.size')===0,'all result read locks released');status='PASS';
}catch(e){error=e.stack;process.stderr.write(error+'\n');process.exitCode=1;}finally{
 if(release){release();release=null;}try{await wait(()=>active===0&&pending.size===0,'requests drained');dom?.window.close();}catch(e){error=error||e.stack;process.exitCode=1;}
 const captured=[];for(const b of blobs){const bytes=Buffer.from(await b.blob.arrayBuffer());captured.push({bytes:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),revoked:b.revoked});}
 fs.writeFileSync(info.output,JSON.stringify({status,error,case:info.case,checks,observations,requests,assets,blobs:captured,anchors,
  scope:'Full served JS/JSDOM, authenticated ASGI and actual registered read/aggregate/save tools; scripted Mock4 calls per executed Run, zero real model. Blob capture is not native browser. SQLite; semantic NOT_RUN.'},null,2)+'\n');process.stdout.write(JSON.stringify({done:true})+'\n');}})();
