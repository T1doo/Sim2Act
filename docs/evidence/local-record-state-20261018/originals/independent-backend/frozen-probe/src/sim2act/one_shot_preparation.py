"""Zero-network preparation/intake metadata. No credential, identity or LIVE executor."""

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Annotated

from pydantic import Field, StrictInt

from .contracts import Strict
from .db import fingerprint
from .errors import DomainError

MANIFEST_SHA = "9227a1d78e24ba3e1660dae408d169fd02df74dc36523cd689a83b881af2b4e4"
PACKAGES = {"a-source", "a-cold", "b-source", "b-cold"}
CAPS = {
    "requests": 14,
    "total_tokens": 64000,
    "output_tokens": 1024,
    "wire_characters": 8000,
    "wire_bytes": 10000,
    "spacing_seconds": 6,
    "stage_seconds": 300,
    "repairs": 0,
}
CHECKLIST = {
    "before": [
        "fresh_full_approval",
        "new_unrevoked_identity",
        "terminated_previous_experiment",
        "explicit_pg_migration_minimum_role",
        "current_read_intersection",
        "all_stage_exact_egress_and_wire_bounds",
        "pool_sidecar_budget_consistency",
        "returned_model_identity_policy",
        "unknown_usage_and_outcome_stop",
        "recovery_and_owned_cleanup_oracles",
    ],
    "between_stages": [
        "independent_source_review",
        "explicit_owner_confirmation",
        "candidate_fingerprint_and_receipt",
        "cold_new_input_and_version_binding",
    ],
    "after": [
        "independent_cold_review",
        "final_usage_and_slot_reconciliation",
        "owned_services_stopped",
        "new_identity_revocation_receipt",
    ],
}
COMPONENTS = [
    "src/sim2act/model.py",
    "src/sim2act/model_budget.py",
    "src/sim2act/protocol_pool.py",
    "src/sim2act/protocol_experiment.py",
    "src/sim2act/protocol_egress.py",
    "src/sim2act/protocol_readiness.py",
    "src/sim2act/conditional_checks.py",
    "src/sim2act/one_shot_preparation.py",
    "requirements.lock",
    "requirements-windows.lock",
    "scripts/WindowsCI.ps1",
    "scripts/Common.ps1",
    "scripts/Setup.ps1",
    "scripts/Doctor.ps1",
    "scripts/Test.ps1",
    "scripts/WindowsBrowserCI.ps1",
    "scripts/windows_browser_ci.py",
    "scripts/windows_ci_smoke.py",
    "scripts/model-protocol-preflight.py",
    "scripts/protocol-store-dryrun.py",
    "scripts/prepare-one-shot-experiment.py",
    ".github/workflows/windows-native-mock.yml",
    "scripts/browser-ci/package.json",
    "scripts/browser-ci/package-lock.json",
    "tests/test_conditional_checks.py",
    "tests/test_one_shot_preparation.py",
]


Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class Receipt(Strict):
    artifact_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    prepared_scope_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


class Intake(Strict):
    # Metadata only. These declarations cannot authenticate approval or enable a send.
    approval_receipt: Receipt | None = None
    identity_fingerprint: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    revoked_identity_fingerprints: list[Hash] = Field(default_factory=list, max_length=16)
    previous_terminated_at: float | None = Field(default=None, strict=True, ge=0)
    approved_at: float | None = Field(default=None, strict=True, ge=0)
    expires_at: float | None = Field(default=None, strict=True, ge=0)
    approved_caps: dict[str, StrictInt] = Field(default_factory=dict)
    receipts: dict[str, Receipt] = Field(default_factory=dict)


def prepare(root):
    root = Path(root).resolve()
    materials = root / "docs/evidence/model-protocol-preparation-20261006/materials"
    raw = (materials / "manifest.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA:
        raise DomainError("VERSION_CONFLICT", "Public preparation manifest changed")
    manifest = json.loads(raw)
    packages = []
    for package in manifest["packages"]:
        if package["package_id"] not in PACKAGES:
            raise DomainError("PERMISSION_DENIED")
        entries = []
        for resource in package["resources"]:
            path = (materials / resource["path"]).resolve()
            try:
                relative = path.relative_to(materials.resolve())
            except ValueError as exc:
                raise DomainError("PERMISSION_DENIED") from exc
            if relative.parts[0] != package["package_id"]:
                raise DomainError(
                    "PERMISSION_DENIED",
                    "Gold/rubric/private files are not public package resources",
                )
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != resource["sha256"]:
                raise DomainError("VERSION_CONFLICT", "Public package bytes changed")
            entries.append(
                {
                    "path": relative.as_posix(),
                    "sha256": resource["sha256"],
                    "bytes": len(data),
                    "lines": len(data.decode("utf-8").splitlines()),
                }
            )
        packages.append(
            {
                "id": package["package_id"],
                "instruction": package["instruction"],
                "resources": entries,
            }
        )
    if {p["id"] for p in packages} != PACKAGES or len(packages) != 4:
        raise DomainError("VERSION_CONFLICT", "Complete two-family source/cold packages required")
    paths = set(COMPONENTS) | {
        p.relative_to(root).as_posix()
        for p in (root / "src").rglob("*")
        if p.is_file()
        and p.suffix in {".py", ".js", ".html", ".css"}
        and "__pycache__" not in p.parts
    }
    components = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in sorted(paths)}
    scope = {
        "schema_version": "one-shot-preparation.v1",
        "public_manifest_sha256": MANIFEST_SHA,
        "public_packages": packages,
        "components": components,
        "proposed_caps_not_approved": copy.deepcopy(CAPS),
        "checklist": copy.deepcopy(CHECKLIST),
        "gold_or_rubric_egress": False,
        "existing_offline_oracles": [
            "scripts/model-protocol-preflight.py",
            "scripts/protocol-store-dryrun.py",
        ],
        "new_checker_scope": "conditional-obligations.synthetic-a.v1 only; not a replacement for protocol source_proof",
        "semantic_acceptance": "UNKNOWN",
        "owner_confirmation": "PENDING",
    }
    return {
        "scope": scope,
        "scope_fingerprint": fingerprint(scope),
        "intake_template": Intake().model_dump(),
        "mode": "PREPARATION_ONLY",
        "live_ready": False,
        "effective_request_budget": 0,
        "network_requests": 0,
        "credentials_created": False,
        "identity_created": False,
    }


def assess(prepared, intake, *, now, root=None):
    canonical = prepare(root or Path(__file__).resolve().parents[2])
    if fingerprint(prepared) != fingerprint(canonical):
        raise DomainError(
            "VERSION_CONFLICT",
            "Preparation does not match current canonical code and public assets",
        )
    if (
        not isinstance(prepared, dict)
        or set(prepared)
        != {
            "scope",
            "scope_fingerprint",
            "intake_template",
            "mode",
            "live_ready",
            "effective_request_budget",
            "network_requests",
            "credentials_created",
            "identity_created",
        }
        or fingerprint(prepared["scope"]) != prepared["scope_fingerprint"]
        or prepared["mode"] != "PREPARATION_ONLY"
        or prepared["live_ready"] is not False
        or prepared["effective_request_budget"] != 0
        or prepared["network_requests"] != 0
        or prepared["credentials_created"] is not False
        or prepared["identity_created"] is not False
    ):
        raise DomainError("VERSION_CONFLICT", "Preparation is not a send authorization")
    value = Intake.model_validate(intake)
    names = set(sum(CHECKLIST.values(), []))
    if set(value.receipts) - names or set(value.approved_caps) - set(CAPS):
        raise DomainError(
            "INVALID_INPUT", "Unknown checklist/cap cannot substitute for required gate"
        )
    if type(now) not in (int, float) or not math.isfinite(now):
        raise DomainError("INVALID_INPUT")
    checks = []

    def check(name, valid):
        checks.append(
            {"id": name, "status": "DECLARED_NOT_AUTHORIZATION" if valid else "MISSING_OR_INVALID"}
        )

    fp = prepared["scope_fingerprint"]
    check(
        "fresh_full_approval",
        bool(
            value.approval_receipt
            and value.approval_receipt.prepared_scope_fingerprint == fp
            and value.previous_terminated_at is not None
            and value.approved_at is not None
            and value.expires_at is not None
            and all(
                math.isfinite(v)
                for v in [value.previous_terminated_at, value.approved_at, value.expires_at]
            )
            and value.previous_terminated_at < value.approved_at <= now < value.expires_at
        ),
    )
    check(
        "new_unrevoked_identity",
        bool(
            value.identity_fingerprint
            and value.revoked_identity_fingerprints
            and value.identity_fingerprint not in value.revoked_identity_fingerprints
        ),
    )
    check(
        "caps_match_prepared_proposal",
        value.approved_caps == CAPS and all(type(v) is int for v in value.approved_caps.values()),
    )
    for name in sorted(names - {"fresh_full_approval", "new_unrevoked_identity"}):
        receipt = value.receipts.get(name)
        check(name, bool(receipt and receipt.prepared_scope_fingerprint == fp))
    return {
        "state": "DECLARATIONS_COMPLETE_FOR_REVIEW"
        if all(c["status"] == "DECLARED_NOT_AUTHORIZATION" for c in checks)
        else "BLOCKED_PENDING_NEW_FULL_APPROVAL_AND_EVIDENCE",
        "checks": checks,
        "live_ready": False,
        "effective_request_budget": 0,
        "network_requests": 0,
        "semantic_acceptance": "UNKNOWN",
        "owner_confirmation": "PENDING",
        "note": "Receipt metadata presence is not signature/authority verification. Before/between/after gates remain separate; no executor exists.",
    }


def measure_wire(body):
    """Measure an already serialized sample; not gold screening or egress authorization."""
    if type(body) is not bytes:
        raise DomainError("INVALID_INPUT", "Exact serialized bytes required")
    try:
        text = body.decode("utf-8")
        value = json.loads(text)
    except (UnicodeDecodeError, ValueError):
        return {"status": "INVALID_UTF8_OR_JSON", "egress_authorized": False}
    # Python JSON permits NaN/Infinity: reject them in a recursive walk by canonical serialization.
    try:
        json.dumps(value, allow_nan=False)
    except ValueError:
        return {"status": "INVALID_UTF8_OR_JSON", "egress_authorized": False}
    valid = (
        type(value) is dict
        and set(value) == {"model", "messages", "tools", "stream", "max_tokens"}
        and value["model"] == "intern-s2"
        and value["stream"] is False
        and type(value["max_tokens"]) is int
        and 1 <= value["max_tokens"] <= CAPS["output_tokens"]
        and type(value["messages"]) is list
        and type(value["tools"]) is list
    )
    bounded = len(text) <= CAPS["wire_characters"] and len(body) <= CAPS["wire_bytes"]
    return {
        "status": "WITHIN_SIZE_AND_ENVELOPE_LIMITS"
        if valid and bounded
        else "OUTSIDE_SIZE_OR_ENVELOPE_LIMITS",
        "characters": len(text),
        "utf8_bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "egress_authorized": False,
        "gold_screened": False,
        "remaining_gate": "exact protocol_egress whitelist, current read receipts, fresh approval and budget required",
    }
