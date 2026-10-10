"""Closed read→sum instance adapter. Uses the existing DAG worker and typed ledger.

A completed, independently reconstructed source Run anchors each immutable version.
No new manifest family, executor, principal, Grant or publication capability.
"""
import copy

from sqlalchemy import insert, select, update

from . import csv_dag as dag
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


def require(ok, message="Internal DAG provenance changed"):
    if not ok:
        raise DomainError("VERSION_CONFLICT", message)


def marked(snapshot):
    return "execution_source" in snapshot


def closed(plan):
    nodes = plan.get("composition", {}).get("definition", {}).get("nodes", [])
    require(len(nodes) == 2 and not any(k in plan for k in ("branch_semantics",)),
            "Only unconditional read→sum composition is reusable")
    read, total = nodes
    require(read["action"] == "resource.read" and total["action"] == "data.aggregate_csv"
        and read["depends_on"] == [] and total["depends_on"] == [read["step_id"]]
        and not any("when" in node for node in nodes)
        and read["inputs"] == {"resource_id": dict(source="data", ref="source", field="resource_id")}
        and total["inputs"] == {
            "resource_id": dict(source="step", ref=read["step_id"], field="resource_id"),
            "column": dict(source="input", field=total["step_id"] + "_column")}
        and plan["composition"]["sinks"] == [total["step_id"]],
        "Only the closed read→sum ports can be reused")
    return total["step_id"]


@dag.graph.controlled
def source_snapshot(store, c, user, rid, limits):
    dag.owner_lock(store, c, user, rid)
    job = dag.row(c, user, rid)
    bound = dag.binding(store, c, job, limits)
    require("internal_instance" not in bound, "A source must be an original completed DAG Run")
    proof = dag.inspect_job_tx(store, c, user, rid, limits)
    plan = bound["plan"]
    sid = closed(plan)
    require(proof["status"] == "SUCCEEDED" and len(proof["steps"]) == 2
        and all(p["status"] == "VERIFIED" for p in proof["steps"])
        and job["context"]["tools"] == 2, "Two actual verified source operations required")
    draft, _, _, _ = load_draft(store, c, user, bound["app_id"], limits, lock=True)
    frozen = {k: copy.deepcopy(draft[k]) for k in ("id", "project_id", "runtime_id", "candidate", "fingerprint")}
    raw = dag.read_source(store, c, job)
    columns = [v["name"] for v in csv_column_options(raw["content"])["columns"] if v["numeric"]]
    cap = store.frozen_contract(c, job).limits
    declared = Limits(**plan["definition"]["manifest"]["runtime_limits"])
    effective = Limits(**{k: min(getattr(cap, k), getattr(declared, k)) for k in Limits.model_fields})
    schema = lifecycle.record_schema(frozen["candidate"])
    validate_value(schema, {"result": proof["result"]["output_by_step"][sid]})
    execution = dict(version=VERSION, run_id=rid, run_version=job["version"], fence=job["fence"],
        accepted_fingerprint=job["fingerprint"], plan_key=bound["plan_key"],
        plan_fingerprint=plan["plan_fingerprint"], source_hash=plan["source_hash"],
        graph_fingerprint=plan["graph_fingerprint"], authorization_fingerprint=plan["authorization_fingerprint"],
        receipt_fingerprints=[fingerprint(p) for p in proof["steps"]], aggregate_step=sid,
        columns=columns, limits=effective.model_dump())
    return dict(namespace=lifecycle.NAMESPACE, draft=frozen,
        dependency_lock=frozen["candidate"]["manifest"]["dependency_lock"], data_schema=schema,
        data_schema_version=1, execution_source=execution,
        check_evidence=[dict(check="csv.read-sum.source-run.v1", status="PASS", run_id=rid,
                            receipt_fingerprints=execution["receipt_fingerprints"])],
        model_requests=0, semantic_status="UNKNOWN", owner_acceptance="PENDING",
        formal_publication_enabled=False)


@dag.graph.controlled
def validate_snapshot(store, c, user, snapshot, limits):
    execution = snapshot.get("execution_source")
    require(isinstance(execution, dict) and execution.get("version") == VERSION,
            "Unknown internal execution source")
    expected = source_snapshot(store, c, user, execution["run_id"], limits)
    require(fingerprint(snapshot) == fingerprint(expected), "Internal version no longer matches its actual source receipts")
    return snapshot


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
        body = ReleaseOrigin(version=VERSION, request_key=approval["id"], approval_id=approval["id"],
            snapshot_fingerprint=fingerprint(snap), source_run_id=rid)
        for kind in ("csv_dag_release_origin", "csv_dag_release_origin_seal"):
            dag.graph.remember(c, user, snap["draft"]["id"], kind, approval["id"], body, body.model_dump())
        return approval


@dag.graph.controlled
def enqueue_tx(store, c, user, i, release, revision, release_fp, input_value, key, limits):
    snapshot = release["snapshot"]
    validate_snapshot(store, c, user, snapshot, limits)
    execution = snapshot["execution_source"]
    require(isinstance(input_value, dict) and set(input_value) == {"column"}
            and type(input_value["column"]) is str and input_value["column"] in execution["columns"],
            "Choose one frozen numeric column; no resource or workflow override")
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
            version=job["version"], cached=True, execution_version=VERSION)
    require(i["revision"] == revision and release["fingerprint"] == release_fp)
    source_body, _ = read_pair(c, user, i["source_app_id"], "csv_dag_plan", execution["plan_key"], dag.PlanInput)
    body = source_body.model_dump(exclude_none=True)
    body["column"] = input_value["column"]
    body["composition"]["nodes"][1]["column"] = input_value["column"]
    body["request_key"] = "instance-plan-" + fingerprint([i["id"], key])[:48]
    cap = Limits(**execution["limits"])
    # No broader platform defaults: compilation and the accepted contract use frozen caps.
    require(all(getattr(limits, k) >= getattr(cap, k) for k in Limits.model_fields), "Current budget tightened")
    plan = dag.propose_tx(store, c, user, i["project_id"], i["source_app_id"], dag.PlanInput(**body), cap)
    plan.pop("cached")
    rid, arid = new_id("run"), new_id("iapprun")
    s = dict(namespace=VERSION, **request, run_id=rid, app_run_id=arid, release_id=release["id"],
        principal_id=user, project_id=i["project_id"], runtime_id=i["runtime_id"], request_key=key,
        request_fingerprint=fingerprint(request), limits=cap.model_dump(),
        execution_source=copy.deepcopy(execution), plan_key=plan["request_key"], plan_fingerprint=plan["plan_fingerprint"])
    marker = dict(version=VERSION, instance_id=i["id"], app_run_id=arid, binding_fingerprint=fingerprint(s))
    confirmation = dag.RunInput(expected_plan_fingerprint=plan["plan_fingerprint"],
        consent="CONFIRM_EXACT_OFFLINE_CSV_DAG", request_key="instance-run-"+fingerprint([i["id"], key])[:48])
    accepted = dag.enqueue_tx(store, c, user, i["project_id"], i["source_app_id"], plan["request_key"],
        confirmation, cap, run_id=rid, internal_instance=marker)
    require(not accepted["cached"])
    c.execute(insert(internal_app_runs).values(id=arid, instance_id=i["id"], release_id=release["id"],
        principal_id=user, request_key=key, fingerprint=fingerprint(request), input=input_value, status="QUEUED"))
    c.execute(insert(internal_run_bindings).values(run_id=rid, app_run_id=arid, snapshot=s, fingerprint=fingerprint(s)))
    return dict(run_id=rid, app_run_id=arid, instance_id=i["id"], status="QUEUED", version=1,
                cached=False, execution_version=VERSION)


@dag.graph.controlled
def validate_binding(store, c, job, accepted, limits, *, authorize=True):
    marker = accepted.get("internal_instance")
    b = c.execute(select(internal_run_bindings).where(internal_run_bindings.c.run_id == job["id"])).mappings().first()
    if marker is None:
        require(not b, "An instance Run cannot downgrade to a plain DAG")
        return None
    require(b is not None and isinstance(marker, dict))
    s = b["snapshot"]
    ar = c.execute(select(internal_app_runs).where(internal_app_runs.c.id == b["app_run_id"])).mappings().first()
    require(s.get("namespace") == VERSION and b["fingerprint"] == fingerprint(s)
        and marker == dict(version=VERSION, instance_id=s["instance_id"], app_run_id=s["app_run_id"],
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
        and i["source_app_id"] == accepted["app_id"] and i["release_id"] == rel["id"]
        and rel["principal_id"] == job["principal_id"] and rel["project_id"] == job["project_id"]
        and rel["snapshot"]["draft"]["project_id"] == job["project_id"]
        and rel["snapshot"]["draft"]["runtime_id"] == job["runtime_id"]
        and rel["snapshot"]["draft"]["id"] == accepted["app_id"]
        and rel["fingerprint"] == s["expected_release_fp"])
    validate_family(c, job["principal_id"], rel["approval_id"], rel["snapshot"])
    if authorize:
        i, r = lifecycle.instance(store, c, job["principal_id"], s["instance_id"], limits, lock=True)
        require(i["revision"] == s["expected_revision"] and i["release_id"] == s["release_id"]
            and i["project_id"] == job["project_id"] and i["runtime_id"] == job["runtime_id"]
            and i["source_app_id"] == accepted["app_id"] and r["fingerprint"] == s["expected_release_fp"]
            and r["snapshot"]["execution_source"] == s["execution_source"]
            and s["limits"] == s["execution_source"]["limits"])
        source_body, _ = read_pair(c, job["principal_id"], accepted["app_id"], "csv_dag_plan", s["execution_source"]["plan_key"], dag.PlanInput)
        derived_body, _ = read_pair(c, job["principal_id"], accepted["app_id"], "csv_dag_plan", s["plan_key"], dag.PlanInput)
        expected = source_body.model_dump(exclude_none=True)
        expected["column"] = s["input"]["column"]
        expected["composition"]["nodes"][1]["column"] = s["input"]["column"]
        expected["request_key"] = "instance-plan-" + fingerprint([i["id"], s["request_key"]])[:48]
        require(derived_body.model_dump(exclude_none=True) == expected and s["input"]["column"] in s["execution_source"]["columns"])
        require(store.frozen_contract(c, job).limits.model_dump() == s["limits"])
        closed(accepted["plan"])
    return s, ar


@dag.graph.controlled
def ledger_result(c, s, ar, base):
    record = c.execute(select(internal_instance_data).where(internal_instance_data.c.run_id == ar["id"])).mappings().first()
    require(record is not None and ar["status"] == "SUCCEEDED" and record["instance_id"] == s["instance_id"]
        and record["release_id"] == s["release_id"] and record["version"] == ar["result_version"]
        and record["schema_version"] == 1 and record["data"] == {"result": ar["output"]}
        and fingerprint(record["data"]) == record["fingerprint"]
        and ar["output"] == base["output_by_step"][s["execution_source"]["aggregate_step"]])
    return {**base, "business_writes": 1, "instance_result": dict(instance_id=s["instance_id"],
        app_run_id=ar["id"], release_id=s["release_id"], result_version=record["version"],
        record_fingerprint=record["fingerprint"])}


@dag.graph.controlled
def checked_result(store, c, job, accepted, base, limits):
    value = validate_binding(store, c, job, accepted, limits)
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
    sid = s["execution_source"]["aggregate_step"]
    output = base["output_by_step"][sid]
    require(base["output_status"] == "PRODUCED" and len(base["steps"]) == 2)
    validate_value(r["snapshot"]["data_schema"], {"result": output})
    dag.oracle(dag.read_source(store, c, job)["content"], output)
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
        accepted = dag.binding(store, c, job, limits)
        value = validate_binding(store, c, job, accepted, limits)
        require(value is not None)
        s, ar = value
        return {**dict(ar), "namespace": lifecycle.NAMESPACE, "execution_version": VERSION,
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
            require(receipt == response and marker.get("version") == VERSION)
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
    require(body.model_dump() == answer and body.version == VERSION and body.approval_id == approval_id
        and aid == snapshot["draft"]["id"] and marked(snapshot)
        and snapshot["execution_source"].get("version") == VERSION
        and snapshot["execution_source"].get("run_id") == body.source_run_id
        and fingerprint(snapshot) == body.snapshot_fingerprint,
        "DAG release cannot change or downgrade execution family")
    return True
