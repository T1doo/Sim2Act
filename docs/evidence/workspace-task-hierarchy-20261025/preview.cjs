'use strict';
// Export identical synthetic state using the real before/after controllers.
// These HTML documents are static DOM previews, never screenshots or UI passes.
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process'),crypto=require('node:crypto'),{JSDOM,VirtualConsole}=require('jsdom');
const base='ef678365900f079971928f1a4631da0e6256cd82',out=__dirname;
const original=JSON.parse(fs.readFileSync('docs/evidence/protocol-source-process-recovery-20261022/original.json'));
const runs=[{id:original.run,goal_summary:'核对报销材料：提交条件、所需凭证与下一步',status:'WAITING_APPROVAL',mode:'UNKNOWN',created_at:1792800000},{id:'run_synthetic_workbench_2',goal_summary:'整理本次资料中的来源与引用',status:'RUNNING',mode:'MOCK',created_at:1792798200}];
const run={namespace:'protocol_jobs.v1',run_id:original.run,phase:'source',status:'WAITING_APPROVAL',semantic_status:'UNKNOWN',semantic_review:'WAITING_APPROVAL',owner_semantic_acceptance:'PENDING',formal_publication_enabled:false,contract_id:'protocol.synthetic.a-source.v1',version:2,fence:2,result:{protocol_result:original.captured.result}};
const digest=b=>crypto.createHash('sha256').update(b).digest('hex');
const manifest={base,classification:'STATIC_DOM_PREVIEW_NOT_BROWSER_SCREENSHOT',fixture:'existing sealed synthetic Source output plus explicitly synthetic history labels/times',requests:'in-memory GET adapter only; no HTTP',source:{},files:{}};
async function build(label){
 const files={};for(const name of ['index.html','app.js','protocol.js','app.css']){const p='src/sim2act/web/'+name;files[name]=label==='before'?cp.execFileSync('git',['show',base+':'+p],{encoding:'utf8'}):fs.readFileSync(p,'utf8');}
 manifest.source[label]=Object.fromEntries(Object.entries(files).map(([k,v])=>[k,digest(v)]));
 const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
 const dom=new JSDOM(files['index.html'],{runScripts:'dangerously',url:'http://127.0.0.1/',virtualConsole:vc}),w=dom.window,d=w.document,$=id=>d.getElementById(id);
 try {
  w.setInterval=()=>0;w.fetch=()=>{throw Error('Preview cannot use HTTP');};
  const install=code=>{const s=d.createElement('script');s.textContent=code;d.body.append(s);};install(files['app.js']);install(files['protocol.js']);
  $('project-select').append(new w.Option('合成示例 · 材料核查',original.project));$('project-select').value=original.project;
  w.eval("token='synthetic-preview';");w.refreshGoalCards=async()=>{};w.refreshApps=async()=>{};w.refreshProtocol=async()=>{};
  w.api=async p=>p.includes('/runs?')?runs:[];await w.refresh();
  $('login').hidden=true;$('identity-switch').hidden=false;$('health').textContent='合成状态预览 · 无后台连接';
  w.previewRun=run;w.eval(`activeRun=previewRun.run_id;protocolContext={token,project:${JSON.stringify(original.project)},generation:protocolGeneration,selection:0,intent:0,busy:false,run:previewRun};renderProtocolRun(protocolContext);`);
  await new Promise(r=>w.setTimeout(r,0));if(errors.length)throw Error(errors.join('\n'));
  d.querySelectorAll('script,link[rel="stylesheet"]').forEach(n=>n.remove());
  const csp=d.createElement('meta');csp.httpEquiv='Content-Security-Policy';csp.content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; form-action 'none'; base-uri 'none'";d.head.append(csp);
  const style=d.createElement('style');style.textContent=files['app.css'];d.head.append(style);
  const banner=d.createElement('p');banner.id='synthetic-workspace-banner';banner.textContent='静态 DOM 对照 · 合成示例 · 非浏览器截图。按钮不连接后台，状态不代表真实任务；请调整窗口查看待验布局。';d.body.prepend(banner);
  const result=dom.serialize(),name=label+'.html';fs.writeFileSync(path.join(out,name),result);manifest.files[name]={bytes:Buffer.byteLength(result),sha256:digest(result)};
 }finally{dom.window.close();}
}
(async()=>{await build('before');await build('after');fs.writeFileSync(path.join(out,'preview-manifest.json'),JSON.stringify(manifest,null,2)+'\n');console.log(JSON.stringify(manifest));})().catch(e=>{console.error(e);process.exitCode=1;});
