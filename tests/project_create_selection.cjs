'use strict';
// Full served page and real authenticated ASGI APIs; JSDOM is not native browser acceptance.
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),requests=[],checks=[],assets=[],pending=new Map(),observations=[];
let serial=0,active=0,dom,w,$,hold=null,release=null;
readline.createInterface({input:process.stdin}).on('line',line=>{const r=JSON.parse(line),resolve=pending.get(r.id);assert(resolve);pending.delete(r.id);resolve(r);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+'\n');});
const wait=async(fn,label)=>{const until=Date.now()+12000;while(Date.now()<until){if(fn())return;await new Promise(r=>setTimeout(r,5));}throw Error('bounded wait: '+label);};
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
const posts=()=>requests.filter(r=>r.method==='POST');
function visible(el){if(!el?.isConnected)return false;for(let p=el;p;p=p.parentElement)if(p.hidden||w.getComputedStyle(p).display==='none')return false;return true;}
async function action(el,type='click'){
 if(typeof el==='string')el=$(el);assert(visible(el));assert(!el.matches(':disabled'));
 const key=type==='change'?'onchange':'onclick',work=[],restore=[];
 for(const [node,name]of [[el,key],[type==='click'?el.form:null,'onsubmit']]){const fn=node?.[name];if(typeof fn!=='function')continue;const wrap=function(e){const p=fn.call(this,e);work.push(Promise.resolve(p));return p;};node[name]=wrap;restore.push(()=>{if(node[name]===wrap)node[name]=fn;});}
 try{if(type==='click')el.click();else el.dispatchEvent(new w.Event(type,{bubbles:true}));await Promise.all(work);}finally{restore.forEach(fn=>fn());}
}
const project=async id=>{$('project-select').value=id;await action('project-select','change');};
const createButton=()=>w.document.querySelector('#project-form button');
async function connect(identity){$('token').value=identity;await action('connect');}
async function boot(){
 const load=async path=>{const r=await rpc({method:'GET',path});assert.equal(r.status,200);assets.push({path,sha256:crypto.createHash('sha256').update(r.text).digest('hex')});return r.text;};
 dom=new JSDOM(await load('/'),{url:'http://testserver/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.setInterval=()=>0;
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{active++;const request={method:options.method||'GET',path,body:options.body?JSON.parse(options.body):undefined};requests.push(request);
  try{const r=await rpc({...request,headers:options.headers});request.status=r.status;request.response=JSON.parse(r.text);
   if(hold&&request.method===hold.method&&path===hold.path){hold=null;await new Promise(resolve=>{release=resolve;});}
   return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
  }finally{active--;}};
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(script.getAttribute('src'));w.document.body.append(node);}
 await connect('synthetic-test-A');await project(info.project);
 check($('project-context-status').textContent.includes(info.project_name),'initial A visible in current-project context');
}
async function chooseAndSave(){
 await action(w.document.querySelector('[data-tab="resources"]'));
 const file=new w.File(['city,amount\r\n杭州,9.25\r\n'],'B 合成.csv',{type:'text/csv'});Object.defineProperty($('resource-file'),'files',{configurable:true,value:[file]});await action('resource-file','change');
 await wait(()=>!!w.eval('resourceFileSnapshot'),'actual FileReader decoded');
 const before=posts().length;await action('resource-save');check(posts().length===before+1,'one explicit material Save');
 const saved=posts().at(-1);observations.push({kind:'actual_save',path:saved.path,body:saved.body,receipt:saved.response});return saved;
}
async function flow(){
 const name='新建 B 合成项目';$('project-name').value=name;hold={method:'POST',path:'/api/projects'};const started=action(createButton());await wait(()=>!!release,'accepted project-create reply held');
 if(info.case==='create-save'){
  createButton().click();$('project-form').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await new Promise(r=>setImmediate(r));
  const count=posts().filter(r=>r.path==='/api/projects').length;observations.push({kind:'pending_duplicate',post_count:count,disabled:createButton().disabled});
 }
 if(info.case==='late-manual'){await project(info.other);await project(info.project);}
 if(info.case==='late-identity'){await action('identity-switch');await connect('synthetic-test-B');}
 const deliver=release;release=null;
 if(info.case==='late-manual')hold={method:'GET',path:'/api/projects'};
 deliver();
 if(info.case==='late-manual'){
  await wait(()=>!!release,'post-create project list reply held');await project(info.other);await project(info.project);
  const deliverList=release;release=null;deliverList();
 }
 await started;await wait(()=>active===0,'create action drained');
 const created=posts().find(r=>r.path==='/api/projects').response.id;
 observations.push({kind:'after_create',created,current:$('project-select').value,context:$('project-context-status').textContent,options:[...$('project-select').options].map(o=>({id:o.value,name:o.textContent}))});
 if(info.case==='create-save'){
  const selectedAfter=$('project-select').value;const saved=await chooseAndSave();
  check(selectedAfter===created,'creating B while A selected selects returned B');
  check(saved.path===`/api/projects/${created}/resources`,'new material Save targets B exact returned project ID');
  check($('project-context-status').textContent.includes(name)&&$('materials').textContent.includes('B 合成.csv')&&!$('materials').textContent.includes('data.csv'),'B context and refreshed materials visible; A material absent');
  check(posts().filter(r=>r.path==='/api/projects').length===1,'pending duplicate gesture creates exactly one project');
  check(observations.find(o=>o.kind==='pending_duplicate').disabled,'create button remains disabled while accepted reply is pending');
  check(saved.body.content==='city,amount\r\n杭州,9.25\r\n','actual file Save preserves exact UTF8/CRLF');
  check((await rpc({command:'verify',created,resource:saved.response.id})).status===200,'all original rows including project A remain unchanged');
 }else if(info.case==='late-manual'){
  check($('project-select').value===info.project,'late create reply cannot steal manual project ABA selection');
  check([...$('project-select').options].some(o=>o.value===created),'accepted B remains discoverable in project selector');
  check($('materials').textContent.includes('data.csv')&&!$('materials').textContent.includes('B 合成.csv'),'manual A material context stays current');
  check((await rpc({command:'verify',created})).status===200,'project A original rows unchanged after late reply');
 }else{
  check($('project-select').value===info.foreign&&!Array.from($('project-select').options).some(o=>o.value===created),'late identity-A create reply cannot select or list project in identity B');
  check($('project-context-status').textContent.includes('Other identity project')&&!$('materials').textContent.includes('data.csv'),'identity B current scope remains visible');
  check((await rpc({command:'verify',created})).status===200,'late identity result changes only original authorized create');
 }
 check(posts().every(r=>r.path==='/api/projects'||r.path.endsWith('/resources')),'no Run executor model release or approval POST');
}
(async()=>{let status='FAIL',error;try{await boot();await flow();status='PASS';}catch(e){error=e.stack;process.stderr.write(error+'\n');process.exitCode=1;}finally{
 if(release){release();release=null;}try{await wait(()=>active===0&&pending.size===0,'HTTP drained');dom?.window.close();}catch(e){error=error||e.stack;process.exitCode=1;}
 fs.writeFileSync(info.output,JSON.stringify({status,error,case:info.case,checks,observations,requests,assets,real_model_calls:0,worker_calls:0,native_browser:'NOT_RUN',pg:'NOT_RUN'},null,2)+'\n');process.stdout.write(JSON.stringify({done:true})+'\n');}})();
