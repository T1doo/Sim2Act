const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert/strict'),{JSDOM}=require('jsdom');
const home='/tmp/sim2act-report-edit-locks-independent-20261009',root=process.env.REVIEW_WEB_ROOT||'/workspace/Sim2Act/src/sim2act/web',out=process.argv[2]||home+'/js-final';
const f=JSON.parse(fs.readFileSync(home+'/page-fixture.json','utf8'));
fs.mkdirSync(out,{recursive:true});let checks=[],hashes={},dom,w,$,calls=[];
const check=(v,label)=>{assert(v,label);checks.push(label);};
function setup(){
 if(dom)dom.window.close();dom=new JSDOM(fs.readFileSync(root+'/index.html','utf8'),{url:'http://127.0.0.1',runScripts:'dangerously'});w=dom.window;$=id=>w.document.getElementById(id);calls=[];
 w.setInterval=()=>0;w.TextEncoder=TextEncoder;Object.defineProperty(w.crypto,'subtle',{value:crypto.webcrypto.subtle});
 for(const el of w.document.querySelectorAll('script[src]')){const file=el.getAttribute('src').slice(1),code=fs.readFileSync(root+'/'+file);hashes[file]=crypto.createHash('sha256').update(code).digest('hex');const s=w.document.createElement('script');s.textContent=code.toString();w.document.body.append(s);}
 w.reviewFixture=JSON.parse(JSON.stringify(f));
 w.eval('token="synthetic-test-A";$("project-select").append(new Option("review",reviewFixture.app.project_id));$("project-select").value=reviewFixture.app.project_id;activeApp=reviewFixture.app.id;activeAppProject=reviewFixture.app.project_id;manifestContext={epoch:manifestEpoch,identity:token,generation:appSelectionGeneration,project:activeAppProject,id:activeApp,app:reviewFixture.app};deliveryContext={epoch:deliveryEpoch,identity:token,generation:appSelectionGeneration,project:activeAppProject,id:activeApp,app:reviewFixture.app,anchor:null,patches:[],busy:false};');
}
function err(code,status,detail){const e=Error(code);if(status)e.httpStatus=status;if(detail)e.detail=detail;return e;}
async function graphPolicy(error,expectRetain,label){
 setup();const g={...f.graph};delete g.cached;
 w.api=async(url,method,body)=>{calls.push({url,method,body});if(url.endsWith('/plans')){if(error)throw error;return {...g,items:[]};}if(url.endsWith('/delivery-graph'))return g;if(url.endsWith('/apps/'+f.app.id))return f.app;throw Error('unexpected '+url);};
 await w.readDeliveryGraph();
 check(Boolean(w.eval('deliveryContext.anchor'))===expectRetain,label+' anchor policy');
 check(Boolean($('delivery-proof').textContent)===expectRetain,label+' displayed current proof policy');
 check(!calls.some(c=>c.url.endsWith('/column-patches')),label+' Report never fetches CSV-only history');
 if(expectRetain&&error)check($('delivery-plans').textContent.includes('不再证明当前图'),label+' stale plan shown as unusable');
}
function proposalSetup(handler){
 setup();w.api=async(url,method,body)=>{calls.push({url,method,body});return handler(url,method,body);};
 w.eval('window.reviewItem=reviewFixture.history.history[0];window.reviewBox=presentationControls(manifestContext,reviewItem);document.body.append(reviewBox);');
 return w.document.querySelector('.report-presentation-propose');
}
function graph(){return {...f.graph,project_id:f.app.project_id,app_id:f.app.id,candidate_fingerprint:f.app.fingerprint};}
function plan(){return {project_id:f.app.project_id,app_id:f.app.id,native_outer_fingerprint:'e'.repeat(64),receipt:{revalidation_scope:'PROJECT',patch_executed:false}};}
function size(){return w.eval('presentationIntents.size');}
(async()=>{try{
 await graphPolicy(null,true,'valid empty plan history');
 await graphPolicy(err('LOCK_CONFLICT',400,'Project revalidation affects a manually locked graph'),true,'known Report lock history');
 await graphPolicy(err('VERSION_CONFLICT',409,'Historical project graph/authority/lock membership changed'),true,'exact historical project membership invalidation');
 await graphPolicy(err('VERSION_CONFLICT',409,'Independent accepted plan seal changed'),false,'tampered plan seal');
 await graphPolicy(err('PERMISSION_DENIED',403,'source unauthorized'),false,'history authorization error');
 await graphPolicy(err('GRANT_REVOKED',403),false,'history revoked grant');
 await graphPolicy(err('OUTCOME_UNKNOWN',409),false,'unclassified history error');
 setup();const originalHistory=w.deliveryHistory;w.deliveryHistory=async()=>{throw err('LOCK_CONFLICT',400);};
 w.eval('deliveryContext.app.candidate.namespace="csv"');
 await assert.rejects(()=>w.deliveryReadPlanHistory(w.eval('deliveryContext')),/LOCK_CONFLICT/);checks.push('CSV lock history never softened');w.deliveryHistory=originalHistory;
 setup();w.manualOpen(w.eval('deliveryContext'));check(!$('manual-lock-panel').hidden,'canonical Report shows public manual lock controls');
 for(const pair of [['registered_tool','intern.conditional_report'],['bounded_report','data.aggregate_csv'],['bounded_agent','intern.conditional_report']]){
  const c={app:{candidate:{actions:[{executor:{kind:pair[0],ref:pair[1]}}]}}};w.manualOpen(c);check($('manual-lock-panel').hidden,'unsupported crossed family '+pair.join('/'));
 }
 w.manualOpen({app:{candidate:{actions:[{executor:{kind:'registered_tool',ref:'data.aggregate_csv'}}]}}});check(!$('manual-lock-panel').hidden,'original CSV controls remain available');
 let button=proposalSetup(async url=>{if(url.endsWith('/derive'))return graph();if(url.endsWith('/plans'))throw err('LOCK_CONFLICT',400);throw Error('unexpected');});
 await button.onclick();check(size()===0,'first known unaccepted locked plan releases draft intent');
 const oldKey=calls.find(c=>c.url.endsWith('/plans')).body.request_key;
 await button.onclick();check(calls.filter(c=>c.url.endsWith('/plans')).at(-1).body.request_key!==oldKey,'same page after known rejection uses a fresh exact plan key');
 let phase=0;button=proposalSetup(async url=>{if(url.endsWith('/derive'))return graph();if(url.endsWith('/plans')){if(phase++===0)throw Error('lost accepted reply');throw err('LOCK_CONFLICT',400);}throw Error('unexpected');});
 await button.onclick();check(size()===1,'lost accepted plan reply retains intent');
 const original=w.eval('presentationIntents.get(presentationKey(manifestContext,reviewItem.run))');
 await button.onclick();check(size()===1&&w.eval('presentationIntents.get(presentationKey(manifestContext,reviewItem.run))')===original,'older UNKNOWN plus later lock conflict preserves original intent');
 check(JSON.stringify(calls.filter(c=>c.url.endsWith('/plans'))[0].body)===JSON.stringify(calls.filter(c=>c.url.endsWith('/plans'))[1].body),'UNKNOWN retry plan body is exact');
 phase=0;button=proposalSetup(async url=>{if(url.endsWith('/derive'))return graph();if(url.endsWith('/plans')){if(phase++===0)return {...plan(),receipt:{revalidation_scope:'PROJECT',patch_executed:true}};throw err('LOCK_CONFLICT',400);}throw Error('unexpected');});
 await button.onclick();check(size()===1&&w.eval('presentationIntents.get(presentationKey(manifestContext,reviewItem.run)).planUnknown===true'),'invalid accepted-plan shape retains UNKNOWN');
 await button.onclick();check(size()===1,'invalid shape followed by lock conflict cannot clear UNKNOWN');
 button=proposalSetup(async url=>{if(url.endsWith('/derive'))return graph();if(url.endsWith('/plans'))throw err('LOCK_CONFLICT',409);throw Error('unexpected');});
 await button.onclick();check(size()===1,'non400 lock error never releases intent');
 button=proposalSetup(async url=>{if(url.endsWith('/derive'))return graph();if(url.endsWith('/plans')){w.eval('activeApp="different-app";manifestContext=null');return plan();}throw Error('unexpected');});
 await button.onclick();check(size()===1&&calls.every(v=>!v.url.endsWith('/report-presentations')),'late plan response after selection change retains intent and sends no patch');
 check(w.eval('[...presentationIntents.values()][0].planUnknown===true'),'late plan response never clears UNKNOWN before current-context validation');
 button=proposalSetup(async url=>{if(url.endsWith('/derive'))throw err('LOCK_CONFLICT',400);throw Error('unexpected');});
 await button.onclick();check(size()===1,'derive error with same code never proves plan rejection');
 button=proposalSetup(async url=>{if(url.endsWith('/derive'))return graph();if(url.endsWith('/plans'))return plan();throw err('LOCK_CONFLICT',400);});
 await button.onclick();check(size()===1&&w.eval('!!presentationIntents.get(presentationKey(manifestContext,reviewItem.run)).plan'),'accepted plan plus rejected patch retains exact intent');
 button=proposalSetup(async url=>{if(url.endsWith('/derive'))return graph();if(url.endsWith('/plans')){w.eval('presentationIntents.set(presentationKey(manifestContext,reviewItem.run),{replacement:"new-context-intent"})');throw err('LOCK_CONFLICT',400);}throw Error('unexpected');});
 await button.onclick();check(w.eval('presentationIntents.get(presentationKey(manifestContext,reviewItem.run)).replacement')==='new-context-intent','late old closure never deletes replacement intent');
 fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({status:'PASS',checks,loaded_source_sha256:hashes},null,2));console.log(JSON.stringify({status:'PASS',checks:checks.length}));
}catch(e){fs.writeFileSync(path.join(out,'failure.json'),JSON.stringify({status:'FAIL',checks,error:String(e.stack),calls,loaded_source_sha256:hashes},null,2));console.error(e);process.exitCode=1;}finally{if(dom)dom.window.close();}})();
