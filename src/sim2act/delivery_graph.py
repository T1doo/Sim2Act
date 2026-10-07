"""V5 §9 pure DeliveryGraph derivation and conservative change planning.

All IDs, versions, locks, observations and authority are supplied by the trusted
server adapter. Never accept context/stable_ids/source_versions from an HTTP
body. A graph hash proves integrity only when compared with the adapter's saved
anchor. Neither API performs writes, dispatches tools or grants authority.
"""

import copy
import hashlib
import json
from typing import Literal

from pydantic import Field, ValidationError

from .contracts import ID, Limits, Strict, strict_json
from .errors import DomainError
from .preflight import preflight

VERSION = "delivery-graph.v1"
MAX_NODES = 128
MAX_EDGES = 512
MAX_BYTES = 262144
HASH = r"^[a-f0-9]{64}$"
KEY = r"^[A-Za-z0-9_.:-]{1,160}$"
NodeKind = Literal[
    "GOAL", "REQUIREMENT", "SOURCE", "ARTIFACT", "ACTION", "VIEW", "CHECK", "MANIFEST", "RELEASE"
]
EdgeKind = Literal["DATA", "RULE", "PRESENTATION", "SEMANTIC", "VERIFIED_BY", "PACKAGED_IN"]
Provenance = Literal["DECLARED", "ACTUAL_READ", "HUMAN_CONFIRMED", "MODEL_CANDIDATE"]


class SourceVersion(Strict):
    revision: int = Field(ge=1)
    content_fingerprint: str = Field(pattern=HASH)


class Edge(Strict):
    upstream: str = Field(pattern=ID)
    downstream: str = Field(pattern=ID)
    type: EdgeKind
    provenance: Provenance


class UnknownDependency(Strict):
    node_id: str = Field(pattern=ID)
    scope: Literal["APP", "PROJECT"]
    reason: str = Field(min_length=1, max_length=400)


class Context(Strict):
    project_id: str = Field(pattern=r"^proj_[a-f0-9]{32}$")
    app_id: str = Field(pattern=r"^app_[a-f0-9]{32}$")
    authorization_revision: int = Field(ge=1)
    authorized: bool
    resource_ids: list[str] = Field(max_length=128)
    node_revisions: dict[str, int] = Field(max_length=128)
    locked_nodes: list[str] = Field(max_length=128)
    source_versions: dict[str, SourceVersion] = Field(max_length=128)
    dependency_edges: list[Edge] = Field(default_factory=list, max_length=512)
    unknown_dependencies: list[UnknownDependency] = Field(default_factory=list, max_length=128)
    graph_fingerprint: str | None = Field(default=None, pattern=HASH)


class Node(Strict):
    id: str = Field(pattern=ID)
    key: str = Field(pattern=KEY)
    kind: NodeKind
    project_id: str = Field(pattern=r"^proj_[a-f0-9]{32}$")
    app_id: str = Field(pattern=r"^app_[a-f0-9]{32}$")
    revision: int = Field(ge=1)
    locked: bool
    definition: dict
    content_fingerprint: str = Field(pattern=HASH)


class Graph(Strict):
    schema_version: Literal["delivery-graph.v1"]
    project_id: str = Field(pattern=r"^proj_[a-f0-9]{32}$")
    app_id: str = Field(pattern=r"^app_[a-f0-9]{32}$")
    authorization_revision: int = Field(ge=1)
    context_fingerprint: str = Field(pattern=HASH)
    resource_ids: list[str] = Field(max_length=128)
    nodes: list[Node] = Field(min_length=1, max_length=128)
    edges: list[Edge] = Field(max_length=512)
    unknown_dependencies: list[UnknownDependency] = Field(max_length=128)
    graph_fingerprint: str = Field(pattern=HASH)


class Change(Strict):
    node_id: str = Field(pattern=ID)
    expected_revision: int = Field(ge=1)
    expected_content_fingerprint: str = Field(pattern=HASH)


class ChangeRequest(Strict):
    request_key: str = Field(min_length=1, max_length=128)
    project_id: str = Field(pattern=r"^proj_[a-f0-9]{32}$")
    app_id: str = Field(pattern=r"^app_[a-f0-9]{32}$")
    changes: list[Change] = Field(min_length=1, max_length=128)


def _json(value):
    try:
        raw = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        return strict_json(raw, max_bytes=MAX_BYTES)
    except (ValueError, TypeError, RecursionError, DomainError):
        raise DomainError("INVALID_MANIFEST", "Closed finite JSON required") from None


def _hash(value):
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def _parse(model, value):
    try:
        return model.model_validate(_json(value))
    except ValidationError:
        raise DomainError("INVALID_MANIFEST", "DeliveryGraph failed strict validation") from None


def _context(value):
    context = _parse(Context, value)
    if any(type(rev) is not int or rev < 1 for rev in context.node_revisions.values()):
        raise DomainError("INVALID_MANIFEST", "Strict positive node revisions required")
    for items in (context.resource_ids, context.locked_nodes):
        if len(set(items)) != len(items):
            raise DomainError("INVALID_MANIFEST", "Duplicate context identity")
    if any(
        not isinstance(r, str)
        or not r.startswith("res_")
        or len(r) != 36
        or any(c not in "0123456789abcdef" for c in r[4:])
        for r in context.resource_ids
    ):
        raise DomainError("INVALID_MANIFEST", "Invalid context resource identity")
    if not context.authorized:
        raise DomainError("PERMISSION_DENIED", "Current server authority required")
    return context


def _context_hash(context):
    body = context.model_dump(exclude={"graph_fingerprint"})
    body["resource_ids"] = sorted(body["resource_ids"])
    body["locked_nodes"] = sorted(body["locked_nodes"])
    body["dependency_edges"] = sorted(body["dependency_edges"], key=_hash)
    body["unknown_dependencies"] = sorted(body["unknown_dependencies"], key=_hash)
    return _hash(body)


def _topology(nodes, edges):
    ids = {n.id for n in nodes}
    if len(ids) != len(nodes) or len({n.key for n in nodes}) != len(nodes):
        raise DomainError("INVALID_MANIFEST", "Duplicate node identity/key")
    edge_ids = [(e.upstream, e.downstream, e.type, e.provenance) for e in edges]
    if len(set(edge_ids)) != len(edges):
        raise DomainError("INVALID_MANIFEST", "Duplicate dependency evidence")
    parents: dict[str, set[str]] = {nid: set() for nid in ids}
    for edge in edges:
        if edge.upstream not in ids or edge.downstream not in ids:
            raise DomainError("INVALID_MANIFEST", "Dangling dependency")
        parents[edge.downstream].add(edge.upstream)
    order: list[str] = []
    while len(order) < len(nodes):
        ready = sorted(nid for nid in ids - set(order) if parents[nid] <= set(order))
        if not ready:
            raise DomainError("INVALID_MANIFEST", "Dependency cycle")
        order.extend(ready)
    return order


def _node_hash(node, edges, sealed):
    incoming = sorted(
        [
            {
                **e.model_dump(),
                "revision": sealed[e.upstream].revision,
                "content_fingerprint": sealed[e.upstream].content_fingerprint,
            }
            for e in edges
            if e.downstream == node.id
        ],
        key=_hash,
    )
    return _hash(
        {**node.model_dump(exclude={"content_fingerprint"}), "upstream_versions": incoming}
    )


def _validate_graph(value):
    graph = _parse(Graph, value)
    if graph.graph_fingerprint != _hash(graph.model_dump(exclude={"graph_fingerprint"})):
        raise DomainError("VERSION_CONFLICT", "Graph fingerprint changed")
    nodes = {n.id: n for n in graph.nodes}
    order = _topology(graph.nodes, graph.edges)
    if any(n.project_id != graph.project_id or n.app_id != graph.app_id for n in graph.nodes):
        raise DomainError("PERMISSION_DENIED", "Cross-project/app graph node")
    sealed: dict[str, Node] = {}
    for nid in order:
        node = nodes[nid]
        if node.content_fingerprint != _node_hash(node, graph.edges, sealed):
            raise DomainError("VERSION_CONFLICT", "Node fingerprint changed")
        sealed[nid] = node
    unknown_ids = [(u.node_id, u.scope) for u in graph.unknown_dependencies]
    if len(set(unknown_ids)) != len(unknown_ids) or any(
        u.node_id not in nodes for u in graph.unknown_dependencies
    ):
        raise DomainError("INVALID_MANIFEST", "Invalid uncertain dependency scope")
    return graph


def derive_manifest_graph(manifest, actions, source_versions, stable_ids, context, platform_limits):
    """Derive an application graph from strict AppManifest/ActionSpec definitions.

    Logical keys: goal:<goal_ref>, source:<resource_id>, rule:<kind>:<ref>,
    action:<step_id>, artifact:<output_field>, view:<component>:<output_field>,
    check:<check_ref>, manifest:<app_id>. External keys (goal/source/rule/check)
    require source_versions; all keys require context.node_revisions/stable_ids.
    No synthetic Release or actual-read evidence is inferred from declarations.
    """
    manifest, actions = _json(manifest), _json(actions)
    if (
        not isinstance(manifest, dict)
        or not isinstance(actions, list)
        or not actions
        or any(not isinstance(a, dict) for a in actions)
    ):
        raise DomainError("INVALID_MANIFEST", "Manifest object and nonempty action array required")
    ctx = _context(context)
    if manifest.get("app_id") != ctx.app_id:
        raise DomainError("PERMISSION_DENIED", "Manifest belongs to another application")
    limits = _parse(
        Limits,
        platform_limits.model_dump() if isinstance(platform_limits, Limits) else platform_limits,
    )
    m, report = preflight(json.dumps(manifest), actions, limits)
    versions = _json(source_versions)
    if versions != {k: v.model_dump() for k, v in ctx.source_versions.items()}:
        raise DomainError("VERSION_CONFLICT", "Source versions differ from trusted context")
    ids = _json(stable_ids)
    if not isinstance(ids, dict):
        raise DomainError("INVALID_MANIFEST", "Stable IDs must be a server mapping")
    resources = sorted(
        set(report["resource_refs"]) | {d.ref for d in m.dependency_lock if d.kind == "resource"}
    )
    if not set(resources) <= set(ctx.resource_ids):
        raise DomainError("PERMISSION_DENIED", "Current resource authority missing")
    definitions = {}
    external = set()

    def add(key, kind, definition, revision=None):
        if key in definitions:
            raise DomainError("INVALID_MANIFEST", "Duplicate logical node")
        if revision is None:
            external.add(key)
            saved = ctx.source_versions.get(key)
            if saved is None:
                raise DomainError("VERSION_CONFLICT", "Missing external version snapshot")
            revision = saved.revision
            definition = {**definition, "source_version": saved.model_dump()}
        if ctx.node_revisions.get(key) != revision:
            raise DomainError("VERSION_CONFLICT", "Node revision differs from trusted context")
        definitions[key] = (kind, definition, revision)
        return key

    goal = add("goal:" + m.goal_ref, "GOAL", {"goal_ref": m.goal_ref})
    for rid in resources:
        add("source:" + rid, "SOURCE", {"resource_ref": rid})
    for dep in m.dependency_lock:
        if dep.kind in {"tool", "prompt", "check"}:
            add("rule:" + dep.kind + ":" + dep.ref, "REQUIREMENT", dep.model_dump())
    checks = sorted(
        {m.validation_suite_ref}
        | {d.ref for d in m.dependency_lock if d.kind == "check"}
        | {ref for a in actions for ref in a["postcheck_refs"]}
    )
    if not set(checks) <= {d.ref for d in m.dependency_lock if d.kind == "check"}:
        raise DomainError("INVALID_MANIFEST", "Every checker needs an explicit version lock")
    for ref in checks:
        add("check:" + ref, "CHECK", {"check_ref": ref})
    bindings = {b.binding_id: (b.action_id, b.revision) for b in m.action_bindings}
    action_map = {(a["action_id"], a["revision"]): a for a in actions}
    step_keys = {}
    for step in m.workflow:
        action = action_map[bindings[step.binding_id]]
        step_keys[step.step_id] = add(
            "action:" + step.step_id,
            "ACTION",
            {"action": action, "step": step.model_dump()},
            action["revision"],
        )
    for field, binding in m.outputs.items():
        add(
            "artifact:" + field,
            "ARTIFACT",
            {
                "field": field,
                "binding": binding.model_dump(),
                "schema": m.output_schema["properties"][field],
            },
            m.revision,
        )
    for view in m.views:
        if view.output_field not in m.outputs:
            raise DomainError("INVALID_MANIFEST", "View output must have a declared producer")
        add(
            "view:" + view.component_ref + ":" + view.output_field,
            "VIEW",
            view.model_dump(),
            m.revision,
        )
    packaged = add("manifest:" + m.app_id, "MANIFEST", m.model_dump(), m.revision)
    if (
        set(versions) != external
        or set(ids) != set(definitions)
        or set(ctx.node_revisions) != set(definitions)
    ):
        raise DomainError(
            "INVALID_MANIFEST", "Exact logical node and external-version mappings required"
        )
    if len(definitions) > MAX_NODES:
        raise DomainError("INVALID_MANIFEST", "DeliveryGraph node limit exceeded")
    if any(not isinstance(nid, str) for nid in ids.values()) or len(set(ids.values())) != len(ids):
        raise DomainError("INVALID_MANIFEST", "Duplicate/invalid stable identity")
    if not set(ctx.locked_nodes) <= set(ids.values()):
        raise DomainError("INVALID_MANIFEST", "Lock references an unknown node")
    edges = []

    def edge(upstream, downstream, kind):
        edges.append(
            {
                "upstream": ids[upstream],
                "downstream": ids[downstream],
                "type": kind,
                "provenance": "DECLARED",
            }
        )

    for ref in checks:
        edge("rule:check:" + ref, "check:" + ref, "RULE")
    data = {d.binding_id: "source:" + d.resource_ref for d in m.data_bindings}
    for step in m.workflow:
        key = step_keys[step.step_id]
        action = action_map[bindings[step.binding_id]]
        edge(goal, key, "RULE")
        for predecessor in step.depends_on:
            edge(step_keys[predecessor], key, "DATA")
        upstream_data = {data[b.ref] for b in step.inputs.values() if b.source == "data"}
        upstream_data.update(
            "source:" + d["ref"] for d in action["dependencies"] if d["kind"] == "resource"
        )
        upstream_data.update(
            "source:" + p["resource_ref"]
            for p in action["permission_requirements"]
            if p["resource_ref"].startswith("res_")
        )
        for parent in sorted(upstream_data):
            edge(parent, key, "DATA")
        rule_refs = {
            (d["kind"], d["ref"])
            for d in action["dependencies"]
            if d["kind"] in {"tool", "prompt", "check"}
        }
        if action["executor"]["kind"] == "registered_tool":
            rule_refs.add(("tool", action["executor"]["ref"]))
        else:
            rule_refs.add(("prompt", "intern.system.v1"))
        rule_refs.update(("tool", t) for t in action["allowed_tool_refs"])
        for kind, ref in sorted(rule_refs):
            edge("rule:" + kind + ":" + ref, key, "RULE")
        for ref in sorted(action["postcheck_refs"]):
            edge(key, "check:" + ref, "VERIFIED_BY")
    for field, binding in m.outputs.items():
        key = "artifact:" + field
        if binding.source == "step":
            edge(step_keys[binding.ref], key, "DATA")
        elif binding.source == "data":
            edge(data[binding.ref], key, "DATA")
        else:
            edge(goal, key, "RULE")
        edge(key, "check:" + m.validation_suite_ref, "VERIFIED_BY")
    for view in m.views:
        view_key = "view:" + view.component_ref + ":" + view.output_field
        edge("artifact:" + view.output_field, view_key, "PRESENTATION")
        edge(view_key, "check:" + m.validation_suite_ref, "VERIFIED_BY")
    for key in sorted(definitions):
        if key != packaged:
            edge(key, packaged, "PACKAGED_IN")
    edges.extend(e.model_dump() for e in ctx.dependency_edges)
    if len(edges) > MAX_EDGES:
        raise DomainError("INVALID_MANIFEST", "DeliveryGraph edge limit exceeded")
    nodes = [
        _parse(
            Node,
            {
                "id": ids[key],
                "key": key,
                "kind": kind,
                "definition": definition,
                "revision": revision,
                "locked": ids[key] in ctx.locked_nodes,
                "project_id": ctx.project_id,
                "app_id": ctx.app_id,
                "content_fingerprint": "0" * 64,
            },
        )
        for key, (kind, definition, revision) in sorted(definitions.items())
    ]
    parsed_edges = [_parse(Edge, e) for e in sorted(edges, key=_hash)]
    order = _topology(nodes, parsed_edges)
    by_id = {n.id: n for n in nodes}
    sealed: dict[str, Node] = {}
    for nid in order:
        node = by_id[nid]
        node.content_fingerprint = _node_hash(node, parsed_edges, sealed)
        sealed[nid] = node
    body = {
        "schema_version": VERSION,
        "project_id": ctx.project_id,
        "app_id": ctx.app_id,
        "authorization_revision": ctx.authorization_revision,
        "context_fingerprint": _context_hash(ctx),
        "resource_ids": resources,
        "nodes": [n.model_dump() for n in nodes],
        "edges": [e.model_dump() for e in parsed_edges],
        "unknown_dependencies": sorted(
            [u.model_dump() for u in ctx.unknown_dependencies], key=_hash
        ),
    }
    return _validate_graph({**body, "graph_fingerprint": _hash(body)}).model_dump()


def plan_change(
    graph, expected_graph_fingerprint, change_request, current_context, previous_receipt=None
):
    """Plan only; replay compares a fresh authorized plan with the stored receipt.

    The adapter must persist the graph anchor and request-key ledger, serialize
    competing requests, and rerun checks before later patching/publication. This
    pure function cannot detect a reused key unless its prior receipt is supplied.
    """
    ctx = _context(current_context)
    request = _parse(ChangeRequest, change_request)
    if request.project_id != ctx.project_id or request.app_id != ctx.app_id:
        raise DomainError("PERMISSION_DENIED", "Cross-project/app change request")
    g = _validate_graph(graph)
    if (
        g.project_id != ctx.project_id
        or g.app_id != ctx.app_id
        or not set(g.resource_ids) <= set(ctx.resource_ids)
    ):
        raise DomainError("PERMISSION_DENIED", "Current graph authority missing")
    if ctx.authorization_revision != g.authorization_revision:
        raise DomainError("PERMISSION_DENIED", "Authorization snapshot changed; derive a new graph")
    if (
        ctx.graph_fingerprint is None
        or g.graph_fingerprint != ctx.graph_fingerprint
        or expected_graph_fingerprint != g.graph_fingerprint
    ):
        raise DomainError("VERSION_CONFLICT", "Trusted saved graph anchor required")
    if _context_hash(ctx) != g.context_fingerprint:
        raise DomainError("VERSION_CONFLICT", "Trusted node/version/dependency snapshot changed")
    nodes = {n.id: n for n in g.nodes}
    changed = set()
    for change in request.changes:
        if change.node_id in changed:
            raise DomainError("INVALID_MANIFEST", "Duplicate changed node")
        changed.add(change.node_id)
        node = nodes.get(change.node_id)
        if (
            node is None
            or change.expected_revision != node.revision
            or change.expected_content_fingerprint != node.content_fingerprint
        ):
            raise DomainError("VERSION_CONFLICT", "Changed node is missing or stale")
    request_body = request.model_dump()
    request_body["changes"] = sorted(request_body["changes"], key=lambda c: c["node_id"])
    request_fp = _hash(request_body)
    if previous_receipt is not None:
        previous_receipt = _json(previous_receipt)
        if (
            not isinstance(previous_receipt, dict)
            or previous_receipt.get("request_key") != request.request_key
            or previous_receipt.get("request_fingerprint") != request_fp
        ):
            raise DomainError("VERSION_CONFLICT", "Prior request key/parameters conflict")
    definite = set(changed)
    uncertain: set[str] = set()
    pending = [(nid, False) for nid in sorted(changed)]
    visited = set()
    while pending:
        nid, unknown = pending.pop()
        if (nid, unknown) in visited:
            continue
        visited.add((nid, unknown))
        (uncertain if unknown else definite).add(nid)
        for edge in g.edges:
            if edge.upstream == nid:
                pending.append(
                    (
                        edge.downstream,
                        unknown or edge.type == "SEMANTIC" or edge.provenance == "MODEL_CANDIDATE",
                    )
                )
    # Unknown access may include the changed material even when no declared edge
    # connects it. Recheck the full application (or all project apps via adapter).
    scope = "NODES"
    if g.unknown_dependencies or any(nodes[nid].kind in {"MANIFEST", "RELEASE"} for nid in changed):
        scope = "PROJECT" if any(u.scope == "PROJECT" for u in g.unknown_dependencies) else "APP"
        uncertain.update(set(nodes) - changed)
    uncertain -= changed
    definite -= uncertain
    affected = definite | uncertain
    if any(nodes[nid].locked for nid in affected):
        raise DomainError("LOCK_CONFLICT", "Affected manually locked object; no changes performed")
    retained = [n.model_dump() for n in g.nodes if n.id not in affected]
    receipt = {
        "schema_version": "delivery-change-plan.v1",
        "graph_fingerprint": g.graph_fingerprint,
        "context_fingerprint": g.context_fingerprint,
        "request_key": request.request_key,
        "request_fingerprint": request_fp,
        "changed_nodes": sorted(changed),
        "definite_impact": sorted(definite),
        "uncertain_impact": sorted(uncertain),
        "revalidation_nodes": sorted(affected),
        "revalidation_scope": scope,
        "project_id": g.project_id,
        "app_id": g.app_id,
        "revalidation_checks": sorted(nid for nid in affected if nodes[nid].kind == "CHECK"),
        "invalidated_packages": sorted(
            nid for nid in affected if nodes[nid].kind in {"MANIFEST", "RELEASE"}
        ),
        "retained_objects": retained,
        "global_invariants": [
            "current_authority",
            "current_versions",
            "strict_preflight",
            "dependency_completeness",
            "manual_locks",
        ],
        "patch_executed": False,
        "business_write_performed": False,
        "publishable": False,
    }
    receipt["plan_fingerprint"] = _hash(receipt)
    if previous_receipt is not None and previous_receipt != receipt:
        raise DomainError("VERSION_CONFLICT", "Prior receipt differs from current authorized plan")
    return copy.deepcopy(receipt)
