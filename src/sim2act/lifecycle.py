"""Internal F2-T08 services; authenticated engineering adapter, no formal publication.

Existing principals/grants only; typed result-ledger data, no arbitrary business writes.
"""

import copy
import time
from typing import Any

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
MAX_LOGIC_SOURCE_DEPTH = 16


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


def execute(store, c, user, draft, limits, input_value, replay=None):
    from .text_continuations import no_context

    no_context(store, c, user, draft)
    _, manifest, action, _ = validate_frozen_candidate(store, c, user, draft, limits)
    from . import pa_spec_apps
    if pa_spec_apps.is_candidate(draft["candidate"]):
        _, _, source, _ = pa_spec_apps.verify_origin(store, c, user, draft, limits)
        return pa_spec_apps.preview(source, draft["candidate"], input_value)
    from . import text_workflows

    if text_workflows.is_candidate(draft["candidate"]):
        _, _, source, _ = text_workflows.verify_origin(store, c, user, draft, limits)
        return text_workflows.preview(source, draft["candidate"], input_value)
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
    if action.executor.kind == "bounded_agent":
        from .agent_apps import execute_protocol

        return execute_protocol(
            {"source": source, "args": args, "action": action.model_dump()},
            replay,
            lambda call_args: authorized_read(
                store, c, user, draft["runtime_id"], draft["project_id"], "resource.read", call_args
            ),
        )
    if action.executor.ref == "text.literal_evidence":
        from .text_apps import compute

        return compute(source, args)
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
            select(internal_approvals).where(internal_approvals.c.id == aid,
                internal_approvals.c.principal_id == user).with_for_update()
        )
        .mappings()
        .first()
    )
    if not row or row["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    p = row["payload"]
    if (
        not isinstance(p, dict)
        or not {"kind", "approval_id", "principal_id", "project_id", "expires_at"} <= p.keys()
        or row["kind"] != kind
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
    replay=None,
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
        draft, _, action, report = load_draft(store, c, user, aid, limits, lock=True)
        if draft["fingerprint"] != expected_draft_fp:
            raise DomainError("VERSION_CONFLICT")
        agent = action.executor.kind == "bounded_agent"
        if (agent and replay is None) or (not agent and replay is not None):
            raise DomainError("INVALID_INPUT", "Offline Replay required only for bounded agent")
        if agent:
            from .agent_apps import ReplayModel

            if type(replay) is not ReplayModel:
                raise DomainError("UNSUPPORTED_CAPABILITY", "Offline Replay only")
        replay_fp = fingerprint(replay.responses) if agent else None
        output = execute(store, c, user, draft, limits, sample_input, replay)
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
                "ref": (
                    "natural.recipe_compile.v1"
                    if draft["candidate"].get("namespace") == "pa-natural-spec-app.v1"
                    else
                    "spec.labeled_citations.v1"
                    if draft["candidate"].get("namespace") == "pa-spec-checklist-app.v1"
                    else
                    "text.four_step_readback.v1"
                    if draft["candidate"].get("namespace") == "closed-text-four-step.v1"
                    else
                    "source.literal_evidence.v1"
                    if action.executor.kind == "bounded_agent" or action.executor.ref == "text.literal_evidence"
                    else "csv.exact_integer_sum.v1"
                ),
                "status": "PASS",
                "candidate_fingerprint": expected_draft_fp,
                "input_fingerprint": fingerprint(sample_input),
                "output_fingerprint": fingerprint(output),
                "plan_fingerprint": fingerprint(report),
            },
            "model_requests": 0,
            "formal_publication_enabled": False,
        }
        if draft["candidate"].get("namespace") == "pa-natural-spec-app.v1":
            snapshot["check_evidence"].update(execution_mode="MODEL_EXECUTION_REQUIRED_OFF_BY_DEFAULT",
                citation_status="NOT_RUN", semantic_status="UNKNOWN", semantic_goal_acceptance="NOT_RUN")
        if agent:
            snapshot["check_evidence"].update(
                execution_mode="OFFLINE_REPLAY_ONLY",
                semantic_status="UNKNOWN",
                offline_replay_fingerprint=replay_fp,
            )
        return new_approval(
            c,
            user,
            pid,
            "release",
            {"snapshot": snapshot, "grant_version": grant_version(c, pid, user)},
        )


def commit_release(store, user, approval_id, exact_fp, limits):
    with store.tx() as c:
        return commit_release_tx(store, c, user, approval_id, exact_fp, limits)


def commit_release_tx(store, c, user, approval_id, exact_fp, limits, *, project_group=None):
    location = c.execute(
        select(internal_approvals.c.project_id).where(internal_approvals.c.id == approval_id)
    ).scalar()
    store.lock_project(c, user, location)
    from . import csv_goal_revisions as csv_revision
    csv_revision.release_gate(store,c,user,approval_id=approval_id)
    from . import csv_full_report_instances as full_report
    report = full_report.release_gate(store, c, user, approval_id=approval_id)
    a = approval(c, user, approval_id, exact_fp, "release", allow_consumed=True)
    if (a["payload"]["snapshot"].get("execution_source", {}).get("version") ==
            "internal.project-csv-read-sum-report.v1" and project_group is None):
        raise DomainError("PERMISSION_DENIED", "Confirm the exact whole project version group")
    if a["payload"].get("project_column_group") != project_group:
        raise DomainError("PERMISSION_DENIED", "Confirm the exact whole project version group")
    old = (
        c.execute(
            select(internal_releases).where(internal_releases.c.approval_id == approval_id)
        )
        .mappings()
        .first()
    )
    if old:
        return dict(read_release(store, c, user, old["id"], limits))
    if report is not None:
        return full_report.commit_release_tx(store, c, user, a)
    p = a["payload"]
    snap = p["snapshot"]
    draft = snap["draft"]
    from .csv_dag_instances import validate_family
    validate_family(c, user, approval_id, snap)
    from .natural_logic_patches import validate_family as validate_logic_family
    validate_logic_family(c,user,approval_id,snap)
    csv_revision.validate_family(c,user,approval_id,snap)
    current, _, _, _ = load_draft(store, c, user, draft["id"], limits, lock=True)
    validate_source_bytes(store, c, user, current)
    if (
        current["fingerprint"] != draft["fingerprint"]
        or grant_version(c, location, user) != p["grant_version"]
    ):
        raise DomainError("VERSION_CONFLICT", "Source or grant precondition changed")
    if "execution_source" in snap:
        from .csv_dag_instances import validate_snapshot
        validate_snapshot(store, c, user, snap, limits)
    if "natural_logic_source" in snap:
        from .natural_logic_patches import validate_snapshot as validate_logic
        validate_logic(store,c,user,snap,limits,commit=True)
    if csv_revision.SOURCE in snap:
        csv_revision.validate_snapshot(store,c,user,snap,limits,current=True)
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
    from . import text_logic_reuse

    if text_logic_reuse.independent(draft):
        text_logic_reuse.record_release_index(c, user, row)
    if csv_revision.SOURCE in snap:
        csv_revision.validate_snapshot(store,c,user,snap,limits,current=True)
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


def owned_release_pointer(store, c, user, rid):
    """Authorize identifiers before reading a Release body; never follow origins."""
    from .csv_full_report_instances import release_gate as report_gate
    from .text_continuations import release_gate

    report_gate(store, c, user, release_id=rid)
    release_gate(store, c, user, rid)
    r = c.execute(select(internal_releases).where(internal_releases.c.id == rid,
        internal_releases.c.principal_id == user)).mappings().first()
    if r is None:
        raise DomainError("PERMISSION_DENIED")
    store.own_project(c, user, r["project_id"])
    return r


def immutable_release_pointer(c, user, r):
    a = c.execute(select(internal_approvals).where(
        internal_approvals.c.id == r["approval_id"], internal_approvals.c.principal_id == user,
        internal_approvals.c.project_id == r["project_id"], internal_approvals.c.kind == "release")).mappings().first()
    if (not a or not a["consumed"] or a["kind"] != "release"
            or a["principal_id"] != user or a["project_id"] != r["project_id"]
            or not isinstance(a["payload"], dict) or fingerprint(a["payload"]) != a["fingerprint"]
            or a["payload"].get("snapshot") != r["snapshot"]
            or fingerprint(r["snapshot"]) != r["fingerprint"]):
        raise DomainError("VERSION_CONFLICT", "Immutable release/approval mismatch")


def owned_instance_pointer(store, c, user, iid, project=None):
    fields = (internal_instances.c.id, internal_instances.c.principal_id,
        internal_instances.c.project_id, internal_instances.c.source_app_id,
        internal_instances.c.runtime_id, internal_instances.c.release_id,
        internal_instances.c.revision, internal_instances.c.data_version)
    i = c.execute(select(*fields).where(internal_instances.c.id == iid,
        internal_instances.c.principal_id == user)).mappings().first()
    if i is None or (project is not None and i["project_id"] != project):
        raise DomainError("PERMISSION_DENIED")
    store.own_project(c, user, i["project_id"])
    from .text_continuations import release_gate

    release_gate(store, c, user, i["release_id"])
    return dict(i)


def logic_release_trace(store, c, user, root, *, proposed_instance=None):
    """Iterative traversal of actual recursive origins, including a proposed edge.

    This is only a metadata cycle gate. Full authority and Worker proofs still
    follow it; a valid graph never substitutes for validate_snapshot.
    """
    from .natural_logic_patches import VERSION

    current = root
    visited: set[str] = set()
    edges: list[dict[str, Any]] = []
    nodes: list[dict[str, Any]] = []
    while True:
        if current["id"] in visited:
            return dict(cyclic=True, over_limit=False, nodes=nodes, edges=edges)
        if len(visited) >= MAX_LOGIC_SOURCE_DEPTH:
            return dict(cyclic=False, over_limit=True, nodes=nodes, edges=edges)
        visited.add(current["id"])
        nodes.append(dict(release_id=current["id"], release_fingerprint=current["fingerprint"]))
        immutable_release_pointer(c, user, current)
        origin = current["snapshot"].get("natural_logic_source")
        if origin is None:
            return dict(cyclic=False, over_limit=False, nodes=nodes, edges=edges)
        if (not isinstance(origin, dict) or set(origin) != {"namespace", "instance_id",
                "preview_key", "preview_fingerprint", "check_fingerprint", "execution_digest"}
                or origin["namespace"] != VERSION or not isinstance(origin["instance_id"], str)):
            raise DomainError("VERSION_CONFLICT", "Invalid logic source pointer")
        i = owned_instance_pointer(store, c, user, origin["instance_id"], root["project_id"])
        next_id = root["id"] if i["id"] == proposed_instance else i["release_id"]
        edges.append(dict(release_id=current["id"], release_fingerprint=current["fingerprint"],
            origin=origin, instance=i, next_release_id=next_id))
        current = owned_release_pointer(store, c, user, next_id)
        if (current["project_id"] != i["project_id"]
                or current["snapshot"]["draft"]["id"] != i["source_app_id"]
                or current["snapshot"]["draft"]["runtime_id"] != i["runtime_id"]):
            raise DomainError("VERSION_CONFLICT", "Source instance binding changed")


def logic_source_hints(c, user, i):
    """Owned scalar indexes are discovery hints, never accepted source proofs."""
    from . import natural_logic_patches as logic
    from .db import delivery_graph_requests, internal_run_bindings, runs

    marker = delivery_graph_requests
    check_keys = set(c.execute(select(marker.c.app_id, marker.c.request_key).where(
        marker.c.principal_id == user, marker.c.kind.in_([logic.CHECK, logic.CHECK + "_seal"]),
        marker.c.snapshot["response"]["check_instance_id"].as_string() == i["id"])).all())
    # The accepted binding and independent JOB receipts retain the role even
    # when both CHECK indexes disappear. Read scoped identifiers, not wire bodies.
    check_keys.update(c.execute(select(
        internal_run_bindings.c.snapshot["logic_check"]["instance_id"].as_string(),
        internal_run_bindings.c.snapshot["logic_check"]["preview_key"].as_string()).join(
        runs, runs.c.id == internal_run_bindings.c.run_id).join(
        internal_app_runs, internal_app_runs.c.id == internal_run_bindings.c.app_run_id).where(
        runs.c.principal_id == user, runs.c.project_id == i["project_id"],
        internal_app_runs.c.principal_id == user, internal_app_runs.c.instance_id == i["id"],
        internal_run_bindings.c.snapshot["instance_id"].as_string() == i["id"],
        internal_run_bindings.c.snapshot["logic_check"]["instance_id"].as_string().is_not(None))).all())
    check_keys.update(c.execute(select(marker.c.snapshot["response"]["instance_id"].as_string(),
        marker.c.snapshot["response"]["preview_key"].as_string()).join(
        runs, marker.c.app_id == runs.c.id).join(internal_app_runs,
        runs.c.request_key == "internal:" + internal_app_runs.c.id).where(
        marker.c.principal_id == user, marker.c.kind.in_([logic.JOB, logic.JOB + "_seal"]),
        runs.c.principal_id == user, runs.c.project_id == i["project_id"],
        internal_app_runs.c.principal_id == user, internal_app_runs.c.instance_id == i["id"])).all())
    source_ids = set(c.execute(select(internal_releases.c.id).join(marker,
        internal_releases.c.approval_id == marker.c.snapshot["response"]["id"].as_string()).where(
        internal_releases.c.principal_id == user, internal_releases.c.project_id == i["project_id"],
        marker.c.principal_id == user, marker.c.app_id == i["id"],
        marker.c.kind.in_([logic.APPROVAL, logic.APPROVAL + "_seal"]))).scalars().all())
    source_ids.update(c.execute(select(internal_releases.c.id).where(
        internal_releases.c.principal_id == user, internal_releases.c.project_id == i["project_id"],
        internal_releases.c.snapshot["natural_logic_source"]["instance_id"].as_string() == i["id"])).scalars().all())
    # The immutable delivered snapshot also retains its isolated check identity.
    check_keys.update(c.execute(select(
        internal_releases.c.snapshot["natural_logic_source"]["instance_id"].as_string(),
        internal_releases.c.snapshot["natural_logic_source"]["preview_key"].as_string()).where(
        internal_releases.c.principal_id == user, internal_releases.c.project_id == i["project_id"],
        internal_releases.c.snapshot["check_evidence"]["check_instance_id"].as_string() == i["id"])).all())
    return dict(check_keys=check_keys, source_ids=source_ids)


def logic_source_pins(store, c, user, i):
    """Committed origins and accepted check instances are immutable evidence."""
    from . import natural_logic_patches as logic
    hints = logic_source_hints(c, user, i)
    check_keys = hints["check_keys"]
    if any(not isinstance(source, str) or not isinstance(key, str) for source, key in check_keys):
        raise DomainError("VERSION_CONFLICT", "Invalid check instance discovery hint")
    pins = []
    for source, key in sorted(set(check_keys)):
        owned_instance_pointer(store, c, user, source, i["project_id"])
        _, started = logic.pair(c, user, source, logic.CHECK, key, logic.Check)
        if started["check_instance_id"] != i["id"]:
            raise DomainError("VERSION_CONFLICT", "Check instance index changed")
        pins.append(dict(role="check", source_instance_id=source, preview_key=key,
            accepted_fingerprint=fingerprint(started)))
    # Either independent approval index can discover a delivered origin. A
    # missing/mutated counterpart must not silently remove its protection.
    released = hints["source_ids"]
    for rid in sorted(set(released)):
        r = owned_release_pointer(store, c, user, rid)
        immutable_release_pointer(c, user, r)
        logic.validate_family(c, user, r["approval_id"], r["snapshot"])
        origin = r["snapshot"]["natural_logic_source"]
        if origin["instance_id"] != i["id"]:
            raise DomainError("VERSION_CONFLICT", "Source instance index changed")
        pins.append(dict(role="source", release_id=rid, release_fingerprint=r["fingerprint"], origin=origin))
    return pins


def switch_preflight(store, c, user, iid, target_id, *, _state_out=None):
    i = owned_instance_pointer(store, c, user, iid)
    old = owned_release_pointer(store, c, user, i["release_id"])
    target = owned_release_pointer(store, c, user, target_id)
    if (target["project_id"] != i["project_id"] or target["snapshot"]["draft"]["id"] != i["source_app_id"]
            or target["snapshot"]["draft"]["runtime_id"] != i["runtime_id"]):
        raise DomainError("PERMISSION_DENIED", "Cannot switch another app/runtime into this instance")
    from .csv_full_report_instances import switch_preflight as report_preflight
    report_fp = report_preflight(store, c, user, i, old, target, state_out=_state_out)
    if report_fp is not None:
        return report_fp
    current_trace = logic_release_trace(store, c, user, old)
    target_trace = logic_release_trace(store, c, user, target, proposed_instance=iid)
    if current_trace["over_limit"] or target_trace["over_limit"]:
        raise DomainError("BUDGET_EXHAUSTED", "Logic source dependency exceeds finite depth")
    if current_trace["cyclic"] or target_trace["cyclic"]:
        raise DomainError("VERSION_CONFLICT", "Instance switch would create or retain a logic source cycle")
    from .project_natural_revalidation import pins as project_pins
    pins = logic_source_pins(store, c, user, i) + project_pins(c,user,i)
    from . import csv_goal_revisions as csv_revision
    pins += csv_revision.pins(c,user,iid)
    if pins:
        raise DomainError("VERSION_CONFLICT", "Instance supplies immutable logic source or check evidence")
    if csv_revision.SOURCE in target["snapshot"]:
        from .contracts import Limits
        ref = target["snapshot"][csv_revision.SOURCE]["reference"]
        # Use the exact frozen cap for this scope-only preflight. switch_target
        # repeats the check with current platform limits before adoption.
        csv_revision.source_gate(store,c,user,ref["instance_id"],ref["preview_key"])
        _,sealed = csv_revision.preview_pair(c,user,ref["instance_id"],ref["preview_key"])
        cap = Limits(**sealed["context"]["limits"])
        value = csv_revision.validate_snapshot(store,c,user,target["snapshot"],cap)
        csv_revision.eligibility(store,c,user,value,cap,i,target_id)
    state = dict(instance=i, current=current_trace, target=target_trace,
        target_id=target_id, target_fingerprint=target["fingerprint"], pins=pins)
    if _state_out is not None:
        _state_out.update(state)
    return fingerprint(state)


def switch_policy(store, c, user, i):
    # Role existence disables selection even if its proof is damaged. Preparing
    # a switch still verifies the full independent pairs and rejects corruption.
    hints = logic_source_hints(c, user, i)
    from .project_natural_revalidation import pins as project_pins
    roles = (["check"] if hints["check_keys"] else []) + (["source"] if hints["source_ids"] else [])
    roles += [x["role"] for x in project_pins(c,user,i)]
    from .csv_goal_revisions import pins as csv_goal_pins
    roles += [x["role"] for x in csv_goal_pins(c,user,i["id"])]
    targets = c.execute(select(internal_releases.c.id).where(
        internal_releases.c.principal_id == user, internal_releases.c.project_id == i["project_id"],
        internal_releases.c.snapshot["draft"]["id"].as_string() == i["source_app_id"])).scalars().all()
    blocked = []
    for rid in sorted(targets):
        if roles:
            blocked.append(rid)
        else:
            trace = logic_release_trace(store, c, user, owned_release_pointer(store, c, user, rid), proposed_instance=i["id"])
            if trace["cyclic"] or trace["over_limit"]:
                blocked.append(rid)
    return dict(namespace="internal.logic-switch-policy.v1", instance_id=i["id"], revision=i["revision"],
        roles=sorted(roles), blocked_release_ids=blocked)


def read_release(store, c, user, rid, limits, *, archival_software=None, _origin_out=None, _logic_out=None, _reuse_origin=None):
    epoch = c.info.get("source_proof_write_epoch", 0)
    with store.proof_authorities(c) as authorities:
        value = _read_release(store,c,user,rid,limits,archival_software=archival_software,
            _origin_out=_origin_out,_logic_out=_logic_out,_reuse_origin=_reuse_origin)
    if _logic_out is not None and _logic_out.get("_call_connection") is c:
        _logic_out["_call_authorities"] = tuple(sorted(authorities))
        _logic_out["_call_write_epoch"] = (epoch
            if epoch == c.info.get("source_proof_write_epoch",0) else None)
    return value


def _read_release(store, c, user, rid, limits, *, archival_software=None, _origin_out=None, _logic_out=None, _reuse_origin=None):
    r = owned_release_pointer(store, c, user, rid)
    if archival_software is not None:
        from .text_continuations import legacy_release

        legacy_release(store, c, user, r, limits, archival_software)
        return r
    immutable_release_pointer(c, user, r)
    from . import csv_full_report_instances as full_report
    if full_report.release_gate(store, c, user, release_id=rid) is not None:
        return full_report.validate_release(store, c, user, r)
    if "natural_logic_source" in r["snapshot"]:
        trace = logic_release_trace(store, c, user, r)
        if trace["over_limit"]:
            raise DomainError("BUDGET_EXHAUSTED", "Logic source dependency exceeds finite depth")
        if trace["cyclic"]:
            raise DomainError("VERSION_CONFLICT", "Logic source dependency cycle")
    s = r["snapshot"]
    draft = s["draft"]
    from .csv_dag_instances import FIXED_REPORT_VERSION, validate_family, validate_snapshot
    fixed_project_source = s.get("execution_source", {}).get("version") == FIXED_REPORT_VERSION
    if fixed_project_source:
        # This family must authorize the current source before protected
        # provenance ledgers, including cold release/peer/instance reads.
        validate_snapshot(store, c, user, s, limits)
    validate_family(c, user, r["approval_id"], s)
    from .natural_logic_patches import validate_family as validate_logic_family
    validate_logic_family(c,user,r["approval_id"],s)
    from . import csv_goal_revisions as csv_revision
    csv_revision.validate_family(c,user,r["approval_id"],s)
    if (
        s["namespace"] != NAMESPACE
        or s["formal_publication_enabled"] is not False
        or draft["project_id"] != r["project_id"]
        or s["dependency_lock"] != draft["candidate"]["manifest"]["dependency_lock"]
    ):
        raise DomainError("VERSION_CONFLICT")
    if "execution_source" in s:
        if not fixed_project_source:
            validate_snapshot(store, c, user, s, limits)
        return r
    record_schema(draft["candidate"], s["data_schema"])
    origin: dict[str, Any] = _origin_out if _origin_out is not None else {}
    validate_frozen_candidate(store, c, user, draft, limits, _origin_out=origin,_reuse_origin=_reuse_origin)
    validate_source_bytes(store, c, user, draft)
    if csv_revision.SOURCE in s:
        csv_revision.validate_snapshot(store,c,user,s,limits)
    if "natural_logic_source" in s:
        from .natural_logic_patches import validate_snapshot as validate_logic
        logic_value = validate_logic(store,c,user,s,limits,_verified_origin=origin)
        if _logic_out is not None:
            _logic_out.update(value=logic_value,principal_id=user,platform_limits=limits.model_dump(),
                release_id=rid,release_fingerprint=r["fingerprint"],
                _call_connection=c,_call_transaction=c.get_transaction(),
                _call_write_epoch=c.info.get("source_proof_write_epoch",0))
    from . import text_logic_reuse

    if text_logic_reuse.independent(draft):
        text_logic_reuse.verify_release_index(c, user, r)
    return r


def create_instance(store, user, rid, expected_release_fp, limits, *, request_key=None):
    with store.tx() as c:
        return create_instance_tx(store, c, user, rid, expected_release_fp, limits, request_key=request_key)


def create_instance_tx(store, c, user, rid, expected_release_fp, limits, *, request_key=None, _csv_goal_check=None):
    if request_key is not None and (
        not isinstance(request_key, str) or not 1 <= len(request_key) <= 100
    ):
        raise DomainError("INVALID_INPUT")
    location = c.execute(
        select(internal_releases.c.project_id).where(internal_releases.c.id == rid)
    ).scalar()
    store.lock_project(c, user, location)
    r = read_release(store, c, user, rid, limits)
    if r["fingerprint"] != expected_release_fp:
        raise DomainError("VERSION_CONFLICT")
    from .csv_goal_revisions import SOURCE
    if SOURCE in r["snapshot"]:
        from . import csv_goal_revisions as csv_revision
        if _csv_goal_check is None:
            raise DomainError("UNSUPPORTED_CAPABILITY", "Explicitly adopt this checked version on its original instance")
        ref = csv_revision.Reference.model_validate(_csv_goal_check.model_dump())
        _,value = csv_revision.load_preview(store,c,user,ref.instance_id,ref.preview_key,limits,current=True)
        csv_revision.extension(value["namespace"])
        if (ref.purpose != "CHECK"
                or ref != csv_revision.reference(ref.instance_id,ref.preview_key,value)
                or value["context"]["release_id"] != rid
                or request_key != "csv-goal-check:" + fingerprint([ref.instance_id,ref.preview_key])):
            raise DomainError("VERSION_CONFLICT", "Only the exact original isolated CSV CHECK may use this parent Release")
    draft = r["snapshot"]["draft"]
    from .text_continuations import no_context

    no_context(store, c, user, draft)
    # Existing PK plus project lock gives durable per-intent idempotency without new DDL.
    iid = (
        "iinstance_" + fingerprint({"user": user, "release": rid, "key": request_key})[:32]
        if request_key is not None
        else new_id("iinstance")
    )
    existing = (
        c.execute(select(internal_instances).where(internal_instances.c.id == iid))
        .mappings()
        .first()
    )
    if existing:
        if (
            existing["principal_id"] != user
            or existing["project_id"] != location
            or existing["release_id"] != rid
        ):
            raise DomainError("VERSION_CONFLICT")
        return dict(existing)
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


def instance(store, c, user, iid, limits, *, lock=False, _origin_out=None, _verified_origin=None, _logic_out=None):
    q = select(internal_instances).where(internal_instances.c.id == iid)
    i = c.execute(q.with_for_update() if lock else q).mappings().first()
    if not i or i["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    r = read_release(store, c, user, i["release_id"], limits, _origin_out=_origin_out,_reuse_origin=_verified_origin,_logic_out=_logic_out)
    if (
        r["project_id"] != i["project_id"]
        or r["snapshot"]["draft"]["id"] != i["source_app_id"]
        or r["snapshot"]["draft"]["runtime_id"] != i["runtime_id"]
    ):
        raise DomainError("VERSION_CONFLICT")
    from .csv_full_report_instances import is_snapshot, validate_instance_history
    if is_snapshot(r["snapshot"]):
        validate_instance_history(c, user, i, r)
    return i, r


def data_rows(c, iid, *, store=None, user=None, run_id=None):
    from .pb_natural_uses import data_scope_gate

    data_scope_gate(store, c, user, iid, app_run_id=run_id)
    from .csv_full_report_instances import data_scope_gate as report_data_gate
    report_data_gate(store, c, user, iid, app_run_id=run_id)
    if store is not None and user is not None:
        from .csv_goal_revisions import job_gate as csv_revision_gate
        from .db import internal_run_bindings
        job_ids = c.execute(select(internal_run_bindings.c.run_id)
            .join(internal_app_runs,internal_app_runs.c.id == internal_run_bindings.c.app_run_id)
            .where(internal_app_runs.c.instance_id == iid,
                *([] if run_id is None else [internal_app_runs.c.id == run_id]))).scalars().all()
        for job_id in job_ids:
            csv_revision_gate(store,c,user,job_id)
    rows = (
        c.execute(
            select(internal_instance_data)
            .where(internal_instance_data.c.instance_id == iid,
                *([] if run_id is None else [internal_instance_data.c.run_id == run_id]))
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
        i, release = instance(store, c, user, iid, limits)
        records = data_rows(c, iid, store=store, user=user)
        from . import csv_full_report_instances as full_report
        from . import pa_spec_apps, text_workflows
        if full_report.is_snapshot(release["snapshot"]):
            full_report.verify_records(store, c, user, i, records)
            return {**dict(i), "namespace": full_report.VERSION, "data": [dict(x) for x in records]}
        if pa_spec_apps.is_candidate(release["snapshot"]["draft"]["candidate"]):
            pa_spec_apps.verify_instance_records(store, c, user, i, records, limits)

        if text_workflows.is_candidate(release["snapshot"]["draft"]["candidate"]):
            text_workflows.verify_instance_records(store, c, user, i, records, limits)
        elif "execution_source" in release["snapshot"]:
            from .csv_dag_instances import check_instance_records
            check_instance_records(store, c, user, i, records, limits)
        elif release["snapshot"]["draft"]["candidate"]["actions"][0]["executor"]["ref"] == "text.literal_evidence":
            from .text_run_checks import verify_records

            verify_records(store, c, user, records, limits)
        return {**dict(i), "namespace": NAMESPACE, "data": [dict(x) for x in records],
            "switch_policy": switch_policy(store, c, user, i)}


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
        from .csv_full_report_instances import is_snapshot
        if is_snapshot(r["snapshot"]):
            raise DomainError("UNSUPPORTED_CAPABILITY", "Prepare and confirm the complete ordinary CSV contract")
        from .csv_goal_revisions import SOURCE
        from .csv_goal_revisions import pins as csv_goal_pins
        if SOURCE in r["snapshot"] or csv_goal_pins(c,user,iid):
            raise DomainError("UNSUPPORTED_CAPABILITY", "CSV Goal revisions require the durable AppRun Worker")
        if r["snapshot"]["draft"]["candidate"].get("namespace") == "closed-text-four-step.v1":
            raise DomainError("UNSUPPORTED_CAPABILITY", "Four-step text requires the durable AppRun worker")
        if "execution_source" in r["snapshot"]:
            raise DomainError("UNSUPPORTED_CAPABILITY", "DAG instances require the durable DAG worker")
        if r["snapshot"]["draft"]["candidate"]["actions"][0]["executor"]["ref"] == "text.literal_evidence":
            raise DomainError("UNSUPPORTED_CAPABILITY", "Literal instances require the durable AppRun worker")
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


def switch_target(store, c, user, i, old, target, limits):
    from .csv_full_report_instances import switch_preflight as report_preflight
    report_preflight(store, c, user, i, old, target)
    from . import csv_goal_revisions as csv_revision
    if csv_revision.SOURCE in target["snapshot"]:
        value = csv_revision.validate_snapshot(store,c,user,target["snapshot"],limits)
        csv_revision.eligibility(store,c,user,value,limits,i,target["id"])
    from .text_continuations import no_context

    no_context(store, c, user, old["snapshot"]["draft"])
    no_context(store, c, user, target["snapshot"]["draft"])
    if (
        target["project_id"] != i["project_id"]
        or target["snapshot"]["draft"]["id"] != i["source_app_id"]
        or target["snapshot"]["draft"]["runtime_id"] != i["runtime_id"]
    ):
        raise DomainError(
            "PERMISSION_DENIED", "Cannot switch another app/runtime into this instance"
        )
    if "execution_source" in old["snapshot"] or "execution_source" in target["snapshot"]:
        from .csv_dag_instances import validate_switch
        validate_switch(store, c, user, i, old, target, limits)
    compatible(old["snapshot"]["data_schema"], target["snapshot"]["data_schema"])
    same_schema = target["snapshot"]["data_schema"] == old["snapshot"]["data_schema"]
    old_version = old["snapshot"]["data_schema_version"]
    target_version = target["snapshot"]["data_schema_version"]
    if (same_schema and target_version != old_version) or (
        not same_schema and target_version <= old_version
    ):
        raise DomainError("VERSION_CONFLICT", "Unknown data version transition")
    records = data_rows(c, i["id"], store=store, user=user)
    for record in records:
        validate_value(target["snapshot"]["data_schema"], record["data"], "retained_data")
    return records


def prepare_switch(
    store, user, iid, target_id, expected_revision, limits, *, expected_target_fingerprint=None, _tx=None
):
    from contextlib import nullcontext
    with (nullcontext(_tx) if _tx is not None else store.tx()) as c:
        pid = c.execute(
            select(internal_instances.c.project_id).where(internal_instances.c.id == iid)
        ).scalar()
        store.lock_project(c, user, pid)
        dependency_fp = switch_preflight(store, c, user, iid, target_id)
        i, old = instance(store, c, user, iid, limits, lock=True)
        target = read_release(store, c, user, target_id, limits)
        if i["revision"] != expected_revision:
            raise DomainError("VERSION_CONFLICT")
        records = switch_target(store, c, user, i, old, target, limits)
        if (
            expected_target_fingerprint is not None
            and target["fingerprint"] != expected_target_fingerprint
        ):
            raise DomainError("VERSION_CONFLICT", "Selected target fingerprint changed")
        if switch_preflight(store, c, user, iid, target_id) != dependency_fp:
            raise DomainError("VERSION_CONFLICT", "Logic dependencies changed during switch preflight")
        return new_approval(
            c,
            user,
            pid,
            "switch",
            {
                "instance_id": iid,
                "from_release_id": old["id"],
                "logic_dependency_fingerprint": dependency_fp,
                "target_release_id": target_id,
                "target_fingerprint": target["fingerprint"],
                "revision": expected_revision,
                "data_version": i["data_version"],
                "data_fingerprint": fingerprint([dict(x) for x in records]),
                "grant_version": grant_version(c, pid, user),
            },
        )


def require_switch_payload(p):
    if (
        not {
            "instance_id",
            "logic_dependency_fingerprint",
            "from_release_id",
            "target_release_id",
            "target_fingerprint",
            "revision",
            "data_version",
            "data_fingerprint",
            "grant_version",
        }
        <= p.keys()
    ):
        raise DomainError("VERSION_CONFLICT", "Incomplete switch approval")
    ids = ["instance_id", "from_release_id", "target_release_id"]
    hashes = ["target_fingerprint", "data_fingerprint", "grant_version", "logic_dependency_fingerprint"]
    if (
        any(type(p[k]) is not str or not 1 <= len(p[k]) <= 100 for k in ids)
        or any(
            type(p[k]) is not str
            or len(p[k]) != 64
            or any(x not in "0123456789abcdef" for x in p[k])
            for k in hashes
        )
        or any(
            type(p[k]) is not int or p[k] < minimum
            for k, minimum in [("revision", 1), ("data_version", 0)]
        )
    ):
        raise DomainError("VERSION_CONFLICT", "Invalid switch approval shape")


def inspect_switch_approval(store, user, iid, aid, limits):
    with store.tx() as c:
        pid = c.execute(
            select(internal_instances.c.project_id).where(internal_instances.c.id == iid)
        ).scalar()
        store.lock_project(c, user, pid)
        row = (
            c.execute(select(internal_approvals).where(internal_approvals.c.id == aid,
                internal_approvals.c.principal_id == user, internal_approvals.c.project_id == pid,
                internal_approvals.c.kind == "switch"))
            .mappings()
            .first()
        )
        if not row or row["principal_id"] != user or row["project_id"] != pid:
            raise DomainError("PERMISSION_DENIED")
        a = approval(c, user, aid, row["fingerprint"], "switch")
        p = a["payload"]
        require_switch_payload(p)
        if p["instance_id"] != iid:
            raise DomainError("PERMISSION_DENIED")
        if switch_preflight(store, c, user, iid, p["target_release_id"]) != p["logic_dependency_fingerprint"]:
            raise DomainError("VERSION_CONFLICT", "Logic dependencies changed since switch approval")
        i, old = instance(store, c, user, iid, limits, lock=True)
        target = read_release(store, c, user, p["target_release_id"], limits)
        records = switch_target(store, c, user, i, old, target, limits)
        if (
            i["revision"] != p["revision"]
            or i["release_id"] != p["from_release_id"]
            or i["data_version"] != p["data_version"]
            or target["fingerprint"] != p["target_fingerprint"]
            or grant_version(c, pid, user) != p["grant_version"]
            or fingerprint([dict(x) for x in records]) != p["data_fingerprint"]
        ):
            raise DomainError("VERSION_CONFLICT", "Switch preconditions changed")
        if switch_preflight(store, c, user, iid, target["id"]) != p["logic_dependency_fingerprint"] or a["expires_at"] <= time.time():
            raise DomainError("VERSION_CONFLICT", "Logic dependencies changed during approval read")
        return {
            **dict(a),
            "retained_records": len(records),
            "from_schema_version": old["snapshot"]["data_schema_version"],
            "target_schema_version": target["snapshot"]["data_schema_version"],
            "data_preserved": True,
            "new_grants": False,
        }


def commit_switch(store, user, approval_id, exact_fp, limits, *, _tx=None):
    from contextlib import nullcontext
    with (nullcontext(_tx) if _tx is not None else store.tx()) as c:
        pid = c.execute(
            select(internal_approvals.c.project_id).where(internal_approvals.c.id == approval_id)
        ).scalar()
        store.lock_project(c, user, pid)
        a = approval(c, user, approval_id, exact_fp, "switch")
        p = a["payload"]
        require_switch_payload(p)
        instance_project = c.execute(
            select(internal_instances.c.project_id).where(
                internal_instances.c.id == p["instance_id"]
            )
        ).scalar()
        if instance_project != pid:
            raise DomainError("PERMISSION_DENIED", "Approval project differs from instance")
        transition: dict[str, Any] = {}
        if switch_preflight(store, c, user, p["instance_id"], p["target_release_id"], _state_out=transition) != p["logic_dependency_fingerprint"]:
            raise DomainError("VERSION_CONFLICT", "Logic dependencies changed since switch approval")
        i, old = instance(store, c, user, p["instance_id"], limits, lock=True)
        target = read_release(store, c, user, p["target_release_id"], limits)
        if (
            i["revision"] != p["revision"]
            or i["release_id"] != p["from_release_id"]
            or i["data_version"] != p["data_version"]
            or target["fingerprint"] != p["target_fingerprint"]
            or grant_version(c, pid, user) != p["grant_version"]
            or fingerprint([dict(x) for x in data_rows(c, i["id"], store=store, user=user)]) != p["data_fingerprint"]
        ):
            raise DomainError("VERSION_CONFLICT", "Switch preconditions changed")
        switch_target(store, c, user, i, old, target, limits)
        if switch_preflight(store, c, user, i["id"], target["id"]) != p["logic_dependency_fingerprint"] or a["expires_at"] <= time.time():
            raise DomainError("VERSION_CONFLICT", "Logic dependencies changed before switch commit")
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
        changed = c.execute(
            update(internal_instances)
            .where(internal_instances.c.id == i["id"], internal_instances.c.revision == p["revision"],
                internal_instances.c.release_id == p["from_release_id"], internal_instances.c.data_version == p["data_version"])
            .values(release_id=target["id"], revision=i["revision"] + 1, history=history)
        ).rowcount
        if changed != 1:
            raise DomainError("VERSION_CONFLICT", "Instance switch lost its compare-and-swap")
        c.execute(
            update(internal_approvals)
            .where(internal_approvals.c.id == approval_id)
            .values(consumed=True)
        )
        # Verify the actual post-state inside this transaction. Any late source,
        # authority, history or expiry failure rolls back pointer and consumption.
        read_release(store, c, user, target["id"], limits)
        after: dict[str, Any] = {}
        switch_preflight(store, c, user, i["id"], target["id"], _state_out=after)
        expected = copy.deepcopy(transition)
        expected["instance"].update(release_id=target["id"], revision=i["revision"] + 1)
        expected["current"] = expected["target"]
        stored_history = c.execute(select(internal_instances.c.history).where(internal_instances.c.id == i["id"])).scalar_one()
        committed_approval = approval(c, user, approval_id, exact_fp, "switch", allow_consumed=True)
        if (not committed_approval["consumed"] or committed_approval["expires_at"] <= time.time()
                or grant_version(c, i["project_id"], user) != p["grant_version"]
                or fingerprint(after) != fingerprint(expected) or stored_history != history
                or fingerprint([dict(x) for x in data_rows(c, i["id"], store=store, user=user)]) != p["data_fingerprint"]
                or a["expires_at"] <= time.time()):
            raise DomainError("VERSION_CONFLICT", "Switch postconditions changed before transaction commit")
        return {
            "instance_id": i["id"],
            "release_id": target["id"],
            "revision": i["revision"] + 1,
            "data_version": i["data_version"],
            "namespace": NAMESPACE,
        }
