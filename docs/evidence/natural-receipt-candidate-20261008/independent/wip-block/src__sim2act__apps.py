"""Bounded read-only declarative previews. No release, model or generated code executor."""

import json
import time

from sqlalchemy import insert, select

from .contracts import Limits, validate_action, validate_action_input, validate_value
from .db import (
    app_drafts,
    app_previews,
    fingerprint,
    goal_candidate_requests,
    grants,
    new_id,
    preview_extractions,
    principals,
    resources,
    task_extractions,
)
from .errors import DomainError
from .goals import validate_card_version
from .preflight import preflight
from .tools import authorized_read, csv_column_options, validate_call


def object_schema(properties):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def csv_candidate(rid, source_hash, goal, limits):
    """Fixed trusted template; caller supplies a goal label, never an executable prompt."""
    app_id, action_id = new_id("app"), new_id("action")
    text = {"type": "string"}
    action_input = object_schema({"resource_id": text, "column": text})
    output = object_schema(
        {
            "resource_id": text,
            "column": text,
            "count": {"type": "integer"},
            "sum": text,
            "source_hash": text,
        }
    )
    permissions = [
        {"tool_ref": tool, "resource_ref": rid} for tool in ("resource.read", "data.aggregate_csv")
    ]
    action = {
        "schema_version": "1.0-draft",
        "action_id": action_id,
        "revision": 1,
        "input_schema": action_input,
        "output_schema": output,
        "executor": {"kind": "registered_tool", "ref": "data.aggregate_csv", "version": "1"},
        "allowed_tool_refs": [],
        "dependencies": [{"kind": "resource", "ref": rid, "version": "1"}],
        "permission_requirements": permissions,
        "effect": "read",
        "preconditions": [],
        "postcheck_refs": ["receipt.readback.v1"],
        "limits": limits.model_dump(),
        "idempotency": "read_only",
        "reconcile_ref": "operation.lookup.v1",
        "error_contract": ["INVALID_INPUT", "PERMISSION_DENIED", "GRANT_REVOKED"],
    }
    manifest = {
        "schema_version": "1.0-draft",
        "app_id": app_id,
        "revision": 1,
        "origin": "goal",
        "goal_ref": new_id("goal"),
        "source_run_ref": None,
        "input_schema": object_schema({"column": text}),
        "output_schema": output,
        "outputs": {
            key: {"source": "step", "ref": "aggregate", "field": key}
            for key in output["properties"]
        },
        "views": [{"component_ref": "text", "output_field": "sum"}],
        "workflow": [
            {
                "step_id": "aggregate",
                "binding_id": "csv_sum",
                "depends_on": [],
                "inputs": {
                    "resource_id": {"source": "data", "ref": "source", "field": "resource_id"},
                    "column": {"source": "input", "field": "column"},
                },
            }
        ],
        "action_bindings": [{"binding_id": "csv_sum", "action_id": action_id, "revision": 1}],
        "data_bindings": [{"binding_id": "source", "resource_ref": rid}],
        "runtime_identity_requirements": {"mode": "user_and_app_intersection"},
        "permission_requirements": permissions,
        "dependency_lock": [
            {"kind": "resource", "ref": rid, "version": "1"},
            {"kind": "tool", "ref": "data.aggregate_csv", "version": "1"},
            {"kind": "check", "ref": "receipt.readback.v1", "version": "1"},
        ],
        "validation_suite_ref": "receipt.readback.v1",
        "runtime_limits": limits.model_dump(),
        "data_schema_version": 1,
    }
    return {
        "manifest": manifest,
        "actions": [action],
        "source_hash": source_hash,
        "goal": {
            "known": goal,
            "assumptions": ["所选列是有限十进制数"],
            "unresolved": ["仅固定模板，不是模型自主生成或发布验收"],
        },
    }


def authorize_source(store, c, user, project, rid, runtime):
    for tool in ("resource.read", "data.aggregate_csv"):
        store.authorize(c, user, project["runtime_id"], project["id"], rid, tool)
        if runtime != project["runtime_id"]:
            store.authorize(c, user, runtime, project["id"], rid, tool)


def create_csv_draft(store, user, pid, name, rid, goal, platform_limits):
    limits = Limits(
        max_requests=1,
        max_tools=1,
        max_repairs=0,
        max_total_tokens=1,
        max_output_tokens=1,
        run_seconds=1,
    )
    with store.tx() as c:
        project = store.lock_project(c, user, pid)
        authorize_source(store, c, user, project, rid, project["runtime_id"])
        source = authorized_read(
            store, c, user, project["runtime_id"], pid, "resource.read", {"resource_id": rid}
        )
        if source["format"] != "csv":
            raise DomainError("INVALID_INPUT", "请选择已授权的 CSV 材料")
        candidate = csv_candidate(rid, source["hash"], goal, limits)
        return persist_csv_candidate(c, project, name, rid, candidate, platform_limits)


def persist_csv_candidate(c, project, name, rid, candidate, platform_limits):
    # All production callers acquire this project before card/app/grant locks.
    from .db import projects
    from .tools import read_data

    c.execute(select(projects.c.id).where(projects.c.id == project["id"]).with_for_update()).one()
    source = read_data(c, rid, "resource.read", {"resource_id": rid})
    if source["format"] != "csv" or source["hash"] != candidate["source_hash"]:
        raise DomainError("VERSION_CONFLICT", "持久化前材料版本或退休状态已变化")
    compile_preview(candidate, platform_limits)
    aid = candidate["manifest"]["app_id"]
    runtime = new_id("appruntime")
    c.execute(insert(principals).values(id=runtime, name="read-only app preview"))
    # User explicitly selects this one resource in the create-and-authorize UI/API command.
    for tool in ("resource.read", "data.aggregate_csv"):
        c.execute(
            insert(grants).values(
                id=new_id("grant"),
                principal_id=runtime,
                project_id=project["id"],
                resource_id=rid,
                tool_ref=tool,
                expires_at=time.time() + 86400,
                revision=1,
                revoked=False,
            )
        )
    c.execute(
        insert(app_drafts).values(
            id=aid,
            project_id=project["id"],
            runtime_id=runtime,
            name=name,
            candidate=candidate,
            fingerprint=fingerprint(candidate),
            created_at=time.time(),
        )
    )
    return {"id": aid, "state": "PREVIEW_ONLY", "publishable": False}


def compile_preview(candidate, platform_limits):
    if isinstance(candidate, dict) and candidate.get("namespace") == "bounded-report-manifest.v1":
        from .report_manifest_apps import compile_report

        return compile_report(candidate, platform_limits)
    if (not isinstance(candidate, dict) or not isinstance(candidate.get("manifest"), dict)
            or not isinstance(candidate.get("actions"), list)
            or not 1 <= len(candidate["actions"]) <= 16):
        raise DomainError("INVALID_MANIFEST", "Closed candidate manifest/actions required")
    manifest, report = preflight(
        json.dumps(candidate["manifest"]), candidate["actions"], platform_limits
    )
    actions = [validate_action(json.dumps(a)) for a in candidate["actions"]]
    if any(a.executor.kind == "bounded_agent" for a in actions):
        from .agent_apps import compile_agent

        return compile_agent(candidate, manifest, actions, report)
    if (
        len(manifest.workflow) != 1
        or len(actions) != 1
        or actions[0].executor.kind != "registered_tool"
        or actions[0].executor.ref != "data.aggregate_csv"
        or len(manifest.data_bindings) != 1
    ):
        raise DomainError("UNSUPPORTED_CAPABILITY", "本轮仅支持单节点 CSV 汇总预览")
    # The advertised fixed capability includes wiring and schemas, not just the tool name.
    expected = csv_candidate(
        manifest.data_bindings[0].resource_ref,
        candidate["source_hash"],
        "",
        manifest.runtime_limits,
    )
    expected["manifest"]["app_id"] = manifest.app_id
    expected["manifest"]["goal_ref"] = manifest.goal_ref
    expected["actions"][0]["action_id"] = actions[0].action_id
    expected["manifest"]["action_bindings"][0]["action_id"] = actions[0].action_id
    expected["goal"] = candidate["goal"]
    if "generation" in candidate:
        expected["generation"] = candidate["generation"]
    if "extraction" in candidate:
        expected["extraction"] = candidate["extraction"]
        expected["manifest"]["origin"] = "task_run"
        expected["manifest"]["source_run_ref"] = manifest.source_run_ref
    if "task_proof" in candidate:
        expected["task_proof"] = candidate["task_proof"]
        expected["manifest"]["origin"] = "task_run"
        expected["manifest"]["source_run_ref"] = manifest.source_run_ref
    if candidate != expected:
        raise DomainError("UNSUPPORTED_CAPABILITY", "固定CSV能力的接线或声明已变化")
    return manifest, actions[0], report


def load_draft(store, c, user, aid, platform_limits, *, lock=False):
    query = select(app_drafts).where(app_drafts.c.id == aid)
    draft = c.execute(query.with_for_update() if lock else query).mappings().first()
    if not draft:
        raise DomainError("PERMISSION_DENIED")
    return validate_frozen_candidate(store, c, user, draft, platform_limits)


def validate_source_family(c, user, draft):
    """Bind dispatch to independent stored origin records before choosing an executor."""
    candidate = draft["candidate"]
    markers = []
    for table, field, kind in (
        (goal_candidate_requests, "generation", "registered_tool"),
        (preview_extractions, "extraction", "registered_tool"),
        (task_extractions, None, None),
    ):
        rows = c.execute(select(table).where(table.c.app_id == draft["id"])).mappings().all()
        for row in rows:
            expected_field, expected_kind = field, kind
            if table is task_extractions:
                snapshot = row["snapshot"]
                proof = snapshot.get("proof") if isinstance(snapshot, dict) else None
                if isinstance(snapshot, dict) and snapshot.get("kind") == "agent_source.v1":
                    expected_field, expected_kind = "agent_provenance", "bounded_agent"
                elif isinstance(snapshot, dict) and snapshot.get("kind") in {"registered_csv_source.v1", "natural_csv_receipt_candidate.v1"}:
                    expected_field, expected_kind = "task_proof", "registered_tool"
                elif (
                    isinstance(snapshot, dict)
                    and "kind" not in snapshot
                    and isinstance(proof, dict)
                    and proof.get("kind") == "completed_fixed_csv_task"
                ):
                    expected_field, expected_kind = "task_proof", "registered_tool"
                else:
                    raise DomainError(
                        "VERSION_CONFLICT", "Independent extraction marker kind changed"
                    )
            if row["principal_id"] != user:
                raise DomainError("VERSION_CONFLICT", "Independent extraction marker owner changed")
            markers.append((expected_field, expected_kind))
    if len(markers) > 1 or not isinstance(candidate, dict):
        raise DomainError("VERSION_CONFLICT", "Independent extraction marker conflict")
    claimed = {
        k for k in ("generation", "extraction", "task_proof", "agent_provenance") if k in candidate
    }
    expected = {markers[0][0]} if markers else set()
    if claimed != expected:
        raise DomainError(
            "VERSION_CONFLICT", "Independent extraction marker does not match candidate"
        )
    if markers:
        actions = candidate.get("actions")
        if not isinstance(actions, list) or not actions:
            raise DomainError("VERSION_CONFLICT", "Independent extraction marker executor missing")
        for action in actions:
            executor = action.get("executor") if isinstance(action, dict) else None
            if not isinstance(executor, dict) or executor.get("kind") != markers[0][1]:
                raise DomainError(
                    "VERSION_CONFLICT", "Independent extraction marker executor changed"
                )
    else:
        manifest = candidate.get("manifest")
        if (
            not isinstance(manifest, dict)
            or manifest.get("origin") != "goal"
            or manifest.get("source_run_ref") is not None
        ):
            raise DomainError(
                "VERSION_CONFLICT", "Independent extraction marker missing for task origin"
            )


def validate_frozen_candidate(store, c, user, draft, platform_limits):
    """Revalidate exact frozen specs and current grants without reading mutable draft content."""
    aid = draft["id"]
    project = store.own_project(c, user, draft["project_id"])
    candidate = draft["candidate"]
    if fingerprint(candidate) != draft["fingerprint"]:
        raise DomainError("VERSION_CONFLICT", "草案指纹已变化")
    validate_source_family(c, user, draft)
    manifest, action, report = compile_preview(candidate, platform_limits)
    if action.executor.kind == "bounded_agent":
        from .agent_apps import existing_runtime, validate_agent_origin

        existing_runtime(store, c, user, draft["project_id"], draft["runtime_id"])
        validate_agent_origin(store, c, user, draft, platform_limits)
        rid = manifest.data_bindings[0].resource_ref
        source = authorized_read(
            store,
            c,
            user,
            draft["runtime_id"],
            draft["project_id"],
            "resource.read",
            {"resource_id": rid},
        )
        if source["hash"] != candidate["source_hash"] or source["format"] not in {"txt", "md"}:
            raise DomainError("VERSION_CONFLICT", "Frozen agent source changed")
        return draft, manifest, action, report
    generated = (
        c.execute(select(goal_candidate_requests).where(goal_candidate_requests.c.app_id == aid))
        .mappings()
        .first()
    )
    if ("generation" in candidate) != bool(generated):
        raise DomainError("VERSION_CONFLICT", "目标候选来源记录不可移除或添加")
    if generated and (
        not isinstance(candidate["generation"], dict)
        or generated["card_id"] != candidate["generation"].get("goal_card_id")
        or generated["principal_id"] != user
    ):
        raise DomainError("VERSION_CONFLICT", "目标候选来源记录不可移除或替换")
    if generated:
        origin = candidate["generation"]
        accepted_request = fingerprint(
            {
                "card_id": generated["card_id"],
                "expected_version": origin.get("goal_version"),
                "resource_id": manifest.data_bindings[0].resource_ref,
                "capability": origin.get("capability"),
            }
        )
        # Compare to the independent accepted-request record, not the rewritten candidate hash.
        if accepted_request != generated["request_fingerprint"]:
            raise DomainError("VERSION_CONFLICT", "候选来源版本、材料或能力与已接受请求不一致")
    extracted = c.execute(
        select(preview_extractions.c.app_id).where(preview_extractions.c.app_id == aid)
    ).first()
    if extracted and "extraction" not in candidate:
        raise DomainError("VERSION_CONFLICT", "提取来源记录不可移除")
    if "extraction" in candidate:
        from .extraction import validate_extraction

        validate_extraction(store, c, user, draft, platform_limits)
    task_origin = c.execute(
        select(task_extractions).where(task_extractions.c.app_id == aid)
    ).mappings().first()
    if bool(task_origin) != ("task_proof" in candidate):
        raise DomainError("VERSION_CONFLICT", "完成任务来源不可添加或移除")
    if task_origin:
        if task_origin["snapshot"].get("kind") == "registered_csv_source.v1":
            from .registered_run_extraction import validate_registered_candidate

            validate_registered_candidate(store, c, user, draft, platform_limits)
        elif task_origin["snapshot"].get("kind") == "natural_csv_receipt_candidate.v1":
            from .natural_receipt_extraction import validate_candidate

            validate_candidate(store, c, user, draft, platform_limits)
        else:
            from .local_tasks import validate_task_candidate

            validate_task_candidate(store, c, user, draft)
    if "generation" in candidate:
        origin = candidate["generation"]
        old = validate_card_version(store, c, user, origin["goal_card_id"], origin["goal_version"])
        if (
            old["snapshot"] != origin["goal_snapshot"]
            or old["fingerprint"] != origin["goal_fingerprint"]
            or candidate["goal"] != old["snapshot"]["content"]
        ):
            raise DomainError("VERSION_CONFLICT", "候选目标来源不一致")
        if manifest.goal_ref != origin["goal_card_id"]:
            raise DomainError("VERSION_CONFLICT")
    rid = manifest.data_bindings[0].resource_ref
    if "generation" in candidate:
        frozen = next(
            (r for r in old["snapshot"]["resource_snapshots"] if r["resource_id"] == rid), None
        )
        if not frozen or frozen["format"] != "csv" or frozen["hash"] != candidate["source_hash"]:
            raise DomainError("VERSION_CONFLICT", "候选所选材料与来源不一致")
    authorize_source(store, c, user, project, rid, draft["runtime_id"])
    source = c.execute(select(resources).where(resources.c.id == rid)).mappings().one()
    if source["hash"] != candidate["source_hash"]:
        raise DomainError("VERSION_CONFLICT", "材料版本已变化，请重新创建草案")
    return draft, manifest, action, report


def preview(store, user, aid, input_value, key, platform_limits):
    with store.tx() as c:
        draft, manifest, action, report = load_draft(
            store, c, user, aid, platform_limits, lock=True
        )
        if action.executor.kind == "bounded_agent":
            raise DomainError("UNSUPPORTED_CAPABILITY", "Use internal offline AppRun service")
        fp = fingerprint({"candidate": draft["fingerprint"], "input": input_value})
        old = (
            c.execute(
                select(app_previews).where(
                    app_previews.c.app_id == aid,
                    app_previews.c.principal_id == user,
                    app_previews.c.request_key == key,
                )
            )
            .mappings()
            .first()
        )
        if old:
            if old["fingerprint"] != fp:
                raise DomainError("VERSION_CONFLICT", "请求键已绑定其他输入")
            return public_preview(old)
        output, error = None, None
        try:
            validate_value(manifest.input_schema, input_value)
            step = manifest.workflow[0]
            data = {d.binding_id: {"resource_id": d.resource_ref} for d in manifest.data_bindings}
            args = {
                field: (input_value if source.source == "input" else data[source.ref])[source.field]
                for field, source in step.inputs.items()
            }
            validate_action_input(action, args)
            validate_call(action.executor.ref, args)
            # Dynamic argument must remain within the compiled declaration and app grants.
            if args["resource_id"] != manifest.data_bindings[0].resource_ref:
                raise DomainError("PERMISSION_DENIED")
            value = authorized_read(
                store, c, user, draft["runtime_id"], draft["project_id"], action.executor.ref, args
            )
            validate_value(action.output_schema, value, "action_output")
            output = {field: value[source.field] for field, source in manifest.outputs.items()}
            validate_value(manifest.output_schema, output, "output")
        except DomainError as exc:
            error = exc.public()
        row = {
            "id": new_id("preview"),
            "app_id": aid,
            "principal_id": user,
            "request_key": key,
            "fingerprint": fp,
            "input": input_value,
            "status": "FAILED" if error else "SUCCEEDED",
            "output": output,
            "error": error,
            "created_at": time.time(),
        }
        c.execute(insert(app_previews).values(**row))
        return public_preview(row)


def public_preview(row):
    return {
        **dict(row),
        "namespace": "PREVIEW",
        "mode": "MOCK_ENGINEERING",
        "model_requests": 0,
        "business_writes": 0,
        "release_id": None,
        "check": "typed_output_and_source_hash" if row["status"] == "SUCCEEDED" else None,
    }


def inspect_draft(store, user, aid, platform_limits):
    with store.tx() as c:
        candidate = c.execute(select(app_drafts.c.candidate).where(app_drafts.c.id == aid)).scalar()
    if isinstance(candidate, dict) and candidate.get("namespace") == "bounded-report-manifest.v1":
        from .report_manifest_apps import inspect

        return inspect(store, user, aid, platform_limits)
    with store.tx() as c:
        draft, manifest, _, report = load_draft(store, c, user, aid, platform_limits)
        source = authorized_read(
            store,
            c,
            user,
            draft["runtime_id"],
            draft["project_id"],
            "resource.read",
            {"resource_id": manifest.data_bindings[0].resource_ref},
        )
        history = (
            c.execute(
                select(app_previews)
                .where(app_previews.c.app_id == aid, app_previews.c.principal_id == user)
                .order_by(app_previews.c.created_at.desc())
                .limit(50)
            )
            .mappings()
            .all()
        )
        return {
            **dict(draft),
            "state": "PREVIEW_ONLY",
            "publishable": False,
            "input_schema": manifest.input_schema,
            "validation": {
                k: report[k]
                for k in ("state", "execution_performed", "publishable", "topological_order")
            },
            "history": [public_preview(r) for r in history],
            "input_guidance": (
                csv_column_options(source["content"])
                if manifest.validation_suite_ref == "receipt.readback.v1"
                else {"mode": "OFFLINE_REPLAY_ONLY", "semantic_status": "UNKNOWN"}
            ),
        }
