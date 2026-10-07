'use strict';
const fs=require('node:fs'),path=require('node:path'),{JSDOM}=require('jsdom'),{execFile}=require('node:child_process');
const execute=require('node:util').promisify(execFile),assert=require('node:assert/strict');
const root=process.argv[2],python=process.argv[3],repo=process.cwd(),info=JSON.parse(fs.readFileSync(path.join(root,'info.json'))),base=`http://127.0.0.1:${info.port}`;
let dom,window;
async function reload(){
 dom?.window.close();dom=new JSDOM(await(await fetch(base)).text(),{url:base,runScripts:'dangerously'});window=dom.window;
 window.fetch=(url,opts)=>fetch(new URL(url,base),opts);
 for(const file of ['app.js','internal.js','protocol.js','use.js']){const script=window.document.createElement('script');script.textContent=await(await fetch(base+'/'+file)).text();window.document.body.append(script);}
}
(async()=>{try{
 const result=await require('../scripts/browser-ci/conditional-checks-ui.cjs')({evaluate:code=>window.eval(code),reload,info,
  action:async name=>JSON.parse((await execute(python,['scripts/conditional-ui/fixture.py','--root',root,'--action',name],{cwd:repo,env:{...process.env,PYTHONPATH:'src'},encoding:'utf8',timeout:10000})).stdout)});
 assert.equal(result.status,'PASS');result.native='NOT_RUN';result.pixels='NOT_RUN';result.driver='same shared oracle / actual loopback HTTP and JSDOM / real poll';
 fs.writeFileSync(path.join(root,'conditional-results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}catch(e){console.error(e.stack);process.exitCode=1;}finally{dom?.window.close();}})();
