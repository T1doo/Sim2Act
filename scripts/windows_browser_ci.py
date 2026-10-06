"""Bounded Windows Server browser fixture; synthetic data, unchanged production routes."""

import argparse
import base64
import copy
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
from sqlalchemy import select, update

from sim2act import lifecycle
from sim2act.api import create_app
from sim2act.apps import create_csv_draft
from sim2act.config import Settings
from sim2act.contracts import Limits
from sim2act.db import Store, fingerprint, internal_approvals
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
        if item["type"] == "browser":
            assert not any(arg.startswith("--disable-features=") or arg in {
                "--enable-unsafe-swiftshader", "--unsafely-disable-devtools-self-xss-warnings",
                "--disable-ipc-flooding-protection", "--disable-client-side-phishing-detection",
                "--password-store=basic", "--use-mock-keychain",
            } for arg in args), "SDK browser protection weakening observed"
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
                           "integrity_rid": integrity, "security_args_verified": True,
                           "command_switches": [arg.split("=", 1)[0] for arg in args if arg.startswith("--")]})
        finally:
            if token:
                kernel.CloseHandle(token)
            kernel.CloseHandle(handle)
    return result


def emit(root):
    # Only explicit named synthetic outputs, not config/profile/DB/env/log dumps.
    for name in ["browser-results.json", "desktop.png", "mobile.png", "failure.png",
                 "agent-results.json", "agent-desktop.png", "agent-narrow.png", "agent-failure.png"]:
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
    parser.add_argument("--incompatible-release", type=str)
    parser.add_argument("--next-short-switch-ttl", action="store_true")
    args = parser.parse_args()
    if os.name != "nt":
        raise SystemExit("Actual Windows required; no platform substitution")
    root = args.root.resolve()
    if args.audit:
        print(json.dumps(audit_processes(json.loads(args.audit.read_text()))))
        return
    store, settings = fixture(root)
    info_path = root / "info.json"
    if args.next_short_switch_ttl or args.incompatible_release:
        assert info_path.exists() and store.test_only
        if args.next_short_switch_ttl:
            (root / "short-switch-ttl.json").write_text('{"fixture_only":true}')
            return
        limits = Limits(**{key: getattr(settings, key) for key in Limits.model_fields})
        user = store.authenticate("synthetic-browser-A")
        with store.tx() as c:
            release = lifecycle.read_release(store, c, user, args.incompatible_release, limits)
        schema = copy.deepcopy(release["snapshot"]["data_schema"])
        schema["properties"]["release_ref"] = {"type": "string"}
        schema["required"].append("release_ref")
        draft = release["snapshot"]["draft"]
        a = lifecycle.prepare_release(store, user, draft["id"], draft["fingerprint"], limits,
                                      {"column": "amount"}, data_schema=schema, data_schema_version=2)
        bad = lifecycle.commit_release(store, user, a["id"], a["fingerprint"], limits)
        print(json.dumps({"id": bad["id"], "fingerprint": bad["fingerprint"]}))
        return
    if args.serve:
        original = lifecycle.new_approval
        def fixture_approval(c, user, pid, kind, payload):
            receipt = original(c, user, pid, kind, payload)
            marker = root / "short-switch-ttl.json"
            if kind == "switch" and marker.exists():
                # One owned synthetic approval gets a narrowed TTL before its first receipt.
                # Production lifetime/clock/CSP/routes remain unchanged.
                assert store.test_only and json.loads(marker.read_text())["fixture_only"] is True
                marker.unlink()
                row = c.execute(select(internal_approvals).where(internal_approvals.c.id == receipt["id"])).mappings().one()
                p = dict(row["payload"])
                p["expires_at"] = time.time()+3
                fp = fingerprint(p)
                c.execute(update(internal_approvals).where(internal_approvals.c.id == receipt["id"]).values(payload=p, expires_at=p["expires_at"], fingerprint=fp))
                receipt["fingerprint"] = fp
            return receipt
        lifecycle.new_approval = fixture_approval
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
    agent_api = None
    agent_root = root / "agent"
    agent_root.mkdir()
    (root / "agent-results.json").write_text(json.dumps({
        "status": "NOT_RUN", "checks": [], "screenshots": [], "visualReview": "NOT_REVIEWED",
        "modelRequests": 0, "legacyChecksCounted": 0,
    }), encoding="utf-8")
    try:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            agent_port = sock.getsockname()[1]
        subprocess.run([sys.executable, "scripts/agent-ui/fixture.py", "--root", str(agent_root),
                        "--port", str(agent_port), "--action", "seed"], cwd=repo,
                       env={**child_env, "PYTHONPATH": "src"}, check=True, timeout=30)
        with (root / "api.log").open("wb") as log:
            api = subprocess.Popen([sys.executable, __file__, "--root", str(root), "--serve"], cwd=repo, env=child_env, stdout=log, stderr=log)
        with (agent_root / "api.log").open("wb") as log:
            agent_api = subprocess.Popen([sys.executable, "scripts/agent-ui/fixture.py", "--root",
                                          str(agent_root), "--action", "serve"], cwd=repo,
                                         env={**child_env, "PYTHONPATH": "src"}, stdout=log, stderr=log)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            assert api.poll() is None and agent_api.poll() is None, "Synthetic API exited before readiness"
            try:
                if all(httpx.get(f"http://127.0.0.1:{p}/health", timeout=1).status_code == 200
                       for p in (port, agent_port)):
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
        else:
            raise RuntimeError("Synthetic API readiness deadline exceeded")
        subprocess.run(["node", "scripts/browser-ci/internal-ui.cjs", str(root), sys.executable], cwd=repo, env=child_env, check=True, timeout=150)
    finally:
        cleanup_error = None
        try:
            for owned in (agent_api, api):
                try:
                    if owned is not None and owned.poll() is None:
                        owned.terminate()
                        try:
                            owned.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            owned.kill()
                            owned.wait(timeout=5)
                except Exception as error:
                    # Attempt every owned child's cleanup even if one fails.
                    if cleanup_error is None:
                        cleanup_error = error
        finally:
            emit(root)
        if cleanup_error is not None:
            raise cleanup_error


if __name__ == "__main__":
    main()
