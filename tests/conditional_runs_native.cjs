'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const root=process.argv[2],python=process.argv[3],info=JSON.parse(fs.readFileSync(path.join(root,'info.json'))),base=`http://127.0.0.1:${info.port}`;
let dom,w,fixture;
async function reload(){
 dom?.window.close();dom=new JSDOM(await(await fetch(base)).text(),{url:base,runScripts:'dangerously'});w=dom.window;w.fetch=(url,opts)=>fetch(new URL(url,base),opts);
 for(const file of ['app.js','internal.js','protocol.js','use.js','conditional-runs.js']){const script=w.document.createElement('script');script.textContent=await(await fetch(base+'/'+file)).text();w.document.body.append(script);}
}
(async()=>{try{
 fixture=require('../scripts/browser-ci/conditional-fixture-session.cjs')({python,root});
 const bound=await require('../scripts/browser-ci/conditional-runs-ui.cjs')({evaluate:code=>w.eval(code),reload,info,action:fixture.action});
 // Same session/document fixture as native: all previous manual22 remain unchanged.
 const manual=await require('../scripts/browser-ci/conditional-checks-ui.cjs')({evaluate:code=>w.eval(code),reload,info,action:fixture.action});
 assert.equal(bound.checks.length,19);assert.equal(manual.checks.length,22);assert.equal(bound.actual_mock_requests,4);
 const done=fixture;fixture=null;await done.close();
 const result={status:'PASS',bound,manual,fixtureTimings:done.timings,native:'NOT_RUN',pixels:'NOT_RUN'};
 fs.writeFileSync(path.join(root,'bound-native-results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}catch(e){console.error(e.stack);process.exitCode=1;}finally{dom?.window.close();if(fixture)await fixture.close();}})();
