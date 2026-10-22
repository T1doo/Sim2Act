"""One Windows protected-browser window; reuse sealed facts, never run a Worker.

The first workflow step supplies the absolute 180s deadline, including dependency
setup. Cleanup has one shared further 10s deadline. Only explicitly named,
bounded synthetic results are emitted to the existing job log (no artifacts).
"""

import base64
import gzip
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
def evidence_for(phase):
    if phase not in {"source", "extract"}:
        raise ValueError("Unknown explicit completion phase")
    return REPO / f"docs/evidence/protocol-{phase}-process-recovery-20261022"
REAL_TIME = time.time


def write(root, name, value):
    (root / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def collect(root):
    outputs = {}
    total = 0
    for name in ("launch-contract.json", "inventory.json", "result.json", "browser.json", "initial.png", "unknown.png", "completed.png", "failure.png"):
        file = root / name
        if not file.exists():
            continue
        data = file.read_bytes()
        total += len(data)
        assert len(data) <= 500_000 and total <= 2_000_000, "Evidence log bound exceeded"
        outputs[name] = data
    return outputs


def emit(outputs, phase="extract"):
    prefix = "SIM2ACT_SOURCE_UI" if phase == "source" else "SIM2ACT_EXTRACT_UI"
    for name, data in outputs.items():
        encoded = base64.b64encode(data).decode()
        print(prefix + "_FILE " + json.dumps(dict(name=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), chunks=(len(encoded) + 3999) // 4000)))
        for i, start in enumerate(range(0, len(encoded), 4000)):
            print(f"{prefix}_CHUNK {name} {i} {encoded[start:start + 4000]}")
    sys.stdout.flush()


def launch_paths(root, deadline, phase="extract"):
    evidence = evidence_for(phase)
    """Resolve the entire existing launch toolchain before any installation.

    Scalar executable paths are passed as argv elements, never a shell string.
    Missing/unknown layouts fail together; no alternate SDK or PATH retry.
    """
    errors, paths = [], {}

    def file(label, value):
        if time.monotonic() >= deadline:
            raise TimeoutError("Original work deadline during launch preflight")
        try:
            if value is None or not str(value).strip() or any(c in str(value) for c in "\r\n"):
                raise ValueError("missing or ambiguous path")
            path = Path(value)
            if not path.is_absolute() or not path.is_file():
                raise ValueError("absolute existing file required")
            paths[label] = str(path.resolve(strict=True))
        except (OSError, ValueError) as error:
            errors.append(dict(path=label, error=type(error).__name__, message=str(error)))

    file("python", sys.executable)
    for label, name in (("pwsh", "pwsh.exe"), ("node", "node.exe"), ("npm_cmd", "npm.cmd"), ("git", "git.exe")):
        if time.monotonic() >= deadline:
            raise TimeoutError("Original work deadline during tool resolution")
        file(label, shutil.which(name))
    if "npm_cmd" in paths:
        file("npm_cli", Path(paths["npm_cmd"]).parent / "node_modules/npm/bin/npm-cli.js")
    try:
        expected = Path(os.environ["pythonLocation"]) / "python.exe"
        if "python" not in paths or not os.path.samefile(paths["python"], expected):
            raise ValueError("interpreter differs from selected setup-python file")
    except (OSError, KeyError, ValueError) as error:
        errors.append(dict(path="selected_python", error=type(error).__name__, message=str(error)))
    required = [
        ".gitattributes", ".github/workflows/windows-native-mock.yml", "pyproject.toml", "requirements-windows.lock",
        "scripts/OwnedBrowserSetup.ps1", "scripts/WindowsExtractCompletionUI.ps1",
        "scripts/protocol_completion_browser_ci.py", "scripts/windows_browser_ci.py",
        "scripts/browser-ci/package.json", "scripts/browser-ci/package-lock.json", "scripts/browser-ci/extract-completion.cjs",
        "src/sim2act/__init__.py", "src/sim2act/api.py", "src/sim2act/web/index.html", "src/sim2act/web/app.js", "src/sim2act/web/app.css", "src/sim2act/web/protocol.js",
    ]
    required += [str((evidence / name).relative_to(REPO)) for name in ("original.json", "before.sqlite.gz", "original-received-sidecar.json")]
    required += [f"docs/evidence/protocol-store-loop-20261006/evaluation/{name}.json" for name in ("a-source", "a-cold", "b-source", "b-cold")]
    for name in required:
        file(name, REPO / name)
    write(root, "launch-contract.json", dict(status="FAIL" if errors else "QUALIFIED_FILES_ONLY", paths=paths, errors=errors, cwd=str(REPO), root=str(root), scope="file/layout checks, not Windows handle/sandbox qualification"))
    if errors:
        raise RuntimeError("Launch contract incomplete: " + json.dumps(errors))
    return paths


def join_api_threads(thread, deadline, attempt):
    """Normal loop/thread shutdown within the coordinator's shared remainder."""
    if thread:
        attempt("api_join", lambda: thread.join(max(0, deadline - time.monotonic())))
    for worker in threading.enumerate():
        if worker.name == "AnyIO worker thread":
            attempt("anyio_join", lambda worker=worker: worker.join(max(0, deadline - time.monotonic())))
    return [worker.name for worker in threading.enumerate() if worker.name == "AnyIO worker thread" and worker.is_alive()]


def main():
    assert sys.argv[1:] in ([], ["--source"]), "Unknown phase arguments; no fallback"
    phase = "source" if sys.argv[1:] else "extract"
    evidence = evidence_for(phase)
    assert os.name == "nt" and os.environ.get("GITHUB_ACTIONS") == "true"
    assert os.environ.get("GITHUB_RUN_ATTEMPT") == "1", "No rerun"
    assert os.environ.get("GITHUB_REF") == "refs/heads/dev/production-trial-stages-20261018"
    absolute = int(os.environ["SIM2ACT_UI_UNTIL"]) / 1000
    until = time.monotonic() + (absolute - REAL_TIME())
    root = Path(os.environ["RUNNER_TEMP"]) / (f"sim2act-{phase}-ui-" + os.environ["GITHUB_RUN_ID"] + "-1")
    root.mkdir()  # New window only; never reuse a consumed directory.
    result = dict(status="UNKNOWN", phase=phase, scope="SYNTHETIC SQLite / real Windows Edge DOM; not G0 or production source", limits=dict(work_seconds=180, cleanup_seconds=10, completion_post=3, business_get=30, static_get=40, screenshots=4), model_calls=0, new_worker=0, new_source=0, new_extract=0)
    node = server = thread = store = counts = None
    monitor_stop = threading.Event()
    watcher = None
    forbidden_calls = []
    owned = {}
    owned_lock = threading.Lock()
    setup = []
    cleanup_until = None
    exit_code = 1
    private_files = []

    def remaining():
        value = until - time.monotonic()
        if value <= 0:
            raise TimeoutError("Single absolute 180s work deadline")
        return value

    def command(args, log):
        config = root / (log + ".json")
        executable = args[0]
        assert Path(executable).is_absolute() and Path(executable).is_file()
        write(root, config.name, dict(executable=executable, arguments=args[1:], cwd=str(REPO), until_ms=absolute * 1000, receipt=str(root / (log + ".receipt.json"))))
        with (root / log).open("wb") as output:
            # The original deadline belongs to the supervisor too. The extra
            # two seconds allow its exact-handle tree termination, not work.
            wait = remaining()
            supervisor = subprocess.Popen([paths["pwsh"], "-NoProfile", "-NonInteractive", "-File", paths["scripts/OwnedBrowserSetup.ps1"], "-Config", str(config)], cwd=REPO, stdout=output, stderr=subprocess.STDOUT)
            setup.append(supervisor)
            supervisor.wait(timeout=wait + 2)
            assert supervisor.returncode == 0, "Owned setup failed; no retry"

    try:
        remaining()
        paths = launch_paths(root, until, phase)
        remaining()
        # Existing project lock/SDK/license, official registries, no lifecycle
        # scripts, new SDK, browser installation, Actions cache or artifact.
        site = root / "site"
        command([paths["python"], "-m", "pip", "--isolated", "install", "--target", str(site), "--only-binary=:all:", "--no-input", "--no-cache-dir", "--disable-pip-version-check", "--keyring-provider", "disabled", "--retries", "0", "--timeout", "20", "--index-url", "https://pypi.org/simple", "-r", paths["requirements-windows.lock"]], "pip.log")
        sys.path[:0] = [str(site), str(REPO / "src"), str(REPO / "scripts")]
        command([paths["node"], paths["npm_cli"], "ci", "--prefix", str(REPO / "scripts/browser-ci"), "--ignore-scripts", "--no-audit", "--no-fund", "--registry=https://registry.npmjs.org", "--cache", str(root / "npm-cache"), "--fetch-retries=0", "--fetch-timeout=30000"], "npm.log")
        import psutil
        import uvicorn
        from sqlalchemy import select
        from starlette.responses import JSONResponse

        from sim2act.api import create_app
        from sim2act.config import Settings
        from sim2act.db import Store, fingerprint, meta, protocol_jobs, runs
        from sim2act.model import InternModel
        from sim2act.model_budget import BudgetedProvider
        from sim2act.worker import Worker

        original = json.loads((evidence / "original.json").read_text(encoding="utf-8"))
        db = root / "fixture.sqlite"
        private_files.extend([db, root / "fixture.sqlite-wal", root / "fixture.sqlite-shm", root / "info.json", root / "owned-browser-pids.json"])
        with gzip.open(evidence / "before.sqlite.gz", "rb") as src, db.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        sidecar = root / (original["run"] + ".json")
        private_files.extend([sidecar, sidecar.with_suffix(".lock")])
        shutil.copyfile(evidence / "original-received-sidecar.json", sidecar)
        sidecar.with_suffix(".lock").write_bytes(b"")
        side_bytes = sidecar.read_bytes()
        store = Store("sqlite:///" + str(db), test_only=True)  # No initialize/migrate.
        settings = Settings(**dict(original["settings"], database_url=str(store.engine.url), data_dir=root))
        assert settings.mode == "mock" and not settings.live_enabled and not settings.token

        def snapshot():
            with store.engine.connect() as c:
                return {t.name: sorted(fingerprint(dict(r)) for r in c.execute(select(t)).mappings()) for t in meta.sorted_tables}

        before = snapshot()
        with store.engine.connect() as c:
            all_jobs = list(c.execute(select(protocol_jobs)).mappings())
            before_run = dict(c.execute(select(runs).where(runs.c.id == original["run"])).mappings().one())
        if phase == "source":
            assert len(all_jobs) == 1 and all_jobs[0]["run_id"] == original["run"]
            assert all_jobs[0]["accepted_snapshot"]["phase"] == "source"
            others = []  # Source does not manufacture another Run for navigation.
        else:
            others = [r["run_id"] for r in all_jobs if r["accepted_snapshot"]["phase"] == "extract" and r["run_id"] != original["run"]]
            assert len(others) == 1

        def forbidden(*args, **kwargs):
            forbidden_calls.append("send/reserve/accept")
            raise AssertionError("Forbidden new model/Worker action")

        for owner, name in ((InternModel, "request"), (InternModel, "request_serialized"), (BudgetedProvider, "call"), (BudgetedProvider, "preflight"), (BudgetedProvider, "accept_candidate"), (Worker, "reserve"), (Worker, "__init__"), (Store, "claim")):
            setattr(owner, name, forbidden)
        # Explicit test business clock only. All operation/cleanup limits use
        # saved real wall clock or monotonic; product clock code is unchanged.
        time.time = lambda: original["resume_at"]
        app = create_app(store, settings)
        counts = dict(completion_post=0, business_get=0, static_get=0, blocked=0)
        counter_lock = threading.Lock()
        completion_path = f'/api/projects/{original["project"]}/protocol/runs/{original["run"]}/complete-{phase if phase == "source" else "extraction"}'

        @app.middleware("http")
        async def bounded_http(request, call_next):
            route = request.url.path
            with counter_lock:
                if request.method == "GET":
                    kind = "business_get" if route.startswith("/api/") or route == "/health" else "static_get"
                    counts[kind] += 1
                    allowed = counts[kind] <= (30 if kind == "business_get" else 40)
                elif request.method == "POST" and route == completion_path:
                    counts["completion_post"] += 1
                    allowed = counts["completion_post"] <= 3
                else:
                    allowed = False
                if time.monotonic() >= until or not allowed:
                    counts["blocked"] += 1
                    return JSONResponse({"error": {"code": "TEST_WINDOW_STOP"}}, status_code=409)
            return await call_next(request)

        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        ready = time.monotonic() + min(10, remaining())
        while not server.started:
            assert thread.is_alive() and time.monotonic() < ready, "API did not start"
            time.sleep(0.01)
        commit = subprocess.check_output([paths["git"], "rev-parse", "HEAD"], cwd=REPO, timeout=remaining(), text=True).strip()
        hashes = {name: hashlib.sha256((REPO / name).read_bytes()).hexdigest() for name in ("src/sim2act/web/app.js", "src/sim2act/web/app.css", "src/sim2act/web/protocol.js", "src/sim2act/web/index.html", "scripts/protocol_completion_browser_ci.py", "scripts/browser-ci/extract-completion.cjs", "scripts/browser-ci/package-lock.json", "scripts/OwnedBrowserSetup.ps1", "scripts/WindowsExtractCompletionUI.ps1", ".github/workflows/windows-native-mock.yml")}
        write(root, "inventory.json", dict(commit=commit, source_sha256=hashes, synthetic_clock=original["resume_at"], browser_install=False, added_sdk=False))
        info = dict(phase=phase, base=f"http://127.0.0.1:{port}", project=original["project"], run=original["run"], captured=original["captured"], until_ms=absolute * 1000,
                    expected_version=before_run["version"], expected_fence=before_run["fence"])
        if phase == "extract":
            info["other"] = others[0]
        write(root, "info.json", info)
        env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(site), str(REPO / "src")]))
        output = (root / "driver.log").open("wb")
        node = subprocess.Popen([paths["node"], paths["scripts/browser-ci/extract-completion.cjs"], str(root), paths["python"]], cwd=REPO, env=env, stdout=output, stderr=subprocess.STDOUT)
        node_process = psutil.Process(node.pid)
        node_process.create_time()  # Bind this process identity once, not by later PID lookup.

        def monitor():
            while not monitor_stop.wait(0.1):
                if node.poll() is not None:
                    break
                try:
                    for child in node_process.children(recursive=True):
                        try:
                            created = child.create_time()
                        except psutil.NoSuchProcess:
                            continue  # A short-lived child cannot stop the root watcher.
                        with owned_lock:
                            owned[(child.pid, created)] = child
                except psutil.NoSuchProcess:
                    if node.poll() is None:
                        result["monitor_error"] = "NODE_IDENTITY_DISAPPEARED_WHILE_HANDLE_LIVE"
                        (root / "stop").touch()
                    break
                except BaseException as error:
                    result["monitor_error"] = type(error).__name__
                    (root / "stop").touch()
                    break
                if time.monotonic() >= until:
                    (root / "stop").touch()
                    server.should_exit = True

        watcher = threading.Thread(target=monitor, daemon=True)
        watcher.start()
        try:
            node.wait(timeout=remaining())
        finally:
            output.close()
        assert node.returncode == 0, "Native DOM driver failed; no rerun"
        browser = json.loads((root / "browser.json").read_text(encoding="utf-8"))
        assert browser["status"] == "PASS" and browser["screenshots"] <= 4
        assert counts["blocked"] == 0 and not forbidden_calls and "monitor_error" not in result
        after = snapshot()
        assert {name for name in before if before[name] != after[name]} == {"runs", "protocol_jobs", "events"}
        assert set(before["events"]).issubset(after["events"]) and len(after["events"]) == len(before["events"]) + 4
        with store.engine.connect() as c:
            run = dict(c.execute(select(runs).where(runs.c.id == original["run"])).mappings().one())
            job = dict(c.execute(select(protocol_jobs).where(protocol_jobs.c.run_id == original["run"])).mappings().one())
        assert fingerprint(job["result_snapshot"]["protocol_result"]) == fingerprint(original["captured"]["result"])
        if phase == "source":
            assert run["status"] == "WAITING_APPROVAL"
            assert job["result_snapshot"]["protocol_result"]["semantic_status"] == "UNKNOWN"
            assert "compiled_plan" not in job["result_snapshot"]
            assert len(browser["commandBodies"]) == 2
            assert fingerprint(browser["commandBodies"][0]) == fingerprint(browser["commandBodies"][1])
            from sim2act.db import events
            from sim2act.protocol_source_completion import COMPLETED
            with store.engine.connect() as c:
                receipt_event = c.execute(select(events.c.data).where(events.c.run_id == original["run"], events.c.kind == COMPLETED)).scalar_one()
            # The real page chooses its key. Never replace crypto/controller or
            # copy the process probe's separately chosen completion key.
            assert fingerprint(receipt_event["request"]) == fingerprint(browser["commandBodies"][0])
            assert fingerprint(receipt_event["response"]) == fingerprint(browser["receipts"][0])
            assert browser["receipts"][0]["result_fingerprint"] == job["result_fingerprint"]
        else:
            assert fingerprint(job["result_snapshot"]["compiled_plan"]) == fingerprint(original["captured"]["compiled"])
        assert run["created_at"] == before_run["created_at"] and run["context"] == before_run["context"]
        assert sidecar.read_bytes() == side_bytes
        result.update(status="PASS", accounting_tables_unchanged=True, exact_original_result=True, exact_receipts=browser["receipts"], original_deadlines_unchanged=True, server_counts=counts, business_clock="explicit synthetic / not G0", forbidden_calls=forbidden_calls)
        remaining()
        exit_code = 0
    except BaseException:
        result.update(status="FAIL", error=traceback.format_exc(limit=8))
        # Retain bounded original failure diagnostics in log; never config/env.
        for name in ("pip.log", "npm.log", "driver.log"):
            file = root / name
            if file.exists():
                print(name + " (last 6000 bytes):\n" + file.read_bytes()[-6000:].decode("utf-8", "replace"))
    finally:
        cleanup_until = min(time.monotonic() + 10, until + 10)
        cleanup_errors = []

        def attempt(label, fn):
            try:
                return fn()
            except BaseException as error:
                cleanup_errors.append(dict(step=label, error=type(error).__name__, message=str(error)))
                result["status"] = "UNKNOWN"
                return None

        shared = root / "cleanup-until.json"
        if shared.exists():
            prior = attempt("shared_cleanup_deadline", lambda: json.loads(shared.read_text()))
            if prior is not None:
                cleanup_until = min(cleanup_until, time.monotonic() + max(0, prior - REAL_TIME()))
        result["coordinator_cleanup_seconds_at_entry"] = max(0, cleanup_until - time.monotonic())
        attempt("request_stop", lambda: (root / "stop").touch())
        if server:
            server.should_exit = True
        # The outer exact-handle supervisor has the same deadline and covers a
        # catastrophic Python failure. Normal cleanup confirms each owned item.
        if node and node.poll() is None:
            try:
                node.wait(timeout=max(0.01, cleanup_until - time.monotonic() - 3))
            except subprocess.TimeoutExpired:
                result["status"] = "UNKNOWN"
            except BaseException as error:
                cleanup_errors.append(dict(step="node_grace", error=type(error).__name__))
                result["status"] = "UNKNOWN"
        monitor_stop.set()
        if watcher:
            attempt("monitor_join", lambda: watcher.join(max(0, cleanup_until - time.monotonic())))
            if watcher.is_alive():
                cleanup_errors.append(dict(step="monitor_join", error="STILL_RUNNING"))
                result["status"] = "UNKNOWN"
        with owned_lock:
            registered = list(owned.items())
        # Forced cleanup is not success. psutil.Process retains create_time and
        # refuses PID reuse. A denied terminate is not retried another way.
        for (pid, _created), process in registered:
            alive = attempt(f"owned_{pid}_status", process.is_running)
            if alive:
                result["status"] = "UNKNOWN"
                attempt(f"owned_{pid}_terminate", process.terminate)
        if node and node.poll() is None:
            attempt("node_terminate", node.terminate)
            attempt("node_wait", lambda: node.wait(timeout=max(0.01, cleanup_until - time.monotonic())))
        for installer in setup:
            if installer.poll() is None:
                attempt("installer_supervisor_wait", lambda installer=installer: installer.wait(timeout=max(0.01, cleanup_until - time.monotonic())))
        anyio_alive = join_api_threads(thread, cleanup_until, attempt)
        time.time = REAL_TIME
        alive = [pid for (pid, _), process in registered if attempt(f"owned_{pid}_final", process.is_running)]
        installers_alive = [p.pid for p in setup if p.poll() is None]
        receipts = []
        for name in ("pip.log.receipt.json", "npm.log.receipt.json"):
            if (root / name).exists():
                receipt = attempt(name, lambda name=name: json.loads((root / name).read_text(encoding="utf-8-sig")))
                receipts.append(receipt)
                if receipt and (receipt["timed_out"] or receipt["forced_tree_stop"]):
                    result["status"] = "UNKNOWN"
        result["cleanup"] = dict(api_stopped=not thread or not thread.is_alive(), anyio_alive=anyio_alive, node_exit=None if node is None else node.poll(), owned_browser_descendants_alive=alive, installer_supervisors_alive=installers_alive, errors=cleanup_errors)
        result["setup_receipts"] = receipts
        if counts is not None:
            with counter_lock:
                result["server_counts"] = dict(counts)
        result["forbidden_attempts"] = forbidden_calls
        if alive or anyio_alive or installers_alive or thread and thread.is_alive() or time.monotonic() > cleanup_until:
            result["status"] = "UNKNOWN"
        if store and (not thread or not thread.is_alive()):
            attempt("store_dispose", store.engine.dispose)
        attempt("write_result", lambda: write(root, "result.json", result))
        outputs = attempt("collect_evidence", lambda: collect(root)) or {}
        # No deletion while process/thread termination is unconfirmed. Bounded
        # failure evidence remains in the ephemeral job directory and job log.
        if result["status"] == "PASS":
            for file in private_files:
                attempt("delete_owned_" + file.name, lambda file=file: file.unlink(missing_ok=True))
            result["cleanup"]["fixture_deleted"] = all(not file.exists() for file in private_files)
        else:
            result["cleanup"]["fixture_deleted"] = False
        result["cleanup"]["within_deadline"] = time.monotonic() <= cleanup_until
        if not result["cleanup"]["within_deadline"]:
            result["status"] = "UNKNOWN"
        outputs["result.json"] = json.dumps(result, ensure_ascii=False, indent=2).encode()
        attempt("write_final_result", lambda: write(root, "result.json", result))
        attempt("emit_evidence", lambda: emit(outputs, phase))
    return exit_code if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
