'use strict';
// Full served scripts; clipboard insertion and IME events are explicit DOM adapters.
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),pending=new Map(),requests=[],assets=[],checks=[],runIds=[];
let serial=0,dom,w,$,active=0;
readline.createInterface({input:process.stdin}).on('line',line=>{const r=JSON.parse(line),resolve=pending.get(r.id);assert(resolve);pending.delete(r.id);resolve(r);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+'\n');});
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
const wait=async(test,label)=>{const end=Date.now()+12000;while(Date.now()<end){if(test())return;await new Promise(r=>setTimeout(r,5));}throw Error('bounded wait: '+label);};
function visible(el){if(!el?.isConnected)return false;for(let p=el;p;p=p.parentElement)if(p.hidden||w.getComputedStyle(p).display==='none')return false;return true;}
async function click(value){const el=typeof value==='string'?$(value):value;assert(visible(el),'visible click '+value);assert(!el.matches(':disabled'),'enabled click '+value);const work=[],restore=[];
 for(const [node,key]of [[el,'onclick'],[el.form,'onsubmit']]){const fn=node?.[key];if(typeof fn!=='function')continue;const wrap=function(e){const result=fn.call(this,e);work.push(Promise.resolve(result));return result;};node[key]=wrap;restore.push(()=>{if(node[key]===wrap)node[key]=fn;});}
 try{el.focus();el.click();await Promise.all(work);}finally{restore.forEach(fn=>fn());}}
const posts=()=>requests.filter(r=>r.method==='POST');
const control=async command=>assert.equal((await rpc({command})).status,200);
function input(el,value,type='insertText',composing=false){el.value=value;el.dispatchEvent(new w.InputEvent('input',{bubbles:true,inputType:type,isComposing:composing,data:value}));}
function paste(el,text){
 const event=new w.Event('paste',{bubbles:true,cancelable:true});Object.defineProperty(event,'clipboardData',{value:{getData:()=>text}});el.dispatchEvent(event);
 const before=new w.InputEvent('beforeinput',{bubbles:true,cancelable:true,inputType:'insertFromPaste',data:text});el.dispatchEvent(before);
 assert(!event.defaultPrevented&&!before.defaultPrevented,'product does not cancel clipboard insertion');
 // JSDOM has no trusted clipboard default insertion; emulate only that default.
 el.setRangeText(text,el.selectionStart,el.selectionEnd,'end');el.dispatchEvent(new w.InputEvent('input',{bubbles:true,inputType:'insertFromPaste',data:text}));
}
async function setup(){
 const load=async path=>{const r=await rpc({method:'GET',path});assert.equal(r.status,200);assets.push({path,sha256:crypto.createHash('sha256').update(r.text).digest('hex')});return r.text;};
 dom=new JSDOM(await load('/'),{url:'http://testserver/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.setInterval=()=>0;
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{active++;const request={method:options.method||'GET',path,body:options.body?JSON.parse(options.body):undefined};requests.push(request);
  try{const r=await rpc({...request,headers:options.headers});request.status=r.status;
   if(request.method==='POST'||/\/runs\/[^/]+$/.test(path))request.response=JSON.parse(r.text);
   return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
  }finally{active--;}};
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(script.getAttribute('src'));w.document.body.append(node);}
 await wait(()=>active===0&&pending.size===0,'initial reads');await control('readonly');
}
async function events(){
 const fields=[...w.document.querySelectorAll('[data-term-input]')];assert.equal(fields.length,7);
 const variants=['中'.repeat(80),'中'.repeat(81),'😀'.repeat(41),'😀'.repeat(80),'😀'.repeat(81),'中😀'.repeat(40),'中😀'.repeat(40)+'中','e\u0301'.repeat(40)];
 for(const el of fields){
  el.disabled=false;el.required=false;check(!el.hasAttribute('maxlength')&&el.pattern==='[\\s\\S]{0,80}',el.id+' uses a code-point pattern without a truncating limit');
  w.bindTextTermInput(el);check(w.document.querySelectorAll('#'+el.id+'-limit').length===1&&el.getAttribute('aria-describedby').split(' ').includes(el.id+'-limit'),el.id+' has one associated counter');
  for(const value of variants){input(el,value);const count=Array.from(value).length;assert.equal(el.value,value);assert.equal(w.textTermReady(el),count<=80);assert.equal(el.validity.patternMismatch,count>80);assert($(el.id+'-limit').textContent.startsWith(count+'/80'));}
  input(el,'中'.repeat(79));el.setSelectionRange(79,79);paste(el,'😀');assert.equal(el.value,'中'.repeat(79)+'😀');assert.equal(el.selectionStart,81);assert.equal(w.textTermReady(el),true);
  paste(el,'😀');assert.equal(el.value,'中'.repeat(79)+'😀😀');assert.equal(w.textTermReady(el),false);check(el.value.isWellFormed(),el.id+' paste preserves complete surrogate pairs and over-limit text');
  el.dispatchEvent(new w.CompositionEvent('compositionstart',{bubbles:true}));input(el,'😀'.repeat(80),'insertCompositionText',true);assert.equal(w.textTermReady(el),false);assert($(el.id+'-limit').textContent.includes('组合输入'));
  el.dispatchEvent(new w.InputEvent('input',{bubbles:true,isComposing:false}));assert.equal(w.textTermReady(el),false);
  el.dispatchEvent(new w.CompositionEvent('compositionend',{bubbles:true,data:el.value}));assert.equal(w.textTermReady(el),true);assert.equal(el.value,'😀'.repeat(80));
  el.dispatchEvent(new w.CompositionEvent('compositionstart',{bubbles:true}));input(el,'😀'.repeat(81),'insertCompositionText',true);assert(!el.hasAttribute('aria-invalid'));el.dispatchEvent(new w.CompositionEvent('compositionend',{bubbles:true}));assert.equal(w.textTermReady(el),false);assert.equal(el.getAttribute('aria-invalid'),'true');check(el.value==='😀'.repeat(81),el.id+' composition ends with validation and no value rewrite');
 }
 for(const prefix of ['app','internal']){w.showTextWorkflowInputs(prefix,false);assert($(prefix+'-workflow-a').disabled&&$(prefix+'-workflow-b').disabled);assert(!$(prefix+'-workflow-a').willValidate);w.showTextWorkflowInputs(prefix,true);assert(!$(prefix+'-workflow-a').disabled&&$(prefix+'-workflow-a').validity.patternMismatch);w.showTextWorkflowInputs(prefix,false);}
 input($('text-continuation-term'),'😀'.repeat(81));await w.tcSubmit('preview');$('text-continuation-term').dispatchEvent(new w.CompositionEvent('compositionstart'));input($('text-continuation-term'),'😀'.repeat(80),'insertCompositionText',true);await w.tcSubmit('preview');
 check(posts().length===0,'field event matrix, hidden groups and blocked continuation preview produce no write');await control('readonly');
}
async function open(){await click($('use-list').querySelector(`[data-use-family="LITERAL_TEXT"][data-app-id="${info.app}"] button`));}
async function use(){
 $('token').value='synthetic-test-A';await click('connect');await click(w.document.querySelector('[data-tab="apps"]'));await open();
 const app=$('app-agent-term');input(app,'😀'.repeat(81));let n=posts().length;await click('app-preview-submit');await $('app-preview-form').onsubmit(new w.Event('submit',{cancelable:true}));await click('internal-prepare');check(posts().length===n,'81 blocks both native-form adapter/direct preview handler and explicit sample approval');await control('readonly');
 app.dispatchEvent(new w.CompositionEvent('compositionstart',{bubbles:true}));input(app,'😀'.repeat(80),'insertCompositionText',true);await click('app-preview-submit');await click('internal-prepare');check(posts().length===n,'active IME never submits preview or approval');
 app.dispatchEvent(new w.CompositionEvent('compositionend',{bubbles:true}));await click('internal-prepare');check(posts().length===n+1&&posts().at(-1).body.sample_input.term==='😀'.repeat(80)&&posts().at(-1).status===201,'committed80-code-point sample uses original approval endpoint');await control('checkpoint');
 input(app,'');paste(app,'😀'.repeat(80));await click('app-preview-submit');check(posts().length===n+2&&posts().at(-1).response.output.term==='😀'.repeat(80),'whole80-code-point paste reaches actual preview unchanged');check(app.value===''&&$('app-agent-term-limit').textContent.startsWith('0/80'),'programmatic app reopen refreshes counter');await control('checkpoint');
 const row=[...$('internal-instances').children].find(r=>r.textContent.includes(info.instance));await click(row.querySelector('button'));
 const field=$('internal-term');n=posts().length;input(field,'😀'.repeat(81));await click('internal-run-submit');await $('internal-run-form').onsubmit(new w.Event('submit',{cancelable:true}));check(posts().length===n&&!w.eval('engineeringPending.has(engineering.instance.id)'),'81 creates neither POST nor durable intent');await control('readonly');
 field.dispatchEvent(new w.CompositionEvent('compositionstart',{bubbles:true}));input(field,'😀'.repeat(80),'insertCompositionText',true);await click('internal-run-submit');check(posts().length===n,'IME80 creates no Run before compositionend');field.dispatchEvent(new w.CompositionEvent('compositionend',{bubbles:true}));
 for(const term of ['中'.repeat(80),'😀'.repeat(80),'中😀'.repeat(40)]){input(field,'');paste(field,term);const before=posts().length;const work=click('internal-run-submit');$('internal-run-submit').click();await work;check(posts().length===before+1&&posts().at(-1).body.input.term===term,'valid80-code-point new input double-click accepts one exact request');runIds.push(w.eval('engineering.run.id'));await control('worker');await click('internal-refresh');}
 check(new Set(runIds).size===3&&$('internal-data').textContent.includes('历史结果 v3'),'BMP/nonBMP/mixed inputs create three distinct real persisted versions');await control('readonly');
 const original=posts().at(-1),before=posts().length;w._termPending=structuredClone(original.body);w.eval('engineeringPending.set(engineering.instance.id,window._termPending);engineeringButtons(engineering)');input(field,'😀'.repeat(81));field.dispatchEvent(new w.CompositionEvent('compositionstart',{bubbles:true}));await click('internal-retry');check(posts().length===before+1&&JSON.stringify(posts().at(-1).body)===JSON.stringify(original.body),'existing accepted request replay uses its frozen input despite81/IME draft');check(w.eval('engineering.run.id')===runIds.at(-1),'same original request does not create a fourth Run');await control('readonly');
 input(app,'😀'.repeat(81));const csv=[...$('app-list').children].find(r=>r.textContent.includes('CSV inactive term check'));await click(csv.querySelector('button'));check(app.disabled&&field.disabled&&$('app-preview-form').checkValidity(),'CSV mode disables inactive term patterns');check(app.value===''&&$('app-agent-term-limit').textContent.startsWith('0/80'),'mode change clears stale term counter');await control('readonly');
}
(async()=>{let status='FAIL',error;
 try{await setup();if(info.scenario==='events')await events();else await use();await wait(()=>active===0&&pending.size===0,'HTTP drained');status='PASS';}
 catch(e){error=e.stack;process.stderr.write(error+'\n');process.exitCode=1;}
 finally{try{await wait(()=>active===0&&pending.size===0,'final drain');}catch(e){error=error||e.stack;process.exitCode=1;}
  fs.writeFileSync(info.output,JSON.stringify({status,error,scenario:info.scenario,checks,assets,requests,run_ids:runIds,scope:'full served JSDOM events + explicit clipboard default adapter + actual ASGI HTTP/SQLite NoModel Worker',native_ime:'NOT_RUN',native_clipboard:'NOT_RUN',native_browser:'NOT_RUN',pg:'NOT_RUN'},null,2)+'\n');dom?.window.close();process.stdout.write(JSON.stringify({done:true})+'\n');}
})();
