const fs=require('fs'),{JSDOM}=require('jsdom');
const root='/workspace/Sim2Act-task-recovery/src/sim2act/web';
const dom=new JSDOM(fs.readFileSync(root+'/index.html','utf8'),{url:'http://127.0.0.1:5001',runScripts:'dangerously'});
const w=dom.window;w.setInterval=()=>0;w.fetch=async()=>({ok:false,status:403,json:async()=>({error:{code:'PERMISSION_DENIED'}})});
const script=w.document.createElement('script');script.textContent=fs.readFileSync(root+'/app.js','utf8');w.document.body.append(script);
const result=w.eval(`(async()=>{token='synthetic-test-A';activeRun='run_'+'a'.repeat(32);refs=['res_'+'a'.repeat(32)];$('result').textContent='A private task result';$('raw-result').textContent='A persisted run';$('events').textContent='A event';$('token').value='synthetic-test-B';await $('connect').onclick();return {error:$('error').textContent,result:$('result').textContent,raw:$('raw-result').textContent,events:$('events').textContent,activeRun,refs};})()`);
result.then(x=>{console.log(JSON.stringify(x,null,2));dom.window.close();});
