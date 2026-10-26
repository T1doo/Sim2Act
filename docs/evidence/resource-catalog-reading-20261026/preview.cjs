'use strict';
// Source-bound static DOM only. No browser, backend, screenshot or pixel claim.
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process'),crypto=require('node:crypto'),{JSDOM,VirtualConsole}=require('jsdom');
const base='cc4e609539e20d4e3d24a0186650e8f6fe2ce32e',out=__dirname;
const fixture={tools:['resource.read','data.aggregate_csv','artifact.save_text'],code_execution:'DISABLED',connection:{model:'intern-s2',mode:'MOCK',status:'MOCK_ENGINEERING'}};
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const manifest={base,classification:'STATIC_DOM_PREVIEW_NOT_PIXELS',fixture,source:{},files:{},http:0};
for(const version of ['before','after']){
 const assets={};for(const name of ['index.html','app.css','app.js']){assets[name]=version==='before'?cp.execFileSync('git',['show',base+':src/sim2act/web/'+name],{encoding:'utf8'}):fs.readFileSync('src/sim2act/web/'+name,'utf8');}
 manifest.source[version]=Object.fromEntries(Object.entries(assets).map(([n,s])=>[n,hash(s)]));
 for(const category of ['connections','capabilities']){
  const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
  const dom=new JSDOM(assets['index.html'],{runScripts:'dangerously',virtualConsole:vc}),w=dom.window,d=w.document,$=id=>d.getElementById(id);
  try{
   w.setInterval=()=>0;w.fetch=()=>{manifest.http++;throw Error('Preview must not use HTTP');};
   const script=d.createElement('script');script.textContent=assets['app.js'];d.body.append(script);
   $('project-select').append(new w.Option('合成排版示例','preview-project'));
   w.eval("token='synthetic-static-preview';");
   $('login').hidden=true;$('identity-switch').hidden=false;$('health').textContent='静态合成预览 · 无后台连接';
   w.renderProjectContext();w.selectWorkspace('resources');w.selectResourceCategory(category);w.renderResourceCatalog(fixture);
   if(errors.length)throw Error(errors.join('\n'));
   d.querySelectorAll('script,link[rel="stylesheet"]').forEach(n=>n.remove());
   const csp=d.createElement('meta');csp.httpEquiv='Content-Security-Policy';csp.content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; form-action 'none'; base-uri 'none'";d.head.append(csp);
   const style=d.createElement('style');style.textContent=assets['app.css'];d.head.append(style);
   const note=d.createElement('p');note.textContent='静态 DOM 对照 · 合成配置 · 不是截图或模型连通验收。按钮不连接后台；原始元数据可原生展开。';note.setAttribute('role','note');$('resources').prepend(note);
   d.title='静态预览 · '+version+' · '+category;
   const content=dom.serialize(),file=version+'-'+category+'.html';fs.writeFileSync(path.join(out,file),content);manifest.files[file]={bytes:Buffer.byteLength(content),sha256:hash(content)};
  }finally{w.close();}
 }
}
if(manifest.http)throw Error('Unexpected preview request');
fs.writeFileSync(path.join(out,'preview-manifest.json'),JSON.stringify(manifest,null,2)+'\n');console.log(JSON.stringify(manifest));
