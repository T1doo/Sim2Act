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
    kind: Literal["registered_tool", "bounded_agent"]
    ref: str
    version: Literal["1"]


class ActionSpec(Strict):
    schema_version: Literal["1.0-draft"]
    action_id: str = Field(pattern=ID)
    revision: int = Field(ge=1)
    input_schema: dict
    output_schema: dict
    executor: Executor
    allowed_tool_refs: list[str]
    dependencies: list[dict]
    permission_requirements: list[dict]
    effect: Literal["read", "project_write", "external_write"]
    preconditions: list[dict]
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
    views: list[dict]
    workflow: list[dict]
    action_bindings: list[dict]
    data_bindings: list[dict]
    runtime_identity_requirements: dict
    permission_requirements: list[dict]
    dependency_lock: list[dict]
    validation_suite_ref: str
    runtime_limits: Limits
    data_schema_version: int = Field(ge=1)


class GoalSpec(Strict):
    goal_id: str = Field(pattern=ID)
    project_id: str = Field(pattern=ID)
    owner_id: str = Field(pattern=ID)
    goal: str = Field(min_length=1, max_length=4000)
    constraints: list[str]
    acceptance_version: str
    resource_refs: list[str]
    unresolved: list[str]


class Run(Strict):
    run_id: str = Field(pattern=ID)
    project_id: str = Field(pattern=ID)
    principal_id: str = Field(pattern=ID)
    runtime_id: str = Field(pattern=ID)
    status: RunState
    input_snapshot: dict
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


def schema_check(schema: dict):
    allowed = {
        "type",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "enum",
        "maxLength",
        "minimum",
        "maximum",
    }
    if set(schema) - allowed or schema.get("type") not in {
        "object",
        "array",
        "string",
        "integer",
        "number",
        "boolean",
        "null",
    }:
        raise DomainError("INVALID_MANIFEST", "Unsupported schema keyword or type")
    if schema["type"] == "object":
        if schema.get("additionalProperties") is not False:
            raise DomainError("INVALID_MANIFEST", "Closed object schema required")
        for child in schema.get("properties", {}).values():
            schema_check(child)
    if schema["type"] == "array":
        schema_check(schema["items"])


def validate_action(raw: str):
    try:
        action = ActionSpec.model_validate(strict_json(raw))
        if action.effect == "external_write":
            raise ValueError("R0 external writes disabled")
        tools = {"resource.read", "data.aggregate_csv", "artifact.save_text"}
        executors = tools if action.executor.kind == "registered_tool" else {"intern.agent"}
        if action.executor.ref not in executors or set(action.allowed_tool_refs) - tools:
            raise ValueError("Unknown registered reference")
        if action.postcheck_refs != ["receipt.readback.v1"]:
            raise ValueError("Independent receipt check required")
        schema_check(action.input_schema)
        schema_check(action.output_schema)
        return action
    except (ValueError, KeyError, TypeError) as e:
        raise DomainError("INVALID_MANIFEST", "Manifest failed strict F1 validation") from e
