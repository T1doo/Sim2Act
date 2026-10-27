'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict'),{JSDOM,VirtualConsole}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),errors=[],requests=[],replies=[],checks=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(fs.readFileSync('src/sim2act/web/index.html','utf8'),{runScripts:'dangerously',virtualConsole:vc}),w=dom.window,$=id=>w.document.getElementById(id);w.setInterval=()=>0;w.fetch=async(path,options)=>{assert.equal(options.method,'GET');const response=await fetch(info.base+path,options);requests.push({path,method:options.method,status:response.status});if(response.ok)replies.push(await response.clone().json());return response;};
const script=w.document.createElement('script');script.textContent=fs.readFileSync('src/sim2act/web/app.js','utf8');w.document.body.append(script);
function select(id){$('project-select').replaceChildren(new w.Option('Synthetic project',id));}
function check(value,label){assert.ok(value,label);checks.push(label);}
(async()=>{try{
 w.eval("token='grant-owner-a';identityConnectionGeneration=1;");select(info.projectA);await w.refreshGrants();
 const actual=replies[0];check(actual.length===info.grantCount&&$('grants').children.length===actual.length,'actual owned project grants render each original returned record');
 actual.forEach((g,i)=>{const principal=g.principal_id.startsWith('runtime_')?'项目运行身份':g.principal_id.startsWith('appruntime_')?'应用预览身份':'当前使用者';const expected=`${g.tool_ref} · ${principal} · ${g.revoked?'已撤回':'有效至 '+new Date(g.expires_at*1000).toLocaleString()}`;assert.ok($('grants').children[i].textContent.startsWith(expected));});
 w.eval("identityConnectionGeneration++;clearIdentityView();token='grant-owner-b';");select(info.projectB);await w.refreshGrants();check(replies[1].length===0&&$('grants').textContent.includes('未返回授权记录')&&!$('grants').querySelector('button'),'actual empty B directory is neutral and removes A actions');
 select(info.projectA);w.eval('projectSelectionGeneration++');await assert.rejects(w.refreshGrants(),e=>e.httpStatus===403&&e.message==='PERMISSION_DENIED');
 check($('grants').textContent.includes('尚未确认')&&$('grants').querySelector('button')?.textContent.includes('只读')&&!$('grants').textContent.includes('resource.read'),'actual cross-owner 403 fails closed with read-only recovery, no prior grant records');
 check(requests.length===3&&requests.every(r=>r.method==='GET')&&requests.map(r=>r.status).join(',')==='200,200,403'&&!errors.length,'exactly three real local GETs, original rejection, no script errors');
 console.log(JSON.stringify({status:'PASS',scope:'original controller + actual loopback FastAPI/SQLite; no native browser/models',checks,requests,models:0,business_post:0},null,2));
}finally{dom.window.close();}})().catch(e=>{console.error(e.stack);process.exitCode=1;});
