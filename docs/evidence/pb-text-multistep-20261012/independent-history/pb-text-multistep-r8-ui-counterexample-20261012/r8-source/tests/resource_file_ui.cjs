'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {createHash,randomUUID}=require('node:crypto'),{TextDecoder}=require('node:util'),{JSDOM}=require('jsdom');
const root=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(root,'info.json'))),bytes=fs.readFileSync(path.join(root,'真实 合成.csv'));
const checks=[],requests=[],pages=[],heldFiles=[];let dom,w,$,page,mode='normal',heldSave=null,heldRead=null;
const check=(ok,name)=>{assert(ok,name);checks.push(name);};
const wait=async(fn,name)=>{const end=Date.now()+6000;while(Date.now()<end){if(fn())return;await new Promise(r=>setTimeout(r,10));}throw Error('Timeout '+name);};
const submit=id=>$(id).dispatchEvent(new w.Event('submit',{cancelable:true}));
const posts=()=>requests.filter(r=>r.method==='POST');
async function idle(){await wait(()=>page.requests===0 && page.actions.size===0 && page.readers===0,'all I/O/actions drained');await new Promise(r=>setImmediate(r));assert.deepEqual(page.errors,[]);}
async function close(){if(!dom)return;await idle();pages.push({requests:page.requests,actions:page.actions.size,readers:page.readers,errors:page.errors.length,loaded_hashes:page.loaded});dom.window.close();dom=null;}
async function setup(){
  await close();const html=await(await fetch(info.base)).text();check(createHash('sha256').update(html).digest('hex')===info.web_hashes['index.html'],'actual HTML hash');
  dom=new JSDOM(html,{url:info.base,runScripts:'dangerously'});w=dom.window;$=id=>w.document.getElementById(id);w.crypto.randomUUID=randomUUID;w.TextDecoder=TextDecoder;w.setInterval=()=>0;
  page={requests:0,actions:new Set(),readers:0,errors:[],loaded:{'index.html':info.web_hashes['index.html']}};const current=page;
  for(const name of ['onclick','onchange','oninput','onsubmit']){
    const d=Object.getOwnPropertyDescriptor(w.HTMLElement.prototype,name);assert(d?.set);
    Object.defineProperty(w.HTMLElement.prototype,name,{...d,set(fn){d.set.call(this,typeof fn==='function'?function(...args){const r=fn.apply(this,args);if(r?.then){current.actions.add(r);r.then(()=>current.actions.delete(r),e=>{current.errors.push(e);current.actions.delete(r);});}return r;}:fn);}});
  }
  w.addEventListener('error',e=>current.errors.push(e.error||Error(e.message)));
  const RealReader=w.FileReader;
  w.FileReader=class extends RealReader{
    readAsArrayBuffer(file){
      current.readers++;let done=false;const end=()=>{if(!done){done=true;current.readers--;}};
      const loaded=this.onload;this.onload=e=>{const deliver=()=>{try{loaded?.call(this,e);}finally{end();}};if(mode==='hold-file'){mode='normal';heldFiles.push(deliver);}else deliver();};
      this.addEventListener('abort',end);this.addEventListener('error',end);super.readAsArrayBuffer(file);
    }
  };
  w.fetch=async(url,opts={})=>{
    const target=new URL(url,info.base);assert.equal(target.origin,info.base);const method=opts.method||'GET';const req={method,path:target.pathname,...(opts.body?{body:JSON.parse(opts.body)}:{})};requests.push(req);current.requests++;
    try{
      if(mode==='hold-read-loss' && method==='GET' && target.pathname.endsWith('/resources')){mode='normal';await new Promise(r=>heldRead=r);heldRead=null;throw TypeError('Synthetic late list read failure');}
      if(mode==='read-after-save' && method==='GET' && target.pathname.endsWith('/resources')){mode='normal';throw TypeError('Synthetic accepted-save subsequent read loss');}
      const response=await fetch(target,opts),data=await response.arrayBuffer();
      if(method==='POST' && target.pathname.endsWith('/resources')){
        assert.equal(response.status,201);req.accepted=JSON.parse(Buffer.from(data).toString());
        if(mode==='lost-save'){mode='normal';throw TypeError('Synthetic lost successful resource acceptance');}
        if(mode==='hold-save'){mode='normal';await new Promise(r=>heldSave=r);heldSave=null;}
        if(mode==='arm-read-loss'){mode='read-after-save';}
        if(mode==='arm-held-read-loss'){mode='hold-read-loss';}
        if(mode.startsWith('uncertain-')){const kind=mode.slice(10);mode='normal';return kind==='id' ? new Response(JSON.stringify({id:'res_bad'}),{status:201}) : new Response(JSON.stringify({detail:'Synthetic uncertain response'}),{status:Number(kind)});}
      }
      return new Response(data,{status:response.status,headers:response.headers});
    }finally{current.requests--;}
  };
  for(const node of [...w.document.querySelectorAll('script[src]')]){
    const file=node.getAttribute('src'),source=await(await fetch(info.base+file)).text(),name=file.slice(1),hash=createHash('sha256').update(source).digest('hex');assert.equal(hash,info.web_hashes[name]);current.loaded[name]=hash;
    const script=w.document.createElement('script');script.textContent=source;w.document.body.append(script);
  }
  $('token').value='synthetic-test-A';$('connect').click();await wait(()=>$('login').hidden,'connect');await idle();
}
function choose(data=bytes,name='真实 合成.csv',count=1){
  const file=new w.File([data],name,{type:'text/csv'});Object.defineProperty($('resource-file'),'files',{configurable:true,value:Array(count).fill(file)});
  $('resource-file').dispatchEvent(new w.Event('change'));return file;
}
async function selected(){await wait(()=>!!w.eval('resourceFileSnapshot'),'local file decoded');await idle();}
async function project(id){$('project-select').value=id;$('project-select').dispatchEvent(new w.Event('change'));await idle();}
const work=async()=>{const r=await fetch(info.base+'/test-only-worker',{method:'POST',headers:{Authorization:'Bearer synthetic-test-A','Content-Type':'application/json'},body:'{}'});assert.equal(r.status,200);};
function clear(){ $('resource-file-clear').click(); }
(async()=>{try{
  await setup();const initialPosts=posts().length;check($('resource-file').type==='file'&&!$('resource-file').multiple,'single native file picker exists');
  if(info.case==='business'){
    $('project-name').value='文件导入 合成闭环';submit('project-form');await wait(()=>[...$('project-select').options].some(o=>o.textContent==='文件导入 合成闭环'),'fresh project created');await idle();const pid=[...$('project-select').options].find(o=>o.textContent==='文件导入 合成闭环').value;await project(pid);
    check($('app-resource').options.length===0,'fresh project has no seeded material or app');const beforeFile=posts().length;
    choose();await selected();check(posts().length===beforeFile,'file choice creates no network write');
    check($('resource-file-status').textContent.includes('文件导入 合成闭环')&&$('resource-file-status').textContent.includes(bytes.length+'字节'),'name byte count and target project visible before explicit Save');
    check(w.eval('resourceFileSnapshot.content').includes('\r\n')&&!$('content').value.includes('\r'),'raw CRLF separate from normalized textarea display');
    mode='hold-save';submit('resource-form');submit('resource-form');await wait(()=>!!heldSave,'successful save receipt held');
    check(posts().length===beforeFile+1 && $('resource-save').disabled,'double submit performs one explicit resource Save');heldSave();await idle();
    const saved=posts().at(-1);check(saved.body.content===bytes.toString('utf8')&&saved.body.name==='真实 合成.csv','Save sends exact UTF8 file content including CRLF');
    check($('app-resource').options.length===1&&posts().length===beforeFile+1,'Save does not create draft release instance or run');
    $('app-name').value='本地材料 汇总';$('app-goal').value='汇总我选择的数值列';submit('app-form');await wait(()=>!$('app-preview-form').hidden,'explicit draft');await idle();const aid=w.eval('activeApp');
    $('app-column').value='amount';submit('app-preview-form');await wait(()=>$('app-output').textContent.includes('20.25'),'real preview');await idle();
    $('internal-prepare').click();await wait(()=>!!w.eval('engineering.approval'),'prepared internal snapshot');await idle();
    check($('internal-approval-detail').textContent.includes(saved.accepted.id),'approval binds actually imported resource');
    $('internal-approval-ack').checked=true;$('internal-approval-ack').dispatchEvent(new w.Event('change'));$('internal-commit').click();await wait(()=>$('internal-releases').querySelector('button'),'explicit internal release');await idle();
    $('internal-releases').querySelector('button').click();await wait(()=>!$('internal-run-form').hidden,'explicit instance');await idle();const instance=w.eval('engineering.instance.id'),release=w.eval('engineering.instance.release_id'),results=[];
    for(const [column,expected,version] of [['amount','20.25',1],['quantity','9',2]]){
      $('internal-column').value=column;submit('internal-run-form');await wait(()=>w.eval('engineering.run?.status')==='QUEUED','new persistent queued AppRun');await idle();const id=w.eval('engineering.run.id');await work();$('internal-refresh').click();await idle();
      const reply=await fetch(info.base+`/api/internal/instances/${instance}/runs/${id}`,{headers:{Authorization:'Bearer synthetic-test-A'}}),r=await reply.json();assert.equal(reply.status,200);
      check(r.status==='SUCCEEDED'&&r.result.sum===expected&&r.result_version===version,column+' normal worker creates independent durable result');results.push({id,column,sum:r.result.sum,version});
      check($('internal-data').textContent.includes('v'+version),'version visible through actual product GET');
    }
    check(results[0].id!==results[1].id,'new numeric input creates a different actual run');const coldPosts=posts().length;await setup();$('project-select').value=pid;$('project-select').dispatchEvent(new w.Event('change'));await idle();
    await wait(()=>$('use-list').querySelector('button'),'cold saved instance');$('use-list').querySelector('button').click();await wait(()=>$('use-history').textContent.includes('v2'),'cold results');await idle();
    check($('use-history').textContent.includes('v1')&&posts().length===coldPosts,'cold page retains both durable results with zero POST');check($('use-info').textContent.includes('未发布内部版本'),'formal publication remains closed');
    Object.assign(info,{project_id:pid,app_id:aid,resource_id:saved.accepted.id,instance_id:instance,release_id:release,results});
  } else if(info.case==='guards'){
    for(const [data,name,count,prompt] of [[Buffer.from([0xc3,0x28]),'bad.csv',1,'UTF-8'],[Buffer.concat([Buffer.from([0xef,0xbb,0xbf]),bytes]),'bom.csv',1,'BOM'],[Buffer.alloc(32769,97),'big.csv',1,'32768'],[bytes,'x.txt',1,'.csv'],[bytes,'two.csv',2,'一个'],[Buffer.alloc(0),'empty.csv',1,'32768'],[Buffer.from('a\0,b'),'nul.csv',1,'空字节']]){
      choose(data,name,count);await idle();check(!w.eval('resourceFileSnapshot')&&$('resource-file-status').textContent.includes(prompt)&&!$('content').value,'invalid '+name+' rejected before Save');
    }
    choose(Buffer.alloc(32768,97),'limit.csv');await selected();check(w.eval('resourceFileSnapshot.bytes')===32768,'exact byte limit can be read without saving');clear();
    for(const action of ['cancel','replace','edit','project-ABA','identity']){
      mode='hold-file';choose();await wait(()=>heldFiles.length===1,'real FileReader completion held');
      if(action==='cancel')clear();
      if(action==='replace'){choose(Buffer.from('amount\n2\n'),'replacement.csv');await selectedExceptHeld();}
      if(action==='edit'){$('content').value='manual draft';$('content').dispatchEvent(new w.Event('input'));}
      if(action==='project-ABA'){await projectExceptHeld(info.other);await projectExceptHeld(info.project);}
      if(action==='identity'){$('token').value='synthetic-test-B';$('connect').click();await wait(()=>$('project-select').selectedOptions[0]?.textContent==='Other identity project','identity B');}
      heldFiles.shift()();await idle();
      check(action==='replace' ? $('resource-name').value==='replacement.csv'&&$('content').value==='amount\n2\n' : action==='edit' ? $('content').value==='manual draft'&&!w.eval('resourceFileSnapshot') : $('content').value===''&&!w.eval('resourceFileSnapshot'),'late file cannot overwrite '+action);
      if(action!=='identity')clear();
    }
    check(posts().length===initialPosts,'all file validation and navigation guards perform zero POST');
  } else if(info.case==='lost-save'){
    choose();await selected();mode='lost-save';submit('resource-form');submit('resource-form');await wait(()=>$('resource-file-status').textContent.includes('回执未知'),'unknown Save');await idle();
    const frozen=posts().at(-1);check(posts().length===initialPosts+1&&$('resource-save').disabled&&!$('resource-save-read').hidden,'lost acceptance retains one Save and blocks resubmission');
    submit('resource-form');$('resource-save-read').click();await idle();check(posts().length===initialPosts+1&&$('materials').textContent.includes('真实 合成.csv'),'explicit verification only reads actual accepted material');
    await project(info.other);check($('content').value==='','foreign project clears unknown material');await project(info.project);check($('resource-save').disabled&&$('resource-file-status').textContent.includes('回执未知'),'project ABA does not forget unknown Save');
    check(JSON.stringify(w.eval('resourceSaveRequests.get(resourceSaveKey()).body'))===JSON.stringify(frozen.body),'original unknown body remains frozen');$('resource-save-reset').click();await idle();check(posts().length===initialPosts+1&&!$('content').value,'explicit reset does not accept or replay unknown Save');
  } else if(info.case==='read-after-save'){
    choose();await selected();mode='arm-read-loss';submit('resource-form');await wait(()=>$('resource-file-status').textContent.includes('保存回执已收到'),'accepted Save read failure');await idle();
    check(posts().length===initialPosts+1&&!$('content').value,'accepted Save list failure clears intent and never repeats writes');await w.refresh();await idle();check($('materials').textContent.includes('真实 合成.csv')&&posts().length===initialPosts+1,'manual read restores list without creating downstream objects');
  } else if(info.case==='uncertain-response'){
    for(const kind of ['id','408','425','429']){
      choose();await selected();const count=posts().length;mode='uncertain-'+kind;submit('resource-form');await wait(()=>$('resource-file-status').textContent.includes('回执未知'),'uncertain '+kind);await idle();
      submit('resource-form');$('resource-save-read').click();await idle();check(posts().length===count+1&&$('resource-save').disabled,kind+' accepted but uncertain reply cannot release or repeat Save');
      $('resource-save-reset').click();await idle();
    }
  } else if(info.case==='read-ABA'){
    choose();await selected();mode='arm-held-read-loss';submit('resource-form');await wait(()=>!!heldRead,'accepted Save followup list read held');
    await projectExceptHeld(info.other);await projectExceptHeld(info.project);choose(Buffer.from('amount\n77\n'),'new-intent.csv');await selectedExceptHeldRead();const status=$('resource-file-status').textContent;
    heldRead();await idle();check($('resource-name').value==='new-intent.csv'&&$('resource-file-status').textContent===status,'old accepted Save late read failure cannot append into new material context');check(posts().length===initialPosts+1,'late read failure never repeats Save');
  } else if(info.case==='save-ABA'){
    choose();await selected();mode='hold-save';submit('resource-form');await wait(()=>!!heldSave,'actual accepted Save held');
    await projectExceptHeld(info.other);check($('content').value==='','late Save cannot fill another project');await projectExceptHeld(info.project);
    const generation=w.eval('resourceFileGeneration'),reads=requests.length;heldSave();await idle();check(w.eval('resourceFileGeneration')===generation&&$('resource-file-status').textContent.includes('先前保存已接受'),'accepted reply across project ABA preserves new view generation and requests explicit read');
    check(posts().length===initialPosts+1&&!$('resource-save-read').hidden&&requests.length===reads,'late acceptance does not automatically refresh or create downstream objects');
    $('resource-save-read').click();await idle();check($('materials').textContent.includes('真实 合成.csv')&&posts().length===initialPosts+1,'manual late receipt read finds persisted file with no extra Save');
    $('resource-save-reset').click();await idle();check(!w.eval('resourceSaveRequests.has(resourceSaveKey())')&&$('content').value==='','explicit completed-intent reset is read/write free');
  } else if(info.case==='manual'){
    choose();await selected();$('resource-name').value='manual.csv';$('content').value='amount,quantity\n3,8\n';$('content').dispatchEvent(new w.Event('input'));
    check(!w.eval('resourceFileSnapshot')&&$('resource-file-status').textContent.includes('手工文本模式'),'manual edit explicitly removes original file binding');submit('resource-form');await idle();check(posts().at(-1).body.content==='amount,quantity\n3,8\n','existing text Save uses edited input');
  }
  await close();const result={status:'PASS',case:info.case,checks,pages,requests,real_model_requests:0,browser:'NOT_RUN',windows:'NOT_RUN',...(info.case==='business'?{project_id:info.project_id,app_id:info.app_id,resource_id:info.resource_id,release_id:info.release_id,instance_id:info.instance_id,results:info.results}:{})};fs.writeFileSync(path.join(root,'results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify({status:result.status,case:info.case,checks:checks.length,pages:pages.length}));
}catch(e){fs.writeFileSync(path.join(root,'failure.json'),JSON.stringify({checks,error:e.stack},null,2));console.error(e.stack);process.exitCode=1;}finally{heldSave?.();heldRead?.();while(heldFiles.length)heldFiles.shift()();try{await close();}catch(e){console.error(e.stack);process.exitCode=1;}}})();
async function selectedExceptHeld(){await wait(()=>w.eval('resourceFileSnapshot?.name')==='replacement.csv','replacement read');await wait(()=>page.requests===0&&page.actions.size===0,'replacement actions');}
async function projectExceptHeld(id){$('project-select').value=id;$('project-select').dispatchEvent(new w.Event('change'));const held=heldSave||heldRead ? 1 : 0;await wait(()=>page.requests===held&&page.actions.size===held,'navigation completes while original I/O remains held');}
async function selectedExceptHeldRead(){await wait(()=>w.eval('resourceFileSnapshot?.name')==='new-intent.csv','new file loaded during held old read');await wait(()=>page.readers===0,'new file reader complete');}
