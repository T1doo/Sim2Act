"""Read-only P-A literal generation conversation and original strict candidate checks.

No model IO, Run, Operation, source attestation or publication right is issued.
A separately bounded caller supplies actual adapter responses. Every transition
re-reads the original GoalCard and both authorities before consuming its content.
"""

import copy
import json

from . import goal_applications as generation
from .apps import compile_preview
from .contracts import GoalCardRunSource, Limits, strict_json, validate_value
from .db import fingerprint
from .errors import DomainError
from .goals import GoalCardInput, load_card
from .model import normalize_usage, parse_response, require_returned_model, returned_model_identity
from .text_apps import compute
from .tools import authorized_read

VERSION = "pa-literal-candidate-preview.v1"


def require(ok, message="Literal candidate preview context changed"):
    if not ok:
        raise DomainError("VERSION_CONFLICT", message)


def prepare(store, c, user, card_id, request, limits):
    """Read original owned Goal/material; allocate target IDs without creating a Run/App."""
    require(store.owns_connection(c) and not c.closed, "Original read connection required")
    request = generation.GenerationRunInput.model_validate(request)
    require(request.activation is None and request.family is None)
    require(type(limits) is Limits)
    limits = Limits.model_validate(limits.model_dump())
    card, project, history = load_card(store, c, user, card_id)
    require(card["version"] == request.expected_version
            and card["fingerprint"] == request.expected_fingerprint)
    saved = GoalCardRunSource(card_id=card_id, version=card["version"],
        fingerprint=card["fingerprint"], snapshot=history[0]["snapshot"])
    goal = GoalCardInput.model_validate(saved.snapshot["content"])
    require(len(goal.resource_refs) == 1, "One exact literal source required")
    source = authorized_read(store, c, user, project["runtime_id"], project["id"],
        "resource.read", {"resource_id": goal.resource_refs[0]})
    require(source["format"] in {"txt", "md"} and len(source["content"].encode()) <= 4096
            and len(source["content"].splitlines()) <= 64)
    selected = generation.policy("intern-s2", user, project["id"],
        {"card_id": card_id, **request.model_dump(exclude_none=True)})
    return dict(version=VERSION, user=user, project_id=project["id"], runtime_id=project["runtime_id"],
        card_id=card_id, request=request.model_dump(exclude_none=True), limits=limits.model_dump(),
        saved_goal=saved.model_dump(), source=source, selection=selected,
        messages=generation._literal_initial_messages(saved.model_dump(), selected, source,
                                                      limits.model_dump()))


def _current(store, c, user, context):
    # No cached source/permission result; regenerate the complete authorized value.
    require(type(context) is dict and context.get("version") == VERSION
            and context.get("user") == user)
    fresh = prepare(store, c, user, context["card_id"], context["request"],
                    Limits.model_validate(context["limits"]))
    require(fingerprint(fresh) == fingerprint(context))
    return fresh


def _reply(raw, limits):
    """Supplied response data is checked, never attested as a real provider call."""
    if type(raw) is not dict:
        raise DomainError("MODEL_OUTPUT_INVALID", "Exact response object required")
    identity = returned_model_identity("intern-s2", raw.get("model"))
    require_returned_model(identity)
    usage = normalize_usage(raw)
    require(usage["status"] == "known", "Known response usage required")
    require(usage["tokens"]["completion_tokens"] <= limits["max_output_tokens"]
            and usage["tokens"]["total_tokens"] <= limits["max_total_tokens"],
            "Candidate response exceeds the frozen preview limits")
    message, calls = parse_response(raw)
    return message, calls, identity, usage


def read_feedback(store, c, user, context, raw):
    """Original gateway read after one actual supplied resource.read selection."""
    fresh = _current(store, c, user, context)
    message, calls, _identity, _usage = _reply(raw, fresh["limits"])
    require(len(calls) == 1 and calls[0]["function"]["name"] == "resource.read"
            and calls[0]["args"] == {"resource_id": fresh["source"]["resource_id"]},
            "Only the original bound resource.read may supply feedback")
    result = authorized_read(store, c, user, fresh["runtime_id"], fresh["project_id"],
        "resource.read", calls[0]["args"])
    require(fingerprint(result) == fingerprint(fresh["source"]))
    tool = dict(role="tool", tool_call_id=calls[0]["id"],
                content=json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    _current(store, c, user, context)
    return dict(messages=[*copy.deepcopy(fresh["messages"]), message, tool],
                feedback=result, kind="AUTHORIZED_READ_NOT_OPERATION_RECEIPT")


def preview(store, c, user, context, raw, *, sample_inputs=()):
    """Strict original compiler + frozen bindings + read-only registered sample compute.

    This does not prove generation provenance, save a draft, confirm, release or
    create a runtime. The existing production/confirmation source gates remain.
    """
    fresh = _current(store, c, user, context)
    message, calls, identity, usage = _reply(raw, fresh["limits"])
    require(not calls and set(message) == {"role", "content"}, "Content-only candidate required")
    value = strict_json(message["content"], 16384)
    if not isinstance(value, dict) or set(value) != {"manifest", "actions", "source_hash", "goal"}:
        raise DomainError("INVALID_MANIFEST", "Closed provider candidate required")
    limits = Limits.model_validate(fresh["limits"])
    manifest, action, report = compile_preview(value, limits)
    generation._require_literal_candidate_binding(value, manifest, action,
        app_id=fresh["selection"]["app_id"], action_id=fresh["selection"]["action_id"],
        goal_id=fresh["card_id"], material=fresh["source"],
        goal=fresh["saved_goal"]["snapshot"]["content"], limits=limits)
    samples = []
    require(type(sample_inputs) in (tuple, list) and len(sample_inputs) <= 8)
    for item in sample_inputs:
        validate_value(manifest.input_schema, item)
        result = compute(fresh["source"], {"resource_id": fresh["source"]["resource_id"], **item})
        samples.append(dict(input=copy.deepcopy(item), result=result))
    _current(store, c, user, context)
    return dict(state="PREVIEW_ONLY", candidate=value, candidate_fingerprint=fingerprint(value),
        validation=report, samples=samples, model_identity=identity, usage=usage,
        provider_call_performed_by_entry=False, generation_provenance="NOT_ATTESTED",
        application_execution_performed=False, publishable=False,
        semantic_status="UNKNOWN", goal_acceptance="NOT_RUN")
