"""Canonical Report ActionSpec/AppManifest previews over sealed finite protocol plans."""

import copy
import json
import time

from fastapi import Depends
from pydantic import Field, ValidationError
from sqlalchemy import insert, select

from . import conditional_apps as named
from .conditional_checks import Scenario
from .conditional_runs import COLD, inputs_for, report_schema, validate_snapshot
from .contracts import Limits, Strict, validate_action_input, validate_value
from .db import app_drafts, app_previews, fingerprint, new_id, task_extractions
from .errors import DomainError
from .preflight import preflight
from .protocol_jobs import _public, enqueue, verified_pending

NAMESPACE = "bounded-report-manifest.v1"
CHECK = "source.conditional_report.v1"
HASH = r"^[a-f0-9]{64}$"
APP = r"^app_[a-f0-9]{32}$"
RUN = r"^run_[a-f0-9]{32}$"
RESOURCE = r"^res_[a-f0-9]{32}$"


class PromoteRequest(Strict):
    expected_app_fingerprint: str = Field(pattern=HASH)
    request_key: str = Field(min_length=1, max_length=100)


class PreviewRequest(Strict):
    expected_candidate_fingerprint: str = Field(pattern=HASH)
    input: Scenario
    request_key: str = Field(min_length=1, max_length=100)


class Proof(Strict):
    named_app_id: str = Field(pattern=APP)
    expected_named_fingerprint: str = Field(pattern=HASH)
    extraction_run_id: str = Field(pattern=RUN)
    expected_plan_fingerprint: str = Field(pattern=HASH)
    expected_check_fingerprint: str = Field(pattern=HASH)
    source_run_id: str = Field(pattern=RUN)
    source_resource_id: str = Field(pattern=RESOURCE)
    target_resource_id: str = Field(pattern=RESOURCE)
    expected_target_hash: str = Field(pattern=HASH)
    runtime_id: str
    limits: Limits


def obj(properties):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def scenario_schema():
    return obj(
        {
            "kind": {"type": "string", "enum": ["HYPOTHETICAL_EMPLOYEE"]},
            "trip_ended": {"type": "boolean", "nullable": True},
            "amount": {"type": "integer", "nullable": True, "minimum": 0, "maximum": 1000000},
            "receipt_present": {"type": "boolean", "nullable": True},
            "approved": {"type": "boolean", "nullable": True},
            "elapsed_days": {"type": "integer", "nullable": True, "minimum": 0, "maximum": 3650},
        }
    )


def canonical(aid, action_id, goal_ref, proof):
    proof = Proof.model_validate(proof).model_dump()
    fields = scenario_schema()["properties"]
    output = report_schema()
    refs = sorted(set([proof["source_resource_id"], proof["target_resource_id"]]))
    permissions = [{"tool_ref": "resource.read", "resource_ref": ref} for ref in refs]
    dependencies = [{"kind": "resource", "ref": ref, "version": "1"} for ref in refs]
    action = {
        "schema_version": "1.0-draft",
        "action_id": action_id,
        "revision": 1,
        "input_schema": obj({"resource_id": {"type": "string"}, **fields}),
        "output_schema": output,
        "executor": {"kind": "bounded_report", "ref": "intern.conditional_report", "version": "1"},
        "allowed_tool_refs": ["resource.read"],
        "dependencies": dependencies,
        "permission_requirements": permissions,
        "effect": "read",
        "preconditions": [],
        "postcheck_refs": [CHECK],
        "limits": proof["limits"],
        "idempotency": "read_only",
        "reconcile_ref": "operation.lookup.v1",
        "error_contract": [
            "INVALID_INPUT",
            "PERMISSION_DENIED",
            "GRANT_REVOKED",
            "VERSION_CONFLICT",
            "RESOURCE_UNAVAILABLE",
        ],
    }
    manifest = {
        "schema_version": "1.0-draft",
        "app_id": aid,
        "revision": 1,
        "origin": "task_run",
        "goal_ref": goal_ref,
        "source_run_ref": proof["source_run_id"],
        "input_schema": scenario_schema(),
        "output_schema": output,
        "outputs": {
            k: {"source": "step", "ref": "report", "field": k} for k in output["properties"]
        },
        "views": [{"component_ref": "text", "output_field": "decision"}],
        "workflow": [
            {
                "step_id": "report",
                "binding_id": "conditional_report",
                "depends_on": [],
                "inputs": {
                    "resource_id": {"source": "data", "ref": "rules", "field": "resource_id"},
                    **{k: {"source": "input", "field": k} for k in fields},
                },
            }
        ],
        "action_bindings": [
            {"binding_id": "conditional_report", "action_id": action_id, "revision": 1}
        ],
        "data_bindings": [{"binding_id": "rules", "resource_ref": proof["target_resource_id"]}],
        "runtime_identity_requirements": {"mode": "user_and_project_intersection"},
        "permission_requirements": permissions,
        "dependency_lock": [
            *dependencies,
            {"kind": "tool", "ref": "resource.read", "version": "1"},
            {"kind": "prompt", "ref": "intern.system.v1", "version": "1"},
            {"kind": "check", "ref": CHECK, "version": "1"},
        ],
        "validation_suite_ref": CHECK,
        "runtime_limits": proof["limits"],
        "data_schema_version": 1,
    }
    return {
        "namespace": NAMESPACE,
        "manifest": manifest,
        "actions": [action],
        "source_hash": proof["expected_target_hash"],
        "report_proof": proof,
    }


def compile_report(candidate, platform_limits):
    try:
        if (
            not isinstance(candidate, dict)
            or set(candidate) != {"namespace", "manifest", "actions", "source_hash", "report_proof"}
            or candidate["namespace"] != NAMESPACE
            or len(candidate["actions"]) != 1
        ):
            raise DomainError("INVALID_MANIFEST")
        proof = Proof.model_validate(candidate["report_proof"])
        manifest, report = preflight(
            json.dumps(candidate["manifest"]), candidate["actions"], platform_limits
        )
        action = candidate["actions"][0]
        expected = canonical(
            manifest.app_id, action["action_id"], manifest.goal_ref, proof.model_dump()
        )
        if fingerprint(candidate) != fingerprint(expected):
            raise DomainError(
                "INVALID_MANIFEST", "Exact registered Report wiring/schema/check/authority required"
            )
        from .contracts import validate_action

        return (
            manifest,
            validate_action(json.dumps(action)),
            {
                **report,
                "compiler": NAMESPACE,
                "actual_execution_gateway": "protocol-cold.v1",
                "scope": "finite Report only; semantic UNKNOWN, owner PENDING",
            },
        )
    except (KeyError, TypeError, ValidationError, ValueError) as exc:
        raise DomainError("INVALID_MANIFEST") from exc


def scoped(store, c, user, aid, pid=None):
    row = c.execute(select(app_drafts.c.project_id).where(app_drafts.c.id == aid)).first()
    if not row or (pid is not None and row[0] != pid):
        raise DomainError("PERMISSION_DENIED")
    store.lock_project(c, user, row[0])
    return row[0]


def _read_canonical(store, c, user, aid, limits, pid):
    pid = scoped(store, c, user, aid, pid)
    draft = c.execute(select(app_drafts).where(app_drafts.c.id == aid)).mappings().one()
    marker = (
        c.execute(select(task_extractions).where(task_extractions.c.app_id == aid))
        .mappings()
        .first()
    )
    snapshot = marker["snapshot"] if marker else None
    if (
        not marker
        or marker["principal_id"] != user
        or not isinstance(snapshot, dict)
        or set(snapshot) != {"kind", "request", "candidate", "candidate_fingerprint"}
        or snapshot["kind"] != NAMESPACE
    ):
        raise DomainError("VERSION_CONFLICT")
    candidate = draft["candidate"]
    if (
        fingerprint(candidate) != draft["fingerprint"]
        or fingerprint(snapshot["candidate"]) != draft["fingerprint"]
        or snapshot["candidate_fingerprint"] != draft["fingerprint"]
    ):
        raise DomainError("VERSION_CONFLICT")
    manifest, action, report = compile_report(candidate, limits)
    proof = candidate["report_proof"]
    request = snapshot["request"]
    if (
        not isinstance(request, dict)
        or set(request) != {"named_app_id", "expected_app_fingerprint", "request_key"}
        or marker["request_fingerprint"]
        != fingerprint({"namespace": NAMESPACE, "project_id": pid, **request})
        or not isinstance(request["request_key"], str)
        or marker["request_key"] != "manifest:" + request["request_key"]
        or request["named_app_id"] != proof["named_app_id"]
        or request["expected_app_fingerprint"] != proof["expected_named_fingerprint"]
    ):
        raise DomainError("VERSION_CONFLICT")
    try:
        PromoteRequest.model_validate(
            {key: request[key] for key in ("expected_app_fingerprint", "request_key")}
        )
        if not isinstance(request["named_app_id"], str):
            raise ValueError("Invalid persisted origin")
    except (ValidationError, ValueError, TypeError):
        raise DomainError("VERSION_CONFLICT") from None
    return draft, marker, manifest, action, report, proof


def _fresh_origin(store, c, user, pid, parent, plan):
    """Immediately consume our private named validation; recheck mutable origin heads."""
    origin = parent["candidate"]["origin"]
    project = store.lock_project(c, user, pid)
    job, run = verified_pending(store, c, user, origin["extraction_run_id"])
    current = (job["result"] or {}).get("compiled_plan")
    if job["phase"] != "extract" or run["status"] != "SUCCEEDED" or not isinstance(current, dict):
        raise DomainError("VERIFICATION_FAILED", "Completed protocol extraction required")
    if (
        run["project_id"] != pid
        or project["runtime_id"] != parent["runtime_id"]
        or fingerprint(current) != fingerprint(plan)
        or current.get("plan_fingerprint") != origin["expected_plan_fingerprint"]
        or fingerprint({k: v for k, v in current.items() if k != "plan_fingerprint"})
        != origin["expected_plan_fingerprint"]
    ):
        raise DomainError("VERSION_CONFLICT", "Validated extraction changed")
    validate_snapshot(job["snapshot"])
    _, source = verified_pending(store, c, user, plan["source_run_id"])
    named._current_target(store, c, user, pid, project, origin)
    return job, source


def _validate_canonical(store, c, user, pid, parts, parent, plan):
    draft, marker, manifest, action, report, proof = parts
    if (
        parent["id"] != proof["named_app_id"]
        or parent["project_id"] != pid
        or parent["fingerprint"] != proof["expected_named_fingerprint"]
        or draft["runtime_id"] != parent["runtime_id"]
        or proof["runtime_id"] != parent["runtime_id"]
        or manifest.app_id != draft["id"]
        or draft["name"] != parent["name"]
        or marker["task_id"] != proof["extraction_run_id"]
    ):
        raise DomainError("VERSION_CONFLICT")
    origin = parent["candidate"]["origin"]
    for key in [
        "extraction_run_id",
        "expected_plan_fingerprint",
        "expected_check_fingerprint",
        "target_resource_id",
        "expected_target_hash",
    ]:
        if proof[key] != origin[key]:
            raise DomainError("VERSION_CONFLICT")
    extraction_job, source = _fresh_origin(store, c, user, pid, parent, plan)
    if fingerprint(proof["limits"]) != fingerprint(extraction_job["snapshot"]["limits"]):
        raise DomainError("VERSION_CONFLICT", "Frozen extraction budget cannot be rewritten")
    if (
        proof["source_run_id"] != source["id"]
        or proof["source_resource_id"] != source["resource_refs"][0]
        or manifest.goal_ref != store.frozen_contract(c, source).goal.goal_id
    ):
        raise DomainError("VERSION_CONFLICT")
    return draft, manifest, action, report


def load(store, c, user, aid, limits, pid=None):
    parts = _read_canonical(store, c, user, aid, limits, pid)
    pid = parts[0]["project_id"]
    parent, plan, _ = named._load_validated_origin(store, c, user, pid, parts[-1]["named_app_id"])
    return _validate_canonical(store, c, user, pid, parts, parent, plan)


def promote(store, user, pid, aid, body, limits):
    request = {"named_app_id": aid, **body.model_dump()}
    request_fp = fingerprint({"namespace": NAMESPACE, "project_id": pid, **request})
    with store.tx() as c:
        parent, plan, _ = named._load_validated_origin(store, c, user, pid, aid)
        if (
            parent["id"] != aid
            or parent["project_id"] != pid
            or parent["fingerprint"] != body.expected_app_fingerprint
        ):
            raise DomainError("VERSION_CONFLICT")
        origin = parent["candidate"]["origin"]
        old = (
            c.execute(
                select(task_extractions).where(
                    task_extractions.c.task_id == origin["extraction_run_id"],
                    task_extractions.c.principal_id == user,
                    task_extractions.c.request_key == "manifest:" + body.request_key,
                )
            )
            .mappings()
            .first()
        )
        if old:
            if old["request_fingerprint"] != request_fp:
                raise DomainError("VERSION_CONFLICT")
            parts = _read_canonical(store, c, user, old["app_id"], limits, pid)
            draft, manifest, action, report = _validate_canonical(
                store, c, user, pid, parts, parent, plan
            )
            return {**metadata(draft, manifest, report), "cached": True}
        job, source = _fresh_origin(store, c, user, pid, parent, plan)
        # Freeze original caps; shared preflight rejects a tightened platform before any write.
        caps = copy.deepcopy(job["snapshot"]["limits"])
        proof = {
            "named_app_id": aid,
            "expected_named_fingerprint": parent["fingerprint"],
            **origin,
            "source_run_id": source["id"],
            "source_resource_id": source["resource_refs"][0],
            "runtime_id": parent["runtime_id"],
            "limits": Limits.model_validate(caps).model_dump(),
        }
        newaid = new_id("app")
        candidate = canonical(
            newaid, new_id("action"), store.frozen_contract(c, source).goal.goal_id, proof
        )
        manifest, _, report = compile_report(candidate, limits)
        draft = {
            "id": newaid,
            "project_id": pid,
            "runtime_id": parent["runtime_id"],
            "name": parent["name"],
            "candidate": candidate,
            "fingerprint": fingerprint(candidate),
            "created_at": time.time(),
        }
        c.execute(insert(app_drafts).values(**draft))
        c.execute(
            insert(task_extractions).values(
                task_id=origin["extraction_run_id"],
                principal_id=user,
                request_key="manifest:" + body.request_key,
                request_fingerprint=request_fp,
                app_id=newaid,
                snapshot={
                    "kind": NAMESPACE,
                    "request": request,
                    "candidate": candidate,
                    "candidate_fingerprint": draft["fingerprint"],
                },
            )
        )
        return {**metadata(draft, manifest, report), "cached": False}


def metadata(draft, manifest, report):
    return {
        "namespace": NAMESPACE,
        "id": draft["id"],
        "name": draft["name"],
        "project_id": draft["project_id"],
        "runtime_id": draft["runtime_id"],
        "fingerprint": draft["fingerprint"],
        "candidate": copy.deepcopy(draft["candidate"]),
        "input_schema": manifest.input_schema,
        "state": "PREVIEW_ONLY",
        "publishable": False,
        "formal_publication_enabled": False,
        "semantic_status": "UNKNOWN",
        "owner_acceptance": "PENDING",
        "overall_run_acceptance": "NOT_ACCEPTED",
        "validation": report,
        "input_guidance": {
            "mode": "BOUNDED_REPORT",
            "authorization_domain": "SHARED_EXISTING_PROJECT_RUNTIME",
            "input": "new typed hypothetical Scenario only",
            "source_report_reused": False,
            "release_supported": False,
        },
    }


def server_key(user, aid, app_fp, key):
    return "manifest-report:" + fingerprint(
        {"user": user, "app_id": aid, "fingerprint": app_fp, "key": key}
    )


def payload_for(draft, scenario):
    proof = draft["candidate"]["report_proof"]
    return {
        "extraction_run_id": proof["extraction_run_id"],
        "expected_plan_fingerprint": proof["expected_plan_fingerprint"],
        "resource_bindings": {"rules": proof["target_resource_id"]},
        "inputs": inputs_for(scenario),
        "contract_id": COLD,
    }


def preview(store, user, pid, aid, body, limits):
    with store.tx() as c:
        draft, manifest, action, _ = load(store, c, user, aid, limits, pid)
        if draft["fingerprint"] != body.expected_candidate_fingerprint:
            raise DomainError("VERSION_CONFLICT")
        scenario = body.input.model_dump()
        validate_value(manifest.input_schema, scenario)
        validate_action_input(
            action,
            {"resource_id": draft["candidate"]["report_proof"]["target_resource_id"], **scenario},
        )
        payload = payload_for(draft, scenario)
        key = server_key(user, aid, draft["fingerprint"], body.request_key)
        # Actual accepted cold Run uses the exact common compiled manifest budget ceiling.
        run_limits = manifest.runtime_limits
    result = enqueue(store, user, pid, "cold", payload, key, run_limits, bounded=True)
    with store.tx() as c:
        draft, _, _, _ = load(store, c, user, aid, limits, pid)
        if draft["fingerprint"] != body.expected_candidate_fingerprint:
            raise DomainError("VERSION_CONFLICT")
        value = body.model_dump()
        fp = fingerprint({"namespace": NAMESPACE, "app_id": aid, **value})
        old = (
            c.execute(
                select(app_previews).where(
                    app_previews.c.app_id == aid,
                    app_previews.c.principal_id == user,
                    app_previews.c.request_key == body.request_key,
                )
            )
            .mappings()
            .first()
        )
        output = {"namespace": NAMESPACE, "run_id": result["run_id"]}
        if old:
            if old["fingerprint"] != fp or fingerprint(old["output"]) != fingerprint(output):
                raise DomainError("VERSION_CONFLICT")
        else:
            c.execute(
                insert(app_previews).values(
                    id=new_id("preview"),
                    app_id=aid,
                    principal_id=user,
                    request_key=body.request_key,
                    fingerprint=fp,
                    input=value,
                    status="QUEUED",
                    output=output,
                    created_at=time.time(),
                )
            )
    return {
        **result,
        "app_id": aid,
        "candidate_fingerprint": draft["fingerprint"],
        "compiler_namespace": NAMESPACE,
        "state": "PREVIEW_ONLY",
    }


def records(store, c, user, draft, manifest):
    items = []
    for row in c.execute(
        select(app_previews)
        .where(app_previews.c.app_id == draft["id"], app_previews.c.principal_id == user)
        .order_by(app_previews.c.created_at.desc())
    ).mappings():
        try:
            request = PreviewRequest.model_validate(row["input"])
        except ValidationError as exc:
            raise DomainError("VERSION_CONFLICT") from exc
        if (
            row["request_key"] != request.request_key
            or request.expected_candidate_fingerprint != draft["fingerprint"]
            or row["fingerprint"]
            != fingerprint({"namespace": NAMESPACE, "app_id": draft["id"], **request.model_dump()})
            or not isinstance(row["output"], dict)
            or set(row["output"]) != {"namespace", "run_id"}
            or row["output"]["namespace"] != NAMESPACE
        ):
            raise DomainError("VERSION_CONFLICT")
        job, run = verified_pending(store, c, user, row["output"]["run_id"])
        validate_snapshot(job["snapshot"])
        if (
            run["project_id"] != draft["project_id"]
            or run["principal_id"] != user
            or run["runtime_id"] != draft["runtime_id"]
            or run["request_key"]
            != "protocol:"
            + server_key(user, draft["id"], draft["fingerprint"], request.request_key)
            or job["phase"] != "cold"
            or fingerprint(job["snapshot"]["payload"])
            != fingerprint(payload_for(draft, request.input.model_dump()))
            or fingerprint(job["snapshot"]["limits"])
            != fingerprint(manifest.runtime_limits.model_dump())
        ):
            raise DomainError("VERSION_CONFLICT")
        items.append(
            {
                "id": row["id"],
                "input": request.input.model_dump(),
                "run": _public(job, run),
                "namespace": NAMESPACE,
            }
        )
    return items


def inspect(store, user, aid, limits, pid=None):
    with store.tx() as c:
        draft, manifest, _, report = load(store, c, user, aid, limits, pid)
        return {
            **metadata(draft, manifest, report),
            "history": records(store, c, user, draft, manifest),
        }


def mount(app, store, identity, limits, settings):
    dependency = Depends(identity)

    def offline():
        if settings.mode != "mock":
            raise DomainError("PERMISSION_DENIED", "Only private offline Report previews exist")

    @app.post("/api/projects/{pid}/conditional-apps/{aid}/manifest-preview", status_code=201)
    def create(pid: str, aid: str, body: PromoteRequest, user=dependency):
        offline()
        return promote(store, user, pid, aid, body, limits)

    @app.get("/api/projects/{pid}/apps/{aid}")
    def read(pid: str, aid: str, user=dependency):
        return inspect(store, user, aid, limits, pid)

    @app.post("/api/projects/{pid}/apps/{aid}/previews", status_code=202)
    def execute(pid: str, aid: str, body: PreviewRequest, user=dependency):
        offline()
        return preview(store, user, pid, aid, body, limits)

    @app.get("/api/projects/{pid}/apps/{aid}/history")
    def history(pid: str, aid: str, user=dependency):
        return inspect(store, user, aid, limits, pid)
