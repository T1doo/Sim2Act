"""Offline launcher/assembly contracts, not Windows runtime acceptance."""

import importlib.util
import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("value", [
    {}, {"event": "SYNTHETIC_WORKSPACE_READY", "mode": "LIVE", "url": "http://127.0.0.1:9"},
    {"event": "SYNTHETIC_WORKSPACE_READY", "mode": "SYNTHETIC_TEST_ONLY", "url": "http://evil:9"},
    {"event": "SYNTHETIC_WORKSPACE_READY", "mode": "SYNTHETIC_TEST_ONLY", "url": "http://127.0.0.1:65536"},
    {"event": "SYNTHETIC_WORKSPACE_READY", "mode": "SYNTHETIC_TEST_ONLY", "url": "http://127.0.0.1:9/path"},
])
def test_no_browser_for_unconfirmed_or_nonlocal_url(value):
    assert load("portable_desktop").ready_url(json.dumps(value)) is None


def test_ready_exact_loopback():
    module = load("portable_desktop")
    assert module.ready_url("not JSON") is None
    assert module.ready_url(json.dumps(dict(event="SYNTHETIC_WORKSPACE_READY",
           mode="SYNTHETIC_TEST_ONLY", url="http://127.0.0.1:12345"))) == "http://127.0.0.1:12345"


def configured(tmp_path, monkeypatch):
    module = load("portable_desktop")
    monkeypatch.setattr(module.subprocess, "CREATE_NEW_PROCESS_GROUP", 512, raising=False)
    monkeypatch.setattr(module.signal, "CTRL_BREAK_EVENT", 1, raising=False)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    interpreter = runtime / "python.exe"
    interpreter.touch()
    chrome = tmp_path / "chrome.exe"
    chrome.touch()
    monkeypatch.setattr(module, "__file__", str(tmp_path / "desktop.py"))
    monkeypatch.setattr(module.sys, "platform", "win32")
    monkeypatch.setattr(module.sys, "version_info", (3, 12, 10))
    monkeypatch.setattr(module.sys, "executable", str(interpreter))
    monkeypatch.setattr(module, "browser_path", lambda: chrome)
    return module, interpreter, chrome


def test_private_launch_ready_then_browser_and_same_data_reopen(tmp_path, monkeypatch):
    module, interpreter, chrome = configured(tmp_path, monkeypatch)
    commands = []
    event = json.dumps(dict(event="SYNTHETIC_WORKSPACE_READY", mode="SYNTHETIC_TEST_ONLY",
                            url="http://127.0.0.1:12345", worker_id="worker_" + "a" * 32))
    stopped = json.dumps(dict(event="SYNTHETIC_WORKSPACE_STOPPED", worker_id="worker_" + "a" * 32,
                              worker_stopped=True, clean=True, data_preserved=True))

    def popen(command, **kwargs):
        commands.append((command, kwargs))
        return SimpleNamespace(stdout=io.StringIO(event + "\n" + event + "\n" + stopped + "\n"),
                               wait=lambda **kw: 0, poll=lambda: 0, pid=999)

    monkeypatch.setattr(module.subprocess, "Popen", popen)
    assert module.main() == 0
    assert len(commands) == 2  # Duplicate READY cannot open another browser.
    command, options = commands[0]
    assert command[0] == str(interpreter) and command[-1] == "--new"
    assert "shell" not in options
    assert options["creationflags"] == module.subprocess.CREATE_NEW_PROCESS_GROUP
    assert options["env"]["TEMP"] == str(tmp_path / "temp")
    assert commands[1][0] == [str(chrome), "--user-data-dir=" + str(tmp_path / "chrome-profile"),
        "--disk-cache-dir=" + str(tmp_path / "chrome-cache"), "--no-first-run",
        "--no-default-browser-check", "http://127.0.0.1:12345"]
    assert not (tmp_path / "preview-running.lock").exists()
    (tmp_path / "workspace data").mkdir()
    commands.clear()
    assert module.main() == 0
    assert "--new" not in commands[0][0]


def test_failed_child_no_browser_no_retry(tmp_path, monkeypatch):
    module, _, _ = configured(tmp_path, monkeypatch)
    calls = []

    def popen(*args, **kwargs):
        calls.append(args)
        return SimpleNamespace(stdout=io.StringIO("failed before READY\n"),
                               wait=lambda **kw: 1, poll=lambda: 1, pid=999)

    monkeypatch.setattr(module.subprocess, "Popen", popen)
    assert module.main() == 1
    assert len(calls) == 1
    assert not (tmp_path / "preview-running.lock").exists()


def test_running_claim_not_removed_or_reused(tmp_path, monkeypatch):
    module, _, _ = configured(tmp_path, monkeypatch)
    lock = tmp_path / "preview-running.lock"
    lock.write_text("historical unknown", encoding="ascii")
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **kw: pytest.fail("must not launch"))
    with pytest.raises(FileExistsError):
        module.main()
    assert lock.read_text() == "historical unknown"


def test_builder_rejects_hash_and_zip_traversal(tmp_path):
    builder = load("package_windows_portable")
    path = tmp_path / "asset"
    path.write_bytes(b"new")
    with pytest.raises(ValueError, match="Frozen input"):
        builder.read_asset(path, dict(bytes=3, sha256="bad"))
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr("../escape", "bad")
    with pytest.raises(ValueError, match="Unsafe archive"):
        builder.merge_archive({}, data.getvalue(), "runtime/")


def test_original_sqlite_startup_does_not_import_pg(tmp_path, monkeypatch):
    import builtins

    from sim2act.synthetic_workspace import NeverModel, open_workspace, settings_for, workspace_app
    from sim2act.worker import Worker

    original = builtins.__import__

    def no_pg(name, *args, **kwargs):
        if name.split(".")[0] in ("psycopg", "psycopg_binary"):
            pytest.fail("SQLite startup imported a missing PostgreSQL driver")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_pg)
    root, store, marker = open_workspace(tmp_path / "blank", new=True)
    try:
        settings = settings_for(root)
        assert Worker(store, settings, NeverModel()).store is store
        assert workspace_app(store, settings) is not None
        assert marker["mode"] == "SYNTHETIC_TEST_ONLY"
    finally:
        store.engine.dispose()


def test_exact_assembled_archive_all_bytes_and_notices():
    builder = load("package_windows_portable")
    directory = ROOT / "deliverables/windows-afternoon-20261023"
    archive_path = directory / "Sim2Act-preview-win64-7794748c.zip"
    with zipfile.ZipFile(archive_path) as archive:
        prefix = "Sim2Act-preview/"
        manifest = json.loads(archive.read(prefix + "portable-manifest.json"))
        assert manifest["product_commit"] == "7794748c78041682c82f0e7fda239d2601dc91b5"
        assert manifest["installed_runtime_wheels"] == 21
        assert len(archive.namelist()) == len(manifest["files"]) + 1
        for name, record in manifest["files"].items():
            data = archive.read(prefix + name)
            assert len(data) == record["bytes"] and builder.digest(data) == record["sha256"]
        assert archive.read(prefix + "runtime/python312._pth") == b"python312.zip\n.\nLib\\site-packages\nimport site\n"
        names = archive.namelist()
        site = prefix + "runtime/Lib/site-packages/"
        # SQLAlchemy's own PG dialect source remains intact; external drivers
        # and their native libpq payload are deliberately absent.
        assert not any(name.startswith((site + "psycopg/", site + "psycopg_binary/",
                                       site + "psycopg-", site + "psycopg_binary-")) for name in names)
        assert prefix + "runtime/LICENSE.txt" in names
        assert any("certifi-" in name and "LICENSE" in name for name in names)
        assert any("pydantic_core/" in name and name.endswith(".pyd") for name in names)
        assert not any(name.endswith((".db", ".sqlite", ".env")) for name in names)
        assert archive.read(prefix + "desktop.py") == (ROOT / "scripts/portable_desktop.py").read_bytes()

def test_chrome_detection_uses_existing_program_files_only(tmp_path, monkeypatch):
    module = load("portable_desktop")
    standard = tmp_path / "standard"
    x86 = tmp_path / "x86"
    for root in (standard, x86):
        chrome = root / "Google/Chrome/Application/chrome.exe"
        chrome.parent.mkdir(parents=True)
        chrome.touch()
    monkeypatch.setenv("ProgramFiles", str(standard))
    monkeypatch.setenv("ProgramFiles(x86)", str(x86))
    assert module.browser_path() == standard / "Google/Chrome/Application/chrome.exe"


def test_edge_is_never_a_fallback_and_missing_chrome_precedes_data(tmp_path, monkeypatch):
    module, _, _ = configured(tmp_path, monkeypatch)
    program_files = tmp_path / "program-files"
    edge = program_files / "Microsoft/Edge/Application/msedge.exe"
    edge.parent.mkdir(parents=True)
    edge.touch()
    monkeypatch.setenv("ProgramFiles", str(program_files))
    monkeypatch.setenv("ProgramFiles(x86)", str(program_files))
    monkeypatch.setattr(module, "browser_path", load("portable_desktop").browser_path)
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **kw: pytest.fail("must not launch"))
    with pytest.raises(RuntimeError, match="Google Chrome was not found"):
        module.main()
    assert not (tmp_path / "workspace data").exists()
    assert not (tmp_path / "preview-running.lock").exists()

def test_zero_child_exit_without_real_worker_receipt_is_not_clean():
    module = load("portable_desktop")
    child = SimpleNamespace(stdout=io.StringIO("no receipt\n"), poll=lambda: 0, wait=lambda **kw: 0)
    assert module.monitor_server(child, lambda url: pytest.fail("no READY")) == 1


def test_unrelated_worker_receipt_cannot_attest_owned_worker():
    module = load("portable_desktop")
    ready = json.dumps(dict(event="SYNTHETIC_WORKSPACE_READY", mode="SYNTHETIC_TEST_ONLY",
                            url="http://127.0.0.1:12345", worker_id="worker_" + "a" * 32))
    stopped = json.dumps(dict(event="SYNTHETIC_WORKSPACE_STOPPED", worker_id="worker_" + "b" * 32,
                              worker_stopped=True, clean=True, data_preserved=True))
    child = SimpleNamespace(stdout=io.StringIO(ready + "\n" + stopped + "\n"),
                            poll=lambda: 0, wait=lambda **kw: 0)
    assert module.monitor_server(child, lambda url: None) == 1


def test_requested_stop_signals_only_owned_group_once(monkeypatch):
    module = load("portable_desktop")
    monkeypatch.setattr(module.signal, "CTRL_BREAK_EVENT", 1, raising=False)
    callbacks, sent = {}, []
    real_queue = module.queue.Queue

    class RequestQueue:
        def __init__(self):
            self.delegate = real_queue()
            self.requested = False

        def put(self, value):
            self.delegate.put(value)

        def get(self, **kw):
            if not self.requested:
                self.requested = True
                callbacks[module.signal.SIGINT](module.signal.SIGINT, None)
                raise module.queue.Empty
            return self.delegate.get(**kw)

    def capture(number, handler):
        previous = callbacks.get(number)
        callbacks[number] = handler
        return previous

    monkeypatch.setattr(module.signal, "signal", capture)
    monkeypatch.setattr(module.queue, "Queue", RequestQueue)
    child = SimpleNamespace(stdout=io.StringIO(""), poll=lambda: 0 if sent else None,
                            wait=lambda **kw: 0, send_signal=lambda number: sent.append(number))
    assert module.monitor_server(child, lambda url: pytest.fail("no READY")) == 1
    assert sent == [module.signal.CTRL_BREAK_EVENT]

def test_output_eof_with_live_child_preserves_running_claim(tmp_path, monkeypatch):
    module, _, _ = configured(tmp_path, monkeypatch)
    monitor = module.monitor_server
    monkeypatch.setattr(module, "monitor_server", lambda child, browser:
                        monitor(child, browser, output_timeout=0.01))
    child = SimpleNamespace(stdout=io.StringIO(""), poll=lambda: None, pid=999)
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **kw: child)
    with pytest.raises(TimeoutError, match="stdout closed"):
        module.main()
    assert (tmp_path / "preview-running.lock").read_text(encoding="ascii")


def test_output_read_failure_preserves_running_claim(tmp_path, monkeypatch):
    module, _, _ = configured(tmp_path, monkeypatch)

    class BrokenOutput:
        def __iter__(self):
            raise OSError("fixture read failure")

        def close(self):
            pytest.fail("unknown output must not be closed")

    child = SimpleNamespace(stdout=BrokenOutput(), poll=lambda: None, pid=999)
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **kw: child)
    with pytest.raises(RuntimeError, match="output read failed"):
        module.main()
    assert (tmp_path / "preview-running.lock").read_text(encoding="ascii")


def test_missing_output_eof_preserves_running_claim(tmp_path, monkeypatch):
    module, _, _ = configured(tmp_path, monkeypatch)
    release, done = module.threading.Event(), module.threading.Event()

    class HeldOutput:
        def __iter__(self):
            try:
                release.wait(1)
                return iter(())
            finally:
                done.set()

        def close(self):
            pytest.fail("reader still owns the output")

    monitor = module.monitor_server
    monkeypatch.setattr(module, "monitor_server", lambda child, browser:
                        monitor(child, browser, output_timeout=0.01))
    child = SimpleNamespace(stdout=HeldOutput(), poll=lambda: 0, pid=999)
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **kw: child)
    try:
        with pytest.raises(TimeoutError, match="output EOF"):
            module.main()
        assert (tmp_path / "preview-running.lock").read_text(encoding="ascii")
    finally:
        release.set()
        assert done.wait(1)


def test_stop_timeout_preserves_running_claim(tmp_path, monkeypatch):
    module, _, _ = configured(tmp_path, monkeypatch)
    monitor = module.monitor_server
    callbacks, sent = {}, []
    real_queue = module.queue.Queue

    class StopQueue:
        def __init__(self):
            self.delegate = real_queue()
            self.requested = False

        def put(self, value):
            self.delegate.put(value)

        def get(self, **kw):
            if not self.requested:
                self.requested = True
                callbacks[module.signal.SIGINT](module.signal.SIGINT, None)
                raise module.queue.Empty
            return self.delegate.get(**kw)

    def capture(number, handler):
        old = callbacks.get(number)
        callbacks[number] = handler
        return old

    monkeypatch.setattr(module.signal, "signal", capture)
    monkeypatch.setattr(module.queue, "Queue", StopQueue)
    monkeypatch.setattr(module, "monitor_server", lambda child, browser:
                        monitor(child, browser, stop_timeout=0.01))
    child = SimpleNamespace(stdout=io.StringIO(""), poll=lambda: None, pid=999,
                            send_signal=lambda number: sent.append(number))
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **kw: child)
    with pytest.raises(TimeoutError, match="stop was not confirmed"):
        module.main()
    assert sent == [module.signal.CTRL_BREAK_EVENT]
    assert (tmp_path / "preview-running.lock").read_text(encoding="ascii")
