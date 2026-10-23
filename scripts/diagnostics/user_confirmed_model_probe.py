"""One user-authorized connection diagnostic, never production account authority.

Uses only the already configured Intern credential and the existing adapter.
No Store, Worker, application approval, source resolver or fee proof is created.
An exclusive output directory is the single-use execution record; failures never retry.
"""

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

from sim2act.config import Settings
from sim2act.contracts import strict_json
from sim2act.errors import DomainError
from sim2act.model import (
    InternModel,
    normalize_usage,
    parse_response,
    require_returned_model,
    returned_model_identity,
)

EXPECTED = {"probe": "sim2act-connectivity", "value": 7}
MAX_OUTPUT = 1024
REQUEST_SECONDS = 120
WINDOW_SECONDS = 600


def _save(output, report):
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")


def run(output, *, environ=None, _transport=None):
    """The transport argument is for isolated MockTransport tests, not a CLI option."""
    env = os.environ if environ is None else environ
    output.mkdir(parents=True, exist_ok=False)
    started, wall = time.monotonic(), time.time()
    report = dict(
        classification="USER_CONFIRMED_CONNECTION_DIAGNOSTIC",
        fee_basis="USER_CONFIRMED_NO_COST_NOT_OFFICIAL_VERIFICATION",
        production_authority=False,
        source_verification="NOT_PERFORMED",
        account_identity_verification="NOT_PERFORMED",
        endpoint=InternModel.ENDPOINT,
        model="intern-s2",
        limits=dict(requests=1, max_output_tokens=MAX_OUTPUT,
                    window_seconds=WINDOW_SECONDS, request_seconds=REQUEST_SECONDS),
        adapter_entries=0, wire_guard_entries=0, retries=0,
        provider_received="UNKNOWN", status="PREPARED",
        started_at=wall,
    )
    _save(output, report)
    try:
        if env.get("SIM2ACT_MODEL", "intern-s2") != "intern-s2":
            raise DomainError("CONFIGURATION_MISMATCH")
        token = env.get("SIM2ACT_INTERN_TOKEN", "") or env.get("INTERN_API_TOKEN", "")
        if not token:
            raise DomainError("CREDENTIAL_NOT_CONFIGURED")
        settings = Settings("unused-diagnostic-no-database", output, mode="live",
                            live_enabled=True, token=token, max_requests=1,
                            max_repairs=0, max_output_tokens=MAX_OUTPUT)
        body = json.dumps(dict(
            model="intern-s2", stream=False, max_tokens=MAX_OUTPUT, tools=[],
            messages=[dict(role="user", content=(
                'Return exactly this JSON object, with no other text and no tools: '
                '{"probe":"sim2act-connectivity","value":7}'))],
        ), separators=(",", ":")).encode()
        report["request_sha256"] = hashlib.sha256(body).hexdigest()
        report["request_bytes"] = len(body)
        deadline = min(wall + REQUEST_SECONDS, wall + WINDOW_SECONDS)

        def guard(request):
            report["wire_guard_entries"] += 1
            if not (report["wire_guard_entries"] == 1
                    and request.method == "POST" and str(request.url) == InternModel.ENDPOINT
                    and request.content == body and time.time() < deadline
                    and time.monotonic() - started < WINDOW_SECONDS):
                raise DomainError("DIAGNOSTIC_BOUNDARY_REJECTED")
            report["status"] = "DISPATCH_BOUNDARY_REACHED_OUTCOME_UNKNOWN"
            _save(output, report)
            return {"deadline": deadline}

        report["adapter_entries"] = 1
        _save(output, report)
        received = InternModel(settings, _transport).request_serialized_captured(body, guard)
        report["provider_received"] = "RESPONSE_RECEIVED"
        report["http_status"] = 200
        report["response_bytes"] = len(received.body)
        report["response_complete"] = True
        if token.encode() in received.body:
            raise DomainError("CREDENTIAL_ECHO_REDACTED")
        report["response_sha256"] = hashlib.sha256(received.body).hexdigest()
        raw = received.parsed
        report["usage"] = normalize_usage(raw)
        identity = returned_model_identity("intern-s2", raw.get("model") if type(raw) is dict else None)
        # Do not persist arbitrary provider strings, private reasoning or error bodies.
        report["model_identity"] = {k: v for k, v in identity.items() if k != "raw_returned_model"}
        require_returned_model(identity)
        safe, calls = parse_response(raw)
        if calls:
            raise DomainError("UNEXPECTED_TOOL_CALL")
        value = strict_json(safe["content"], 1024)
        if not (type(value) is dict and set(value) == set(EXPECTED)
                and type(value["probe"]) is str and value["probe"] == EXPECTED["probe"]
                and type(value["value"]) is int and value["value"] == 7):
            raise DomainError("DIAGNOSTIC_OUTPUT_MISMATCH")
        usage = report["usage"]["tokens"] or {}
        if usage.get("completion_tokens", 0) > MAX_OUTPUT:
            raise DomainError("DIAGNOSTIC_OUTPUT_BUDGET_EXCEEDED")
        report["validated_output"] = value
        report["status"] = "VALID_RESPONSE"
    except DomainError as error:
        report["status"] = "REJECTED_OR_FAILED"
        report["error_code"] = error.code
        captured = getattr(error, "_received_body", None)
        status = getattr(error, "_received_status_code", None)
        if type(status) is int and 100 <= status <= 599:
            report["http_status"] = status
            report["provider_received"] = "RESPONSE_HEADERS_RECEIVED"
        if type(captured) is bytes:
            if captured or getattr(error, "_received_body_complete", False):
                report["provider_received"] = "RESPONSE_BODY_CAPTURED"
            report["response_bytes"] = len(captured)
            if token.encode() not in captured:
                report["response_sha256"] = hashlib.sha256(captured).hexdigest()
            else:
                report["credential_echo_redacted"] = True
            report["response_complete"] = getattr(error, "_received_body_complete", False)
        # Never print exceptions: a transport error can reference a credential-bearing request.
    except Exception as error:
        report["status"] = "UNKNOWN_INTERNAL_FAILURE"
        report["error_type"] = type(error).__name__
    finally:
        report["elapsed_seconds"] = time.monotonic() - started
        report["finished_at"] = time.time()
        report["within_window"] = report["elapsed_seconds"] <= WINDOW_SECONDS
        _save(output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--execute-user-confirmed-diagnostic", action="store_true", required=True)
    args = parser.parse_args()
    report = run(args.output)
    print(json.dumps({key: report[key] for key in
                      ("status", "adapter_entries", "wire_guard_entries", "elapsed_seconds")}))
    return 0 if report["status"] == "VALID_RESPONSE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
