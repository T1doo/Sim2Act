const assert=require('node:assert/strict');
const protocolBase='http://127.0.0.1:4444'; const protocolInfo={project:'p',other_project:'q'};
const result={protocol:{metadata:{source:{id:'r'}},conditional:{expectedNegativeURLs:['/api/projects/p/conditional-checks/sources/c','/api/projects/p/conditional-checks']}}};
const expectedProtocolError=e=>{
      if(e.kind!=='console')return false;
      const u=new URL(e.url||protocolBase);
      if(u.origin!==new URL(protocolBase).origin)return false;
      const failedReceipt=e.message.includes('net::ERR_FAILED')&&(u.pathname===`/api/projects/${protocolInfo.project}/protocol/source`||/^\/api\/projects\/[^/]+\/protocol\/runs\/[^/]+\/recover$/.test(u.pathname));
      const denied=e.message.includes('403')&&(u.pathname===`/api/projects/${protocolInfo.project}/protocol/contracts`||u.pathname===`/api/projects/${protocolInfo.other_project}/protocol/runs/${result.protocol.metadata.source?.id}`);
      const missingIcon=e.message.includes('404')&&u.pathname==='/favicon.ico';
      const conditionalNegative=result.protocol.conditional?.expectedNegativeURLs.includes(u.pathname)&&(e.message.includes('403')||e.message.includes('409'));
      return failedReceipt||denied||missingIcon||conditionalNegative;
    };
const cases=[
['expected source409',{kind:'console',url:protocolBase+'/api/projects/p/conditional-checks/sources/c',message:'Failed to load resource: 409'},true],
['expected revoked403',{kind:'console',url:protocolBase+'/api/projects/p/conditional-checks',message:'Failed to load resource: 403'},true],
['pageerror403',{kind:'pageerror',url:protocolBase+'/api/projects/p/conditional-checks',message:'403'},false],
['outside403',{kind:'console',url:'http://example.org/api/projects/p/conditional-checks',message:'403'},false],
['foreignproject403',{kind:'console',url:protocolBase+'/api/projects/q/conditional-checks',message:'403'},false],
['conditional500',{kind:'console',url:protocolBase+'/api/projects/p/conditional-checks',message:'500'},false],
['conditional404',{kind:'console',url:protocolBase+'/api/projects/p/conditional-checks',message:'404'},false],
['sourcewrongid409',{kind:'console',url:protocolBase+'/api/projects/p/conditional-checks/sources/x',message:'409'},false],
['oldprotocol409',{kind:'console',url:protocolBase+'/api/projects/p/protocol/contracts',message:'409'},false],
['unknownscript',{kind:'console',url:protocolBase+'/app.js',message:'409'},false]];
for(const [name,e,want] of cases){assert.equal(Boolean(expectedProtocolError(e)),want,name);}console.log(JSON.stringify({status:'PASS',checks:cases.map(x=>x[0]),oracle:'actual extracted classifier, no mirrored predicate'}));
