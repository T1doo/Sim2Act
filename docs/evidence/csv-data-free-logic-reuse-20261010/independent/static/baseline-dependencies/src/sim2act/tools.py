import csv
import hashlib
import io
import json
from decimal import Decimal, DecimalException
from typing import Any

from sqlalchemy import insert, select, update

from .contracts import resource_id
from .db import (
    fingerprint,
    local_effects,
    new_id,
    operation_intents,
    operations,
    resource_retirements,
    resources,
    run_contracts,
    runs,
)
from .errors import DomainError

TOOLS: dict[str, dict[str, Any]] = {
    "resource.read": {
        "type": "object",
        "properties": {"resource_id": {"type": "string"}},
        "required": ["resource_id"],
        "additionalProperties": False,
    },
    "data.aggregate_csv": {
        "type": "object",
        "properties": {"resource_id": {"type": "string"}, "column": {"type": "string"}},
        "required": ["resource_id", "column"],
        "additionalProperties": False,
    },
    "artifact.save_text": {
        "type": "object",
        "properties": {"text": {"type": "string", "maxLength": 8000}},
        "required": ["text"],
        "additionalProperties": False,
    },
}


def validate_call(name, args):
    if name not in TOOLS:
        raise DomainError("UNSUPPORTED_CAPABILITY", "Unregistered tool")
    schema = TOOLS[name]
    if (
        not isinstance(args, dict)
        or set(args) != set(schema["required"])
        or any(not isinstance(v, str) for v in args.values())
    ):
        raise DomainError("MODEL_OUTPUT_INVALID", "Incomplete or unknown tool parameters")
    if "resource_id" in args:
        resource_id(args["resource_id"])
    if len(json.dumps(args).encode()) > 32768 or len(args.get("text", "")) > 8000:
        raise DomainError("INVALID_INPUT")


def definitions():
    return [
        {"type": "function", "function": {"name": name, "description": name, "parameters": schema}}
        for name, schema in TOOLS.items()
    ]


def dispatch(store, run_id, fence, call, *, crash_before_commit=False,
             natural_activation_settings=None):
    """Authorization, local effect and receipt are one transaction, fenced by the Run row."""
    name, args = call["function"]["name"], call["args"]
    validate_call(name, args)
    fp = fingerprint({"tool": name, "args": args})
    with store.tx() as c:
        source = c.execute(select(runs.c.principal_id, runs.c.project_id, run_contracts.c.snapshot)
                           .join(run_contracts, run_contracts.c.run_id == runs.c.id)
                           .where(runs.c.id == run_id)).mappings().first()
        selected = source["snapshot"].get("natural_planning") if source else None
        activated = isinstance(selected, dict) and selected.get("activation") is not None
        if activated:
            store.lock_project(c, source["principal_id"], source["project_id"])
        run = store.guard(c, run_id, fence)
        if activated:
            from .goal_planner import verified_plan, verify_confirmation
            from .natural_activations import validate_run

            validate_run(store, c, run, natural_activation_settings, active=True)
            binding = verified_plan(store, c, run)
            verify_confirmation(store, c, run, binding)
            expected = []
            for step in binding["plan"]["steps"]:
                step_args = {"resource_id": step["resource_id"]}
                if step["tool_ref"] == "data.aggregate_csv":
                    step_args["column"] = step["column"]
                expected.append({"id": "nl_" + binding["fingerprint"] + "_" + step["id"],
                                 "name": step["tool_ref"], "args": step_args})
            if {"id": call["id"], "name": name, "args": args} not in expected:
                raise DomainError("PERMISSION_DENIED", "Operation is outside confirmed activation")
        if run["status"] != "RUNNING":
            raise DomainError("VERSION_CONFLICT", "Pause/cancel stops new dispatch")
        rid = args.get("resource_id", run["project_id"])
        if rid != run["project_id"] and rid not in run["resource_refs"]:
            raise DomainError("PERMISSION_DENIED")
        store.authorize(c, run["principal_id"], run["runtime_id"], run["project_id"], rid, name)
        old = (
            c.execute(
                select(operations).where(
                    operations.c.run_id == run_id, operations.c.call_id == call["id"]
                )
            )
            .mappings()
            .first()
        )
        if old:
            if old["fingerprint"] != fp:
                raise DomainError("VERSION_CONFLICT")
            if old["status"] == "VERIFIED":
                return old["receipt"]
            raise DomainError("OUTCOME_UNKNOWN")
        ctx = dict(run["context"])
        if ctx["tools"] >= store.frozen_contract(c, run).limits.max_tools:
            raise DomainError("BUDGET_EXHAUSTED")
        oid = new_id("op")
        c.execute(
            insert(operations).values(
                id=oid,
                run_id=run_id,
                call_id=call["id"],
                fingerprint=fp,
                tool_ref=name,
                status="PREPARED",
            )
        )
        c.execute(
            insert(operation_intents).values(operation_id=oid, request={"tool": name, "args": args})
        )
        artifact_refs = []
        if name == "artifact.save_text":
            data = write_text_artifact(
                store, c, run["principal_id"], run["runtime_id"], run["project_id"], args["text"]
            )
            output_id = data["resource_id"]
            c.execute(insert(local_effects).values(
                operation_id=oid, resource_id=output_id, content_hash=data["hash"]
            ))
            artifact_refs = [output_id]
        else:
            data = authorized_read(
                store, c, run["principal_id"], run["runtime_id"], run["project_id"], name, args
            )
        receipt = {
            "operation_id": oid,
            "status": "VERIFIED",
            "data": data,
            "artifact_refs": artifact_refs,
            "receipt_ref": oid,
            "check_results": [{"check": "receipt.readback.v1", "status": "PASS"}],
            "usage_ref": None,
            "error": None,
        }
        c.execute(
            update(operations)
            .where(operations.c.id == oid)
            .values(status="VERIFIED", receipt=receipt)
        )
        ctx["tools"] += 1
        c.execute(update(runs).where(runs.c.id == run_id).values(context=ctx))
        store.event(
            c, run_id, "TOOL_VERIFIED", {"operation_id": oid, "tool_ref": name, "source_ref": rid}
        )
        if crash_before_commit:
            raise RuntimeError("FAULT_INJECTION before local commit")
        return receipt


def authorized_read(store, c, principal, runtime, project_id, name, args):
    """Shared trusted read gateway for task tools and declarative preview inputs."""
    if name not in {"resource.read", "data.aggregate_csv"}:
        raise DomainError("UNSUPPORTED_CAPABILITY")
    validate_call(name, args)
    rid = args["resource_id"]
    store.authorize(c, principal, runtime, project_id, rid, name)
    return read_data(c, rid, name, args)


def csv_column_options(content):
    """Bounded input guidance only; no cells, execution results or permissions returned."""
    try:
        reader = csv.DictReader(io.StringIO(content))
        names = reader.fieldnames
        if not names or any(not n for n in names) or len(names) != len(set(names)):
            raise ValueError("CSV 表头为空或重复，请保存修正后的材料并重建草案。")
        valid = dict.fromkeys(names, True)
        totals = dict.fromkeys(names, Decimal(0))
        count = 0
        for row in reader:
            count += 1
            if count > 1000:
                raise ValueError("CSV 超过 1000 条记录，请缩小材料范围。")
            if None in row:
                raise ValueError("CSV 行包含多余字段，请修正材料。")
            for name in names:
                try:
                    if valid[name]:
                        number = Decimal(row[name])
                        valid[name] = number.is_finite()
                        if valid[name]:
                            totals[name] += number
                except (DecimalException, TypeError, ValueError):
                    valid[name] = False
        return {
            "row_count": count,
            "columns": [
                {"name": n, "numeric": valid[n], "reason": None if valid[n] else "存在缺值、文本、非有限数或合计超出十进制范围"}
                for n in names
            ],
            "error": None,
        }
    except (ValueError, csv.Error) as exc:
        message = str(exc) if isinstance(exc, ValueError) else "CSV 格式无效，请修正材料。"
        return {"row_count": None, "columns": [], "error": message}


def read_data(c, rid, name, args):
    if c.execute(select(resource_retirements.c.resource_id).where(resource_retirements.c.resource_id == rid)).first():
        raise DomainError("RESOURCE_UNAVAILABLE", "来源已显式退休，旧内容不可读取")
    res = c.execute(select(resources).where(resources.c.id == rid)).mappings().one()
    if hashlib.sha256(res["content"].encode()).hexdigest() != res["hash"]:
        raise DomainError("VERIFICATION_FAILED")
    if name == "resource.read":
        data = {
            "resource_id": rid,
            "content": res["content"],
            "hash": res["hash"],
            "format": res["format"],
        }
    else:
        if res["format"] != "csv":
            raise DomainError("INVALID_INPUT", "CSV resource required")
        data = aggregate_csv_content(res["content"], rid, args["column"])
    return data


def aggregate_csv_content(content, rid, column):
    """Registered CSV computation over an already authorized immutable read snapshot."""
    try:
        reader = csv.DictReader(io.StringIO(content))
        if (
            not reader.fieldnames
            or len(reader.fieldnames) != len(set(reader.fieldnames))
            or column not in reader.fieldnames
        ):
            raise ValueError("column")
        vals = []
        for row in reader:
            if None in row or row[column] is None:
                raise ValueError("row")
            num = Decimal(row[column])
            if not num.is_finite():
                raise ValueError("nonfinite")
            vals.append(num)
            if len(vals) > 1000:
                raise ValueError("row limit")
        data = {
            "resource_id": rid,
            "column": column,
            "count": len(vals),
            "sum": str(sum(vals, Decimal(0))),
            "source_hash": hashlib.sha256(content.encode()).hexdigest(),
        }
    except (DecimalException, ValueError, TypeError, csv.Error) as e:
        raise DomainError(
            "INVALID_INPUT", "CSV column must contain finite decimal values"
        ) from e
    return data


def reconcile_readback(store, c, run, operation):
    """Trusted local evidence only; unknown adapters never claim absence or dispatch again."""
    intent = c.execute(
        select(operation_intents.c.request).where(
            operation_intents.c.operation_id == operation["id"]
        )
    ).scalar()
    if (
        not intent
        or fingerprint(intent) != operation["fingerprint"]
        or intent.get("tool") != operation["tool_ref"]
    ):
        return "OUTCOME_UNKNOWN", None
    name, args = intent["tool"], intent["args"]
    validate_call(name, args)
    store.frozen_contract(c, run)
    rid = args.get("resource_id", run["project_id"])
    if rid != run["project_id"] and rid not in run["resource_refs"]:
        raise DomainError("PERMISSION_DENIED")
    store.authorize(c, run["principal_id"], run["runtime_id"], run["project_id"], rid, name)
    artifacts = []
    if name == "artifact.save_text":
        effect = (
            c.execute(select(local_effects).where(local_effects.c.operation_id == operation["id"]))
            .mappings()
            .first()
        )
        if not effect:
            return "OUTCOME_UNKNOWN", None  # No pointer cannot prove absence of an effect.
        resource = (
            c.execute(
                select(resources).where(
                    resources.c.id == effect["resource_id"],
                    resources.c.project_id == run["project_id"],
                )
            )
            .mappings()
            .first()
        )
        if not resource:
            return "EFFECT_KNOWN_INVALID", None
        store.authorize(
            c,
            run["principal_id"],
            run["runtime_id"],
            run["project_id"],
            resource["id"],
            "resource.read",
        )
        expected = hashlib.sha256(args["text"].encode()).hexdigest()
        if (
            effect["content_hash"] != expected
            or resource["hash"] != expected
            or hashlib.sha256(resource["content"].encode()).hexdigest() != expected
        ):
            return "EFFECT_KNOWN_INVALID", None
        data = {"resource_id": resource["id"], "hash": expected}
        artifacts = [resource["id"]]
    else:
        store.authorize(
            c, run["principal_id"], run["runtime_id"], run["project_id"], rid, "resource.read"
        )
        data = read_data(c, rid, name, args)
    receipt = {
        "operation_id": operation["id"],
        "status": "VERIFIED",
        "data": data,
        "artifact_refs": artifacts,
        "receipt_ref": operation["id"],
        "check_results": [{"check": "receipt.readback.v1", "status": "PASS"}],
        "usage_ref": None,
        "error": None,
    }
    return "VERIFIED", receipt


def write_text_artifact(store, c, principal, runtime, project_id, content):
    """Existing registered project artifact effect; caller owns transaction/idempotency.

    No new tool or write grant. Derived artifact read grants match normal dispatch.
    """
    validate_call("artifact.save_text", {"text": content})
    store.authorize(c, principal, runtime, project_id, project_id, "artifact.save_text")
    output_id = new_id("res")
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    c.execute(insert(resources).values(
        id=output_id, project_id=project_id, name="Run artifact", format="md",
        content=content, hash=content_hash,
    ))
    store.add_grants(c, principal, runtime, project_id, output_id, ["resource.read"])
    back = c.execute(select(resources.c.content).where(resources.c.id == output_id)).scalar_one()
    if back != content:
        raise DomainError("VERIFICATION_FAILED")
    return {"resource_id": output_id, "hash": content_hash}
