'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const [root,python]=process.argv.slice(2);let fixture;
(async()=>{try{
 fixture=require('../scripts/browser-ci/conditional-fixture-session.cjs')({python,root});
 const before=await fixture.action('snapshot');
 await assert.rejects(fixture.action('run-source'),e=>{assert.match(e.message,/action=run-source; exit=1; category=ValueError/);assert(!e.message.includes(root)&&!e.message.includes(python));return true;});
 const diagnostic={...fixture.diagnostics};await assert.rejects(fixture.close());fixture=null;
 fixture=require('../scripts/browser-ci/conditional-fixture-session.cjs')({python,root});
 const after=await fixture.action('snapshot');assert.deepEqual(after,before);await fixture.close();fixture=null;
 fs.writeFileSync(path.join(root,'closed-session-diagnostic.json'),JSON.stringify({status:'PASS',diagnostic,allTablesUnchanged:true},null,2));
}catch(e){console.error(e.stack);process.exitCode=1;}finally{if(fixture)await fixture.close();}})();
