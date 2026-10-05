import csv
import hashlib
import io
import json
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import insert, select, update

from .contracts import resource_id
from .db import fingerprint, local_effects, new_id, operation_intents, operations, resources
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


def dispatch(store, run_id, fence, call, *, crash_before_commit=False):
    """Authorization, local effect and receipt are one transaction, fenced by the Run row."""
    name, args = call["function"]["name"], call["args"]
    validate_call(name, args)
    fp = fingerprint({"tool": name, "args": args})
    with store.tx() as c:
        run = store.guard(c, run_id, fence)
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
            output_id = new_id("res")
            content = args["text"]
            c.execute(
                insert(resources).values(
                    id=output_id,
                    project_id=run["project_id"],
                    name="Run artifact",
                    format="md",
                    content=content,
                    hash=hashlib.sha256(content.encode()).hexdigest(),
                )
            )
            c.execute(
                insert(local_effects).values(
                    operation_id=oid,
                    resource_id=output_id,
                    content_hash=hashlib.sha256(content.encode()).hexdigest(),
                )
            )
            store.add_grants(
                c,
                run["principal_id"],
                run["runtime_id"],
                run["project_id"],
                output_id,
                ["resource.read"],
            )
            data = {"resource_id": output_id, "hash": hashlib.sha256(content.encode()).hexdigest()}
            artifact_refs = [output_id]
            # Independent readback of written content before marking verified.
            back = c.execute(
                select(resources.c.content).where(resources.c.id == output_id)
            ).scalar_one()
            if back != content:
                raise DomainError("VERIFICATION_FAILED")
        else:
            data = read_data(c, rid, name, args)
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
        from .db import runs

        c.execute(update(runs).where(runs.c.id == run_id).values(context=ctx))
        store.event(
            c, run_id, "TOOL_VERIFIED", {"operation_id": oid, "tool_ref": name, "source_ref": rid}
        )
        if crash_before_commit:
            raise RuntimeError("FAULT_INJECTION before local commit")
        return receipt


def read_data(c, rid, name, args):
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
        try:
            reader = csv.DictReader(io.StringIO(res["content"]))
            if (
                not reader.fieldnames
                or len(reader.fieldnames) != len(set(reader.fieldnames))
                or args["column"] not in reader.fieldnames
            ):
                raise ValueError("column")
            vals = []
            for row in reader:
                if None in row or row[args["column"]] is None:
                    raise ValueError("row")
                num = Decimal(row[args["column"]])
                if not num.is_finite():
                    raise ValueError("nonfinite")
                vals.append(num)
                if len(vals) > 1000:
                    raise ValueError("row limit")
            data = {
                "resource_id": rid,
                "column": args["column"],
                "count": len(vals),
                "sum": str(sum(vals, Decimal(0))),
                "source_hash": res["hash"],
            }
        except (InvalidOperation, ValueError, TypeError, csv.Error) as e:
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
