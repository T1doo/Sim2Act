"""One authorized public Windows runner; owned loopback PG, ten PG-compatible record nodes only."""

import base64
import gzip
import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / ".record-pg-ci-evidence"
SELECTED = REPO / "docs/evidence/record-pg-isolation-20261020/existing-record-regression-nodeids.json"
RESTART_NODE = "tests/test_local_record_content_edits.py::test_content_edit_actual_worker_independent_fold_cold_read_and_explicit_revert"
EXCLUDED_NODE = "tests/test_local_record_apps.py::test_referenced_json_read_revoke_blocks_current_recovery_and_commit_before_bodies"
SECRET_VALUES = []


def selected_nodes():
    original = json.loads(SELECTED.read_text(encoding="utf-8"))
    assert len(original) == len(set(original)) == 11 and EXCLUDED_NODE in original
    return [node for node in original if node != EXCLUDED_NODE]


def root():
    if (os.name != "nt" or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("GITHUB_REPOSITORY") != "T1doo/Sim2Act"
            or os.environ.get("GITHUB_RUN_ATTEMPT") != "1"
            or os.environ.get("GITHUB_REF") != "refs/heads/dev/production-trial-stages-20261018"):
        raise ValueError("Actual authorized Windows one-time runner required")
    return Path(os.environ["RUNNER_TEMP"]) / f"sim2act-record-pg-{os.environ['GITHUB_RUN_ID']}-1"


def clean_text(value):
    value = str(value)
    for secret in sorted(SECRET_VALUES, key=len, reverse=True):
        if secret:
            value = value.replace(secret, "[REDACTED]")
    return value


def write(name, value):
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / name).write_text(clean_text(json.dumps(value, ensure_ascii=False, indent=2, default=str)) + "\n", encoding="utf-8")


def save_private(cfg):
    temporary = root() / "private.tmp"
    temporary.write_text(json.dumps(cfg), encoding="utf-8")
    temporary.replace(root() / "private.json")


def config():
    cfg = json.loads((root() / "private.json").read_text(encoding="utf-8"))
    if cfg["sha"] != os.environ["GITHUB_SHA"] or Path(cfg["cluster"]) != root() / "pgdata":
        raise ValueError("Owned cluster provenance changed")
    SECRET_VALUES.extend(cfg[key] for key in ["owner_password", "app_password", "owner_url", "runtime_url"])
    return cfg


def tool(cfg, program, args, *, password=None, timeout=35, ok=(0,)):
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "COMSPEC", "PATHEXT"}
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    env["PGCLIENTENCODING"] = "UTF8"
    if password is not None:
        env["PGPASSWORD"] = password
    result = subprocess.run([str(Path(cfg["pgbin"]) / (program + ".exe")), *args],
        env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if result.returncode not in ok:
        raise RuntimeError(f"{program} exit {result.returncode}: " + clean_text(result.stdout + result.stderr))
    return result


def setup():
    import psycopg
    from psycopg import sql

    owned = root()
    if owned.exists():
        raise ValueError("This run's directory must be fresh; no instance recovery")
    pgbin = Path(os.environ.get("PGBIN", ""))
    if not (pgbin / "initdb.exe").is_file():
        raise ValueError("Runner PostgreSQL binary unavailable; no fallback install")
    owned.mkdir()
    nonce = secrets.token_hex(16)
    owner_pw, app_pw = secrets.token_hex(32), secrets.token_hex(32)
    SECRET_VALUES.extend([owner_pw, app_pw])
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    cfg = dict(sha=os.environ["GITHUB_SHA"], pgbin=str(pgbin), cluster=str(owned / "pgdata"),
        port=port, owner="record_owner_" + nonce, app="record_app_" + nonce,
        database="record_test_" + nonce, owner_password=owner_pw, app_password=app_pw,
        evidence=str(EVIDENCE))
    for kind, role, password in [("owner", cfg["owner"], owner_pw), ("runtime", cfg["app"], app_pw)]:
        cfg[kind + "_url"] = f"postgresql+psycopg://{role}:{password}@127.0.0.1:{port}/{cfg['database']}"
    save_private(cfg)
    SECRET_VALUES.extend([cfg["owner_url"], cfg["runtime_url"]])
    password_file = owned / "initdb-password.txt"
    password_file.write_text(owner_pw, encoding="utf-8")
    try:
        tool(cfg, "initdb", ["-D", cfg["cluster"], "-U", cfg["owner"], "--auth=scram-sha-256",
            "--encoding=UTF8", "--locale=C", "--pwfile=" + str(password_file)])
    finally:
        password_file.unlink(missing_ok=True)
    with (Path(cfg["cluster"]) / "postgresql.conf").open("a", encoding="utf-8") as handle:
        handle.write(f"\nlisten_addresses='127.0.0.1'\nport={port}\nmax_connections=40\nshared_buffers='64MB'\n"
            "log_statement='none'\nlog_min_error_statement='panic'\n")
    tool(cfg, "pg_ctl", ["-D", cfg["cluster"], "-l", str(owned / "postgres.log"), "-w", "-t", "30", "start"])
    tool(cfg, "createdb", ["-h", "127.0.0.1", "-p", str(port), "-U", cfg["owner"], "--no-password", cfg["database"]], password=owner_pw)
    with psycopg.connect(host="127.0.0.1", port=port, user=cfg["owner"], password=owner_pw, dbname=cfg["database"]) as conn:
        conn.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS").format(sql.Identifier(cfg["app"]), sql.Literal(app_pw)))
    with psycopg.connect(host="127.0.0.1", port=port, user=cfg["app"], password=app_pw, dbname=cfg["database"]) as conn:
        version = conn.execute("SELECT version(), current_setting('server_version'), pg_postmaster_start_time(), current_user").fetchone()
        flags = conn.execute("SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user").fetchone()
        public_create = conn.execute("SELECT has_schema_privilege(current_user,'public','CREATE')").fetchone()[0]
        assert not any(flags) and public_create is False
    write("setup.json", dict(sha=cfg["sha"], runner="windows-2025", repository_public=True,
        version=version, app_role_flags=list(flags), app_public_create=public_create,
        loopback="127.0.0.1", port=port, initdb_password_file_deleted=not password_file.exists(),
        original_nodeids=selected_nodes(), excluded_sqlite_only_node=EXCLUDED_NODE))
    print("PASS: owned loopback PostgreSQL initialized; actual version and runtime role recorded")


def restart_oracle(env):
    from fastapi.testclient import TestClient
    from record_test_store import reopen_record_test_store
    from sqlalchemy import text
    from test_local_record_apps import snapshot

    from sim2act.api import create_app

    cfg = config()
    store, settings = env[:2]
    with store.tx() as conn:
        before_server = conn.execute(text("SELECT pg_postmaster_start_time(), pg_backend_pid(), current_user")).one()
        pending = conn.execute(text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND xact_start IS NOT NULL AND pid<>pg_backend_pid()" )).scalar_one()
        assert pending == 0
    before = snapshot(store)
    started = time.monotonic()
    tool(cfg, "pg_ctl", ["-D", cfg["cluster"], "-m", "fast", "-w", "-t", "30", "stop"])
    stopped = tool(cfg, "pg_ctl", ["-D", cfg["cluster"], "status"], ok=(3,))
    tool(cfg, "pg_ctl", ["-D", cfg["cluster"], "-l", str(root() / "postgres.log"), "-w", "-t", "30", "start"])
    # Existing pool must recover as well as an independently created cold pool.
    with store.tx() as conn:
        after_server = conn.execute(text("SELECT pg_postmaster_start_time(), pg_backend_pid(), current_user")).one()
    assert after_server[0] != before_server[0] and after_server[2] == before_server[2] == cfg["app"]
    assert snapshot(store) == before
    cold = reopen_record_test_store(store)
    try:
        assert snapshot(cold) == before
        with TestClient(create_app(cold, settings)) as client:
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            from sqlalchemy import select

            from sim2act.db import internal_instances
            with cold.tx() as conn:
                ids = conn.execute(select(internal_instances.c.id)).scalars().all()
            states = []
            for iid in ids:
                response = client.get("/api/internal/record-instances/" + iid)
                assert response.status_code == 200
                states.append(response.json())
            assert len(states) == 1 and states[0]["data_version"] == 5
            assert [h["event"]["kind"] for h in states[0]["history"]] == ["CREATE", "CREATE", "EDIT_CONTENT", "EDIT_CONTENT", "SET_STATE"]
            assert states[0]["records"][0]["state"] == "DONE" and states[0]["records"][1]["state"] == "OPEN"
        assert snapshot(cold) == before
    finally:
        cold.engine.dispose()
    write("restart.json", dict(status="PASS", before=list(before_server), after=list(after_server),
        stopped_status_exit=stopped.returncode, same_owned_cluster=True, all_table_snapshots_identical=True,
        cold_authorized_record_projection=states, elapsed_seconds=time.monotonic() - started))


def child_test():
    import pytest

    cfg = config()
    sys.path[:0] = [str(REPO / "src"), str(REPO / "tests")]
    nodes = selected_nodes()
    assert len(nodes) == len(set(nodes)) == 10 and RESTART_NODE in nodes
    class Restart:
        count = 0

        @pytest.hookimpl(hookwrapper=True)
        def pytest_runtest_call(self, item):
            outcome = yield
            if item.nodeid == RESTART_NODE and outcome.excinfo is None:
                self.count += 1
                assert self.count == 1
                restart_oracle(item.funcargs["env"])

    plugin = Restart()
    try:
        code = pytest.main([*nodes, "-q", "--tb=short", "--basetemp=" + str(EVIDENCE / "pytest"),
            "--junitxml=" + str(EVIDENCE / "junit.xml")], plugins=[plugin])
    finally:
        # Node may inherit our stdout pipe. Reap only our descendants before
        # exiting so the parent cannot wait forever on an orphaned open pipe.
        import psutil
        children = psutil.Process().children(recursive=True)
        for child in reversed(children):
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs(children, timeout=8)
        assert not alive, "Owned test descendants did not terminate"
        write("test-process-cleanup.json", dict(status="PASS", remaining_descendants=0,
            reaped_descendants=len(children)))
    write("test-summary.json", dict(pytest_exit=int(code), restart_count=plugin.count, expected_nodes=nodes,
        source_sha=cfg["sha"], actual_pg=True, real_models=0, excluded_sqlite_only_node=EXCLUDED_NODE))
    return int(code) if int(code) else (0 if plugin.count == 1 else 1)


def kill_owned_test(cfg):
    if not cfg.get("test_pid"):
        return
    import psutil
    try:
        process = psutil.Process(cfg["test_pid"])
        if abs(process.create_time() - cfg["test_created"]) < 0.01:
            children = process.children(recursive=True)
            for child in reversed(children):
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            try:
                process.kill()
            except psutil.NoSuchProcess:
                pass
            _, alive = psutil.wait_procs([*children, process], timeout=8)
            assert not alive, "Owned test process tree did not terminate"
    except psutil.NoSuchProcess:
        pass


def test():
    import psutil
    cfg = config()
    child_env = dict(os.environ)
    for key in list(child_env):
        if any(word in key.upper() for word in ["TOKEN", "SECRET", "PASSWORD", "DATABASE_URL"]):
            child_env.pop(key)
    child_env["SIM2ACT_RECORD_PG_CONFIG"] = str(root() / "private.json")
    child_env["NODE_PATH"] = str(root() / "node/node_modules")
    process = subprocess.Popen([sys.executable, str(Path(__file__)), "_test"], cwd=REPO,
        env=child_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    cfg.update(test_pid=process.pid, test_created=psutil.Process(process.pid).create_time())
    save_private(cfg)
    try:
        stdout, _ = process.communicate(timeout=300)
    except subprocess.TimeoutExpired:
        kill_owned_test(cfg)
        stdout, _ = process.communicate(timeout=10)
        (EVIDENCE / "pytest.log").write_text(clean_text(stdout), encoding="utf-8")
        raise RuntimeError("Original record selection exceeded the fixed 300-second watchdog") from None
    (EVIDENCE / "pytest.log").write_text(clean_text(stdout), encoding="utf-8")
    print(clean_text(stdout))
    if process.returncode:
        raise RuntimeError("Original record PG selection failed; no retry")


def redact_evidence():
    for path in EVIDENCE.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".xml", ".log", ".stderr"}:
            value = path.read_text(encoding="utf-8", errors="replace")
            path.write_text(clean_text(value), encoding="utf-8")


def cleanup():
    owned = root()
    if not owned.exists():
        write("cleanup.json", dict(status="NO_OWNED_RESOURCE_CREATED", root_absent=True))
        return
    cfg = config()
    kill_owned_test(cfg)
    cluster = Path(cfg["cluster"])
    status = None
    if (cluster / "PG_VERSION").exists():
        current = tool(cfg, "pg_ctl", ["-D", str(cluster), "status"], ok=(0, 3))
        if current.returncode == 0:
            tool(cfg, "pg_ctl", ["-D", str(cluster), "-m", "fast", "-w", "-t", "30", "stop"])
        status = tool(cfg, "pg_ctl", ["-D", str(cluster), "status"], ok=(3,)).returncode
    redact_evidence()
    sanitized_files = {str(p.relative_to(EVIDENCE)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in EVIDENCE.rglob("*") if p.is_file() and p.suffix in {".json", ".xml", ".log", ".stderr"}}
    import shutil
    shutil.rmtree(owned)
    assert not owned.exists()
    write("cleanup.json", dict(status="PASS", post_stop_status_exit=status, owned_cluster_deleted=not cluster.exists(),
        private_config_deleted=not (owned / "private.json").exists(), initdb_password_deleted=not (owned / "initdb-password.txt").exists(),
        owned_root_deleted=True, container_used=False, volume_used=False, redaction_complete=True, sanitized_files=sanitized_files))
    print("PASS: owned PostgreSQL stopped and its entire directory/private files deleted")


def report():
    # Withhold all raw bundles unless cleanup and sanitization were confirmed.
    receipt = EVIDENCE / "cleanup.json"
    if not receipt.is_file():
        raise ValueError("Cleanup missing: raw evidence withheld")
    cleanup_receipt = json.loads(receipt.read_text(encoding="utf-8"))
    if cleanup_receipt.get("status") == "NO_OWNED_RESOURCE_CREATED":
        print("RECORD_PG_RESULT cleanup.json " + json.dumps(cleanup_receipt))
        return
    if cleanup_receipt.get("status") != "PASS" or not cleanup_receipt.get("redaction_complete"):
        raise ValueError("Cleanup/sanitization not confirmed: raw evidence withheld")
    files = [p for p in EVIDENCE.rglob("*") if p.is_file() and p.suffix in {".json", ".xml", ".log", ".stderr"}]
    observed = {str(p.relative_to(EVIDENCE)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in files if p != receipt}
    if observed != cleanup_receipt.get("sanitized_files"):
        raise ValueError("Evidence changed after sanitization: raw evidence withheld")
    # No additional artifact storage; the bounded bundle contains sanitized data.
    total = 0
    manifest = []
    for path in sorted(EVIDENCE.rglob("*")):
        if path.is_file() and path.suffix in {".json", ".xml", ".log", ".stderr"}:
            raw = path.read_bytes()
            packed = gzip.compress(raw, mtime=0)
            total += len(packed)
            if total > 2000000:
                raise ValueError("Evidence exceeds fixed two-megabyte compressed log envelope")
            encoded = base64.b64encode(packed).decode()
            name = str(path.relative_to(EVIDENCE)).replace("\\", "/")
            chunks = [encoded[i:i + 40000] for i in range(0, len(encoded), 40000)]
            manifest.append(dict(path=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), chunks=len(chunks)))
            for index, chunk in enumerate(chunks):
                print("RECORD_PG_FILE " + json.dumps(dict(path=name, index=index, data=chunk)))
    print("RECORD_PG_MANIFEST " + json.dumps(manifest))
    for name in ["setup.json", "test-summary.json", "restart.json", "cleanup.json"]:
        path = EVIDENCE / name
        if path.exists():
            print("RECORD_PG_RESULT " + name + " " + path.read_text(encoding="utf-8"))
    if not (EVIDENCE / "cleanup.json").exists():
        raise ValueError("Owned cleanup result is missing")


if __name__ == "__main__":
    try:
        command = sys.argv[1]
        if command == "_test":
            raise SystemExit(child_test())
        {"setup": setup, "test": test, "cleanup": cleanup, "report": report}[command]()
    except Exception as error:
        print("RECORD_PG_ERROR " + clean_text(type(error).__name__ + ": " + str(error)), file=sys.stderr)
        raise SystemExit(1) from None
