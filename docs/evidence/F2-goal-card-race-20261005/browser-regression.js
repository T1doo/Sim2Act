// Run via agent-browser eval --stdin on the authenticated disposable fixture.
// Delays real responses; no substituted API payloads. Only synthetic records.
(async () => {
  const results = [], requests = [], gates = [];
  const originalFetch = window.fetch;
  window.fetch = async (url, options = {}) => {
    const method = options.method || "GET";
    requests.push({url: String(url), method});
    const gate = gates.find(g => !g.used && g.url === String(url) && g.method === method);
    if (gate) gate.used = true;
    const response = await originalFetch(url, options);
    if (gate) {gate.received = true; await gate.promise;}
    return response;
  };
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  const wait = async predicate => {
    const deadline = Date.now() + 12000;
    while (!predicate()) {if (Date.now() > deadline) throw Error("fixture wait timeout"); await sleep(20);}
  };
  const hold = (url, method = "GET") => {
    const g = {url, method, used: false, received: false};
    g.promise = new Promise(resolve => g.release = resolve);gates.push(g);return g;
  };
  const check = (name, predicate) => {if (!predicate) throw Error(name); results.push({name, status:"PASS"});};
  const select = async pid => {$("project-select").value = pid;$("project-select").dispatchEvent(new Event("change"));await wait(() => $("goal-card-list").textContent.includes(pid === pa ? "项目A" : "尚无目标卡"));};
  const open = id => showGoalCard(id);
  const fill = title => {$("goal-card-title").value = title;$("goal-card-goal").value = "SYNTHETIC goal";};
  const submit = () => $("goal-card-form").dispatchEvent(new Event("submit", {cancelable:true}));
  try {
    const projects = await api("/api/projects");
    var pa = projects.find(p => p.name === "SYNTHETIC 项目A").id;
    const pb = projects.find(p => p.name === "SYNTHETIC 项目B").id;
    const cards = await api(`/api/projects/${pa}/goal-cards`);
    const ca = cards.items.find(c => c.title === "项目A固定汇总目标").id;
    const cb = (await api(`/api/projects/${pa}/goal-cards`, "POST", {
      title:"项目A第二张卡", goal:"SYNTHETIC second", known:[], assumptions:[], unresolved:[],
      constraints:[], acceptance_checks:[], resource_refs:[]
    })).id;
    const cardUrl = `/api/goal-cards/${ca}`;
    await select(pa);

    let gate = hold(cardUrl), pending = open(ca);
    await wait(() => gate.used);await select(pb);await wait(() => gate.received);
    gate.release();await pending;
    check("late A GET after selecting B cannot restore A", activeGoalCard === null && !$("goal-card-title").value);
    const aBefore = await api(cardUrl);
    fill("项目B新草案");submit();await wait(() => !goalCardSaving && !goalCardLoading);
    const aAfter = await api(cardUrl);
    check("save after navigation creates B and leaves A unchanged", activeGoalCard.project_id === pb && aAfter.version === aBefore.version);

    await select(pa);gate = hold(cardUrl);pending = open(ca);
    await wait(() => gate.used);$("goal-card-new").click();fill("New unsaved text");
    await wait(() => gate.received);gate.release();await pending;
    check("New invalidates pending GET and preserves typed text", activeGoalCard === null && $("goal-card-title").value === "New unsaved text");

    gate = hold(cardUrl);pending = open(ca);await wait(() => gate.used);await open(cb);
    await wait(() => gate.received);gate.release();await pending;
    check("later selection wins over older response", activeGoalCard.id === cb && $("goal-card-title").value === "项目A第二张卡");

    gate = hold(cardUrl);pending = open(ca);await wait(() => gate.used);
    const newer = open(ca);await newer;await wait(() => gate.received);gate.release();await pending;
    check("repeated opening keeps latest selection", activeGoalCard.id === ca && activeGoalCard.project_id === pa);

    gate = hold(cardUrl, "PUT");$("goal-card-goal").value = "SYNTHETIC save before New";
    const putsBefore = requests.filter(r => r.method === "PUT").length;
    submit();submit();await wait(() => gate.used);$("goal-card-new").click();fill("New during save");
    await wait(() => gate.received);gate.release();await wait(() => !goalCardSaving);
    check("duplicate submit emits one PUT; save completion preserves New", requests.filter(r => r.method === "PUT").length === putsBefore + 1 && activeGoalCard === null && $("goal-card-title").value === "New during save");

    await open(ca);gate = hold(cardUrl, "PUT");$("goal-card-goal").value = "SYNTHETIC save before navigation";
    submit();await wait(() => gate.used);$("project-select").value = pb;$("project-select").dispatchEvent(new Event("change"));
    fill("B unsaved during A save");await wait(() => gate.received);gate.release();await wait(() => !goalCardSaving);
    check("save completion cannot reopen A after navigation", activeGoalCard === null && $("project-select").value === pb && $("goal-card-title").value === "B unsaved during A save");

    const putCount = requests.filter(r => r.method === "PUT").length;
    activeGoalCard = {id:ca, version:1, project_id:pa};submit();await sleep(100);
    check("submit rejects mismatched active-card project before PUT", requests.filter(r => r.method === "PUT").length === putCount && $("error").textContent.includes("不属于当前项目"));
    $("goal-card-new").click();
    let rejected = false;try {await open(ca);} catch(e) {rejected = e.message.includes("不属于当前项目");}
    check("response project validation refuses wrong-project card", rejected && activeGoalCard === null);

    await select(pa);await open(ca);
    const loaded = await api(cardUrl);
    await api(cardUrl,"PUT", {...loaded.content, goal:"SYNTHETIC concurrent revision", expected_version:loaded.version});
    $("goal-card-goal").value = "SYNTHETIC stale unsaved text";submit();await wait(() => !goalCardSaving);
    check("backend CAS rejects stale save and preserves unsaved text", $("error").textContent.includes("VERSION_CONFLICT") && $("goal-card-goal").value === "SYNTHETIC stale unsaved text");
    await open(ca);const oldVersion = activeGoalCard.version;
    $("goal-card-goal").value = "SYNTHETIC normal revision";submit();await wait(() => !goalCardSaving && !goalCardLoading);
    check("normal save reopens exact new version with correct project", activeGoalCard.version === oldVersion + 1 && activeGoalCard.project_id === pa && $("goal-card-goal").value === "SYNTHETIC normal revision");
    return {status:"PASS", checks:results, model_requests:0, real_user_data:false};
  } finally {
    gates.forEach(g => g.release());window.fetch = originalFetch;
  }
})()
