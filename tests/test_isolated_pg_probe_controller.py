"""Controller gates + real TEST_ONLY SQLite HTTP lifecycle; never PG or credentials."""

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
from desktop_service_fixture import TOKEN

from sim2act.desktop_protocol import TEST_ONLY

SCRIPT = Path(__file__).parents[1] / "scripts/diagnostics/isolated_pg_probe.py"
spec = importlib.util.spec_from_file_location("isolated_pg_probe_controller", SCRIPT)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_real_core_client_uses_original_http_and_owned_lifecycle(tmp_path):
    root = tmp_path / "explicit-test-only-sqlite"

    def service():
        return probe.OwnedDesktop(
            [
                sys.executable,
                "-B",
                "-u",
                str(Path(__file__).with_name("desktop_service_fixture.py")),
                "--root",
                str(root),
            ],
            backend=TEST_ONLY,
        )

    result = probe.core_flow(service, TOKEN)
    assert result["status"] == "CORE_MODEL0_PASSED" and result["backend"] == TEST_ONLY
    assert result["actual_model_requests"] == 0 and result["result_sum"] == "30"
    assert result["same_origin"] and result["cancel_final"] and result["read_revoked"]
    assert [p["path"] for p in result["pa_pb_preparations"]] == ["P-A", "P-B"]
    assert not (root / "desktop-service-claim.json").exists()
    (tmp_path / "test-only-core-receipt.json").write_text(json.dumps(result, indent=2) + "\n")


@pytest.mark.parametrize("fault", ["wrong-digest", "missing-platform", "wrong-platform"])
def test_manifest_is_exact_bytes_and_platform_not_mutable_tag(tmp_path, monkeypatch, fault):
    raw = json.dumps(
        dict(
            manifests=[
                dict(platform=dict(os="linux", architecture="amd64"), digest="sha256:" + "a" * 64)
            ]
        )
    ).encode()
    if fault == "missing-platform":
        raw = b'{"manifests":[]}'
    if fault == "wrong-platform":
        raw = raw.replace(b"amd64", b"arm64")
    path = tmp_path / "unit-manifest.json"
    path.write_bytes(raw)
    monkeypatch.setattr(
        probe,
        "DIGEST",
        "sha256:" + hashlib.sha256(raw).hexdigest()
        if fault != "wrong-digest"
        else "sha256:" + "0" * 64,
    )
    with pytest.raises(probe.ProbeError):
        probe.manifest_check(path)


@pytest.mark.parametrize("fault", ["no-manifest", "resource", "confirmation", "dependency"])
def test_execute_preflight_rejects_before_any_effect(monkeypatch, fault):
    monkeypatch.setattr(probe, "checked_source", lambda _: None)
    value = dict(
        dependency_manifest_verified=True,
        preconditions=dict(disk_ready=True, memory_ready=True),
        local_dependencies=dict(
            versions_match=True, native_ready=True, python_import_binding_verified=True
        ),
    )
    if fault == "no-manifest":
        value["dependency_manifest_verified"] = False
    if fault == "resource":
        value["preconditions"]["disk_ready"] = False
    if fault == "dependency":
        value["local_dependencies"]["native_ready"] = False
    monkeypatch.setattr(probe, "plan", lambda *_: value)
    monkeypatch.setattr(probe, "run", lambda *_a, **_k: pytest.fail("no Docker/SQL/CLI command"))
    monkeypatch.setattr(
        probe.secrets, "token_hex", lambda *_: pytest.fail("no nonce or root creation")
    )
    monkeypatch.setattr(probe.secrets, "token_urlsafe", lambda *_: pytest.fail("no credentials"))
    with pytest.raises(probe.ProbeError):
        probe.execute(
            "0" * 40, None, "wrong" if fault == "confirmation" else probe.plan_hash(value)
        )


def test_command_timeout_retains_handle_and_never_kills(monkeypatch):
    class Child:
        pid = 999999999

        def communicate(self, *a, **kw):
            raise subprocess.TimeoutExpired("unit-no-execution", 0.01)

        def kill(self):
            pytest.fail("never kill uncertain mutating command")

        def terminate(self):
            pytest.fail("never terminate uncertain mutating command")

    child = Child()
    monkeypatch.setattr(probe.subprocess, "Popen", lambda *_a, **_k: child)
    monkeypatch.setattr(probe, "INFLIGHT", [])
    monkeypatch.setattr(probe, "DEADLINE", None)
    with pytest.raises(probe.ProbeError, match="COMMAND_INFLIGHT_UNKNOWN"):
        probe.run(["unit-no-execution"])
    assert probe.INFLIGHT[0][0] is child and probe.INFLIGHT[0][1]["pid"] == child.pid


def test_existing_nonce_directory_is_never_adopted_or_overwritten(tmp_path, monkeypatch):
    nonce = "a" * 32
    root = tmp_path / ("sim2act-pg-probe-" + nonce)
    root.mkdir()
    original = root / "public-state.json"
    original.write_bytes(b"UNRELATED_OWNER_STATE\n")
    value = dict(
        dependency_manifest_verified=True,
        preconditions=dict(disk_ready=True, memory_ready=True),
        local_dependencies=dict(
            versions_match=True, native_ready=True, python_import_binding_verified=True
        ),
    )
    monkeypatch.setattr(probe, "BASE", tmp_path)
    monkeypatch.setattr(probe, "checked_source", lambda _: None)
    monkeypatch.setattr(probe, "plan", lambda *_: value)
    monkeypatch.setattr(probe.secrets, "token_hex", lambda _: nonce)
    monkeypatch.setattr(
        probe.secrets, "token_urlsafe", lambda *_: pytest.fail("no credentials on collision")
    )
    monkeypatch.setattr(probe, "run", lambda *_a, **_k: pytest.fail("no Docker on collision"))
    with pytest.raises(probe.ProbeError, match="PROBE_FAILED_PRIVATE_STATE_RETAINED"):
        probe.execute("0" * 40, None, probe.plan_hash(value))
    assert original.read_bytes() == b"UNRELATED_OWNER_STATE\n"
    assert set(p.name for p in root.iterdir()) == {"public-state.json"}


def test_complete_native_group_witness_detects_changed_header(tmp_path, monkeypatch):
    import shutil

    base = probe.ROOT
    (tmp_path / "scripts").mkdir()
    (tmp_path / "src/sim2act").mkdir(parents=True)
    shutil.copyfile(base / "scripts/candidate_wheel.py", tmp_path / "scripts/candidate_wheel.py")
    shutil.copyfile(base / "requirements.lock", tmp_path / "requirements.lock")
    helper_spec = importlib.util.spec_from_file_location(
        "unit_native_groups", base / "scripts/candidate_wheel.py"
    )
    helper = importlib.util.module_from_spec(helper_spec)
    helper_spec.loader.exec_module(helper)
    for name in {n for group in helper.NATIVE_SOURCE_GROUPS.values() for n in group}:
        shutil.copyfile(base / "src/sim2act" / name, tmp_path / "src/sim2act" / name)
    changed = tmp_path / "src/sim2act/_cold_source_view.h"
    changed.write_bytes(changed.read_bytes() + b"\n/* unit altered header */\n")
    monkeypatch.setattr(probe, "ROOT", tmp_path)
    facts = probe.dependencies()
    assert facts["native_source_hash_matches"]["_raw_snapshot"] is True
    assert facts["native_source_hash_matches"]["_cold_typed_cohort"] is True
    assert facts["native_source_hash_matches"]["_cold_source_owned_impl"] is False
    assert facts["native_ready"] is False


@pytest.mark.parametrize(
    "diagnostic,accepted",
    [
        (
            'connection failed: connection to server at "127.0.0.1", port 32123 failed: FATAL:  password authentication failed for user "probe_admin"\n',
            True,
        ),
        (
            'connection to server at "127.0.0.1", port 32123 failed: FATAL:  password authentication failed for user "probe_admin"',
            True,
        ),
        (
            'connection failed: connection to server at "127.0.0.1", port 32123 failed: Connection refused',
            False,
        ),
        ("connection timeout expired", False),
        (
            'connection to server at "127.0.0.1", port 32124 failed: FATAL:  password authentication failed for user "probe_admin"',
            False,
        ),
        (
            'connection to server at "127.0.0.1", port 32123 failed: FATAL:  password authentication failed for user "another_user"',
            False,
        ),
    ],
)
def test_connect_authentication_negative_does_not_accept_network_failure(diagnostic, accepted):
    class Failure(Exception):
        sqlstate = None

    assert probe.password_rejected(Failure(diagnostic), 32123, "probe_admin") is accepted


def test_typed_connection_authentication_sqlstate_is_exact():
    class Authentication(Exception):
        sqlstate = "28P01"

    class Other(Exception):
        sqlstate = "08006"

    assert (
        probe.password_rejected(Authentication("private suppressed"), 32123, "probe_admin") is True
    )
    assert (
        probe.password_rejected(Other("password authentication failed"), 32123, "probe_admin")
        is False
    )
