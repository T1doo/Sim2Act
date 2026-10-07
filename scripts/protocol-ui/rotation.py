"""One owned protocol API at a time; independent normally seeded offline test DB."""

import importlib.util
import json
import subprocess
import threading
import time
from pathlib import Path

import httpx

from sim2act.conditional_checks import SOURCE_HASH


def snapshot(root):
    path = Path(__file__).resolve().parents[1] / "conditional-ui/fixture.py"
    spec = importlib.util.spec_from_file_location("rotation_owned_snapshot", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.action(root, "snapshot")


def stop(child):
    if child is not None and child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)


def run_node(command, old_api, old_root, repo, env, timeout=150, stdout=None, stderr=None):
    old_root = Path(old_root)
    fresh = old_root / "fresh"
    old_info = json.loads((old_root / "info.json").read_text(encoding="utf-8"))
    fresh_info = json.loads((fresh / "info.json").read_text(encoding="utf-8"))
    if fresh_info["port"] != old_info["port"] or old_api.poll() is not None:
        raise ValueError("Existing owned same-port protocol API required")
    request, response = old_root / "fresh-request.json", old_root / "fresh-response.json"
    if request.exists() or response.exists():
        raise ValueError("Owned transition must be fresh and single-use")
    node = subprocess.Popen(command, cwd=repo, env=env, stdout=stdout, stderr=stderr)
    replacement = None
    switched = False
    deadline = time.monotonic() + timeout
    expired = threading.Event()

    def expire_node():
        expired.set()
        if node.poll() is None:
            try:
                node.kill()
            except ProcessLookupError:
                pass

    def check_deadline():
        if expired.is_set() or time.monotonic() >= deadline:
            raise subprocess.TimeoutExpired(command, timeout)

    watchdog = threading.Timer(max(0, deadline - time.monotonic()), expire_node)
    watchdog.start()
    try:
        while node.poll() is None:
            check_deadline()
            if request.exists() and not switched:
                if request.stat().st_size > 100:
                    raise ValueError("Closed transition request exceeded bound")
                value = json.loads(request.read_text(encoding="utf-8"))
                if type(value) is not dict or value != {"action": "fresh-protocol-fixture.v1"}:
                    raise ValueError("Closed transition action required")
                before = snapshot(old_root)
                check_deadline()
                baseline = snapshot(fresh)
                check_deadline()
                stop(old_api)
                if old_api.poll() is None:
                    raise RuntimeError("Old owned protocol API not joined")
                check_deadline()
                with (fresh / "api.log").open("wb") as log:
                    replacement = subprocess.Popen(
                        [command[-1], "scripts/protocol-ui/fixture.py", "--root", str(fresh), "--action", "serve"],
                        cwd=repo, env=env, stdout=log, stderr=log,
                    )
                ready_deadline = min(deadline, time.monotonic() + 10)
                while time.monotonic() < ready_deadline:
                    if replacement.poll() is not None:
                        raise RuntimeError("Fresh owned protocol API exited before readiness")
                    try:
                        base = f"http://127.0.0.1:{old_info['port']}"
                        metadata = httpx.get(base + f"/api/projects/{fresh_info['project']}/resources",
                                             headers={"Authorization": "Bearer " + fresh_info["bearer"]}, timeout=0.5)
                        if metadata.status_code == 200 and any(
                            r["id"] == fresh_info["source"] and r.get("hash") == SOURCE_HASH for r in metadata.json()
                        ) and httpx.get(base + "/health", timeout=0.5).status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.02)
                else:
                    raise RuntimeError("Fresh owned protocol API not ready")
                check_deadline()
                response_tmp = response.with_name(response.name + ".tmp")
                response_tmp.write_text(json.dumps({
                    "namespace": "owned-protocol-api-transition.v1", "status": "READY",
                    "same_port": old_info["port"], "old_api_joined": True,
                    "old_api_exit": old_api.returncode, "max_concurrent_protocol_servers": 1,
                    "old_before": before, "fresh_baseline": baseline,
                    "fresh_current_source": {"project": fresh_info["project"], "resource": fresh_info["source"], "hash": SOURCE_HASH},
                    "old_authority_baseline": old_info["initial_counts"],
                    "fresh_authority_baseline": fresh_info["initial_counts"],
                    "separate_authority_baselines": True,
                }), encoding="utf-8")
                check_deadline()
                response_tmp.replace(response)
                switched = True
            time.sleep(0.02)
        check_deadline()
        if node.returncode:
            raise subprocess.CalledProcessError(node.returncode, command)
        if not switched:
            raise RuntimeError("Expected owned protocol transition never requested")
    finally:
        watchdog.cancel()
        watchdog.join()
        cleanup_error = None
        for owned in (node, replacement, old_api):
            try:
                stop(owned)
            except Exception as error:
                if cleanup_error is None:
                    cleanup_error = error
        if cleanup_error is not None:
            raise RuntimeError("Owned protocol transition cleanup failed") from cleanup_error
