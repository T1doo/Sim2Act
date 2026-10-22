"""Offline real Git non-cone checkout + isolated ASGI dependency closure.

No browser, network, package installation, Worker, model or new acceptance.
Run parent with existing venv; child uses -I -S and explicit existing dependencies.
"""

import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from html.parser import HTMLParser
from pathlib import Path


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def exact(actual, expected):
    if type(actual) is not type(expected):
        return False
    if type(actual) is dict:
        return actual.keys() == expected.keys() and all(exact(actual[k], expected[k]) for k in actual)
    if type(actual) in (list, tuple):
        return len(actual) == len(expected) and all(exact(a, b) for a, b in zip(actual, expected, strict=True))
    return actual == expected


def git(repo, *args, input=None):
    return subprocess.check_output(["git", "-C", str(repo), *args], input=input, timeout=20)


def build(repo, root, commit):
    root.mkdir()
    tree = root / "tree"
    tree.mkdir()
    workflow = git(repo, "show", commit + ":.github/workflows/windows-native-mock.yml").decode()
    block = workflow.split("          sparse-checkout: |\n", 1)[1]
    patterns = []
    for line in block.splitlines():
        if not line.startswith("            /"):
            break
        patterns.append(line.strip())
    assert len(patterns) == 19 and len(patterns) == len(set(patterns))
    git(tree, "init", "--quiet")
    objects = Path(git(repo, "rev-parse", "--git-path", "objects").decode().strip())
    if not objects.is_absolute():
        objects = repo / objects
    (tree / ".git/objects/info/alternates").write_text(str(objects.resolve()) + "\n")
    git(tree, "sparse-checkout", "set", "--no-cone", "--stdin", input=("\n".join(patterns) + "\n").encode())
    start = time.monotonic()
    git(tree, "-c", "advice.detachedHead=false", "checkout", "--detach", commit)
    seconds = time.monotonic() - start
    selected = [item.decode()[2:] for item in git(tree, "ls-files", "-t", "-z").split(b"\0") if item and not item.startswith(b"S ")]
    all_sizes = {}
    for item in git(repo, "ls-tree", "-r", "-l", "-z", commit).split(b"\0"):
        if item:
            meta, name = item.decode().split("\t", 1)
            all_sizes[name] = int(meta.split()[3])
    manifest = {}
    for name in selected:
        file = tree / name
        assert file.is_file() and not file.is_symlink()
        data = file.read_bytes()
        assert data == git(repo, "show", commit + ":" + name), name
        manifest[name] = hashlib.sha256(data).hexdigest()
    save(root / "checkout.json", dict(commit=commit, patterns=patterns, selected_count=len(selected), selected_blob_bytes=sum(all_sizes[n] for n in selected), full_count=len(all_sizes), full_blob_bytes=sum(all_sizes.values()), local_materialization_seconds=seconds, qualification="local shared-object-store metadata only; no network or Windows timing claim", files=manifest))
    import sysconfig

    deps = sysconfig.get_path("purelib")
    with (root / "probe.log").open("wb") as log:
        child = subprocess.run([sys.executable, "-I", "-S", "-B", str(Path(__file__).resolve()), "child", str(repo), str(root), deps], cwd=tree, stdout=log, stderr=subprocess.STDOUT, timeout=60)
    assert child.returncode == 0, (root / "probe.log").read_text()


def child(repo, root, deps):
    tree, data = root / "tree", root / "data"
    data.mkdir()
    assert not any(n == "sim2act" or n.startswith("sim2act.") for n in sys.modules)
    assert not exact(True, 1) and not exact([1], (1,))
    assert not any("editable" in type(f).__name__.lower() for f in sys.meta_path)
    sys.path[:0] = [str(tree / "src"), str(tree / "scripts"), deps]
    opened, forbidden_calls = set(), []

    def audit(event, args):
        if event == "socket.connect":
            raise AssertionError("No real network permitted in offline closure proof")
        if event in {"open", "sqlite3.connect"} and isinstance(args[0], (str, bytes, os.PathLike)):
            value = os.fsdecode(args[0])
            if value == ":memory:":
                return
            path = Path(value).resolve()
            if path.is_relative_to(repo) and not path.is_relative_to(Path(deps)):
                raise AssertionError("Original repository read forbidden: " + str(path.relative_to(repo)))
            if path.is_relative_to(tree):
                opened.add(str(path.relative_to(tree)))

    sys.addaudithook(audit)
    import protocol_completion_browser_ci as launcher
    import windows_browser_ci as native_audit
    from fastapi.testclient import TestClient
    from sqlalchemy import select

    from sim2act.api import create_app
    from sim2act.config import Settings
    from sim2act.db import Store, fingerprint, meta, protocol_jobs
    from sim2act.model import InternModel
    from sim2act.model_budget import BudgetedProvider
    from sim2act.worker import Worker

    assert launcher.REPO == tree and callable(native_audit.audit_processes)
    original = json.loads((launcher.EVIDENCE / "original.json").read_text())
    db = data / "fixture.sqlite"
    with gzip.open(launcher.EVIDENCE / "before.sqlite.gz", "rb") as src, db.open("wb") as dst:
        shutil.copyfileobj(src, dst)
    side = data / (original["run"] + ".json")
    shutil.copyfile(launcher.EVIDENCE / "original-received-sidecar.json", side)
    side.with_suffix(".lock").write_bytes(b"")
    raw_side = side.read_bytes()
    store = Store("sqlite:///" + str(db), test_only=True)
    settings = Settings(**dict(original["settings"], database_url=str(store.engine.url), data_dir=data))

    def forbidden(*args, **kwargs):
        forbidden_calls.append("send/reserve/accept/Worker")
        raise AssertionError("No new model/Worker/acceptance allowed")

    for owner, name in ((InternModel, "request"), (InternModel, "request_serialized"), (BudgetedProvider, "call"), (BudgetedProvider, "accept_candidate"), (Worker, "reserve"), (Worker, "__init__")):
        setattr(owner, name, forbidden)

    def snapshot():
        with store.engine.connect() as connection:
            return {t.name: sorted(fingerprint(dict(r)) for r in connection.execute(select(t)).mappings()) for t in meta.sorted_tables}

    before = snapshot()
    with store.engine.connect() as connection:
        other = next(r["run_id"] for r in connection.execute(select(protocol_jobs)).mappings() if r["accepted_snapshot"]["phase"] == "extract" and r["run_id"] != original["run"])
    requests = []

    class Assets(HTMLParser):
        def __init__(self):
            super().__init__()
            self.paths = []

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "script" or tag == "link" and attrs.get("rel") == "stylesheet":
                self.paths.append(attrs.get("src") or attrs["href"])

    real_time = time.time
    time.time = lambda: original["resume_at"]
    try:
        with TestClient(create_app(store, settings), headers={"Authorization": "Bearer secret test token"}) as client:
            def request(method, path, body=None, status=200):
                response = client.request(method, path, **({"json": body} if body else {}))
                requests.append(dict(method=method, path=path, status=response.status_code))
                assert response.status_code == status, (path, response.status_code, response.text[:200])
                return response

            html = request("GET", "/")
            assets = Assets()
            assets.feed(html.text)
            for path in assets.paths:
                assert path.startswith("/") and not path.startswith("//")
                request("GET", path)
            pid, rid = original["project"], original["run"]
            for path in ("/health", "/api/projects", "/api/capabilities", f"/api/projects/{pid}/resources", f"/api/projects/{pid}/goal-cards", "/api/apps?metadata_only=true", f"/api/projects/{pid}/protocol/contracts", f"/api/projects/{pid}/runs?metadata_only=true", f"/api/projects/{pid}/grants", f"/api/runs/{rid}", f"/api/projects/{pid}/protocol/runs/{rid}", f"/api/projects/{pid}/protocol/runs/{other}"):
                request("GET", path)
            # A missing fixed asset must fail rather than borrow the original
            # full repository or reuse the prior public catalog response.
            missing = tree / "docs/evidence/protocol-store-loop-20261006/evaluation/b-cold.json"
            hidden = data / "b-cold.original"
            missing.rename(hidden)
            try:
                denied = request("GET", f"/api/projects/{pid}/protocol/contracts", status=400)
                assert denied.json()["error"]["code"] == "RESOURCE_UNAVAILABLE"
            finally:
                hidden.rename(missing)
            request("GET", f"/api/projects/{pid}/protocol/contracts")
            base = f"/api/projects/{pid}/protocol/runs/{rid}"
            receipt = request("POST", base + "/complete-extraction", dict(original["request"], request_key="sparse-closure-only")).json()
            done = request("GET", base).json()
            assert receipt["provider_requests"] == 0 and not receipt["automatic_resend"]
            assert exact(done["result"]["compiled_plan"], original["captured"]["compiled"])
            assert exact(done["result"]["protocol_result"], original["captured"]["result"])
        after = snapshot()
        assert {n for n in before if before[n] != after[n]} == {"runs", "protocol_jobs", "events"}
        assert len(after["events"]) == len(before["events"]) + 4
        assert side.read_bytes() == raw_side and not forbidden_calls
        modules = {n: str(Path(m.__file__).resolve().relative_to(tree)) for n, m in sys.modules.items() if (n == "sim2act" or n.startswith("sim2act.")) and getattr(m, "__file__", None)}
        assert all(v.startswith("src/") for v in modules.values())
        result = dict(status="PASS", scope="Linux offline isolated ASGI, not Windows/Edge/G0", isolation="-I -S -B; explicit existing dependencies; original repo source/data/DB reads and all socket connects refused", requests=requests, opened=sorted(opened), modules=modules, forbidden_calls=forbidden_calls, exact_original_result=True, accounting_tables_unchanged=True, sidecar_unchanged=True, synthetic_clock=original["resume_at"])
    finally:
        time.time = real_time
        store.engine.dispose()
    result["cleanup"] = "ASGI TestClient context exited and Store disposed; child returns normally, not native process cleanup proof"
    save(root / "result.json", result)


if __name__ == "__main__":
    if sys.argv[1] == "build":
        build(Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve(), sys.argv[4])
    elif sys.argv[1] == "child":
        child(Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve(), sys.argv[4])
    else:
        raise SystemExit("Use build or child")
