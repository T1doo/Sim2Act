"""One-shot diagnostic boundaries, using synthetic credentials and MockTransport only."""

import importlib.util
import json
from pathlib import Path

import httpx
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/diagnostics/user_confirmed_model_probe.py"
spec = importlib.util.spec_from_file_location("confirmed_probe", SCRIPT)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
TOKEN = "synthetic-probe-credential-not-real"


def response(**changes):
    raw = dict(model="Intern-S2", usage=dict(prompt_tokens=10, completion_tokens=10,
               total_tokens=20), choices=[dict(finish_reason="stop", message=dict(
                   role="assistant", content=json.dumps(probe.EXPECTED)))])
    return {**raw, **changes}


def execute(tmp_path, receive, *, env=None):
    seen = []

    def handler(request):
        seen.append(request)
        return receive(request)

    output = tmp_path / "one-shot"
    result = probe.run(output, environ=env or {"INTERN_API_TOKEN": TOKEN},
                       _transport=httpx.MockTransport(handler))
    assert TOKEN not in (output / "result.json").read_text()
    return result, seen, output


def test_success_one_request_same_identity_and_exclusive_directory(tmp_path):
    report, seen, output = execute(tmp_path, lambda _: httpx.Response(200, json=response()))
    assert report["status"] == "VALID_RESPONSE"
    assert report["model_identity"]["verdict"] == "ACCEPTED"
    assert report["usage"]["status"] == "known"
    assert report["validated_output"] == probe.EXPECTED
    assert len(seen) == report["wire_guard_entries"] == report["adapter_entries"] == 1
    assert seen[0].headers["Authorization"] == "Bearer " + TOKEN
    body = json.loads(seen[0].content)
    assert body["model"] == "intern-s2" and body["stream"] is False
    assert body["max_tokens"] == 1024 and body["tools"] == []
    assert report["production_authority"] is False and report["retries"] == 0
    with pytest.raises(FileExistsError):
        probe.run(output, environ={"INTERN_API_TOKEN": TOKEN})
    assert len(seen) == 1


@pytest.mark.parametrize("env,code", [
    ({"SIM2ACT_MODEL": "different"}, "CONFIGURATION_MISMATCH"),
    ({"SIM2ACT_MODEL": "intern-s2"}, "CREDENTIAL_NOT_CONFIGURED"),
])
def test_missing_configuration_never_enters_adapter(tmp_path, env, code):
    report, seen, _ = execute(tmp_path, lambda _: pytest.fail("No send"), env=env)
    assert seen == [] and report["adapter_entries"] == 0 and report["error_code"] == code


@pytest.mark.parametrize("raw,code", [
    (response(model="other-model"), "MODEL_OUTPUT_INVALID"),
    (response(choices=[dict(finish_reason="length", message=dict(role="assistant", content="{}"))]),
     "MODEL_TIMEOUT_OR_TRUNCATED"),
    (response(choices=[dict(finish_reason="stop", message=dict(role="assistant", content=
        '{"probe":"sim2act-connectivity","value":true}'))]), "DIAGNOSTIC_OUTPUT_MISMATCH"),
    (response(choices=[dict(finish_reason="stop", message=dict(role="assistant", content=
        '{"probe":"sim2act-connectivity","value":7.0}'))]), "DIAGNOSTIC_OUTPUT_MISMATCH"),
    (response(choices=[dict(finish_reason="stop", message=dict(role="assistant", content=TOKEN))]),
     "CREDENTIAL_ECHO_REDACTED"),
])
def test_invalid_response_no_retry_or_unsafe_output(tmp_path, raw, code):
    report, seen, _ = execute(tmp_path, lambda _: httpx.Response(200, json=raw))
    assert len(seen) == 1 and report["retries"] == 0
    assert report["status"] == "REJECTED_OR_FAILED" and report["error_code"] == code
    assert "validated_output" not in report


def test_unknown_usage_preserved(tmp_path):
    raw = response()
    del raw["usage"]
    report, seen, _ = execute(tmp_path, lambda _: httpx.Response(200, json=raw))
    assert len(seen) == 1 and report["status"] == "VALID_RESPONSE"
    assert report["usage"] == {"status": "unknown", "tokens": None}


@pytest.mark.parametrize("status,code", [(403, "RESOURCE_UNAVAILABLE"), (429, "RATE_LIMITED")])
def test_upstream_refusal_no_retry_or_body_leak(tmp_path, status, code):
    report, seen, _ = execute(tmp_path, lambda _: httpx.Response(status, text=TOKEN))
    assert len(seen) == 1 and report["error_code"] == code and report["retries"] == 0
    # The streaming adapter rejects at headers and deliberately never reads this body.
    assert report["http_status"] == status
    assert report["provider_received"] == "RESPONSE_HEADERS_RECEIVED"
    assert report["response_complete"] is False and report["response_bytes"] == 0


def test_timeout_keeps_unknown_outcome_and_never_retries(tmp_path):
    def timeout(request):
        raise httpx.ReadTimeout(TOKEN, request=request)

    report, seen, _ = execute(tmp_path, timeout)
    assert len(seen) == 1 and report["error_code"] == "MODEL_TIMEOUT_OR_TRUNCATED"
    assert report["provider_received"] == "UNKNOWN" and report["retries"] == 0


def test_changed_wire_denied_before_transport(tmp_path, monkeypatch):
    original = probe.InternModel.request_serialized_captured

    def tampered(model, body, guard):
        return original(model, body + b" ", guard)

    monkeypatch.setattr(probe.InternModel, "request_serialized_captured", tampered)
    report, seen, _ = execute(tmp_path, lambda _: pytest.fail("No send"))
    assert seen == [] and report["error_code"] == "DIAGNOSTIC_BOUNDARY_REJECTED"


def test_bounded_stream_marks_incomplete(tmp_path):
    report, seen, _ = execute(tmp_path, lambda _: httpx.Response(200, content=b"x" * 131073))
    assert len(seen) == 1 and report["error_code"] == "MODEL_OUTPUT_INVALID"
    assert report["response_complete"] is False


def test_malformed_credential_echo_is_neither_saved_nor_hashed(tmp_path):
    report, seen, _ = execute(tmp_path, lambda _: httpx.Response(200, content=TOKEN.encode()))
    assert len(seen) == 1 and report["credential_echo_redacted"] is True
    assert "response_sha256" not in report


def test_sync_capture_private_status_does_not_change_public_error(tmp_path):
    settings = probe.Settings("unused", tmp_path, live_enabled=True, token=TOKEN)
    transport = httpx.MockTransport(lambda _: httpx.Response(403, text="denied"))
    with pytest.raises(probe.DomainError) as error:
        probe.InternModel(settings, transport).request_serialized_captured(b"{}", lambda _: None)
    assert error.value._received_status_code == 403
    assert error.value.code == "RESOURCE_UNAVAILABLE"
    assert "_received_status_code" not in error.value.public()
