'use strict';
// Full product DOM/scripts, actual SQLite-generated saved fixture, controlled API.
// Does not claim actual HTTP, model semantics, or native/browser behavior.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {JSDOM}=require('/workspace/node-tools/node_modules/jsdom');
const out='/tmp/pa-independent-review-20261011',web='/workspace/Sim2Act/src/sim2act/web';
const fixture=JSON.parse(fs.readFileSync(path.join(out,'ui-fixture.json')));
let dom,w,$,calls,mode,hold;const results=[];
const clone=v=>JSON.parse(JSON.stringify(v));
const settle=()=>new Promise(r=>setImmediate(r));
async function setup(selected){
  dom?.window.close();dom=new JSDOM(fs.readFileSync(path.join(web,'index.html'),'utf8'),{url:'http://synthetic.invalid',runScripts:'dangerously'});
  w=dom.window;$=id=>w.document.getElementById(id);calls=[];mode=selected;hold=null;
  w.setInterval=()=>1;w.crypto.randomUUID=()=>crypto.randomUUID();w.structuredClone=structuredClone;w.TextEncoder=TextEncoder;
  Object.defineProperty(w.crypto,'subtle',{value:crypto.webcrypto.subtle});
  w.fetch=async(url,opts={})=>{
    const method=opts.method||'GET';calls.push({url,method,body:opts.body&&JSON.parse(opts.body)});let value;
    if(hold&&!hold.used&&hold.url===url){hold.used=true;value=await new Promise(resolve=>hold.resolve=resolve);}
    if(value===undefined){
      if(method==='POST'&&url.endsWith('/confirm-application-candidate'))throw Error('Controlled lost confirmation receipt');
      else if(method==='POST')value=clone(fixture.accepted);
      else if(url.includes('/confirmed-application-candidate?'))value={id:'app_'+'9'.repeat(32),state:'PREVIEW_ONLY',recovered:true};
      else if(url===`/api/goal-cards/${fixture.card.id}`)value=clone(fixture.card);
      else if(url===`/api/runs/${fixture.run.id}`){
        value=clone(fixture.run);
        if(mode==='snapshot')value.contract.snapshot.source_goal_card.snapshot.content.constraints=[];
        if(mode==='candidate')value.result.candidate.goal.constraints=[];
        if(mode==='policy')value.contract.snapshot.application_generation.live_request_allowance=1;
        if(mode==='result')value.result={candidate_fingerprint:'0'.repeat(64),app_created:true,goal_acceptance:'ACCEPTED',semantic_status:'ACCEPTED'};
        if(mode==='run-id')value.id='run_'+'9'.repeat(32);
      }
      else if(url.endsWith('/candidate-options'))value={options:[]};
      else if(url==='/api/apps'||url.endsWith('/goal-cards')||url.endsWith('/candidates')||url.endsWith('/conditional-apps'))value={items:[]};
      else value=[];
    }
    return {ok:true,status:200,json:async()=>value};
  };
  for(const name of ['app.js','goal-application.js']){const s=w.document.createElement('script');s.textContent=fs.readFileSync(path.join(web,name),'utf8');w.document.body.append(s);}
  $('project-select').append(new w.Option('Project',fixture.card.project_id));$('project-select').value=fixture.card.project_id;w.eval('token="synthetic-A"');await w.showGoalCard(fixture.card.id);
}
async function test(name,fn){try{await fn();results.push({name,status:'PASS'});}catch(e){results.push({name,status:'FAIL',error:e.message});}}
(async()=>{try{
  await test('valid actual generated candidate enables acknowledged confirmation',async()=>{await setup('ok');await $('goal-application-start').onclick();$('goal-application-ack').checked=true;$('goal-application-ack').onchange();assert.equal($('goal-application-confirm').disabled,false,$('goal-application-status').textContent);});
  for(const kind of ['snapshot','candidate','policy','result','run-id'])await test('mismatched '+kind+' must clear protected proof and disable confirmation',async()=>{
    await setup(kind);await $('goal-application-start').onclick();$('goal-application-ack').checked=true;$('goal-application-ack').onchange();
    assert.equal($('goal-application-confirm').disabled,true,JSON.stringify({kind,confirmDisabled:$('goal-application-confirm').disabled,status:$('goal-application-status').textContent,proof:$('goal-application-proof').textContent.slice(0,180)}));
    assert.equal($('goal-application-proof').textContent,'');
  });
  await test('card ABA late accepted POST must not read/repaint old run',async()=>{
    await setup('ok');hold={url:`/api/projects/${fixture.card.project_id}/goal-cards/${fixture.card.id}/application-runs`,used:false};
    const pending=$('goal-application-start').onclick();while(!hold.used)await settle();const old=hold;
    w.clearGoalCard();await w.showGoalCard(fixture.card.id);old.resolve(clone(fixture.accepted));await pending;
    assert(!calls.some(c=>c.url===`/api/runs/${fixture.run.id}`),'Late old accepted POST selected/read run after card ABA');
    assert.equal($('goal-application-proof').textContent,'');
  });
  await test('card ABA late run GET must not repaint protected proof',async()=>{
    await setup('ok');hold={url:`/api/runs/${fixture.run.id}`,used:false};const pending=$('goal-application-start').onclick();while(!hold.used)await settle();const old=hold;
    w.clearGoalCard();await w.showGoalCard(fixture.card.id);old.resolve(clone(fixture.run));await pending;
    assert.equal($('goal-application-proof').textContent,'','Late old GET repainted protected proof after card ABA');
  });
  await test('lost confirmation recovery must not select a different application',async()=>{
    await setup('ok');await $('goal-application-start').onclick();$('goal-application-ack').checked=true;$('goal-application-ack').onchange();
    await $('goal-application-confirm').onclick();assert(!$('goal-application-confirm-read').hidden);
    await $('goal-application-confirm-read').onclick();
    assert(!calls.some(c=>c.url==='/api/apps/app_'+'9'.repeat(32)),'Recovery selected wrong app id after lost confirmation');
    assert.equal(calls.filter(c=>c.method==='POST'&&c.url.endsWith('/confirm-application-candidate')).length,1);
  });
  const hashes=Object.fromEntries(['app.js','goal-application.js','index.html'].map(name=>[name,crypto.createHash('sha256').update(fs.readFileSync(path.join(web,name))).digest('hex')]));
  const output={status:results.every(r=>r.status==='PASS')?'PASS':'FAIL',api:'CONTROLLED_NOT_HTTP',fixture:'ACTUAL_SQLITE_NORMAL_WORKER_MOCK',native:'NOT_RUN',semantic:'NOT_RUN',loaded_source_sha256:hashes,results};
  fs.writeFileSync(path.join(out,process.argv[2]||'ui-original.json'),JSON.stringify(output,null,2));console.log(JSON.stringify(output,null,2));if(output.status==='FAIL')process.exitCode=1;
}finally{dom?.window.close();}})().catch(e=>{console.error(e.stack);process.exitCode=1;});
