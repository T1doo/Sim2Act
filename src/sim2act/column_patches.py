"""V5 §9 CSV column-binding drafts on the existing graph/authority ledger.

No new identity, Grant, runtime, canonical release or executable language. The
definition freezes one schema-checked parameter on the same aggregate node.
"""

import copy
from typing import Literal

from fastapi import Depends
from pydantic import Field
from sqlalchemy import func, select

from . import delivery_graph as core
from . import delivery_graph_apps as graph
from .contracts import Strict, validate_action_input, validate_value
from .db import delivery_graph_requests as requests
from .db import fingerprint
from .errors import DomainError
from .tools import authorized_read, csv_column_options, validate_call

HISTORY_LIMIT = 50


def validate_request_key(key):
    """One SQL-before boundary for JSON, decoded path and restored ledger keys."""
    if (not isinstance(key, str) or not 1 <= len(key) <= 128
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in key)):
        raise DomainError("INVALID_INPUT", "Column patch request key must be bounded text without control characters")
    return key


class DefinitionInput(Strict):
    expected_candidate_fingerprint: str = Field(pattern=graph.HASH)
    expected_graph_fingerprint: str = Field(pattern=graph.HASH)
    request_key: str = Field(min_length=1, max_length=128)
    change: core.Change
    kind: Literal["csv.column-binding.v1"]
    baseline_column: str = Field(min_length=1, max_length=200)
    column: str = Field(min_length=1, max_length=200)


class CheckInput(Strict):
    expected_patch_fingerprint: str = Field(pattern=graph.HASH)
    request_key: str = Field(min_length=1, max_length=128)


def scope(store, c, user, pid, aid, body, limits):
    saved = graph.current(store, c, user, pid, aid, limits)
    draft, manifest, action, _, rows, _ = graph.load_family(store, c, user, pid, aid, limits)
    if action.executor.kind != "registered_tool" or action.executor.ref != "data.aggregate_csv":
        raise DomainError("UNSUPPORTED_CAPABILITY", "Only the fixed CSV sum template is supported")
    if saved["candidate_fingerprint"] != body.expected_candidate_fingerprint:
        graph.conflict("Column definition candidate baseline changed")
    node = next(n for n in saved["graph"]["nodes"] if n["key"] == "action:aggregate")
    if node["id"] != body.change.node_id:
        raise DomainError("UNSUPPORTED_CAPABILITY", "Change must select the existing sum node")
    plan = core.plan_change(
        saved["graph"], body.expected_graph_fingerprint,
        dict(project_id=pid, app_id=aid, request_key=body.request_key,
             changes=[body.change.model_dump()]), saved["context"],
    )
    # This executor cannot prove arbitrary/project-wide semantic dependencies.
    # Fail closed rather than perform target-only checks and claim completeness.
    if plan["revalidation_scope"] == "PROJECT" or any(
        e["provenance"] == "MODEL_CANDIDATE" or e["type"] == "SEMANTIC"
        for e in saved["graph"]["edges"]
    ):
        raise DomainError("UNSUPPORTED_CAPABILITY", "Unknown project/semantic dependency needs a broader executor")
    source = next(r for r in rows if r["id"] == manifest.data_bindings[0].resource_ref)
    guidance = csv_column_options(source["content"])
    columns = [v["name"] for v in guidance["columns"] if v["numeric"]]
    if guidance["error"] or body.column not in columns or body.baseline_column not in columns:
        raise DomainError("INVALID_INPUT", "Binding requires an explicit finite numeric CSV column schema")
    if body.column == body.baseline_column:
        raise DomainError("INVALID_INPUT", "A new binding must change the column")
    return saved, draft, manifest, action, source, columns, plan


def build(store, c, user, pid, aid, body, limits):
    saved, draft, manifest, _, source, columns, plan = scope(
        store, c, user, pid, aid, body, limits
    )
    binding = dict(kind=body.kind, node_id=body.change.node_id, field="column",
                   schema={"type": "string", "enum": columns}, value=body.column)
    definition = dict(candidate=copy.deepcopy(draft["candidate"]),
                      column_binding=binding, baseline_input={"column": body.baseline_column})
    patched = core.column_binding_patch(saved["graph"], body.change.node_id, binding)
    baseline_nodes = {n["id"]: n for n in saved["graph"]["nodes"]}
    modified: list[dict] = []
    preserved: list[dict] = []
    for n in patched["nodes"]:
        (preserved if fingerprint(n) == fingerprint(baseline_nodes[n["id"]]) else modified).append(n)
    result = dict(
        namespace="csv-column-patch.v1", project_id=pid, app_id=aid,
        runtime_id=draft["runtime_id"], request_key=body.request_key,
        candidate_fingerprint=draft["fingerprint"],
        baseline_graph_fingerprint=saved["graph"]["graph_fingerprint"],
        baseline_graph_revision=saved["graph_revision"],
        authorization_fingerprint=saved["authorization_fingerprint"],
        definition=definition, definition_fingerprint=fingerprint(definition),
        graph=patched, plan=plan, modified_objects=modified, preserved_objects=preserved,
        source_hash=source["hash"], state="DRAFT_PATCH", checks_status="NOT_RUN",
        semantic_status="UNKNOWN", owner_acceptance="PENDING", publishable=False,
        formal_publication_enabled=False, business_writes=0, model_requests=0,
        # Only draft definitions exist here; checks need separate exact-version confirmation.
        patch_executed=True,
    )
    result["patch_fingerprint"] = fingerprint(result)
    return result


def read_pair(c, user, aid, kind, key, model):
    validate_request_key(key)
    row = graph.lookup(c, user, aid, kind, key)
    seal = graph.lookup(c, user, aid, kind + "_seal", key)
    if not row or not seal:
        graph.conflict("Missing immutable column patch receipt")
    value = graph.checked(row)
    if fingerprint(value) != fingerprint(graph.checked(seal)) or set(value) != {"request", "response"}:
        graph.conflict("Independent column patch seal changed")
    body = model.model_validate(value["request"])
    if (body.request_key != key or row["request_fingerprint"] != fingerprint(body.model_dump())
            or seal["request_fingerprint"] != row["request_fingerprint"]):
        graph.conflict("Column patch accepted parameters changed")
    return body, value["response"]


def require_capacity(c, user, aid, kind):
    # Shared project lock serializes this count with accepted inserts. Refuse
    # extra definitions/checks before acceptance rather than hide their receipt
    # outside the bounded history/readback window. Old keys remain recoverable.
    count = c.execute(select(func.count()).select_from(requests).where(
        requests.c.app_id == aid, requests.c.principal_id == user,
        requests.c.kind == kind)).scalar_one()
    if count >= HISTORY_LIMIT:
        raise DomainError("INVALID_INPUT", "Offline engineering history capacity reached; old records are retained")


def load(store, c, user, pid, aid, key, limits):
    validate_request_key(key)
    # Current authority precedes reading protected saved definitions/results.
    saved = graph.current(store, c, user, pid, aid, limits)
    body, answer = read_pair(c, user, aid, "column_patch", key, DefinitionInput)
    if (body.expected_graph_fingerprint != saved["graph"]["graph_fingerprint"]
            or answer["baseline_graph_revision"] != saved["graph_revision"]):
        graph.conflict("Column patch baseline version expired")
    fresh = build(store, c, user, pid, aid, body, limits)
    if fingerprint(fresh) != fingerprint(answer):
        graph.conflict("Column patch baseline, definition or preservation proof changed")
    return body, answer


@graph.controlled
def propose(store, user, pid, aid, body, limits):
    validate_request_key(body.request_key)
    with store.tx() as c:
        answer = build(store, c, user, pid, aid, body, limits)
        if graph.lookup(c, user, aid, "column_patch", body.request_key):
            old, previous = load(store, c, user, pid, aid, body.request_key, limits)
            if fingerprint(old.model_dump()) != fingerprint(body.model_dump()):
                graph.conflict("Column definition request key changed")
            return {**previous, "cached": True}
        # Path keys may contain slashes/Unicode/percent signs and must be URL
        # encoded by callers. Reject new control/dot-segment keys before saving:
        # HTTP paths cannot reliably round-trip them. Persisted legacy models
        # remain unchanged so accepted addressable keys retain their receipts.
        if any(part in {".", ".."} for part in body.request_key.split("/")):
            raise DomainError("INVALID_INPUT", "Definition request key cannot contain controls or URL dot segments")
        require_capacity(c, user, aid, "column_patch")
        graph.remember(c, user, aid, "column_patch", body.request_key, body, answer)
        graph.remember(c, user, aid, "column_patch_seal", body.request_key, body, answer)
        return {**answer, "cached": False}


def execute(store, c, user, pid, aid, definition, patch, limits):
    saved, draft, manifest, action, source, _, plan = scope(
        store, c, user, pid, aid, definition, limits
    )

    outputs = {}
    for name, column in (("baseline", definition.baseline_column), ("patched", definition.column)):
        value_input = {"column": column}
        validate_value(manifest.input_schema, value_input)
        validate_value(patch["definition"]["column_binding"]["schema"], column)
        args = {"resource_id": source["id"], **value_input}
        validate_action_input(action, args)
        validate_call(action.executor.ref, args)
        value = authorized_read(store, c, user, draft["runtime_id"], pid, action.executor.ref, args)
        validate_value(action.output_schema, value, "action_output")
        output = {field: value[binding.field] for field, binding in manifest.outputs.items()}
        validate_value(manifest.output_schema, output, "output")
        if output["source_hash"] != patch["source_hash"] or output["column"] != column:
            graph.conflict("Actual CSV readback does not match the frozen definition")
        outputs[name] = output
    # Re-read current state before exposing results or saving the receipt. The
    # project transaction lock is shared with resource/grant/graph mutations.
    latest = graph.current(store, c, user, pid, aid, limits)
    if fingerprint(latest) != fingerprint(saved):
        graph.conflict("Authority or source changed during checks")
    return dict(
        namespace="csv-column-check.v1", project_id=pid, app_id=aid,
        patch_fingerprint=patch["patch_fingerprint"],
        definition_fingerprint=patch["definition_fingerprint"],
        graph_fingerprint=patch["graph"]["graph_fingerprint"],
        state="CHECKED_CANDIDATE", checks_status="PASS", outputs=outputs,
        executed_checks=plan["revalidation_checks"], revalidation_scope=plan["revalidation_scope"],
        revalidated_nodes=plan["revalidation_nodes"],
        global_invariants=plan["global_invariants"],
        actual_reads=[dict(resource_id=source["id"], source_hash=source["hash"],
                           column=column, tool_ref=action.executor.ref)
                      for column in (definition.baseline_column, definition.column)],
        preserved_objects=patch["preserved_objects"],
        check_kind="typed_csv_readback_and_global_invariants",
        dependency_completeness="FIXED_TEMPLATE_ONLY_SEMANTICS_UNKNOWN",
        semantic_status="UNKNOWN", owner_acceptance="PENDING", publishable=False,
        formal_publication_enabled=False, business_writes=0, model_requests=0,
    )

def verify_check(store, c, user, pid, aid, definition, patch, body, answer, limits):
    if body.expected_patch_fingerprint != patch["patch_fingerprint"]:
        graph.conflict("Saved check confirmation belongs to a different patch")
    # Reconstruct from trusted current definitions and actual bounded reads, not
    # from client hashes or a re-signed stored check's PASS/status claims.
    expected = execute(store, c, user, pid, aid, definition, patch, limits)
    expected["request_key"] = body.request_key
    expected["check_fingerprint"] = fingerprint(expected)
    if fingerprint(expected) != fingerprint(answer):
        graph.conflict("Saved check differs from the exact current definition/readback")


@graph.controlled
def check(store, user, pid, aid, key, body, limits):
    validate_request_key(key)
    validate_request_key(body.request_key)
    with store.tx() as c:
        definition, patch = load(store, c, user, pid, aid, key, limits)
        if patch["patch_fingerprint"] != body.expected_patch_fingerprint:
            graph.conflict("Confirm the exact saved patch version")
        if graph.lookup(c, user, aid, "column_check", body.request_key):
            old, answer = read_pair(c, user, aid, "column_check", body.request_key, CheckInput)
            if fingerprint(old.model_dump()) != fingerprint(body.model_dump()):
                graph.conflict("Check request key changed")
            if answer["patch_fingerprint"] != patch["patch_fingerprint"]:
                graph.conflict("Check belongs to another patch")
            verify_check(store, c, user, pid, aid, definition, patch, old, answer, limits)
            return {**answer, "cached": True}
        require_capacity(c, user, aid, "column_check")
        answer = execute(store, c, user, pid, aid, definition, patch, limits)
        answer["request_key"] = body.request_key
        answer["check_fingerprint"] = fingerprint(answer)
        graph.remember(c, user, aid, "column_check", body.request_key, body, answer)
        graph.remember(c, user, aid, "column_check_seal", body.request_key, body, answer)
        return {**answer, "cached": False}


@graph.controlled
def history(store, user, pid, aid, limits):
    with store.tx() as c:
        graph.current(store, c, user, pid, aid, limits)
        items, invalidated, unsupported = [], [], []
        rows = c.execute(select(requests.c.request_key).where(
            requests.c.app_id == aid, requests.c.principal_id == user,
            requests.c.kind == "column_patch").order_by(requests.c.request_key).limit(HISTORY_LIMIT)).scalars().all()
        check_keys = c.execute(select(requests.c.request_key).where(
            requests.c.app_id == aid, requests.c.principal_id == user,
            requests.c.kind == "column_check").order_by(requests.c.request_key).limit(HISTORY_LIMIT)).scalars().all()
        supported_checks = []
        for key in check_keys:
            try:
                validate_request_key(key)
                supported_checks.append(key)
            except DomainError:
                unsupported.append(dict(kind="column_check", request_key=key, state="UNSUPPORTED_KEY", reason="INVALID_INPUT"))
        for key in rows:
            try:
                validate_request_key(key)
            except DomainError:
                unsupported.append(dict(kind="column_patch", request_key=key, state="UNSUPPORTED_KEY", reason="INVALID_INPUT"))
                continue
            try:
                definition, patch = load(store, c, user, pid, aid, key, limits)
            except DomainError as exc:
                if exc.code != "VERSION_CONFLICT" or exc.message != "Column patch baseline version expired":
                    raise
                invalidated.append(dict(request_key=key, state="INVALIDATED", reason=exc.code))
                continue
            checks = []
            for row in supported_checks:
                body, result = read_pair(c, user, aid, "column_check", row, CheckInput)
                if result["patch_fingerprint"] == patch["patch_fingerprint"]:
                    verify_check(store, c, user, pid, aid, definition, patch, body, result, limits)
                    checks.append(result)
            items.append(dict(patch=patch, checks=checks))
        return dict(namespace="csv-column-patch-history.v1", project_id=pid, app_id=aid,
                    items=items, invalidated=invalidated,
                    **({"unsupported_keys": unsupported} if unsupported else {}))


def mount(app, store, identity, limits):
    dependency = Depends(identity)
    base = "/api/projects/{pid}/apps/{aid}/delivery-graph/column-patches"

    @app.post(base, status_code=201)
    def definition(pid: str, aid: str, body: DefinitionInput, user=dependency):
        return propose(store, user, pid, aid, body, limits)

    @app.post(base + "/{key:path}/checks", status_code=201)
    def confirm(pid: str, aid: str, key: str, body: CheckInput, user=dependency):
        return check(store, user, pid, aid, key, body, limits)

    @app.get(base)
    def read(pid: str, aid: str, user=dependency):
        return history(store, user, pid, aid, limits)
