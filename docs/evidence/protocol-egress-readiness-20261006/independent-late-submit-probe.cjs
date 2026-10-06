// Pure offline probe: actual UI code, synthetic DOM, deferred fake fetch. No URLs requested.
const fs = require('fs'), vm = require('vm');
const nodes = new Map();
function node(id) {
  if (!nodes.has(id)) nodes.set(id, { value: id === 'project-select' ? 'p' : '', hidden: false, textContent: '', replaceChildren() {}, querySelectorAll() { return []; } });
  return nodes.get(id);
}
let release;
const post = new Promise(resolve => { release = resolve; });
const sandbox = { $: node, token: 'synthetic', activeRun: 'source-old', safe: value => value, crypto: { randomUUID: () => 'synthetic-key' }, fetch: async (_, opts) => {
  if (opts.method === 'POST') return post;
  return { ok: true, json: async () => ({ run_id: 'accepted-old', phase: 'source', status: 'QUEUED', semantic_status: 'UNKNOWN' }) };
} };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('src/sim2act/web/protocol.js', 'utf8'), sandbox);
vm.runInContext("protocolContext={project:'p',token,generation:protocolGeneration,selection:0,intent:0,run:{run_id:'source-old'},busy:false}; globalThis.pending=protocolSubmit('source',{goal:'synthetic'})", sandbox);
if(process.argv.includes('--null-current'))vm.runInContext('protocolContext.run=null;',sandbox);
// Mirror showRun's synchronous user intent before its pending generic GET.
vm.runInContext("protocolSelectRun('selected-new',true); activeRun='selected-new';", sandbox);
const rejectMode=process.argv.includes('--reject');
node('protocol-state').textContent='NEW-RUN-STATUS';
release(rejectMode ? {ok:false,json:async()=>({error:{code:'OLD-SUBMISSION-REJECTED'}})} : { ok: true, json: async () => ({ run_id: 'accepted-old', phase: 'source', status: 'QUEUED', semantic_status: 'UNKNOWN' }) });
sandbox.pending.then(() => {
  const observed = sandbox.activeRun;
  if(rejectMode){const closed=node('protocol-state').textContent==='NEW-RUN-STATUS';console.log(closed?'CLOSED: late rejection preserves new selection status':'REPRODUCED: late rejection overwrites new selection status');if(process.argv.includes('--assert-closed')&&!closed)process.exitCode=1;return;}
  console.log(observed === 'selected-new' ? 'CLOSED: late accepted response preserves selected-new' : 'REPRODUCED: late accepted response replaced selection with ' + observed);
  if (process.argv.includes('--assert-closed') && observed !== 'selected-new') process.exitCode = 1;
}).catch(error => { console.error(error.name); process.exitCode = 1; });
