"""Internal synthetic F2-T08 services; intentionally not wired to HTTP/publication.

Existing principals/grants only; typed result-ledger data, no arbitrary business writes.
"""

import copy
import time

from sqlalchemy import insert, select, update

from .apps import load_draft, validate_frozen_candidate
from .contracts import schema_check, validate_action_input, validate_value
from .db import (
    fingerprint,
    grants,
    internal_app_runs,
    internal_approvals,
    internal_instance_data,
    internal_instances,
    internal_releases,
    new_id,
)
from .errors import DomainError
from .extraction import exact_sum_oracle
from .tools import authorized_read

NAMESPACE = "INTERNAL_ENGINEERING_ONLY"


def grant_version(c, project, user):
    # Conservatively invalidates approval on any same-project grant revision/change.
    return fingerprint(
        [
            dict(r)
            for r in c.execute(
                select(grants)
                .where(grants.c.project_id == project, grants.c.principal_id != "")
                .order_by(grants.c.id)
            ).mappings()
        ]
    )


def execute(store, c, user, draft, limits, input_value):
    _, manifest, action, _ = validate_frozen_candidate(store, c, user, draft, limits)
    validate_value(manifest.input_schema, input_value)
    rid = manifest.data_bindings[0].resource_ref
    args = {"resource_id": rid, **input_value}
    validate_action_input(action, args)
    source = authorized_read(
        store,
        c,
        user,
        draft["runtime_id"],
        draft["project_id"],
        "resource.read",
        {"resource_id": rid},
    )
    value = authorized_read(
        store, c, user, draft["runtime_id"], draft["project_id"], action.executor.ref, args
    )
    validate_value(action.output_schema, value, "action_output")
    output = {field: value[ref.field] for field, ref in manifest.outputs.items()}
    validate_value(manifest.output_schema, output, "output")
    exact_sum_oracle(source["content"], input_value["column"], output)
    return output


def record_schema(candidate, schema=None):
    expected = candidate["manifest"]["output_schema"]
    schema = copy.deepcopy(
        schema
        or {
            "type": "object",
            "properties": {"result": expected},
            "required": ["result"],
            "additionalProperties": False,
        }
    )
    schema_check(schema)
    if (
        schema.get("type") != "object"
        or set(schema) - {"type", "properties", "required", "additionalProperties"}
        or schema.get("additionalProperties") is not False
        or schema.get("properties", {}).get("result") != expected
        or "result" not in schema.get("required", [])
        or set(schema.get("properties", {})) - {"result", "release_ref"}
        or (
            "release_ref" in schema["properties"]
            and schema["properties"]["release_ref"] != {"type": "string"}
        )
    ):
        raise DomainError(
            "INVALID_MANIFEST", "Only typed result records and release metadata supported"
        )
    return schema


def new_approval(c, user, pid, kind, payload):
    aid = new_id("iapproval")
    expiry = time.time() + 300
    payload = {
        **payload,
        "approval_id": aid,
        "principal_id": user,
        "project_id": pid,
        "kind": kind,
        "expires_at": expiry,
    }
    fp = fingerprint(payload)
    c.execute(
        insert(internal_approvals).values(
            id=aid,
            principal_id=user,
            project_id=pid,
            kind=kind,
            payload=payload,
            fingerprint=fp,
            expires_at=expiry,
            consumed=False,
        )
    )
    return {
        "id": aid,
        "fingerprint": fp,
        "namespace": NAMESPACE,
        "formal_publication_enabled": False,
    }


def approval(c, user, aid, fp, kind, *, allow_consumed=False):
    row = (
        c.execute(
            select(internal_approvals).where(internal_approvals.c.id == aid).with_for_update()
        )
        .mappings()
        .first()
    )
    if not row or row["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    p = row["payload"]
    if (
        row["kind"] != kind
        or p["kind"] != kind
        or p["approval_id"] != aid
        or p["principal_id"] != user
        or p["project_id"] != row["project_id"]
        or row["expires_at"] != p["expires_at"]
        or fp != row["fingerprint"]
        or fingerprint(p) != fp
    ):
        raise DomainError("VERSION_CONFLICT", "Exact approval changed")
    if not (allow_consumed and row["consumed"]) and (
        row["consumed"] or row["expires_at"] <= time.time()
    ):
        raise DomainError("VERSION_CONFLICT", "Approval consumed or expired")
    return row


def prepare_release(
    store,
    user,
    aid,
    expected_draft_fp,
    limits,
    sample_input,
    *,
    data_schema=None,
    data_schema_version=1,
):
    if type(data_schema_version) is not int or data_schema_version < 1:
        raise DomainError("INVALID_INPUT")
    with store.tx() as c:
        # Locate only, then project before app/grant locks.
        from .db import app_drafts

        pid = c.execute(select(app_drafts.c.project_id).where(app_drafts.c.id == aid)).scalar()
        if not pid:
            raise DomainError("PERMISSION_DENIED")
        store.lock_project(c, user, pid)
        draft, _, _, report = load_draft(store, c, user, aid, limits, lock=True)
        if draft["fingerprint"] != expected_draft_fp:
            raise DomainError("VERSION_CONFLICT")
        output = execute(store, c, user, draft, limits, sample_input)
        frozen = {
            k: copy.deepcopy(draft[k])
            for k in ["id", "project_id", "runtime_id", "candidate", "fingerprint"]
        }
        snapshot = {
            "namespace": NAMESPACE,
            "draft": frozen,
            "dependency_lock": copy.deepcopy(draft["candidate"]["manifest"]["dependency_lock"]),
            "data_schema": record_schema(draft["candidate"], data_schema),
            "data_schema_version": data_schema_version,
            "check_evidence": {
                "ref": "csv.exact_integer_sum.v1",
                "status": "PASS",
                "candidate_fingerprint": expected_draft_fp,
                "input_fingerprint": fingerprint(sample_input),
                "output_fingerprint": fingerprint(output),
                "plan_fingerprint": fingerprint(report),
            },
            "model_requests": 0,
            "formal_publication_enabled": False,
        }
        return new_approval(
            c,
            user,
            pid,
            "release",
            {"snapshot": snapshot, "grant_version": grant_version(c, pid, user)},
        )


def commit_release(store, user, approval_id, exact_fp, limits):
    with store.tx() as c:
        location = c.execute(
            select(internal_approvals.c.project_id).where(internal_approvals.c.id == approval_id)
        ).scalar()
        store.lock_project(c, user, location)
        a = approval(c, user, approval_id, exact_fp, "release", allow_consumed=True)
        old = (
            c.execute(
                select(internal_releases).where(internal_releases.c.approval_id == approval_id)
            )
            .mappings()
            .first()
        )
        if old:
            return dict(read_release(store, c, user, old["id"], limits))
        p = a["payload"]
        snap = p["snapshot"]
        draft = snap["draft"]
        current, _, _, _ = load_draft(store, c, user, draft["id"], limits, lock=True)
        validate_source_bytes(store, c, user, current)
        if (
            current["fingerprint"] != draft["fingerprint"]
            or grant_version(c, location, user) != p["grant_version"]
        ):
            raise DomainError("VERSION_CONFLICT", "Source or grant precondition changed")
        rid = new_id("irelease")
        row = {
            "id": rid,
            "project_id": location,
            "principal_id": user,
            "approval_id": approval_id,
            "snapshot": snap,
            "fingerprint": fingerprint(snap),
        }
        c.execute(insert(internal_releases).values(**row))
        c.execute(
            update(internal_approvals)
            .where(internal_approvals.c.id == approval_id)
            .values(consumed=True)
        )
        return row


def validate_source_bytes(store, c, user, draft):
    # Read through the same gateway: metadata hashes alone cannot attest current bytes.
    rid = draft["candidate"]["manifest"]["data_bindings"][0]["resource_ref"]
    authorized_read(
        store,
        c,
        user,
        draft["runtime_id"],
        draft["project_id"],
        "resource.read",
        {"resource_id": rid},
    )


def read_release(store, c, user, rid, limits):
    r = c.execute(select(internal_releases).where(internal_releases.c.id == rid)).mappings().first()
    if not r or r["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    store.own_project(c, user, r["project_id"])
    a = (
        c.execute(select(internal_approvals).where(internal_approvals.c.id == r["approval_id"]))
        .mappings()
        .first()
    )
    if (
        not a
        or not a["consumed"]
        or a["kind"] != "release"
        or a["principal_id"] != user
        or a["project_id"] != r["project_id"]
        or fingerprint(a["payload"]) != a["fingerprint"]
        or a["payload"]["snapshot"] != r["snapshot"]
        or fingerprint(r["snapshot"]) != r["fingerprint"]
    ):
        raise DomainError("VERSION_CONFLICT", "Immutable release/approval mismatch")
    s = r["snapshot"]
    draft = s["draft"]
    if (
        s["namespace"] != NAMESPACE
        or s["formal_publication_enabled"] is not False
        or draft["project_id"] != r["project_id"]
        or s["dependency_lock"] != draft["candidate"]["manifest"]["dependency_lock"]
    ):
        raise DomainError("VERSION_CONFLICT")
    record_schema(draft["candidate"], s["data_schema"])
    validate_frozen_candidate(store, c, user, draft, limits)
    validate_source_bytes(store, c, user, draft)
    return r


def create_instance(store, user, rid, expected_release_fp, limits):
    with store.tx() as c:
        location = c.execute(
            select(internal_releases.c.project_id).where(internal_releases.c.id == rid)
        ).scalar()
        store.lock_project(c, user, location)
        r = read_release(store, c, user, rid, limits)
        if r["fingerprint"] != expected_release_fp:
            raise DomainError("VERSION_CONFLICT")
        draft = r["snapshot"]["draft"]
        iid = new_id("iinstance")
        row = {
            "id": iid,
            "project_id": location,
            "principal_id": user,
            "source_app_id": draft["id"],
            "runtime_id": draft["runtime_id"],
            "release_id": rid,
            "revision": 1,
            "data_version": 0,
            "history": [{"revision": 1, "release_id": rid, "kind": "created"}],
        }
        c.execute(insert(internal_instances).values(**row))
        return row


def instance(store, c, user, iid, limits, *, lock=False):
    q = select(internal_instances).where(internal_instances.c.id == iid)
    i = c.execute(q.with_for_update() if lock else q).mappings().first()
    if not i or i["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    r = read_release(store, c, user, i["release_id"], limits)
    if (
        r["project_id"] != i["project_id"]
        or r["snapshot"]["draft"]["id"] != i["source_app_id"]
        or r["snapshot"]["draft"]["runtime_id"] != i["runtime_id"]
    ):
        raise DomainError("VERSION_CONFLICT")
    return i, r


def data_rows(c, iid):
    rows = (
        c.execute(
            select(internal_instance_data)
            .where(internal_instance_data.c.instance_id == iid)
            .order_by(internal_instance_data.c.version)
        )
        .mappings()
        .all()
    )
    for row in rows:
        run = (
            c.execute(select(internal_app_runs).where(internal_app_runs.c.id == row["run_id"]))
            .mappings()
            .first()
        )
        if (
            fingerprint(row["data"]) != row["fingerprint"]
            or not run
            or run["instance_id"] != iid
            or run["release_id"] != row["release_id"]
            or run["result_version"] != row["version"]
            or run["status"] != "SUCCEEDED"
            or run["output"] != row["data"]["result"]
        ):
            raise DomainError("VERSION_CONFLICT", "Instance result lineage changed")
    return rows


def inspect_instance(store, user, iid, limits):
    with store.tx() as c:
        i, _ = instance(store, c, user, iid, limits)
        return {**dict(i), "namespace": NAMESPACE, "data": [dict(x) for x in data_rows(c, iid)]}


def run_instance(
    store, user, iid, expected_revision, expected_release_fp, input_value, key, limits
):
    if not isinstance(key, str) or not 1 <= len(key) <= 100:
        raise DomainError("INVALID_INPUT")
    with store.tx() as c:
        pid = c.execute(
            select(internal_instances.c.project_id).where(internal_instances.c.id == iid)
        ).scalar()
        store.lock_project(c, user, pid)
        i, r = instance(store, c, user, iid, limits, lock=True)
        request_fp = fingerprint(
            {
                "instance_id": iid,
                "expected_revision": expected_revision,
                "expected_release_fp": expected_release_fp,
                "input": input_value,
            }
        )
        old = (
            c.execute(
                select(internal_app_runs).where(
                    internal_app_runs.c.instance_id == iid,
                    internal_app_runs.c.principal_id == user,
                    internal_app_runs.c.request_key == key,
                )
            )
            .mappings()
            .first()
        )
        if old:
            if old["fingerprint"] != request_fp:
                raise DomainError("VERSION_CONFLICT")
            read_release(store, c, user, old["release_id"], limits)
            return {**dict(old), "namespace": "INTERNAL_APPRUN", "cached": True}
        if i["revision"] != expected_revision or r["fingerprint"] != expected_release_fp:
            raise DomainError("VERSION_CONFLICT")
        output, error, version = None, None, None
        try:
            output = execute(store, c, user, r["snapshot"]["draft"], limits, input_value)
            data = {"result": output}
            if "release_ref" in r["snapshot"]["data_schema"]["properties"]:
                data["release_ref"] = r["id"]
            validate_value(r["snapshot"]["data_schema"], data, "instance_record")
        except DomainError as exc:
            output = None
            error = exc.public()
        run_id = new_id("iapprun")
        if error is None:
            version = i["data_version"] + 1
            c.execute(
                insert(internal_instance_data).values(
                    instance_id=iid,
                    version=version,
                    run_id=run_id,
                    release_id=r["id"],
                    schema_version=r["snapshot"]["data_schema_version"],
                    data=data,
                    fingerprint=fingerprint(data),
                )
            )
            c.execute(
                update(internal_instances)
                .where(
                    internal_instances.c.id == iid,
                    internal_instances.c.revision == expected_revision,
                    internal_instances.c.data_version == i["data_version"],
                )
                .values(data_version=version)
            )
        row = {
            "id": run_id,
            "instance_id": iid,
            "release_id": r["id"],
            "principal_id": user,
            "request_key": key,
            "fingerprint": request_fp,
            "input": input_value,
            "status": "FAILED" if error else "SUCCEEDED",
            "output": output,
            "error": error,
            "result_version": version,
        }
        c.execute(insert(internal_app_runs).values(**row))
        return {**row, "namespace": "INTERNAL_APPRUN", "cached": False}


def compatible(old, new):
    old_props, new_props = old["properties"], new["properties"]
    if (
        set(old_props) - set(new_props)
        or any(new_props[k] != v for k, v in old_props.items())
        or set(new["required"]) - set(old["required"])
    ):
        raise DomainError(
            "VERSION_CONFLICT", "Incompatible instance schema; no destructive migration"
        )


def prepare_switch(store, user, iid, target_id, expected_revision, limits):
    with store.tx() as c:
        pid = c.execute(
            select(internal_instances.c.project_id).where(internal_instances.c.id == iid)
        ).scalar()
        store.lock_project(c, user, pid)
        i, old = instance(store, c, user, iid, limits, lock=True)
        target = read_release(store, c, user, target_id, limits)
        if i["revision"] != expected_revision:
            raise DomainError("VERSION_CONFLICT")
        if (
            target["project_id"] != pid
            or target["snapshot"]["draft"]["id"] != i["source_app_id"]
            or target["snapshot"]["draft"]["runtime_id"] != i["runtime_id"]
        ):
            raise DomainError(
                "PERMISSION_DENIED", "Cannot switch another app/runtime into this instance"
            )
        compatible(old["snapshot"]["data_schema"], target["snapshot"]["data_schema"])
        same_schema = target["snapshot"]["data_schema"] == old["snapshot"]["data_schema"]
        old_version = old["snapshot"]["data_schema_version"]
        target_version = target["snapshot"]["data_schema_version"]
        if (same_schema and target_version != old_version) or (
            not same_schema and target_version <= old_version
        ):
            raise DomainError("VERSION_CONFLICT", "Unknown data version transition")
        records = data_rows(c, iid)
        for record in records:
            validate_value(target["snapshot"]["data_schema"], record["data"], "retained_data")
        return new_approval(
            c,
            user,
            pid,
            "switch",
            {
                "instance_id": iid,
                "from_release_id": old["id"],
                "target_release_id": target_id,
                "target_fingerprint": target["fingerprint"],
                "revision": expected_revision,
                "data_version": i["data_version"],
                "data_fingerprint": fingerprint([dict(x) for x in records]),
                "grant_version": grant_version(c, pid, user),
            },
        )


def commit_switch(store, user, approval_id, exact_fp, limits):
    with store.tx() as c:
        pid = c.execute(
            select(internal_approvals.c.project_id).where(internal_approvals.c.id == approval_id)
        ).scalar()
        store.lock_project(c, user, pid)
        a = approval(c, user, approval_id, exact_fp, "switch")
        p = a["payload"]
        i, old = instance(store, c, user, p["instance_id"], limits, lock=True)
        target = read_release(store, c, user, p["target_release_id"], limits)
        if (
            i["revision"] != p["revision"]
            or i["release_id"] != p["from_release_id"]
            or i["data_version"] != p["data_version"]
            or target["fingerprint"] != p["target_fingerprint"]
            or grant_version(c, pid, user) != p["grant_version"]
            or fingerprint([dict(x) for x in data_rows(c, i["id"])]) != p["data_fingerprint"]
        ):
            raise DomainError("VERSION_CONFLICT", "Switch preconditions changed")
        compatible(old["snapshot"]["data_schema"], target["snapshot"]["data_schema"])
        history = [
            *i["history"],
            {
                "revision": i["revision"] + 1,
                "release_id": target["id"],
                "previous_release_id": old["id"],
                "approval_id": approval_id,
                "kind": "switch",
            },
        ]
        c.execute(
            update(internal_instances)
            .where(
                internal_instances.c.id == i["id"], internal_instances.c.revision == p["revision"]
            )
            .values(release_id=target["id"], revision=i["revision"] + 1, history=history)
        )
        c.execute(
            update(internal_approvals)
            .where(internal_approvals.c.id == approval_id)
            .values(consumed=True)
        )
        return {
            "instance_id": i["id"],
            "release_id": target["id"],
            "revision": i["revision"] + 1,
            "data_version": i["data_version"],
            "namespace": NAMESPACE,
        }
