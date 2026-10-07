'use strict';
const fs=require('node:fs'),path=require('node:path'),{JSDOM}=require('jsdom');
const assert=require('node:assert/strict');
const root=process.argv[2],python=process.argv[3],repo=process.cwd(),info=JSON.parse(fs.readFileSync(path.join(root,'info.json'))),base=`http://127.0.0.1:${info.port}`;
let dom,window,fixture;const captures=[],captureMode=process.env.SIM2ACT_CONDITIONAL_CAPTURE_TEST_MODE||'capture';
async function reload(){
 dom?.window.close();dom=new JSDOM(await(await fetch(base)).text(),{url:base,runScripts:'dangerously'});window=dom.window;
 window.fetch=(url,opts)=>fetch(new URL(url,base),opts);
 for(const file of ['app.js','internal.js','protocol.js','use.js']){const script=window.document.createElement('script');script.textContent=await(await fetch(base+'/'+file)).text();window.document.body.append(script);}
}
(async()=>{try{
 fixture=require('../scripts/browser-ci/conditional-fixture-session.cjs')({python,root,cwd:repo});
 const result=await require('../scripts/browser-ci/conditional-checks-ui.cjs')({evaluate:code=>window.eval(code),reload,info,
  action:fixture.action,capture:captureMode==='omit'?undefined:async(label,milestone)=>{
    if(captureMode==='fail')throw Error('Synthetic capture callback failure');
    const text=window.document.getElementById('condition-results').textContent;
    assert(text.includes('报告核对 PASS')&&text.includes('决策 '+milestone.decision));
    assert(text.includes('语义 UNKNOWN；用户确认 PENDING')&&text.includes(milestone.source.hash));
    assert.equal(milestone.source.resource_id,info.source);assert.match(milestone.source.hash,/^[a-f0-9]{64}$/);
    captures.push({label,milestone});return {label,milestone,pixels:'NOT_RUN',native:'NOT_RUN'};
  }});
 assert.deepEqual(captures.map(x=>[x.label,x.milestone.decision]),captureMode==='omit'?[]:[['protocol-desktop','BLOCK'],['protocol-narrow','UNKNOWN']]);
 result.fixtureTimings=fixture.timings;
 const completedFixture=fixture;fixture=null;await completedFixture.close();
 assert.equal(result.status,'PASS');result.native='NOT_RUN';result.pixels='NOT_RUN';result.driver='same shared oracle / actual loopback HTTP and JSDOM / real poll';
 fs.writeFileSync(path.join(root,'conditional-results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}catch(e){console.error(e.stack);process.exitCode=1;}finally{dom?.window.close();if(fixture)await fixture.close();}})();
