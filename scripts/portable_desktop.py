"""Bundled Windows preview launcher. Uses only its private interpreter/data.

The server is the unchanged, explicitly synthetic SQLite workspace, not a
production account or database. No installers, network downloads or fallback.
"""

import json
import os
import re
import struct
import subprocess
import sys
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
    clean = False
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
        # Same console/process group: original Uvicorn receives the real Ctrl+C.
        # Never kill a process tree, inject an API command or reset an old DB.
        child = subprocess.Popen(command, cwd=root, env=environment, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        opened = False
        try:
            for line in child.stdout:
                print(line, end="", flush=True)
                url = ready_url(line)
                if url and not opened:
                    subprocess.Popen([str(chrome), "--user-data-dir=" + str(root / "chrome-profile"),
                                      "--disk-cache-dir=" + str(root / "chrome-cache"),
                                      "--no-first-run", "--no-default-browser-check", url], cwd=root,
                                     env=environment)
                    opened = True
            code = child.wait()
        except KeyboardInterrupt:
            # The child shares this console, so it receives Ctrl+C too.
            code = child.wait(timeout=20)
            for line in child.stdout:
                print(line, end="", flush=True)
        clean = True  # Child termination, not a claim about server/browser cleanup.
        return code
    finally:
        claim.close()
        if child is None or clean or child.poll() is not None:
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
