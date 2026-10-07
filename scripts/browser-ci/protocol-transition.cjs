'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
module.exports=async function transition(root){
 const request=path.join(root,'fresh-request.json'),response=path.join(root,'fresh-response.json');
 assert(!fs.existsSync(request)&&!fs.existsSync(response),'single-use owned protocol transition');
 fs.writeFileSync(request,JSON.stringify({action:'fresh-protocol-fixture.v1'}));
 const end=Date.now()+12000;while(!fs.existsSync(response)&&Date.now()<end)await new Promise(r=>setTimeout(r,20));
 assert(fs.existsSync(response),'owned same-port protocol transition deadline');
 const receipt=JSON.parse(fs.readFileSync(response,'utf8'));assert.equal(receipt.namespace,'owned-protocol-api-transition.v1');assert.equal(receipt.status,'READY');assert.equal(receipt.old_api_joined,true);assert.equal(receipt.max_concurrent_protocol_servers,1);
 const freshRoot=path.join(root,'fresh'),info=JSON.parse(fs.readFileSync(path.join(freshRoot,'info.json'),'utf8'));assert.equal(info.port,receipt.same_port);
 return {receipt,freshRoot,info};
};
module.exports.verifyOld=async function({root,python,receipt}){
 const fixture=require('./conditional-fixture-session.cjs')({python,root});
 try{const after=await fixture.action('snapshot');assert.deepEqual(after,receipt.old_before,'sealed old experiment pool and every old table retained');receipt.old_after=after;receipt.old_all_tables_retained=true;}
 finally{await fixture.close();}
};
