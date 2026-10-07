const fs=require('fs'),vm=require('vm'),assert=require('assert'),crypto=require('crypto');
const {JSDOM}=require('/workspace/browser-tools/node_modules/jsdom');
const root='/tmp/csv-routing-hint-independent/source-4d/src/sim2act/web/';
const files=['app.js','internal.js','protocol.js','use.js','conditional-runs.js','conditional-apps.js','report-manifest.js','delivery-graph.js'];
const cases=JSON.parse(fs.readFileSync('/tmp/csv-routing-hint-independent/dom-result.json')).cases;
function setup(){
 const dom=new JSDOM(fs.readFileSync(root+'index.html','utf8'),{runScripts:'outside-only',url:'http://fixture.invalid'}),w=dom.window,ctx=dom.getInternalVMContext();const calls=[],intervals=[];let gate=null;
 const response=(data,code=200)=>({ok:code<400,status:code,json:async()=>data});
 function data(path){if(path.startsWith('/api/internal/apps/'))return {items:[]};if(path.startsWith('/api/apps/'))return {id:path.split('/').at(-1),project_id:'A',candidate:{manifest:{validation_suite_ref:'receipt.readback.v1'},actions:[{executor:{kind:'registered_tool',ref:'data.aggregate_csv'}}]}};if(path==='/health')return{mode:'mock',api:'ready',worker:'offline'};if(path==='/api/projects')return[{id:'A',name:'A'},{id:'B',name:'B'}];if(path==='/api/apps'||path.endsWith('/goal-cards')||path.endsWith('/conditional-apps')||path.endsWith('/protocol/contracts'))return{items:[]};if(path==='/api/capabilities')return{};return[];}
 w.setInterval=(fn,ms)=>{intervals.push({fn,ms});return intervals.length};w.fetch=async(path,options={})=>{calls.push({path,method:options.method||'GET'});if(gate&&!gate.consumed&&gate.path===path){gate.consumed=true;return gate.promise;}return response(data(path));};
 for(const file of files)vm.runInContext(fs.readFileSync(root+file,'utf8'),ctx,{filename:root+file});
 const run=s=>vm.runInContext(s,ctx);w.document.getElementById('project-select').innerHTML='<option value="A">A</option><option value="B">B</option>';run("token='identity-A'");assert.equal(intervals.length,3);assert.equal(intervals[0].ms,2500);
 function hold(path){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});gate={path,promise,resolve,reject,consumed:false};return gate;}
 return{dom,w,run,calls,hold,tick:intervals[0].fn,response};
}
async function flush(){for(let i=0;i<20;i++)await new Promise(resolve=>setImmediate(resolve));}
async function test(name,fn){const s=setup();try{await fn(s);assert(s.calls.every(c=>c.method==='GET'),'automatic nonGET');cases.push({name,status:'PASS',requests:s.calls.length,methods:[...new Set(s.calls.map(c=>c.method))]});console.log(JSON.stringify(cases.at(-1)));}finally{s.dom.window.close();}}
(async()=>{
 await test('identity_ABA_late_inspect_cannot_restore_current_list',async s=>{const g=s.hold('/api/apps/csv'),pending=s.run("refreshApplicationUse([{id:'csv',name:'old',project_id:'A'}])");await flush();for(const identity of ['identity-B','identity-A']){s.w.document.getElementById('token').value=identity;await s.w.document.getElementById('connect').onclick();}s.w.document.getElementById('use-list').textContent='IDENTITY_CURRENT';g.resolve(s.response({id:'csv',project_id:'A',candidate:{manifest:{validation_suite_ref:'receipt.readback.v1'},actions:[{executor:{kind:'registered_tool',ref:'data.aggregate_csv'}}]}}));await pending;assert.equal(s.w.document.getElementById('use-list').textContent,'IDENTITY_CURRENT');assert(!s.calls.some(c=>c.path==='/api/internal/apps/csv/instances'));});
 const report={source:'4d1a486166436babffb76c2db96e87144ac9fb1a',decision:'LIMITED_ROUTING_DOM_PASS',actual_loaded_files:files.map(file=>({path:root+file,sha256:crypto.createHash('sha256').update(fs.readFileSync(root+file)).digest('hex')})),cases,bounds:'Actual shipped8JS+index.html JSDOM; controlled fetch; actualHTTPSQLite separately. Not realHTTPDOM/PG/native/full timing.'};fs.writeFileSync('/tmp/csv-routing-hint-independent/dom-final-result.json',JSON.stringify(report,null,2));
})().catch(e=>{console.error(e.stack);process.exitCode=1});
