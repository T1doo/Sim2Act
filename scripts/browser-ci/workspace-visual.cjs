'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),adapter=require('./goal-history-state.cjs');
const file=path.resolve(__dirname,'../../docs/evidence/goal-history-visual-candidate-20261025/fixture.json');
const raw=fs.readFileSync(file,'utf8').replace(/\r\n/g,'\n');
assert.equal(crypto.createHash('sha256').update(raw).digest('hex'),'786c98fa304331545baf11b62d3e8dbc1c0cf097493d1b8288f02ef8be228074');
const fixture=JSON.parse(raw),hashes={"index.html": "475393d089cd4de947b08f7c79bb2793efb1322e3dde2de9e6a49edefee8c2b3", "app.css": "2ee9b73ddfc5b9bede4bf09fc4c6643ef5c3316b4a7951ad04e1477fa1d3df09", "app.js": "114849ec122f2cd68b5b0d4c4f4b2191b46f67bb34d48c8be0eae21b6cbea467", "natural-goal.js": "7b15942eecfc256dea39cb158fbdac0b923faad7f4530b8d71d3479f694f8a03"};
function responseFor(info,method,pathname){assert.equal(info.project,fixture.project);return adapter.responseFor(fixture,method,pathname);}
async function runWorkspaceVisual(args){
 for(const [n,h] of Object.entries(hashes))assert.equal(args.info.visual_source.asset_lf_sha256['src/sim2act/web/'+n],h);
 args.result.visual={capture_revision:'history-unknown-four-frame-v1',product:'cfe70c378b31afa51358396abe122f0958c88fb1',execution:args.info.visual_source.commit,fixture_sha256:'786c98fa304331545baf11b62d3e8dbc1c0cf097493d1b8288f02ef8be228074',classification:fixture.classification};
 await adapter.capture({...args,fixture});
 args.check('four bounded synthetic UI frames, zero writes and errors',args.result.screenshots===4&&args.result.counts.business_post===0&&args.result.counts.blocked===0&&!args.result.pageErrors.length);
 args.result.receipts=[];args.result.status='PASS';
}
module.exports={responseFor,runWorkspaceVisual};
