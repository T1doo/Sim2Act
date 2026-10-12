"use strict";
// CONTROLLED local-source JSDOM scheduling only. No HTTP, Worker, native browser,
// real owner signoff or provider. The deferred promises must use the Window realm.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{JSDOM}=require('jsdom');
const scenario=process.argv[2],sourcePath=process.argv[3],outputPath=process.argv[4],base=process.argv[5]||path.dirname(sourcePath);
assert(['initial','refresh','recover','action-readback','initial-edit'].includes(scenario));
const source=fs.readFileSync(sourcePath,'utf8'),internal=fs.readFileSync(path.join(base,'internal.js'),'utf8');
const engineeringCurrent=internal.match(/function engineeringCurrent\(view\) \{[\s\S]*?\n\}/)[0];
const dom=new JSDOM(fs.readFileSync(path.join(base,'index.html'),'utf8'),{runScripts:'outside-only',url:'http://controlled.invalid/'}),w=dom.window;
w.$=id=>w.document.getElementById(id);w.safe=fn=>fn;w.token='synthetic';w.activeApp='controlled-app';w.appSelectionGeneration=9;w.workspaceSelectionGeneration=3;
w.crypto.randomUUID=()=> 'controlled-owner-request';
w.$('project-select').append(new w.Option('project','controlled-project'));w.$('project-select').value='controlled-project';
w.engineering={token:w.token,project:'controlled-project',app:w.activeApp,appGeneration:9,instanceGeneration:1,instance:{id:'controlled-instance',principal_id:'controlled-principal',runs:[]}};
w.fakeView={engineering:w.engineering,instanceGeneration:1,token:w.token,project:'controlled-project',principal:'controlled-principal',app:w.activeApp,iid:'controlled-instance',state:{sequence:0,content_access:true},busy:false,readGeneration:0};
w.pending=[];w.events=[];
w.eval("globalThis.api=(url,method='GET',body)=>new Promise((resolve,reject)=>{pending.push({resolve,reject,url,method,body});events.push(method+' '+pending.length);});");
w.eval(engineeringCurrent+'\n'+source+'\n'+`ownerHash=async()=>"a".repeat(64);
 globalThis.probe={init(){ownerView=globalThis.fakeView;},initial(){return openOwnerReview(globalThis.engineering);},read(){return ownerRead(ownerView);},action(){return ownerAction({command:"PREPARE"});},generation(){return ownerView.readGeneration;},pending(){return ownerPending.get(ownerKey(ownerView));},edit(){return ownerEditGeneration;},seed(){ownerPending.set(ownerKey(ownerView),{command:"PREPARE",request_key:"original-key",expected_sequence:0});}};`);
(async()=>{
 w.probe.init();let caller,oldIndex=0;
 if(['initial','initial-edit'].includes(scenario))caller=w.probe.initial();
 if(scenario==='refresh')caller=w.$('owner-refresh').onclick();
 if(scenario==='recover'){w.probe.seed();w.$('owner-key').value='original-key';caller=w.$('owner-recover').onclick();}
 if(scenario==='action-readback'){
  caller=w.probe.action();assert.equal(w.pending.length,1);assert.equal(w.pending[0].method,'POST');
  w.pending[0].resolve({formal_publication_enabled:false,record:{request_key:w.pending[0].body.request_key,request_fingerprint:'a'.repeat(64)}});
  for(let n=0;w.pending.length<2&&n<50;n++)await new Promise(setImmediate);
  assert.equal(w.pending.length,2,'POST response starts the original key readback');oldIndex=1;
 }
 assert.equal(w.pending[oldIndex].method,'GET');
 const preservedPending=JSON.stringify(w.probe.pending()),oldGeneration=w.probe.generation(),oldEdit=w.probe.edit(),inputEvents=[];
 w.pending[oldIndex].reject(Error('OLD '+scenario+' ERROR'));
 queueMicrotask(()=>{
  if(scenario==='initial-edit'){
   w.events.push('input edit and historyUndo between inner throw and outer catch');
   const key=w.$('owner-key'),original=key.value;
   key.value='EDIT';const input=new w.InputEvent('input',{bubbles:true,inputType:'insertText',data:'EDIT'});key.dispatchEvent(input);inputEvents.push({inputType:input.inputType,isTrusted:input.isTrusted});
   key.value=original;const undo=new w.InputEvent('input',{bubbles:true,inputType:'historyUndo',data:null});key.dispatchEvent(undo);inputEvents.push({inputType:undo.inputType,isTrusted:undo.isTrusted});
   w.$('owner-status').textContent='NEWER OWNER EDIT ACTIVE';
  }else{w.events.push('new read starts between inner throw and outer catch');w.probe.read();w.$('owner-status').textContent='NEWER READ ACTIVE';}
 });
 await caller;
 const actual=w.$('owner-status').textContent,postCount=w.pending.filter(x=>x.method==='POST').length;
 const checks={older_error_not_rendered:actual===(scenario==='initial-edit'?'NEWER OWNER EDIT ACTIVE':'NEWER READ ACTIVE'),read_generation_exact_delta:w.probe.generation()===oldGeneration+(scenario==='initial-edit'?0:1),get_count_exact:w.pending.filter(x=>x.method==='GET').length===(scenario==='initial-edit'?1:2),no_automatic_post:postCount===(scenario==='action-readback'?1:0),original_pending_unchanged:JSON.stringify(w.probe.pending())===preservedPending,edit_generation_exact_delta:w.probe.edit()===oldEdit+(scenario==='initial-edit'?2:0)};
 const status=Object.values(checks).every(Boolean)?'PASS':'FAIL';
 fs.writeFileSync(outputPath,JSON.stringify({status,scenario,classification:'CONTROLLED_LOCAL_SOURCE_JSDOM_MICROTASK',source_path:sourcePath,source_sha256:crypto.createHash('sha256').update(source).digest('hex'),http:'NOT_RUN',worker:'NOT_RUN',native_browser:'NOT_RUN',live_model_requests:0,real_owner_semantic_signoff:'NOT_RUN',digest:'CONTROLLED constant; digest timing not covered here',checks,actual_status:actual,old_generation:oldGeneration,new_generation:w.probe.generation(),events:w.events,input_events:inputEvents,native_os_undo:'NOT_RUN',request_methods:w.pending.map(x=>x.method)},null,2)+'\n');
 console.log(JSON.stringify({status,scenario,checks}));dom.window.close();assert.equal(status,'PASS','outer caller must discard old read failure after a newer read starts');
})().catch(e=>{console.error(e.stack);dom.window.close();process.exitCode=1;});
