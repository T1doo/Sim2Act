"""Owner-authorized permanent closure of an unused ordinary spec request key.

Rejection proofs are only a UI trigger, never an authorization capability. Closing
writes recovery metadata, no Run, model budget, business data or artifact.
"""

from pydantic import Field
from sqlalchemy import insert, select

from .contracts import Strict
from .db import (
    delivery_graph_requests,
    fingerprint,
    internal_app_runs,
    internal_instances,
    internal_releases,
    internal_run_bindings,
    runs,
)
from .db import internal_spec_run_terminals as journal
from .errors import DomainError


class OriginalRequest(Strict):
    # Revision zero is the finite VALIDATION_NOT_STARTED subset. No coercion.
    expected_revision: int = Field(ge=0, strict=True)
    expected_release_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    input: dict
    request_key: str = Field(min_length=1, max_length=100)
    expected_owner_goal_binding_fingerprint: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class CloseInput(Strict):
    release_id: str = Field(pattern=r"^irelease_[a-f0-9]{32}$")
    request: OriginalRequest


def fenced(c, user, iid, key):
    return c.execute(select(journal.c.request_key).where(journal.c.instance_id == iid,
        journal.c.principal_id == user, journal.c.request_key == key)).first() is not None


def _scope(store, c, user, iid):
    row = c.execute(select(internal_instances.c.project_id,
        internal_instances.c.source_app_id).where(internal_instances.c.id == iid,
        internal_instances.c.principal_id == user)).mappings().first()
    if row is None:
        raise DomainError("PERMISSION_DENIED")
    store.lock_project(c, user, row["project_id"])
    return row


def _absent(c, user, iid, key):
    # Scalar identities only. A partial accepted pair is never absence. A stray
    # binding has lost its key, so conservatively block closure for this instance.
    if c.execute(select(internal_app_runs.c.id).where(internal_app_runs.c.instance_id == iid,
            internal_app_runs.c.request_key == key)).first():
        raise DomainError("OUTCOME_UNKNOWN", "Accepted AppRun evidence exists; read original key")
    if c.execute(select(delivery_graph_requests.c.request_key).where(
            delivery_graph_requests.c.app_id == iid,
            delivery_graph_requests.c.request_key == key)).first():
        raise DomainError("OUTCOME_UNKNOWN", "Request ledger evidence exists")
    bindings = c.execute(select(internal_run_bindings.c.run_id,
        internal_run_bindings.c.app_run_id).where(
        internal_run_bindings.c.snapshot["instance_id"].as_string() == iid).limit(129)).all()
    if len(bindings) > 128:
        raise DomainError("OUTCOME_UNKNOWN", "Recovery metadata scan budget exhausted")
    for rid, aid in bindings:
        app = c.execute(select(internal_app_runs.c.instance_id, internal_app_runs.c.principal_id,
            internal_app_runs.c.request_key).where(internal_app_runs.c.id == aid)).first()
        header = c.execute(select(runs.c.principal_id, runs.c.request_key).where(runs.c.id == rid)).first()
        if (app is None or header is None or app.instance_id != iid or app.principal_id != user
                or header.principal_id != user or header.request_key != "internal:" + aid
                or app.request_key == key):
            raise DomainError("OUTCOME_UNKNOWN", "Accepted identities incomplete or conflicting")


def _receipt(row):
    value = {k: row[k] for k in ("instance_id", "principal_id", "request_key", "project_id",
        "app_id", "release_id", "request")}
    try:
        request = OriginalRequest.model_validate(value["request"]).model_dump(exclude_unset=True)
    except ValueError as exc:
        raise DomainError("VERSION_CONFLICT") from exc
    if (request != value["request"] or request["input"] != {}
            or request["request_key"] != value["request_key"]
            or fingerprint(value) != row["fingerprint"]):
        raise DomainError("VERSION_CONFLICT")
    return dict(namespace="spec-run-terminal.v1", status="CLOSED_NOT_ACCEPTED", **value,
        wire_request_fingerprint=fingerprint(request), new_model_requests=0, project_writes=0)


def read(store, c, user, iid, key):
    scope = _scope(store, c, user, iid)
    row = c.execute(select(journal).where(journal.c.instance_id == iid,
        journal.c.principal_id == user, journal.c.request_key == key)).mappings().first()
    if row is None:
        return None
    if row["project_id"] != scope["project_id"] or row["app_id"] != scope["source_app_id"]:
        raise DomainError("VERSION_CONFLICT")
    _absent(c, user, iid, key)
    return _receipt(row)


def close(store, user, iid, key, body):
    request = body.request.model_dump(exclude_unset=True)
    if request["request_key"] != key or request["input"] != {} or (
            "expected_owner_goal_binding_fingerprint" in request and
            request["expected_owner_goal_binding_fingerprint"] is None):
        raise DomainError("INVALID_INPUT", "Only frozen empty-input ordinary spec metadata is supported")
    with store.tx() as c:
        scope = _scope(store, c, user, iid)
        prior = read(store, c, user, iid, key)
        if prior:
            if prior["release_id"] != body.release_id or prior["request"] != request:
                raise DomainError("VERSION_CONFLICT")
            return prior
        # No material or accepted body reads; original release family and scope only.
        from .pa_spec_apps import FAMILIES
        release = c.execute(select(internal_releases.c.snapshot["draft"]["id"].as_string().label("app"),
            internal_releases.c.snapshot["draft"]["candidate"]["namespace"].as_string().label("family"))
            .where(internal_releases.c.id == body.release_id,
                internal_releases.c.project_id == scope["project_id"],
                internal_releases.c.principal_id == user)).mappings().first()
        if release is None or release["app"] != scope["source_app_id"] or release["family"] not in FAMILIES:
            raise DomainError("PERMISSION_DENIED")
        _absent(c, user, iid, key)
        row = dict(instance_id=iid, principal_id=user, request_key=key,
            project_id=scope["project_id"], app_id=scope["source_app_id"],
            release_id=body.release_id, request=request)
        row["fingerprint"] = fingerprint(row)
        c.execute(insert(journal).values(**row))
        return _receipt(row)
