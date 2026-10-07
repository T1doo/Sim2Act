const fs=require('fs'),{JSDOM}=require('jsdom');const root='/workspace/Sim2Act-task-recovery/src/sim2act/web';
const dom=new JSDOM(fs.readFileSync(root+'/index.html','utf8'),{url:'http://127.0.0.1:5001',runScripts:'dangerously'}),w=dom.window;w.setInterval=()=>0;
let release;
w.fetch=async(url,opts)=>{if(url==='/api/projects'&&opts.headers.Authorization==='Bearer synthetic-test-A')return await new Promise(r=>{release=()=>r({ok:false,status:403,json:async()=>({error:{code:'PERMISSION_DENIED'}})});});return {ok:true,status:200,json:async()=>url==='/api/projects'?[]:{mode:'mock'}};};
const s=w.document.createElement('script');s.textContent=fs.readFileSync(root+'/app.js','utf8');w.document.body.append(s);
(async()=>{w.document.getElementById('token').value='synthetic-test-A';const old=w.document.getElementById('connect').onclick();w.document.getElementById('token').value='synthetic-test-B';await w.document.getElementById('connect').onclick();const before=w.document.getElementById('error').textContent;release();await old;console.log(JSON.stringify({before,after:w.document.getElementById('error').textContent},null,2));w.close();})();
