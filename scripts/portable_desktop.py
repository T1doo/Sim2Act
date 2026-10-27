"""Bundled Windows preview launcher. Uses only its private interpreter/data.

The server is the unchanged, explicitly synthetic SQLite workspace, not a
production account or database. No installers, network downloads or fallback.
"""

import json
import os
import queue
import re
import signal
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path


def ready_url(line):
    try:
        event = json.loads(line)
    except (ValueError, TypeError):
        return None
    if (type(event) is dict and event.get("event") == "SYNTHETIC_WORKSPACE_READY"
            and event.get("mode") == "SYNTHETIC_TEST_ONLY"
            and type(event.get("url")) is str
            and re.fullmatch(r"http://127\.0\.0\.1:([1-9][0-9]{0,4})", event["url"])):
        if 1 <= int(event["url"].rsplit(":", 1)[1]) <= 65535:
            return event["url"]
    return None


def browser_path():
    # Existing Google Chrome only; never change the default browser or fall back.
    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(variable)
        if base and Path(base).is_absolute():
            candidate = Path(base) / "Google/Chrome/Application/chrome.exe"
            if candidate.is_file():
                return candidate
    raise RuntimeError("Google Chrome was not found in Program Files. Install Chrome separately before starting this preview; no browser was installed or changed.")



def monitor_server(child, open_browser, *, startup_timeout=30, stop_timeout=20, output_timeout=5):
    """Drain the owned stdout pipe while the main thread services console signals.

    Windows console input and a blocking TextIO read must not compete with final
    worker output. The server has its own group; a requested stop sends one
    CTRL_BREAK only to that freshly created, still-held child. Uvicorn handles
    SIGBREAK through its normal shutdown path. No tree kill or PID discovery.
    """
    messages = queue.Queue()
    requested = threading.Event()
    eof = False
    stop_sent = False
    stop_deadline = None
    exit_deadline = None
    eof_deadline = None
    ready_worker = None
    receipt = None
    opened = False
    startup_deadline = time.monotonic() + startup_timeout
    startup_timed_out = False

    def drain():
        try:
            for line in child.stdout:
                messages.put(("line", line))
        except Exception as error:
            messages.put(("error", type(error).__name__))
        finally:
            messages.put(("eof", None))

    def request_stop(signum, frame):
        requested.set()

    def check_startup_deadline():
        nonlocal startup_timed_out
        # One deadline, never renewed by noise, malformed or duplicate READY.
        if (ready_worker is None and not requested.is_set()
                and time.monotonic() >= startup_deadline):
            startup_timed_out = True
            requested.set()
            print("Server startup timed out before a valid READY; requesting normal stop.", flush=True)

    previous = {}
    reader = threading.Thread(target=drain, name="preview-server-output", daemon=True)
    try:
        for name in ("SIGINT", "SIGBREAK"):
            number = getattr(signal, name, None)
            if number is not None:
                previous[number] = signal.signal(number, request_stop)
        reader.start()
        while True:
            check_startup_deadline()
            if requested.is_set() and not stop_sent:
                stop_sent = True
                stop_deadline = time.monotonic() + stop_timeout
                if child.poll() is None:
                    child.send_signal(signal.CTRL_BREAK_EVENT)
                print("Stopping the owned server; waiting for its real worker receipt.", flush=True)
            code = child.poll()
            if code is not None and exit_deadline is None:
                exit_deadline = time.monotonic() + output_timeout
            if code is not None and eof:
                break
            if eof and code is None and eof_deadline is None:
                eof_deadline = time.monotonic() + output_timeout
            if eof_deadline is not None and time.monotonic() >= eof_deadline:
                raise TimeoutError("Owned server stdout closed but process exit is unknown; preserve the running claim.")
            if stop_deadline is not None and time.monotonic() >= stop_deadline:
                raise TimeoutError("Owned server stop was not confirmed; preserve the running claim.")
            if exit_deadline is not None and time.monotonic() >= exit_deadline:
                raise TimeoutError("Owned server output EOF was not confirmed; preserve the running claim.")
            try:
                kind, value = messages.get(timeout=0.1)
            except queue.Empty:
                continue
            if kind == "error":
                raise RuntimeError("Owned server output read failed: " + value)
            if kind == "eof":
                eof = True
                continue
            print(value, end="", flush=True)
            try:
                event = json.loads(value)
            except (TypeError, ValueError):
                continue
            if type(event) is not dict:
                continue
            # get() may span the deadline; a first READY must still be timely.
            check_startup_deadline()
            url = ready_url(value)
            worker = event.get("worker_id")
            if url and type(worker) is str and re.fullmatch(r"worker_[0-9a-f]{32}", worker):
                if ready_worker is not None and worker != ready_worker:
                    raise RuntimeError("Owned server changed its worker identity.")
                ready_worker = worker
                if not opened and not requested.is_set():
                    open_browser(url)
                    opened = True
            if (event.get("event") == "SYNTHETIC_WORKSPACE_STOPPED"
                    and ready_worker is not None and event.get("worker_id") == ready_worker):
                receipt = event
        reader.join(timeout=1)
        if reader.is_alive():
            raise RuntimeError("Owned output reader has not stopped; preserve the running claim.")
        code = child.wait(timeout=1)
        verified = (receipt is not None and receipt.get("worker_stopped") is True
                    and receipt.get("clean") is True and receipt.get("data_preserved") is True)
        print(json.dumps(dict(event="PREVIEW_SERVER_EXIT", child_returncode=code,
                              stop_requested=requested.is_set(), receipt_verified=verified,
                              worker_id=ready_worker, startup_timed_out=startup_timed_out)), flush=True)
        # A zero exit is not a worker-clean receipt. Never synthesize one.
        return code if code != 0 else (0 if verified and not startup_timed_out else 1)
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)

def main():
    if sys.platform != "win32" or sys.version_info[:2] != (3, 12) or struct.calcsize("P") != 8:
        raise RuntimeError("Use Start-Sim2Act.cmd and its bundled Windows x64 runtime.")
    root = Path(__file__).absolute().parent
    if any(path.is_symlink() or path.is_junction() for path in (root, *root.parents)):
        raise RuntimeError("Linked directories are not supported; data was not opened.")
    expected = root / "runtime/python.exe"
    if Path(sys.executable).resolve() != expected.resolve():
        raise RuntimeError("Only the bundled interpreter can start this preview.")
    chrome = browser_path()  # Before database creation; no default browser fallback.
    for name in ("temp", "chrome-profile", "chrome-cache"):
        target = root / name
        if target.is_symlink() or target.is_junction():
            raise RuntimeError("Linked writable directories are not supported.")
        target.mkdir(exist_ok=True)
    environment = {**os.environ, "TEMP": str(root / "temp"), "TMP": str(root / "temp"),
                   "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
                   "PYTHONPATH": "", "SIM2ACT_LIVE_ENABLED": "false"}
    # Exclusive launcher claim; a crash leaves it in place for honest diagnosis.
    lock = root / "preview-running.lock"
    claim = lock.open("x", encoding="ascii")
    child = None
    confirmed_exit = False
    try:
        claim.write(str(os.getpid()))
        claim.flush()
        data = root / "workspace data"
        command = [str(expected), "-I", "-B", "-u", "-m", "sim2act.cli",
                   "synthetic-workspace", "--data-dir", str(data)]
        if not data.exists():
            command.append("--new")
        print("Sim2Act synthetic preview: no model provider or formal publication.", flush=True)
        print("Public synthetic login: public-synthetic-blank-workspace", flush=True)
        print("Keep this window open. Press Ctrl+C once to stop; close the test Chrome window afterwards.", flush=True)
        # The exact child created here owns a distinct console group. Stopping
        # it is explicit and graceful; a browser is not part of that group.
        child = subprocess.Popen(command, cwd=root, env=environment, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                                 creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)

        def open_browser(url):
            subprocess.Popen([str(chrome), "--user-data-dir=" + str(root / "chrome-profile"),
                              "--disk-cache-dir=" + str(root / "chrome-cache"),
                              "--no-first-run", "--no-default-browser-check", url], cwd=root,
                             env=environment)

        code = monitor_server(child, open_browser)
        confirmed_exit = True  # Actual child exit plus output EOF; receipt checked separately.
        return code
    finally:
        claim.close()
        if child is None or confirmed_exit:
            if child is not None and child.stdout is not None:
                child.stdout.close()
            lock.unlink()
        else:
            print("Server exit NOT confirmed; preserve data and running claim. Owned PID: "
                  + str(child.pid), file=sys.stderr, flush=True)


if __name__ == "__main__":
    try:
        result = main()
    except Exception as error:
        print("Preview stopped: " + str(error), file=sys.stderr, flush=True)
        result = 1
    raise SystemExit(result)
