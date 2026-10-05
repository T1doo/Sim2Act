// Chromium, actual APIs, disposable fixture only. Gates delay actual responses.
(async()=>{
  const checks=[],requests=[],gates=[],originalFetch=window.fetch;
  window.fetch=async(url,options={})=>{
    const method=options.method || "GET";requests.push({url:String(url),method});
    const gate=gates.find(g=>!g.used && g.url===String(url) && g.method===method);
    if(gate)gate.used=true;
    const response=await originalFetch(url,options);
    if(gate){gate.received=true;await gate.promise;}return response;
  };
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  const wait=async predicate=>{const end=Date.now()+12000;while(!predicate()){if(Date.now()>end)throw Error("fixture timeout");await sleep(20);}};
  const hold=(url,method)=>{const gate={url,method,used:false,received:false};gate.promise=new Promise(r=>gate.release=r);gates.push(gate);return gate;};
  const check=(name,predicate)=>{if(!predicate)throw Error(name);checks.push({name,status:"PASS"});};
  const submit=()=>$("goal-candidate-form").dispatchEvent(new Event("submit",{cancelable:true}));
  const appCount=async()=>(await api("/api/apps")).items.length;
  try{
    const projects=await api("/api/projects"),pa=projects.find(p=>p.name==="SYNTHETIC 项目A").id,pb=projects.find(p=>p.name==="SYNTHETIC 项目B").id;
    $("project-select").value=pa;await $("project-select").onchange(new Event("change"));selectWorkspace("projects");
    const cid=(await api(`/api/projects/${pa}/goal-cards`)).items.find(c=>c.title==="项目A固定汇总目标").id;
    const path=`/api/goal-cards/${cid}/candidates`;
    await showGoalCard(cid);const initial=await appCount();
    $("goal-card-goal").value="SYNTHETIC unsaved before cancel";$("goal-candidate-cancel").click();submit();await sleep(80);
    check("cancel before submit writes no candidate and preserves edits",await appCount()===initial && $("goal-card-goal").value==="SYNTHETIC unsaved before cancel");

    const empty=(await api(`/api/projects/${pa}/goal-cards`,"POST",{title:"SYNTHETIC no CSV",goal:"generic text goal",known:[],assumptions:[],unresolved:[],constraints:[],acceptance_checks:[],resource_refs:[]})).id;
    await showGoalCard(empty);
    check("unsupported goal has no create control and explains scope",$("goal-candidate-form").hidden && $("goal-candidate-status").textContent.includes("绑定并保存CSV"));

    await showGoalCard(cid);const old=await api(`/api/goal-cards/${cid}`);
    await api(`/api/goal-cards/${cid}`,"PUT",{...old.content,expected_version:old.version,known:["SYNTHETIC latest saved condition"]});
    $("goal-card-goal").value="SYNTHETIC unsaved stale candidate text";submit();await wait(()=>!candidateBusy);
    check("stale goal candidate fails without writing and preserves editor",await appCount()===initial && $("goal-card-goal").value==="SYNTHETIC unsaved stale candidate text" && $("goal-candidate-status").textContent.includes("VERSION_CONFLICT"));

    await showGoalCard(cid);const saved=await api(`/api/goal-cards/${cid}`);
    $("goal-card-goal").value="SYNTHETIC unsaved NOT frozen";
    let gate=hold(path,"POST"),postBefore=requests.filter(r=>r.url===path && r.method==="POST").length;
    submit();submit();await wait(()=>gate.received);$("goal-candidate-cancel").click();gate.release();await wait(()=>!candidateBusy);
    check("double submit emits one POST and accepted cancellation cannot reopen app",requests.filter(r=>r.url===path && r.method==="POST").length===postBefore+1 && $("apps").hidden && $("goal-card-goal").value==="SYNTHETIC unsaved NOT frozen");
    check("accepted candidate remains discoverable after returning to editor",await appCount()===initial+1 && $("goal-candidate-status").textContent.includes("仍保留"));

    await showGoalCard(cid);submit();await wait(()=>!candidateBusy);
    const aid=activeApp,draft=await api(`/api/apps/${aid}`);
    check("retry returns same candidate with frozen saved conditions",await appCount()===initial+1 && JSON.stringify(draft.candidate.goal)===JSON.stringify(saved.content) && draft.candidate.generation.goal_version===saved.version);
    check("compiled declaration and frozen conditions are visible",draft.validation.state==="PREFLIGHTED_DRAFT" && !draft.validation.execution_performed && $("app-frozen-goal-text").textContent.includes(saved.content.constraints[0]));
    check("candidate opening labels MOCK unaccepted unpublished origin",!$("apps").hidden && $("app-origin").textContent.includes("MOCK") && $("app-origin").textContent.includes("尚未验收") && $("app-origin").textContent.includes("未发布"));

    // Deliberate invalid UI input verifies backend failure/history, no fabricated output.
    $("app-column").append(new Option("SYNTHETIC invalid","missing"));$("app-column").value="missing";
    $("app-preview-form").dispatchEvent(new Event("submit",{cancelable:true}));
    await wait(()=>$("app-output").textContent.includes("FAILED"));
    check("invalid preview visibly fails and retains history",$("app-history").textContent.includes("FAILED"));
    $("app-column").value="quantity";$("app-preview-form").dispatchEvent(new Event("submit",{cancelable:true}));
    await wait(()=>$("app-output").textContent.includes("合计 15"));
    check("new valid input succeeds after failure with separate history",$("app-history").textContent.includes("FAILED") && $("app-history").textContent.includes("SUCCEEDED"));
    const finalDraft=await api(`/api/apps/${aid}`);
    check("preview has zero model/business writes and no release",finalDraft.history.every(r=>r.model_requests===0 && r.business_writes===0 && r.release_id===null));
    $("app-back-goal").click();await wait(()=>activeGoalCard?.id===cid && candidatePanelReady);
    check("return follows persisted goal source and exposes candidate",!$("projects").hidden && $("goal-candidate-list").textContent.includes("打开候选预览"));

    gate=hold(path,"POST");submit();await wait(()=>gate.received);
    $("project-select").value=pb;await $("project-select").onchange(new Event("change"));gate.release();await wait(()=>!candidateBusy);
    check("accepted candidate response after project change cannot open old app",activeApp===null && activeGoalCard===null && $("apps").hidden);

    $("project-select").value=pa;await $("project-select").onchange(new Event("change"));
    gate=hold(`/api/apps/${aid}`,"GET");const pending=showApp(aid,pa);await wait(()=>gate.received);
    $("project-select").value=pb;await $("project-select").onchange(new Event("change"));gate.release();await pending;
    check("late app GET cannot restore wrong-project candidate",activeApp===null && $("app-origin").textContent==="");
    return {status:"PASS",checks,model_requests:0,synthetic_only:true,aid,cid,pa};
  }finally{gates.forEach(g=>g.release());window.fetch=originalFetch;}
})()
