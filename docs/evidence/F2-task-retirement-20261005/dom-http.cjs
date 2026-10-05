// Node/jsdom and loopback HTTP. NOT real rendering/browser/phone verification.
const {JSDOM,VirtualConsole}=require('jsdom');const fs=require('node:fs');
const results=[];const check=(name,truth)=>{if(!truth)throw Error(name);results.push({name,status:'PASS'});};
const origin='http://127.0.0.1:8071';
async function api(path,body){const r=await fetch(origin+path,{method:body?'POST':'GET',headers:{Authorization:'Bearer synthetic-pb-browser','Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});return {status:r.status,value:await r.json()};}
async function wait(fn){for(let i=0;i<100;i++){if(fn())return;await new Promise(r=>setTimeout(r,25));}throw Error('DOM timeout');}
async function page(){let errors=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));const dom=await JSDOM.fromURL(origin,{resources:'usable',runScripts:'dangerously',virtualConsole:vc,beforeParse(w){w.fetch=(p,o)=>fetch(new URL(p,origin),o);w.crypto.randomUUID=require('node:crypto').randomUUID;}});const w=dom.window,d=w.document;await wait(()=>d.getElementById('connect').onclick);d.getElementById('token').value='synthetic-pb-browser';d.getElementById('connect').click();await wait(()=>d.getElementById('app-list').children.length);return {dom,w,d,errors};}
(async()=>{
 const projects=(await api('/api/projects')).value;const pid=projects.find(x=>x.name==='SYNTHETIC source project').id;
 const source=(await api(`/api/projects/${pid}/resources`,{name:'isolated task.csv',format:'csv',content:'amount,quantity\n1.25,7\n2.75,8\n'})).value.id;
 const task=(await api(`/api/projects/${pid}/local-csv-tasks`,{resource_id:source,column:'amount',request_key:'dom-completed-task',synthetic_fixture:true,goal:'fixed_csv_exact_sum.v1'})).value;
 check('actual local task completes after tool and exact oracle',task.status==='SUCCEEDED' && task.namespace==='LOCAL_DECLARATIVE_TASK' && task.output.sum==='4.00' && task.proof.check.status==='PASS');
 const target=(await api(`/api/projects/${pid}/resources`,{name:'task-new.csv',format:'csv',content:'amount,quantity\n10,2\n30,3\n'})).value.id;
 const candidate=(await api(`/api/local-csv-tasks/${task.id}/extract`,{expected_proof_fingerprint:task.proof_fingerprint,resource_id:target,name:'SYNTHETIC retired-source candidate',request_key:'dom-extract'})).value;
 check('candidate stays unpublished',candidate.state==='PREVIEW_ONLY' && candidate.publishable===false);
 const retired=await api(`/api/local-csv-tasks/${task.id}/retire-source`,{expected_proof_fingerprint:task.proof_fingerprint,expected_source_hash:task.proof.source_hash,retain_minimal_proof:true,policy:'erase_source_retain_minimal_proof_require_current_grants.v1'});
 check('owner explicitly retires isolated source with proof policy',retired.status===200);
 const oldRead=await api(`/api/resources/${source}`);check('retired file HTTP read rejects',oldRead.status===400 && oldRead.value.error.code==='RESOURCE_UNAVAILABLE');
 const inspected=(await api(`/api/local-csv-tasks/${task.id}`)).value;check('readable proof contains no old answer or parameter values',inspected.proof_fingerprint===task.proof_fingerprint && !('input' in inspected) && !('output' in inspected) && !JSON.stringify(inspected).includes('4.00'));
 let {dom,w,d,errors}=await page();w.eval('selectWorkspace("apps")');await w.eval(`showApp('${candidate.id}')`);
 check('candidate displays actual task namespace and conservative proof scope',d.getElementById('app-origin').textContent.includes('LOCAL_DECLARATIVE_TASK') && d.getElementById('app-origin').textContent.includes('来源撤权或过期仍拒绝'));
 d.getElementById('app-column').value='amount';d.getElementById('app-preview-form').requestSubmit();await wait(()=>d.getElementById('app-output').textContent.includes('合计 40'));
 check('new input computes 40 rather than original 4',d.getElementById('app-output').textContent.includes('合计 40'));
 check('completed task candidate does not offer recursive preview extraction',d.getElementById('extraction-form').hidden);
 const bad=await api(`/api/apps/${candidate.id}/previews`,{input:{column:'missing'},request_key:'dom-bad'});check('bad new input records FAILED',bad.value.status==='FAILED' && bad.value.error.code==='INVALID_INPUT');
 check('no script errors in first DOM session',errors.length===0);dom.window.close();
 const cold=await page();await cold.w.eval(`showApp('${candidate.id}')`);check('cold session persists both success and failure history',cold.d.getElementById('app-history').textContent.includes('SUCCEEDED') && cold.d.getElementById('app-history').textContent.includes('FAILED'));
 check('cold session only reopens minimal proof with new material',cold.d.getElementById('app-origin').textContent.includes('LOCAL_DECLARATIVE_TASK') && cold.d.getElementById('app-manifest').textContent.includes(target) && !cold.d.getElementById('app-frozen-goal-text').textContent.includes('4.00'));
 cold.d.getElementById('app-column').value='quantity';cold.d.getElementById('app-preview-form').requestSubmit();await wait(()=>cold.d.getElementById('app-output').textContent.includes('合计 5'));
 check('fresh cold runtime parameter computes 5',cold.d.getElementById('app-output').textContent.includes('合计 5'));
 check('no script errors in cold DOM session',cold.errors.length===0);cold.dom.window.close();
 fs.writeFileSync(__dirname+'/dom-http-results.json',JSON.stringify({kind:'NODE_JSDOM_LOOPBACK_HTTP_NOT_BROWSER',results},null,2));console.log(JSON.stringify(results));
})().catch(e=>{console.error(e);process.exit(1);});
