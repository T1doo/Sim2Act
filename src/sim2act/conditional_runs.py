"""Explicit bounded Report runs and candidate-only checks; never Run semantic approval."""

import copy
import json
import re

from fastapi import Depends
from pydantic import Field, ValidationError
from sqlalchemy import select

from .conditional_checks import (
    CONTRACT,
    SOURCE_HASH,
    CheckInput,
    Report,
    Scenario,
    evaluate_source,
)
from .contracts import Strict, strict_json
from .db import events, fingerprint, new_id
from .errors import DomainError
from .model_protocol import obj, validate_candidate
from .tools import authorized_read

NAMESPACE = "conditional-run-checks.v1"
SOURCE = "bounded.conditional-report-source.v1"
COLD = "bounded.conditional-report-cold.v1"
GOAL = "只核对公开注册的A-S有限规则及显式假设事实，返回Report结构的条件、逐行引用、决策、行动、原期限和例外；说明文字不在验收范围，不执行业务动作。"
CHECK_EVENT = "CONDITIONAL_RUN_CHECK"
ANCHOR_EVENT = "CONDITIONAL_CHECK_ANCHOR"


def report_schema():
    text = {"type": "string", "maxLength": 1000}
    finding = obj(
        {
            "rule_id": {"type": "string", "enum": ["R1", "R2", "R3"]},
            "applies": {"type": "string", "enum": ["TRUE", "FALSE", "UNKNOWN"]},
            "citation": obj(
                {"line": {"type": "integer", "minimum": 1, "maximum": 200}, "quote": text}
            ),
        }
    )
    return obj(
        {
            "findings": {"type": "array", "items": finding, "maxItems": 3},
            "decision": {"type": "string", "enum": ["ALLOW", "BLOCK", "UNKNOWN"]},
            "next_actions": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "wait_trip_end",
                        "obtain_receipt",
                        "obtain_prior_approval",
                        "clarify_facts",
                        "clarify_late_policy",
                        "submit_claim_and_receipt",
                    ],
                },
                "maxItems": 6,
            },
            "deadline_days": {"type": "integer", "minimum": 1, "maximum": 3650},
            "absolute_date": {"type": "string", "maxLength": 40},
            "receipt_restarts_deadline": {"type": "boolean"},
            "explanation": text,
        }
    )


def inputs_for(scenario):
    try:
        parsed = Scenario.model_validate(scenario).model_dump()
    except ValidationError as exc:
        raise DomainError("INVALID_INPUT", "Strict hypothetical facts required") from exc
    return {
        "scenario_json": json.dumps(parsed, sort_keys=True, ensure_ascii=False),
        "report_schema_json": json.dumps(report_schema(), sort_keys=True, ensure_ascii=False),
    }


def scenario_from(inputs):
    if not isinstance(inputs, dict) or set(inputs) != {"scenario_json", "report_schema_json"}:
        raise DomainError("INVALID_INPUT")
    scenario = strict_json(inputs["scenario_json"], 3000)
    if inputs_for(scenario) != inputs:
        raise DomainError(
            "VERSION_CONFLICT", "Canonical facts and registered Report schema required"
        )
    return Scenario.model_validate(scenario)


def contract_snapshot(contract_id, inputs):
    if contract_id not in {SOURCE, COLD}:
        raise DomainError("RESOURCE_UNAVAILABLE")
    scenario_from(inputs)
    value = {
        "contract_id": contract_id,
        "version": 1,
        "checker": NAMESPACE,
        "source_hash": SOURCE_HASH,
        "public_goal": GOAL,
        "resource_hashes": [SOURCE_HASH],
        "output_schema": report_schema(),
        "frozen_inputs": copy.deepcopy(inputs),
        "expected_inputs_fingerprint": fingerprint(inputs),
        "check_contract_fingerprint": fingerprint(CONTRACT),
        "scope": "finite Report structure and explicit hypothetical facts only; explanation NOT_CHECKED",
        "semantic_status": "UNKNOWN",
        "owner_acceptance": "PENDING",
    }
    return {**value, "fingerprint": fingerprint(value)}


def validate_snapshot(snapshot):
    if snapshot.get("bounded_check_namespace") != NAMESPACE:
        raise DomainError("PERMISSION_DENIED")
    saved = snapshot.get("contract")
    if not isinstance(saved, dict):
        raise DomainError("VERSION_CONFLICT")
    expected = contract_snapshot(saved.get("contract_id"), saved.get("frozen_inputs"))
    if fingerprint(saved) != fingerprint(expected):
        raise DomainError("VERSION_CONFLICT", "Bounded check registry changed")
    role = "cold" if snapshot["phase"] == "cold" else "source"
    if saved["contract_id"] != (COLD if role == "cold" else SOURCE):
        raise DomainError("VERSION_CONFLICT")


def candidate_for(contract, resource_id):
    if not isinstance(contract, dict) or "frozen_inputs" not in contract:
        raise DomainError("VERSION_CONFLICT")
    if fingerprint(contract) != fingerprint(contract_snapshot(SOURCE, contract["frozen_inputs"])):
        raise DomainError("VERSION_CONFLICT")
    input_schema = obj(
        {
            "scenario_json": {"type": "string", "maxLength": 3000},
            "report_schema_json": {"type": "string", "maxLength": 5000},
        }
    )
    schema = report_schema()
    return {
        "schema_version": "model-protocol.v1",
        "input_schema": input_schema,
        "resources": {"rules": resource_id},
        "steps": [
            {
                "id": "read_rules",
                "kind": "registered_tool",
                "depends_on": [],
                "inputs": {
                    "resource_id": {"source": "data", "ref": "rules", "field": "resource_id"}
                },
                "tool_ref": "resource.read",
            },
            {
                "id": "check_report",
                "kind": "language",
                "depends_on": ["read_rules"],
                "inputs": {
                    "content": {"source": "step", "ref": "read_rules", "field": "content"},
                    "scenario_json": {"source": "input", "ref": "input", "field": "scenario_json"},
                    "report_schema_json": {
                        "source": "input",
                        "ref": "input",
                        "field": "report_schema_json",
                    },
                },
                "instruction": GOAL,
                "output_schema": schema,
            },
        ],
        "output_schema": schema,
        "outputs": {
            field: {"source": "step", "ref": "check_report", "field": field}
            for field in schema["properties"]
        },
    }


def validate_report(value):
    try:
        return Report.model_validate(value)
    except ValidationError as exc:
        raise DomainError(
            "VERIFICATION_FAILED", "Actual Report violates the registered strict structure"
        ) from exc


def _current_check(store, c, user, pid, rid):
    from .protocol_jobs import verified_pending

    job, run = verified_pending(store, c, user, rid)
    snapshot = job["snapshot"]
    validate_snapshot(snapshot)
    if run["project_id"] != pid:
        raise DomainError("PERMISSION_DENIED")
    if (
        job["phase"] not in {"source", "cold"}
        or run["status"] != "WAITING_APPROVAL"
        or run["error"] is not None
        or run["cancel_intent"]
        or not job["result"]
        or store.has_unknown(c, rid)
    ):
        raise DomainError(
            "VERIFICATION_FAILED", "Known complete technical receipt required; not a successful Run"
        )
    complete = job["result"]
    technical = complete["protocol_result"]
    evidence = technical["evidence"]
    if (
        technical["status"] != "AWAITING_EVALUATION"
        or technical["semantic_status"] != "UNKNOWN"
        or complete["completed_run_version"] != run["version"]
        or evidence["goal"] != GOAL
        or evidence["inputs"] != snapshot["contract"]["frozen_inputs"]
        or len(evidence["resource_ids"]) != 1
    ):
        raise DomainError("VERSION_CONFLICT")
    scenario = scenario_from(evidence["inputs"])
    rid_source = evidence["resource_ids"][0]
    source = authorized_read(
        store, c, user, run["runtime_id"], pid, "resource.read", {"resource_id": rid_source}
    )
    request = CheckInput(
        resource_id=rid_source,
        expected_source_hash=SOURCE_HASH,
        expected_contract_fingerprint=fingerprint(CONTRACT),
        scenario=scenario,
        report=validate_report(evidence["output"]),
    )
    checked = evaluate_source(request, source)
    eligible = (
        checked["check_status"] == "PASS"
        and checked["decision"] != "UNKNOWN"
        and all(value is not None for value in scenario.model_dump().values())
        and all(rule["satisfaction"] != "UNKNOWN" for rule in checked["rule_results"])
    )
    return (
        job,
        run,
        {
            "namespace": NAMESPACE,
            "run_id": rid,
            "project_id": pid,
            "principal_id": user,
            "runtime_id": run["runtime_id"],
            "version": run["version"],
            "fence": run["fence"],
            "accepted_fingerprint": job["fingerprint"],
            "result_fingerprint": job["result_fingerprint"],
            "contract_fingerprint": snapshot["contract"]["fingerprint"],
            "goal_fingerprint": fingerprint(evidence["goal"]),
            "input_fingerprint": fingerprint(evidence["inputs"]),
            "output_fingerprint": fingerprint(evidence["output"]),
            "trace_fingerprint": fingerprint(evidence["tool_trace"]),
            "checks": checked,
            "candidate_eligible": eligible,
            "overall_run_acceptance": "NOT_ACCEPTED",
            "semantic_status": "UNKNOWN",
            "owner_acceptance": "PENDING",
            "formal_publication_enabled": False,
        },
    )


class CheckRequest(Strict):
    expected_result_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_version: int = Field(strict=True, ge=1)
    expected_fence: int = Field(strict=True, ge=1)
    request_key: str = Field(min_length=1, max_length=100)


def _check_request(value, *, stored=False):
    try:
        return CheckRequest.model_validate(value).model_dump()
    except (ValidationError, TypeError, ValueError) as exc:
        raise DomainError(
            "VERSION_CONFLICT" if stored else "INVALID_INPUT", "Closed check request required"
        ) from exc


def check_run(store, user, pid, rid, body):
    request = _check_request(body)
    with store.tx() as c:
        store.lock_project(c, user, pid)
        job, run, value = _current_check(store, c, user, pid, rid)
        if any(
            request["expected_" + name] != value[name]
            for name in ["result_fingerprint", "version", "fence"]
        ):
            raise DomainError("VERSION_CONFLICT")
        value["request"] = request
        records = list(
            c.execute(
                select(events.c.data).where(events.c.run_id == rid, events.c.kind == CHECK_EVENT)
            ).scalars()
        )
        for record in records:
            if (
                not isinstance(record, dict)
                or not isinstance(record.get("value"), dict)
                or not isinstance(record["value"].get("request"), dict)
            ):
                raise DomainError("VERSION_CONFLICT", "Malformed stored check receipt")
            if (
                isinstance(record, dict)
                and record.get("value", {}).get("request", {}).get("request_key")
                == request["request_key"]
            ):
                reverify_check(store, c, user, pid, rid, record["fingerprint"])
                if fingerprint(record["value"]) != fingerprint(value):
                    raise DomainError("VERSION_CONFLICT")
                return copy.deepcopy(record)
        record = {"check_id": new_id("check"), "value": value, "fingerprint": fingerprint(value)}
        store.event(c, rid, CHECK_EVENT, record)
        store.event(c, record["check_id"], ANCHOR_EVENT, record)
        return copy.deepcopy(record)


def reverify_check(store, c, user, pid, rid, expected_fingerprint, *, eligible=False):
    _, _, current = _current_check(store, c, user, pid, rid)
    records = list(
        c.execute(
            select(events.c.data).where(events.c.run_id == rid, events.c.kind == CHECK_EVENT)
        ).scalars()
    )
    matching = [
        r for r in records if isinstance(r, dict) and r.get("fingerprint") == expected_fingerprint
    ]
    if len(matching) != 1:
        raise DomainError("VERIFICATION_FAILED", "Unique current Run check binding required")
    record = matching[0]
    if (
        set(record) != {"check_id", "value", "fingerprint"}
        or not isinstance(record["check_id"], str)
        or not re.fullmatch(r"check_[a-f0-9]{32}", record["check_id"])
        or not isinstance(record["value"], dict)
        or fingerprint(record["value"]) != expected_fingerprint
    ):
        raise DomainError("VERSION_CONFLICT")
    anchors = list(
        c.execute(
            select(events.c.data).where(
                events.c.run_id == record["check_id"], events.c.kind == ANCHOR_EVENT
            )
        ).scalars()
    )
    if fingerprint(anchors) != fingerprint([record]):
        raise DomainError("VERSION_CONFLICT", "Independent check receipt anchor changed")
    request = _check_request(record["value"].get("request"), stored=True)
    current["request"] = request
    if fingerprint(current) != expected_fingerprint or any(
        request["expected_" + k] != current[k] for k in ["result_fingerprint", "version", "fence"]
    ):
        raise DomainError(
            "VERSION_CONFLICT", "Stored check does not bind current actual Run evidence"
        )
    if eligible and not current["candidate_eligible"]:
        raise DomainError(
            "VERIFICATION_FAILED",
            "UNKNOWN facts, failed checks or uncovered goal cannot authorize a candidate",
        )
    return copy.deepcopy(record)


def source_completion(store, c, user, rid, expected_result, expected_check):
    from .protocol_jobs import verified_pending

    job, run = verified_pending(store, c, user, rid)
    if job["phase"] != "source":
        raise DomainError("VERIFICATION_FAILED")
    check = reverify_check(store, c, user, run["project_id"], rid, expected_check, eligible=True)
    if expected_result != job["result_fingerprint"]:
        raise DomainError("VERSION_CONFLICT")
    return {
        "run_id": rid,
        "result_fingerprint": expected_result,
        "proof": check,
        "proof_fingerprint": fingerprint(check),
        "check_fingerprint": expected_check,
        "overall_run_acceptance": "NOT_ACCEPTED",
        "semantic_status": "UNKNOWN",
    }


def extract_candidate(store, run, snapshot, protocol):
    """Compile only the public finite template from current trusted technical evidence."""
    from .protocol_jobs import verified_pending

    frozen = snapshot["source"]
    with store.tx() as c:
        current = source_completion(
            store,
            c,
            run["principal_id"],
            frozen["run_id"],
            frozen["result_fingerprint"],
            frozen["check_fingerprint"],
        )
        if current != frozen:
            raise DomainError("VERSION_CONFLICT")
        source_job, source_run = verified_pending(store, c, run["principal_id"], frozen["run_id"])
        template = candidate_for(source_job["snapshot"]["contract"], source_run["resource_refs"][0])
        output = copy.deepcopy(source_job["result"]["protocol_result"]["evidence"]["output"])
    prompt = {
        "public_template": template,
        "actual_checked_report": output,
        "technical_check_fingerprint": frozen["check_fingerprint"],
        "overall_run_acceptance": "NOT_ACCEPTED",
        "semantic_status": "UNKNOWN",
    }
    message, calls = protocol._call(
        [
            {
                "role": "system",
                "content": "Return exactly the public finite reusable declaration as JSON. The actual checked report is evidence only; never embed its answers or facts into the declaration. No code, authority, URLs or additional steps.",
            },
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        [],
        [],
    )
    if calls:
        raise DomainError("INVALID_MANIFEST")
    candidate = strict_json(message["content"])
    validate_candidate(candidate, protocol.scope)
    if fingerprint(candidate) != fingerprint(template):
        raise DomainError(
            "INVALID_MANIFEST",
            "Only the registered finite parameterized Report declaration is covered",
        )
    proof = frozen["proof"]
    receipt = protocol.runner.accept_candidate(fingerprint(candidate), fingerprint(proof))
    return {
        "kind": "model-protocol.v1",
        "candidate": candidate,
        "candidate_fingerprint": fingerprint(candidate),
        "source_proof": proof,
        "source_proof_fingerprint": fingerprint(proof),
        "candidate_receipt": receipt,
        "executable_by_existing_apprun": False,
        "semantic_status": "NOT_RUN",
    }


class StartRequest(Strict):
    resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    expected_source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_contract_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    goal: str = Field(min_length=1, max_length=1000)
    scenario: Scenario
    request_key: str = Field(min_length=1, max_length=100)


class ExtractRequest(Strict):
    source_run_id: str = Field(pattern=r"^run_[a-f0-9]{32}$")
    expected_source_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_check_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    request_key: str = Field(min_length=1, max_length=100)


class ColdRequest(Strict):
    extraction_run_id: str = Field(pattern=r"^run_[a-f0-9]{32}$")
    expected_plan_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    scenario: Scenario
    request_key: str = Field(min_length=1, max_length=100)


def mount(app, store, identity, limits, settings):
    dependency = Depends(identity)

    def offline():
        if settings.mode != "mock":
            raise DomainError(
                "PERMISSION_DENIED", "Only explicit offline bounded validation exists"
            )

    @app.get("/api/projects/{pid}/conditional-runs/contract")
    def contract(pid: str, user=dependency):
        with store.tx() as c:
            store.own_project(c, user, pid)
        return {
            "namespace": NAMESPACE,
            "goal": GOAL,
            "source_hash": SOURCE_HASH,
            "check_contract_fingerprint": fingerprint(CONTRACT),
            "report_schema": report_schema(),
            "report_validation_schema": Report.model_json_schema(),
            "scenario_schema": Scenario.model_json_schema(),
            "semantic_status": "UNKNOWN",
            "owner_acceptance": "PENDING",
            "candidate_only": True,
            "formal_publication_enabled": False,
        }

    @app.post("/api/projects/{pid}/conditional-runs/source", status_code=202)
    def source(pid: str, body: StartRequest, user=dependency):
        from .protocol_jobs import enqueue

        offline()
        if (
            body.goal != GOAL
            or body.expected_source_hash != SOURCE_HASH
            or body.expected_contract_fingerprint != fingerprint(CONTRACT)
        ):
            raise DomainError("VERSION_CONFLICT", "Exact bounded goal and registry required")
        payload = {
            "goal": GOAL,
            "inputs": inputs_for(body.scenario.model_dump()),
            "resource_ids": [body.resource_id],
            "contract_id": SOURCE,
        }
        return enqueue(store, user, pid, "source", payload, body.request_key, limits, bounded=True)

    @app.post("/api/projects/{pid}/conditional-runs/{rid}/checks", status_code=201)
    def check(pid: str, rid: str, body: CheckRequest, user=dependency):
        offline()
        return check_run(store, user, pid, rid, body.model_dump())

    @app.post("/api/projects/{pid}/conditional-runs/extract", status_code=202)
    def extract(pid: str, body: ExtractRequest, user=dependency):
        from .protocol_jobs import enqueue

        offline()
        payload = body.model_dump()
        key = payload.pop("request_key")
        return enqueue(store, user, pid, "extract", payload, key, limits, bounded=True)

    @app.post("/api/projects/{pid}/conditional-runs/cold", status_code=202)
    def cold(pid: str, body: ColdRequest, user=dependency):
        from .protocol_jobs import enqueue

        offline()
        return enqueue(
            store,
            user,
            pid,
            "cold",
            {
                "extraction_run_id": body.extraction_run_id,
                "expected_plan_fingerprint": body.expected_plan_fingerprint,
                "resource_bindings": {"rules": body.resource_id},
                "inputs": inputs_for(body.scenario.model_dump()),
                "contract_id": COLD,
            },
            body.request_key,
            limits,
            bounded=True,
        )

    @app.get("/api/projects/{pid}/conditional-runs/{rid}")
    def inspect_run(pid: str, rid: str, user=dependency):
        from .protocol_jobs import _public, verified_pending

        with store.tx() as c:
            store.own_project(c, user, pid)
            job, run = verified_pending(store, c, user, rid)
            if run["project_id"] != pid:
                raise DomainError("PERMISSION_DENIED")
            validate_snapshot(job["snapshot"])
            return _public(job, run)
