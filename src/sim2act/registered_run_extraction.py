"""Verified durable registered CSV AppRun -> trusted declaration; no new authority."""

import copy
import time

from sqlalchemy import insert, select

from .apps import authorize_source, csv_candidate, load_draft
from .contracts import validate_value
from .db import (
    app_drafts,
    fingerprint,
    internal_run_bindings,
    operation_intents,
    operations,
    run_contracts,
    runs,
    task_extractions,
)
from .errors import DomainError
from .extraction import exact_sum_oracle
from .lifecycle import NAMESPACE, data_rows, read_release
from .tools import authorized_read

KIND = "registered_csv_source.v1"
PROOF = "completed_registered_csv_apprun.v1"
GENERATOR = "TRUSTED_REGISTERED_CSV_FROM_APPRUN.v1"


def verified_csv_source(store, c, user, iid, rid, limits):
    from .app_jobs import load_binding

    job = c.execute(select(runs).where(runs.c.id == rid)).mappings().first()
    if not job or job["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    if job["status"] != "SUCCEEDED" or job["error"] is not None or job["cancel_intent"]:
        raise DomainError("VERIFICATION_FAILED", "Successful durable registered CSV Run required")
    s, a = load_binding(store, c, user, job, limits)
    if s["instance_id"] != iid:
        raise DomainError("PERMISSION_DENIED")
    if a["status"] != "SUCCEEDED" or a["error"] is not None:
        raise DomainError("VERIFICATION_FAILED")
    release = read_release(store, c, user, s["release_id"], limits)
    draft = release["snapshot"]["draft"]
    candidate = draft["candidate"]
    if (
        candidate["manifest"]["origin"] != "goal"
        or candidate["actions"][0]["executor"]
        != {"kind": "registered_tool", "ref": "data.aggregate_csv", "version": "1"}
        or "offline_replay" in s
    ):
        raise DomainError("UNSUPPORTED_CAPABILITY", "Initial registered CSV source only")
    inp = s["input"]
    validate_value(candidate["manifest"]["input_schema"], inp)
    validate_value(candidate["manifest"]["output_schema"], a["output"], "source_output")
    resource = candidate["manifest"]["data_bindings"][0]["resource_ref"]
    args = {"resource_id": resource, **inp}
    source = authorized_read(
        store, c, user, s["runtime_id"], s["project_id"], "resource.read", {"resource_id": resource}
    )
    output = authorized_read(
        store, c, user, s["runtime_id"], s["project_id"], "data.aggregate_csv", args
    )
    if (
        source["format"] != "csv"
        or source["hash"] != candidate["source_hash"]
        or output != a["output"]
    ):
        raise DomainError("VERSION_CONFLICT", "Source bytes/output changed")
    exact_sum_oracle(source["content"], inp["column"], a["output"])
    rows = [r for r in data_rows(c, iid) if r["run_id"] == a["id"]]
    op = (
        c.execute(
            select(operations).where(
                operations.c.run_id == rid, operations.c.call_id == "instance_result"
            )
        )
        .mappings()
        .first()
    )
    if len(rows) != 1 or not op:
        raise DomainError("VERSION_CONFLICT", "Missing exact source record/operation")
    record = rows[0]
    intent = c.execute(
        select(operation_intents.c.request).where(operation_intents.c.operation_id == op["id"])
    ).scalar()
    expected_intent = {"tool": "data.aggregate_csv", "args": args}
    receipt = {
        "operation_id": op["id"],
        "status": "VERIFIED",
        "app_run_id": a["id"],
        "instance_id": iid,
        "release_id": release["id"],
        "result_version": record["version"],
        "output_fingerprint": fingerprint(a["output"]),
        "data": a["output"],
        "artifact_refs": [],
        "check_results": [{"check": "csv.exact_integer_sum.v1", "status": "PASS"}],
    }
    result = {
        "app_run_id": a["id"],
        "instance_id": iid,
        "release_id": release["id"],
        "result_version": record["version"],
        "receipt_ref": op["id"],
    }
    if (
        op["status"] != "VERIFIED"
        or op["tool_ref"] != "data.aggregate_csv"
        or intent != expected_intent
        or op["fingerprint"] != fingerprint(expected_intent)
        or op["receipt"] != receipt
        or job["result"] != result
        or record["release_id"] != release["id"]
        or record["schema_version"] != release["snapshot"]["data_schema_version"]
        or a["result_version"] != record["version"]
    ):
        raise DomainError("VERSION_CONFLICT", "Exact verified source lineage required")
    binding = (
        c.execute(select(internal_run_bindings).where(internal_run_bindings.c.run_id == rid))
        .mappings()
        .one()
    )
    contract = (
        c.execute(select(run_contracts).where(run_contracts.c.run_id == rid)).mappings().one()
    )
    proof = {
        "kind": PROOF,
        "source_run_id": rid,
        "instance_id": iid,
        "app_run_id": a["id"],
        "release_id": release["id"],
        "project_id": s["project_id"],
        "principal_id": user,
        "run_version": job["version"],
        "run_fingerprint": job["fingerprint"],
        "binding_fingerprint": binding["fingerprint"],
        "contract_fingerprint": contract["fingerprint"],
        "release_fingerprint": release["fingerprint"],
        "candidate_fingerprint": draft["fingerprint"],
        "input_fingerprint": fingerprint(inp),
        "output_fingerprint": fingerprint(a["output"]),
        "receipt_fingerprint": fingerprint(receipt),
        "record_fingerprint": fingerprint(dict(record)),
        "source_resource_id": resource,
        "source_hash": source["hash"],
        "source_revision": 1,
        "tool": {"ref": "data.aggregate_csv", "version": "1", "effect": "read"},
        "check": {"ref": "csv.exact_integer_sum.v1", "status": "PASS"},
        "generator": GENERATOR,
        "semantic_goal_acceptance": "NOT_RUN",
        "model_requests": 0,
        "parameter_scope": {
            "creation": ["new_csv_binding_in_existing_authorization_domain"],
            "runtime": ["column"],
        },
    }
    return draft, proof


def _target(store, c, user, source, aid, limits):
    # Reject a foreign project before reading its protected materials.
    location = c.execute(select(app_drafts).where(app_drafts.c.id == aid)).mappings().first()
    if not location or location["project_id"] != source["project_id"]:
        raise DomainError("PERMISSION_DENIED")
    raw = location["candidate"]
    if (
        not isinstance(raw, dict)
        or not isinstance(raw.get("manifest"), dict)
        or raw["manifest"].get("origin") != "goal"
    ):
        raise DomainError("UNSUPPORTED_CAPABILITY", "Initial target app required")
    target, manifest, action, _ = load_draft(store, c, user, aid, limits)
    if action.executor.kind != "registered_tool" or action.executor.ref != "data.aggregate_csv":
        raise DomainError("UNSUPPORTED_CAPABILITY")
    from .agent_apps import existing_runtime

    existing_runtime(store, c, user, source["project_id"], target["runtime_id"])
    project = store.own_project(c, user, source["project_id"])
    rid = manifest.data_bindings[0].resource_ref
    authorize_source(store, c, user, project, rid, target["runtime_id"])
    material = authorized_read(
        store,
        c,
        user,
        target["runtime_id"],
        target["project_id"],
        "resource.read",
        {"resource_id": rid},
    )
    if material["format"] != "csv" or material["hash"] == source["candidate"]["source_hash"]:
        raise DomainError("INVALID_INPUT", "Different already-authorized CSV required")
    return {
        "app_id": aid,
        "fingerprint": target["fingerprint"],
        "resource_id": rid,
        "source_hash": material["hash"],
        "runtime_id": target["runtime_id"],
    }, target["name"]


def _envelope(**values):
    return {
        "namespace": NAMESPACE,
        "state": "PREVIEW_ONLY",
        "publishable": False,
        "formal_publication_enabled": False,
        "generator": GENERATOR,
        "model_requests": 0,
        "semantic_goal_acceptance": "NOT_RUN",
        **values,
    }


def options(store, user, iid, rid, limits):
    with store.tx() as c:
        pid = c.execute(select(runs.c.project_id).where(runs.c.id == rid)).scalar()
        store.lock_project(c, user, pid)
        source, proof = verified_csv_source(store, c, user, iid, rid, limits)
        targets = []
        ids = (
            c.execute(
                select(app_drafts.c.id).where(app_drafts.c.project_id == source["project_id"])
            )
            .scalars()
            .all()
        )
        for aid in ids:
            try:
                target, name = _target(store, c, user, source, aid, limits)
            except DomainError:
                continue
            targets.append(
                {"id": aid, "name": name, **{k: v for k, v in target.items() if k != "app_id"}}
            )
        if not targets:
            raise DomainError(
                "NEEDS_INPUT", "Existing authorized app bound to different CSV required"
            )
        return _envelope(
            proof=proof,
            source_proof_fingerprint=fingerprint(proof),
            proof_fingerprint=fingerprint(proof),
            targets=targets,
        )


def _request(iid, rid, proof_fp, target_id, target_fp, name):
    return {
        "instance_id": iid,
        "source_run_id": rid,
        "expected_proof_fingerprint": proof_fp,
        "target_app_id": target_id,
        "expected_target_draft_fingerprint": target_fp,
        "name": name,
    }


def _candidate(source, proof, target, aid=None, action_id=None):
    from .contracts import Limits

    candidate = csv_candidate(
        target["resource_id"],
        target["source_hash"],
        "",
        Limits(**source["candidate"]["manifest"]["runtime_limits"]),
    )
    if aid is not None:
        candidate["manifest"]["app_id"] = aid
        candidate["actions"][0]["action_id"] = action_id
        candidate["manifest"]["action_bindings"][0]["action_id"] = action_id
    candidate["goal"] = copy.deepcopy(source["candidate"]["goal"])
    candidate["manifest"].update(
        origin="task_run",
        source_run_ref=proof["source_run_id"],
        goal_ref=source["candidate"]["manifest"]["goal_ref"],
    )
    candidate["task_proof"] = {
        "proof": copy.deepcopy(proof),
        "proof_fingerprint": fingerprint(proof),
        "target": copy.deepcopy(target),
        "generator": GENERATOR,
    }
    return candidate


def _result(draft, proof, target, cached):
    return _envelope(
        id=draft["id"],
        candidate_fingerprint=draft["fingerprint"],
        cached=cached,
        source_proof_fingerprint=fingerprint(proof),
        target_resource_hash=target["source_hash"],
        authorization_domain=target["runtime_id"],
    )


def extract(
    store, user, iid, rid, expected_proof_fp, target_app_id, expected_target_fp, name, key, limits
):
    if (
        not isinstance(name, str)
        or not 1 <= len(name) <= 200
        or not isinstance(key, str)
        or not 1 <= len(key) <= 100
    ):
        raise DomainError("INVALID_INPUT")
    with store.tx() as c:
        pid = c.execute(select(runs.c.project_id).where(runs.c.id == rid)).scalar()
        store.lock_project(c, user, pid)
        source, proof = verified_csv_source(store, c, user, iid, rid, limits)
        target, _ = _target(store, c, user, source, target_app_id, limits)
        if fingerprint(proof) != expected_proof_fp or target["fingerprint"] != expected_target_fp:
            raise DomainError("VERSION_CONFLICT")
        request = _request(iid, rid, expected_proof_fp, target_app_id, expected_target_fp, name)
        request_fp = fingerprint(request)
        old = (
            c.execute(
                select(task_extractions).where(
                    task_extractions.c.task_id == rid,
                    task_extractions.c.principal_id == user,
                    task_extractions.c.request_key == key,
                )
            )
            .mappings()
            .first()
        )
        if old:
            if old["request_fingerprint"] != request_fp:
                raise DomainError("VERSION_CONFLICT")
            draft, _, _, _ = load_draft(store, c, user, old["app_id"], limits)
            return _result(draft, proof, target, True)
        candidate = _candidate(source, proof, target)
        from .apps import compile_preview

        compile_preview(candidate, limits)
        draft = {
            "id": candidate["manifest"]["app_id"],
            "project_id": source["project_id"],
            "runtime_id": target["runtime_id"],
            "name": name,
            "candidate": candidate,
            "fingerprint": fingerprint(candidate),
            "created_at": time.time(),
        }
        c.execute(insert(app_drafts).values(**draft))
        c.execute(
            insert(task_extractions).values(
                task_id=rid,
                principal_id=user,
                request_key=key,
                request_fingerprint=request_fp,
                app_id=draft["id"],
                snapshot={
                    "kind": KIND,
                    "proof": proof,
                    "target": target,
                    "request": request,
                    "candidate_fingerprint": draft["fingerprint"],
                },
            )
        )
        return _result(draft, proof, target, False)


def validate_registered_candidate(store, c, user, draft, limits):
    saved = (
        c.execute(select(task_extractions).where(task_extractions.c.app_id == draft["id"]))
        .mappings()
        .first()
    )
    snap = saved["snapshot"] if saved else None
    if (
        not saved
        or saved["principal_id"] != user
        or not isinstance(snap, dict)
        or set(snap) != {"kind", "proof", "target", "request", "candidate_fingerprint"}
        or snap["kind"] != KIND
        or not isinstance(snap["request"], dict)
        or fingerprint(snap["request"]) != saved["request_fingerprint"]
    ):
        raise DomainError("VERSION_CONFLICT", "Independent registered source marker required")
    req = snap["request"]
    if (
        set(req)
        != {
            "instance_id",
            "source_run_id",
            "expected_proof_fingerprint",
            "target_app_id",
            "expected_target_draft_fingerprint",
            "name",
        }
        or req["source_run_id"] != saved["task_id"]
        or ("name" in draft and req["name"] != draft["name"])
    ):
        raise DomainError("VERSION_CONFLICT")
    source, proof = verified_csv_source(
        store, c, user, req["instance_id"], saved["task_id"], limits
    )
    target, _ = _target(store, c, user, source, req["target_app_id"], limits)
    if (
        proof != snap["proof"]
        or fingerprint(proof) != req["expected_proof_fingerprint"]
        or target != snap["target"]
        or target["fingerprint"] != req["expected_target_draft_fingerprint"]
        or source["project_id"] != draft["project_id"]
        or target["runtime_id"] != draft["runtime_id"]
        or snap["candidate_fingerprint"] != draft["fingerprint"]
    ):
        raise DomainError("VERSION_CONFLICT", "Accepted source/target changed")
    expected = _candidate(
        source, proof, target, draft["id"], draft["candidate"]["actions"][0]["action_id"]
    )
    if expected != draft["candidate"]:
        raise DomainError("VERSION_CONFLICT", "Candidate differs from trusted source derivation")
