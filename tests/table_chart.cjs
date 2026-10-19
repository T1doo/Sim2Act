'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const root=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(root,'info.json'))),requests=[],assets=[],checks=[],charts=[],pageErrors=[];
const journal=record=>fs.appendFileSync(path.join(root,'page-journal.jsonl'),JSON.stringify({...record,at:performance.now()})+'\n');
let dom,w,$,active=0,boots=0,holdRun=false,holdReady,releaseHeld,tamperRun=false,tamperRelease=false;
const check=(value,label)=>{assert(value,label);checks.push(label);journal({kind:'assertion',index:checks.length,label});};
const wait=async(test,label)=>{const until=Date.now()+15000;while(Date.now()<until){if(test())return;await new Promise(r=>setTimeout(r,5));}throw Error('bounded wait '+label);};
function visible(el){if(!el?.isConnected)return false;for(let p=el;p;p=p.parentElement)if(p.hidden||w.getComputedStyle(p).display==='none')return false;return true;}
async function click(value){
 const el=typeof value==='string'?$(value):value;assert(visible(el),'visible click '+value);assert(!el.matches(':disabled'),'enabled click '+value);
 const restore=[],work=[];
 for(const [node,key]of [[el,'onclick'],[el.form,'onsubmit']]){const fn=node?.[key];if(typeof fn!=='function')continue;const wrap=function(e){const promise=fn.call(this,e);work.push(Promise.resolve(promise));return promise;};node[key]=wrap;restore.push(()=>{if(node[key]===wrap)node[key]=fn;});}
 try{el.focus();el.click();await Promise.all(work);}finally{restore.forEach(fn=>fn());}
}
const entry=()=>$('use-list').querySelector(`[data-use-family="LITERAL_TEXT"][data-app-id="${info.app}"] button`);
const instanceButton=id=>[...$('internal-instances').children].find(row=>row.textContent.includes(id))?.querySelector('button');
const article=version=>$('internal-data').querySelector(`article[data-result-version="${version}"]`);
const control=(version=1,index=0)=>article(version).querySelectorAll('.table-chart-controls')[index];
const button=c=>c.querySelector('[data-chart-action="show"]');
function choose(c,category='quote',series='start_line'){
 const inputs=c.querySelectorAll('select');inputs[0].value=category;inputs[0].dispatchEvent(new w.Event('change',{bubbles:true}));inputs[1].value=series;inputs[1].dispatchEvent(new w.Event('change',{bubbles:true}));
}
const targetRun=`/api/internal/instances/${info.instance}/runs/${info.outputs[0].id}`;
const runReads=()=>requests.filter(r=>r.path===targetRun).length;
async function close(){if(!dom)return;await wait(()=>active===0,'HTTP drained');dom.window.close();dom=null;}
async function boot(){
 await close();boots++;
 const load=async name=>{const r=await fetch(info.base+(name==='index.html'?'/':'/'+name));const text=await r.text(),sha=crypto.createHash('sha256').update(text).digest('hex');assert.equal(r.status,200);assert.equal(sha,info.web_hashes[name]);const asset={name,status:r.status,sha256:sha,text};assets.push(asset);journal({kind:'asset',asset});return text;};
 dom=new JSDOM(await load('index.html'),{url:info.base+'/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.setInterval=()=>0;
 w.addEventListener('error',e=>pageErrors.push(String(e.error||e.message)));w.addEventListener('unhandledrejection',e=>pageErrors.push(String(e.reason)));
 const style=w.document.createElement('style');style.textContent=await load('app.css');w.document.head.append(style);
 w.fetch=async(input,options={})=>{
  active++;const url=new URL(input,info.base),request={method:options.method||'GET',path:url.pathname,body:options.body||null,cache:options.cache,started:performance.now()};requests.push(request);
  try{
   const response=await fetch(url,options);let text=await response.text();request.actual_status=response.status;request.actual_response_text=text;request.headers=Object.fromEntries(response.headers);journal({kind:'actual_HTTP',request});
   if(url.pathname===targetRun&&holdRun){holdRun=false;await new Promise(resolve=>{releaseHeld=resolve;holdReady();});}
   if(url.pathname===targetRun&&tamperRun){tamperRun=false;const value=JSON.parse(text);value.known_effects[0].fingerprint='0'.repeat(64);text=JSON.stringify(value);request.synthetic_delivery='wrong_typed_fingerprint_after_actual_HTTP';}
   if(url.pathname===`/api/internal/releases/${info.original_release}`&&tamperRelease){tamperRelease=false;const value=JSON.parse(text);value.fingerprint='0'.repeat(64);text=JSON.stringify(value);request.synthetic_delivery='wrong_original_release_fingerprint_after_actual_HTTP';}
   request.delivered_response_text=text;journal({kind:'delivered_HTTP',request});return new Response(text,{status:response.status,headers:response.headers});
  }finally{request.finished=performance.now();active--;}
 };
 for(const source of [...w.document.querySelectorAll('script[src]')]){const script=w.document.createElement('script');script.textContent=await load(source.getAttribute('src').slice(1));w.document.body.append(script);}
 $('token').value='synthetic-test-A';await click('connect');await click(w.document.querySelector('[data-tab="apps"]'));await wait(()=>!!entry(),'literal directory');
}
async function open(){await click(entry());await click(instanceButton(info.instance));}
function capture(c,output,series='start_line'){
 const figure=c.querySelector('figure[data-chart-contract="table-bar.v1"]'),svg=figure?.querySelector('svg');assert(svg,'actual bound chart');
 const bars=[...svg.querySelectorAll('rect')],expected=output.result.citations;
 check(bars.length===expected.length&&bars.every((b,i)=>b.dataset.value===String(expected[i][series])&&b.dataset.row===String(i+1)),'actual SVG bars preserve every original row and numeric value');
 check(figure.textContent.includes(output.id)&&figure.textContent.includes(output.release_id)&&figure.textContent.includes(`结果 v${output.result_version}`)&&figure.textContent.includes('单位：未指定')&&figure.textContent.includes(series),'visible versioned sameRun/Release/field/unspecified-unit contract');
 check(!figure.querySelector('polyline,path,iframe,script,em')&&bars.every(b=>Number.isFinite(Number(b.getAttribute('width')))&&Number(b.getAttribute('width'))>=0),'safe SVG bars with no interpolated curve or source HTML');
 const index=charts.length,raw=svg.outerHTML;fs.writeFileSync(path.join(root,`chart-${index}.svg`),raw);
 charts.push({file:`chart-${index}.svg`,sha256:crypto.createHash('sha256').update(raw).digest('hex'),run_id:output.id,release_id:output.release_id,result_version:output.result_version,field:'citations',category:'quote',series,unit:'UNSPECIFIED',values:expected.map(r=>r[series]),caption:figure.querySelector('figcaption').textContent});
}
function syntheticShapeChecks(){
 const schema={type:'array',maxItems:64,items:{type:'object',additionalProperties:false,required:['label','n'],properties:{label:{type:'string'},n:{type:'number'}}}};
 const rows=[{label:'same',n:-2},{label:'same',n:0},{label:'other',n:3}],range=w.tableBarValues(schema,rows,'label','n');
 check(range.min===-2&&range.max===3&&range.span===5,'SYNTHETIC helper negative and zero domain retains zero baseline');
 const figure=w.renderTableBar(schema,rows,'label','n',{run_id:'synthetic-only',release_id:'synthetic-only',result_version:1,field:'rows'}),bars=[...figure.querySelectorAll('rect')],baseline=Number(figure.querySelector('line').getAttribute('x1'));
 check(Number(bars[0].getAttribute('x'))<baseline&&Number(bars[1].getAttribute('width'))===0&&Number(bars[2].getAttribute('x'))===baseline&&bars.every((b,i)=>b.dataset.row===String(i+1)),'SYNTHETIC helper negative/zero bars and duplicate categories keep original row order');
 const allZero=w.tableBarValues(schema,[{label:'zero',n:0}],'label','n');check(allZero.min===0&&allZero.max===0,'SYNTHETIC all-zero domain remains zero, no fabricated nonzero data');
 const bad=[[],[{label:'x',n:null}],[{label:'x',n:'1'}],[{label:'x'}],[{label:'x',n:Infinity}],[{label:'x',n:NaN}],[{label:'x',n:Number.MAX_SAFE_INTEGER+1}],[{label:'x',n:-9e15},{label:'y',n:1e-320}],[{label:'x',n:1e-20},{label:'y',n:1}]];
 for(const rows of bad)assert.throws(()=>w.tableBarValues(schema,rows,'label','n'));
 assert.throws(()=>w.tableBarValues(schema,rows,'missing','n'));assert.throws(()=>w.tableBarValues(schema,rows,'label','label'));
 check(true,'SYNTHETIC helper explicitly refuses empty/missing/null/non-numeric/non-finite/unsafe/unrepresentable values and absent columns');
 const unbound=w.renderManifestViews(info.manifest,info.outputs[0].result);
 check(!unbound.querySelector('svg,.table-chart-controls')&&unbound.textContent.includes('图表需要已核对的同Run'),'unbound renderer input cannot authorize a chart');
}
(async()=>{
 let status='FAIL',error;
 try{
  await boot();await open();syntheticShapeChecks();
  check(article(1)&&article(2)&&article(3)&&!$('internal-data').querySelector('svg'),'real persisted table and chart declarations never auto-render a graph');
  check($('internal-instance-info').textContent.includes(info.current_release)&&article(1).dataset.releaseId===info.original_release,'real older Run retains original Release after legitimate instance switch');
  let c=control(),other=control(1,1),start=runReads();
  check([...c.querySelectorAll('select')].every(s=>s.value==='')&&c.textContent.includes('单位未指定'),'both selectors explicitly start unselected');
  await click(button(c));check(runReads()===start&&!c.querySelector('svg'),'no selection refuses locally without business execution');
  choose(c);choose(other);const showing=click(button(c));button(c).click();button(other).click();await showing;
  check(runReads()===start+1&&!other.querySelector('svg'),'duplicate and sibling view clicks share one same-result Run read');capture(c,info.outputs[0]);
  check(requests.filter(r=>r.path===targetRun).at(-1).cache==='no-store','chart explicit action uses fresh no-store Run GET');
  start=runReads();choose(c,'quote','end_line');check(!c.querySelector('svg')&&runReads()===start,'changing series immediately removes old chart without HTTP or Run');
  await click(button(c));capture(c,info.outputs[0],'end_line');
  const empty=control(2);choose(empty);start=requests.length;await click(button(empty));check(!empty.querySelector('svg')&&requests.length===start&&empty.textContent.includes('空表'),'actual empty successful result refuses chart without filling rows');
  choose(c,'missing','start_line');start=requests.length;await click(button(c));check(!c.querySelector('svg')&&requests.length===start,'nonexistent category cannot be selected or rendered');
  choose(c,'quote','quote');start=requests.length;await click(button(c));check(!c.querySelector('svg')&&requests.length===start,'non-numeric quote is absent from series choices and refuses render');
  check(article(3).querySelector('tbody').textContent.includes('<em>Beta literal</em>')&&!$('internal-data').querySelector('em'),'original tables retain full literal content and no injected HTML');
  if(info.case==='display'){
   await boot();await open();c=control();check(!c.querySelector('svg')&&[...c.querySelectorAll('select')].every(s=>s.value===''),'cold DOM history reopening needs explicit display choices');
   choose(c);await click(button(c));capture(c,info.outputs[0]);
   const beta=control(3,1);choose(beta);await click(button(beta));capture(beta,info.outputs[2]);
   check(info.outputs.every(r=>$('internal-runs').textContent.includes(r.id)),'same original Runs remain reachable alongside chart history');
  }else{
   choose(c);holdRun=true;const held=new Promise(resolve=>{holdReady=resolve;}),show=click(button(c));await held;choose(c,'quote','end_line');releaseHeld();releaseHeld=null;await show;
   check(!c.querySelector('svg'),'actual late200 after series change cannot repopulate old chart');
   await click(button(c));capture(c,info.outputs[0],'end_line');
   holdRun=true;const heldTab=new Promise(resolve=>{holdReady=resolve;}),showTab=click(button(c));await heldTab;
   await click(w.document.querySelector('[data-tab="resources"]'));await click(w.document.querySelector('[data-tab="apps"]'));
   releaseHeld();releaseHeld=null;await showTab;check(!c.querySelector('svg'),'actual late200 after workspace ABA is isolated');
   await click(button(c));capture(c,info.outputs[0],'end_line');check(true,'new explicit click after returning to workspace remains usable');
   tamperRun=true;await click(button(c));check(!c.querySelector('svg')&&c.textContent.includes('VERSION_CONFLICT'),'controlled wrong typed fingerprint after actual HTTP refuses chart');
   tamperRelease=true;await click(button(c));check(!c.querySelector('svg')&&c.textContent.includes('绑定不一致'),'controlled wrong original Release after actual HTTP refuses chart');
   holdRun=true;const held2=new Promise(resolve=>{holdReady=resolve;}),show2=click(button(c));await held2;await click(instanceButton(info.empty));releaseHeld();releaseHeld=null;await show2;
   check(w.eval('engineering.instance.id')===info.empty&&!$('internal-data').querySelector('svg'),'actual late200 cannot populate a newly selected empty instance');
   await click(instanceButton(info.instance));c=control();choose(c);await click(button(c));capture(c,info.outputs[0]);
   const response=await fetch(info.base+'/test-only-chart-revoke',{method:'POST',headers:{Authorization:'Bearer synthetic-test-A','Content-Type':'application/json'},body:'{}'});
   journal({kind:'fixture_revoke_HTTP',method:'POST',status:response.status,response_text:await response.text(),body:'{}'});assert.equal(response.status,200);
   await click(button(c));check(!$('internal-data').textContent&&requests.at(-1).actual_status===403,'actual READ revocation403 clears protected tables/chart/controls');
  }
  check(requests.every(r=>r.method==='GET'&&!r.body),'all product page actions are GET without business/permission writes');
  await wait(()=>active===0,'final HTTP');check(pageErrors.length===0,'no unhandled page errors');status='PASS';
 }catch(e){error=e.stack;process.stderr.write(error+'\n');process.exitCode=1;}
 finally{
  if(releaseHeld){releaseHeld();releaseHeld=null;}try{await close();}catch(e){status='FAIL';error=error||e.stack;process.exitCode=1;}
  fs.writeFileSync(path.join(root,'results.json'),JSON.stringify({status,error,case:info.case,checks,requests,assets,charts,boots,pageErrors,adapter:'JSDOM SVG structure + actual loopback HTTP; not native visual acceptance',synthetic_helpers:'negative/zero/shape probes are pure display counterexamples, not produced Run data',real_model_calls:0,native_browser:'NOT_RUN',windows:'NOT_RUN',pg:'NOT_RUN',remote_ci:'NOT_RUN'},null,2)+'\n');
 }
})();
