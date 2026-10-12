"""Verified finite registered AppRun -> trusted declaration; no new authority."""

import copy
import time

from pydantic import Field
from sqlalchemy import insert, select

from .apps import authorize_source, csv_candidate, load_draft
from .contracts import Strict, validate_value
from .db import (
    app_drafts,
    attempts,
    fingerprint,
    internal_run_bindings,
    new_id,
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


class RegisteredExtractionInput(Strict):
    expected_proof_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    target_app_id: str = Field(pattern=r"^app_[a-f0-9]{32}$")
    expected_target_draft_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    name: str = Field(min_length=1, max_length=200)
    request_key: str = Field(min_length=1, max_length=100)


KIND = "registered_csv_source.v1"
PROOF = "completed_registered_csv_apprun.v1"
GENERATOR = "TRUSTED_REGISTERED_CSV_FROM_APPRUN.v1"
TEXT_KIND = "registered_text_source.v1"
TEXT_PROOF = "completed_registered_text_apprun.v1"
TEXT_GENERATOR = "TRUSTED_REGISTERED_TEXT_FROM_APPRUN.v1"


def verified_source(store, c, user, iid, rid, limits):
    from .app_jobs import KIND as JOB_KIND
    from .app_jobs import load_binding
    from .text_run_checks import verify

    # Scope private queue contents before reading source lineage.
    job = (
        c.execute(select(runs).where(runs.c.id == rid, runs.c.principal_id == user))
        .mappings()
        .first()
    )
    if not job:
        raise DomainError("PERMISSION_DENIED")
    if job["status"] != "SUCCEEDED" or job["error"] is not None or job["cancel_intent"]:
        raise DomainError("VERIFICATION_FAILED", "Successful durable registered Run required")
    snapshot, actual = load_binding(store, c, user, job, limits)
    if snapshot["instance_id"] != iid:
        raise DomainError("PERMISSION_DENIED")
    release = read_release(store, c, user, snapshot["release_id"], limits)
    draft = release["snapshot"]["draft"]
    candidate = draft["candidate"]
    if candidate["actions"][0]["executor"]["ref"] != "text.literal_evidence":
        return verified_csv_source(store, c, user, iid, rid, limits)
    if (
        not candidate.get("goal_application")
        or candidate["manifest"]["origin"] != "goal"
        or "offline_replay" in snapshot
        or "execution_source" in release["snapshot"]
    ):
        raise DomainError("UNSUPPORTED_CAPABILITY", "Initial generated literal source only")
    # Literal AppRuns have zero model Attempts; their original generation history
    # is independently verified by read_release -> text_apps.verify_origin.
    if (
        c.execute(select(attempts.c.id).where(attempts.c.run_id == rid)).first()
        or store.has_unknown(c, rid)
        or job["context"]
        != {
            "kind": JOB_KIND,
            "messages": [],
            "requests": 0,
            "tools": 0,
            "repairs": 0,
            "reserved_tokens": 0,
        }
    ):
        raise DomainError(
            "VERIFICATION_FAILED", "Pure literal source has polluted or unresolved history"
        )
    verify(store, c, user, job, limits)
    records = [r for r in data_rows(c, iid) if r["run_id"] == actual["id"]]
    ops = c.execute(select(operations).where(operations.c.run_id == rid)).mappings().all()
    if len(records) != 1 or len(ops) != 1 or ops[0]["call_id"] != "instance_result":
        raise DomainError("VERSION_CONFLICT", "One exact source record and operation required")
    binding = (
        c.execute(select(internal_run_bindings).where(internal_run_bindings.c.run_id == rid))
        .mappings()
        .one()
    )
    contract = (
        c.execute(select(run_contracts).where(run_contracts.c.run_id == rid)).mappings().one()
    )
    resource = candidate["manifest"]["data_bindings"][0]["resource_ref"]
    proof = {
        "kind": TEXT_PROOF,
        "source_run_id": rid,
        "instance_id": iid,
        "app_run_id": actual["id"],
        "release_id": release["id"],
        "project_id": snapshot["project_id"],
        "principal_id": user,
        "run_version": job["version"],
        "run_fingerprint": job["fingerprint"],
        "binding_fingerprint": binding["fingerprint"],
        "contract_fingerprint": contract["fingerprint"],
        "release_fingerprint": release["fingerprint"],
        "candidate_fingerprint": draft["fingerprint"],
        "input_fingerprint": fingerprint(snapshot["input"]),
        "output_fingerprint": fingerprint(actual["output"]),
        "receipt_fingerprint": fingerprint(ops[0]["receipt"]),
        "record_fingerprint": fingerprint(dict(records[0])),
        "source_resource_id": resource,
        "source_hash": candidate["source_hash"],
        "source_revision": 1,
        "generation": copy.deepcopy(candidate["goal_application"]),
        "literal_attempt_count": 0,
        "literal_attempts_fingerprint": fingerprint([]),
        "tool": {"ref": "text.literal_evidence", "version": "1", "effect": "read"},
        "check": {"ref": "source.literal_evidence.v1", "status": "PASS"},
        "generator": TEXT_GENERATOR,
        "semantic_goal_acceptance": "NOT_RUN",
        "model_requests": 0,
        "parameter_scope": {
            "creation": ["new_txt_md_binding_in_existing_authorization_domain"],
            "runtime": ["term"],
        },
    }
    return draft, proof


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
    location = (
        c.execute(
            select(app_drafts).where(
                app_drafts.c.id == aid, app_drafts.c.project_id == source["project_id"]
            )
        )
        .mappings()
        .first()
    )
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
    text = source["candidate"]["actions"][0]["executor"]["ref"] == "text.literal_evidence"
    ref = "text.literal_evidence" if text else "data.aggregate_csv"
    if action.executor.kind != "registered_tool" or action.executor.ref != ref:
        raise DomainError("UNSUPPORTED_CAPABILITY")
    from .agent_apps import existing_runtime

    existing_runtime(store, c, user, source["project_id"], target["runtime_id"])
    project = store.own_project(c, user, source["project_id"])
    rid = manifest.data_bindings[0].resource_ref
    if not text:
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
    if (
        material["format"] not in ({"txt", "md"} if text else {"csv"})
        or material["hash"] == source["candidate"]["source_hash"]
    ):
        raise DomainError("INVALID_INPUT", "Different already-authorized material required")
    if text and (
        len(material["content"].encode()) > 4096 or len(material["content"].splitlines()) > 64
    ):
        raise DomainError("INVALID_INPUT", "Finite TXT/MD required")
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
        source, proof = verified_source(store, c, user, iid, rid, limits)
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
                "NEEDS_INPUT",
                "Existing authorized app bound to different compatible material required",
            )
        return _envelope(
            proof=proof,
            source_proof_fingerprint=fingerprint(proof),
            proof_fingerprint=fingerprint(proof),
            targets=targets,
            generator=proof["generator"],
            owner_acceptance="PENDING",
            technical_semantic_status="UNKNOWN",
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


def _candidate(source, proof, target, aid=None, action_id=None, extraction_request=None):
    from .contracts import Limits

    if proof["kind"] == TEXT_PROOF:
        candidate = copy.deepcopy(source["candidate"])
        candidate.pop("goal_application")
        manifest, action = candidate["manifest"], candidate["actions"][0]
        manifest["app_id"], action["action_id"] = (
            aid or new_id("app"),
            action_id or new_id("action"),
        )
        manifest["action_bindings"][0]["action_id"] = action["action_id"]
        rid = target["resource_id"]
        manifest["data_bindings"][0]["resource_ref"] = rid
        for spec in (manifest, action):
            for permission in spec["permission_requirements"]:
                permission["resource_ref"] = rid
        action["dependencies"][0]["ref"] = rid
        for dependency in manifest["dependency_lock"]:
            if dependency["kind"] == "resource":
                dependency["ref"] = rid
        candidate["source_hash"] = target["source_hash"]
    else:
        candidate = csv_candidate(
            target["resource_id"],
            target["source_hash"],
            "",
            Limits(**source["candidate"]["manifest"]["runtime_limits"]),
        )
    if aid is not None and proof["kind"] != TEXT_PROOF:
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
        "generator": proof["generator"],
    }
    if proof["kind"] == TEXT_PROOF:
        if not isinstance(extraction_request, dict):
            raise DomainError("VERSION_CONFLICT", "Exact text extraction request required")
        candidate["task_proof"]["extraction_request"] = copy.deepcopy(extraction_request)
    return candidate


def _result(draft, proof, target, cached):
    return _envelope(
        id=draft["id"],
        candidate_fingerprint=draft["fingerprint"],
        cached=cached,
        source_proof_fingerprint=fingerprint(proof),
        target_resource_hash=target["source_hash"],
        authorization_domain=target["runtime_id"],
        generator=proof["generator"],
        owner_acceptance="PENDING",
        technical_semantic_status="UNKNOWN",
        source_run_id=proof["source_run_id"],
        instance_id=proof["instance_id"],
        principal_id=proof["principal_id"],
        project_id=proof["project_id"],
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
        source, proof = verified_source(store, c, user, iid, rid, limits)
        target, _ = _target(store, c, user, source, target_app_id, limits)
        if fingerprint(proof) != expected_proof_fp or target["fingerprint"] != expected_target_fp:
            raise DomainError("VERSION_CONFLICT")
        request = _request(iid, rid, expected_proof_fp, target_app_id, expected_target_fp, name)
        request_fp = fingerprint(request)
        intent = None
        if proof["kind"] == TEXT_PROOF:
            from .registered_request_recovery import guard

            intent = guard(c, user, iid, rid, key, source, request)
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
            if intent is not None:
                if intent["state"] != "COMMITTED":
                    raise DomainError("VERSION_CONFLICT")
                from .registered_request_recovery import committed

                committed(c, intent, draft)
            return {
                **_result(draft, proof, target, True),
                "request_key": key,
                "request_fingerprint": request_fp,
            }
        if intent is not None and intent["state"] != "PREPARED":
            raise DomainError("VERSION_CONFLICT")
        candidate = _candidate(
            source, proof, target, extraction_request={**request, "request_key": key}
        )
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
                    "kind": TEXT_KIND if proof["kind"] == TEXT_PROOF else KIND,
                    "proof": proof,
                    "target": target,
                    "request": request,
                    "candidate_fingerprint": draft["fingerprint"],
                },
            )
        )
        if intent is not None:
            from .registered_request_recovery import committed

            committed(c, intent, draft)
        return {
            **_result(draft, proof, target, False),
            "request_key": key,
            "request_fingerprint": request_fp,
        }


def recover(store, user, iid, rid, key, limits, *, require_latest=False):
    """Read an existing exact-key receipt; never creates or resubmits an extraction."""
    if not isinstance(key, str) or not 1 <= len(key) <= 100:
        raise DomainError("INVALID_INPUT")
    with store.tx() as c:
        pid = c.execute(
            select(runs.c.project_id).where(runs.c.id == rid, runs.c.principal_id == user)
        ).scalar()
        store.lock_project(c, user, pid)
        source, proof = verified_source(store, c, user, iid, rid, limits)
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
        if not old:
            raise DomainError(
                "RESOURCE_UNAVAILABLE", "No extraction accepted with this original key"
            )
        draft, _, _, _ = load_draft(store, c, user, old["app_id"], limits)
        request = old["snapshot"]["request"]
        if request["instance_id"] != iid:
            raise DomainError("PERMISSION_DENIED")
        target, _ = _target(store, c, user, source, request["target_app_id"], limits)
        latest = {}
        if require_latest:
            if proof["kind"] != TEXT_PROOF:
                raise DomainError("UNSUPPORTED_CAPABILITY")
            from .registered_request_recovery import guard

            row = guard(c, user, iid, rid, key, source, request)
            if (row["state"] != "COMMITTED" or row["app_id"] != draft["id"]
                    or row["candidate_fingerprint"] != draft["fingerprint"]):
                raise DomainError("VERSION_CONFLICT")
            latest = {"latest_verified": True, "latest_request_key": key,
                      "journal_sequence": row["sequence"]}
        return {
            **_result(draft, proof, target, True),
            "request_key": key,
            "request_fingerprint": old["request_fingerprint"],
            **latest,
        }


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
        or snap["kind"] not in {KIND, TEXT_KIND}
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
    source, proof = verified_source(store, c, user, req["instance_id"], saved["task_id"], limits)
    target, _ = _target(store, c, user, source, req["target_app_id"], limits)
    if (
        snap["kind"] != (TEXT_KIND if proof["kind"] == TEXT_PROOF else KIND)
        or proof != snap["proof"]
        or fingerprint(proof) != req["expected_proof_fingerprint"]
        or target != snap["target"]
        or target["fingerprint"] != req["expected_target_draft_fingerprint"]
        or source["project_id"] != draft["project_id"]
        or target["runtime_id"] != draft["runtime_id"]
        or snap["candidate_fingerprint"] != draft["fingerprint"]
    ):
        raise DomainError("VERSION_CONFLICT", "Accepted source/target changed")
    expected = _candidate(
        source,
        proof,
        target,
        draft["id"],
        draft["candidate"]["actions"][0]["action_id"],
        extraction_request={**req, "request_key": saved["request_key"]},
    )
    if expected != draft["candidate"]:
        raise DomainError("VERSION_CONFLICT", "Candidate differs from trusted source derivation")
