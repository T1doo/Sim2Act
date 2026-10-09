const fs=require('fs'),assert=require('assert/strict'),crypto=require('crypto'),{JSDOM}=require('jsdom');
const root='/workspace/Sim2Act/src/sim2act/web',out='/tmp/sim2act-report-edit-locks-independent-20261009';
const dom=new JSDOM(fs.readFileSync(root+'/index.html','utf8'),{url:'http://127.0.0.1',runScripts:'dangerously'}),w=dom.window;
w.setInterval=()=>0;w.TextEncoder=TextEncoder;Object.defineProperty(w.crypto,'subtle',{value:crypto.webcrypto.subtle});
for(const el of w.document.querySelectorAll('script[src]')){const s=w.document.createElement('script');s.textContent=fs.readFileSync(root+'/'+el.getAttribute('src').slice(1),'utf8');w.document.body.append(s);}
w.eval('$("project-select").append(new Option("review","review"));$("project-select").value="review";activeApp="app_review";manifestContext={epoch:manifestEpoch,identity:token,generation:appSelectionGeneration,project:"review",id:activeApp,app:{fingerprint:"a".repeat(64)}};');
const calls=[];let phase=0;
w.api=async(url,method,body)=>{
  calls.push({url,method,body});
  if(url.endsWith('/derive'))return {project_id:'review',app_id:'app_review',candidate_fingerprint:'a'.repeat(64),graph_fingerprint:'b'.repeat(64),graph:{nodes:[{kind:'VIEW',key:'view:text:decision',id:'node_'+'1'.repeat(32),revision:1,content_fingerprint:'c'.repeat(64)}]}};
  if(url.endsWith('/plans')){
    if(phase++===0)throw Error('lost accepted plan reply');
    const e=Error('LOCK_CONFLICT');e.httpStatus=400;e.detail='Project revalidation affects a manually locked graph';throw e;
  }
  throw Error('unexpected '+url);
};
const result={};
(async()=>{
  try{
    w.eval('window.reviewItem={run:{run_id:"run_"+"2".repeat(32),version:1,fence:1,result_fingerprint:"d".repeat(64),status:"WAITING_APPROVAL",result:{protocol_result:{evidence:{output:{decision:"ALLOW",explanation:"example"}}}}}};window.reviewBox=presentationControls(manifestContext,reviewItem);document.body.append(reviewBox);');
    const button=w.document.querySelector('.report-presentation-propose');
    await button.onclick();
    result.before_retry=w.eval('presentationIntents.size');
    result.plan_key=w.eval('presentationIntents.get(presentationKey(manifestContext,reviewItem.run)).planKey');
    assert.equal(result.before_retry,1);
    await button.onclick();
    result.after_retry=w.eval('presentationIntents.size');
    result.plan_posts=calls.filter(v=>v.url.endsWith('/plans'));
    result.same_plan_request=JSON.stringify(result.plan_posts[0].body)===JSON.stringify(result.plan_posts[1].body);
    result.status=w.document.querySelector('.report-presentation-controls').textContent;
    fs.writeFileSync(out+'/unknown-probe.json',JSON.stringify(result,null,2));
    assert.equal(result.after_retry,1,'previous acceptance UNKNOWN must retain exact plan key despite later lock rejection');
  }catch(e){fs.writeFileSync(out+'/unknown-probe-failure.txt',String(e.stack));console.error(e);process.exitCode=1;}
  finally{dom.window.close();}
})();
