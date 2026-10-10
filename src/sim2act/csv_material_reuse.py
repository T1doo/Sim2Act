"""Reuse a verified closed CSV recipe on another existing authorized CSV draft.

Only a new ordinary DAG plan is written. Execution, release and instance creation
remain separate confirmations on the existing worker/lifecycle paths.
"""

import copy

from pydantic import Field
from sqlalchemy import select

from . import csv_dag as dag
from . import csv_dag_instances as instances
from . import delivery_graph_apps as graph
from . import lifecycle
from .column_patches import KeyInput, read_pair, require_capacity
from .contracts import Limits
from .db import app_drafts, delivery_graph_requests, fingerprint, internal_releases
from .errors import DomainError
from .tools import csv_column_options

KIND = "csv_dag_material_plan"
VERSION = "internal.csv-material-reuse.v1"
PREFIX = "material-plan-"


class MaterialInput(KeyInput):
    expected_release_fingerprint: str = Field(pattern=graph.HASH)
    target_app_id: str = Field(pattern=r"^app_[a-f0-9]{32}$")
    expected_candidate_fingerprint: str = Field(pattern=graph.HASH)
    expected_graph_fingerprint: str = Field(pattern=graph.HASH)
    expected_resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    expected_source_hash: str = Field(pattern=graph.HASH)
    column: str = Field(min_length=1, max_length=200)
    request_key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")


def plan_key(rid, body):
    # The intent belongs to the source version, even if a retry changes target.
    return PREFIX + fingerprint([rid, body.request_key])[:48]


def read_origin(c, user, aid, key):
    rows = [graph.lookup(c, user, aid, kind, key) for kind in (KIND, KIND + "_seal")]
    instances.require(all(rows), "Missing immutable material receipt")
    value, seal = [graph.checked(row) for row in rows]
    instances.require(
        set(value) == {"request", "response"} and fingerprint(value) == fingerprint(seal)
    )
    body = MaterialInput.model_validate(value["request"])
    binding = value["response"]
    instances.require(
        all(row["request_fingerprint"] == fingerprint(body.model_dump()) for row in rows)
        and binding["request_key"] == body.request_key
        and plan_key(binding["source_release_id"], body) == key
    )
    return body, binding


def recipe(store, c, user, rid, limits):
    row = (
        c.execute(
            select(internal_releases).where(
                internal_releases.c.id == rid, internal_releases.c.principal_id == user
            )
        )
        .mappings()
        .first()
    )
    if row is None:
        raise DomainError("PERMISSION_DENIED")
    store.lock_project(c, user, row["project_id"])
    execution = row["snapshot"].get("execution_source", {})
    instances.require(execution.get("version") in instances.VERSIONS)
    # One material transfer, not a recursive chain of source-release interpreters.
    if execution["plan_key"].startswith((PREFIX, "logic-plan-", "logic-instance-plan-")):
        raise DomainError(
            "UNSUPPORTED_CAPABILITY", "Select the original completed CSV flow version"
        )
    rel = lifecycle.read_release(store, c, user, rid, limits)
    s = rel["snapshot"]
    source, plan = read_pair(
        c, user, s["draft"]["id"], "csv_dag_plan", execution["plan_key"], dag.PlanInput
    )
    instances.closed(plan)
    instances.require("material_reuse" not in plan and source.composition is not None)
    cap = Limits(**execution["limits"])
    if any(getattr(limits, k) < getattr(cap, k) for k in Limits.model_fields):
        raise DomainError(
            "BUDGET_EXHAUSTED", "Current budget is below the source's frozen envelope"
        )
    return rel, copy.deepcopy(source.composition.model_dump(exclude_none=True)), cap


def target(store, c, user, rel, aid, cap):
    return target_for_schema(store, c, user, rel["project_id"], aid, cap,
        rel["snapshot"]["data_schema"], excluded_id=rel["snapshot"]["draft"]["candidate"]["manifest"]["data_bindings"][0]["resource_ref"],
        excluded_hash=rel["snapshot"]["execution_source"]["source_hash"])


def target_for_schema(store, c, user, pid, aid, cap, schema, *, excluded_id=None, excluded_hash=None):
    # Reject original-resource aliases before any family/resource loading. This
    # metadata projection never loads the candidate goal, columns or source hash.
    meta = c.execute(select(app_drafts.c.project_id,
        app_drafts.c.candidate["manifest"]["data_bindings"].label("bindings"),
        app_drafts.c.candidate["actions"][0]["executor"].label("executor"))
        .where(app_drafts.c.id == aid)).mappings().first()
    if meta is None or meta["project_id"] != pid:
        raise DomainError("PERMISSION_DENIED")
    bindings, executor = meta["bindings"], meta["executor"]
    if (not isinstance(bindings, list) or len(bindings) != 1 or not isinstance(bindings[0], dict) or not isinstance(executor, dict)
            or executor.get("kind") != "registered_tool" or executor.get("ref") != "data.aggregate_csv"):
        raise DomainError("UNSUPPORTED_CAPABILITY", "Target must be a registered CSV draft")
    if bindings[0].get("resource_ref") == excluded_id:
        raise DomainError("INVALID_INPUT", "Original resource is outside the data-free target path")
    saved = graph.current(store, c, user, pid, aid, cap)
    draft, manifest, action, _, rows, _ = graph.load_family(store, c, user, pid, aid, cap)
    if action.executor.kind != "registered_tool" or action.executor.ref != "data.aggregate_csv":
        raise DomainError(
            "UNSUPPORTED_CAPABILITY", "Target must be an existing registered CSV draft"
        )
    rid = manifest.data_bindings[0].resource_ref
    instances.require(len(rows) == 1 and rows[0]["id"] == rid)
    raw = dag.authorized_read(
        store, c, user, draft["runtime_id"], pid, "resource.read", {"resource_id": rid}
    )
    store.authorize(c, user, draft["runtime_id"], pid, rid, "data.aggregate_csv")
    guide = csv_column_options(raw["content"])
    columns = [v["name"] for v in guide["columns"] if v["numeric"]]
    if raw["format"] != "csv" or guide["error"] or not columns:
        raise DomainError("INVALID_INPUT", "New CSV requires unique finite numeric columns")
    if rid == excluded_id or excluded_hash is not None and raw["hash"] == excluded_hash:
        raise DomainError("INVALID_INPUT", "Choose another CSV with different bytes")
    instances.require(
        fingerprint(lifecycle.record_schema(draft["candidate"]))
        == fingerprint(schema)
    )
    return dict(
        target_app_id=aid,
        project_id=pid,
        runtime_id=draft["runtime_id"],
        candidate_fingerprint=draft["fingerprint"],
        graph_fingerprint=saved["graph"]["graph_fingerprint"],
        graph_revision=saved["graph_revision"],
        authorization_fingerprint=saved["authorization_fingerprint"],
        resource_id=rid,
        source_hash=raw["hash"],
        columns=columns,
        name=rows[0]["name"],
    )


def definition(store, c, user, rid, body, limits, key):
    rel, composition, cap = recipe(store, c, user, rid, limits)
    instances.require(rel["fingerprint"] == body.expected_release_fingerprint)
    t = target(store, c, user, rel, body.target_app_id, cap)
    instances.require(
        t["candidate_fingerprint"] == body.expected_candidate_fingerprint
        and t["graph_fingerprint"] == body.expected_graph_fingerprint
        and t["resource_id"] == body.expected_resource_id
        and t["source_hash"] == body.expected_source_hash
    )
    if body.column not in t["columns"]:
        raise DomainError("INVALID_INPUT", "Choose a numeric column of the new CSV")
    composition["nodes"][1]["column"] = body.column
    plan_body = dag.PlanInput(
        expected_candidate_fingerprint=t["candidate_fingerprint"],
        expected_graph_fingerprint=t["graph_fingerprint"],
        column=body.column,
        composition=composition,
        request_key=key,
    )
    binding = dict(
        version=VERSION,
        source_release_id=rid,
        source_release_fingerprint=rel["fingerprint"],
        source_execution=copy.deepcopy(rel["snapshot"]["execution_source"]),
        target=t,
        column=body.column,
        limits=cap.model_dump(),
        plan_input=plan_body.model_dump(exclude_none=True),
        principal_id=user,
        request_key=body.request_key,
        model_requests=0,
        semantic_status="UNKNOWN",
        owner_acceptance="PENDING",
        formal_publication_enabled=False,
    )
    return binding, plan_body, cap


def plan_origin(store, c, user, pid, aid, body, limits):
    rows = [graph.lookup(c, user, aid, kind, body.request_key) for kind in (KIND, KIND + "_seal")]
    prior = graph.lookup(c, user, aid, "csv_dag_plan", body.request_key)
    marked = prior is not None and "material_reuse" in graph.checked(prior).get("response", {})
    if not any(rows) and not marked and not body.request_key.startswith(PREFIX):
        return None
    intent, old = read_origin(c, user, aid, body.request_key)
    binding, expected, cap = definition(
        store, c, user, old["source_release_id"], intent, limits, body.request_key
    )
    instances.require(
        pid == binding["target"]["project_id"]
        and aid == intent.target_app_id
        and fingerprint(old) == fingerprint(binding)
        and fingerprint(body.model_dump(exclude_none=True))
        == fingerprint(expected.model_dump(exclude_none=True))
    )
    return binding, cap


@graph.controlled
def propose(store, user, rid, body, limits):
    with store.tx() as c:
        key = plan_key(rid, body)
        binding, plan_body, cap = definition(store, c, user, rid, body, limits, key)
        aid, pid = body.target_app_id, binding["target"]["project_id"]
        # Validate compiler budgets, manual locks and dependencies before binding writes.
        dag.build(
            store,
            c,
            user,
            pid,
            aid,
            plan_body.model_copy(
                update={"request_key": "material-preflight-" + key[len(PREFIX) :]}
            ),
            cap,
        )
        rows = (
            c.execute(
                select(delivery_graph_requests).where(
                    delivery_graph_requests.c.principal_id == user,
                    delivery_graph_requests.c.kind.in_([KIND, KIND + "_seal"]),
                    delivery_graph_requests.c.request_key == key,
                )
            )
            .mappings()
            .all()
        )
        instances.require(
            not rows or len(rows) == 2 and all(row["app_id"] == aid for row in rows),
            "Same key changed its complete material request",
        )
        old = bool(rows)
        if old:
            prior, saved = read_origin(c, user, aid, key)
            instances.require(
                prior == body and fingerprint(saved) == fingerprint(binding),
                "Same key changed its complete material request",
            )
        else:
            require_capacity(c, user, aid, KIND)
            for kind in (KIND, KIND + "_seal"):
                graph.remember(c, user, aid, kind, key, body, binding)
        plan = dag.propose_tx(store, c, user, pid, aid, plan_body, cap)
        return dict(
            namespace=VERSION,
            source_release_id=rid,
            binding=binding,
            binding_fingerprint=fingerprint(binding),
            plan=plan,
            cached=bool(old),
            model_requests=0,
            formal_publication_enabled=False,
        )


@graph.controlled
def inspect(store, user, rid, aid, key, limits):
    with store.tx() as c:
        intent, value = read_origin(c, user, aid, key)
        instances.require(value["source_release_id"] == rid and aid == intent.target_app_id)
        binding, plan_body, cap = definition(store, c, user, rid, intent, limits, key)
        instances.require(fingerprint(binding) == fingerprint(value))
        plan = dag.load_plan(store, c, user, binding["target"]["project_id"], aid, key, cap)
        return dict(
            namespace=VERSION,
            source_release_id=rid,
            binding=binding,
            binding_fingerprint=fingerprint(binding),
            plan=plan,
            model_requests=0,
            formal_publication_enabled=False,
        )


@graph.controlled
def options(store, user, rid, limits):
    with store.tx() as c:
        rel, _, cap = recipe(store, c, user, rid, limits)
        ids = (
            c.execute(select(app_drafts.c.id).where(app_drafts.c.project_id == rel["project_id"]))
            .scalars()
            .all()
        )
        items = []
        for aid in ids:
            try:
                items.append(target(store, c, user, rel, aid, cap))
            except DomainError:
                continue
        return dict(
            namespace=VERSION,
            source_release_id=rid,
            source_release_fingerprint=rel["fingerprint"],
            items=items,
            limits=cap.model_dump(),
            model_requests=0,
            formal_publication_enabled=False,
        )
