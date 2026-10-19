'use strict';
// Full served page + actual ASGI IPC; explicitly not native browser acceptance.
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),pending=new Map(),requests=[],assets=[],checks=[];
let serial=0,dom,w,$,boots=0,active=0,hold=false,holdReady=null,releaseRead=null,tamper=false;
readline.createInterface({input:process.stdin}).on('line',line=>{const r=JSON.parse(line),resolve=pending.get(r.id);assert(resolve);pending.delete(r.id);resolve(r);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+'\n');});
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
const wait=async(test,label)=>{const until=Date.now()+12000;while(Date.now()<until){if(test())return;await new Promise(r=>setTimeout(r,5));}throw Error('bounded wait: '+label);};
function visible(el){if(!el?.isConnected)return false;for(let p=el;p;p=p.parentElement)if(p.hidden||w.getComputedStyle(p).display==='none')return false;return true;}
async function click(value){
 const el=typeof value==='string'?$(value):value;assert(visible(el),'visible click '+value);assert(!el.matches(':disabled'),'enabled click '+value);
 const restore=[],work=[];
 for(const [node,key]of [[el,'onclick'],[el.form,'onsubmit']]){const fn=node?.[key];if(typeof fn!=='function')continue;const wrap=function(e){const promise=fn.call(this,e);work.push(Promise.resolve(promise));return promise;};node[key]=wrap;restore.push(()=>{if(node[key]===wrap)node[key]=fn;});}
 try{el.focus();el.click();await Promise.all(work);}finally{restore.forEach(fn=>fn());}
}
const entry=()=>$('use-list').querySelector(`[data-use-family="LITERAL_TEXT"][data-app-id="${info.app}"] button`);
const instanceButton=id=>[...$('internal-instances').children].find(row=>row.textContent.includes(id))?.querySelector('button');
async function close(){if(!dom)return;await wait(()=>active===0&&pending.size===0,'HTTP drained');dom.window.close();dom=null;}
async function boot(){
 await close();boots++;
 const load=async path=>{const r=await rpc({method:'GET',path});assert.equal(r.status,200);assets.push({path,sha256:crypto.createHash('sha256').update(r.text).digest('hex')});return r.text;};
 dom=new JSDOM(await load('/'),{url:'http://testserver/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.setInterval=()=>0;
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{active++;const request={method:options.method||'GET',path,body:options.body?JSON.parse(options.body):undefined};requests.push(request);
  try{const r=await rpc({...request,headers:options.headers});request.status=r.status;request.response_sha256=crypto.createHash('sha256').update(r.text).digest('hex');
   if(path===`/api/internal/releases/${info.release}`){
    if(hold){hold=false;await new Promise(resolve=>{releaseRead=resolve;holdReady();});}
    if(tamper){tamper=false;const value=JSON.parse(r.text);value.fingerprint='0'.repeat(64);r.text=JSON.stringify(value);request.synthetic_delivery_mutation='wrong_release_fingerprint';}
   }
   return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
  }finally{active--;}};
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(script.getAttribute('src'));w.document.body.append(node);}
 $('token').value='synthetic-test-A';await click('connect');await click(w.document.querySelector('[data-tab="apps"]'));await wait(()=>!!entry(),'literal directory');
}
async function open(){await click(entry());await click(instanceButton(info.instance));}
function results(){return [...$('internal-data').querySelectorAll('article.agent-result')];}
function verify(){
 const nodes=results();check(nodes.length===3,'three actual persistent result versions');
 for(const [index,node]of nodes.entries()){
  check(node.dataset.resultVersion===String(index+1)&&node.dataset.releaseId===info.release,'result version and original Release '+(index+1));
  check([...node.querySelectorAll('.manifest-views>section')].map(n=>`${n.dataset.viewComponent}:${n.dataset.outputField}`).join('|')==='text:term|table:citations|text:semantic_status','accepted mixed component order '+(index+1));
  check([...node.querySelectorAll('th')].map(n=>n.textContent).join('|')===info.columns.join('|'),'schema column order '+(index+1));
  check(node.querySelector('.manifest-text').textContent===info.terms[index]&&node.querySelectorAll('.manifest-text')[1].textContent==='UNKNOWN','typed text values '+(index+1));
  check(node.querySelectorAll('tbody tr').length===(index===2?0:2),'bounded complete table rows '+(index+1));
 }
 check(nodes[1].querySelector('tbody').textContent.includes('<em>Beta literal</em>')&&!$('internal-data').querySelector('em'),'HTML source is literal text, never elements');
 check(nodes[2].textContent.includes('暂无记录')&&nodes[2].querySelectorAll('th').length===3,'empty table retains declared headers and clear message');
 check(nodes.every(node=>node.querySelector('details summary').textContent==='查看原始结果'),'raw result remains accessible');
 check(info.runs.every(id=>$('internal-runs').textContent.includes(id)),'same three real Runs remain reachable');
}
(async()=>{
 let status='FAIL',error;
 try{
  await boot();await open();verify();
  const reads=()=>requests.filter(r=>r.path===`/api/internal/releases/${info.release}`).length,before=reads();
  w.eval('engineering.draft.candidate.manifest.views=[]');await click(instanceButton(info.instance));
  check(reads()===before+1,'one fresh authorized lookup per unique result Release per selection');
  check(results().every(n=>n.querySelectorAll('.manifest-views>section').length===3),'synthetic frontend current-draft pollution cannot rewrite immutable historical views');
  const unsupported=w.renderManifestViews({...info.manifest,views:[{component_ref:'chart',output_field:'citations'},{component_ref:'table',output_field:'term'}]},info.example);
  check(unsupported.textContent.includes('图表需要已核对的同Run')&&unsupported.textContent.includes('此字段形状暂不支持')&&!unsupported.querySelector('svg,canvas,.table-chart-controls'),'synthetic renderer refuses chart controls without sameRun context and unsupported table shape');
  tamper=true;await click(instanceButton(info.instance));
  check(!$('internal-data').textContent&&$('internal-run-status').textContent.includes('绑定不一致'),'synthetic wrong fingerprint delivery clears result content');
  await open();hold=true;const held=new Promise(resolve=>{holdReady=resolve;}),opening=click(instanceButton(info.instance));
  await Promise.race([held,opening.then(()=>{throw Error('Release response hold was not reached');})]);
  await click(instanceButton(info.empty));const release=releaseRead;releaseRead=null;release();await opening;
  check(w.eval('engineering.instance.id')===info.empty&&!$('internal-data').textContent,'late real Release read cannot populate newly selected empty instance');
  await boot();await open();verify();
  check(requests.every(r=>r.method==='GET'),'entire page phase uses GET only, no Run or authority write');
  status='PASS';
 }catch(e){error=e.stack;process.stderr.write(error+'\n');process.exitCode=1;}
 finally{
  if(releaseRead){releaseRead();releaseRead=null;}try{await close();}catch(e){status='FAIL';error=error||e.stack;process.exitCode=1;}
  fs.writeFileSync(info.output,JSON.stringify({status,error,checks,requests,assets,boots,negative_classification:'current-draft mutation / wrong fingerprint delivery / unsupported renderer input are synthetic frontend negatives, not new server Releases',scope:'Actual ASGI TestClient HTTP + full served JS in JSDOM; fixture normal Mock generation + NoModel Worker',native_browser:'NOT_RUN',windows:'NOT_RUN',pg:'NOT_RUN',remote_ci:'NOT_RUN',real_model:'NOT_RUN'},null,2)+'\n');
  process.stdout.write(JSON.stringify({done:true})+'\n');
 }
})();
