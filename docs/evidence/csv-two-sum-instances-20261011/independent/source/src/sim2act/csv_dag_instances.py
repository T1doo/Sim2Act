"""Closed read→sum[→report] / read→two sums adapter on the existing worker.

A completed, independently reconstructed source Run anchors each immutable version.
No new manifest family, executor, principal, Grant or publication capability.
"""
import copy

from sqlalchemy import insert, select, update

from . import csv_dag as dag
from . import csv_reports as report
from . import lifecycle
from .apps import load_draft
from .column_patches import KeyInput, read_pair
from .contracts import Limits, validate_value
from .db import (
    delivery_graph_requests,
    events,
    fingerprint,
    internal_app_runs,
    internal_approvals,
    internal_instance_data,
    internal_instances,
    internal_releases,
    internal_run_bindings,
    new_id,
)
from .errors import DomainError
from .tools import csv_column_options

VERSION = "internal.csv-read-sum.v1"
REPORT_VERSION = "internal.csv-read-sum-report.v1"
TWO_SUM_VERSION = "internal.csv-read-two-sums.v1"
VERSIONS = (VERSION, REPORT_VERSION, TWO_SUM_VERSION)


def require(ok, message="Internal DAG provenance changed"):
    if not ok:
        raise DomainError("VERSION_CONFLICT", message)


def marked(snapshot):
    return "execution_source" in snapshot


def closed(plan):
    nodes = plan.get("composition", {}).get("definition", {}).get("nodes", [])
    require(len(nodes) in (2, 3) and "branch_semantics" not in plan,
            "Only unconditional read→sum[→report] or read→two sums is reusable")
    read, total = nodes[:2]
    require(read["action"] == "resource.read" and total["action"] == "data.aggregate_csv"
        and read["depends_on"] == [] and total["depends_on"] == [read["step_id"]]
        and not any("when" in node for node in nodes)
        and read["inputs"] == {"resource_id": dict(source="data", ref="source", field="resource_id")}
        and total["inputs"] == {
            "resource_id": dict(source="step", ref=read["step_id"], field="resource_id"),
            "column": dict(source="input", field=total["step_id"] + "_column")},
        "Only the closed read→sum ports can be reused")
    if len(nodes) == 3 and nodes[2]["action"] == "data.aggregate_csv":
        other = nodes[2]
        require(other["depends_on"] == [read["step_id"]]
            and other["inputs"] == {
                "resource_id": dict(source="step", ref=read["step_id"], field="resource_id"),
                "column": dict(source="input", field=other["step_id"] + "_column")}
            and len({n["step_id"] for n in nodes}) == 3
            and plan["composition"]["sinks"] == [total["step_id"], other["step_id"]],
            "Both sums require the same read predecessor and two complete sinks")
        return [total["step_id"], other["step_id"]]
    require(plan["composition"]["sinks"] == [nodes[-1]["step_id"]])
    if len(nodes) == 3:
        formatted = nodes[2]
        require(formatted["action"] == report.REF
            and formatted["depends_on"] == [total["step_id"]]
            and formatted["inputs"] == {k: dict(source="step", ref=total["step_id"], field=k)
                                        for k in report.FIELDS},
            "Report requires exactly the complete aggregate tuple")
    return total["step_id"]


def aggregate_result(base, execution):
    """The typed ledger stays five fields; the complete report remains in Run proof."""
    if execution["version"] == VERSION:
        return base["output_by_step"][execution["aggregate_step"]]
    if execution["version"] == TWO_SUM_VERSION:
        steps = execution["aggregate_steps"]
        require(len(base["steps"]) == 3 and all(p["status"] == "VERIFIED" for p in base["steps"])
            and set(base["output_by_step"]) == set(steps))
        values = {sid: base["output_by_step"][sid] for sid in steps}
        require(all(sum(p["step_id"] == sid for p in base["steps"]) == 1
            and fingerprint(values[sid]) == fingerprint(next(p["data"] for p in base["steps"] if p["step_id"] == sid))
            for sid in steps), "Both complete sums must match actual operation receipts")
        return values
    require(execution["version"] == REPORT_VERSION)
    totals = [p for p in base["steps"] if p["step_id"] == execution["aggregate_step"]]
    require(len(base["steps"]) == 3 and len(totals) == 1
        and all(p["status"] == "VERIFIED" for p in base["steps"]))
    value = totals[0]["data"]
    require(base["output_by_step"] == {execution["report_step"]: report.render(value)},
            "Report result differs from its actual aggregate receipt")
    return value


@dag.graph.controlled
def source_snapshot(store, c, user, rid, limits):
    dag.owner_lock(store, c, user, rid)
    job = dag.row(c, user, rid)
    bound = dag.binding(store, c, job, limits)
    require("internal_instance" not in bound, "A source must be an original completed DAG Run")
    proof = dag.inspect_job_tx(store, c, user, rid, limits)
    plan = bound["plan"]
    sid = closed(plan)
    count = len(plan["composition"]["definition"]["nodes"])
    require(proof["status"] == "SUCCEEDED" and len(proof["steps"]) == count
        and all(p["status"] == "VERIFIED" for p in proof["steps"])
        and job["context"]["tools"] == count, "Every actual source operation must be verified")
    draft, _, _, _ = load_draft(store, c, user, bound["app_id"], limits, lock=True)
    frozen = {k: copy.deepcopy(draft[k]) for k in ("id", "project_id", "runtime_id", "candidate", "fingerprint")}
    raw = dag.read_source(store, c, job)
    columns = [v["name"] for v in csv_column_options(raw["content"])["columns"] if v["numeric"]]
    cap = store.frozen_contract(c, job).limits
    declared = Limits(**plan["definition"]["manifest"]["runtime_limits"])
    effective = Limits(**{k: min(getattr(cap, k), getattr(declared, k)) for k in Limits.model_fields})
    dual = isinstance(sid, list)
    schema = (report.obj({"result": report.obj({step: copy.deepcopy(report.INPUT) for step in sid})})
              if dual else lifecycle.record_schema(frozen["candidate"]))
    execution = dict(version=TWO_SUM_VERSION if dual else VERSION if count == 2 else REPORT_VERSION,
        run_id=rid, run_version=job["version"], fence=job["fence"],
        accepted_fingerprint=job["fingerprint"], plan_key=bound["plan_key"],
        plan_fingerprint=plan["plan_fingerprint"], source_hash=plan["source_hash"],
        graph_fingerprint=plan["graph_fingerprint"], authorization_fingerprint=plan["authorization_fingerprint"],
        receipt_fingerprints=[fingerprint(p) for p in proof["steps"]],
        columns=columns, limits=effective.model_dump())
    if dual:
        definition = plan["definition"]
        bindings = {v["binding_id"]: v["action_id"] for v in definition["manifest"]["action_bindings"]}
        actions = {v["action_id"]: v for v in definition["actions"]}
        execution["read_step"] = plan["composition"]["definition"]["nodes"][0]["step_id"]
        execution["aggregate_steps"] = sid
        execution["aggregate_nodes"] = {n["step_id"]: dict(
            inputs=copy.deepcopy(n["inputs"]), depends_on=n["depends_on"][:], columns=columns[:],
            limits=copy.deepcopy(actions[bindings[n["step_id"]]]["limits"]))
            for n in plan["composition"]["definition"]["nodes"][1:]}
    else:
        execution["aggregate_step"] = sid
    if count == 3 and not dual:
        execution["report_step"] = plan["composition"]["definition"]["nodes"][2]["step_id"]
    validate_value(schema, {"result": aggregate_result(proof["result"], execution)})
    return dict(namespace=lifecycle.NAMESPACE, draft=frozen,
        dependency_lock=frozen["candidate"]["manifest"]["dependency_lock"], data_schema=schema,
        data_schema_version=1, execution_source=execution,
        check_evidence=[dict(check="csv.read-two-sums.source-run.v1" if dual else "csv.read-sum.source-run.v1" if count == 2 else
                            "csv.read-sum-report.source-run.v1", status="PASS", run_id=rid,
                            receipt_fingerprints=execution["receipt_fingerprints"])],
        model_requests=0, semantic_status="UNKNOWN", owner_acceptance="PENDING",
        formal_publication_enabled=False)


@dag.graph.controlled
def validate_snapshot(store, c, user, snapshot, limits):
    execution = snapshot.get("execution_source")
    require(isinstance(execution, dict) and execution.get("version") in VERSIONS,
            "Unknown internal execution source")
    expected = source_snapshot(store, c, user, execution["run_id"], limits)
    require(fingerprint(snapshot) == fingerprint(expected), "Internal version no longer matches its actual source receipts")
    return snapshot


def validate_input(execution, value):
    if execution["version"] == TWO_SUM_VERSION:
        require(isinstance(value, dict) and set(value) == {"columns"}
            and isinstance(value["columns"], dict)
            and set(value["columns"]) == set(execution["aggregate_steps"])
            and all(type(value["columns"][sid]) is str
                and value["columns"][sid] in execution["aggregate_nodes"][sid]["columns"]
                for sid in execution["aggregate_steps"]),
            "Choose exactly one frozen column for each sum node; no structural override")
    else:
        require(isinstance(value, dict) and set(value) == {"column"}
            and type(value["column"]) is str and value["column"] in execution["columns"],
            "Choose one frozen numeric column; no resource or workflow override")


def apply_input(body, execution, value):
    validate_input(execution, value)
    if execution["version"] == TWO_SUM_VERSION:
        wanted = value["columns"]
        body["column"] = wanted[execution["aggregate_steps"][0]]
        for node in body["composition"]["nodes"]:
            if node["step_id"] in wanted:
                node["column"] = wanted[node["step_id"]]
    else:
        body["column"] = value["column"]
        body["composition"]["nodes"][1]["column"] = value["column"]


@dag.graph.controlled
def prepare_release(store, user, rid, expected_plan_fp, limits, *, request_key):
    with store.tx() as c:
        snap = source_snapshot(store, c, user, rid, limits)
        require(snap["execution_source"]["plan_fingerprint"] == expected_plan_fp)
        pid = snap["draft"]["project_id"]
        intent = dict(run_id=rid, expected_plan_fingerprint=expected_plan_fp, request_key=request_key)
        prior = c.execute(select(internal_approvals).where(internal_approvals.c.principal_id == user,
            internal_approvals.c.project_id == pid, internal_approvals.c.kind == "release")).mappings().all()
        found = [a for a in prior if a["payload"].get("dag_intent", {}).get("run_id") == rid
                 and a["payload"].get("dag_intent", {}).get("request_key") == request_key]
        require(len(found) <= 1)
        if found:
            a = found[0]
            lifecycle.approval(c, user, a["id"], a["fingerprint"], "release", allow_consumed=True)
            require(a["payload"].get("dag_intent") == intent and a["payload"]["snapshot"] == snap)
            return dict(id=a["id"], fingerprint=a["fingerprint"], namespace=lifecycle.NAMESPACE,
                        formal_publication_enabled=False)
        approval = lifecycle.new_approval(c, user, pid, "release", dict(snapshot=snap,
            dag_intent=intent, grant_version=lifecycle.grant_version(c, pid, user)))
        body = ReleaseOrigin(version=snap["execution_source"]["version"], request_key=approval["id"], approval_id=approval["id"],
            snapshot_fingerprint=fingerprint(snap), source_run_id=rid)
        for kind in ("csv_dag_release_origin", "csv_dag_release_origin_seal"):
            dag.graph.remember(c, user, snap["draft"]["id"], kind, approval["id"], body, body.model_dump())
        return approval


@dag.graph.controlled
def enqueue_tx(store, c, user, i, release, revision, release_fp, input_value, key, limits):
    snapshot = release["snapshot"]
    validate_snapshot(store, c, user, snapshot, limits)
    execution = snapshot["execution_source"]
    validate_input(execution, input_value)
    request = dict(instance_id=i["id"], expected_revision=revision,
        expected_release_fp=release_fp, input=input_value)
    old = c.execute(select(internal_app_runs).where(internal_app_runs.c.instance_id == i["id"],
        internal_app_runs.c.principal_id == user, internal_app_runs.c.request_key == key)).mappings().first()
    if old:
        require(old["fingerprint"] == fingerprint(request), "Same key changed its complete request")
        b = c.execute(select(internal_run_bindings).where(internal_run_bindings.c.app_run_id == old["id"])).mappings().first()
        require(bool(b))
        job = dag.row(c, user, b["run_id"])
        dag.binding(store, c, job, limits)
        return dict(run_id=job["id"], app_run_id=old["id"], instance_id=i["id"], status=job["status"],
            version=job["version"], cached=True, execution_version=execution["version"])
    require(i["revision"] == revision and release["fingerprint"] == release_fp)
    source_body, source_plan = read_pair(c, user, i["source_app_id"], "csv_dag_plan", execution["plan_key"], dag.PlanInput)
    body = source_body.model_dump(exclude_none=True)
    apply_input(body, execution, input_value)
    body["request_key"] = "instance-plan-" + fingerprint([i["id"], key])[:48]
    cap = Limits(**execution["limits"])
    # No broader platform defaults: compilation and the accepted contract use frozen caps.
    require(all(getattr(limits, k) >= getattr(cap, k) for k in Limits.model_fields), "Current budget tightened")
    plan_body = dag.PlanInput(**body)
    if "logical_reuse" in source_plan:
        from .csv_logic_reuse import INSTANCE_PREFIX, prepare_instance_plan
        plan_body = plan_body.model_copy(update={"request_key": INSTANCE_PREFIX + fingerprint([i["id"], key])[:48]})
        plan_body = prepare_instance_plan(store, c, user, i["project_id"], i["source_app_id"], source_plan, plan_body, cap)
    plan = dag.propose_tx(store, c, user, i["project_id"], i["source_app_id"], plan_body, cap)
    plan.pop("cached")
    rid, arid = new_id("run"), new_id("iapprun")
    s = dict(namespace=execution["version"], **request, run_id=rid, app_run_id=arid, release_id=release["id"],
        principal_id=user, project_id=i["project_id"], runtime_id=i["runtime_id"], request_key=key,
        request_fingerprint=fingerprint(request), limits=cap.model_dump(),
        execution_source=copy.deepcopy(execution), plan_key=plan["request_key"], plan_fingerprint=plan["plan_fingerprint"])
    marker = dict(version=execution["version"], instance_id=i["id"], app_run_id=arid, binding_fingerprint=fingerprint(s))
    confirmation = dag.RunInput(expected_plan_fingerprint=plan["plan_fingerprint"],
        consent="CONFIRM_EXACT_OFFLINE_CSV_DAG", request_key="instance-run-"+fingerprint([i["id"], key])[:48])
    accepted = dag.enqueue_tx(store, c, user, i["project_id"], i["source_app_id"], plan["request_key"],
        confirmation, cap, run_id=rid, internal_instance=marker)
    require(not accepted["cached"])
    c.execute(insert(internal_app_runs).values(id=arid, instance_id=i["id"], release_id=release["id"],
        principal_id=user, request_key=key, fingerprint=fingerprint(request), input=input_value, status="QUEUED"))
    c.execute(insert(internal_run_bindings).values(run_id=rid, app_run_id=arid, snapshot=s, fingerprint=fingerprint(s)))
    return dict(run_id=rid, app_run_id=arid, instance_id=i["id"], status="QUEUED", version=1,
                cached=False, execution_version=execution["version"])


@dag.graph.controlled
def validate_instance_history(c, i):
    """Every pointer transition must have an exact consumed approval; never execute it."""
    history = i["history"]
    require(type(i["revision"]) is int and type(i["data_version"]) is int
        and i["data_version"] >= 0 and isinstance(history, list)
        and len(history) == i["revision"] and len(history) >= 1
        and all(isinstance(entry, dict) for entry in history), "Invalid instance history structure")
    require(fingerprint(history[0]) == fingerprint(dict(
        revision=1, release_id=history[0].get("release_id"), kind="created")))
    records = lifecycle.data_rows(c, i["id"])
    previous_data_version = 0
    for revision, entry in enumerate(history[1:], 2):
        a = c.execute(select(internal_approvals).where(
            internal_approvals.c.id == entry.get("approval_id"))).mappings().first()
        require(a is not None and a["kind"] == "switch" and a["consumed"] is True
            and a["principal_id"] == i["principal_id"] and a["project_id"] == i["project_id"]
            and isinstance(a["payload"], dict)
            and a["fingerprint"] == fingerprint(a["payload"]), "Unapproved instance history")
        p = a["payload"]
        lifecycle.require_switch_payload(p)
        rel = c.execute(select(internal_releases).where(
            internal_releases.c.id == p["target_release_id"])).mappings().first()
        require(rel is not None and rel["principal_id"] == i["principal_id"]
            and rel["project_id"] == i["project_id"] and rel["fingerprint"] == p["target_fingerprint"]
            and fingerprint(rel["snapshot"]) == rel["fingerprint"]
            and rel["snapshot"]["draft"]["id"] == i["source_app_id"]
            and rel["snapshot"]["draft"]["runtime_id"] == i["runtime_id"])
        require(p["instance_id"] == i["id"] and p["revision"] == revision - 1
            and p["from_release_id"] == history[revision - 2]["release_id"]
            and previous_data_version <= p["data_version"] <= i["data_version"]
            and p["data_fingerprint"] == fingerprint([dict(r) for r in records if r["version"] <= p["data_version"]])
            and fingerprint(entry) == fingerprint(dict(revision=revision, release_id=p["target_release_id"],
                previous_release_id=p["from_release_id"], approval_id=a["id"], kind="switch")),
            "Instance switch history changed")
        previous_data_version = p["data_version"]
    require(history[-1]["release_id"] == i["release_id"])


def validate_switch(store, c, user, i, old, target, limits):
    """Keep the closed execution contract and all earlier checked data, with no active Run."""
    a, b = old["snapshot"].get("execution_source"), target["snapshot"].get("execution_source")
    require(isinstance(a, dict) and isinstance(b, dict), "Cannot mix DAG and ordinary versions")
    require(a["version"] in VERSIONS and all(a.get(k) == b.get(k) for k in
        ("version", "aggregate_step", "report_step", "columns", "limits", "read_step", "aggregate_steps", "aggregate_nodes")),
        "DAG execution family, ports, columns and budget must match")
    validate_instance_history(c, i)
    records = lifecycle.data_rows(c, i["id"])
    check_instance_records(store, c, user, i, records, limits)
    for rid in instance_run_ids(c, user, i):
        require(dag.row(c, user, rid)["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"},
            "Finish or cancel outstanding instance Runs before switching")


def validate_binding(store, c, job, accepted, limits, *, authorize=True, historical=False):
    marker = accepted.get("internal_instance")
    b = c.execute(select(internal_run_bindings).where(internal_run_bindings.c.run_id == job["id"])).mappings().first()
    if marker is None:
        require(not b, "An instance Run cannot downgrade to a plain DAG")
        return None
    require(b is not None and isinstance(marker, dict))
    s = b["snapshot"]
    ar = c.execute(select(internal_app_runs).where(internal_app_runs.c.id == b["app_run_id"])).mappings().first()
    require(s.get("namespace") in VERSIONS and s["namespace"] == s["execution_source"]["version"]
        and b["fingerprint"] == fingerprint(s)
        and marker == dict(version=s["namespace"], instance_id=s["instance_id"], app_run_id=s["app_run_id"],
                           binding_fingerprint=fingerprint(s))
        and s["run_id"] == job["id"] and s["principal_id"] == job["principal_id"]
        and s["project_id"] == job["project_id"] and s["runtime_id"] == job["runtime_id"]
        and s["app_run_id"] == b["app_run_id"] and ar is not None
        and ar["instance_id"] == s["instance_id"] and ar["release_id"] == s["release_id"]
        and ar["principal_id"] == job["principal_id"] and ar["request_key"] == s["request_key"]
        and ar["input"] == s["input"] and ar["fingerprint"] == s["request_fingerprint"]
        and s["request_fingerprint"] == fingerprint({k:s[k] for k in
            ("instance_id", "expected_revision", "expected_release_fp", "input")})
        and accepted["plan_key"] == s["plan_key"] and accepted["plan"]["plan_fingerprint"] == s["plan_fingerprint"])
    i = c.execute(select(internal_instances).where(internal_instances.c.id == s["instance_id"])).mappings().first()
    rel = c.execute(select(internal_releases).where(internal_releases.c.id == s["release_id"])).mappings().first()
    require(i is not None and rel is not None and i["principal_id"] == job["principal_id"]
        and i["project_id"] == job["project_id"] and i["runtime_id"] == job["runtime_id"]
        and i["source_app_id"] == accepted["app_id"]
        and rel["principal_id"] == job["principal_id"] and rel["project_id"] == job["project_id"]
        and rel["snapshot"]["draft"]["project_id"] == job["project_id"]
        and rel["snapshot"]["draft"]["runtime_id"] == job["runtime_id"]
        and rel["snapshot"]["draft"]["id"] == accepted["app_id"]
        and rel["fingerprint"] == s["expected_release_fp"])
    validate_family(c, job["principal_id"], rel["approval_id"], rel["snapshot"])
    archived = historical and job["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}
    if archived:
        validate_instance_history(c, i)
        require(any(h["revision"] == s["expected_revision"] and h["release_id"] == s["release_id"]
                    for h in i["history"]), "Run has no approved historical revision")
    else:
        require(i["release_id"] == rel["id"])
    if authorize:
        i, r = lifecycle.instance(store, c, job["principal_id"], s["instance_id"], limits, lock=True)
        if archived:
            r = lifecycle.read_release(store, c, job["principal_id"], s["release_id"], limits)
        else:
            require(i["revision"] == s["expected_revision"] and i["release_id"] == s["release_id"])
        require(i["project_id"] == job["project_id"] and i["runtime_id"] == job["runtime_id"]
            and i["source_app_id"] == accepted["app_id"] and r["fingerprint"] == s["expected_release_fp"]
            and r["snapshot"]["execution_source"] == s["execution_source"]
            and s["limits"] == s["execution_source"]["limits"])
        source_body, source_plan = read_pair(c, job["principal_id"], accepted["app_id"], "csv_dag_plan", s["execution_source"]["plan_key"], dag.PlanInput)
        derived_body, derived_plan = read_pair(c, job["principal_id"], accepted["app_id"], "csv_dag_plan", s["plan_key"], dag.PlanInput)
        expected = source_body.model_dump(exclude_none=True)
        apply_input(expected, s["execution_source"], s["input"])
        expected["request_key"] = "instance-plan-" + fingerprint([i["id"], s["request_key"]])[:48]
        if "logical_reuse" in source_plan:
            from .csv_logic_reuse import INSTANCE_PREFIX
            expected["request_key"] = INSTANCE_PREFIX + fingerprint([i["id"], s["request_key"]])[:48]
            expected["logic_origin"] = source_plan["logical_reuse"]
            require(derived_plan.get("logical_reuse") == source_plan["logical_reuse"])
        require(fingerprint(derived_body.model_dump(exclude_none=True)) == fingerprint(expected))
        require(store.frozen_contract(c, job).limits.model_dump() == s["limits"])
        closed(accepted["plan"])
    return s, ar


@dag.graph.controlled
def ledger_result(c, s, ar, base):
    record = c.execute(select(internal_instance_data).where(internal_instance_data.c.run_id == ar["id"])).mappings().first()
    require(record is not None and ar["status"] == "SUCCEEDED" and record["instance_id"] == s["instance_id"]
        and record["release_id"] == s["release_id"] and record["version"] == ar["result_version"]
        and record["schema_version"] == 1 and fingerprint(record["data"]) == fingerprint({"result": ar["output"]})
        and fingerprint(record["data"]) == record["fingerprint"]
        and fingerprint(ar["output"]) == fingerprint(aggregate_result(base, s["execution_source"])))
    return {**base, "business_writes": 1, "instance_result": dict(instance_id=s["instance_id"],
        app_run_id=ar["id"], release_id=s["release_id"], result_version=record["version"],
        record_fingerprint=record["fingerprint"])}


@dag.graph.controlled
def checked_result(store, c, job, accepted, base, limits):
    value = validate_binding(store, c, job, accepted, limits, historical=True)
    if value is None:
        return base
    s, ar = value
    return ledger_result(c, s, ar, base)


@dag.graph.controlled
def commit_result(store, c, job, accepted, base, limits):
    value = validate_binding(store, c, job, accepted, limits)
    if value is None:
        return base
    s, ar = value
    require(ar["status"] != "SUCCEEDED" and ar["result_version"] is None)
    i, r = lifecycle.instance(store, c, job["principal_id"], s["instance_id"], limits, lock=True)
    output = aggregate_result(base, s["execution_source"])
    require(base["output_status"] == "PRODUCED" and len(base["steps"]) ==
            (2 if s["namespace"] == VERSION else 3))
    validate_value(r["snapshot"]["data_schema"], {"result": output})
    content = dag.read_source(store, c, job)["content"]
    for value in output.values() if s["namespace"] == TWO_SUM_VERSION else [output]:
        dag.oracle(content, value)
    version = i["data_version"] + 1
    data = {"result": output}
    c.execute(insert(internal_instance_data).values(instance_id=i["id"], version=version, run_id=ar["id"],
        release_id=r["id"], schema_version=1, data=data, fingerprint=fingerprint(data)))
    changed = c.execute(update(internal_instances).where(internal_instances.c.id == i["id"],
        internal_instances.c.revision == s["expected_revision"], internal_instances.c.release_id == r["id"],
        internal_instances.c.data_version == i["data_version"]).values(data_version=version)).rowcount
    require(changed == 1)
    c.execute(update(internal_app_runs).where(internal_app_runs.c.id == ar["id"]).values(
        status="SUCCEEDED", error=None, output=output, result_version=version))
    return ledger_result(c, s, {**ar, "status":"SUCCEEDED", "output":output, "result_version":version}, base)


def sync_state(store, c, job, state, error):
    accepted = c.execute(select(events.c.data).where(events.c.run_id == job["id"], events.c.kind == "CSV_DAG_ACCEPTED")).scalars().all()
    if len(accepted) != 1 or "internal_instance" not in accepted[0]:
        return
    # Bad provenance must not grant authority to alter a foreign AppRun on failure.
    try:
        require(fingerprint(accepted[0]) == job["fingerprint"])
        value = validate_binding(store, c, job, accepted[0], None, authorize=False)
    except (DomainError, KeyError, TypeError):
        return
    if value:
        s, _ = value
        c.execute(update(internal_app_runs).where(internal_app_runs.c.id == s["app_run_id"]).values(status=state, error=error))


@dag.graph.controlled
def inspect_job(store, user, rid, limits):
    with store.tx() as c:
        proof = dag.inspect_job_tx(store, c, user, rid, limits)
        job = dag.row(c, user, rid)
        accepted = dag.binding(store, c, job, limits, historical=True)
        value = validate_binding(store, c, job, accepted, limits, historical=True)
        require(value is not None)
        s, ar = value
        return {**dict(ar), "namespace": lifecycle.NAMESPACE, "execution_version": s["namespace"],
            "run_id": rid, "app_run_id": ar["id"], "version": job["version"], "status": job["status"],
            "expected_revision": s["expected_revision"], "plan_key": s["plan_key"], "proof": proof}


@dag.graph.controlled
def instance_run_ids(c, user, i):
    # Enumerate either independently persisted acceptance row, not only the joins
    # whose deletion we are trying to detect.
    accepted = c.execute(select(delivery_graph_requests).where(
        delivery_graph_requests.c.principal_id == user,
        delivery_graph_requests.c.app_id == i["source_app_id"],
        delivery_graph_requests.c.kind.in_(["csv_dag_run", "csv_dag_run_seal"]))).mappings().all()
    wanted = set()
    for row in accepted:
        response = dag.graph.checked(row)["response"]
        marker = response.get("internal_instance")
        if marker is not None and marker.get("instance_id") == i["id"]:
            _, receipt = read_pair(c, user, i["source_app_id"], "csv_dag_run", row["request_key"], dag.RunInput)
            require(receipt == response and marker.get("version") in VERSIONS)
            wanted.add(receipt["run_id"])
    joined = set(c.execute(select(internal_run_bindings.c.run_id).join(internal_app_runs,
        internal_app_runs.c.id == internal_run_bindings.c.app_run_id).where(
            internal_app_runs.c.instance_id == i["id"], internal_app_runs.c.principal_id == user)).scalars().all())
    # The acceptance event is a third independent link. Pair markers and joins
    # can be jointly removed while the original accepted Run still exists.
    event_rows = c.execute(select(events.c.run_id, events.c.data).where(
        events.c.kind == "CSV_DAG_ACCEPTED",
        events.c.data["principal_id"].as_string() == user,
        events.c.data["project_id"].as_string() == i["project_id"],
        events.c.data["app_id"].as_string() == i["source_app_id"],
        events.c.data["internal_instance"]["instance_id"].as_string() == i["id"])).all()
    event_ids = {rid for rid, _ in event_rows}
    require(len(event_ids) == len(event_rows) and wanted == joined == event_ids,
        "Accepted instance Run history is incomplete")
    return sorted(wanted)


@dag.graph.controlled
def check_instance_records(store, c, user, i, records, limits):
    require(type(i["data_version"]) is int and i["data_version"] == len(records)
        and [r["version"] for r in records] == list(range(1, i["data_version"] + 1)),
        "Typed instance versions are missing or reordered")
    succeeded = set()
    for rid in instance_run_ids(c, user, i):
        proof = dag.inspect_job_tx(store, c, user, rid, limits)
        if proof["status"] == "SUCCEEDED":
            pointer = proof["result"]["instance_result"]
            succeeded.add(pointer["app_run_id"])
            record = next((r for r in records if r["run_id"] == pointer["app_run_id"]), None)
            require(record is not None and pointer["record_fingerprint"] == record["fingerprint"])
    require(succeeded == {r["run_id"] for r in records}, "Result/Run terminal history is incomplete")


class ReleaseOrigin(KeyInput):
    request_key: str
    version: str
    approval_id: str
    snapshot_fingerprint: str
    source_run_id: str


@dag.graph.controlled
def validate_family(c, user, approval_id, snapshot):
    anchors = c.execute(select(delivery_graph_requests.c.app_id).where(
        delivery_graph_requests.c.principal_id == user,
        delivery_graph_requests.c.request_key == approval_id,
        delivery_graph_requests.c.kind.in_(["csv_dag_release_origin", "csv_dag_release_origin_seal"]))).scalars().all()
    require(len(anchors) <= 2 and len(set(anchors)) <= 1)
    if not anchors:
        approval_payload = c.execute(select(internal_approvals.c.payload).where(internal_approvals.c.id == approval_id, internal_approvals.c.principal_id == user)).scalar()
        require(not marked(snapshot) and not (isinstance(approval_payload, dict) and "dag_intent" in approval_payload), "Missing independent DAG release origin")
        return False
    aid = anchors[0]
    body, answer = read_pair(c, user, aid, "csv_dag_release_origin", approval_id, ReleaseOrigin)
    require(body.model_dump() == answer and body.version in VERSIONS and body.approval_id == approval_id
        and aid == snapshot["draft"]["id"] and marked(snapshot)
        and snapshot["execution_source"].get("version") == body.version
        and snapshot["execution_source"].get("run_id") == body.source_run_id
        and fingerprint(snapshot) == body.snapshot_fingerprint,
        "DAG release cannot change or downgrade execution family")
    return True
