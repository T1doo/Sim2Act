"""Closed compiler input for the existing offline CSV DAG, never a Manifest API."""

import copy
from typing import Literal

from pydantic import Field

from . import csv_reports as report
from .contracts import BranchExpression, FieldSource, Strict
from .db import fingerprint
from .errors import DomainError

VERSION = "csv.composition.v1"
REFS = ("resource.read", "data.aggregate_csv", report.REF)
IDENT = r"^[a-z][a-z0-9_]{0,39}$"


class Node(Strict):
    step_id: str = Field(pattern=IDENT)
    action: Literal["resource.read", "data.aggregate_csv", "intern.csv_report.v1"]
    column: str | None = Field(default=None, min_length=1, max_length=200,
                               exclude_if=lambda value: value is None)
    inputs: dict[str, FieldSource] = Field(min_length=1, max_length=5)
    depends_on: list[str] = Field(max_length=3)
    when: BranchExpression | None = Field(default=None, exclude_if=lambda value: value is None)


class Composition(Strict):
    version: Literal["csv.composition.v1"]
    nodes: list[Node] = Field(min_length=1, max_length=4)


def compile_closed(candidate, composition, limits, read_schema):
    nodes = {node.step_id: node for node in composition.nodes}
    if len(nodes) != len(composition.nodes):
        raise DomainError("INVALID_INPUT", "Duplicate composition node")
    count = len(nodes)
    node_limits = limits.model_dump()
    for key in ("max_requests", "max_tools", "max_total_tokens", "run_seconds"):
        node_limits[key] //= count
        if node_limits[key] < 1:
            raise DomainError("BUDGET_EXHAUSTED", "Conservative composition envelope exhausted")
    node_limits["max_repairs"] = 0
    original = candidate["manifest"]
    manifest = copy.deepcopy(original)
    manifest["revision"] += 1
    manifest["runtime_limits"] = limits.model_dump()
    rid = original["data_bindings"][0]["resource_ref"]
    props, inputs, actions, workflow, bindings = {}, {}, [], [], []
    for node in composition.nodes:
        args = {key: source.model_dump(exclude_none=True) for key, source in node.inputs.items()}
        parents = node.depends_on
        if (len(set(parents)) != len(parents) or node.step_id in parents or set(parents) - set(nodes)):
            raise DomainError("INVALID_INPUT", "Invalid declared composition predecessors")
        required = ({"resource_id", "column"} if node.action == "data.aggregate_csv" else
                    set(report.FIELDS) if node.action == report.REF else {"resource_id"})
        if set(args) != required:
            raise DomainError("INVALID_INPUT", "Exact semantic ports required")
        if node.action == "data.aggregate_csv":
            if node.column is None:
                raise DomainError("INVALID_INPUT", "Aggregate column must be pinned")
            field = node.step_id + "_column"
            props[field] = {"type": "string", "enum": [node.column]}
            inputs[field] = node.column
            if args["column"] != dict(source="input", field=field):
                raise DomainError("INVALID_INPUT", "Column requires this node's pinned input")
            input_schema = report.obj({"resource_id": {"type": "string"}, "column": props[field]})
            output_schema = report.INPUT
        else:
            if node.column is not None:
                raise DomainError("INVALID_INPUT", "Only aggregate nodes have a column")
            input_schema = report.INPUT if node.action == report.REF else report.obj({"resource_id": {"type": "string"}})
            output_schema = report.OUTPUT if node.action == report.REF else read_schema
        if node.action == report.REF:
            # Keep a coherent aggregate tuple: no mixing one sum with another count/column.
            source = args["sum"]
            ref = source.get("ref")
            if (source.get("source") != "step" or ref not in nodes
                    or nodes[ref].action != "data.aggregate_csv"
                    or any(args[k] != dict(source="step", ref=ref, field=k) for k in report.FIELDS)):
                raise DomainError("INVALID_INPUT", "Report ports require one aggregate predecessor")
        else:
            source = args["resource_id"]
            ref = source.get("ref")
            if source != dict(source="data", ref="source", field="resource_id") and not (
                    source.get("source") == "step" and source.get("field") == "resource_id"
                    and ref in nodes and nodes[ref].action in REFS[:2]):
                raise DomainError("INVALID_INPUT", "Resource port requires the existing source lineage")
        action = copy.deepcopy(candidate["actions"][0])
        action.update(action_id="action_" + fingerprint([VERSION, original["app_id"], node.step_id])[:32],
                      revision=manifest["revision"], executor=dict(kind="registered_tool", ref=node.action, version="1"),
                      input_schema=copy.deepcopy(input_schema), output_schema=copy.deepcopy(output_schema),
                      limits=copy.deepcopy(node_limits))
        action["permission_requirements"] = ([] if node.action == report.REF else
            [p for p in action["permission_requirements"] if node.action == "data.aggregate_csv" or p["tool_ref"] == "resource.read"])
        action["dependencies"] = [] if node.action == report.REF else [dict(kind="resource", ref=rid, version="1")]
        actions.append(action)
        bindings.append(dict(binding_id=node.step_id, action_id=action["action_id"], revision=action["revision"]))
        step = dict(step_id=node.step_id, binding_id=node.step_id, depends_on=parents[:], inputs=args)
        if node.when is not None:
            step["when"] = node.when.model_dump(exclude_none=True)
        workflow.append(step)
    manifest["input_schema"] = report.obj(props)
    # Same optional typed run input as the existing controlled branches.
    if any(node.when is not None for node in composition.nodes):
        manifest["input_schema"]["properties"]["include_report"] = {"type": "boolean"}
    manifest["workflow"], manifest["action_bindings"] = workflow, bindings
    referenced = {p for node in composition.nodes for p in node.depends_on}
    sinks = [node.step_id for node in composition.nodes if node.step_id not in referenced]
    outputs, output_props = {}, {}
    for sid in sinks:
        schema = actions[list(nodes).index(sid)]["output_schema"]
        for field, value in schema["properties"].items():
            key = sid + "_" + field
            outputs[key] = dict(source="step", ref=sid, field=field)
            output_props[key] = copy.deepcopy(value)
    manifest["outputs"], manifest["output_schema"] = outputs, report.obj(output_props)
    manifest["views"] = [dict(component_ref="text", output_field=next(iter(outputs)))] if outputs else []
    manifest["dependency_lock"] = [dict(kind="resource", ref=rid, version="1"),
        *[dict(kind="tool", ref=ref, version="1") for ref in REFS if any(n.action == ref for n in composition.nodes)],
        dict(kind="check", ref="receipt.readback.v1", version="1")]
    return dict(manifest=manifest, actions=actions), inputs, sinks
