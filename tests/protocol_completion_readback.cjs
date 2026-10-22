'use strict';
// Actual classic-script controller, minimal elements; no native DOM claim.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=process.argv[2],web=path.join(__dirname,'../src/sim2act/web');
const source=fs.readFileSync(path.join(web,'protocol.js'),'utf8'),html=fs.readFileSync(path.join(web,'index.html'),'utf8');
const cases=JSON.parse(fs.readFileSync(path.join(root,'cases.json'),'utf8')),checks=[];
let ctx,elements,calls,respond;
const ev=code=>vm.runInContext(code,ctx);
function setup(item,handler){
  elements=new Map([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],{hidden:false,disabled:false,checked:false,value:'',textContent:'',replaceChildren(){this.textContent='';},querySelectorAll(){return [];}}]));
  elements.get('project-select').value='project';calls=[];
  respond=handler||((url)=>({data:url.endsWith('/completion-receipt')?item.locator:item.run}));
  ctx=vm.createContext({token:'owner',activeRun:item.run.run_id,workspaceSelectionGeneration:0,Option:function(){},safe:fn=>fn,
    crypto:{randomUUID(){throw Error('Readonly cannot choose a key');}},
    document:{getElementById(id){assert(elements.has(id),id);return elements.get(id);}},
    fetch:async(url,options)=>{assert.equal(options.method,'GET');calls.push({method:options.method,url});assert(calls.length<=14);const r=await respond(url);return {ok:(r.status||200)<400,status:r.status||200,json:async()=>r.data};}});
  ctx.$=id=>ctx.document.getElementById(id);vm.runInContext(source,ctx);ctx.selected=JSON.parse(JSON.stringify(item.run));
  ev('protocolContext={token,project:"project",generation:protocolGeneration,selection:0,intent:0,busy:false,run:selected};renderProtocolRun(protocolContext);');
}
const locate=()=>elements.get('protocol-completion-locate').onclick();
const entry=()=>ev('protocolCompletionReadbacks.get(protocolCompletionKey(protocolContext,activeRun))');
function check(ok,name){assert.ok(ok,name);checks.push(name);}
function closed(){return elements.get('protocol-state').textContent.includes('不可确认')&&!/SUCCEEDED|PASS|APPROVED/.test(elements.get('protocol-state').textContent)&&
  !elements.get('protocol-result').textContent&&elements.get('protocol-extract').hidden&&elements.get('protocol-cold-form').hidden&&
  !elements.get('protocol-completion-locate-receipt').textContent&&!elements.get('protocol-completion-locate-status').textContent.includes('已复读');}
(async()=>{
  if(process.argv[3]==='unknown'){
    const item={...cases[0],run:{...cases[0].run,phase:'source',status:'RUNNING',version:1,fence:1,result:null,result_fingerprint:null,error:{code:'OUTCOME_UNKNOWN'}}};
    const outcomes=[];
    setup(item,()=>({status:403,data:{error:{code:'READ_DENIED'}}}));await elements.get('protocol-review-locate').onclick();
    outcomes.push({scenario:'review locator failure preserves UNKNOWN',preserved:ev('protocolContext.run.error?.code')==='OUTCOME_UNKNOWN',closed:!ev('protocolCompletionEligible(protocolContext.run)')});
    setup(item);elements.get('projects').hidden=true;ev('protocolCompletionWorkspaceChanged()');elements.get('projects').hidden=false;
    outcomes.push({scenario:'close return preserves UNKNOWN',preserved:ev('protocolContext.run.error?.code')==='OUTCOME_UNKNOWN',closed:!ev('protocolCompletionEligible(protocolContext.run)')});
    const report={status:outcomes.every(o=>o.preserved&&o.closed)?'PASS':'FAIL',scope:'controller VM only',source_sha256:crypto.createHash('sha256').update(source).digest('hex'),outcomes};
    fs.writeFileSync(path.join(root,'unknown-preservation.json'),JSON.stringify(report,null,2));assert.equal(report.status,'PASS',JSON.stringify(outcomes));console.log('2 UNKNOWN preservation checks PASS');return;
  }
  for(const item of cases){
    setup(item);check(ev('protocolCompletionReadbacks.size===0&&protocolCompletionIntents.size===0'),'fresh map '+item.label);
    await locate();check(entry()?.state==='accepted'&&entry().body.request_key===item.locator.request.request_key&&calls.length===2,'two GET exact original '+item.label);
    check(ev('protocolCompletionIntents.size===0&&protocolReviewIntents.size===0'),'does not enter either command map '+item.label);
    if(item.run.phase==='source'&&item.run.status==='WAITING_APPROVAL')check(elements.get('protocol-extract').hidden&&elements.get('protocol-cold-form').hidden,'Source completion is not semantic PASS');
    for(const fault of ['NOT_FOUND','locator403','detail403','bad-format','bad-cached','mismatch']){
      setup(item);await locate();const key=entry().body.request_key;
      respond=url=>fault==='NOT_FOUND'?{data:{...item.locator,state:'NOT_FOUND',request:null,receipt:null}}:
        fault==='locator403'?{status:403,data:{error:{code:'READ_DENIED'}}}:
        fault==='bad-format'?{data:{...item.locator,extra:true}}:
        fault==='bad-cached'?{data:{...item.locator,receipt:{...item.locator.receipt,cached:true}}}:
        url.endsWith('/completion-receipt')?{data:item.locator}:
        fault==='detail403'?{status:403,data:{error:{code:'READ_DENIED'}}}:{data:{...item.run,fence:item.run.fence+1}};
      await locate();ev('renderProtocolRun(protocolContext)');
      check(closed()&&entry().body.request_key===key&&ev('protocolContext.run.status')===item.run.status,'neutral projection, original key/status '+item.label+' '+fault);
      respond=url=>({data:url.endsWith('/completion-receipt')?item.locator:item.run});await locate();
      check(entry().state==='accepted'&&entry().body.request_key===key,'fresh GET recovery '+item.label+' '+fault);
    }
  }
  const item=cases[0];let release,old,detail;
  setup(item,url=>url.endsWith('/completion-receipt')?new Promise(r=>release=()=>r({data:item.locator})):{data:item.run});
  let pending=locate();await Promise.resolve();await locate();check(calls.length===1,'double click one GET while busy');
  await ev('showProtocolRun(activeRun)');release();await pending;check(entry().state==='accepted','background selection does not cancel locator');
  for(const mode of ['intent','workspace','closed','identity','project','run']){
    setup(item,url=>new Promise(r=>release=()=>r({data:item.locator})));pending=locate();await Promise.resolve();
    if(mode==='intent')ev('protocolContext.intent++');
    if(mode==='workspace')ev('workspaceSelectionGeneration++');
    if(mode==='closed'){elements.get('projects').hidden=true;ev('protocolCompletionWorkspaceChanged()');elements.get('projects').hidden=false;}
    if(mode==='identity')ev('token="another"');
    if(mode==='project')elements.get('project-select').value='another';
    if(mode==='run')ev('activeRun="run_other"');
    release();await pending;check(calls.length===1&&!elements.get('protocol-completion-locate-receipt').textContent,'late locator isolated '+mode);
  }
  setup(item);ctx.saved=item.locator.request;
  ev('protocolCompletionIntents.set(protocolCompletionKey(protocolContext,activeRun),{rid:activeRun,phase:"source",body:{...saved,request_key:"different"},state:"unknown"})');
  await locate();check(!entry()&&closed()&&ev('protocolCompletionIntents.values().next().value.state')==='unknown','conflicting unknown command not upgraded or resent');
  setup(item);ctx.saved=item.locator.request;
  ev('protocolCompletionIntents.set(protocolCompletionKey(protocolContext,activeRun),{rid:activeRun,phase:"source",body:saved,state:"unknown"})');
  await locate();check(entry().state==='accepted'&&ev('protocolCompletionIntents.values().next().value.state')==='unknown','matching unknown command remains separate and sends nothing');
  detail=0;
  setup(item,url=>url.endsWith('/completion-receipt')?{data:item.locator}:++detail===1?new Promise(r=>old=()=>r({status:403,data:{error:{code:'OLDER_REJECT'}}})):{data:item.run});
  pending=locate();for(let n=0;n<30&&!old;n++)await Promise.resolve();assert(old);
  await ev('showProtocolRun(activeRun)');old();await pending;check(entry().state==='accepted','newer full read supersedes older rejection');
  setup(item);await locate();respond=()=>({status:403,data:{error:{code:'LOCATOR_REJECT'}}});await locate();
  respond=()=>({data:item.run});await ev('showProtocolRun(activeRun)');check(closed(),'background detail alone cannot repair a failed locator');
  setup(item);ctx.saved=item.locator.receipt;ev('protocolCompletionReadbacks.set(protocolCompletionKey(protocolContext,activeRun),{rid:activeRun,phase:"source",body:{expected_version:1,expected_fence:1,request_key:"x"},receipt:saved,state:"reading"})');
  await ev('showProtocolRun(activeRun)');check(entry().state==='reading','unregistered background result cannot attest a receipt');
  setup(item);await locate();elements.get('projects').hidden=true;ev('protocolCompletionWorkspaceChanged()');
  check(!elements.get('protocol-completion-locate-receipt').textContent,'close clears visible readback');
  for(const mode of ['intent','workspace','closed','identity','project','run']){
    detail=0;old=null;
    setup(item,url=>url.endsWith('/completion-receipt')?{data:item.locator}:new Promise(r=>old=()=>r({data:item.run})));
    pending=locate();for(let n=0;n<30&&!old;n++)await Promise.resolve();assert(old);
    if(mode==='intent')ev('protocolContext.intent++');
    if(mode==='workspace')ev('workspaceSelectionGeneration++');
    if(mode==='closed'){elements.get('projects').hidden=true;ev('protocolCompletionWorkspaceChanged()');elements.get('projects').hidden=false;}
    if(mode==='identity')ev('token="another"');
    if(mode==='project')elements.get('project-select').value='another';
    if(mode==='run')ev('activeRun="run_other"');
    old();await pending;check(entry()?.state!=='accepted'&&!elements.get('protocol-completion-locate-receipt').textContent,'late detail isolated '+mode);
  }
  for(const error of [null,{code:'OUTCOME_UNKNOWN'}]){
    const incomplete={...item,run:{...item.run,status:'RUNNING',version:1,fence:1,result:null,result_fingerprint:null,error},
      locator:{...item.locator,state:'NOT_FOUND',request:null,receipt:null}};
    setup(incomplete);const eligible=ev('protocolCompletionEligible(protocolContext.run)');await locate();
    check(ev('protocolCompletionEligible(protocolContext.run)')===eligible&&eligible===(error===null),'readback never promotes UNKNOWN or disables independent known Source completion');
    if(error){elements.get('protocol-completion-confirm').checked=true;const count=calls.length;await ev('completeProtocolExtraction()');check(calls.length===count,'UNKNOWN cannot enter original completion writer');}
  }
  const reviewed=cases.find(c=>c.run.phase==='source'&&c.run.status==='SUCCEEDED');assert(reviewed);
  setup(reviewed);respond=url=>({data:url.endsWith('/completion-receipt')?{...reviewed.locator,state:'NOT_FOUND',request:null,receipt:null}:reviewed.run});
  await locate();check(closed()&&!entry(),'ordinary completed Run without optional V2 receipt closes locator projection');
  await elements.get('protocol-read').onclick();
  check(!elements.get('protocol-extract').hidden&&elements.get('protocol-state').textContent.includes('PASS')&&!entry()&&
    !elements.get('protocol-completion-locate-receipt').textContent,'explicit fresh Run GET restores original route without manufacturing receipt');
  await locate();respond=()=>({status:403,data:{error:{code:'FRESH_READ_DENIED'}}});
  let denied=false;try{await elements.get('protocol-read').onclick();}catch(error){denied=error.message==='FRESH_READ_DENIED';}
  check(denied&&elements.get('protocol-extract').hidden&&!elements.get('protocol-result').textContent,'explicit failed GET cannot restore output or receipt');
  setup(reviewed);respond=url=>({data:url.endsWith('/completion-receipt')?{...reviewed.locator,state:'NOT_FOUND',request:null,receipt:null}:reviewed.run});await locate();
  detail=0;old=null;respond=()=>++detail===1?new Promise(r=>old=()=>r({data:reviewed.run})):{data:reviewed.run};
  pending=elements.get('protocol-read').onclick();await Promise.resolve();assert(old);
  await ev('showProtocolRun(activeRun)');old();await pending;
  check(closed(),'explicit GET ignored by newer selection does not clear optional receipt failure');
  await elements.get('protocol-read').onclick();check(!elements.get('protocol-extract').hidden&&!entry(),'subsequent actually adopted explicit GET restores only Run');
  const report={status:'PASS',scope:'actual controller VM / sealed authenticated API replies, not native DOM',checks,source_sha256:crypto.createHash('sha256').update(source).digest('hex'),model_requests:0,business_post:0};
  fs.writeFileSync(path.join(root,'completion-readback-controller.json'),JSON.stringify(report,null,2));console.log(checks.length+' completion readback VM checks PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
