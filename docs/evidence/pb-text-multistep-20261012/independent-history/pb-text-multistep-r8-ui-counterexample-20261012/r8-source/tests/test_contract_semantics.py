import copy
import json

import pytest

from sim2act.contracts import (
    schema_check,
    validate_action,
    validate_action_input,
    validate_manifest,
)
from sim2act.db import new_id
from sim2act.errors import DomainError


def action_fixture(resource):
    return {
        "schema_version": "1.0-draft",
        "action_id": new_id("action"),
        "revision": 1,
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "minimum": 0},
                "kind": {"type": "string", "enum": ["csv", "txt"]},
            },
            "required": ["amount", "kind"],
            "additionalProperties": False,
        },
        "output_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
            "additionalProperties": False,
        },
        "executor": {"kind": "bounded_agent", "ref": "intern.agent", "version": "1"},
        "allowed_tool_refs": ["resource.read"],
        "dependencies": [{"kind": "tool", "ref": "resource.read", "version": "1"}],
        "permission_requirements": [{"tool_ref": "resource.read", "resource_ref": resource}],
        "effect": "read",
        "preconditions": [{"op": "in", "field": "kind", "value": ["csv"]}],
        "postcheck_refs": ["receipt.readback.v1"],
        "limits": {
            "max_requests": 4,
            "max_tools": 4,
            "max_repairs": 1,
            "max_total_tokens": 64000,
            "max_output_tokens": 1024,
            "run_seconds": 300,
        },
        "idempotency": "read_only",
        "reconcile_ref": "operation.lookup.v1",
        "error_contract": ["INVALID_INPUT"],
    }


@pytest.mark.parametrize(
    "schema",
    [
        {
            "type": "object",
            "properties": {},
            "required": ["missing"],
            "additionalProperties": False,
        },
        {"type": "object", "properties": {}, "required": ["x", "x"], "additionalProperties": False},
        {"type": "array", "items": {"type": "string"}, "maxItems": 1001},
        {"type": "string", "maxLength": True},
        {"type": "integer", "minimum": 2, "maximum": 1},
        {"type": "boolean", "enum": [1]},
        {"type": "object", "properties": [], "additionalProperties": False},
        {"type": "string", "$ref": "file:///private"},
    ],
)
def test_AT03_schema_semantics_fail_closed(schema):
    with pytest.raises(DomainError):
        schema_check(schema)


@pytest.mark.parametrize(
    "value",
    [
        {"amount": True, "kind": "csv"},
        {"amount": -1, "kind": "csv"},
        {"amount": 1, "kind": "txt"},
        {"amount": 1, "kind": "csv", "script": "bad"},
    ],
)
def test_AT03_strict_input_and_conditions(value):
    action = validate_action(json.dumps(action_fixture(new_id("res"))))
    with pytest.raises(DomainError):
        validate_action_input(action, value)


def test_AT03_nested_refs_effects_and_no_side_effect_validation(env):
    store, s, client, a, b, pid, res = env
    base = action_fixture(res)
    action = validate_action(json.dumps(base))
    validate_action_input(action, {"amount": 1.25, "kind": "csv"})
    for mutation in [
        {"dependencies": [{"kind": "prompt", "ref": "https://remote/code", "version": "1"}]},
        {"dependencies": [{"kind": "tool", "ref": "resource.read", "version": "1", "script": "x"}]},
        {"permission_requirements": [{"tool_ref": "resource.read", "resource_ref": "C:\\secret"}]},
        {"permission_requirements": [{"tool_ref": "artifact.save_text", "resource_ref": pid}]},
        {"preconditions": [{"op": "eval", "field": "kind", "value": "x"}]},
        {"allowed_tool_refs": ["resource.read", "artifact.save_text"]},
        {"idempotency": "transactional"},
    ]:
        with pytest.raises(DomainError):
            validate_action(json.dumps(base | mutation))
    response = client.post(
        f"/api/projects/{pid}/contracts/validate",
        json={"action": base, "input": {"amount": 1.25, "kind": "csv"}},
    )
    assert response.status_code == 200 and response.json()["execution_performed"] is False
    assert client.get(f"/api/projects/{pid}/runs").json() == []
    invalid = copy.deepcopy(base)
    invalid["permission_requirements"][0]["resource_ref"] = new_id("res")
    assert (
        client.post(f"/api/projects/{pid}/contracts/validate", json={"action": invalid}).status_code
        == 403
    )


def manifest_fixture():
    closed = {"type": "object", "properties": {}, "additionalProperties": False}
    return {
        "schema_version": "1.0-draft",
        "app_id": new_id("app"),
        "revision": 1,
        "origin": "goal",
        "goal_ref": new_id("goal"),
        "input_schema": closed,
        "output_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "additionalProperties": False,
        },
        "views": [{"component_ref": "text", "output_field": "text"}],
        "workflow": [{"step_id": "read", "binding_id": "read", "depends_on": []}],
        "action_bindings": [{"binding_id": "read", "action_id": new_id("action"), "revision": 1}],
        "data_bindings": [],
        "runtime_identity_requirements": {"mode": "user_and_app_intersection"},
        "permission_requirements": [],
        "dependency_lock": [],
        "validation_suite_ref": "receipt.readback.v1",
        "runtime_limits": action_fixture(new_id("res"))["limits"],
        "data_schema_version": 1,
    }


def test_manifest_draft_only_validates_dag_origin_and_trusted_views():
    base = manifest_fixture()
    assert validate_manifest(json.dumps(base)).origin == "goal"
    for mutation in [
        {"origin": "task_run"},
        {
            "views": [
                {"component_ref": "text", "output_field": "text", "html": "<script>bad</script>"}
            ]
        },
        {"views": [{"component_ref": "iframe", "output_field": "text"}]},
        {"workflow": [{"step_id": "read", "binding_id": "read", "depends_on": ["read"]}]},
        {"workflow": [{"step_id": "read", "binding_id": "missing", "depends_on": []}]},
        {"runtime_identity_requirements": {"mode": "admin"}},
    ]:
        with pytest.raises(DomainError):
            validate_manifest(json.dumps(base | mutation))
