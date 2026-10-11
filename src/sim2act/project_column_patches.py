"""Finite shared-CSV binding overlays, checked by the existing DAG worker.

Only canonical single-sum drafts are admitted. This is an immutable project
candidate, never a mutation of resources, canonical manifests or releases.
"""

import time
from typing import Literal

from fastapi import Depends
from pydantic import Field
from sqlalchemy import select

from . import column_patches as columns
from . import csv_dag as dag
from . import delivery_graph_apps as graph
from .contracts import Limits
from .db import app_drafts, delivery_graph_locks, fingerprint
from .delivery_graph import Change
from .errors import DomainError
from .project_revalidation import CSVBinding, CSVInput, SafeInput, csv_check

KIND = "project_column_patch"
START = KIND + "_start"
FINISH = KIND + "_finish"
NAMESPACE = "finite-project-column-patch.v1"
MAX_APPS = 16
DISCLAIMER = "Finite declarations do not certify full semantic dependency completeness; owner acceptance pending"


class Proposal(SafeInput):
    expected_candidate_fingerprint: str = Field(pattern=graph.HASH)
    expected_graph_fingerprint: str = Field(pattern=graph.HASH)
    baseline_column: str = Field(min_length=1, max_length=200)
    column: str = Field(min_length=1, max_length=200)
    request_key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")


class Confirmation(SafeInput):
    expected_patch_fingerprint: str = Field(pattern=graph.HASH)
    consent: Literal["CONFIRM_EXACT_FINITE_PROJECT_COLUMN_PATCH"]
    request_key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")


def flags():
    return dict(semantic_status="UNKNOWN", owner_acceptance="PENDING", publishable=False,
                formal_publication_enabled=False, model_requests=0, business_writes=0,
                canonical_patch_executed=False)


def key_for(key, aid, purpose):
    return "project-column-" + fingerprint([key, aid, purpose])[:48]


def finite(saved, manifest, action):
    """Reject opaque/semantic/project dependencies; retain the semantic disclaimer.

    Current() re-derives this exact trusted canonical graph. The sole APP
    disclaimer is not evidence for arbitrary dependencies or semantic acceptance.
    """
    g = saved["graph"]
    if (action.executor.kind != "registered_tool" or action.executor.ref != "data.aggregate_csv"
            or len(manifest.workflow) != 1 or len(manifest.data_bindings) != 1
            or any(e["type"] == "SEMANTIC" or e["provenance"] == "MODEL_CANDIDATE" for e in g["edges"])
            or g["unknown_dependencies"] != [dict(node_id=manifest.app_id, scope="APP", reason=DISCLAIMER)]):
        raise DomainError("UNSUPPORTED_CAPABILITY", "Project column patch requires only provable fixed CSV bindings; opaque or semantic dependencies remain unsupported")


def build(store, c, user, pid, aid, body, limits):
    store.lock_project(c, user, pid)
    ids = c.execute(select(app_drafts.c.id).where(app_drafts.c.project_id == pid)
                    .order_by(app_drafts.c.id).limit(MAX_APPS + 1)).scalars().all()
    if len(ids) > MAX_APPS:
        raise DomainError("UNSUPPORTED_CAPABILITY", "Finite project requires at most 16 canonical CSV drafts")
    if aid not in ids:
        raise DomainError("PERMISSION_DENIED")
    target = graph.current(store, c, user, pid, aid, limits)
    if (body.expected_candidate_fingerprint != target["candidate_fingerprint"]
            or body.expected_graph_fingerprint != target["graph"]["graph_fingerprint"]):
        graph.conflict("Project column target version changed")
    source_ids = target["graph"]["resource_ids"]
    if len(source_ids) != 1:
        raise DomainError("UNSUPPORTED_CAPABILITY", "One fixed CSV source required")
    members, affected, preserved = [], [], []
    for peer in ids:
        saved = graph.current(store, c, user, pid, peer, limits)
        draft, manifest, action, *_ = graph.load_family(store, c, user, pid, peer, limits)
        finite(saved, manifest, action)
        if len(draft["candidate"]["actions"]) != 1:
            raise DomainError("UNSUPPORTED_CAPABILITY", "Only the single-sum canonical family is supported")
        members.append(dict(anchor=saved, lock_records=[dict(r) for r in c.execute(
            select(delivery_graph_locks).where(delivery_graph_locks.c.app_id == peer)
            .order_by(delivery_graph_locks.c.node_id)).mappings()]))
        if manifest.data_bindings[0].resource_ref == source_ids[0]:
            node = next(n for n in saved["graph"]["nodes"] if n["key"] == "action:aggregate")
            definition = columns.DefinitionInput(
                expected_candidate_fingerprint=saved["candidate_fingerprint"],
                expected_graph_fingerprint=saved["graph"]["graph_fingerprint"],
                request_key=key_for(body.request_key, peer, "overlay"),
                kind="csv.column-binding.v1", baseline_column=body.baseline_column, column=body.column,
                change=Change(node_id=node["id"], expected_revision=node["revision"],
                            expected_content_fingerprint=node["content_fingerprint"]))
            patch = columns.build(store, c, user, pid, peer, definition, limits)
            affected.append(dict(app_id=peer, name=draft["name"], request=definition.model_dump(), patch=patch))
        else:
            preserved.append(dict(app_id=peer, nodes=saved["graph"]["nodes"]))
    value = dict(namespace=NAMESPACE, project_id=pid, app_id=aid, principal_id=user,
                 request_key=body.request_key, source_id=source_ids[0],
                 baseline_column=body.baseline_column, column=body.column,
                 members=members, affected=affected, preserved=preserved,
                 dependency_scope="FIXED_CSV_BINDINGS_ONLY", semantic_dependencies_discharged=False,
                 budget=dict(max_applications=MAX_APPS, applications=len(affected),
                             worker_tools=6 * len(affected), model_requests=0,
                             per_run=limits.model_dump(), finalization_seconds=limits.run_seconds),
                 state="DRAFT_PROJECT_PATCH", checks_status="NOT_RUN", **flags())
    return {**value, "patch_fingerprint": fingerprint(value)}


def load(store, c, user, pid, aid, key, limits):
    # Scope and current source authority precede even protected receipt lookup.
    graph.current(store, c, user, pid, aid, limits)
    body, saved = columns.read_pair(c, user, aid, KIND, key, Proposal)
    if fingerprint(build(store, c, user, pid, aid, body, limits)) != fingerprint(saved):
        graph.conflict("Project membership, source, versions, authority, locks or budget changed")
    return saved


def save_pair(c, user, aid, kind, key, body, value):
    columns.require_capacity(c, user, aid, kind)
    for name in (kind, kind + "_seal"):
        graph.remember(c, user, aid, name, key, body, value)


@graph.controlled
def propose(store, user, pid, aid, body, limits):
    with store.tx() as c:
        value = build(store, c, user, pid, aid, body, limits)
        if graph.lookup(c, user, aid, KIND, body.request_key):
            old, _ = columns.read_pair(c, user, aid, KIND, body.request_key, Proposal)
            if old != body:
                graph.conflict("Project column request key changed")
            return {**load(store, c, user, pid, aid, body.request_key, limits), "cached": True}
        save_pair(c, user, aid, KIND, body.request_key, body, value)
        return {**value, "cached": False}


def accepted(store, c, user, pid, aid, key, limits):
    patch = load(store, c, user, pid, aid, key, limits)
    body, value = columns.read_pair(c, user, aid, START, key, Confirmation)
    if body.expected_patch_fingerprint != patch["patch_fingerprint"]:
        graph.conflict("Project patch exact confirmation changed")
    if (value.get("patch_fingerprint") != patch["patch_fingerprint"]
            or value.get("request_key") != body.request_key
            or value.get("patch_key") != key
            or {(v["app_id"], v["phase"]) for v in value["jobs"]} != {
                (v["app_id"], phase) for v in patch["affected"] for phase in ("baseline", "patched")}
            or len(value["jobs"]) != 2 * len(patch["affected"])
            or fingerprint(value.get("budget")) != fingerprint(patch["budget"])):
        graph.conflict("Project patch accepted job membership changed")
    for job in value["jobs"]:
        if (job["plan_key"] != key_for(key, job["app_id"], job["phase"] + "-plan")
                or job["run_key"] != key_for(key, job["app_id"], job["phase"] + "-run")):
            graph.conflict("Project job request keys changed")
        plan = dag.load_plan(store, c, user, pid, job["app_id"], job["plan_key"], limits)
        request, receipt = columns.read_pair(c, user, job["app_id"], "csv_dag_run", job["run_key"], dag.RunInput)
        column = patch["baseline_column"] if job["phase"] == "baseline" else patch["column"]
        if (plan["input"] != {"column": column}
                or request.expected_plan_fingerprint != plan["plan_fingerprint"]
                or receipt["run_id"] != job["run_id"]):
            graph.conflict("Project patch job column or identity changed")
        row = dag.row(c, user, job["run_id"])
        if (fingerprint(row["created_at"]) != fingerprint(job["accepted_at"])
                or fingerprint(job["deadline"]) != fingerprint(job["accepted_at"] + patch["budget"]["finalization_seconds"])):
            graph.conflict("Project job acceptance time or deadline changed")
        dag.binding(store, c, row, limits)
    wanted = start_receipt(pid, aid, key, patch, value["jobs"])
    if fingerprint(value) != fingerprint(wanted):
        graph.conflict("Project acceptance claims changed")
    return patch, body, value


def start_receipt(pid, aid, key, patch, jobs):
    return dict(namespace=NAMESPACE, project_id=pid, app_id=aid, patch_key=key,
                patch_fingerprint=patch["patch_fingerprint"], request_key=key,
                jobs=jobs, budget=patch["budget"], state="CHECKS_QUEUED", checks_status="NOT_RUN", **flags())


@graph.controlled
def start(store, user, pid, aid, key, body, limits):
    with store.tx() as c:
        patch = load(store, c, user, pid, aid, key, limits)
        if body.request_key != key or body.expected_patch_fingerprint != patch["patch_fingerprint"]:
            graph.conflict("Confirm the exact finite project patch")
        if graph.lookup(c, user, aid, START, key):
            _, old, value = accepted(store, c, user, pid, aid, key, limits)
            if old != body:
                graph.conflict("Project patch already has a different confirmation")
            return {**value, "cached": True}
        jobs = []
        for item, phase, column in [(item, phase, column) for item in patch["affected"]
                                   for phase, column in (("baseline", patch["baseline_column"]), ("patched", patch["column"]))]:
            peer = item["app_id"]
            request = dag.PlanInput(expected_candidate_fingerprint=item["patch"]["candidate_fingerprint"],
                expected_graph_fingerprint=item["patch"]["baseline_graph_fingerprint"],
                column=column, request_key=key_for(key, peer, phase + "-plan"))
            plan = dag.propose_tx(store, c, user, pid, peer, request, limits)
            run_body = dag.RunInput(expected_plan_fingerprint=plan["plan_fingerprint"],
                consent="CONFIRM_EXACT_OFFLINE_CSV_DAG", request_key=key_for(key, peer, phase + "-run"))
            result = dag.enqueue_tx(store, c, user, pid, peer, request.request_key, run_body, limits)
            accepted_at = dag.row(c, user, result["run_id"])["created_at"]
            jobs.append(dict(app_id=peer, phase=phase, plan_key=request.request_key, run_key=run_body.request_key,
                             run_id=result["run_id"], accepted_at=accepted_at,
                             deadline=accepted_at + patch["budget"]["finalization_seconds"]))
        value = start_receipt(pid, aid, key, patch, jobs)
        # Recheck the frozen project after all job acceptance; every insert rolls
        # back together if any peer, capacity or version check fails.
        load(store, c, user, pid, aid, key, limits)
        save_pair(c, user, aid, START, key, body, value)
        return {**value, "cached": False}


def outcome(store, c, user, pid, aid, key, limits):
    patch, _, start_value = accepted(store, c, user, pid, aid, key, limits)
    jobs = []
    complete = True
    failed = False
    for bound in start_value["jobs"]:
        proof = dag.inspect_job_tx(store, c, user, bound["run_id"], limits)
        row = dag.row(c, user, bound["run_id"])
        if row["cancel_intent"] or proof["status"] in {"FAILED", "CANCELLED", "PARTIAL", "WAITING_RESOURCE"}:
            failed = True
        if proof["status"] != "SUCCEEDED":
            complete = False
        jobs.append(dict(**bound, proof=proof, fence=row["fence"], cancel_intent=row["cancel_intent"]))
    checks = []
    if complete and not failed:
        for item in patch["affected"]:
            peer = item["app_id"]
            parts = graph.load_family(store, c, user, pid, peer, limits)
            actual = {}
            for name, column in (("baseline", patch["baseline_column"]), ("patched", patch["column"])):
                selection = CSVBinding(app_id=peer, kind="CSV",
                    expected_graph_fingerprint=item["patch"]["baseline_graph_fingerprint"], input=CSVInput(column=column))
                actual[name] = csv_check(store, c, user, pid, parts, selection)
                if actual[name]["status"] != "PASS":
                    failed = True
                worker_output = next(j for j in jobs if j["app_id"] == peer and j["phase"] == name)["proof"]["result"]["output"]
                if fingerprint({k: worker_output[k] for k in actual[name]["output"]}) != fingerprint(actual[name]["output"]):
                    failed = True
            checks.append(dict(app_id=peer, actual=actual))
    load(store, c, user, pid, aid, key, limits)
    value = dict(namespace=NAMESPACE, project_id=pid, app_id=aid, patch_key=key,
                 patch_fingerprint=patch["patch_fingerprint"], request_key=start_value["request_key"],
                 jobs=jobs, checks=checks, checks_status="FAIL" if failed else "PASS" if complete else "NOT_RUN",
                 state="CHECKS_FAILED" if failed else "CHECKS_COMPLETE" if complete else "CHECKS_PENDING",
                 affected=patch["affected"], preserved=patch["preserved"], budget=patch["budget"], **flags())
    return {**value, "outcome_fingerprint": fingerprint(value)}


@graph.controlled
def inspect(store, user, pid, aid, key, limits):
    with store.tx() as c:
        patch = load(store, c, user, pid, aid, key, limits)
        if not graph.lookup(c, user, aid, START, key):
            return {**patch, "cached": True}
        value = outcome(store, c, user, pid, aid, key, limits)
        if graph.lookup(c, user, aid, FINISH, key):
            body, saved = columns.read_pair(c, user, aid, FINISH, key, Confirmation)
            if (body.expected_patch_fingerprint != patch["patch_fingerprint"]
                    or fingerprint(saved) != fingerprint(finished(value))):
                graph.conflict("Project patch final receipt or actual checks changed")
            return {**saved, "cached": True}
        return {**value, "cached": True}


def finished(value):
    body = {**value, "state": "CHECKED_PROJECT_CANDIDATE", "finite_revalidation_completed": True,
            "draft_patch_executed": True}
    return {**body, "receipt_fingerprint": fingerprint(body)}


@graph.controlled
def finalize(store, user, pid, aid, key, body, limits):
    with store.tx() as c:
        patch, confirmation, start_value = accepted(store, c, user, pid, aid, key, limits)
        if confirmation != body:
            graph.conflict("Finalization must use the original exact confirmation")
        value = outcome(store, c, user, pid, aid, key, limits)
        if graph.lookup(c, user, aid, FINISH, key):
            old, saved = columns.read_pair(c, user, aid, FINISH, key, Confirmation)
            if old != body or fingerprint(saved) != fingerprint(finished(value)):
                graph.conflict("Project final receipt changed")
            return {**saved, "cached": True}
        if value["checks_status"] != "PASS":
            raise DomainError("VERIFICATION_FAILED", "All affected actual worker jobs and independent checks must pass; no project patch committed")
        deadline = min(j["deadline"] for j in start_value["jobs"])
        if time.time() >= deadline:
            raise DomainError("BUDGET_EXHAUSTED", "Project confirmation expired; late results cannot commit")
        answer = finished(value)
        save_pair(c, user, aid, FINISH, key, body, answer)
        load(store, c, user, pid, aid, key, limits)
        if time.time() >= deadline:
            raise DomainError("BUDGET_EXHAUSTED", "Project budget expired before commit")
        return {**answer, "cached": False}


def mount(app, store, identity, limits, settings):
    base = "/api/projects/{pid}/apps/{aid}/project-column-patches"
    dependency = Depends(identity)

    def effective():
        return Limits(**{k: getattr(settings, k) for k in Limits.model_fields})

    def offline():
        if settings.mode != "mock" or settings.live_enabled:
            raise DomainError("PERMISSION_DENIED", "Offline deterministic project checks only")

    @app.post(base, status_code=201)
    def preview(pid: str, aid: str, body: Proposal, user=dependency):
        offline()
        return propose(store, user, pid, aid, body, effective())

    @app.get(base + "/{key}")
    def read(pid: str, aid: str, key: str, user=dependency):
        return inspect(store, user, pid, aid, key, effective())

    @app.get(base + "/{key}/definition")
    def definition(pid: str, aid: str, key: str, user=dependency):
        with store.tx() as c:
            return load(store, c, user, pid, aid, key, effective())

    @app.post(base + "/{key}/runs", status_code=202)
    def run(pid: str, aid: str, key: str, body: Confirmation, user=dependency):
        offline()
        return start(store, user, pid, aid, key, body, effective())

    @app.post(base + "/{key}/finalize", status_code=201)
    def commit(pid: str, aid: str, key: str, body: Confirmation, user=dependency):
        offline()
        return finalize(store, user, pid, aid, key, body, effective())
