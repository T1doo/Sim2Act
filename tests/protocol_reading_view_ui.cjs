'use strict';
// Real DOM/MutationObserver and original controller. No API/model/Worker calls.
const fs=require('node:fs'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const html=fs.readFileSync('src/sim2act/web/index.html','utf8'),code=fs.readFileSync('src/sim2act/web/protocol.js','utf8');
const original=JSON.parse(fs.readFileSync('docs/evidence/protocol-source-process-recovery-20261022/original.json','utf8'));
const dom=new JSDOM(html,{runScripts:'dangerously',url:'http://127.0.0.1/'}),w=dom.window,d=w.document;
const pid=original.project,rid=original.run,checks=[];
w.$=id=>d.getElementById(id);w.safe=fn=>fn;w.fetch=()=>{throw Error('No network allowed')};
const install=text=>{const script=d.createElement('script');script.textContent=text;d.body.append(script);};
install(`let token='synthetic';let activeRun=${JSON.stringify(rid)};let workspaceSelectionGeneration=0;`);
d.getElementById('project-select').append(new w.Option('synthetic',pid));d.getElementById('project-select').value=pid;
install(code);
const run={namespace:'protocol_jobs.v1',run_id:rid,phase:'source',status:'WAITING_APPROVAL',semantic_status:'UNKNOWN',semantic_review:'WAITING_APPROVAL',owner_semantic_acceptance:'PENDING',formal_publication_enabled:false,contract_id:'protocol.synthetic.a-source.v1',version:2,fence:2,result:{protocol_result:original.captured.result}};
const tick=()=>new Promise(r=>w.setTimeout(r,0));
function check(value,label){assert(value,label);checks.push(label)}
function load(value=run){w.testRun=JSON.parse(JSON.stringify(value));w.eval(`protocolContext={token,project:${JSON.stringify(pid)},generation:protocolGeneration,selection:0,intent:0,busy:false,run:testRun};renderProtocolRun(protocolContext);`);}
(async()=>{try{
 load();await tick();
 const state=()=>d.getElementById('protocol-state-view'),summary=()=>d.getElementById('protocol-reading-view');
 check(!state().hidden&&state().textContent.includes('UNKNOWN')&&state().textContent.includes('PENDING'),'unverified and human acceptance explicit');
 check(!summary().hidden&&summary().textContent.includes('先取得主管批准')&&summary().textContent.includes('绝对截止时间：UNKNOWN'),'actual source output readable with UNKNOWN visible');
 check(d.getElementById('protocol-result').textContent===JSON.stringify(run.result,null,2),'complete original JSON bytes unchanged');
 check(state().querySelectorAll('.state-facts > div').length===4,'technical/semantic/owner/publication separated');
 check(state().querySelector('[data-tone="uncertain"] dd').textContent==='UNKNOWN','unknown has its own visual warning, not a success tone');
 check([...state().querySelectorAll('[data-tone="waiting"] dd')].map(n=>n.textContent).join('|')==='等待核查|PENDING','pending review and owner remain separately waiting');
 const identifiers=state().querySelector('details');identifiers.open=true;
 const selected=summary().querySelector('.reading-next-step'),selection=w.getSelection(),range=d.createRange();range.selectNodeContents(selected);selection.addRange(range);
 w.eval('protocolContext.run=JSON.parse(JSON.stringify(protocolContext.run));renderProtocolRun(protocolContext);');await tick();
 check(state().querySelector('details')===identifiers&&identifiers.open&&selection.toString()===selected.textContent,'unchanged real poll preserves expanded identifiers and selected text');
 w.eval(`invalidateProtocolCompletionReadback(protocolContext,null);`);await tick();
 check(summary().hidden&&state().textContent.includes('不可确认')&&d.getElementById('protocol-state').dataset.readState==='error','real read invalidation clears summary and gives explicit error');
 check(w.eval('protocolContext.run.status')==='WAITING_APPROVAL'&&d.getElementById('protocol-extract').hidden&&d.getElementById('protocol-cold-form').hidden,'real Run and original next-action gates unchanged');
 check(!state().querySelector('details')&&!summary().contains(selected),'invalidation discards old disclosure and selected protected content');
 load({...run,status:'SUCCEEDED'});await tick();
 check(state().textContent.includes('技术执行成功')&&state().querySelector('[data-tone="uncertain"] dd').textContent==='UNKNOWN'&&state().textContent.includes('PENDING')&&state().textContent.includes('未发布'),'technical success does not promote semantic, owner or publication states');
 load();await tick();w.eval(`protocolStatus(protocolContext,'正在读取…');`);await tick();check(summary().hidden&&!d.getElementById('protocol-state').dataset.presented,'transient read status cannot retain success summary');
 load();await tick();d.getElementById('protocol-result').textContent='not matching pinned result';await tick();check(summary().hidden&&state().hidden,'raw/pinned content mismatch closes extra presentation');
 const malicious=JSON.parse(JSON.stringify(run));malicious.result.protocol_result.evidence.output.case.required_next_step='<img src=x onerror=alert(1)>';
 load(malicious);await tick();check(summary().textContent.includes('<img')&&!summary().querySelector('img'),'source text is never executed or parsed as HTML');
 load();await tick();w.eval(`token='different identity';`);d.getElementById('protocol-state').textContent+=' ';await tick();check(summary().hidden&&state().hidden,'identity change cannot retain readable protected projection');
 w.eval(`token='synthetic';`);load();await tick();d.getElementById('projects').hidden=true;w.eval('protocolCompletionWorkspaceChanged()');await tick();d.getElementById('projects').hidden=false;await tick();check(summary().hidden,'close-return cannot restore cleared result without fresh read');
 const note=d.querySelector('.app-usage-notes');check(note&&!note.open&&note.textContent.includes('不自动授权或运行')&&d.querySelector('.app-entry-guidance').textContent.includes('未发布'),'progressive app guidance retains full restrictions plus visible critical limit');
 console.log(JSON.stringify({status:'PASS',scope:'real DOM and original protocol controller; not native pixels',checks,network_calls:0,models:0},null,2));
}finally{dom.window.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
