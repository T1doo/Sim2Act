const fs=require('fs'),crypto=require('crypto'),assert=require('assert/strict'),path=require('path');
const {JSDOM}=require('jsdom');
const root=process.env.REVIEW_WEB_ROOT||'/workspace/Sim2Act/src/sim2act/web';
const out=process.argv[2]||'/tmp/sim2act-condition-groups-independent-20261009/final';
fs.mkdirSync(out,{recursive:true});
const checks=[],hashes={},dom=new JSDOM(fs.readFileSync(root+'/index.html','utf8'),{url:'http://127.0.0.1',runScripts:'dangerously'}),w=dom.window;
w.setInterval=()=>0;w.TextEncoder=TextEncoder;Object.defineProperty(w.crypto,'subtle',{value:crypto.webcrypto.subtle});
for(const tag of w.document.querySelectorAll('script[src]')){
    const file=tag.getAttribute('src').slice(1),code=fs.readFileSync(root+'/'+file);
    hashes[file]=crypto.createHash('sha256').update(code).digest('hex');
    const script=w.document.createElement('script');script.textContent=code.toString();w.document.body.append(script);
}
const check=(v,label)=>{assert(v,label);checks.push(label);};
try{
    w.eval('$("project-select").append(new Option("review","review"));$("project-select").value="review";activeApp="review-app";deliveryContext={epoch:deliveryEpoch,identity:token,generation:appSelectionGeneration,project:"review",id:activeApp,app:{fingerprint:"review"}};csvDagContext={parent:deliveryContext,nodeSequence:0,plan:null,job:null,busy:false};csvDagNodeAdd()');
    for(const [name,host] of [['legacy',w.document.getElementById('csv-dag-branch')],['composition',w.document.getElementById('csv-dag-nodes').children[0]]]){
        const mode=host.querySelector('[data-role="combine"]'),rows=host.querySelector('[data-role="conditions"]'),add=host.querySelector('[data-role="condition-add"]');
        mode.value='any';mode.dispatchEvent(new w.Event('change'));
        check(rows.children.length===1&&!add.disabled,name+' two leaves allow add');
        add.click();add.click();
        check(rows.children.length===3&&add.disabled,name+' four leaves disable add');
        add.click();check(rows.children.length===3,name+' disabled add cannot create fifth leaf');
        rows.children[1].querySelector('button').click();
        check(rows.children.length===2&&!add.disabled,name+' removing leaf re-enables add');
        w.eval('csvDagIntents.set(csvDagKey(csvDagContext),{kind:"run",body:{request_key:"frozen-review"}});csvDagButtons()');
        check([...host.querySelectorAll('input,select,button')].every(v=>v.disabled),name+' unresolved original key locks every control');
        add.click();check(rows.children.length===2,name+' locked add cannot mutate draft');
        w.eval('csvDagIntents.clear();csvDagButtons()');
        check(!add.disabled,name+' restored original key unlocks add below maximum');
        add.click();check(rows.children.length===3&&add.disabled,name+' adding after restoration disables at four again');
    }
    fs.writeFileSync(path.join(out,'js-result.json'),JSON.stringify({status:'PASS',checks,loaded_source_sha256:hashes},null,2));
    console.log(JSON.stringify({status:'PASS',checks:checks.length}));
}catch(e){fs.writeFileSync(path.join(out,'js-failure.txt'),String(e.stack));console.error(e);process.exitCode=1;}
finally{dom.window.close();}
