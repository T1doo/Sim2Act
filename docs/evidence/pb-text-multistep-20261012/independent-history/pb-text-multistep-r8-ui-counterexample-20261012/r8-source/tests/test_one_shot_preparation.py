"""Preparation cannot grant LIVE even with caller-filled declarations."""

import copy
import json
import socket
from pathlib import Path

import pytest
from pydantic import ValidationError

from sim2act.db import fingerprint
from sim2act.errors import DomainError
from sim2act.one_shot_preparation import CAPS, CHECKLIST, assess, measure_wire, prepare

ROOT = Path(__file__).resolve().parents[1]


def declared(prepared):
    receipt = {
        "artifact_sha256": "a" * 64,
        "prepared_scope_fingerprint": prepared["scope_fingerprint"],
    }
    return {
        "approval_receipt": receipt.copy(),
        "identity_fingerprint": "1" * 64,
        "revoked_identity_fingerprints": ["2" * 64],
        "previous_terminated_at": 100.0,
        "approved_at": 150.0,
        "expires_at": 300.0,
        "approved_caps": copy.deepcopy(CAPS),
        "receipts": {name: receipt.copy() for name in sum(CHECKLIST.values(), [])},
    }


def test_zero_network_no_identity_or_credentials_and_complete_packages(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Preparation must not connect or create a principal")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    from sim2act.db import Store

    monkeypatch.setattr(Store, "__init__", forbidden)
    value = prepare(ROOT)
    assert len(value["scope"]["public_packages"]) == 4
    assert "src/sim2act/api.py" in value["scope"]["components"]
    assert value["live_ready"] is False and value["effective_request_budget"] == 0
    assert value["identity_created"] is False and value["credentials_created"] is False
    state = assess(value, value["intake_template"], now=200)
    assert state["state"].startswith("BLOCKED") and state["live_ready"] is False
    assert all(c["status"] == "MISSING_OR_INVALID" for c in state["checks"])


def test_complete_receipt_declarations_are_never_send_authorization():
    value = prepare(ROOT)
    result = assess(value, declared(value), now=200)
    assert result["state"] == "DECLARATIONS_COMPLETE_FOR_REVIEW"
    assert result["live_ready"] is False and result["effective_request_budget"] == 0
    assert result["owner_confirmation"] == "PENDING" and result["semantic_acceptance"] == "UNKNOWN"


@pytest.mark.parametrize(
    "change,check",
    [
        ("expired", "fresh_full_approval"),
        ("old_approval", "fresh_full_approval"),
        ("wrong_scope", "fresh_full_approval"),
        ("revoked", "new_unrevoked_identity"),
        ("unknown_prior", "new_unrevoked_identity"),
        ("extra_budget", "caps_match_prepared_proposal"),
        ("missing_usage", "unknown_usage_and_outcome_stop"),
        ("missing_cleanup", "owned_services_stopped"),
    ],
)
def test_new_full_experiment_cannot_reuse_incomplete_or_old_metadata(change, check):
    value = prepare(ROOT)
    intake = declared(value)
    if change == "expired":
        intake["expires_at"] = 199.0
    elif change == "old_approval":
        intake["approved_at"] = 99.0
    elif change == "wrong_scope":
        intake["approval_receipt"]["prepared_scope_fingerprint"] = "0" * 64
    elif change == "revoked":
        intake["identity_fingerprint"] = "2" * 64
    elif change == "unknown_prior":
        intake["revoked_identity_fingerprints"] = []
    elif change == "extra_budget":
        intake["approved_caps"]["requests"] = 15
    elif change == "missing_usage":
        del intake["receipts"]["unknown_usage_and_outcome_stop"]
    elif change == "missing_cleanup":
        del intake["receipts"]["owned_services_stopped"]
    result = assess(value, intake, now=200)
    assert {"id": check, "status": "MISSING_OR_INVALID"} in result["checks"]
    assert result["live_ready"] is False and result["network_requests"] == 0


def test_returned_scope_has_no_mutable_alias_and_resealing_cannot_change_caps():
    original = fingerprint({"caps": CAPS, "checklist": CHECKLIST})
    value = prepare(ROOT)
    value["scope"]["proposed_caps_not_approved"]["requests"] = 999
    value["scope"]["checklist"]["before"].clear()
    assert fingerprint({"caps": CAPS, "checklist": CHECKLIST}) == original
    value["scope_fingerprint"] = fingerprint(value["scope"])
    with pytest.raises(DomainError) as raised:
        assess(value, {}, now=200)
    assert raised.value.code == "VERSION_CONFLICT"


@pytest.mark.parametrize("field", ["token", "password", "api_key"])
def test_intake_never_accepts_credentials(field):
    value = prepare(ROOT)
    with pytest.raises(ValidationError):
        assess(value, {field: "do-not-create-or-use"}, now=200)


def test_caps_bool_is_not_zero_repair_budget():
    value = prepare(ROOT)
    intake = declared(value)
    intake["approved_caps"]["repairs"] = False
    with pytest.raises(ValidationError):
        assess(value, intake, now=200)


def wire(content):
    return json.dumps(
        {
            "model": "intern-s2",
            "stream": False,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": content}],
            "tools": [],
        },
        ensure_ascii=False,
    ).encode()


def test_actual_serialized_wire_size_is_measured_but_never_authorized():
    result = measure_wire(wire("Public fixture only"))
    assert result["status"] == "WITHIN_SIZE_AND_ENVELOPE_LIMITS"
    assert result["egress_authorized"] is False and result["gold_screened"] is False
    assert measure_wire(wire("a" * 8001))["status"].startswith("OUTSIDE")
    result = measure_wire(wire("字" * 4000))
    assert result["characters"] < 8000 and result["utf8_bytes"] > 10000
    assert result["status"].startswith("OUTSIDE")
    assert measure_wire(b'{"model":NaN}')["status"] == "INVALID_UTF8_OR_JSON"
    assert measure_wire(b"\xff")["status"] == "INVALID_UTF8_OR_JSON"


def test_cli_invalid_intake_does_not_echo_secret(tmp_path):
    import os
    import subprocess
    import sys

    intake = tmp_path / "intake.json"
    intake.write_text(json.dumps({"token": "SYNTHETIC_SECRET_MUST_NOT_APPEAR"}))
    result = subprocess.run(
        [
            sys.executable,
            "scripts/prepare-one-shot-experiment.py",
            "--intake",
            str(intake),
            "--output",
            str(tmp_path / "output.json"),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        cwd=ROOT,
    )
    assert (
        result.returncode == 2
        and "SYNTHETIC_SECRET_MUST_NOT_APPEAR" not in result.stdout + result.stderr
    )
    assert not (tmp_path / "output.json").exists()
