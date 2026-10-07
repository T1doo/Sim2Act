import json
import math
import re
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .errors import DomainError

ID = r"^[a-z]+_[a-f0-9]{32}$"


class RunState(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_INPUT = "WAITING_INPUT"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    WAITING_RESOURCE = "WAITING_RESOURCE"
    PAUSE_REQUESTED = "PAUSE_REQUESTED"
    PAUSED = "PAUSED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    RECONCILING = "RECONCILING"
    SUCCEEDED = "SUCCEEDED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class OperationState(StrEnum):
    PREPARED = "PREPARED"
    DISPATCHED = "DISPATCHED"
    RECEIPT_KNOWN = "RECEIPT_KNOWN"
    VERIFIED = "VERIFIED"
    FAILED_SAFE = "FAILED_SAFE"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    EFFECT_KNOWN_INVALID = "EFFECT_KNOWN_INVALID"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Limits(Strict):
    max_requests: int = Field(ge=1, le=4)
    max_tools: int = Field(ge=1, le=4)
    max_repairs: int = Field(ge=0, le=1)
    max_total_tokens: int = Field(ge=1, le=64000)
    max_output_tokens: int = Field(ge=1, le=1024)
    run_seconds: int = Field(ge=1, le=300)


class Executor(Strict):
    kind: Literal["registered_tool", "bounded_agent", "bounded_report"]
    ref: str
    version: Literal["1"]


class Dependency(Strict):
    kind: Literal["tool", "resource", "check", "prompt"]
    ref: str = Field(min_length=1, max_length=100)
    version: Literal["1"]


class PermissionRequirement(Strict):
    tool_ref: Literal["resource.read", "data.aggregate_csv", "artifact.save_text"]
    resource_ref: str = Field(pattern=r"^(res|proj)_[a-f0-9]{32}$")


class Precondition(Strict):
    op: Literal["exists", "eq", "in"]
    field: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
    value: Any = None


class View(Strict):
    component_ref: Literal["text", "table", "chart"]
    output_field: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")


class FieldSource(Strict):
    source: Literal["input", "step", "data"]
    ref: str | None = None
    field: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")


class WorkflowStep(Strict):
    step_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    binding_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    depends_on: list[str] = Field(max_length=16)
    inputs: dict[str, FieldSource] = Field(default_factory=dict, max_length=32)


class ActionBinding(Strict):
    binding_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    action_id: str = Field(pattern=r"^action_[a-f0-9]{32}$")
    revision: int = Field(ge=1)


class DataBinding(Strict):
    binding_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    resource_ref: str = Field(pattern=r"^res_[a-f0-9]{32}$")


class RuntimeIdentity(Strict):
    mode: Literal["user_and_app_intersection", "user_and_project_intersection"]


class ActionSpec(Strict):
    schema_version: Literal["1.0-draft"]
    action_id: str = Field(pattern=ID)
    revision: int = Field(ge=1)
    input_schema: dict
    output_schema: dict
    executor: Executor
    allowed_tool_refs: list[str]
    dependencies: list[Dependency] = Field(max_length=32)
    permission_requirements: list[PermissionRequirement] = Field(max_length=32)
    effect: Literal["read", "project_write", "external_write"]
    preconditions: list[Precondition] = Field(max_length=16)
    postcheck_refs: list[str]
    limits: Limits
    idempotency: Literal["read_only", "transactional"]
    reconcile_ref: Literal["operation.lookup.v1"]
    error_contract: list[str]


class AppManifest(Strict):
    schema_version: Literal["1.0-draft"]
    app_id: str = Field(pattern=ID)
    revision: int = Field(ge=1)
    origin: Literal["goal", "task_run"]
    goal_ref: str = Field(pattern=ID)
    source_run_ref: str | None = Field(default=None, pattern=ID)
    input_schema: dict
    output_schema: dict
    outputs: dict[str, FieldSource] = Field(default_factory=dict, max_length=32)
    views: list[View] = Field(max_length=16)
    workflow: list[WorkflowStep] = Field(max_length=16)
    action_bindings: list[ActionBinding] = Field(max_length=16)
    data_bindings: list[DataBinding] = Field(max_length=16)
    runtime_identity_requirements: RuntimeIdentity
    permission_requirements: list[PermissionRequirement] = Field(max_length=32)
    dependency_lock: list[Dependency] = Field(max_length=32)
    validation_suite_ref: str
    runtime_limits: Limits
    data_schema_version: int = Field(ge=1)


class GoalSpec(Strict):
    goal_id: str = Field(pattern=ID)
    project_id: str = Field(pattern=ID)
    owner_id: str = Field(pattern=ID)
    goal: str = Field(min_length=1, max_length=4000)
    constraints: list[str] = Field(max_length=16)
    acceptance_version: Literal["F1-tool-chain.v1"]
    resource_refs: list[str] = Field(max_length=8)
    unresolved: list[str] = Field(max_length=16)


class ResourceSnapshot(Strict):
    resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    revision: Literal[1]
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    format: Literal["txt", "md", "csv", "json"]


class GoalCardRunSource(Strict):
    card_id: str = Field(pattern=r"^goal_[a-f0-9]{32}$")
    version: int = Field(ge=1)
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    snapshot: dict


class FrozenRunContract(Strict):
    run_id: str = Field(pattern=r"^run_[a-f0-9]{32}$")
    # Existing project runtime or existing declarative app runtime; neither creates a grant.
    runtime_id: str = Field(pattern=r"^(runtime|appruntime)_[a-f0-9]{32}$")
    contract_version: Literal["F1.3"]
    goal: GoalSpec
    resources: list[ResourceSnapshot] = Field(max_length=8)
    limits: Limits
    mode: Literal["mock", "live"]
    request_model: Literal["intern-s2"]
    source_goal_card: GoalCardRunSource | None = None


class Run(Strict):
    run_id: str = Field(pattern=ID)
    project_id: str = Field(pattern=ID)
    principal_id: str = Field(pattern=ID)
    runtime_id: str = Field(pattern=ID)
    status: RunState
    input_snapshot: FrozenRunContract
    contract_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    fencing_token: int = Field(ge=0)
    cancel_intent: bool


class Operation(Strict):
    operation_id: str = Field(pattern=ID)
    run_id: str = Field(pattern=ID)
    request_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    status: OperationState
    receipt_ref: str | None


class Grant(Strict):
    grant_id: str = Field(pattern=ID)
    principal_id: str = Field(pattern=ID)
    project_id: str = Field(pattern=ID)
    resource_id: str = Field(pattern=ID)
    tool_ref: str
    expires_at: float
    revision: int = Field(ge=1)
    revoked: bool


class Approval(Strict):
    approval_id: str = Field(pattern=ID)
    request_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    release_ref: str = Field(pattern=ID)
    resource_refs: list[str]
    data_version: int = Field(ge=1)
    principal_id: str = Field(pattern=ID)
    expires_at: float
    grant_revision: int = Field(ge=1)


def strict_json(raw: str | bytes, max_bytes: int = 65536) -> Any:
    if len(raw.encode() if isinstance(raw, str) else raw) > max_bytes:
        raise DomainError("INVALID_INPUT", "JSON exceeds size limit")

    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError("duplicate key")
            result[k] = v
        return result

    def constant(_):
        raise ValueError("nonfinite number")

    try:
        result = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)

        def depth(v, n=0):
            if n > 20:
                raise ValueError("depth")
            if isinstance(v, float) and not math.isfinite(v):
                raise ValueError("nonfinite")
            if isinstance(v, dict):
                for child in v.values():
                    depth(child, n + 1)
            if isinstance(v, list):
                for child in v:
                    depth(child, n + 1)

        depth(result)
        return result
    except (ValueError, TypeError, RecursionError) as e:
        raise DomainError("INVALID_INPUT", "Malformed, duplicate or oversized JSON") from e


def resource_id(value: str):
    if not re.fullmatch(r"res_[a-f0-9]{32}", value):
        raise DomainError("INVALID_INPUT", "Expected logical resource ID")
    return value


def schema_check(schema: dict, depth=0):
    if not isinstance(schema, dict) or depth > 8:
        raise DomainError("INVALID_MANIFEST", "Schema depth or shape invalid")
    common = {"type", "enum", "nullable"}
    if "nullable" in schema and (type(schema["nullable"]) is not bool or schema.get("type") not in {"boolean", "integer"}):
        raise DomainError("INVALID_MANIFEST", "Only explicitly typed boolean/integer may be nullable")
    by_type = {
        "object": {"properties", "required", "additionalProperties"},
        "array": {"items", "maxItems"},
        "string": {"maxLength"},
        "integer": {"minimum", "maximum"},
        "number": {"minimum", "maximum"},
        "boolean": set(),
        "null": set(),
    }
    kind = schema.get("type")
    if not isinstance(kind, str) or kind not in by_type or set(schema) - common - by_type[kind]:
        raise DomainError("INVALID_MANIFEST", "Unsupported schema keyword or type")
    if kind == "object":
        props, required = schema.get("properties", {}), schema.get("required", [])
        if (
            schema.get("additionalProperties") is not False
            or not isinstance(props, dict)
            or len(props) > 32
        ):
            raise DomainError("INVALID_MANIFEST", "Closed bounded object required")
        if (
            not isinstance(required, list)
            or any(not isinstance(x, str) for x in required)
            or len(set(required)) != len(required)
            or set(required) - set(props)
        ):
            raise DomainError("INVALID_MANIFEST", "Required fields must exist and be unique")
        for name, child in props.items():
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", name):
                raise DomainError("INVALID_MANIFEST", "Invalid field name")
            schema_check(child, depth + 1)
    if kind == "array":
        if "items" not in schema:
            raise DomainError("INVALID_MANIFEST", "Typed array items required")
        schema_check(schema["items"], depth + 1)
    for key, cap in [("maxLength", 32768), ("maxItems", 1000)]:
        if key in schema and (type(schema[key]) is not int or not 0 <= schema[key] <= cap):
            raise DomainError("INVALID_MANIFEST", "Schema limit cannot raise platform cap")
    for key in ["minimum", "maximum"]:
        if key in schema and (
            type(schema[key]) not in {int, float} or not math.isfinite(schema[key])
        ):
            raise DomainError("INVALID_MANIFEST", "Numeric bound must be finite")
    if "minimum" in schema and "maximum" in schema and schema["minimum"] > schema["maximum"]:
        raise DomainError("INVALID_MANIFEST", "Inverted numeric bounds")
    if "enum" in schema:
        vals = schema["enum"]
        if (
            not isinstance(vals, list)
            or not 1 <= len(vals) <= 20
            or len({json.dumps(x, sort_keys=True) for x in vals}) != len(vals)
        ):
            raise DomainError("INVALID_MANIFEST", "Enum must be bounded and unique")
        for value in vals:
            validate_value({k: v for k, v in schema.items() if k != "enum"}, value)


def validate_value(schema: dict, value, path="input"):
    kind = schema["type"]
    if value is None and schema.get("nullable") is True:
        if "enum" not in schema or any(x is None for x in schema["enum"]):
            return
        raise DomainError("INVALID_INPUT", path + " outside enum")
    valid = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": type(value) is int,
        "number": type(value) in {int, float} and math.isfinite(value),
        "boolean": type(value) is bool,
        "null": value is None,
    }
    if not valid[kind]:
        raise DomainError("INVALID_INPUT", path + " has wrong type")
    if "enum" in schema and not any(type(value) is type(x) and value == x for x in schema["enum"]):
        raise DomainError("INVALID_INPUT", path + " outside enum")
    if kind == "object":
        props = schema.get("properties", {})
        if set(value) - set(props) or set(schema.get("required", [])) - set(value):
            raise DomainError("INVALID_INPUT", path + " has unknown or missing field")
        for key, child in value.items():
            validate_value(props[key], child, path + "." + key)
    if kind == "array":
        if len(value) > schema.get("maxItems", 1000):
            raise DomainError("INVALID_INPUT", "Array exceeds limit")
        for item in value:
            validate_value(schema["items"], item, path + "[]")
    if kind == "string" and len(value) > schema.get("maxLength", 32768):
        raise DomainError("INVALID_INPUT", "String exceeds limit")
    if kind in {"integer", "number"} and (
        value < schema.get("minimum", value) or value > schema.get("maximum", value)
    ):
        raise DomainError("INVALID_INPUT", "Number outside bounds")


def check_dependencies(dependencies):
    registry = {
        "tool": {"resource.read", "data.aggregate_csv", "artifact.save_text"},
        "check": {"receipt.readback.v1", "source.literal_evidence.v1", "source.conditional_report.v1"},
        "prompt": {"intern.system.v1"},
    }
    seen = set()
    for d in dependencies:
        if (d.kind, d.ref) in seen:
            raise DomainError("INVALID_MANIFEST", "Duplicate dependency")
        seen.add((d.kind, d.ref))
        if d.kind == "resource":
            resource_id(d.ref)
        elif d.ref not in registry[d.kind]:
            raise DomainError("INVALID_MANIFEST", "Unregistered dependency")


def validate_action(raw: str):
    try:
        action = ActionSpec.model_validate(strict_json(raw))
        tools = {"resource.read", "data.aggregate_csv", "artifact.save_text"}
        executors = tools if action.executor.kind == "registered_tool" else ({"intern.conditional_report"} if action.executor.kind == "bounded_report" else {"intern.agent"})
        if action.executor.kind == "bounded_report" and action.allowed_tool_refs != ["resource.read"]:
            raise ValueError("Report executor has only a fixed read capability")
        if (
            action.executor.ref not in executors
            or set(action.allowed_tool_refs) - tools
            or len(set(action.allowed_tool_refs)) != len(action.allowed_tool_refs)
        ):
            raise ValueError("Unknown or duplicate registered reference")
        effective = (
            set(action.allowed_tool_refs)
            if action.executor.kind in {"bounded_agent", "bounded_report"}
            else {action.executor.ref}
        )
        if action.executor.kind == "registered_tool" and set(action.allowed_tool_refs) - effective:
            raise ValueError("Registered executor cannot dispatch other tools")
        writes = "artifact.save_text" in effective
        if (
            action.effect == "external_write"
            or (writes and action.effect != "project_write")
            or (not writes and action.effect != "read")
        ):
            raise ValueError("Effect must match registered capabilities")
        if action.idempotency != ("transactional" if writes else "read_only"):
            raise ValueError("Idempotency must match trusted effect")
        valid_checks = [["source.conditional_report.v1"]] if action.executor.kind == "bounded_report" else [["receipt.readback.v1"], ["source.literal_evidence.v1"]]
        if action.postcheck_refs not in valid_checks:
            raise ValueError("Independent receipt check required")
        check_dependencies(action.dependencies)
        for req in action.permission_requirements:
            prerequisite_read = (
                req.tool_ref == "resource.read" and "data.aggregate_csv" in effective
            )
            if (
                req.tool_ref not in effective and not prerequisite_read
            ) or req.resource_ref.startswith("proj_") != (req.tool_ref == "artifact.save_text"):
                raise ValueError("Permission request cannot broaden executor")
        schema_check(action.input_schema)
        schema_check(action.output_schema)
        for condition in action.preconditions:
            props = action.input_schema.get("properties", {})
            if condition.field not in props:
                raise ValueError("Condition references missing input")
            if condition.op == "exists":
                if condition.value is not None:
                    raise ValueError("Exists condition has no value")
            elif condition.op == "in":
                if not isinstance(condition.value, list) or not 1 <= len(condition.value) <= 20:
                    raise ValueError("Membership condition must be finite")
                for value in condition.value:
                    validate_value(props[condition.field], value)
            else:
                validate_value(props[condition.field], condition.value)
        return action
    except (ValueError, KeyError, TypeError, DomainError) as e:
        raise DomainError("INVALID_MANIFEST", "Manifest failed strict F1 validation") from e


def validate_action_input(action: ActionSpec, value):
    validate_value(action.input_schema, value)
    for condition in action.preconditions:
        present = condition.field in value
        actual = value.get(condition.field)
        passed = (
            present
            if condition.op == "exists"
            else present
            and (actual in condition.value if condition.op == "in" else actual == condition.value)
        )
        if not passed:
            raise DomainError("INVALID_INPUT", "Declared precondition failed")


def validate_manifest(raw: str):
    try:
        manifest = AppManifest.model_validate(strict_json(raw))
        if manifest.origin == "task_run" and not manifest.source_run_ref:
            raise ValueError("Task origin must preserve source run")
        if manifest.origin == "goal" and manifest.source_run_ref:
            raise ValueError("Goal origin cannot claim task evidence")
        schema_check(manifest.input_schema)
        schema_check(manifest.output_schema)
        check_dependencies(manifest.dependency_lock)
        bindings = {b.binding_id for b in manifest.action_bindings}
        steps = {s.step_id for s in manifest.workflow}
        if (
            len(bindings) != len(manifest.action_bindings)
            or len(steps) != len(manifest.workflow)
            or not steps
        ):
            raise ValueError("Workflow and binding IDs must be unique and nonempty")
        known: set[str] = set()
        pending = list(manifest.workflow)
        while pending:
            ready = [s for s in pending if set(s.depends_on) <= known]
            if not ready:
                raise ValueError("Cycle or unknown predecessor")
            for step in ready:
                if step.binding_id not in bindings or len(set(step.depends_on)) != len(
                    step.depends_on
                ):
                    raise ValueError("Unknown action binding or duplicate edge")
                known.add(step.step_id)
                pending.remove(step)
        for view in manifest.views:
            if view.output_field not in manifest.output_schema.get("properties", {}):
                raise ValueError("View references missing output")
        if manifest.validation_suite_ref not in {"receipt.readback.v1", "source.literal_evidence.v1", "source.conditional_report.v1"}:
            raise ValueError("Unknown independent check suite")
        return manifest
    except (ValueError, KeyError, TypeError, DomainError) as e:
        raise DomainError("INVALID_MANIFEST", "Draft manifest failed structural validation") from e
