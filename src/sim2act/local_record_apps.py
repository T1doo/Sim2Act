"""Closed typed record commands over the existing registered JSON artifact save.

The save tool still returns only resource_id/hash. This versioned adapter owns
record identities, immutable event validation and the instance CAS/projection.
It grants no new write authority and never accepts caller-supplied tool text.
"""

import copy
import hashlib
import json
import time
from typing import Annotated, Literal

from fastapi import Depends
from pydantic import Field
from sqlalchemy import insert, select, update

from . import lifecycle
from .apps import object_schema
from .contracts import (
    FrozenRunContract,
    GoalSpec,
    Limits,
    Strict,
    strict_json,
    validate_action,
    validate_action_input,
    validate_manifest,
    validate_value,
)
from .csv_logic_reuse import implementation
from .db import (
    attempts,
    events,
    fingerprint,
    local_effects,
    new_id,
    operation_intents,
    operations,
    projects,
    resources,
    run_contracts,
    runs,
)
from .db import (
    delivery_graph_requests as journal,
)
from .db import (
    internal_app_runs as app_runs,
)
from .db import (
    internal_approvals as approvals,
)
from .db import (
    internal_instance_data as typed,
)
from .db import (
    internal_instances as instances,
)
from .db import (
    internal_releases as releases,
)
from .db import (
    internal_run_bindings as bindings,
)
from .errors import DomainError
from .tools import definitions, reconcile_readback, write_text_artifact

VERSION = "local-record-app.v1"
EVENT_VERSION = "local-record-event.v1"
MAPPING = "local-record-input.v1"
DEF, CREATE, PREPARE, RELEASED, RELEASE_SEAL, INSTANCE, PREVIEW, ACCEPTED, RUN_SCOPE = (
    VERSION + "." + v for v in
    ("definition", "create", "release-preview", "release-commit", "release-seal", "instance", "preview", "accepted", "run-scope")
)
HASH = r"^[a-f0-9]{64}$"
MAX_EVENTS, MAX_RECORDS = 64, 32
TERMINAL = {"SUCCEEDED", "FAILED", "CANCELLED", "PARTIAL"}


def require(ok, message="Exact local record contract changed"):
    if not ok:
        raise DomainError("VERSION_CONFLICT", message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


class Key(Strict):
    request_key: str = Field(min_length=1, max_length=100)


class CreateApp(Key):
    name: str = Field(min_length=1, max_length=200)
    goal: str = Field(min_length=1, max_length=4000)
    consent: Literal["SAVE_LOCAL_RECORD_FORM"]


class ReleaseInput(Key):
    expected_definition_fingerprint: str = Field(pattern=HASH)
    consent: Literal["FREEZE_RECORD_FORM_AND_WRITE_BOUNDARY"]


class CommitRelease(Strict):
    fingerprint: str = Field(pattern=HASH)


class InstanceInput(Key):
    expected_release_fingerprint: str = Field(pattern=HASH)


class PrivateInstanceInput(InstanceInput):
    consent: Literal["CREATE_PRIVATE_WRITE_PREVIEW_NO_BUSINESS_PROMOTION"]


class CommandBase(Key):
    expected_revision: int = Field(strict=True, ge=1)
    expected_data_version: int = Field(strict=True, ge=0)
    expected_release_fingerprint: str = Field(pattern=HASH)


class CreateRecord(CommandBase):
    command: Literal["CREATE"]
    title: str = Field(min_length=1, max_length=200)
    details: str = Field(max_length=2000)


class SetState(CommandBase):
    command: Literal["SET_STATE"]
    record_id: str = Field(pattern=r"^record_[a-f0-9]{32}$")
    expected_record_revision: int = Field(strict=True, ge=1)
    target_state: Literal["DONE"]
    reason: str = Field(min_length=1, max_length=500)


class Confirm(Strict):
    expected_preview_fingerprint: str = Field(pattern=HASH)
    consent: Literal["WRITE_THIS_EXACT_LOCAL_RECORD_EVENT"]


class Control(Strict):
    command: Literal["pause", "cancel", "resume"]
    version: int = Field(strict=True, ge=1)


def command(value):
    model = CreateRecord if value.get("command") == "CREATE" else SetState
    body = model.model_validate(value).model_dump()
    require(fingerprint(body) == fingerprint(value), "Typed command is not canonical")
    if not (body["title"] if body["command"] == "CREATE" else body["reason"]).strip():
        raise DomainError("INVALID_INPUT", "Explicit nonblank record title or transition reason required")
    return body


def pair(c, user, scope, kind, key):
    rows = c.execute(select(journal).where(journal.c.app_id == scope,
        journal.c.principal_id == user, journal.c.kind.in_([kind, kind + "_seal"]),
        journal.c.request_key == key)).mappings().all()
    if not rows:
        return None
    require(len(rows) == 2)
    a, b = rows
    value = a["snapshot"]
    require(isinstance(value, dict) and set(value) == {"namespace", "request", "response"}
        and value["namespace"] == VERSION and isinstance(value["request"], dict)
        and isinstance(value["response"], dict)
        and fingerprint(value) == a["fingerprint"] == b["fingerprint"] == fingerprint(b["snapshot"])
        and a["request_fingerprint"] == b["request_fingerprint"] == fingerprint(value["request"]))
    return copy.deepcopy(value)


def remember(c, user, scope, kind, key, request, response):
    value = dict(namespace=VERSION, request=copy.deepcopy(request), response=copy.deepcopy(response))
    for tag in (kind, kind + "_seal"):
        c.execute(insert(journal).values(app_id=scope, principal_id=user, kind=tag, request_key=key,
            request_fingerprint=fingerprint(request), snapshot=value, fingerprint=fingerprint(value)))


def has_app(c, aid):
    return c.execute(select(journal.c.app_id).where(journal.c.app_id == aid,
        journal.c.kind.in_([DEF, DEF + "_seal"]))).first() is not None


def is_release(c, rid):
    return bool(c.execute(select(releases.c.id).where(releases.c.id == rid,
        releases.c.snapshot["namespace"].as_string() == VERSION)).first()
        or c.execute(select(journal.c.app_id).where(journal.c.app_id == rid,
            journal.c.kind.in_([RELEASE_SEAL, RELEASE_SEAL + "_seal"]))).first())


def is_instance(c, iid):
    from .record_preview_storage import INSTANCE as PRIVATE_INSTANCE
    rid = c.execute(select(instances.c.release_id).where(instances.c.id == iid)).scalar()
    return bool((rid is not None and is_release(c, rid)) or c.execute(select(journal.c.app_id).where(
        journal.c.kind.in_([INSTANCE, INSTANCE + "_seal", PRIVATE_INSTANCE, PRIVATE_INSTANCE + "_seal"]),
        journal.c.snapshot["response"]["id"].as_string() == iid)).first())


def is_job_tx(c, rid):
    if c.execute(select(journal.c.app_id).where(journal.c.app_id == rid,
            journal.c.kind.in_([RUN_SCOPE, RUN_SCOPE + "_seal"]))).first():
        return True
    row = c.execute(select(bindings.c.snapshot["namespace"].as_string().label("namespace"),
        app_runs.c.release_id).join(app_runs, app_runs.c.id == bindings.c.app_run_id)
        .where(bindings.c.run_id == rid)).mappings().first()
    return bool(row and (row["namespace"] == VERSION or is_release(c, row["release_id"])))


def is_job(store, rid):
    with store.engine.connect() as c:
        return is_job_tx(c, rid)


def reject_legacy(c, *, rid=None, iid=None, release_id=None, aid=None, approval_id=None):
    hit = (rid is not None and is_job_tx(c, rid)) or (iid is not None and is_instance(c, iid))
    hit = hit or (release_id is not None and is_release(c, release_id)) or (aid is not None and has_app(c, aid))
    if approval_id is not None:
        hit = hit or bool(c.execute(select(approvals.c.id).where(approvals.c.id == approval_id,
            approvals.c.kind == VERSION)).first() or c.execute(select(journal.c.app_id).where(
                journal.c.kind.in_([PREPARE, PREPARE + "_seal"]),
                journal.c.snapshot["response"]["id"].as_string() == approval_id)).first()
            or c.execute(select(journal.c.app_id).where(
                journal.c.kind.in_([RELEASE_SEAL, RELEASE_SEAL + "_seal"]),
                journal.c.snapshot["response"]["approval_id"].as_string() == approval_id)).first())
    if hit:
        raise DomainError("UNSUPPORTED_CAPABILITY", "Use the exact typed local-record endpoint")


def bounds(limits):
    return Limits(max_requests=1, max_tools=1, max_repairs=0, max_total_tokens=1,
        max_output_tokens=1, run_seconds=limits.run_seconds).model_dump()


def candidate(aid, action_id, goal_id, pid, limits):
    text = dict(type="string")
    inputs = object_schema(dict(text=dict(type="string", maxLength=8000)))
    outputs = object_schema(dict(resource_id=text, hash=text))
    permission = [dict(tool_ref="artifact.save_text", resource_ref=pid)]
    deps = [dict(kind="tool", ref="artifact.save_text", version="1"),
        dict(kind="check", ref="receipt.readback.v1", version="1")]
    action = dict(schema_version="1.0-draft", action_id=action_id, revision=1,
        input_schema=inputs, output_schema=outputs,
        executor=dict(kind="registered_tool", ref="artifact.save_text", version="1"),
        allowed_tool_refs=[], dependencies=deps, permission_requirements=permission,
        effect="project_write", preconditions=[], postcheck_refs=["receipt.readback.v1"],
        limits=bounds(limits), idempotency="transactional", reconcile_ref="operation.lookup.v1",
        error_contract=["INVALID_INPUT", "PERMISSION_DENIED", "GRANT_REVOKED", "VERSION_CONFLICT", "OUTCOME_UNKNOWN"])
    manifest = dict(schema_version="1.0-draft", app_id=aid, revision=1, origin="goal", goal_ref=goal_id,
        source_run_ref=None, input_schema=inputs, output_schema=outputs,
        outputs={key: dict(source="step", ref="save", field=key) for key in outputs["properties"]},
        views=[dict(component_ref="text", output_field="resource_id")],
        workflow=[dict(step_id="save", binding_id="save", depends_on=[],
            inputs=dict(text=dict(source="input", field="text")))],
        action_bindings=[dict(binding_id="save", action_id=action_id, revision=1)], data_bindings=[],
        runtime_identity_requirements=dict(mode="user_and_project_intersection"),
        permission_requirements=permission, dependency_lock=deps, validation_suite_ref="receipt.readback.v1",
        runtime_limits=bounds(limits), data_schema_version=1)
    validate_action(canonical(action))
    validate_manifest(canonical(manifest))
    return dict(namespace=VERSION, manifest=manifest, actions=[action])


def definition(aid, action_id, goal_id, user, project, body, limits):
    return dict(namespace=VERSION, id=aid, name=body["name"], principal_id=user,
        project_id=project["id"], runtime_id=project["runtime_id"], purpose=body["goal"], goal_id=goal_id,
        candidate=candidate(aid, action_id, goal_id, project["id"], limits),
        typed_mapping_version=MAPPING,
        typed_command_schemas=dict(CREATE=CreateRecord.model_json_schema(), SET_STATE=SetState.model_json_schema()),
        hard_conditions=["CREATE assigns a stable record identity and OPEN@1", "Only OPEN to DONE with an explicit reason",
            "Immutable events and exact record/data CAS; no history overwrite", "No model or semantic acceptance"],
        limits=dict(max_events=MAX_EVENTS, max_records=MAX_RECORDS),
        derived_read_grants_per_event=2, formal_publication_enabled=False)


def public_app(value):
    return {**copy.deepcopy(value), "fingerprint": fingerprint(value), "definition": copy.deepcopy(value),
        "input_guidance": dict(mode="LOCAL_RECORDS"), "formal_publication_enabled": False}


def app_scope(store, c, user, aid):
    pid = c.execute(select(journal.c.snapshot["response"]["project_id"].as_string())
        .where(journal.c.app_id == aid, journal.c.principal_id == user,
            journal.c.kind.in_([DEF, DEF + "_seal"]))).scalars().all()
    if not pid:
        raise DomainError("PERMISSION_DENIED")
    require(len(pid) == 2 and len(set(pid)) == 1, "Owned record definition seal missing")
    return store.lock_project(c, user, pid[0])


def checked_app(store, c, user, aid, limits):
    project = app_scope(store, c, user, aid)
    saved = pair(c, user, aid, DEF, "definition")
    require(saved is not None)
    body = CreateApp.model_validate(saved["request"]).model_dump()
    value = saved["response"]
    expected = definition(aid, value["candidate"]["actions"][0]["action_id"], value["goal_id"], user, project, body, limits)
    require(fingerprint(expected) == fingerprint(value))
    return value


def summaries(c, user):
    rows = c.execute(select(journal.c.app_id,
        journal.c.snapshot["response"]["name"].as_string().label("name"),
        journal.c.snapshot["response"]["project_id"].as_string().label("pid"))
        .where(journal.c.principal_id == user, journal.c.kind == DEF)).mappings().all()
    owned = set(c.execute(select(projects.c.id).where(projects.c.owner_id == user)).scalars())
    return [dict(id=r["app_id"], name=r["name"], project_id=r["pid"], use_family="LOCAL_RECORDS",
        definition_version=VERSION, csv_instance_candidate=False) for r in rows if r["pid"] in owned]


def create_app(store, user, pid, body, limits):
    with store.tx() as c:
        project = store.lock_project(c, user, pid)
        store.authorize(c, user, project["runtime_id"], pid, pid, "artifact.save_text")
        old = pair(c, user, pid, CREATE, body["request_key"])
        if old:
            require(fingerprint(old["request"]) == fingerprint(body), "Original application key differs")
            value = checked_app(store, c, user, old["response"]["id"], limits)
        else:
            if not body["name"].strip() or not body["goal"].strip():
                raise DomainError("INVALID_INPUT")
            value = definition(new_id("app"), new_id("action"), new_id("goal"), user, project, body, limits)
            remember(c, user, value["id"], DEF, "definition", body, value)
            remember(c, user, pid, CREATE, body["request_key"], body, dict(id=value["id"]))
        return {**public_app(value), "request_key": body["request_key"], "request_fingerprint": fingerprint(body)}


def release_snapshot(value):
    return dict(namespace=VERSION, app_id=value["id"], principal_id=value["principal_id"],
        project_id=value["project_id"], runtime_id=value["runtime_id"], definition=value,
        definition_fingerprint=fingerprint(value), software_fingerprint=implementation(),
        tool_definitions_fingerprint=fingerprint(definitions()),
        data_schema=lifecycle.record_schema(value["candidate"], {"type": "object", "properties": {
            "result": value["candidate"]["manifest"]["output_schema"], "release_ref": {"type": "string"}},
            "required": ["result", "release_ref"], "additionalProperties": False}),
        check=dict(status="PASS", scope="CANONICAL_TYPED_MAPPING_AND_ARTIFACT_SCHEMA_ONLY",
            artifact_writes=0, grant_writes=0, model_requests=0), formal_publication_enabled=False)


def release_header(store, c, user, rid):
    row = c.execute(select(releases.c.id, releases.c.principal_id, releases.c.project_id,
        releases.c.approval_id, releases.c.fingerprint,
        releases.c.snapshot["namespace"].as_string().label("namespace"),
        releases.c.snapshot["app_id"].as_string().label("app_id"),
        releases.c.snapshot["runtime_id"].as_string().label("runtime_id"))
        .where(releases.c.id == rid, releases.c.principal_id == user)).mappings().first()
    if row is None:
        raise DomainError("PERMISSION_DENIED")
    project = store.lock_project(c, user, row["project_id"])
    require(row["namespace"] == VERSION and row["runtime_id"] == project["runtime_id"])
    seal = pair(c, user, rid, RELEASE_SEAL, "release")
    require(seal is not None and fingerprint(seal["request"]) == fingerprint(seal["response"])
        and seal["response"] == {k: row[k] for k in ("id", "principal_id", "project_id", "approval_id", "fingerprint", "app_id", "runtime_id")})
    return dict(row)


def read_release(store, c, user, rid, limits):
    header = release_header(store, c, user, rid)
    row = dict(c.execute(select(releases).where(releases.c.id == rid)).mappings().one())
    value = checked_app(store, c, user, header["app_id"], limits)
    require(fingerprint(row["snapshot"]) == row["fingerprint"] == fingerprint(release_snapshot(value)))
    approval = lifecycle.approval(c, user, row["approval_id"],
        c.execute(select(approvals.c.fingerprint).where(approvals.c.id == row["approval_id"])).scalar_one(),
        VERSION, allow_consumed=True)
    require(approval["consumed"] and fingerprint(approval["payload"]["snapshot"]) == row["fingerprint"])
    return row


def release_metadata(row):
    return dict(id=row["id"], fingerprint=row["fingerprint"], project_id=row["project_id"],
        source_app_id=row["snapshot"]["app_id"])


def release_request(store, c, user, aid, key, limits):
    value = checked_app(store, c, user, aid, limits)
    saved = pair(c, user, aid, PREPARE, key)
    if not saved:
        raise DomainError("OUTCOME_UNKNOWN", "Original record Release request not found")
    body = ReleaseInput.model_validate(saved["request"]).model_dump()
    require(body["expected_definition_fingerprint"] == fingerprint(value))
    # Recovery is a read of the original receipt, including an expired proposal.
    # Commit below still uses the original approval expiry/consumption guard.
    approval = c.execute(select(approvals).where(approvals.c.id == saved["response"]["id"],
        approvals.c.principal_id == user)).mappings().first()
    require(approval is not None)
    approval = dict(approval)
    payload = approval["payload"]
    require(approval["kind"] == VERSION and approval["project_id"] == value["project_id"]
        and set(payload) == {"snapshot", "approval_id", "principal_id", "project_id", "kind", "expires_at"}
        and payload["kind"] == VERSION and payload["approval_id"] == approval["id"]
        and payload["principal_id"] == user and payload["project_id"] == approval["project_id"]
        and payload["expires_at"] == approval["expires_at"]
        and fingerprint(payload) == approval["fingerprint"] == saved["response"]["fingerprint"]
        and fingerprint(payload["snapshot"]) == fingerprint(release_snapshot(value)))
    committed = pair(c, user, aid, RELEASED, key)
    release = read_release(store, c, user, committed["response"]["id"], limits) if committed else None
    require(bool(approval["consumed"]) == bool(committed))
    return dict(namespace=VERSION, app_id=aid, request_key=key, request_fingerprint=fingerprint(body),
        approval=approval, release=release_metadata(release) if release else None, formal_publication_enabled=False)


def prepare_release(store, user, aid, body, limits):
    with store.tx() as c:
        value = checked_app(store, c, user, aid, limits)
        store.authorize(c, user, value["runtime_id"], value["project_id"], value["project_id"], "artifact.save_text")
        old = pair(c, user, aid, PREPARE, body["request_key"])
        if old:
            require(fingerprint(old["request"]) == fingerprint(body))
        else:
            require(body["expected_definition_fingerprint"] == fingerprint(value))
            approval = lifecycle.new_approval(c, user, value["project_id"], VERSION, dict(snapshot=release_snapshot(value)))
            remember(c, user, aid, PREPARE, body["request_key"], body, dict(id=approval["id"], fingerprint=approval["fingerprint"]))
        return release_request(store, c, user, aid, body["request_key"], limits)


def commit_release(store, user, aid, key, body, limits):
    with store.tx() as c:
        current = release_request(store, c, user, aid, key, limits)
        require(current["approval"]["fingerprint"] == body["fingerprint"])
        old = pair(c, user, aid, RELEASED, key)
        if old:
            require(fingerprint(old["request"]) == fingerprint(body))
            return current
        approval = lifecycle.approval(c, user, current["approval"]["id"], body["fingerprint"], VERSION)
        snapshot = approval["payload"]["snapshot"]
        value = checked_app(store, c, user, aid, limits)
        require(fingerprint(snapshot) == fingerprint(release_snapshot(value)))
        store.authorize(c, user, value["runtime_id"], value["project_id"], value["project_id"], "artifact.save_text")
        rid = new_id("irelease")
        c.execute(insert(releases).values(id=rid, project_id=value["project_id"], principal_id=user,
            approval_id=approval["id"], snapshot=snapshot, fingerprint=fingerprint(snapshot)))
        header = dict(id=rid, principal_id=user, project_id=value["project_id"], approval_id=approval["id"],
            fingerprint=fingerprint(snapshot), app_id=aid, runtime_id=value["runtime_id"])
        remember(c, user, rid, RELEASE_SEAL, "release", header, header)
        c.execute(update(approvals).where(approvals.c.id == approval["id"], approvals.c.consumed.is_(False)).values(consumed=True))
        remember(c, user, aid, RELEASED, key, body, dict(id=rid))
        return release_request(store, c, user, aid, key, limits)


def instance_header(store, c, user, iid):
    row = c.execute(select(instances.c.id, instances.c.project_id, instances.c.principal_id,
        instances.c.source_app_id, instances.c.runtime_id, instances.c.release_id,
        instances.c.revision, instances.c.data_version).where(instances.c.id == iid,
            instances.c.principal_id == user)).mappings().first()
    if row is None:
        raise DomainError("PERMISSION_DENIED")
    project = store.lock_project(c, user, row["project_id"])
    release = release_header(store, c, user, row["release_id"])
    require(row["runtime_id"] == project["runtime_id"] == release["runtime_id"]
        and row["source_app_id"] == release["app_id"] and row["project_id"] == release["project_id"]
        and type(row["revision"]) is int and row["revision"] == 1
        and type(row["data_version"]) is int and 0 <= row["data_version"] <= MAX_EVENTS)
    from . import record_preview_storage as private
    anchors = c.execute(select(journal.c.app_id, journal.c.request_key,journal.c.kind).where(
        journal.c.principal_id == user, journal.c.kind.in_([INSTANCE, INSTANCE + "_seal",private.INSTANCE,private.INSTANCE + "_seal"]),
        journal.c.snapshot["response"]["id"].as_string() == iid)).all()
    require(len(anchors) == 2 and len({(r[0],r[1]) for r in anchors}) == 1 and anchors[0][0] == row["release_id"],
        "Original instance creation receipt missing or rebound")
    kind=private.INSTANCE if any(r[2] == private.INSTANCE for r in anchors) else INSTANCE
    require({r[2] for r in anchors} == {kind,kind + "_seal"})
    created = pair(c, user, row["release_id"], kind, anchors[0][1])
    require(created is not None and created["response"] == dict(id=iid))
    request = created["request"]
    if kind == private.INSTANCE:
        request = PrivateInstanceInput.model_validate(request).model_dump()
    else:
        request = InstanceInput.model_validate(request).model_dump()
    require(request["expected_release_fingerprint"] == release["fingerprint"]
        and request["request_key"] == anchors[0][1])
    result=dict(row)
    if kind == private.INSTANCE:
        result["preview_scope"]=private.scope(result,release,request)
    return result, release


def create_instance(store, user, rid, body, limits, *, private=False):
    with store.tx() as c:
        release = read_release(store, c, user, rid, limits)
        value = release["snapshot"]["definition"]
        store.authorize(c, user, value["runtime_id"], value["project_id"], value["project_id"], "artifact.save_text")
        require(body["expected_release_fingerprint"] == release["fingerprint"])
        from . import record_preview_storage as private_store
        kind=private_store.INSTANCE if private else INSTANCE
        if private:
            body = PrivateInstanceInput.model_validate(body).model_dump()
        old = pair(c, user, rid, kind, body["request_key"])
        if old:
            require(fingerprint(old["request"]) == fingerprint(body))
            row, _ = instance_header(store, c, user, old["response"]["id"])
        else:
            row = dict(id=new_id("iinstance"), project_id=value["project_id"], principal_id=user,
                source_app_id=value["id"], runtime_id=value["runtime_id"], release_id=rid, revision=1, data_version=0)
            c.execute(insert(instances).values(**row, history=[]))
            if private:
                require(len(c.execute(select(journal.c.app_id).where(journal.c.principal_id == user,
                    journal.c.kind == kind, journal.c.app_id == rid)).all()) < 32,
                    "Private preview instance capacity reached")
            remember(c, user, rid, kind, body["request_key"], body, dict(id=row["id"]))
            row,_=instance_header(store,c,user,row["id"])
        return dict(namespace=VERSION, request_key=body["request_key"], request_fingerprint=fingerprint(body),
            instance=row, **private_store.exposure(row), formal_publication_enabled=False)


def scope_job(store, c, user, rid, iid=None):
    row = c.execute(select(runs.c.project_id, runs.c.runtime_id, runs.c.request_key,
        bindings.c.app_run_id, bindings.c.snapshot["instance_id"].as_string().label("iid"),
        app_runs.c.instance_id, app_runs.c.release_id).select_from(runs)
        .join(bindings, bindings.c.run_id == runs.c.id).join(app_runs, app_runs.c.id == bindings.c.app_run_id)
        .where(runs.c.id == rid, runs.c.principal_id == user, app_runs.c.principal_id == user)).mappings().first()
    if row is None or (iid is not None and row["iid"] != iid):
        raise DomainError("PERMISSION_DENIED")
    i, release = instance_header(store, c, user, row["iid"])
    expected = dict(namespace=VERSION, run_id=rid, app_run_id=row["app_run_id"], instance_id=i["id"],
        principal_id=user, project_id=i["project_id"], runtime_id=i["runtime_id"], release_id=row["release_id"], app_id=i["source_app_id"])
    if "preview_scope" in i:
        expected["preview_scope_fingerprint"] = i["preview_scope"]["fingerprint"]
    saved = pair(c, user, rid, RUN_SCOPE, "accepted")
    require(saved is not None and fingerprint(saved["request"]) == fingerprint(expected)
        and fingerprint(saved["response"]) == fingerprint(expected)
        and row["instance_id"] == i["id"] and row["project_id"] == i["project_id"]
        and row["runtime_id"] == i["runtime_id"] and row["release_id"] == release["id"]
        and row["request_key"] == "internal:" + row["app_run_id"])
    return i, release, row["app_run_id"]


def authorize_data(store, c, user, i, *, write=True):
    if write:
        store.authorize(c, user, i["runtime_id"], i["project_id"], i["project_id"], "artifact.save_text")
    aids = list(c.execute(select(app_runs.c.id).where(app_runs.c.instance_id == i["id"])).scalars())
    job_ids = list(c.execute(select(bindings.c.run_id).where(bindings.c.app_run_id.in_(aids))).scalars())
    ids = set(c.execute(select(local_effects.c.resource_id).join(operations, operations.c.id == local_effects.c.operation_id)
        .where(operations.c.run_id.in_(job_ids))).scalars())
    ids.update(c.execute(select(events.c.data["artifact_resource"].as_string()).where(events.c.run_id.in_(job_ids),
        events.c.kind == "LOCAL_RECORD_COMMITTED")).scalars())
    ids.update(c.execute(select(typed.c.data["result"]["resource_id"].as_string()).where(typed.c.instance_id == i["id"])).scalars())
    ids.update(c.execute(select(app_runs.c.output["resource_id"].as_string()).where(app_runs.c.instance_id == i["id"])).scalars())
    ids.discard(None)
    require(len(ids) <= MAX_EVENTS)
    for resource in sorted(ids):
        if "preview_scope" in i:
            from .record_preview_storage import artifact
            artifact(store,c,user,i,resource)
        else:
            store.authorize(c, user, i["runtime_id"], i["project_id"], resource, "resource.read")


def job_scope_gate(store, c, rid):
    if not is_job_tx(c, rid):
        return False
    user = c.execute(select(runs.c.principal_id).where(runs.c.id == rid)).scalar_one()
    i, _, _ = scope_job(store, c, user, rid)
    authorize_data(store, c, user, i)
    return True


def run_contract(i, value, rid, limits):
    return FrozenRunContract(run_id=rid, runtime_id=i["runtime_id"], contract_version="F1.3",
        goal=GoalSpec(goal_id=value["goal_id"], project_id=i["project_id"], owner_id=i["principal_id"],
            goal=value["purpose"], constraints=value["hard_conditions"], acceptance_version="F1-tool-chain.v1",
            resource_refs=[], unresolved=["Fixed typed form; not model-generated, semantic acceptance NOT_RUN"]),
        resources=[], limits=Limits(**bounds(limits)), mode="mock", request_model="intern-s2").model_dump()


def apply_event(current, event, previous, version, i):
    keys = {"namespace", "app_id", "instance_id", "release_id", "principal_id", "kind", "collection_version",
        "record_id", "record_revision", "previous_event_fingerprint", "previous_collection_fingerprint", "title", "details", "state", "reason"}
    require(set(event) == keys and event["namespace"] == EVENT_VERSION and event["app_id"] == i["source_app_id"]
        and event["instance_id"] == i["id"] and event["release_id"] == i["release_id"]
        and event["principal_id"] == i["principal_id"] and type(event["collection_version"]) is int
        and event["collection_version"] == version and event["previous_collection_fingerprint"] == previous
        and type(event["record_revision"]) is int and isinstance(event["title"], str) and 1 <= len(event["title"]) <= 200
        and event["title"].strip() and isinstance(event["details"], str) and len(event["details"]) <= 2000)
    import re
    require(isinstance(event["record_id"], str) and re.fullmatch(r"record_[a-f0-9]{32}", event["record_id"]) is not None)
    old = current.get(event["record_id"])
    if event["kind"] == "CREATE":
        require(old is None and len(current) < MAX_RECORDS and event["record_revision"] == 1
            and event["state"] == "OPEN" and event["previous_event_fingerprint"] is None and event["reason"] == "")
    else:
        require(event["kind"] == "SET_STATE" and old is not None and old["state"] == "OPEN"
            and event["state"] == "DONE" and event["record_revision"] == old["record_revision"] + 1
            and event["previous_event_fingerprint"] == old["last_event_fingerprint"]
            and event["title"] == old["title"] and event["details"] == old["details"]
            and isinstance(event["reason"], str) and 1 <= len(event["reason"]) <= 500 and event["reason"].strip())
    fp = fingerprint(event)
    current[event["record_id"]] = {k: event[k] for k in ("record_id", "record_revision", "title", "details", "state")} | dict(last_event_fingerprint=fp)
    return fp


def accepted_binding(store, c, user, rid, limits):
    i, header, aid = scope_job(store, c, user, rid)
    authorize_data(store, c, user, i)
    release = read_release(store, c, user, header["id"], limits)
    b = c.execute(select(bindings).where(bindings.c.run_id == rid)).mappings().one()
    s = b["snapshot"]
    require(s.get("preview_scope_fingerprint") == i.get("preview_scope",{}).get("fingerprint"))
    job = c.execute(select(runs).where(runs.c.id == rid, runs.c.principal_id == user)).mappings().one()
    require(all(job["context"].get(k) == v for k, v in execution_scope(i).items()))
    a = c.execute(select(app_runs).where(app_runs.c.id == aid)).mappings().one()
    require(s["namespace"] == VERSION and fingerprint(s) == b["fingerprint"] == job["fingerprint"]
        and s["run_id"] == rid and s["app_run_id"] == aid and s["instance_id"] == i["id"]
        and s["principal_id"] == user and s["project_id"] == i["project_id"] and s["runtime_id"] == i["runtime_id"]
        and s["release_id"] == release["id"] and s["expected_release_fingerprint"] == release["fingerprint"]
        and a["fingerprint"] == s["request_fingerprint"] == fingerprint(s["request"])
        and fingerprint(a["input"]) == fingerprint(s["input"])
        and a["instance_id"] == i["id"] and a["release_id"] == release["id"]
        and a["principal_id"] == user and a["request_key"] == s["preview_key"]
        and (a["status"] == job["status"] or (a["status"] == "QUEUED" and job["status"] == "RUNNING")))
    commit = Confirm.model_validate(s["request"]).model_dump()
    require(commit["expected_preview_fingerprint"] == s["preview_fingerprint"])
    preview = pair(c, user, i["id"], PREVIEW, s["preview_key"])
    require(preview is not None and fingerprint(preview["response"]) == s["preview_fingerprint"]
        and fingerprint(preview["request"]) == fingerprint(s["input"]))
    accepted = pair(c, user, i["id"], ACCEPTED, s["preview_key"])
    require(accepted is not None and fingerprint(accepted["request"]) == fingerprint(commit)
        and accepted["response"] == dict(run_id=rid, app_run_id=aid))
    contract = store.frozen_contract(c, job).model_dump()
    require(fingerprint(contract) == fingerprint(run_contract(i, release["snapshot"]["definition"], rid, limits))
        and job["resource_refs"] == [] and contract["resources"] == []
        and all(type(job["context"].get(k)) is int and job["context"][k] == 0 for k in ("requests", "repairs", "reserved_tokens"))
        and not c.execute(select(attempts.c.id).where(attempts.c.run_id == rid)).first())
    return i, release, dict(job), dict(a), s, preview["response"]


def execution_scope(i):
    from .record_preview_storage import exposure
    return exposure(i)


def run_result(i, a, event, output, version):
    return dict(namespace=VERSION, instance_id=i["id"], app_run_id=a["id"], release_id=a["release_id"],
        result_version=version, record_id=event["record_id"], record_revision=event["record_revision"],
        event_fingerprint=fingerprint(event), artifact=output, **execution_scope(i))


def projection(store, c, user, i, limits):
    authorize_data(store, c, user, i)
    release = read_release(store, c, user, i["release_id"], limits)
    rows = c.execute(select(typed).where(typed.c.instance_id == i["id"]).order_by(typed.c.version)).mappings().all()
    require(len(rows) == i["data_version"])
    current: dict = {}
    history, previous = [], None
    verified = set()
    for version, row in enumerate(rows, 1):
        require(type(row["version"]) is int and row["version"] == version and row["release_id"] == i["release_id"]
            and row["schema_version"] == 1 and fingerprint(row["data"]) == row["fingerprint"])
        validate_value(release["snapshot"]["data_schema"], row["data"])
        rid = c.execute(select(bindings.c.run_id).where(bindings.c.app_run_id == row["run_id"])).scalar_one()
        _, _, job, a, snapshot, preview = accepted_binding(store, c, user, rid, limits)
        ops = c.execute(select(operations).where(operations.c.run_id == rid)).mappings().all()
        require(len(ops) == 1 and ops[0]["tool_ref"] == "artifact.save_text" and ops[0]["call_id"] == "record_event"
            and ops[0]["status"] == "VERIFIED")
        op = ops[0]
        from . import record_preview_storage as private
        status, receipt = reconcile_readback(store, c, job, op,preview_context=private.target(i,job,op["id"]))
        output = row["data"]["result"]
        require(status == "VERIFIED" and fingerprint(receipt) == fingerprint(op["receipt"])
            and fingerprint(output) == fingerprint(receipt["data"]) == fingerprint(a["output"])
            and row["data"]["release_ref"] == release["id"] and a["result_version"] == version
            and a["status"] == job["status"] == "SUCCEEDED" and a["error"] is None and job["error"] is None
            and not job["cancel_intent"] and job["context"]["tools"] == 1
            and snapshot["expected_data_version"] == version - 1 and snapshot["expected_revision"] == i["revision"])
        if "preview_scope" in i:
            resource=private.artifact(store,c,user,i,output["resource_id"])
        else:
            resource = c.execute(select(resources).where(resources.c.id == output["resource_id"],
                resources.c.project_id == i["project_id"])).mappings().one()
        event = strict_json(resource["content"], 32768)
        require(resource["format"] == "json" and resource["content"] == canonical(event)
            and resource["hash"] == hashlib.sha256(resource["content"].encode()).hexdigest() == output["hash"]
            and fingerprint(event) == fingerprint(preview["event"]) == preview["event_fingerprint"])
        intent = c.execute(select(operation_intents.c.request).where(operation_intents.c.operation_id == op["id"])).scalar_one()
        require(fingerprint(intent) == fingerprint(dict(tool="artifact.save_text", args=dict(text=canonical(event)))))
        previous = apply_event(current, event, previous, version, i)
        require(fingerprint(job["result"]) == fingerprint(run_result(i, a, event, output, version)))
        committed = c.execute(select(events.c.data).where(events.c.run_id == rid,
            events.c.kind == "LOCAL_RECORD_COMMITTED")).scalars().all()
        require(fingerprint(committed) == fingerprint([dict(instance_id=i["id"], app_run_id=a["id"],
            artifact_resource=output["resource_id"], event_fingerprint=previous, result_version=version)]))
        history.append(dict(version=version, event=event, event_fingerprint=previous, artifact=output,
            run_id=rid, app_run_id=a["id"]))
        verified.add(a["id"])
    ar = c.execute(select(app_runs.c.id, app_runs.c.status, app_runs.c.output,
        app_runs.c.result_version).where(app_runs.c.instance_id == i["id"])).mappings().all()
    require({a["id"] for a in ar if a["status"] == "SUCCEEDED"} == verified, "Successful records and typed events differ")
    for a in ar:
        if a["id"] in verified:
            continue
        require(a["output"] is None and a["result_version"] is None, "Uncommitted record output residue")
        job = c.execute(select(runs.c.id, runs.c.result, runs.c.status).join(bindings,
            bindings.c.run_id == runs.c.id).where(bindings.c.app_run_id == a["id"])).mappings().one()
        require((job["status"] == a["status"] or (a["status"] == "QUEUED" and job["status"] == "RUNNING"))
            and job["result"] is None
            and not c.execute(select(operations.c.id).where(operations.c.run_id == job["id"])).first()
            and not c.execute(select(events.c.id).where(events.c.run_id == job["id"],
                events.c.kind == "LOCAL_RECORD_COMMITTED")).first(), "Uncommitted record effect residue")
    return list(current.values()), history


def no_pending(c, iid):
    require(c.execute(select(app_runs.c.id).where(app_runs.c.instance_id == iid,
        app_runs.c.status.not_in(TERMINAL))).first() is None, "An instance write is already in progress")


def build_preview(i, release, body, records, history):
    body = command(body)
    require(body["expected_revision"] == i["revision"] and body["expected_data_version"] == i["data_version"]
        and body["expected_release_fingerprint"] == release["fingerprint"] and i["data_version"] < MAX_EVENTS,
        "Record baseline or capacity changed")
    current = {r["record_id"]: r for r in records}
    if body["command"] == "CREATE":
        require(len(current) < MAX_RECORDS)
        record_id, revision, old, title, details, reason, state = new_id("record"), 1, None, body["title"], body["details"], "", "OPEN"
    else:
        old = current.get(body["record_id"])
        require(old is not None and old["record_revision"] == body["expected_record_revision"]
            and old["state"] == "OPEN", "Record identity, version or allowed state changed")
        assert old is not None  # require above rejects before field access.
        record_id, revision = old["record_id"], old["record_revision"] + 1
        title, details, reason, state = old["title"], old["details"], body["reason"], body["target_state"]
    event = dict(namespace=EVENT_VERSION, app_id=i["source_app_id"], instance_id=i["id"], release_id=i["release_id"],
        principal_id=i["principal_id"], kind=body["command"], collection_version=i["data_version"] + 1,
        record_id=record_id, record_revision=revision, previous_event_fingerprint=old["last_event_fingerprint"] if old else None,
        previous_collection_fingerprint=history[-1]["event_fingerprint"] if history else None,
        title=title, details=details, state=state, reason=reason)
    apply_event(copy.deepcopy(current), event, event["previous_collection_fingerprint"], i["data_version"] + 1, i)
    validate_action_input(validate_action(canonical(release["snapshot"]["definition"]["candidate"]["actions"][0])), dict(text=canonical(event)))
    return dict(event=event, event_fingerprint=fingerprint(event), input=body, instance_revision=i["revision"],
        data_version=i["data_version"], release_id=i["release_id"], release_fingerprint=release["fingerprint"],
        expires_at=time.time() + 900, typed_mapping_version=MAPPING)


def request_state(store, c, user, iid, key, limits):
    i, _ = instance_header(store, c, user, iid)
    authorize_data(store, c, user, i)
    saved = pair(c, user, iid, PREVIEW, key)
    if not saved:
        raise DomainError("OUTCOME_UNKNOWN", "Original record request key not found")
    command(saved["request"])
    preview = saved["response"]
    require(fingerprint(preview["input"]) == fingerprint(saved["request"]) and preview["event"]["instance_id"] == iid
        and preview["event"]["principal_id"] == user and preview["event_fingerprint"] == fingerprint(preview["event"]))
    accepted = pair(c, user, iid, ACCEPTED, key)
    receipt = None
    if accepted:
        _, _, job, a, _, frozen = accepted_binding(store, c, user, accepted["response"]["run_id"], limits)
        require(fingerprint(frozen) == fingerprint(preview))
        _, history = projection(store, c, user, i, limits)
        matches = [row for row in history if row["run_id"] == job["id"] and row["app_run_id"] == a["id"]]
        require(len(matches) == (1 if job["status"] == "SUCCEEDED" else 0),
            "Original Run receipt lacks its exact committed event")
        receipt = dict(run_id=job["id"], app_run_id=a["id"], status=job["status"], version=job["version"], cached=True)
    return dict(namespace=VERSION, principal_id=user, project_id=i["project_id"], instance_id=iid,
        app_id=i["source_app_id"], request_key=key, request_fingerprint=fingerprint(saved["request"]),
        preview=preview, preview_fingerprint=fingerprint(preview), run=receipt, formal_publication_enabled=False)


def preview(store, user, iid, body, limits):
    with store.tx() as c:
        i, _ = instance_header(store, c, user, iid)
        records, history = projection(store, c, user, i, limits)
        old = pair(c, user, iid, PREVIEW, body["request_key"])
        if old:
            require(fingerprint(old["request"]) == fingerprint(body))
        else:
            no_pending(c, iid)
            release = read_release(store, c, user, i["release_id"], limits)
            value = build_preview(i, release, body, records, history)
            remember(c, user, iid, PREVIEW, body["request_key"], body, value)
        return request_state(store, c, user, iid, body["request_key"], limits)


def confirm(store, user, iid, key, body, limits):
    from .app_jobs import submission_tx
    guard: dict = {}
    with submission_tx(store, guard) as c:
        i, _ = instance_header(store, c, user, iid)
        authorize_data(store, c, user, i)
        old = pair(c, user, iid, ACCEPTED, key)
        if old:
            require(fingerprint(old["request"]) == fingerprint(body))
            return request_state(store, c, user, iid, key, limits)
        guard["proof"] = dict(namespace="local-record-submission-rejection.v1", principal_id=user,
            project_id=i["project_id"], instance_id=iid, request_key=key, request_fingerprint=fingerprint(body),
            acceptance="NOT_ACCEPTED", previous_request="ABSENT", phase="TX_ROLLED_BACK")
        state = request_state(store, c, user, iid, key, limits)
        frozen = state["preview"]
        require(state["preview_fingerprint"] == body["expected_preview_fingerprint"] and time.time() < frozen["expires_at"])
        records, history = projection(store, c, user, i, limits)
        no_pending(c, iid)
        release = read_release(store, c, user, i["release_id"], limits)
        fresh = build_preview(i, release, frozen["input"], records, history)
        fresh["event"]["record_id"] = frozen["event"]["record_id"]
        fresh["event_fingerprint"] = fingerprint(fresh["event"])
        fresh["expires_at"] = frozen["expires_at"]
        require(fingerprint(fresh) == fingerprint(frozen), "Exact record preview is stale")
        jid, aid = new_id("run"), new_id("iapprun")
        snapshot = dict(namespace=VERSION, run_id=jid, app_run_id=aid, instance_id=iid,
            principal_id=user, project_id=i["project_id"], runtime_id=i["runtime_id"], release_id=release["id"],
            expected_release_fingerprint=release["fingerprint"], expected_revision=i["revision"],
            expected_data_version=i["data_version"], preview_key=key, preview_fingerprint=fingerprint(frozen),
            request=body, request_fingerprint=fingerprint(body), input=frozen["input"])
        if "preview_scope" in i:
            snapshot["preview_scope_fingerprint"] = i["preview_scope"]["fingerprint"]
        contract = run_contract(i, release["snapshot"]["definition"], jid, limits)
        c.execute(insert(run_contracts).values(run_id=jid, snapshot=contract, fingerprint=fingerprint(contract)))
        c.execute(insert(runs).values(id=jid, project_id=i["project_id"], principal_id=user, runtime_id=i["runtime_id"],
            goal=release["snapshot"]["definition"]["purpose"], resource_refs=[], status="QUEUED", request_key="internal:" + aid,
            fingerprint=fingerprint(snapshot), created_at=time.time(), lease_until=0, fence=0, version=1, cancel_intent=False,
            context=dict(kind="INTERNAL_APPRUN", local_records=VERSION, **execution_scope(i), messages=[], requests=0, tools=0, repairs=0, reserved_tokens=0)))
        c.execute(insert(app_runs).values(id=aid, instance_id=iid, release_id=release["id"], principal_id=user,
            request_key=key, fingerprint=fingerprint(body), input=frozen["input"], status="QUEUED", output=None, error=None, result_version=None))
        c.execute(insert(bindings).values(run_id=jid, app_run_id=aid, snapshot=snapshot, fingerprint=fingerprint(snapshot)))
        metadata = dict(namespace=VERSION, run_id=jid, app_run_id=aid, instance_id=iid, principal_id=user,
            project_id=i["project_id"], runtime_id=i["runtime_id"], release_id=release["id"], app_id=i["source_app_id"])
        if "preview_scope" in i:
            metadata["preview_scope_fingerprint"] = i["preview_scope"]["fingerprint"]
        remember(c, user, jid, RUN_SCOPE, "accepted", metadata, metadata)
        remember(c, user, iid, ACCEPTED, key, body, dict(run_id=jid, app_run_id=aid))
        store.event(c, jid, "ACCEPTED", dict(namespace=VERSION, instance_id=iid, app_run_id=aid,
            release_id=release["id"], preview_fingerprint=fingerprint(frozen)))
        response = request_state(store, c, user, iid, key, limits)
        response["run"]["cached"] = False
        return response


def process_job(worker, run):
    from .app_jobs import lock_live, state_write, stop_state
    require(worker.s.mode == "mock" and not worker.s.live_enabled, "Local records are NoModel engineering only")
    limits = Limits(**{k: getattr(worker.s, k) for k in Limits.model_fields})
    with worker.store.tx() as c:
        job = lock_live(worker.store, c, run)
        i, release, job, a, snapshot, frozen = accepted_binding(worker.store, c, job["principal_id"], job["id"], limits)
        if job["status"] != "RUNNING" or worker.stop.is_set():
            state_write(worker.store, c, job, a["id"], stop_state(job, False))
            return
        deadline = job["created_at"] + min(worker.s.run_seconds,
            release["snapshot"]["definition"]["candidate"]["manifest"]["runtime_limits"]["run_seconds"])
        require(time.time() < deadline, "Original record Run deadline ended")
        require(i["revision"] == snapshot["expected_revision"] and i["data_version"] == snapshot["expected_data_version"]
            and time.time() < frozen["expires_at"], "Record version or original preview expired")
        records, history = projection(worker.store, c, job["principal_id"], i, limits)
        current = {r["record_id"]: r for r in records}
        event = frozen["event"]
        apply_event(current, event, history[-1]["event_fingerprint"] if history else None, i["data_version"] + 1, i)
        args = dict(text=canonical(event))
        action = validate_action(canonical(release["snapshot"]["definition"]["candidate"]["actions"][0]))
        validate_action_input(action, args)
        require(not c.execute(select(operations.c.id).where(operations.c.run_id == job["id"])).first())
        oid = new_id("op")
        intent = dict(tool="artifact.save_text", args=args)
        c.execute(insert(operations).values(id=oid, run_id=job["id"], call_id="record_event", fingerprint=fingerprint(intent),
            tool_ref="artifact.save_text", status="PREPARED"))
        c.execute(insert(operation_intents).values(operation_id=oid, request=intent))
        from . import record_preview_storage as private
        preview_context = private.target(i, job, oid)
        # Same transaction as the event and CAS; never dispatch's separate transaction.
        output = write_text_artifact(worker.store, c, job["principal_id"], i["runtime_id"], i["project_id"],
            args["text"], artifact_format="json", preview_context=preview_context)
        c.execute(insert(local_effects).values(operation_id=oid, resource_id=output["resource_id"], content_hash=output["hash"]))
        receipt = dict(operation_id=oid, status="VERIFIED", data=output, artifact_refs=[output["resource_id"]],
            receipt_ref=oid, check_results=[dict(check="receipt.readback.v1", status="PASS")], usage_ref=None, error=None)
        c.execute(update(operations).where(operations.c.id == oid).values(status="VERIFIED", receipt=receipt))
        data, version = dict(result=output, release_ref=release["id"]), i["data_version"] + 1
        validate_value(release["snapshot"]["data_schema"], data)
        c.execute(insert(typed).values(instance_id=i["id"], version=version, run_id=a["id"], release_id=release["id"],
            schema_version=1, data=data, fingerprint=fingerprint(data)))
        require(c.execute(update(instances).where(instances.c.id == i["id"], instances.c.revision == i["revision"],
            instances.c.data_version == i["data_version"], instances.c.release_id == release["id"]).values(data_version=version)).rowcount == 1)
        # Current authority, real readback and live fence before terminal commit.
        if preview_context is not None:
            private.artifact(worker.store, c, job["principal_id"], i, output["resource_id"])
        else:
            worker.store.authorize(c, job["principal_id"], i["runtime_id"], i["project_id"], output["resource_id"], "resource.read")
        op = c.execute(select(operations).where(operations.c.id == oid)).mappings().one()
        status, readback = reconcile_readback(worker.store, c, job, op, preview_context=preview_context)
        require(status == "VERIFIED" and fingerprint(readback) == fingerprint(receipt))
        guarded = worker.store.guard(c, job["id"], run["fence"])
        require(guarded["status"] == "RUNNING" and not guarded["cancel_intent"] and not worker.stop.is_set()
            and time.time() < min(deadline, frozen["expires_at"]), "Original record commit interval ended")
        c.execute(update(app_runs).where(app_runs.c.id == a["id"]).values(status="SUCCEEDED", output=output, result_version=version, error=None))
        c.execute(update(runs).where(runs.c.id == job["id"]).values(status="SUCCEEDED", version=job["version"] + 1,
            lease_until=0, result=run_result(i, a, event, output, version), error=None, context={**job["context"], "tools": 1}))
        worker.store.event(c, job["id"], "LOCAL_RECORD_COMMITTED", dict(instance_id=i["id"], app_run_id=a["id"],
            artifact_resource=output["resource_id"], event_fingerprint=fingerprint(event), result_version=version))
        worker.store.event(c, job["id"], "TOOL_VERIFIED", dict(operation_id=oid, tool_ref="artifact.save_text"))
        worker.store.event(c, job["id"], "STATE", dict(status="SUCCEEDED"))


def fail_job(worker, run, error):
    from .app_jobs import state_write, stop_state
    with worker.store.tx() as c:
        _, _, aid = scope_job(worker.store, c, run["principal_id"], run["id"])
        job = c.execute(select(runs.c.id, runs.c.fence, runs.c.status, runs.c.cancel_intent,
            runs.c.version).where(runs.c.id == run["id"])).mappings().one()
        if job["fence"] != run["fence"] or job["status"] in TERMINAL:
            return
        state = stop_state(job, False) if job["cancel_intent"] or job["status"] == "PAUSE_REQUESTED" else "FAILED"
        state_write(worker.store, c, job, aid, state, error.public() if state == "FAILED" else None)


def reject_queued_scope(store, c, rid, error):
    from .app_jobs import state_write
    user = c.execute(select(runs.c.principal_id).where(runs.c.id == rid)).scalar_one()
    _, _, aid = scope_job(store, c, user, rid)
    row = c.execute(select(runs.c.id, runs.c.status, runs.c.version, runs.c.cancel_intent)
        .where(runs.c.id == rid)).mappings().one()
    if row["status"] == "QUEUED":
        state_write(store, c, row, aid, "FAILED", error.public())


def inspect_instance(store, user, iid, limits):
    with store.tx() as c:
        i, release = instance_header(store, c, user, iid)
        records, history = projection(store, c, user, i, limits)
        result_runs = []
        for row in c.execute(select(bindings.c.run_id).join(app_runs, app_runs.c.id == bindings.c.app_run_id)
                .where(app_runs.c.instance_id == iid)).mappings():
            _, _, job, a, _, _ = accepted_binding(store, c, user, row["run_id"], limits)
            result_runs.append(dict(id=job["id"], app_run_id=a["id"], status=job["status"], version=job["version"], result_version=a["result_version"]))
        return dict(namespace=VERSION, **i, release_fingerprint=release["fingerprint"], records=records, history=history,
            runs=result_runs, **{k:v for k,v in execution_scope(i).items() if k != "preview_scope"}, formal_publication_enabled=False)


def inspect_job(store, user, iid, rid, limits):
    with store.tx() as c:
        return _inspect_job(store, c, user, iid, rid, limits)


def _inspect_job(store, c, user, iid, rid, limits):
    i, _, _ = scope_job(store, c, user, rid, iid)
    _, history = projection(store, c, user, i, limits)
    _, release, job, a, _, _ = accepted_binding(store, c, user, rid, limits)
    value = next((v for v in history if v["run_id"] == rid), None)
    op = c.execute(select(operations.c.receipt).where(operations.c.run_id == rid)).scalar_one_or_none()
    return dict(namespace=VERSION, instance_id=iid, id=rid, app_run_id=a["id"], release_id=release["id"],
        status=job["status"], version=job["version"], result_version=a["result_version"], output=a["output"],
        event=value["event"] if value else None, receipt=op, error=job["error"], **execution_scope(i), formal_publication_enabled=False)


def inspect_project_run(store, user, rid, limits):
    """Typed history read; legacy execution/commands remain closed to this family."""
    with store.tx() as c:
        i, release, aid = scope_job(store, c, user, rid)
        result = _inspect_job(store, c, user, i["id"], rid, limits)
        require(result["id"] == rid and result["instance_id"] == i["id"]
            and result["release_id"] == release["id"] and result["app_run_id"] == aid)
        return dict(result, principal_id=user, project_id=i["project_id"], app_id=i["source_app_id"])


def private_control_metadata(store, user, iid, rid):
    """Owned, anchored stop metadata; never projects result or private content."""
    with store.tx() as c:
        i, _, _ = scope_job(store, c, user, rid, iid)
        if "preview_scope" not in i:
            raise DomainError("PERMISSION_DENIED")
        row = c.execute(select(runs.c.status, runs.c.version).where(runs.c.id == rid)).mappings().one()
        return dict(namespace=VERSION, id=rid, instance_id=iid, principal_id=user,
            project_id=i["project_id"], app_id=i["source_app_id"], runtime_id=i["runtime_id"],
            release_id=i["release_id"], status=row["status"], version=row["version"],
            content_access=False, execution_namespace=i["preview_scope"]["namespace"],
            preview_scope_fingerprint=i["preview_scope"]["fingerprint"], formal_publication_enabled=False)


def control(store, user, iid, rid, body, limits):
    with store.tx() as c:
        i, _, aid = scope_job(store, c, user, rid, iid)
        if body["command"] == "resume":
            projection(store, c, user, i, limits)
        row = c.execute(select(runs.c.id, runs.c.status, runs.c.version, runs.c.cancel_intent,
            runs.c.lease_until).where(runs.c.id == rid).with_for_update()).mappings().one()
        require(row["version"] == body["version"])
        state = row["status"]
        if body["command"] == "cancel" and state not in TERMINAL:
            state = "CANCEL_REQUESTED" if state in {"RUNNING", "PAUSE_REQUESTED"} else "CANCELLED"
        elif body["command"] == "pause" and state in {"QUEUED", "RUNNING"}:
            state = "PAUSE_REQUESTED" if state == "RUNNING" else "PAUSED"
        elif body["command"] == "resume" and state == "PAUSED" and not row["cancel_intent"]:
            state = "QUEUED"
        else:
            raise DomainError("VERSION_CONFLICT")
        # Preserve the active lease, like the original command controller. The
        # fenced worker alone completes an in-flight pause/cancel transition.
        c.execute(update(runs).where(runs.c.id == rid).values(status=state,
            version=row["version"] + 1,
            cancel_intent=row["cancel_intent"] or body["command"] == "cancel"))
        c.execute(update(app_runs).where(app_runs.c.id == aid).values(status=state))
        store.event(c, rid, "COMMAND", dict(command=body["command"], status=state))
        return dict(namespace=VERSION, id=rid, status=state, version=row["version"] + 1,
            content_access=False, formal_publication_enabled=False)


def mount(app, store, limits, identity):
    user_dependency = Depends(identity)

    @app.post("/api/projects/{pid}/record-apps", status_code=201)
    def post_app(pid: str, body: CreateApp, user=user_dependency):
        return create_app(store, user, pid, body.model_dump(), limits)

    @app.get("/api/projects/{pid}/record-app-requests/{key}")
    def app_request(pid: str, key: str, user=user_dependency):
        with store.tx() as c:
            store.own_project(c, user, pid)
            saved = pair(c, user, pid, CREATE, key)
            if not saved:
                raise DomainError("OUTCOME_UNKNOWN")
            value = checked_app(store, c, user, saved["response"]["id"], limits)
            return {**public_app(value), "request_key": key, "request_fingerprint": fingerprint(saved["request"])}

    @app.get("/api/apps/{aid}/record-delivery")
    def delivery(aid: str, user=user_dependency):
        with store.tx() as c:
            value = checked_app(store, c, user, aid, limits)
            rs = c.execute(select(releases.c.id).where(releases.c.principal_id == user,
                releases.c.snapshot["namespace"].as_string() == VERSION,
                releases.c.snapshot["app_id"].as_string() == aid)).scalars().all()
            rels = [release_metadata(read_release(store, c, user, rid, limits)) for rid in rs]
            ii = c.execute(select(instances.c.id).where(instances.c.principal_id == user,
                instances.c.source_app_id == aid)).scalars().all()
            headers = [instance_header(store, c, user, iid)[0] for iid in ii]
            return dict(namespace=VERSION, app_id=aid, definition_fingerprint=fingerprint(value), releases=rels,
                instances=[i for i in headers if "preview_scope" not in i],
                preview_instances=[i for i in headers if "preview_scope" in i], formal_publication_enabled=False)

    @app.post("/api/apps/{aid}/record-release-approvals", status_code=201)
    def post_release(aid: str, body: ReleaseInput, user=user_dependency):
        return prepare_release(store, user, aid, body.model_dump(), limits)

    @app.get("/api/apps/{aid}/record-release-requests/{key}")
    def get_release_request(aid: str, key: str, user=user_dependency):
        with store.tx() as c:
            return release_request(store, c, user, aid, key, limits)

    @app.post("/api/apps/{aid}/record-release-requests/{key}/commit")
    def post_commit_release(aid: str, key: str, body: CommitRelease, user=user_dependency):
        return commit_release(store, user, aid, key, body.model_dump(), limits)

    @app.post("/api/internal/record-releases/{rid}/instances", status_code=201)
    def post_instance(rid: str, body: InstanceInput, user=user_dependency):
        return create_instance(store, user, rid, body.model_dump(), limits)

    @app.get("/api/internal/record-releases/{rid}/instance-requests/{key}")
    def get_instance_request(rid: str, key: str, user=user_dependency):
        with store.tx() as c:
            read_release(store, c, user, rid, limits)
            saved = pair(c, user, rid, INSTANCE, key)
            if not saved:
                raise DomainError("OUTCOME_UNKNOWN")
            row, _ = instance_header(store, c, user, saved["response"]["id"])
            return dict(namespace=VERSION, request_key=key, request_fingerprint=fingerprint(saved["request"]),
                instance=row, formal_publication_enabled=False)

    @app.get("/api/internal/record-instances/{iid}")
    def get_instance(iid: str, user=user_dependency):
        return inspect_instance(store, user, iid, limits)

    @app.post("/api/internal/record-instances/{iid}/previews", status_code=201)
    def post_preview(iid: str, body: Annotated[CreateRecord | SetState, Field(discriminator="command")], user=user_dependency):
        return preview(store, user, iid, body.model_dump(), limits)

    @app.get("/api/internal/record-instances/{iid}/record-requests/{key}")
    def get_request(iid: str, key: str, user=user_dependency):
        with store.tx() as c:
            return request_state(store, c, user, iid, key, limits)

    @app.post("/api/internal/record-instances/{iid}/previews/{key}/commit", status_code=202)
    def post_confirm(iid: str, key: str, body: Confirm, user=user_dependency):
        return confirm(store, user, iid, key, body.model_dump(), limits)

    @app.get("/api/internal/record-instances/{iid}/runs/{rid}")
    def get_job(iid: str, rid: str, user=user_dependency):
        return inspect_job(store, user, iid, rid, limits)

    @app.get("/api/internal/record-instances/{iid}/runs/{rid}/private-control-status")
    def get_private_control(iid: str, rid: str, user=user_dependency):
        return private_control_metadata(store, user, iid, rid)

    @app.post("/api/internal/record-instances/{iid}/runs/{rid}/commands")
    def post_control(iid: str, rid: str, body: Control, user=user_dependency):
        return control(store, user, iid, rid, body.model_dump(), limits)

    from . import record_preview_storage
    record_preview_storage.mount(app, store, limits, identity)
