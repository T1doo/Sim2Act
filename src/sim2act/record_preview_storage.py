"""Private storage target for the existing local-record writer, never a new tool.

The original Worker/Operation/typed CAS remain in charge. This target stores
actual artifacts in app_previews and creates no project resource or Grant.
"""

import hashlib
import time
from dataclasses import dataclass

from fastapi import Depends
from sqlalchemy import insert, select

from .db import app_previews, fingerprint, local_effects, new_id, operation_intents, operations
from .errors import DomainError

NAMESPACE = "local-record-private-preview.v1"
INSTANCE = NAMESPACE + ".instance"


def require(ok, message="Private preview scope or stored artifact changed"):
    if not ok:
        raise DomainError("VERSION_CONFLICT", message)


def scope(i, release, request):
    value = dict(
        namespace=NAMESPACE,
        instance_id=i["id"],
        principal_id=i["principal_id"],
        project_id=i["project_id"],
        app_id=i["source_app_id"],
        runtime_id=i["runtime_id"],
        release_id=i["release_id"],
        release_fingerprint=release["fingerprint"],
        creation_request_fingerprint=fingerprint(request),
    )
    return {**value, "fingerprint": fingerprint(value)}


@dataclass(frozen=True)
class Target:
    instance_id: str
    run_id: str
    operation_id: str
    scope_fingerprint: str
    fence: int


def target(i, run, oid):
    if "preview_scope" not in i:
        return None
    return Target(i["id"], run["id"], oid, i["preview_scope"]["fingerprint"], run["fence"])


def exposure(i):
    return (
        dict(execution_namespace=NAMESPACE, preview_scope=i["preview_scope"])
        if "preview_scope" in i
        else {}
    )


def owned(store, c, user, i):
    from . import local_record_apps as records

    fresh, _ = records.instance_header(store, c, user, i["id"])
    require("preview_scope" in fresh and fresh["preview_scope"] == i.get("preview_scope"))
    store.authorize(
        c, user, fresh["runtime_id"], fresh["project_id"], fresh["project_id"], "artifact.save_text"
    )
    return fresh


def metadata(i, rid, oid):
    return dict(
        namespace=NAMESPACE,
        scope_fingerprint=i["preview_scope"]["fingerprint"],
        instance_id=i["id"],
        run_id=rid,
        operation_id=oid,
        project_id=i["project_id"],
        principal_id=i["principal_id"],
        runtime_id=i["runtime_id"],
        app_id=i["source_app_id"],
        release_id=i["release_id"],
    )


def artifact(store, c, user, i, resource_id):
    """Authority and scalar binding precede the private content projection."""
    from . import local_record_apps as records

    i = owned(store, c, user, i)
    header = (
        c.execute(
            select(
                app_previews.c.id,
                app_previews.c.app_id,
                app_previews.c.principal_id,
                app_previews.c.request_key,
                app_previews.c.input,
                app_previews.c.fingerprint,
                app_previews.c.status,
                app_previews.c.output["hash"].as_string().label("hash"),
            ).where(app_previews.c.id == resource_id)
        )
        .mappings()
        .first()
    )
    if header is None:
        raise DomainError("PERMISSION_DENIED")
    m = header["input"]
    require(
        isinstance(m, dict)
        and m.get("namespace") == NAMESPACE
        and m.get("instance_id") == i["id"]
        and m.get("scope_fingerprint") == i["preview_scope"]["fingerprint"]
    )
    actual, _, _ = records.scope_job(store, c, user, m["run_id"], i["id"])
    require(
        actual["preview_scope"] == i["preview_scope"]
        and m == metadata(i, m["run_id"], m["operation_id"])
        and header["app_id"] == i["source_app_id"]
        and header["principal_id"] == user
        and header["request_key"] == m["operation_id"]
        and header["status"] == "SUCCEEDED"
        and header["fingerprint"] == fingerprint(dict(scope=m, hash=header["hash"]))
    )
    op = (
        c.execute(
            select(operations.c.run_id, operations.c.tool_ref, operations.c.status).where(
                operations.c.id == m["operation_id"]
            )
        )
        .mappings()
        .first()
    )
    effect = (
        c.execute(select(local_effects).where(local_effects.c.operation_id == m["operation_id"]))
        .mappings()
        .first()
    )
    require(
        op is not None
        and op["run_id"] == m["run_id"]
        and op["tool_ref"] == "artifact.save_text"
        and op["status"] == "VERIFIED"
        and effect is not None
        and effect["resource_id"] == resource_id
        and effect["content_hash"] == header["hash"]
    )
    output = c.execute(
        select(app_previews.c.output).where(app_previews.c.id == resource_id)
    ).scalar_one()
    require(
        isinstance(output, dict)
        and set(output) == {"content", "hash", "format"}
        and output["format"] == "json"
        and isinstance(output["content"], str)
        and output["hash"]
        == header["hash"]
        == hashlib.sha256(output["content"].encode()).hexdigest()
    )
    return dict(
        id=resource_id, project_id=i["project_id"], name="Private record preview.json", **output
    )


def write(store, c, user, runtime, pid, content, context):
    from . import local_record_apps as records

    require(type(context) is Target)
    i, _, _ = records.scope_job(store, c, user, context.run_id, context.instance_id)
    i = owned(store, c, user, i)
    require(
        i["runtime_id"] == runtime
        and i["project_id"] == pid
        and i["preview_scope"]["fingerprint"] == context.scope_fingerprint
    )
    run = store.guard(c, context.run_id, context.fence)
    require(
        run["status"] == "RUNNING"
        and run["principal_id"] == user
        and run["runtime_id"] == runtime
        and run["project_id"] == pid
        and not run["cancel_intent"]
    )
    op = (
        c.execute(select(operations).where(operations.c.id == context.operation_id))
        .mappings()
        .one()
    )
    intent = c.execute(
        select(operation_intents.c.request).where(
            operation_intents.c.operation_id == context.operation_id
        )
    ).scalar_one()
    require(
        op["run_id"] == run["id"]
        and op["tool_ref"] == "artifact.save_text"
        and op["status"] == "PREPARED"
        and intent == dict(tool="artifact.save_text", args=dict(text=content))
        and fingerprint(intent) == op["fingerprint"]
    )
    require(
        not c.execute(
            select(app_previews.c.id).where(
                app_previews.c.app_id == i["source_app_id"],
                app_previews.c.principal_id == user,
                app_previews.c.request_key == context.operation_id,
            )
        ).first()
    )
    rid = new_id("res")
    digest = hashlib.sha256(content.encode()).hexdigest()
    m = metadata(i, run["id"], context.operation_id)
    c.execute(
        insert(app_previews).values(
            id=rid,
            app_id=i["source_app_id"],
            principal_id=user,
            request_key=context.operation_id,
            fingerprint=fingerprint(dict(scope=m, hash=digest)),
            input=m,
            status="SUCCEEDED",
            output=dict(content=content, hash=digest, format="json"),
            error=None,
            created_at=time.time(),
        )
    )
    back = c.execute(
        select(app_previews.c.output["content"].as_string()).where(app_previews.c.id == rid)
    ).scalar_one()
    require(back == content and hashlib.sha256(back.encode()).hexdigest() == digest)
    return dict(resource_id=rid, hash=digest)


def readback(store, c, run, operation, context):
    from . import local_record_apps as records

    require(
        type(context) is Target
        and context.run_id == run["id"]
        and context.operation_id == operation["id"]
    )
    i, _, _ = records.scope_job(store, c, run["principal_id"], run["id"], context.instance_id)
    require(i.get("preview_scope", {}).get("fingerprint") == context.scope_fingerprint)
    effect = (
        c.execute(select(local_effects).where(local_effects.c.operation_id == operation["id"]))
        .mappings()
        .first()
    )
    if effect is None:
        return "OUTCOME_UNKNOWN", None
    resource = artifact(store, c, run["principal_id"], i, effect["resource_id"])
    intent = c.execute(
        select(operation_intents.c.request).where(
            operation_intents.c.operation_id == operation["id"]
        )
    ).scalar_one()
    require(resource["content"] == intent["args"]["text"])
    data = dict(resource_id=resource["id"], hash=resource["hash"])
    return "VERIFIED", dict(
        operation_id=operation["id"],
        status="VERIFIED",
        data=data,
        artifact_refs=[resource["id"]],
        receipt_ref=operation["id"],
        check_results=[dict(check="receipt.readback.v1", status="PASS")],
        usage_ref=None,
        error=None,
    )


def mount(app, store, limits, identity):
    from . import local_record_apps as records

    dep = Depends(identity)

    @app.post("/api/internal/record-releases/{rid}/private-previews", status_code=201)
    def create(rid: str, body: records.PrivateInstanceInput, user=dep):
        return records.create_instance(store, user, rid, body.model_dump(), limits, private=True)

    @app.get("/api/internal/record-releases/{rid}/private-preview-requests/{key}")
    def recover(rid: str, key: str, user=dep):
        with store.tx() as c:
            records.read_release(store, c, user, rid, limits)
            saved = records.pair(c, user, rid, INSTANCE, key)
            if saved is None:
                raise DomainError("OUTCOME_UNKNOWN")
            i, _ = records.instance_header(store, c, user, saved["response"]["id"])
            return dict(
                namespace=records.VERSION,
                request_key=key,
                request_fingerprint=fingerprint(saved["request"]),
                instance=i,
                execution_namespace=NAMESPACE,
                formal_publication_enabled=False,
            )
