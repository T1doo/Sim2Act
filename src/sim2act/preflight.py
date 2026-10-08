"""Draft-only static preflight. No executable plan, release or permission is created."""

import json

from .contracts import validate_action, validate_manifest
from .csv_reports import REF as CSV_REPORT
from .errors import DomainError


def preflight(raw, candidates, platform_limits):
    manifest = validate_manifest(raw)
    actions = {}
    for candidate in candidates:
        action = validate_action(json.dumps(candidate))
        action_key = (action.action_id, action.revision)
        if action_key in actions:
            raise DomainError("INVALID_MANIFEST", "Duplicate action revision")
        actions[action_key] = action
    report_only = bool(actions) and all(a.executor.kind == "bounded_report" for a in actions.values())
    if any(a.executor.kind == "bounded_report" for a in actions.values()):
        if not report_only or manifest.runtime_identity_requirements.mode != "user_and_project_intersection" or manifest.validation_suite_ref != "source.conditional_report.v1":
            raise DomainError("INVALID_MANIFEST", "Report preview has exact shared project runtime/check scope")
    elif manifest.runtime_identity_requirements.mode != "user_and_app_intersection":
        raise DomainError("INVALID_MANIFEST", "Existing families retain their application identity contract")
    bound = {}
    for binding in manifest.action_bindings:
        binding_key = (binding.action_id, binding.revision)
        if binding_key not in actions:
            raise DomainError("INVALID_MANIFEST", "Unresolved exact action revision")
        bound[binding.binding_id] = actions[binding_key]
    if set(actions) != {(b.action_id, b.revision) for b in manifest.action_bindings}:
        raise DomainError("INVALID_MANIFEST", "Unreferenced action candidate")
    data = {d.binding_id: d for d in manifest.data_bindings}
    if len(data) != len(manifest.data_bindings) or set(data) & set(bound):
        raise DomainError("INVALID_MANIFEST", "Ambiguous data binding")
    steps = {s.step_id: s for s in manifest.workflow}
    if set(bound) != {s.binding_id for s in manifest.workflow}:
        raise DomainError("INVALID_MANIFEST", "Unused action binding")
    order: list[str] = []
    pending = list(manifest.workflow)
    while pending:
        ready = [s for s in pending if set(s.depends_on) <= set(order)]
        for step in ready:
            order.append(step.step_id)
            pending.remove(step)
    permission_set = {(p.tool_ref, p.resource_ref) for p in manifest.permission_requirements}
    locks = {(d.kind, d.ref, d.version) for d in manifest.dependency_lock}
    required_locks = {("resource", d.resource_ref, "1") for d in data.values()}
    resources = {d.resource_ref for d in data.values()}
    required_permissions: set[tuple[str, str]] = set()
    budgets = dict.fromkeys(
        ["max_requests", "max_tools", "max_repairs", "max_total_tokens", "run_seconds"], 0
    )

    def source_schema(source, predecessors):
        if source.source == "input":
            if source.ref is not None:
                raise DomainError("INVALID_MANIFEST", "Input reference must omit ref")
            props = manifest.input_schema.get("properties", {})
            required = set(manifest.input_schema.get("required", []))
        elif source.source == "step":
            if source.ref not in predecessors:
                raise DomainError("INVALID_MANIFEST", "Data edge needs declared predecessor")
            action = bound[steps[source.ref].binding_id]
            props = action.output_schema.get("properties", {})
            required = set(action.output_schema.get("required", []))
        else:
            if source.ref not in data:
                raise DomainError("INVALID_MANIFEST", "Unresolved data binding")
            props = {"resource_id": {"type": "string"}}
            required = {"resource_id"}
        if source.field not in props or source.field not in required:
            raise DomainError("INVALID_MANIFEST", "Source field missing or not guaranteed")
        return props[source.field]

    for step in manifest.workflow:
        action = bound[step.binding_id]
        if action.input_schema["type"] != "object" or action.output_schema["type"] != "object":
            raise DomainError("INVALID_MANIFEST", "Preflight requires object node contracts")
        props = action.input_schema.get("properties", {})
        if set(step.inputs) - set(props) or set(action.input_schema.get("required", [])) - set(
            step.inputs
        ):
            raise DomainError("INVALID_MANIFEST", "Required input unconnected or unknown input")
        for field, source in step.inputs.items():
            if source_schema(source, set(step.depends_on)) != props[field]:
                raise DomainError("INVALID_MANIFEST", "Schema edge mismatch; no implicit coercion")
        required_locks.update((d.kind, d.ref, d.version) for d in action.dependencies)
        resources.update(d.ref for d in action.dependencies if d.kind == "resource")
        required_locks.add(
            ("tool", action.executor.ref, "1")
        ) if action.executor.kind == "registered_tool" else required_locks.add(
            ("prompt", "intern.system.v1", "1")
        )
        required_locks.update(("tool", t, "1") for t in action.allowed_tool_refs)
        action_permissions = {(p.tool_ref, p.resource_ref) for p in action.permission_requirements}
        scoped_resources = {ref for tool, ref in action_permissions if ref.startswith("res_")} | {
            d.ref for d in action.dependencies if d.kind == "resource"
        }
        effective_tools = (
            set(action.allowed_tool_refs)
            if action.executor.kind in {"bounded_agent", "bounded_report"}
            else {action.executor.ref}
        )
        if action.executor.kind == "registered_tool" and action.executor.ref == CSV_REPORT:
            # validate_action enforces the exact pure schema, empty read/write
            # scope and no delegated tools. Other capability checks stay intact.
            effective_tools = set()
        for tool in effective_tools:
            if tool == "artifact.save_text":
                if not any(t == tool and ref.startswith("proj_") for t, ref in action_permissions):
                    raise DomainError(
                        "INVALID_MANIFEST", "Write scope must be explicitly requested"
                    )
            elif not scoped_resources or any(
                (tool, ref) not in action_permissions
                or ("resource.read", ref) not in action_permissions
                for ref in scoped_resources
            ):
                raise DomainError(
                    "INVALID_MANIFEST", "Read capability requires complete static resource scope"
                )
        required_permissions.update(action_permissions)
        resources.update(scoped_resources)
        required_locks.update(("resource", ref, "1") for ref in scoped_resources)
        required_locks.update(("check", ref, "1") for ref in action.postcheck_refs)
        for key in budgets:
            budgets[key] += getattr(action.limits, key)
        if action.limits.max_output_tokens > manifest.runtime_limits.max_output_tokens:
            raise DomainError("BUDGET_EXHAUSTED", "Node output cap exceeds draft cap")
    if required_locks - locks or required_permissions - permission_set:
        raise DomainError("INVALID_MANIFEST", "Draft omitted dependency or permission request")
    if set(manifest.outputs) - set(manifest.output_schema.get("properties", {})) or set(
        manifest.output_schema.get("required", [])
    ) - set(manifest.outputs):
        raise DomainError("INVALID_MANIFEST", "Required output unconnected")
    for name, source in manifest.outputs.items():
        if source_schema(source, set(steps)) != manifest.output_schema["properties"][name]:
            raise DomainError("INVALID_MANIFEST", "Output schema edge mismatch")
    for key, count in budgets.items():
        if count > getattr(manifest.runtime_limits, key):
            raise DomainError("BUDGET_EXHAUSTED", "Conservative sum of node budgets exceeds draft")
    for key, count in manifest.runtime_limits.model_dump().items():
        if count > getattr(platform_limits, key):
            raise DomainError("BUDGET_EXHAUSTED", "Draft exceeds configured platform budget")
    return manifest, {
        "state": "PREFLIGHTED_DRAFT",
        "publishable": False,
        "execution_performed": False,
        "not_an_executable_plan": True,
        "topological_order": order,
        "budget_envelope": budgets,
        "resource_refs": sorted(resources),
        "candidate_fingerprint_basis": manifest.model_dump(),
    }
