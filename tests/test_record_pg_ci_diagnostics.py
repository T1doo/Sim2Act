"""Local Python process shims only: no Windows/PG emulation or database calls."""

import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Local POSIX executable Python shims")


@pytest.fixture
def harness(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1] / "scripts/record_pg_ci.py"
    spec = importlib.util.spec_from_file_location("record_pg_ci_local", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    owned = tmp_path / "owned"
    owned.mkdir()
    evidence = tmp_path / "evidence"
    monkeypatch.setattr(module, "root", lambda: owned)
    monkeypatch.setattr(module, "EVIDENCE", evidence)
    cluster = owned / "pgdata"
    cluster.mkdir()
    (cluster / "PG_VERSION").write_text("PYTHON_SHIM_NOT_POSTGRESQL")
    binaries = owned / "bin"
    binaries.mkdir()
    (binaries / "python.exe").symlink_to(sys.executable)
    cfg = dict(cluster=str(cluster), pgbin=str(binaries),
        owner_password="0123456789abcdef" * 4, app_password="fedcba9876543210" * 4,
        owner_url="postgresql+psycopg://synthetic:dummy-owner@127.0.0.1:1/synthetic",
        runtime_url="postgresql+psycopg://synthetic:dummy-app@127.0.0.1:1/synthetic")
    monkeypatch.setattr(module, "config", lambda: cfg)
    return module, cfg, owned, evidence


def install_pg_named_python_shim(cfg, *, status_delay=0.02, stop_delay=0.02):
    script = Path(cfg["pgbin"]) / "pg_ctl.exe"
    script.write_text(f"""#!{sys.executable}
import pathlib, sys, time
cluster = pathlib.Path(sys.argv[sys.argv.index('-D') + 1])
operation = sys.argv[-1]
with (cluster / 'shim-operations.txt').open('a') as handle:
    handle.write(operation + '\\n')
if operation == 'stop':
    print('synthetic stop reached', flush=True)
    time.sleep({stop_delay!r})
    (cluster / 'shim-stopped').write_text('yes')
    sys.exit(0)
time.sleep({status_delay!r})
sys.exit(3 if (cluster / 'shim-stopped').exists() else 0)
""")
    script.chmod(0o755)


def test_timeout_saved_outputs_are_sanitized_and_survive_owned_root_deletion(harness, monkeypatch):
    module, cfg, owned, evidence = harness
    (owned / "private.json").write_text("PRIVATE_CONFIG_MUST_NOT_BE_READ")
    (owned / "initdb-password.txt").write_text("PASSWORD_FILE_MUST_NOT_BE_READ")
    (owned / "postgres.log").write_text("startup reached\n" + cfg["owner_password"] + "\n")
    reads = []
    original_open = Path.open

    def observed_open(path, *args, **kwargs):
        if args and "r" in args[0]:
            reads.append(path)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", observed_open)
    code = ("import sys,time; print('saved stdout " + cfg["owner_password"] + "',flush=True); "
        "print('saved stderr " + cfg["runtime_url"] + "',file=sys.stderr,flush=True); "
        "print('" + cfg["app_password"][:8] + "',end='',flush=True); time.sleep(3)")
    with pytest.raises(RuntimeError, match="watchdog"):
        module.tool(cfg, "python", ["-c", code], timeout=0.3)
    failure = (evidence / "tool-failure-diagnostics.json").read_bytes()
    receipt = json.loads(failure)
    assert receipt["reason"] == "tool_timeout"
    combined = "".join(entry["text"] for entry in receipt["logs"])
    assert "saved stdout [REDACTED]" in combined and "saved stderr [REDACTED]" in combined
    assert cfg["app_password"][:8] not in combined
    install_pg_named_python_shim(cfg)
    (Path(cfg["cluster"]) / "shim-stopped").write_text("already stopped")
    module.cleanup()
    assert not owned.exists()
    assert (evidence / "tool-failure-diagnostics.json").read_bytes() == failure
    assert "startup reached" in (evidence / "startup-diagnostics.json").read_text()
    assert not any(path.name in {"private.json", "initdb-password.txt"} for path in reads)
    for path in evidence.iterdir():
        text = path.read_text()
        assert all(secret not in text for secret in cfg.values() if secret in
            [cfg["owner_password"], cfg["app_password"], cfg["owner_url"], cfg["runtime_url"]])
        assert "PRIVATE_CONFIG_MUST_NOT_BE_READ" not in text and "PASSWORD_FILE_MUST_NOT_BE_READ" not in text
    cleanup = json.loads((evidence / "cleanup.json").read_text())
    assert cleanup["status"] == "PASS" and cleanup["post_stop_status_exit"] == 3


def test_diagnostic_bounds_drop_cut_or_unterminated_lines_and_reject_private_links(harness, monkeypatch):
    module, cfg, owned, evidence = harness
    private = owned / "private.json"
    password_file = owned / "initdb-password.txt"
    private.write_text("PRIVATE_CONTENT_MARKER")
    password_file.write_text("PASSWORD_CONTENT_MARKER")
    (owned / "postgres.log").write_text("safe startup line\n" + "X" * 4080 + cfg["owner_password"] + "\n")
    partial = owned / ("tool-" + "1" * 32 + ".stdout")
    partial.write_text("complete line\n" + cfg["app_password"][:8])
    linked = owned / ("tool-" + "2" * 32 + ".stderr")
    linked.symlink_to(private)
    hardlinked = owned / ("tool-" + "3" * 32 + ".stdout")
    os.link(password_file, hardlinked)
    forbidden = owned / "tool-private.stdout"
    forbidden.write_text("FORBIDDEN_NAME_MARKER")
    for index in range(20):
        (owned / (f"tool-{index + 10:032x}.stdout")).write_bytes(b"\x00" * 4096 + b"\n")
    module.capture_diagnostics(cfg, "probe.json", "local_bounds_probe", (partial, linked, hardlinked, forbidden))
    raw = (evidence / "probe.json").read_bytes()
    receipt = json.loads(raw)
    assert len(raw) <= module.DIAGNOSTIC_OUTPUT_BYTES
    assert len(receipt["logs"]) <= module.DIAGNOSTIC_FILES
    assert sum(entry.get("bytes_read", 0) for entry in receipt["logs"]) <= receipt["total_read_limit"]
    by_name = {entry["file"]: entry for entry in receipt["logs"]}
    assert by_name["postgres.log"]["text"] == "safe startup line\n"
    assert by_name["postgres.log"]["truncated"] is True
    assert by_name[partial.name]["text"] == "complete line\n"
    assert by_name[partial.name]["dropped_unterminated_line"] is True
    assert by_name[linked.name]["status"] == by_name[hardlinked.name]["status"] == "UNREADABLE_OR_UNSAFE_LOG"
    assert all(marker not in raw.decode() for marker in ["PRIVATE_CONTENT_MARKER", "PASSWORD_CONTENT_MARKER",
        "FORBIDDEN_NAME_MARKER", cfg["owner_password"][:8], cfg["app_password"][:8]])
    assert module.diagnostic_text("postgres://other:unregistered@127.0.0.1:1/db\n" + cfg["app_password"].upper(), cfg) == (
        "[REDACTED_DATABASE_URL]\n[REDACTED_HEX]")


def test_three_cleanup_process_calls_share_one_deadline(harness, monkeypatch):
    module, cfg, owned, evidence = harness
    install_pg_named_python_shim(cfg)
    monkeypatch.setattr(module, "CLEANUP_COMMAND_SECONDS", 2.8)
    monkeypatch.setattr(module, "CLEANUP_FINAL_STATUS_SECONDS", 0.2)
    observed = []
    original_tool = module.tool

    def tracked_tool(*args, **kwargs):
        observed.append(dict(deadline=kwargs["deadline"], timeout=kwargs["timeout"], args=args[2]))
        return original_tool(*args, **kwargs)

    monkeypatch.setattr(module, "tool", tracked_tool)
    start = time.monotonic()
    module.cleanup()
    assert time.monotonic() - start < 2.8
    assert not owned.exists() and len(observed) == 3
    assert observed[0]["deadline"] == observed[2]["deadline"]
    assert observed[1]["deadline"] == pytest.approx(observed[0]["deadline"] - 0.2)
    stop_args = observed[1]["args"]
    assert 0 < int(stop_args[stop_args.index("-t") + 1]) < observed[1]["timeout"]
    assert observed[1]["timeout"] < 2.8 and all(entry["timeout"] <= 35 for entry in observed)
    receipt = json.loads((evidence / "cleanup.json").read_text())
    assert receipt["shared_command_budget_seconds"] == 2.8 and receipt["post_stop_status_exit"] == 3


def test_slow_stop_cannot_reset_cleanup_budget_or_delete_without_final_status(harness, monkeypatch):
    module, cfg, owned, evidence = harness
    install_pg_named_python_shim(cfg, status_delay=0.15, stop_delay=9)
    monkeypatch.setattr(module, "CLEANUP_COMMAND_SECONDS", 2.8)
    monkeypatch.setattr(module, "CLEANUP_FINAL_STATUS_SECONDS", 0.2)
    start = time.monotonic()
    with pytest.raises(RuntimeError, match="watchdog"):
        module.cleanup()
    assert time.monotonic() - start < 3.3
    assert (Path(cfg["cluster"]) / "shim-operations.txt").read_text().splitlines() == ["status", "stop"]
    assert owned.exists() and not (evidence / "cleanup.json").exists()
    assert (evidence / "startup-diagnostics.json").exists()
    assert "synthetic stop reached" in (evidence / "tool-failure-diagnostics.json").read_text()


def test_expired_shared_deadline_starts_no_final_status_process(harness, monkeypatch):
    module, cfg, owned, evidence = harness
    install_pg_named_python_shim(cfg)
    now = [100.0]
    monkeypatch.setattr(module, "time", SimpleNamespace(monotonic=lambda: now[0]))
    original_tool = module.tool
    calls = []

    def advanced_clock_tool(*args, **kwargs):
        calls.append(args[2][-1])
        result = original_tool(*args, **kwargs)
        now[0] = 101.0 if len(calls) == 1 else 145.0
        return result

    monkeypatch.setattr(module, "tool", advanced_clock_tool)
    with pytest.raises(RuntimeError, match="budget exhausted"):
        module.cleanup()
    assert calls == ["status", "stop"]
    assert owned.exists() and not (evidence / "cleanup.json").exists()
    assert (evidence / "startup-diagnostics.json").exists()


def test_missing_cluster_version_preserves_diagnostics_without_deletion_or_pass(harness, monkeypatch):
    module, cfg, owned, evidence = harness
    (Path(cfg["cluster"]) / "PG_VERSION").unlink()
    (owned / "postgres.log").write_text("synthetic incomplete initialization\n")

    def no_tool_call(*args, **kwargs):
        raise AssertionError("Unverified cluster must start no PG tool")

    monkeypatch.setattr(module, "tool", no_tool_call)
    with pytest.raises(RuntimeError, match="initialization is unverified"):
        module.cleanup()
    assert owned.exists() and not (evidence / "cleanup.json").exists()
    assert "synthetic incomplete initialization" in (evidence / "startup-diagnostics.json").read_text()


def test_operation_budget_clamps_watchdog_and_never_extends_short_connection_time(harness, monkeypatch):
    module, cfg, owned, evidence = harness
    now = [20.0]
    monkeypatch.setattr(module, "time", SimpleNamespace(time=lambda: 1000.0, monotonic=lambda: now[0]))
    monkeypatch.setenv("SIM2ACT_RECORD_OPERATION_UNTIL", "1450")
    deadline = module.operation_deadline()
    assert deadline == 470.0
    assert module.remaining_timeout(deadline, 100, reserve=18) == 100
    now[0] = 450.0
    assert module.remaining_timeout(deadline, 100, reserve=18) == 2
    assert module.connection_timeout(deadline) == 10
    now[0] = 468.1
    with pytest.raises(RuntimeError, match="cannot cover a PG connection"):
        module.connection_timeout(deadline)
    with pytest.raises(RuntimeError, match="budget exhausted"):
        module.remaining_timeout(deadline, 100, reserve=18)


def test_expired_operation_budget_prevents_setup_but_cannot_block_cleanup(harness, monkeypatch):
    module, cfg, owned, evidence = harness
    monkeypatch.setenv("SIM2ACT_RECORD_OPERATION_UNTIL", str(time.time() - 1))
    with monkeypatch.context() as guarded:
        def setup_must_not_reach_owned_root():
            raise AssertionError("Expired setup must create no owned resources")

        guarded.setattr(module, "root", setup_must_not_reach_owned_root)
        with pytest.raises(RuntimeError, match="operation budget expired"):
            module.setup()
    install_pg_named_python_shim(cfg)
    module.cleanup()
    assert not owned.exists()
    assert json.loads((evidence / "cleanup.json").read_text())["status"] == "PASS"
