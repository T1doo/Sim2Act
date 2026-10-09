const fs=require('fs'),crypto=require('crypto'),assert=require('assert/strict');
const {JSDOM}=require('jsdom');
const root='/workspace/Sim2Act/src/sim2act/web',out='/tmp/sim2act-condition-groups-independent-20261009';
const checks=[],hashes={};
const dom=new JSDOM(fs.readFileSync(root+'/index.html','utf8'),{url:'http://127.0.0.1',runScripts:'dangerously'});
const w=dom.window;
w.setInterval=()=>0;w.TextEncoder=TextEncoder;
Object.defineProperty(w.crypto,'subtle',{value:crypto.webcrypto.subtle});
for(const script of w.document.querySelectorAll('script[src]')){
  const file=script.getAttribute('src').slice(1),bytes=fs.readFileSync(root+'/'+file);
  hashes[file]=crypto.createHash('sha256').update(bytes).digest('hex');
  const loaded=w.document.createElement('script');loaded.textContent=bytes.toString();w.document.body.append(loaded);
}
const check=(v,label)=>{assert(v,label);checks.push(label);};
const atom=(op,field,value,ref)=>({op,source:ref?{source:'step',ref,field}:{source:'input',field},...(op==='exists'?{}:{value})});
(async()=>{
  const parents=[{step_id:'aggregate',status:'VERIFIED',data:{count:2,sum:'15'}}];
  for(const op of ['all','any']){
    const d=await w.csvDagBranchDecision({depends_on:['aggregate'],when:{op,conditions:[atom('exists','include_report'),atom('in','count',[2], 'aggregate'),atom('eq','sum','15','aggregate')]}},{},parents,'typed-conditions.v2');
    check(d.passed===(op==='any')&&d.observation.conditions.map(c=>c.passed).join(',')==='false,true,true',op+' all three leaf observations including missing exists');
    const step={depends_on:['aggregate'],when:{op,conditions:[atom('eq','count',op==='any'?2:3,'aggregate'),atom('in','include_report',[true])]}};
    await assert.rejects(()=>w.csvDagBranchDecision(step,{},parents,'typed-conditions.v2'),/INVALID_INPUT/);checks.push(op+' missing final in input never short circuits');
    const skipped=await w.csvDagBranchDecision(step,{},[{step_id:'aggregate',status:'SKIPPED',data:null}],'typed-conditions.v2');
    check(skipped.reason==='DEPENDENCY_SKIPPED'&&skipped.observation.evaluated===false,op+' skip preempts missing input and null parent data');
  }
  w.eval('$("project-select").append(new Option("review","review"));$("project-select").value="review";activeApp="review-app";deliveryContext={epoch:deliveryEpoch,identity:token,generation:appSelectionGeneration,project:"review",id:activeApp,app:{fingerprint:"review"}};csvDagContext={parent:deliveryContext,plan:{branch_semantics:"typed-conditions.v2"},job:null,busy:false}');
  const $=id=>w.document.getElementById(id),host=$('csv-dag-branch'),mode=host.querySelector('[data-role="combine"]'),rows=host.querySelector('[data-role="conditions"]'),add=host.querySelector('[data-role="condition-add"]');
  mode.value='all';mode.dispatchEvent(new w.Event('change'));
  add.click();add.click();
  check(rows.children.length===3,'four total leaves available');
  const maxDisabled=add.disabled;
  add.click();check(rows.children.length===3,'fifth leaf blocked by append guard');
  checks.push('legacy max button disabled='+maxDisabled);
  $('csv-dag-confirm').checked=true;
  mode.value='any';mode.dispatchEvent(new w.Event('change'));
  check(!$('csv-dag-confirm').checked&&$('csv-dag-definition').textContent==='','group mode edit clears proof and confirmation');
  w.eval('csvDagIntents.set(csvDagKey(csvDagContext),{kind:"run",body:{request_key:"fixed"}});csvDagButtons()');
  check([...host.querySelectorAll('input,select,button')].every(v=>v.disabled),'unknown original-key intent locks every leaf and group control');
  w.eval('csvDagIntents.clear();csvDagButtons()');
  rows.children[0].querySelector('button').click();
  check(rows.children.length===2,'remove group leaf bounded');
  const r={status:'PASS_WITH_UI_NIT',checks,legacy_max_button_disabled:maxDisabled,loaded_source_sha256:hashes};
  fs.writeFileSync(out+'/js-result.json',JSON.stringify(r,null,2));dom.window.close();
  console.log(JSON.stringify(r));
})().catch(e=>{dom.window.close();console.error(e);process.exitCode=1;});
