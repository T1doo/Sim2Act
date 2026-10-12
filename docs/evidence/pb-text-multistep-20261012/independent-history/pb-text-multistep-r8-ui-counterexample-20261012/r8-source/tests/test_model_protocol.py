"""Zero-network protocol contracts; fake evidence is explicitly test-only."""

import copy
import json
from dataclasses import replace
from pathlib import Path

import httpx
import pytest

from sim2act.config import Settings
from sim2act.db import fingerprint
from sim2act.errors import DomainError
from sim2act.model import InternModel
from sim2act.model_budget import BudgetedProvider, initialize_ledger
from sim2act.model_protocol import ModelProtocol, Scope, obj, validate_candidate

A, B = "res_" + "a" * 32, "res_" + "b" * 32
SCOPE = {
    "approval_id": "explicit-offline-test",
    "project_id": "proj_" + "c" * 32,
    "resource_ids": [A, B],
    "tool_refs": ["resource.read", "data.aggregate_csv"],
    "max_requests": 3,
    "mode": "offline",
    "model": "intern-s2",
}


def wire(value=None, calls=None, model="intern-s2"):
    message = {"role": "assistant", "content": json.dumps(value) if calls is None else ""}
    if calls is not None:
        message["tool_calls"] = [
            {
                "id": "read",
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)},
            }
            for name, args in calls
        ]
    return {
        "model": model,
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        "choices": [
            {"finish_reason": "stop" if calls is None else "tool_calls", "message": message}
        ],
    }


def read(tool, args):
    """Synthetic independent registered outputs, never caller-supplied gold input."""
    if tool == "resource.read":
        return {
            "resource_id": args["resource_id"],
            "content": "Alpha" if args["resource_id"] == A else "Beta",
            "hash": "a" * 64 if args["resource_id"] == A else "b" * 64,
            "format": "txt",
        }
    return {
        "resource_id": args["resource_id"],
        "column": args["column"],
        "count": 2,
        "sum": "3" if args["resource_id"] == A else "15",
        "source_hash": "a" * 64,
    }


def verify(stage, evidence):
    """TEST oracle checks real fixture data and complete outputs, independent of protocol."""
    if not evidence["tool_trace"]:
        return {"semantic_status": "UNKNOWN"}
    for entry in evidence["tool_trace"]:
        assert entry["data"] == read(entry["tool"], entry["args"])
    material = evidence["tool_trace"][0]["data"]
    expected = (
        {"summary": material["content"]} if "content" in material else {"total": material["sum"]}
    )
    if evidence["output"] != expected:
        return {"semantic_status": "UNKNOWN"}
    return {
        "status": "SUCCEEDED",
        "semantic_status": "PASS",
        "evidence_fingerprint": fingerprint(evidence),
        "goal_fingerprint": fingerprint(evidence["goal"]),
        "input_fingerprint": fingerprint(evidence["inputs"]),
        "output_fingerprint": fingerprint(evidence["output"]),
        "trace_fingerprint": fingerprint(evidence["tool_trace"]),
        "checks": [
            {"check_id": "TEST independent material/output/goal acceptance", "status": "PASS"}
        ],
    }


class FakeRunner:
    """Protocol-only fake; not a production approval or model adapter."""

    def __init__(self, responses, scope=SCOPE):
        self.responses, self.requests, self.halted = list(responses), [], False
        self.scope = copy.deepcopy(scope)
        self.accepted = {}
        self.latest_response_fingerprint = None

    def require_scope(self, scope):
        assert scope == self.scope
        if self.halted:
            raise DomainError("OUTCOME_UNKNOWN")

    def call(self, messages, tools):
        self.requests.append((copy.deepcopy(messages), copy.deepcopy(tools)))
        raw = self.responses.pop(0)
        content = raw["choices"][0]["message"]["content"]
        self.latest_response_fingerprint = fingerprint(json.loads(content)) if content else None
        return raw

    def accept_candidate(self, candidate_fingerprint, source_proof_fingerprint):
        if candidate_fingerprint != self.latest_response_fingerprint:
            raise DomainError("VERIFICATION_FAILED")
        slot = len(self.requests) - 1
        if slot in self.accepted:
            raise DomainError("VERIFICATION_FAILED")
        receipt = {
            "scope_fingerprint": fingerprint(SCOPE),
            "stage": "TEST extract",
            "slot": slot,
            "candidate_fingerprint": candidate_fingerprint,
            "source_proof_fingerprint": source_proof_fingerprint,
        }
        self.accepted[slot] = copy.deepcopy(receipt)
        return copy.deepcopy(receipt)

    def verify_candidate_receipt(self, receipt, candidate_fingerprint, source_proof_fingerprint):
        if (
            not isinstance(receipt, dict)
            or self.accepted.get(receipt.get("slot")) != receipt
            or receipt["candidate_fingerprint"] != candidate_fingerprint
            or receipt["source_proof_fingerprint"] != source_proof_fingerprint
        ):
            raise DomainError("VERIFICATION_FAILED")
        return True

    def halt(self):
        self.halted = True


def protocol(responses, verifier=verify):
    runner = FakeRunner(responses)
    return ModelProtocol(
        runner, scope=SCOPE, enabled=True, independent_verify=verifier, read_only=read
    ), runner


def candidate(language=True):
    item = {
        "schema_version": "model-protocol.v1",
        "input_schema": obj({"style": {"type": "string"}}),
        "resources": {"material": A},
        "steps": [
            {
                "id": "read",
                "kind": "registered_tool",
                "depends_on": [],
                "inputs": {
                    "resource_id": {"source": "data", "ref": "material", "field": "resource_id"}
                },
                "tool_ref": "resource.read",
            }
        ],
        "output_schema": obj({"summary": {"type": "string"}}),
        "outputs": {
            "summary": {
                "source": "step",
                "ref": "compose" if language else "read",
                "field": "summary" if language else "content",
            }
        },
    }
    if language:
        item["steps"].append(
            {
                "id": "compose",
                "kind": "language",
                "depends_on": ["read"],
                "inputs": {
                    "material": {"source": "step", "ref": "read", "field": "content"},
                    "style": {"source": "input", "ref": "input", "field": "style"},
                },
                "instruction": "Return the material in the requested style.",
                "output_schema": obj({"summary": {"type": "string"}}),
            }
        )
    return item


def completed():
    p, _ = protocol(
        [wire(calls=[("resource.read", {"resource_id": A})]), wire({"summary": "Alpha"})]
    )
    return p.complete_task("Return supplied material", {"style": "exact"}, [A])


@pytest.mark.parametrize("value", [True, 2.0, 0, 4, "2"])
def test_frozen_source_history_limit_is_strict_and_bounded(value):
    with pytest.raises(DomainError, match="Frozen source request limit"):
        ModelProtocol(scope=SCOPE, source_request_limit=value)


def test_one_request_extraction_uses_source_history_own_bound():
    source = completed()
    runner = FakeRunner([wire(candidate())], scope={**SCOPE, "max_requests": 1})
    protocol = ModelProtocol(
        runner,
        scope={**SCOPE, "max_requests": 1},
        enabled=True,
        independent_verify=verify,
        read_only=read,
        source_request_limit=2,
    )
    assert protocol.extract_candidate(source)["candidate"]
    assert len(runner.requests) == 1
    source["evidence"]["attempts"].append(copy.deepcopy(source["evidence"]["attempts"][0]))
    runner = FakeRunner([], scope={**SCOPE, "max_requests": 1})
    protocol = ModelProtocol(
        runner,
        scope={**SCOPE, "max_requests": 1},
        enabled=True,
        independent_verify=verify,
        read_only=read,
        source_request_limit=2,
    )
    with pytest.raises(DomainError, match="Complete bounded source trace"):
        protocol.extract_candidate(source)
    assert runner.requests == []


def test_default_disabled_no_call_or_authority():
    p = ModelProtocol()
    with pytest.raises(DomainError, match="disabled"):
        p.complete_task("read", {}, [A])
    runner = FakeRunner([])
    p = ModelProtocol(runner, scope=SCOPE, independent_verify=verify, read_only=read)
    with pytest.raises(DomainError):
        p.extract_candidate(completed())
    assert runner.requests == [] and not runner.halted


def test_model_selected_language_fields_dag_and_cold_new_material_no_old_answer():
    source = completed()
    p, runner = protocol([wire(candidate()), wire({"summary": "Beta"})])
    extracted = p.extract_candidate(source)
    assert extracted["candidate"]["steps"][1]["kind"] == "language"
    assert not extracted["executable_by_existing_apprun"]
    cold = p.run_candidate(extracted, {"style": "exact"}, {"material": B}, source=source)
    assert cold["status"] == "SUCCEEDED" and cold["evidence"]["output"] == {"summary": "Beta"}
    last = json.dumps(runner.requests[-1])
    assert "Beta" in last and "Alpha" not in last and A not in last


def test_model_can_select_different_registered_workflow_without_task_family():
    source = completed()
    item = {
        "schema_version": "model-protocol.v1",
        "input_schema": obj({"column": {"type": "string"}}),
        "resources": {"sheet": A},
        "steps": [
            {
                "id": "sum",
                "kind": "registered_tool",
                "tool_ref": "data.aggregate_csv",
                "depends_on": [],
                "inputs": {
                    "resource_id": {"source": "data", "ref": "sheet", "field": "resource_id"},
                    "column": {"source": "input", "ref": "input", "field": "column"},
                },
            }
        ],
        "output_schema": obj({"total": {"type": "string"}}),
        "outputs": {"total": {"source": "step", "ref": "sum", "field": "sum"}},
    }
    p, runner = protocol([wire(item)])
    extracted = p.extract_candidate(source)
    cold = p.run_candidate(extracted, {"column": "quantity"}, {"sheet": B}, source=source)
    assert cold["evidence"]["output"] == {"total": "15"} and len(runner.requests) == 1


@pytest.mark.parametrize("status", ["FAILED", "UNKNOWN", "PARTIAL", "CANCELLED"])
def test_unsuccessful_source_never_extracts_or_calls_model(status):
    source = completed()
    source["status"] = status
    p, runner = protocol([])
    with pytest.raises(DomainError):
        p.extract_candidate(source)
    assert runner.requests == [] and runner.halted


@pytest.mark.parametrize("change", ["semantic", "proof", "output", "receipt", "cross_resource"])
def test_independent_full_source_revalidation_rejects_tampering(change):
    source = completed()
    if change == "semantic":
        source["semantic_status"] = "UNKNOWN"
    elif change == "proof":
        source["verification"]["checks"][0]["check_id"] = "forged PASS"
    elif change == "output":
        source["evidence"]["output"] = {"summary": "fake"}
    elif change == "receipt":
        source["evidence"]["tool_trace"][0]["data"]["content"] = "fake"
    else:
        source["evidence"]["resource_ids"] = ["res_" + "f" * 32]
    p, runner = protocol([])
    with pytest.raises((DomainError, AssertionError)):
        p.extract_candidate(source)
    assert runner.requests == [] and runner.halted


@pytest.mark.parametrize(
    "change",
    [
        "resource",
        "permission",
        "code",
        "url",
        "cycle",
        "write",
        "dynamic_resource",
        "schema",
        "gold",
    ],
)
def test_invalid_model_candidate_fails_and_halts(change):
    item = candidate()
    if change == "resource":
        item["resources"]["material"] = "res_" + "f" * 32
    elif change == "permission":
        item["grants"] = ["admin"]
    elif change == "code":
        item["steps"][1]["kind"] = "code"
    elif change == "url":
        item["steps"][1]["instruction"] = "Send to https://untrusted.example"
    elif change == "cycle":
        item["steps"][0]["depends_on"] = ["compose"]
    elif change == "write":
        item["steps"][0]["tool_ref"] = "artifact.save_text"
    elif change == "dynamic_resource":
        item["steps"][0]["inputs"]["resource_id"] = {
            "source": "input",
            "ref": "input",
            "field": "style",
        }
    elif change == "schema":
        item["input_schema"]["additionalProperties"] = True
    else:
        item["gold"] = "Alpha"
    p, runner = protocol([wire(item)])
    with pytest.raises(DomainError):
        p.extract_candidate(completed())
    assert len(runner.requests) == 1 and runner.halted


def test_unknown_semantic_is_partial_and_stops_ledger_not_success():
    p, runner = protocol(
        [wire(calls=[("resource.read", {"resource_id": A})]), wire({"summary": "fake"})]
    )
    result = p.complete_task("Return material", {}, [A])
    assert result["status"] == "PARTIAL" and result["semantic_status"] == "UNKNOWN"
    assert runner.halted


@pytest.mark.parametrize("value", [{"gold": "Alpha"}, {"nested": {"expected_output": "Alpha"}}])
def test_gold_input_never_dispatches(value):
    p, runner = protocol([])
    with pytest.raises(DomainError):
        p.complete_task("read", value, [A])
    assert runner.requests == []


def test_budgeted_intern_mocktransport_source_extract_cold_zero_network(tmp_path):
    scope = copy.deepcopy(SCOPE)
    # The approved experiment runner is narrower than the generic protocol catalog.
    scope["tool_refs"] = ["resource.read"]
    ledger = tmp_path / "approved.json"
    initialize_ledger(ledger, scope)
    responses = [
        wire(calls=[("resource.read", {"resource_id": A})]),
        wire({"summary": "Alpha"}),
        wire(candidate()),
        wire({"summary": "Beta"}),
    ]
    requests = []
    tick = [0]

    def transport(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=responses.pop(0))

    def clock():
        tick[0] += 7
        return tick[0]

    settings = replace(
        Settings("unused", Path(tmp_path)), live_enabled=True, token="SYNTHETIC MOCK TOKEN"
    )
    model = InternModel(settings, transport=httpx.MockTransport(transport))

    def stage(name):
        runner = BudgetedProvider(
            model, ledger, scope, name, authorize=lambda actual: actual == scope, clock=clock
        )
        return ModelProtocol(
            runner, scope=scope, enabled=True, independent_verify=verify, read_only=read
        )

    source = stage("source_a").complete_task("Return material", {"style": "exact"}, [A])
    extracted = stage("extract_a").extract_candidate(source)
    result = stage("cold_a").run_candidate(
        extracted, {"style": "exact"}, {"material": B}, source=source
    )
    assert result["status"] == "SUCCEEDED" and result["evidence"]["output"] == {"summary": "Beta"}
    recorded = json.loads(ledger.read_text())
    assert len(requests) == len(recorded["slots"]) == 4 and not recorded["halted"]
    assert all(slot["status"] == "RECEIVED" for slot in recorded["slots"])
    assert recorded["known_tokens"] == 80 and recorded["reserved"] > 0
    assert "Alpha" not in json.dumps(requests[-1])


def test_source_tool_cannot_cross_scope_even_when_model_requests_registered_tool():
    p, runner = protocol([wire(calls=[("resource.read", {"resource_id": B})])])
    with pytest.raises(DomainError):
        p.complete_task("read A only", {}, [A])
    assert runner.halted


def test_model_identity_and_unknown_usage_refuse_even_test_transport():
    bad = wire({"anything": "value"}, model="other-model")
    p, runner = protocol([bad])
    with pytest.raises(DomainError):
        p.complete_task("read", {}, [A])
    assert runner.halted
    bad = wire({"anything": "value"})
    bad.pop("usage")
    p, runner = protocol([bad])
    with pytest.raises(DomainError, match="Unknown usage"):
        p.complete_task("read", {}, [A])
    assert runner.halted


def test_pure_candidate_validator_is_not_an_execution_entry():
    parsed = validate_candidate(candidate(False), Scope.model_validate(SCOPE))
    assert parsed.steps[0].tool_ref == "resource.read"


def test_invalid_protocol_response_halts_real_ledger_without_refund_or_followup(tmp_path):
    scope = {**SCOPE, "tool_refs": ["resource.read"]}
    ledger = tmp_path / "halt-approved.json"
    initialize_ledger(ledger, scope)
    calls = []

    def respond(request):
        calls.append(request.url)
        return httpx.Response(200, json=wire({"code": "unsupported"}))

    settings = replace(
        Settings("unused", tmp_path), live_enabled=True, token="SYNTHETIC MOCK TOKEN"
    )
    model = InternModel(settings, transport=httpx.MockTransport(respond))
    runner = BudgetedProvider(model, ledger, scope, "extract_a", authorize=lambda _: True)
    p = ModelProtocol(runner, scope=scope, enabled=True, independent_verify=verify, read_only=read)
    with pytest.raises(DomainError):
        p.extract_candidate(completed())
    first = json.loads(ledger.read_text())
    assert first["halted"] and first["reserved"] > 0 and len(first["slots"]) == 1
    assert first["slots"][0]["status"] == "RECEIVED"
    with pytest.raises(DomainError) as stopped:
        cold = BudgetedProvider(model, ledger, scope, "cold_a", authorize=lambda _: True)
        cold.call([{"role": "user", "content": "no automatic resend"}], [])
    assert stopped.value.code == "OUTCOME_UNKNOWN"
    assert len(calls) == 1 and json.loads(ledger.read_text()) == first


@pytest.mark.parametrize(
    "attempt",
    [
        None,
        {"identity": None, "usage": None},
        {"identity": {}, "usage": {}},
        {"identity": {"enforced": False}, "usage": {"status": "known"}},
    ],
)
def test_source_attempt_typed_shape_rejects_even_with_recomputed_caller_proof(attempt):
    source = completed()
    source["evidence"]["attempts"] = [attempt]
    source["verification"] = verify("source", source["evidence"])
    p, runner = protocol([])
    with pytest.raises(DomainError):
        p.extract_candidate(source)
    assert runner.requests == [] and runner.halted


@pytest.mark.parametrize("change", ["replace_valid", "missing_receipt", "rehash_receipt"])
def test_cold_independent_acceptance_rejects_valid_candidate_replacement_before_read_or_model(
    change,
):
    source = completed()
    p, extract_runner = protocol([wire(candidate())])
    extracted = p.extract_candidate(source)
    cold, cold_runner = protocol([])
    cold_runner.accepted = copy.deepcopy(extract_runner.accepted)
    reads = []
    cold.read_only = lambda *args: reads.append(args)
    if change == "replace_valid":
        extracted["candidate"] = candidate(False)
        extracted["candidate_fingerprint"] = fingerprint(extracted["candidate"])
    elif change == "missing_receipt":
        extracted.pop("candidate_receipt")
    else:
        extracted["candidate"]["steps"][1]["instruction"] = "Return changed but valid instruction."
        extracted["candidate_fingerprint"] = fingerprint(extracted["candidate"])
        extracted["candidate_receipt"]["candidate_fingerprint"] = extracted["candidate_fingerprint"]
    with pytest.raises(DomainError):
        cold.run_candidate(extracted, {"style": "exact"}, {"material": B}, source=source)
    assert reads == [] and cold_runner.requests == [] and cold_runner.halted


def test_validated_raw_candidate_preserves_explicit_nulls_for_accepted_response_anchor():
    source = completed()
    raw = candidate(False)
    raw["steps"][0]["instruction"] = None
    raw["steps"][0]["output_schema"] = None
    p, runner = protocol([wire(raw)])
    extracted = p.extract_candidate(source)
    assert extracted["candidate"] == raw and extracted["candidate_fingerprint"] == fingerprint(raw)
    assert (
        extracted["candidate_receipt"]["candidate_fingerprint"]
        == runner.latest_response_fingerprint
    )


def test_source_identity_enforced_integer_is_not_boolean_even_with_coherent_test_proof():
    source = completed()
    source["evidence"]["attempts"][0]["identity"]["enforced"] = 1
    source["verification"] = verify("source", source["evidence"])
    p, runner = protocol([])
    with pytest.raises(DomainError):
        p.extract_candidate(source)
    assert runner.requests == [] and runner.halted


def test_cold_receipt_verification_requires_positive_true_not_none():
    source = completed()
    p, _ = protocol([wire(candidate())])
    extracted = p.extract_candidate(source)
    cold, runner = protocol([])
    runner.verify_candidate_receipt = lambda *_: None
    reads = []
    cold.read_only = lambda *args: reads.append(args)
    with pytest.raises(DomainError):
        cold.run_candidate(extracted, {"style": "exact"}, {"material": B}, source=source)
    assert reads == [] and runner.requests == []


def test_trusted_store_deferred_evaluation_never_self_signs_or_halts_pending():
    runner = FakeRunner(
        [wire(calls=[("resource.read", {"resource_id": A})]), wire({"summary": "Alpha"})]
    )

    def forbidden_verifier(*_):
        raise AssertionError("Pending execution cannot sign its own semantic result")

    result = ModelProtocol(
        runner,
        scope=SCOPE,
        enabled=True,
        independent_verify=forbidden_verifier,
        read_only=read,
        defer_evaluation=True,
    ).complete_task("Read", {"style": "exact"}, [A])
    assert result["status"] == "AWAITING_EVALUATION"
    assert result["semantic_status"] == "UNKNOWN" and result["verification"] is None
    assert not runner.halted


def test_store_read_context_keeps_original_model_tool_call_identity():
    runner = FakeRunner(
        [wire(calls=[("resource.read", {"resource_id": A})]), wire({"summary": "Alpha"})]
    )
    seen = []

    def context_read(tool, args, context):
        seen.append(context)
        return read(tool, args)

    ModelProtocol(
        runner,
        scope=SCOPE,
        enabled=True,
        independent_verify=verify,
        read_only=context_read,
        read_context=True,
    ).complete_task("Read", {"style": "exact"}, [A])
    assert seen == [{"tool_call_id": "read", "request_index": 0, "step_id": None}]
