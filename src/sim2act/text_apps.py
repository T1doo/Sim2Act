"""Registered deterministic literal retrieval; semantic acceptance stays UNKNOWN."""

from .agent_apps import CHECK, check_evidence, schemas
from .contracts import validate_value
from .db import fingerprint
from .errors import DomainError

REF = "text.literal_evidence"


def check_action(action):
    action_input, output = schemas()
    if (
        action.executor.kind != "registered_tool"
        or action.executor.ref != REF
        or action.input_schema != action_input
        or action.output_schema != output
        or action.allowed_tool_refs
        or action.preconditions
        or action.effect != "read"
        or action.idempotency != "read_only"
        or action.postcheck_refs != [CHECK]
        or len(action.dependencies) != 1
        or action.dependencies[0].kind != "resource"
        or [p.model_dump() for p in action.permission_requirements]
        != [{"tool_ref": "resource.read", "resource_ref": action.dependencies[0].ref}]
    ):
        raise DomainError("INVALID_MANIFEST", "Exact registered literal read contract required")


def compile_text(candidate, manifest, actions, report):
    if set(candidate) not in (
        {"manifest", "actions", "source_hash", "goal"},
        {"manifest", "actions", "source_hash", "goal", "goal_application"},
        {"manifest", "actions", "source_hash", "goal", "task_proof"},
    ):
        raise DomainError("INVALID_MANIFEST", "Closed text candidate required")
    if len(actions) != 1 or len(manifest.workflow) != 1 or len(manifest.data_bindings) != 1:
        raise DomainError("INVALID_MANIFEST", "One finite literal retrieval action required")
    action = actions[0]
    check_action(action)
    step = manifest.workflow[0]
    binding = manifest.data_bindings[0]
    _, output = schemas()
    if (
        manifest.input_schema
        != {
            "type": "object",
            "properties": {"term": action.input_schema["properties"]["term"]},
            "required": ["term"],
            "additionalProperties": False,
        }
        or manifest.output_schema != output
        or manifest.validation_suite_ref != CHECK
        or (manifest.origin, manifest.source_run_ref is None)
        != (("task_run", False) if "task_proof" in candidate else ("goal", True))
        or action.dependencies[0].ref != binding.resource_ref
        or [p.model_dump() for p in manifest.permission_requirements]
        != [p.model_dump() for p in action.permission_requirements]
        or step.depends_on
        or step.when is not None
        or {k: v.model_dump(exclude_none=True) for k, v in step.inputs.items()}
        != {
            "resource_id": {"source": "data", "ref": binding.binding_id, "field": "resource_id"},
            "term": {"source": "input", "field": "term"},
        }
        or {k: v.model_dump(exclude_none=True) for k, v in manifest.outputs.items()}
        != {k: {"source": "step", "ref": step.step_id, "field": k} for k in output["properties"]}
        or manifest.runtime_limits != action.limits
        or {(d.kind, d.ref, d.version) for d in manifest.dependency_lock}
        != {("resource", binding.resource_ref, "1"), ("tool", REF, "1"), ("check", CHECK, "1")}
        or not isinstance(candidate["source_hash"], str)
        or len(candidate["source_hash"]) != 64
    ):
        raise DomainError("INVALID_MANIFEST", "Literal wiring, source and check are frozen")
    return (
        manifest,
        action,
        {**report, "execution_mode": "REGISTERED_LITERAL", "semantic_status": "UNKNOWN"},
    )


def compute(source, args):
    term = args.get("term")
    if (
        source["format"] not in {"txt", "md"}
        or len(source["content"].encode()) > 4096
        or len(source["content"].splitlines()) > 64
        or not isinstance(term, str)
        or not term
        or term != term.strip()
        or len(term) > 80
    ):
        raise DomainError("INVALID_INPUT", "Finite TXT/MD and nonempty trimmed term required")
    citations = [
        {"start_line": i, "end_line": i, "quote": line}
        for i, line in enumerate(source["content"].splitlines(), 1)
        if term in line
    ]
    if len(citations) > 16:
        raise DomainError("INVALID_INPUT", "At most sixteen matching lines supported")
    value = {
        "resource_id": args["resource_id"],
        "revision": 1,
        "source_hash": source["hash"],
        "term": term,
        "citations": citations,
        "semantic_status": "UNKNOWN",
    }
    validate_value(schemas()[1], value)
    check_evidence(source, args, value)
    return value


def verify_origin(store, c, user, draft, limits):
    if "task_proof" in draft["candidate"]:
        from .registered_run_extraction import validate_registered_candidate

        validate_registered_candidate(store, c, user, draft, limits)
        return
    from pydantic import ValidationError
    from sqlalchemy import select

    from .db import events, goal_application_candidates, runs
    from .goal_applications import ConfirmInput, verified_candidate

    marker = (
        c.execute(
            select(goal_application_candidates).where(
                goal_application_candidates.c.app_id == draft["id"]
            )
        )
        .mappings()
        .first()
    )
    if not marker or marker["principal_id"] != user:
        raise DomainError("VERSION_CONFLICT", "Independent goal generation marker required")
    run = c.execute(select(runs).where(runs.c.id == marker["run_id"])).mappings().one()
    raw = verified_candidate(store, c, run, limits)
    try:
        confirmation = ConfirmInput.model_validate(marker["confirmation"])
    except (ValidationError, ValueError, TypeError) as exc:
        raise DomainError("VERSION_CONFLICT", "Exact candidate confirmation missing") from exc
    accepted = {
        "app_id": draft["id"],
        "run_id": run["id"],
        "principal_id": user,
        "project_id": draft["project_id"],
        "runtime_id": draft["runtime_id"],
        "candidate_fingerprint": fingerprint(raw),
        "confirmation": confirmation.model_dump(),
    }
    sealed = (
        c.execute(
            select(events.c.data).where(
                events.c.run_id == run["id"], events.c.kind == "GA_APP_CONFIRMED"
            )
        )
        .scalars()
        .all()
    )
    if (
        sealed != [accepted]
        or confirmation.candidate_fingerprint != fingerprint(raw)
        or confirmation.expected_version != run["version"]
    ):
        raise DomainError(
            "VERSION_CONFLICT", "Candidate confirmation differs from exact accepted authorization"
        )
    expected = {
        **raw,
        "goal_application": {"run_id": run["id"], "candidate_fingerprint": fingerprint(raw)},
    }
    ready = {
        "candidate": raw,
        "candidate_fingerprint": fingerprint(raw),
        "goal_acceptance": "NOT_RUN",
        "semantic_status": "UNKNOWN",
        "app_created": False,
    }
    if (
        run["status"] != "PARTIAL"
        or run["cancel_intent"]
        or run["error"] is not None
        or run["result"] != ready
        or run["principal_id"] != user
        or run["project_id"] != draft["project_id"]
        or marker["candidate_fingerprint"] != fingerprint(raw)
        or fingerprint(expected) != draft["fingerprint"]
        or expected != draft["candidate"]
    ):
        raise DomainError("VERSION_CONFLICT", "Candidate differs from actual goal generation")
