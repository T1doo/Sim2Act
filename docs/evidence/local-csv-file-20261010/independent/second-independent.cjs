'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),{createHash,randomUUID}=require('crypto'),{TextDecoder}=require('util'),{JSDOM}=require('jsdom');
const root=process.argv[2],cfg=JSON.parse(fs.readFileSync(path.join(root,'config.json'))),source=fs.readFileSync(path.join(root,'independent.CSV'));
let dom,w,$,network=[],checks=[],pages=[],inflight=0,mode='',release=null,fileRelease=null;const sha=b=>createHash('sha256').update(b).digest('hex');
const ok=(v,s)=>{assert(v,s);checks.push(s);};const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn,label){const end=Date.now()+6000;while(!fn()){assert(Date.now()<end,'timeout '+label);await pause(10);}}
async function idle(){await until(()=>inflight===0,'network drain');await pause(20);}
function input(id,value){$(id).value=value;$(id).dispatchEvent(new w.Event('input'));}
function act(id,event='click'){return $(id)['on'+event].call($(id),{preventDefault(){}});}
const posts=()=>network.filter(x=>x.method==='POST');const saves=()=>posts().filter(x=>x.pathname.endsWith('/resources'));
async function start(){
 if(dom){await idle();pages.push({loaded:dom.loaded,requests:network.length,error:dom.errors});dom.window.close();}
 const html=Buffer.from(await(await fetch(cfg.url)).arrayBuffer());ok(sha(html)===cfg.hashes['index.html'],'actual HTML frozen bytes');
 dom=new JSDOM(html.toString(),{url:cfg.url,runScripts:'dangerously'});w=dom.window;$=id=>w.document.getElementById(id);w.setInterval=()=>0;w.TextDecoder=TextDecoder;w.crypto.randomUUID=randomUUID;dom.loaded={'index.html':sha(html)};dom.errors=[];w.addEventListener('error',e=>dom.errors.push(String(e.error||e.message)));
 const Native=w.FileReader;
 w.FileReader=class extends Native{readAsArrayBuffer(file){const original=this.onload;this.onload=e=>{if(mode==='file-hold'){mode='';fileRelease=()=>original?.call(this,e);}else original?.call(this,e);};super.readAsArrayBuffer(file);}};
 w.fetch=async(url,opts={})=>{
  const u=new URL(url,cfg.url);assert.equal(u.origin,cfg.url);const r={method:opts.method||'GET',pathname:u.pathname,body:opts.body?JSON.parse(opts.body):null};network.push(r);inflight++;
  try{
   const response=await fetch(u,opts),body=await response.arrayBuffer();r.status=response.status;
   if(r.method==='POST'&&r.pathname.endsWith('/resources')){
    const chosen=mode;mode='';r.actual=JSON.parse(Buffer.from(body).toString());
    if(chosen==='lost')throw TypeError('Independent accepted response lost');
    if(chosen==='badid')return new Response('{"id":"res_bad"}',{status:201});
    if(chosen==='badjson')return new Response('{', {status:201});
    if(chosen.startsWith('status'))return new Response('{"detail":"Independent ambiguous response"}',{status:Number(chosen.slice(6))});
    if(chosen==='hold-save')await new Promise(resolve=>release=resolve);
    if(chosen==='arm-read')mode='hold-read';
   }else if(r.method==='GET'&&r.pathname.endsWith('/resources')&&mode==='hold-read'){
    mode='';await new Promise(resolve=>release=resolve);throw TypeError('Independent late accepted-save list error');
   }
   return new Response(body,{status:response.status,headers:response.headers});
  }finally{inflight--;}
 };
 for(const s of [...w.document.querySelectorAll('script[src]')]){const name=s.getAttribute('src').slice(1),bytes=Buffer.from(await(await fetch(cfg.url+'/'+name)).arrayBuffer());ok(sha(bytes)===cfg.hashes[name],'actual frozen script '+name);dom.loaded[name]=sha(bytes);const e=w.document.createElement('script');e.textContent=bytes.toString();w.document.body.append(e);}
 $('token').value='independent-A';await act('connect');ok($('login').hidden,'synthetic owner authenticated');await idle();
 if(cfg.case!=='old-negative'){$('project-select').value=cfg.a;await act('project-select','change');}
}
function choose(bytes=source,name='independent.CSV',count=1){Object.defineProperty($('resource-file'),'files',{configurable:true,value:Array.from({length:count},()=>new w.File([bytes],name,{type:'text/csv'}))});return act('resource-file','change');}
async function selected(){await until(()=>w.eval('resourceFileSnapshot!==null'),'file loaded');await idle();}
async function switchProject(id){$('project-select').value=id;await act('project-select','change');if(!release)await idle();}
async function save(){await act('resource-form','submit');await idle();}
async function tick(){const r=await fetch(cfg.url+'/independent-worker',{method:'POST'}),body=await r.text();fs.appendFileSync(path.join(root,'worker-responses.log'),r.status+' '+body+'\n');ok(r.ok&&JSON.parse(body).worked,'real independent worker executes queued run');}
async function prepareFile(){choose();await selected();}
(async()=>{try{
 await start();
 if(cfg.case==='old-negative'){
  let failed=false;try{assert($('resource-file'),'actual local CSV selector exists');}catch(e){failed=true;fs.writeFileSync(path.join(root,'expected-old-failure.log'),e.stack);}
  ok(failed,'exact old667 page fails new file-selector assertion');ok(posts().length===0,'old negative read-only zero POST');
 }else if(cfg.case==='business'){
  await prepareFile();ok(posts().length===0,'local file selection zero writes');ok($('content').value===source.toString().replaceAll('\r\n','\n'),'preview textarea normalization visible');await save();ok(saves().length===1&&saves()[0].body.content===source.toString(),'Save sends exact original CRLF UTF8 content');ok($('resource-file-status').textContent.includes('已保存并授权'),'acceptance displayed');
  input('app-name','Independent reusable CSV');input('app-goal','Choose an existing column');$('app-resource').value=saves()[0].actual.id;await act('app-form','submit');ok(! $('app-preview-form').hidden,'real CSV draft selected');$('app-column').value='left';await act('app-preview-form','submit');ok($('app-output').textContent.includes('1.75'),'real preview negative decimal independent sum');
  await act('internal-prepare');ok(!$('internal-approval').hidden&&$('internal-approval-detail').textContent.includes('fingerprint'),'exact internal snapshot visible before confirmation');$('internal-approval-ack').checked=true;await act('internal-approval-ack','change');await act('internal-commit');ok($('internal-releases').textContent.includes('创建独立实例'),'explicit internal Release persisted');
  const create=[...$('internal-releases').querySelectorAll('button')].find(b=>b.textContent==='创建独立实例');await create.onclick({preventDefault(){}});ok(!$('internal-run-form').hidden,'real independent instance created');const instance=w.eval('engineering.instance.id'),app=w.eval('engineering.app');
  await w.eval(`openApplicationUse(${JSON.stringify(app)},${JSON.stringify(instance)})`);
  for(const [column,total] of [['left','1.75'],['right','4']]){$('use-column').value=column;await act('use-form','submit');await tick();await act('use-refresh');ok($('use-output').textContent.includes('合计 '+total),'actual fresh result '+column+'='+total);}
  ok($('use-history').textContent.includes('v1')&&$('use-history').textContent.includes('v2'),'two durable versions displayed');const postBefore=posts().length;await start();await w.eval(`openApplicationUse(${JSON.stringify(app)},${JSON.stringify(instance)})`);ok(posts().length===postBefore,'cold reopen zero POST');ok($('use-history').textContent.includes('1.75')&&$('use-history').textContent.includes('合计 4'),'cold results preserved separately');ok($('use-acceptance').textContent.includes('NOT_RUN')&&$('use-acceptance').textContent.includes('PENDING'),'semantic/owner remain unaccepted');
 }else if(cfg.case==='limits'){
  for(const [bytes,name,count,label] of [[Buffer.alloc(0),'empty.csv',1,'empty'],[Buffer.alloc(32769),'large.csv',1,'byte cap'],[Buffer.from([239,187,191,97]),'bom.csv',1,'BOM'],[Buffer.from([255,97]),'encoding.csv',1,'invalid UTF8'],[Buffer.from('a\0b'),'nul.csv',1,'NUL'],[source,'wrong.txt',1,'extension'],[source,'x'.repeat(197)+'.csv',1,'name cap'],[source,'multi.csv',2,'multiple']]){choose(bytes,name,count);await until(()=>!w.eval('resourceFileReader'),'invalid settled');ok(w.eval('resourceFileSnapshot===null')&&$('content').value==='','invalid '+label+' clears stale file');ok(posts().length===0,'invalid '+label+' zero writes');}
  choose(Buffer.alloc(32768,97),'boundary.csv');await selected();ok(w.eval('resourceFileSnapshot.bytes')===32768,'exact byte cap locally accepted');ok(posts().length===0,'boundary read only');
 }else if(cfg.case==='file-context'){
  mode='file-hold';choose();await until(()=>fileRelease,'held FileReader completion');await act('resource-file-clear');fileRelease();fileRelease=null;ok($('content').value==='','cancel rejects stale file completion');
  mode='file-hold';choose(source,'old.csv');await until(()=>fileRelease,'old completion held');choose(Buffer.from('a,b\n2,3\n'),'new.csv');await selected();fileRelease();fileRelease=null;ok($('resource-name').value==='new.csv'&&$('content').value==='a,b\n2,3\n','newer file wins old completion');
  mode='file-hold';choose();await until(()=>fileRelease,'ABA file held');await switchProject(cfg.b);await switchProject(cfg.a);fileRelease();fileRelease=null;ok($('content').value==='','project ABA discards prior file');
  mode='file-hold';choose();await until(()=>fileRelease,'identity file held');$('token').value='independent-B';await act('connect');fileRelease();fileRelease=null;ok($('content').value==='','new identity discards prior file');ok(posts().length===0,'all file contexts zero writes');
 }else if(cfg.case==='lost'){
  await prepareFile();mode='lost';await save();ok($('resource-save').disabled&&!$('resource-save-read').hidden,'lost accepted response freezes intent');const original=saves()[0].body;await act('resource-form','submit');await switchProject(cfg.b);await switchProject(cfg.a);await act('resource-save-read');ok(saves().length===1,'retry/project ABA/list refresh never repeats unkeyed Save');ok($('content').value===original.content.replaceAll('\r\n','\n'),'UNKNOWN original text preserved');ok($('resource-file-status').textContent.includes('不能仅凭相同内容'),'hash coincidence not acceptance');
 }else if(cfg.case==='uncertain'){
  for(const kind of ['status408','status425','status429','badid','badjson']){await prepareFile();mode=kind;await save();ok($('resource-save').disabled&&!$('resource-save-read').hidden,'ambiguous '+kind+' keeps UNKNOWN');const n=saves().length;await act('resource-form','submit');await act('resource-save-read');ok(saves().length===n,'ambiguous '+kind+' no repeat or downstream POST');await act('resource-save-reset');ok(!$('resource-save').disabled&&$('content').value==='','explicit reset ends only page intent '+kind);}
 }else if(cfg.case==='accepted-aba'){
  await prepareFile();mode='hold-save';const saving=act('resource-form','submit');await until(()=>release,'accepted POST response held');const requestsBefore=network.length;await switchProject(cfg.b);await switchProject(cfg.a);const afterNavigation=network.length;release();release=null;await saving;await idle();ok(network.length===afterNavigation&&afterNavigation>requestsBefore,'late accepted response performs no automatic refresh');ok($('resource-file-status').textContent.includes('先前保存已接受')&&$('resource-save').disabled,'late acceptance preserves original intent and ID');await act('resource-save-read');ok(saves().length===1,'explicit accepted recovery GET only');await act('resource-save-reset');ok($('content').value==='','explicit reset permits new selection');
 }else if(cfg.case==='read-aba'){
  await prepareFile();mode='arm-read';const saving=act('resource-form','submit');await until(()=>release,'post-save list read held');await switchProject(cfg.b);await switchProject(cfg.a);choose(Buffer.from('a,b\n2,9\n'),'later.csv');await selected();const status=$('resource-file-status').textContent;release();release=null;await saving;await idle();ok($('resource-file-status').textContent===status&&$('resource-name').value==='later.csv','late list error cannot overwrite newer selection');ok(saves().length===1,'read-error recovery never repeats accepted Save');
 }else if(cfg.case==='manual'){
  await prepareFile();input('content','x,y\n-4,8\n');ok(w.eval('resourceFileSnapshot===null'),'manual edit revokes raw-file binding');input('resource-name','manual.csv');await save();ok(saves().length===1&&saves()[0].body.content==='x,y\n-4,8\n'&&saves()[0].body.name==='manual.csv','manual Save uses edited text not old file');
 }
 await idle();ok(dom.errors.length===0,'page has no runtime error');pages.push({loaded:dom.loaded,requests:network.length,error:dom.errors});fs.writeFileSync(path.join(root,'result.json'),JSON.stringify({status:'PASS',checks,pages,network,models:0},null,2));console.log(JSON.stringify({status:'PASS',checks:checks.length,pages:pages.length}));dom.window.close();
}catch(e){fs.writeFileSync(path.join(root,'result.json'),JSON.stringify({status:'FAIL',checks,pages,network,error:e.stack},null,2));console.error(e.stack);dom?.window.close();process.exitCode=1;}})();
