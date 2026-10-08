"""Single-node CSV edit protection; no identity or permission mutation."""

from typing import Literal

from fastapi import Depends
from pydantic import Field
from sqlalchemy import select

from . import delivery_graph_apps as graph
from .column_patches import KeyInput, validate_request_key
from .db import delivery_graph_locks as locks
from .db import delivery_graph_requests as requests
from .db import fingerprint
from .errors import DomainError

KIND = "manual_edit_lock"
NAMESPACE = "manual-edit-lock.v1"
CONSENT = "CONFIRM_EXACT_PROJECT_EDIT_LOCK"


class LockInput(KeyInput):
    expected_graph_fingerprint: str = Field(pattern=graph.HASH)
    expected_graph_revision: int = Field(ge=1)
    change: graph.core.Change
    expected_lock_revision: int = Field(ge=0)
    locked: bool
    request_key: str = Field(min_length=1, max_length=128)
    consent: Literal["CONFIRM_EXACT_PROJECT_EDIT_LOCK"]


def binding(saved):
    return fingerprint({k: saved[k] for k in (
        "candidate_fingerprint", "source_versions", "authorization_fingerprint",
        "runtime_id", "stable_ids",
    )} | {"node_revisions": saved["context"]["node_revisions"]})


def context(store, c, user, pid, aid, limits):
    # Authorization and supported family precede all protected graph/lock ledgers.
    _, _, action, *_ = graph.load_family(store, c, user, pid, aid, limits)
    if action.executor.kind != "registered_tool" or action.executor.ref != "data.aggregate_csv":
        raise DomainError("UNSUPPORTED_CAPABILITY", "Only fixed CSV application edit locks are supported")
    saved = graph.state(store, c, user, pid, aid)
    fresh, _ = graph.build(store, c, user, pid, aid, limits, saved)
    if binding(fresh) != binding(saved):
        graph.conflict("Current source or authority changed; derive a new anchor")
    return saved, fresh


def lock_row(c, aid, node_id):
    return c.execute(select(locks).where(locks.c.app_id == aid, locks.c.node_id == node_id)).mappings().first()


def receipt(c, user, aid, key, fresh):
    row = graph.lookup(c, user, aid, KIND, key)
    seal = graph.lookup(c, user, aid, KIND + "_seal", key)
    value = graph.checked(row)
    if fingerprint(value) != fingerprint(graph.checked(seal)):
        graph.conflict("Manual lock accepted seal changed")
    if set(value) != {"request", "response"}:
        graph.conflict("Malformed manual lock receipt")
    body = LockInput.model_validate(value["request"])
    answer = value["response"]
    if body.request_key != key or row["request_fingerprint"] != fingerprint(body.model_dump()):
        graph.conflict("Manual lock request changed")
    if seal["request_fingerprint"] != row["request_fingerprint"]:
        graph.conflict("Manual lock request seal changed")
    canonical = graph.lookup(c, user, aid, "lock", key)
    original, saved_answer = graph.checked_request(canonical)
    expected = graph.LockInput(expected_graph_fingerprint=body.expected_graph_fingerprint,
        request_key=key, change=body.change, locked=body.locked)
    if fingerprint(original.model_dump()) != fingerprint(expected.model_dump()):
        graph.conflict("Canonical lock request changed")
    if (set(answer) != {"namespace", "project_id", "app_id", "request_key", "lock", "source_binding",
                        "needs_derive", "patch_executed", "business_write_performed", "publishable", "formal_publication_enabled"}
            or answer["namespace"] != NAMESPACE or answer["project_id"] != fresh["project_id"]
            or answer["app_id"] != aid or answer["request_key"] != key
            or fingerprint(answer["lock"]) != fingerprint(saved_answer["lock"])
            or answer["lock"]["revision"] != body.expected_lock_revision + 1
            or answer["needs_derive"] is not True
            or any(answer[k] is not False for k in ["patch_executed", "business_write_performed", "publishable", "formal_publication_enabled"])):
        graph.conflict("Manual lock response changed")
    value = answer["lock"]
    if (set(value) != {"project_id", "app_id", "principal_id", "node_id", "logical_key", "locked", "revision", "request_key"}
            or value["project_id"] != fresh["project_id"] or value["app_id"] != aid
            or value["principal_id"] != user or value["node_id"] != body.change.node_id
            or fresh["stable_ids"].get(value["logical_key"]) != value["node_id"]
            or value["request_key"] != key or type(value["revision"]) is not int
            or type(value["locked"]) is not bool or value["locked"] is not body.locked):
        graph.conflict("Manual lock identity or strict version changed")
    if answer["source_binding"] != binding(fresh):
        return body, None
    now = graph.checked(lock_row(c, aid, body.change.node_id))
    status = "CURRENT" if fingerprint(now) == fingerprint(answer["lock"]) else "SUPERSEDED"
    return body, {**answer, "receipt_status": status, "is_current": status == "CURRENT"}


@graph.controlled
def submit(store, user, pid, aid, body, limits):
    body = body if isinstance(body, LockInput) else LockInput.model_validate(body)
    validate_request_key(body.request_key)
    with store.tx() as c:
        saved, fresh = context(store, c, user, pid, aid, limits)
        prior = graph.lookup(c, user, aid, KIND, body.request_key)
        if prior:
            original, answer = receipt(c, user, aid, body.request_key, fresh)
            if fingerprint(original.model_dump()) != fingerprint(body.model_dump()) or answer is None:
                graph.conflict("Manual lock key parameters or source changed")
            return {**answer, "cached": True}
        if graph.lookup(c, user, aid, "lock", body.request_key):
            graph.conflict("Key belongs to an existing internal lock")
        current = graph.current(store, c, user, pid, aid, limits)
        if (current["graph_revision"] != body.expected_graph_revision
                or current["graph"]["graph_fingerprint"] != body.expected_graph_fingerprint):
            graph.conflict("Manual lock exact graph baseline changed")
        node = next((n for n in current["graph"]["nodes"] if n["id"] == body.change.node_id), None)
        if (node is None or node["revision"] != body.change.expected_revision
                or node["content_fingerprint"] != body.change.expected_content_fingerprint):
            graph.conflict("Manual lock node version changed")
        row = lock_row(c, aid, node["id"])
        old = graph.checked(row) if row else None
        if (old["revision"] if old else 0) != body.expected_lock_revision:
            graph.conflict("Manual lock revision changed")
        if (old["locked"] if old else False) is body.locked:
            raise DomainError("INVALID_INPUT", "Select a different lock state")
        canonical = graph.LockInput(expected_graph_fingerprint=body.expected_graph_fingerprint,
            request_key=body.request_key, change=body.change, locked=body.locked)
        result = graph.write_lock(c, user, pid, aid, canonical, node)
        answer = dict(namespace=NAMESPACE, project_id=pid, app_id=aid, request_key=body.request_key,
            lock=result["lock"], source_binding=binding(fresh), needs_derive=True,
            patch_executed=False, business_write_performed=False, publishable=False, formal_publication_enabled=False)
        for kind in [KIND, KIND + "_seal"]:
            graph.remember(c, user, aid, kind, body.request_key, body, answer)
        return {**answer, "receipt_status": "CURRENT", "is_current": True, "cached": False}


@graph.controlled
def inspect(store, user, pid, aid, limits, key=None):
    if key is not None:
        validate_request_key(key)
    with store.tx() as c:
        saved, fresh = context(store, c, user, pid, aid, limits)
        if key is not None:
            _, answer = receipt(c, user, aid, key, fresh)
            if answer is None:
                graph.conflict("Manual lock receipt source invalidated")
            return {**answer, "cached": True}
        nodes = []
        for node in fresh["graph"]["nodes"]:
            row = lock_row(c, aid, node["id"])
            value = graph.checked(row) if row else None
            nodes.append(dict(node_id=node["id"], locked=node["locked"], lock_revision=value["revision"] if value else 0))
        keys = c.execute(select(requests.c.request_key).where(requests.c.app_id == aid,
            requests.c.principal_id == user, requests.c.kind == KIND).order_by(requests.c.request_key).limit(50)).scalars().all()
        history = []
        for request_key in keys:
            _, answer = receipt(c, user, aid, request_key, fresh)
            history.append(answer or dict(request_key=request_key, receipt_status="INVALIDATED", is_current=False))
        return dict(namespace=NAMESPACE, project_id=pid, app_id=aid, nodes=nodes, history=history,
            graph_fingerprint=fresh["graph"]["graph_fingerprint"], graph_revision=saved["graph_revision"],
            needs_derive=fresh["graph"]["graph_fingerprint"] != saved["graph"]["graph_fingerprint"],
            publishable=False, formal_publication_enabled=False)


def mount(app, store, identity, limits):
    base = "/api/projects/{pid}/apps/{aid}/delivery-graph/manual-locks"
    dependency = Depends(identity)

    @app.post(base, status_code=201)
    def change(pid: str, aid: str, body: LockInput, user=dependency):
        return submit(store, user, pid, aid, body, limits)

    @app.get(base)
    def read(pid: str, aid: str, user=dependency):
        return inspect(store, user, pid, aid, limits)

    @app.get(base + "/receipt")
    def recover(pid: str, aid: str, request_key: str, user=dependency):
        return inspect(store, user, pid, aid, limits, request_key)
