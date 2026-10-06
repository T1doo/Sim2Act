"""Bounded Windows Server browser fixture; synthetic data, unchanged production routes."""

import argparse
import base64
import ctypes
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import psutil
import uvicorn

from sim2act.api import create_app
from sim2act.apps import create_csv_draft
from sim2act.config import Settings
from sim2act.contracts import Limits
from sim2act.db import Store
from sim2act.process_env import system_environment
from sim2act.worker import Worker


def fixture(root):
    store = Store("sqlite:///" + str(root / "fixture.db"), test_only=True)
    settings = Settings(str(store.engine.url), root, mode="mock")
    return store, settings


def audit_processes(pids):
    """Read-only owned browser process/token queries, no privileges adjusted."""
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    security = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    security.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    security.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    security.IsTokenRestricted.argtypes = [wintypes.HANDLE]
    security.GetSidSubAuthorityCount.argtypes = [ctypes.c_void_p]
    security.GetSidSubAuthorityCount.restype = ctypes.POINTER(ctypes.c_ubyte)
    security.GetSidSubAuthority.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    security.GetSidSubAuthority.restype = ctypes.POINTER(wintypes.DWORD)
    result = []
    for item in pids:
        pid = int(item["id"])
        process = psutil.Process(pid)
        args = process.cmdline()
        assert Path(process.exe()).name.lower() == "msedge.exe", "Unexpected browser process"
        # Actual observed args, not just requested launch option. Values/profile paths not echoed.
        assert not any(arg.split("=", 1)[0] in {
            "--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu-sandbox",
            "--disable-seccomp-filter-sandbox", "--no-zygote",
            "--disable-renderer-sandbox", "--allow-no-sandbox-job",
        } for arg in args), "Sandbox-disabling argument observed"
        handle = kernel.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        token = wintypes.HANDLE()
        try:
            if not security.OpenProcessToken(handle, 0x0008, ctypes.byref(token)):  # TOKEN_QUERY
                raise ctypes.WinError(ctypes.get_last_error())
            needed = wintypes.DWORD()
            app_container = wintypes.DWORD()
            if not security.GetTokenInformation(token, 29, ctypes.byref(app_container), ctypes.sizeof(app_container), ctypes.byref(needed)):
                raise ctypes.WinError(ctypes.get_last_error())
            security.GetTokenInformation(token, 25, None, 0, ctypes.byref(needed))
            buffer = ctypes.create_string_buffer(needed.value)
            if not security.GetTokenInformation(token, 25, buffer, needed, ctypes.byref(needed)):
                raise ctypes.WinError(ctypes.get_last_error())
            sid = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]
            count = security.GetSidSubAuthorityCount(sid)[0]
            integrity = security.GetSidSubAuthority(sid, count - 1)[0]
            restricted = bool(security.IsTokenRestricted(token))
            result.append({"type": item["type"], "pid": pid, "sandbox_disabling_args": [],
                           "app_container": bool(app_container.value), "restricted_token": restricted,
                           "integrity_rid": integrity})
        finally:
            if token:
                kernel.CloseHandle(token)
            kernel.CloseHandle(handle)
    return result


def emit(root):
    # Only explicit named synthetic outputs, not config/profile/DB/env/log dumps.
    for name in ["browser-results.json", "desktop.png", "mobile.png", "failure.png"]:
        path = root / name
        if not path.exists():
            continue
        data = path.read_bytes()
        assert len(data) <= 2_000_000, "Synthetic evidence bound exceeded"
        encoded = base64.b64encode(data).decode()
        print("SIM2ACT_BROWSER_FILE " + json.dumps({"name": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "chunks": (len(encoded) + 3999) // 4000}), flush=True)
        for n, start in enumerate(range(0, len(encoded), 4000)):
            print(f"SIM2ACT_BROWSER_CHUNK {name} {n} {encoded[start:start + 4000]}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--worker-once", action="store_true")
    parser.add_argument("--audit", type=Path)
    args = parser.parse_args()
    if os.name != "nt":
        raise SystemExit("Actual Windows required; no platform substitution")
    root = args.root.resolve()
    if args.audit:
        print(json.dumps(audit_processes(json.loads(args.audit.read_text()))))
        return
    store, settings = fixture(root)
    if args.serve:
        info = json.loads((root / "info.json").read_text())
        uvicorn.run(create_app(store, settings), host="127.0.0.1", port=info["port"], access_log=False)
        return
    if args.worker_once:
        class NoModel:
            def complete(self, *_args, **_kwargs):
                raise AssertionError("Internal browser fixture must never call a model")
        assert Worker(store, settings, NoModel()).once()
        store.engine.dispose()
        return
    assert os.environ.get("GITHUB_ACTIONS") == "true"
    repo = Path(__file__).resolve().parents[1]
    store.initialize()  # Explicit synthetic test fixture migration; no production API DDL.
    limits = Limits(**{key: getattr(settings, key) for key in Limits.model_fields})
    for title, bearer, content in [("SYNTHETIC browser A", "synthetic-browser-A", "amount\n10\n30\n"),
                                   ("SYNTHETIC browser B", "synthetic-browser-B", "amount\n321.99\n")]:
        owner = store.user(title, bearer)
        project = store.project(owner, title)
        resource = store.resource(owner, project, "synthetic.csv", "csv", content)
        create_csv_draft(store, owner, project, title, resource, "synthetic readonly sum", limits)
    store.engine.dispose()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    info = {"port": port, "commit": os.environ["GITHUB_SHA"], "inventory": json.loads((root / "inventory.json").read_text(encoding="utf-8-sig"))}
    (root / "info.json").write_text(json.dumps(info), encoding="utf-8")
    child_env = system_environment()
    child_env.update({key: os.environ[key] for key in ["ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA", "USERPROFILE"] if key in os.environ})
    api = None
    try:
        with (root / "api.log").open("wb") as log:
            api = subprocess.Popen([sys.executable, __file__, "--root", str(root), "--serve"], cwd=repo, env=child_env, stdout=log, stderr=log)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            assert api.poll() is None, "Synthetic API exited before readiness"
            try:
                if httpx.get(f"http://127.0.0.1:{port}/health", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
        else:
            raise RuntimeError("Synthetic API readiness deadline exceeded")
        subprocess.run(["node", "scripts/browser-ci/internal-ui.cjs", str(root), sys.executable], cwd=repo, env=child_env, check=True, timeout=150)
    finally:
        if api is not None and api.poll() is None:
            api.terminate()
            try:
                api.wait(timeout=10)
            except subprocess.TimeoutExpired:
                api.kill()
                api.wait(timeout=5)
        emit(root)


if __name__ == "__main__":
    main()
