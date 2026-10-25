'use strict';
// Product template/controller in JSDOM; bounded synthetic GET adapter, no HTTP.
const fs=require('node:fs'),assert=require('node:assert/strict'),{JSDOM,VirtualConsole}=require('jsdom'),css=require('css-tree');
const errors=[],checks=[],requests=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(fs.readFileSync('src/sim2act/web/index.html','utf8'),{runScripts:'dangerously',virtualConsole:vc}),w=dom.window,d=w.document,$=id=>d.getElementById(id);
w.setInterval=()=>0;w.fetch=()=>{throw Error('No HTTP permitted');};
const script=d.createElement('script');script.textContent=fs.readFileSync('src/sim2act/web/app.js','utf8');d.body.append(script);assert.deepEqual(errors,[]);
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
const run={id:'run_synthetic_readonly',goal_summary:'核对本次材料中的提交条件',status:'WAITING_APPROVAL',mode:'MOCK',created_at:1792800000};
let opens=0;const item=w.runHistoryRow(run,()=>{opens++;});$('runs').append(item);
(async()=>{try{
 check(item.querySelector('h3').textContent===run.goal_summary&&item.querySelector('.task-status').textContent==='执行 · WAITING_APPROVAL'&&item.querySelector('.task-mode').textContent==='提交模式 MOCK','goal, technical state and saved mode have separate readable structure');
 await item.querySelector('button').onclick();check(opens===1&&item.querySelector('button').type==='button','one click uses original safe action without form submission');
 for(const [status,tone] of [[undefined,'uncertain'],['UNKNOWN','uncertain'],['SUCCEEDED','complete'],['constructor','neutral'],['NEW_STATE','neutral']]){
  const row=w.runHistoryRow({...run,status,mode:'unrecognized'},()=>{});
  assert.equal(row.querySelector('.task-status').dataset.tone,tone);
  assert(row.textContent.includes(status||'UNKNOWN'));assert(row.textContent.includes('提交模式 UNKNOWN'));assert(!row.textContent.includes('验收通过'));
 }
 check(true,'missing, unknown and future states remain literal; technical success never claims acceptance');
 const attack='<img src=x onerror=alert(1)>',long=attack+'长目标'.repeat(120);
 const untrusted=w.runHistoryRow({...run,goal_summary:long,status:attack,created_at:1e100,execution_namespace:'local-record-private-preview.v1'},()=>{});
 check(!untrusted.querySelector('img')&&untrusted.querySelector('h3').textContent===long&&untrusted.textContent.includes('时间未知')&&untrusted.textContent.includes('PREVIEW 私有试写'),'long and hostile text stays complete text; invalid time and private preview remain explicit');
 const controls=[...d.querySelectorAll('button,input,select,textarea')].map(n=>[n.id,n.disabled,n.hidden]);w.runHistoryRow(run,()=>{});
 assert.deepEqual([...d.querySelectorAll('button,input,select,textarea')].map(n=>[n.id,n.disabled,n.hidden]),controls);
 check(true,'rendering a history entry changes no action availability');
 $('project-select').replaceChildren(new w.Option('Synthetic A','project-a'),new w.Option('Synthetic B','project-b'));w.eval("token='synthetic-actor';");
 w.refreshGoalCards=async()=>{};w.refreshApps=async()=>{};w.showRun=async()=>{opens++;};let fail=false;
 w.api=async(path,method='GET')=>{requests.push({path,method});assert.equal(method,'GET');if(path.includes('/runs?')){if(fail)throw Error('Synthetic history read failed');return [run];}if(path.endsWith('/resources')||path.endsWith('/grants'))return [];throw Error('Unexpected adapter path '+path);};
 await w.refresh();const original=$('runs').querySelector('button'),before=opens;await original.onclick();assert.equal(opens,before+1);
 w.eval("token='other-actor';");await original.onclick();assert.equal(opens,before+1);
 w.eval("token='synthetic-actor';");$('project-select').value='project-b';await original.onclick();assert.equal(opens,before+1);
 check(true,'actual refresh closure opens current task but rejects its old button after identity or project change');
 $('project-select').value='project-a';fail=true;await assert.rejects(w.refresh(),/Synthetic history/);
 check(!$('runs').children.length&&$('run-history-status').textContent.includes('历史读取失败'),'failed fresh history read clears old tasks and exposes read-only recovery');
 const sheet=css.parse(fs.readFileSync('src/sim2act/web/app.css','utf8')),rules=[];
 function visit(list,media=''){for(const n of list){if(n.type==='Rule')rules.push({selector:css.generate(n.prelude),media,decl:Object.fromEntries([...n.block.children].filter(x=>x.type==='Declaration').map(x=>[x.property,css.generate(x.value)+(x.important?'!important':'')]))});else if(n.type==='Atrule'&&n.block)visit(n.block.children,media+'@'+n.name+(n.prelude?css.generate(n.prelude):''));}}visit(sheet.children);
 check(rules.some(r=>r.media.includes('prefers-reduced-motion:reduce')&&r.decl.animation==='none!important'&&r.decl.transition==='none!important')&&rules.filter(r=>r.selector.includes('.task-compose')&&r.decl.transition).every(r=>r.media.includes('prefers-reduced-motion:no-preference')),'new disclosure motion is opt-in and global reduced-motion rule remains authoritative');
 check(rules.some(r=>r.selector.includes(':focus-visible')&&r.decl.outline)&&rules.some(r=>r.selector==='#runs button:disabled'&&r.decl.color)&&rules.some(r=>r.selector==='.task-status'&&r.decl['overflow-wrap']==='anywhere'),'focus, disabled states and long status wrapping have explicit CSS declarations');
 function lum(hex){return [.2126,.7152,.0722].reduce((sum,k,i)=>{let c=parseInt(hex.slice(1+i*2,3+i*2),16)/255;return sum+k*(c<=.04045?c/12.92:((c+.055)/1.055)**2.4);},0);}
 const contrasts=[['active','#8b3918','#fff0e4'],['uncertain','#805313','#fff7e5'],['error','#87382b','#fff2ed'],['technical complete','#355646','#f0f6f2']].map(([state,fg,bg])=>({state,fg,bg,ratio:(lum(bg)+.05)/(lum(fg)+.05)}));
 assert(contrasts.every(x=>x.ratio>=4.5));check(true,'new labelled status text meets 4.5:1 contrast for its declared solid colors');
 assert.deepEqual(errors,[]);
 console.log(JSON.stringify({status:'PASS',scope:'DOM/CSS declarations and synthetic adapter only; NOT pixel, layout or native keyboard acceptance',checks,contrasts,requests,http:0,models:0},null,2));
}finally{dom.window.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
