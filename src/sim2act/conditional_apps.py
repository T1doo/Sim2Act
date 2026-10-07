"""Named PREVIEW_ONLY wrappers over sealed bounded cold plans; not AppManifest apps."""

import copy
import time

from fastapi import Depends
from pydantic import Field, ValidationError
from sqlalchemy import insert, select

from .conditional_checks import SOURCE_HASH, Scenario
from .conditional_runs import (
    COLD,
    inputs_for,
    source_completion,
    validate_snapshot,
)
from .conditional_runs import (
    NAMESPACE as CHECK_NAMESPACE,
)
from .contracts import Strict
from .db import app_drafts, app_previews, fingerprint, new_id, task_extractions
from .errors import DomainError
from .protocol_jobs import _plan, _public, enqueue, verified_pending
from .tools import authorized_read

NAMESPACE = "bounded-conditional-app.v1"
HASH = r"^[a-f0-9]{64}$"
RUN = r"^run_[a-f0-9]{32}$"
RESOURCE = r"^res_[a-f0-9]{32}$"


class SaveRequest(Strict):
    extraction_run_id: str = Field(pattern=RUN)
    expected_plan_fingerprint: str = Field(pattern=HASH)
    expected_check_fingerprint: str = Field(pattern=HASH)
    target_resource_id: str = Field(pattern=RESOURCE)
    expected_target_hash: str = Field(pattern=HASH)
    name: str = Field(min_length=1, max_length=200)
    request_key: str = Field(min_length=1, max_length=100)


class RunRequest(Strict):
    expected_app_fingerprint: str = Field(pattern=HASH)
    scenario: Scenario
    request_key: str = Field(min_length=1, max_length=100)


def _anchors_validated(store, c, user, pid, body):
    project = store.lock_project(c, user, pid)
    plan = _plan(store, c, user, body["extraction_run_id"], body["expected_plan_fingerprint"])
    job, run = verified_pending(store, c, user, body["extraction_run_id"])
    validate_snapshot(job["snapshot"])
    if run["project_id"] != pid or plan.get("bounded_check_namespace") != CHECK_NAMESPACE:
        raise DomainError("PERMISSION_DENIED")
    if plan.get("source_check_fingerprint") != body["expected_check_fingerprint"]:
        raise DomainError("VERSION_CONFLICT")
    source_completion(
        store,
        c,
        user,
        plan["source_run_id"],
        plan["source_result_fingerprint"],
        body["expected_check_fingerprint"],
    )
    _current_target(store, c, user, pid, project, body)
    return project, plan, job


def anchors(store, c, user, pid, body):
    project, _, _ = _anchors_validated(store, c, user, pid, body)
    return project


def _current_target(store, c, user, pid, project, body):
    target = authorized_read(
        store,
        c,
        user,
        project["runtime_id"],
        pid,
        "resource.read",
        {"resource_id": body["target_resource_id"]},
    )
    if (
        target["format"] not in {"txt", "md"}
        or target["hash"] != SOURCE_HASH
        or target["hash"] != body["expected_target_hash"]
    ):
        raise DomainError("VERSION_CONFLICT")


def _load_validated_origin(store, c, user, pid, aid):
    store.lock_project(c, user, pid)
    draft = c.execute(select(app_drafts).where(app_drafts.c.id == aid)).mappings().first()
    marker = (
        c.execute(select(task_extractions).where(task_extractions.c.app_id == aid))
        .mappings()
        .first()
    )
    if not draft or draft["project_id"] != pid or not marker or marker["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    wrapper = draft["candidate"]
    frozen = marker["snapshot"]
    if (
        not isinstance(wrapper, dict)
        or set(wrapper)
        != {
            "namespace",
            "version",
            "project_id",
            "runtime_id",
            "name",
            "origin",
            "state",
            "permissions",
        }
        or not isinstance(wrapper["origin"], dict)
    ):
        raise DomainError("VERSION_CONFLICT")
    if (
        not isinstance(wrapper, dict)
        or wrapper.get("namespace") != NAMESPACE
        or not isinstance(frozen, dict)
        or set(frozen) != {"kind", "wrapper", "wrapper_fingerprint"}
    ):
        raise DomainError("VERSION_CONFLICT")
    if (
        frozen["kind"] != NAMESPACE
        or fingerprint(frozen["wrapper"]) != fingerprint(wrapper)
        or frozen["wrapper_fingerprint"] != fingerprint(wrapper)
        or draft["fingerprint"] != fingerprint(wrapper)
    ):
        raise DomainError("VERSION_CONFLICT")
    if (
        wrapper["project_id"] != pid
        or wrapper["name"] != draft["name"]
        or wrapper["runtime_id"] != draft["runtime_id"]
    ):
        raise DomainError("VERSION_CONFLICT")
    try:
        parsed = SaveRequest.model_validate(
            {**wrapper["origin"], "name": draft["name"], "request_key": marker["request_key"]}
        )
    except (TypeError, ValidationError) as exc:
        raise DomainError("VERSION_CONFLICT") from exc
    if marker["task_id"] != parsed.extraction_run_id:
        raise DomainError("VERSION_CONFLICT")
    values = parsed.model_dump()
    values.pop("request_key")
    if marker["request_fingerprint"] != fingerprint(
        {"namespace": NAMESPACE, "project_id": pid, **values}
    ):
        raise DomainError("VERSION_CONFLICT")
    expected_wrapper = {
        "namespace": NAMESPACE,
        "version": 1,
        "project_id": pid,
        "runtime_id": draft["runtime_id"],
        "name": draft["name"],
        "origin": {k: v for k, v in values.items() if k != "name"},
        "state": "PREVIEW_ONLY",
        "permissions": {
            "resource_ids": [parsed.target_resource_id],
            "tool_refs": ["resource.read"],
        },
    }
    if fingerprint(wrapper) != fingerprint(expected_wrapper):
        raise DomainError("VERSION_CONFLICT")
    project, plan, job = _anchors_validated(store, c, user, pid, wrapper["origin"])
    if project["runtime_id"] != draft["runtime_id"]:
        raise DomainError("VERSION_CONFLICT")
    return draft, plan, job


def load(store, c, user, pid, aid):
    draft, _, _ = _load_validated_origin(store, c, user, pid, aid)
    return draft


def public(draft):
    return {
        "namespace": NAMESPACE,
        "id": draft["id"],
        "name": draft["name"],
        "project_id": draft["project_id"],
        "fingerprint": draft["fingerprint"],
        "state": "PREVIEW_ONLY",
        "formal_publication_enabled": False,
        "overall_run_acceptance": "NOT_ACCEPTED",
        "semantic_status": "UNKNOWN",
        "owner_acceptance": "PENDING",
        "authorization_domain": "SHARED_EXISTING_PROJECT_RUNTIME",
        "runtime_id": draft["runtime_id"],
        "scenario_schema": Scenario.model_json_schema(),
        "origin": copy.deepcopy(draft["candidate"]["origin"]),
    }


def save(store, user, pid, body):
    values = body.model_dump()
    key = values.pop("request_key")
    request_fp = fingerprint({"namespace": NAMESPACE, "project_id": pid, **values})
    with store.tx() as c:
        project = anchors(store, c, user, pid, values)
        prior = (
            c.execute(
                select(task_extractions).where(
                    task_extractions.c.task_id == body.extraction_run_id,
                    task_extractions.c.principal_id == user,
                    task_extractions.c.request_key == key,
                )
            )
            .mappings()
            .first()
        )
        if prior:
            if prior["request_fingerprint"] != request_fp:
                raise DomainError("VERSION_CONFLICT")
            return {**public(load(store, c, user, pid, prior["app_id"])), "cached": True}
        origin = {k: v for k, v in values.items() if k != "name"}
        wrapper = {
            "namespace": NAMESPACE,
            "version": 1,
            "project_id": pid,
            "runtime_id": project["runtime_id"],
            "name": body.name,
            "origin": origin,
            "state": "PREVIEW_ONLY",
            "permissions": {
                "resource_ids": [body.target_resource_id],
                "tool_refs": ["resource.read"],
            },
        }
        aid = new_id("app")
        fp = fingerprint(wrapper)
        row = {
            "id": aid,
            "project_id": pid,
            "runtime_id": project["runtime_id"],
            "name": body.name,
            "candidate": wrapper,
            "fingerprint": fp,
            "created_at": time.time(),
        }
        c.execute(insert(app_drafts).values(**row))
        c.execute(
            insert(task_extractions).values(
                task_id=body.extraction_run_id,
                principal_id=user,
                request_key=key,
                request_fingerprint=request_fp,
                app_id=aid,
                snapshot={"kind": NAMESPACE, "wrapper": wrapper, "wrapper_fingerprint": fp},
            )
        )
        return {**public(row), "cached": False}


def cold_payload(draft, body):
    origin = draft["candidate"]["origin"]
    return {
        "extraction_run_id": origin["extraction_run_id"],
        "expected_plan_fingerprint": origin["expected_plan_fingerprint"],
        "resource_bindings": {"rules": origin["target_resource_id"]},
        "inputs": inputs_for(body.scenario.model_dump()),
        "contract_id": COLD,
    }


def submit(store, user, pid, aid, body, limits):
    values = body.model_dump()
    request_fp = fingerprint({"namespace": NAMESPACE, "app_id": aid, **values})
    with store.tx() as c:
        draft = load(store, c, user, pid, aid)
        if draft["fingerprint"] != body.expected_app_fingerprint:
            raise DomainError("VERSION_CONFLICT")
        payload = cold_payload(draft, body)
        # Deterministic server key permits receipt recovery even if binding insertion was interrupted.
        server_key = "conditional-app:" + fingerprint(
            {"app_id": aid, "user": user, "key": body.request_key}
        )
    result = enqueue(store, user, pid, "cold", payload, server_key, limits, bounded=True)
    with store.tx() as c:
        draft = load(store, c, user, pid, aid)
        if draft["fingerprint"] != body.expected_app_fingerprint:
            raise DomainError("VERSION_CONFLICT")
        prior = (
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
        if prior:
            if prior["fingerprint"] != request_fp or prior["output"] != {
                "namespace": NAMESPACE,
                "run_id": result["run_id"],
            }:
                raise DomainError("VERSION_CONFLICT")
        else:
            c.execute(
                insert(app_previews).values(
                    id=new_id("preview"),
                    app_id=aid,
                    principal_id=user,
                    request_key=body.request_key,
                    fingerprint=request_fp,
                    input=values,
                    status="QUEUED",
                    output={"namespace": NAMESPACE, "run_id": result["run_id"]},
                    created_at=time.time(),
                )
            )
    return {
        **result,
        "app_id": aid,
        "app_fingerprint": draft["fingerprint"],
        "state": "PREVIEW_ONLY",
    }


def history(store, user, pid, aid):
    with store.tx() as c:
        draft = load(store, c, user, pid, aid)
        rows = (
            c.execute(
                select(app_previews)
                .where(app_previews.c.app_id == aid, app_previews.c.principal_id == user)
                .order_by(app_previews.c.created_at.desc())
            )
            .mappings()
            .all()
        )
        items = []
        for row in rows:
            try:
                parsed = RunRequest.model_validate(row["input"])
            except ValidationError as exc:
                raise DomainError("VERSION_CONFLICT") from exc
            expected = fingerprint({"namespace": NAMESPACE, "app_id": aid, **parsed.model_dump()})
            if (
                row["fingerprint"] != expected
                or row["request_key"] != parsed.request_key
                or parsed.expected_app_fingerprint != draft["fingerprint"]
                or set(row["output"] or {}) != {"namespace", "run_id"}
                or row["output"]["namespace"] != NAMESPACE
            ):
                raise DomainError("VERSION_CONFLICT")
            job, run = verified_pending(store, c, user, row["output"]["run_id"])
            validate_snapshot(job["snapshot"])
            if (
                run["project_id"] != pid
                or job["phase"] != "cold"
                or fingerprint(job["snapshot"]["payload"])
                != fingerprint(cold_payload(draft, parsed))
                or run["request_key"]
                != "protocol:conditional-app:"
                + fingerprint({"app_id": aid, "user": user, "key": parsed.request_key})
                or run["principal_id"] != user
                or run["runtime_id"] != draft["runtime_id"]
            ):
                raise DomainError("VERSION_CONFLICT")
            items.append(
                {
                    "receipt_id": row["id"],
                    "scenario": parsed.scenario.model_dump(),
                    "run": _public(job, run),
                }
            )
        return {"namespace": NAMESPACE, "app": public(draft), "items": items}


def mount(app, store, identity, limits, settings):
    dependency = Depends(identity)

    def offline():
        if settings.mode != "mock":
            raise DomainError("PERMISSION_DENIED", "Only explicit offline preview exists")

    @app.post("/api/projects/{pid}/conditional-apps", status_code=201)
    def create(pid: str, body: SaveRequest, user=dependency):
        offline()
        return save(store, user, pid, body)

    @app.get("/api/projects/{pid}/conditional-apps")
    def listing(pid: str, user=dependency):
        with store.tx() as c:
            store.lock_project(c, user, pid)
            rows = (
                c.execute(
                    select(app_drafts)
                    .where(app_drafts.c.project_id == pid)
                    .order_by(app_drafts.c.created_at.desc())
                )
                .mappings()
                .all()
            )
            ids = [
                r["id"]
                for r in rows
                if isinstance(r["candidate"], dict) and r["candidate"].get("namespace") == NAMESPACE
            ]
            return {
                "namespace": NAMESPACE,
                "items": [public(load(store, c, user, pid, aid)) for aid in ids],
            }

    @app.get("/api/projects/{pid}/conditional-apps/{aid}")
    def inspect(pid: str, aid: str, user=dependency):
        with store.tx() as c:
            return public(load(store, c, user, pid, aid))

    @app.post("/api/projects/{pid}/conditional-apps/{aid}/runs", status_code=202)
    def run(pid: str, aid: str, body: RunRequest, user=dependency):
        offline()
        return submit(store, user, pid, aid, body, limits)

    @app.get("/api/projects/{pid}/conditional-apps/{aid}/history")
    def read_history(pid: str, aid: str, user=dependency):
        return history(store, user, pid, aid)
