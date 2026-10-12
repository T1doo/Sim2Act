"""R0 bounded-agent protocol on the existing AppManifest/AppRun path.

Only explicitly offline Replay is executable here. Literal evidence is verifiable;
semantic inference and autonomous model generation remain UNKNOWN/NOT_RUN.
"""

import copy
import json
import time

from sqlalchemy import insert, select

from .contracts import strict_json, validate_value
from .db import (
    app_drafts,
    fingerprint,
    internal_run_bindings,
    operation_intents,
    operations,
    principals,
    runs,
    task_extractions,
)
from .errors import DomainError
from .model import SYSTEM_PROMPT, parse_response
from .tools import authorized_read, definitions

CHECK = "source.literal_evidence.v1"
GOAL = "literal_evidence_only"
PROVENANCE = "agent_source.v1"


class ReplayModel:
    """Finite in-memory wire responses, never a network/provider adapter or runtime gold."""

    def __init__(self, responses):
        self.responses = copy.deepcopy(responses)
        self.requests = []

    def request(self, messages, tools):
        self.requests.append(copy.deepcopy({"messages": messages, "tools": tools}))
        if not self.responses:
            raise DomainError("BUDGET_EXHAUSTED", "Offline Replay exhausted; no fallback")
        return self.responses.pop(0)


def offline_replay_model(responses):
    """Bound explicit HTTP/persisted offline data; never generate an answer or adapter."""
    if (
        type(responses) is not list
        or len(responses) != 2
        or any(
            type(r) is not dict
            or set(r) - {"choices", "model", "id", "object", "created", "usage"}
            or type(r.get("choices")) is not list
            or len(r["choices"]) != 1
            or type(r["choices"][0]) is not dict
            for r in responses
        )
    ):
        raise DomainError("INVALID_INPUT", "Exactly two offline wire responses required")
    try:
        size = len(json.dumps(responses, ensure_ascii=False, allow_nan=False).encode("utf-8"))
    except (TypeError, ValueError, RecursionError):
        raise DomainError("INVALID_INPUT", "Invalid offline response JSON") from None
    if size > 32000:
        raise DomainError("BUDGET_EXHAUSTED", "Offline responses exceed 32000 UTF-8 bytes")
    return ReplayModel(responses)


def is_agent(candidate):
    return any(
        a.get("executor", {}).get("kind") == "bounded_agent"
        for a in candidate.get("actions", [])
        if isinstance(a, dict)
    )


def schemas():
    from .apps import object_schema

    text = {"type": "string"}
    quote = object_schema(
        {
            "start_line": {"type": "integer", "minimum": 1},
            "end_line": {"type": "integer", "minimum": 1},
            "quote": {"type": "string", "maxLength": 4096},
        }
    )
    return (
        object_schema({"resource_id": text, "term": {"type": "string", "maxLength": 80}}),
        object_schema(
            {
                "resource_id": text,
                "revision": {"type": "integer", "enum": [1]},
                "source_hash": text,
                "term": {"type": "string", "maxLength": 80},
                "citations": {"type": "array", "items": quote, "maxItems": 16},
                "semantic_status": {"type": "string", "enum": ["UNKNOWN"]},
            }
        ),
    )


def compile_agent(candidate, manifest, actions, report):
    input_schema, output_schema = schemas()
    if len(actions) != 1 or len(manifest.workflow) != 1 or len(manifest.data_bindings) != 1:
        raise DomainError("UNSUPPORTED_CAPABILITY", "Single R0 agent node only")
    action, step = actions[0], manifest.workflow[0]
    if step.when is not None:
        raise DomainError("UNSUPPORTED_CAPABILITY", "Agent preview does not execute workflow conditions")
    rid = manifest.data_bindings[0].resource_ref
    expected_inputs = {
        "resource_id": {
            "source": "data",
            "ref": manifest.data_bindings[0].binding_id,
            "field": "resource_id",
        },
        "term": {"source": "input", "field": "term"},
    }
    actual_inputs = {k: v.model_dump(exclude_none=True) for k, v in step.inputs.items()}
    expected_outputs = {
        k: {"source": "step", "ref": step.step_id, "field": k} for k in output_schema["properties"]
    }
    actual_outputs = {k: v.model_dump(exclude_none=True) for k, v in manifest.outputs.items()}
    permissions = [{"tool_ref": "resource.read", "resource_ref": rid}]
    if (
        set(candidate)
        - {"manifest", "actions", "source_hash", "source_revision", "goal", "agent_provenance"}
        or candidate.get("goal") != GOAL
        or type(candidate.get("source_revision")) is not int
        or candidate["source_revision"] != 1
        or action.executor.kind != "bounded_agent"
        or action.executor.ref != "intern.agent"
        or action.allowed_tool_refs != ["resource.read"]
        or action.postcheck_refs != [CHECK]
        or manifest.validation_suite_ref != CHECK
        or action.input_schema != input_schema
        or action.output_schema != output_schema
        or manifest.input_schema
        != {
            "type": "object",
            "properties": {"term": input_schema["properties"]["term"]},
            "required": ["term"],
            "additionalProperties": False,
        }
        or manifest.output_schema != output_schema
        or actual_inputs != expected_inputs
        or actual_outputs != expected_outputs
        or [p.model_dump() for p in action.permission_requirements] != permissions
        or [p.model_dump() for p in manifest.permission_requirements] != permissions
        or action.preconditions
        or action.limits.max_requests != 2
        or action.limits.max_tools != 1
        or action.limits.max_repairs != 0
        or action.limits != manifest.runtime_limits
    ):
        raise DomainError("UNSUPPORTED_CAPABILITY", "Only explicit literal evidence R0 contract")
    if (
        not isinstance(candidate.get("source_hash"), str)
        or len(candidate["source_hash"]) != 64
        or any(ch not in "0123456789abcdef" for ch in candidate["source_hash"])
    ):
        raise DomainError("INVALID_MANIFEST")
    report = {
        **report,
        "not_an_executable_plan": False,
        "execution_mode": "OFFLINE_REPLAY_ONLY",
        "semantic_status": "UNKNOWN",
    }
    return manifest, action, report


def existing_runtime(store, c, user, pid, runtime):
    project = store.own_project(c, user, pid)
    # Reuse means the same existing authorization domain, not a new isolated identity.
    if (
        not isinstance(runtime, str)
        or not runtime.startswith("appruntime_")
        or runtime == project["runtime_id"]
        or not c.execute(select(principals.c.id).where(principals.c.id == runtime)).first()
        or not c.execute(
            select(app_drafts.c.id).where(
                app_drafts.c.project_id == pid, app_drafts.c.runtime_id == runtime
            )
        ).first()
    ):
        raise DomainError("PERMISSION_DENIED", "Existing same-project app identity required")


def persist_agent_candidate(store, user, pid, runtime, candidate, name, limits):

    with store.tx() as c:
        store.lock_project(c, user, pid)
        return persist(c, store, user, pid, runtime, candidate, name, limits)


def persist(c, store, user, pid, runtime, candidate, name, limits):
    from .apps import compile_preview

    if not isinstance(name, str) or not 1 <= len(name) <= 200:
        raise DomainError("INVALID_INPUT")
    manifest, _, _ = compile_preview(candidate, limits)
    if not is_agent(candidate) or manifest.origin != "goal" or "agent_provenance" in candidate:
        raise DomainError("INVALID_MANIFEST", "Task origin requires verified extraction service")
    existing_runtime(store, c, user, pid, runtime)
    rid = manifest.data_bindings[0].resource_ref
    source = authorized_read(store, c, user, runtime, pid, "resource.read", {"resource_id": rid})
    if source["format"] not in {"md", "txt"} or source["hash"] != candidate["source_hash"]:
        raise DomainError("VERSION_CONFLICT")
    aid = manifest.app_id
    c.execute(
        insert(app_drafts).values(
            id=aid,
            project_id=pid,
            runtime_id=runtime,
            name=name,
            candidate=copy.deepcopy(candidate),
            fingerprint=fingerprint(candidate),
            created_at=time.time(),
        )
    )
    return {
        "id": aid,
        "state": "OFFLINE_REPLAY_ONLY",
        "publishable": False,
        "authorization_domain": runtime,
        "model_requests": 0,
    }


def check_evidence(source, args, output):
    """Only literal retrieval correctness; no rule/obligation semantic judgement."""
    _, output_schema = schemas()
    validate_value(output_schema, output, "agent_output")
    term = args["term"]
    if not term or term != term.strip() or len(source["content"].encode()) > 4096:
        raise DomainError("INVALID_INPUT", "Bounded nonempty literal term/source required")
    lines = source["content"].splitlines()
    if len(lines) > 64:
        raise DomainError("INVALID_INPUT")
    matches = [
        {"start_line": n, "end_line": n, "quote": line}
        for n, line in enumerate(lines, 1)
        if term in line
    ]
    if len(matches) > 16:
        raise DomainError("BUDGET_EXHAUSTED")
    expected = {
        "resource_id": source["resource_id"],
        "revision": 1,
        "source_hash": source["hash"],
        "term": term,
        "citations": matches,
        "semantic_status": "UNKNOWN",
    }
    if fingerprint(output) != fingerprint(expected):
        raise DomainError("VERIFICATION_FAILED", "Literal evidence or exact source span mismatch")
    return {
        "check": CHECK,
        "version": "1",
        "status": "PASS",
        "goal": GOAL,
        "semantic_status": "UNKNOWN",
        "source_revision": 1,
        "source_hash": source["hash"],
        "output_fingerprint": fingerprint(output),
    }


def execute_protocol(plan, model, read):
    if type(model) is not ReplayModel:
        raise DomainError("UNSUPPORTED_CAPABILITY", "Offline Replay only; no provider fallback")
    from .contracts import validate_action

    action = validate_action(json.dumps(plan["action"]))
    limits = action.limits
    args = plan["args"]
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "goal": GOAL,
                    "instructions": "Read the bound source; return the declared JSON schema with all "
                    "literal term matching whole-line citations. Semantic status remains UNKNOWN.",
                    "input": args,
                    "source_revision": 1,
                    "source_hash": plan["source"]["hash"],
                    "output_schema": action.output_schema,
                },
                ensure_ascii=False,
            ),
        },
    ]
    tools = [t for t in definitions() if t["function"]["name"] == "resource.read"]
    used: set[str] = set()
    envelopes, read_result = 0, None
    request_start = len(model.requests)
    started = time.monotonic()
    for _ in range(limits.max_requests):
        envelope = len(
            json.dumps({"messages": messages, "tools": tools}, ensure_ascii=False).encode()
        )
        envelopes += envelope + limits.max_output_tokens
        if (
            envelope > 16000
            or envelopes > limits.max_total_tokens
            or time.monotonic() - started > limits.run_seconds
        ):
            raise DomainError("BUDGET_EXHAUSTED")
        raw = model.request(messages, tools)
        strict_json(json.dumps(raw), 20000)
        if time.monotonic() - started > limits.run_seconds:
            raise DomainError("BUDGET_EXHAUSTED")
        safe, calls = parse_response(raw)
        # Offline output bound is bytes; not a claim of actual tokenizer usage.
        if len(json.dumps(safe, ensure_ascii=False).encode()) > limits.max_output_tokens * 4:
            raise DomainError("BUDGET_EXHAUSTED")
        messages.append(safe)
        if calls:
            if read_result is not None or len(calls) != 1 or len(used) >= limits.max_tools:
                raise DomainError("BUDGET_EXHAUSTED")
            call = calls[0]
            if (
                call["id"] in used
                or call["function"]["name"] != "resource.read"
                or call["args"] != {"resource_id": args["resource_id"]}
            ):
                raise DomainError(
                    "MODEL_OUTPUT_INVALID", "Replay tool call exceeds frozen R0 scope"
                )
            used.add(call["id"])
            read_result = read(call["args"])
            if read_result != plan["source"]:
                raise DomainError("VERSION_CONFLICT", "Source changed during protocol")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "name": "resource.read",
                    "content": json.dumps(
                        {"status": "VERIFIED", "data": read_result}, ensure_ascii=False
                    ),
                }
            )
        else:
            if read_result is None:
                raise DomainError(
                    "VERIFICATION_FAILED", "Actual read feedback required before final"
                )
            output = strict_json(safe["content"], 16000)
            check = check_evidence(read_result, args, output)
            plan["protocol"] = {
                "mode": "OFFLINE_REPLAY",
                "provider_requests": 0,
                "requests": len(model.requests) - request_start,
                "tools": len(used),
                "messages": messages,
                "fingerprint": fingerprint(messages),
                "check": check,
            }
            return output
    raise DomainError("BUDGET_EXHAUSTED", "No final within frozen Replay budget")


def validate_protocol(plan, protocol, output):
    if not isinstance(protocol, dict) or not isinstance(protocol.get("messages"), list):
        raise DomainError("VERSION_CONFLICT", "Missing offline protocol")
    responses = []
    for message in protocol["messages"]:
        if not isinstance(message, dict):
            raise DomainError("VERSION_CONFLICT")
        if message.get("role") == "assistant":
            responses.append(
                {
                    "choices": [
                        {
                            "finish_reason": "tool_calls" if message.get("tool_calls") else "stop",
                            "message": message,
                        }
                    ]
                }
            )
    fresh = copy.deepcopy(plan)
    actual = execute_protocol(fresh, ReplayModel(responses), lambda _: plan["source"])
    if fingerprint(actual) != fingerprint(output) or fingerprint(fresh["protocol"]) != fingerprint(
        protocol
    ):
        raise DomainError("VERSION_CONFLICT", "Protocol no longer matches frozen input/readback")


def validate_accepted_replay(plan, responses, protocol, output):
    """Trace reconstruction alone cannot prove correspondence to the accepted wire data."""
    fresh = copy.deepcopy(plan)
    actual = execute_protocol(fresh, offline_replay_model(responses), lambda _: plan["source"])
    if fingerprint(actual) != fingerprint(output) or fingerprint(fresh["protocol"]) != fingerprint(protocol):
        raise DomainError("VERSION_CONFLICT", "Protocol differs from accepted offline Replay")


def verified_source(store, c, user, rid, limits, *, require_initial=True):
    from .app_jobs import load_binding
    from .lifecycle import data_rows, read_release

    job = c.execute(select(runs).where(runs.c.id == rid)).mappings().first()
    if not job or job["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    s, a = load_binding(store, c, user, job, limits)
    release = read_release(store, c, user, s["release_id"], limits)
    draft = release["snapshot"]["draft"]
    if (
        job["status"] != "SUCCEEDED"
        or a["status"] != "SUCCEEDED"
        or (require_initial and draft["candidate"]["manifest"]["origin"] != "goal")
        or not is_agent(draft["candidate"])
    ):
        raise DomainError("VERIFICATION_FAILED", "Verified initial agent AppRun required")
    rows = data_rows(c, s["instance_id"])
    record = next((r for r in rows if r["run_id"] == a["id"]), None)
    op = (
        c.execute(
            select(operations).where(
                operations.c.run_id == rid, operations.c.call_id == "instance_result"
            )
        )
        .mappings()
        .first()
    )
    resource = draft["candidate"]["manifest"]["data_bindings"][0]["resource_ref"]
    args = {"resource_id": resource, **s["input"]}
    source = authorized_read(
        store, c, user, s["runtime_id"], s["project_id"], "resource.read", {"resource_id": resource}
    )
    check = check_evidence(source, args, a["output"])
    intent = (
        c.execute(
            select(operation_intents.c.request).where(operation_intents.c.operation_id == op["id"])
        ).scalar()
        if op
        else None
    )
    receipt = op["receipt"] if op else None
    if (
        not record
        or not op
        or op["status"] != "VERIFIED"
        or op["tool_ref"] != "resource.read"
        or intent != {"tool": "resource.read", "args": {"resource_id": resource}}
        or op["fingerprint"] != fingerprint(intent)
        or not isinstance(receipt, dict)
        or receipt.get("data") != a["output"]
        or receipt.get("app_run_id") != a["id"]
        or receipt.get("result_version") != record["version"]
        or receipt.get("check_results") != [check]
        or not isinstance(receipt.get("protocol"), dict)
        or receipt["protocol"].get("check") != check
        or receipt["protocol"].get("mode") != "OFFLINE_REPLAY"
        or receipt["protocol"].get("provider_requests") != 0
        or fingerprint(receipt["protocol"].get("messages"))
        != receipt["protocol"].get("fingerprint")
    ):
        raise DomainError("VERSION_CONFLICT", "Source operation/readback lineage changed")
    validate_protocol(
        {"source": source, "args": args, "action": draft["candidate"]["actions"][0]},
        receipt["protocol"],
        a["output"],
    )
    if "offline_replay" in s:
        validate_accepted_replay(
            {"source": source, "args": args, "action": draft["candidate"]["actions"][0]},
            s["offline_replay"], receipt["protocol"], a["output"],
        )
    expected_receipt = {
        "operation_id": op["id"],
        "status": "VERIFIED",
        "app_run_id": a["id"],
        "instance_id": s["instance_id"],
        "release_id": s["release_id"],
        "result_version": record["version"],
        "output_fingerprint": fingerprint(a["output"]),
        "data": a["output"],
        "artifact_refs": [],
        "check_results": [check],
        "protocol": receipt["protocol"],
    }
    if fingerprint(receipt) != fingerprint(expected_receipt):
        raise DomainError("VERSION_CONFLICT", "Exact VERIFIED receipt identity/shape required")
    return {
        "kind": PROVENANCE,
        "source_run_id": rid,
        "run_fingerprint": job["fingerprint"],
        "release_fingerprint": release["fingerprint"],
        "input_fingerprint": fingerprint(s["input"]),
        "output_fingerprint": fingerprint(a["output"]),
        "receipt_fingerprint": fingerprint(receipt),
        "source_hash": source["hash"],
        "source_revision": 1,
        "check": check,
        "parameterized_fields": ["resource_binding", "term"],
        "goal": GOAL,
    }


def extract_agent_candidate(
    store, user, source_run, expected_proof, candidate, runtime, name, key, limits
):
    from .apps import compile_preview

    if not isinstance(key, str) or not 1 <= len(key) <= 100:
        raise DomainError("INVALID_INPUT")
    with store.tx() as c:
        pid = c.execute(select(runs.c.project_id).where(runs.c.id == source_run)).scalar()
        store.lock_project(c, user, pid)
        proof = verified_source(store, c, user, source_run, limits)
        if fingerprint(proof) != expected_proof:
            raise DomainError("VERSION_CONFLICT")
        request_fp = fingerprint(
            {"proof": expected_proof, "candidate": candidate, "runtime": runtime, "name": name}
        )
        old = (
            c.execute(
                select(task_extractions).where(
                    task_extractions.c.task_id == source_run,
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
            from .apps import load_draft

            load_draft(store, c, user, old["app_id"], limits)
            return {"id": old["app_id"], "cached": True}
        # Candidate may rebind resource and term input; schemas/protocol/check and budgets stay frozen.
        source_job = c.execute(
            select(internal_run_bindings.c.snapshot).where(
                internal_run_bindings.c.run_id == source_run
            )
        ).scalar_one()
        from .lifecycle import read_release

        original = read_release(store, c, user, source_job["release_id"], limits)["snapshot"][
            "draft"
        ]["candidate"]
        old_m, old_a, _ = compile_preview(original, limits)
        new_m, new_a, _ = compile_preview(candidate, limits)
        if (
            new_m.origin != "goal"
            or new_m.input_schema != old_m.input_schema
            or new_m.output_schema != old_m.output_schema
            or new_a.limits != old_a.limits
            or runtime != source_job["runtime_id"]
        ):
            raise DomainError("UNSUPPORTED_CAPABILITY")
        result = persist(c, store, user, pid, runtime, candidate, name, limits)
        frozen = copy.deepcopy(candidate)
        frozen["agent_provenance"] = proof
        frozen["manifest"]["origin"] = "task_run"
        frozen["manifest"]["source_run_ref"] = source_run
        from sqlalchemy import update

        c.execute(
            update(app_drafts)
            .where(app_drafts.c.id == result["id"])
            .values(candidate=frozen, fingerprint=fingerprint(frozen))
        )
        c.execute(
            insert(task_extractions).values(
                task_id=source_run,
                principal_id=user,
                request_key=key,
                request_fingerprint=request_fp,
                app_id=result["id"],
                snapshot={
                    "kind": PROVENANCE,
                    "proof": proof,
                    "candidate_fingerprint": fingerprint(frozen),
                "runtime_id": runtime,
                "project_id": pid,
                "accepted_name": name,
                },
            )
        )
        return result


def validate_agent_origin(store, c, user, draft, limits):
    candidate = draft["candidate"]
    marker = (
        c.execute(select(task_extractions).where(task_extractions.c.app_id == draft["id"]))
        .mappings()
        .first()
    )
    provenance = candidate.get("agent_provenance")
    if bool(marker) != (provenance is not None):
        raise DomainError("VERSION_CONFLICT", "Independent extraction marker required")
    if not marker:
        if candidate["manifest"]["origin"] != "goal":
            raise DomainError("VERSION_CONFLICT")
        return
    snap = marker["snapshot"]
    if (
        not isinstance(snap, dict)
        or snap.get("kind") != PROVENANCE
        or marker["principal_id"] != user
        or snap.get("proof") != provenance
        or snap.get("project_id") != draft["project_id"]
        or snap.get("runtime_id") != draft["runtime_id"]
        or snap.get("candidate_fingerprint") != draft["fingerprint"]
        or candidate["manifest"]["source_run_ref"] != marker["task_id"]
        or candidate["manifest"]["origin"] != "task_run"
        or verified_source(store, c, user, marker["task_id"], limits) != provenance
    ):
        raise DomainError("VERSION_CONFLICT", "Trusted source/provenance changed")
    accepted_candidate = copy.deepcopy(candidate)
    accepted_candidate.pop("agent_provenance")
    accepted_candidate["manifest"]["origin"] = "goal"
    accepted_candidate["manifest"]["source_run_ref"] = None
    accepted_request = {
        "proof": fingerprint(provenance),
        "candidate": accepted_candidate,
        "runtime": draft["runtime_id"],
        "name": snap.get("accepted_name"),
    }
    if marker["request_fingerprint"] != fingerprint(accepted_request):
        raise DomainError("VERSION_CONFLICT", "Independent accepted extraction request changed")
