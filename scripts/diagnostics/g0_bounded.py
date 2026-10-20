"""Explicit once-only launcher; --describe is read-only and cannot run a prefix.

Build native dependency separately. Execution additionally requires a grant
matching --describe, a fresh output parent, clean reviewed HEAD, and expires_at.
No current implementation or unit-test command grants execution permission.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import selectors
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path

from g0_guard import DB_FILES, FILES, LIMITS, MIB, Boundary, Budget, Files, same_sqlite_api

REPO = Path(__file__).resolve().parents[2]
SCOPE = "fresh-synthetic-generate3-source2-cold1-first-g0-no-w5-v1"
PARENT_FILES = {"source-manifest.json", "control.jsonl", "output.log", "receipt.json"}


def require_start_qualification():
    # This frozen delivery has only a BLOCKED construction ACK. A future
    # runnable branch requires its own code review and validation; creating an
    # operator grant or changing the interpreter cannot enable this build.
    raise Boundary("BLOCKED_BUILD_ONLY: runnable branch has no start qualification")


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args], text=True).strip()


def describe(library):
    if sys.platform != "linux" or sys.version_info[:2] != (3, 12) or sys.flags.optimize:
        raise Boundary("only reviewed Linux CPython 3.12 without optimization")
    same_sqlite_api()  # Fail before grant consumption, run directory or product import.
    require_start_qualification()
    if git("branch", "--show-current") != "dev/production-trial-stages-20261018" or git(
        "status", "--porcelain"
    ):
        raise Boundary("reviewed clean development branch required")
    import _sqlite3
    import sqlite3

    paths = sorted(
        set(
            p
            for folder in (REPO / "src", REPO / "tests", REPO / "scripts/diagnostics")
            for p in folder.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        )
    )
    dependencies = REPO / ".venv/lib/python3.12/site-packages"
    paths += sorted(
        p for p in dependencies.rglob("*") if p.is_file() and "__pycache__" not in p.parts
    )
    paths += [REPO / "pyproject.toml"]
    paths += [
        Path(getattr(_sqlite3, "__file__", sys.executable)).resolve(strict=True),
        Path(library).resolve(strict=True),
        Path(sys.executable).resolve(strict=True),
    ]
    manifest = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    return dict(
        scope=SCOPE,
        head=git("rev-parse", "HEAD"),
        limits=LIMITS,
        native_library=str(Path(library).resolve(strict=True)),
        source_manifest_sha256=digest,
        sqlite_version=sqlite3.sqlite_version,
        source_manifest=manifest,
    )


def validate_grant(grant, description, now):
    expected = {k: v for k, v in description.items() if k != "source_manifest"}
    if set(grant) != set(expected) | {"expires_at", "grant_id"}:
        raise Boundary("exact grant fields required")
    if any(grant[k] != v for k, v in expected.items()):
        raise Boundary("grant does not match frozen code/dependency/limits")
    identifier = grant["grant_id"]
    if (
        type(identifier) is not str
        or not 8 <= len(identifier) <= 64
        or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in identifier)
    ):
        raise Boundary("invalid once-only grant identifier")
    expiry = grant["expires_at"]
    if type(expiry) not in (int, float) or not now < expiry <= now + 3600:
        raise Boundary("grant expiry must be finite and within one hour")


def proc_identity(pid):
    # /proc comm may contain spaces or ')'; parse after the final ')'.
    raw = Path(f"/proc/{pid}/stat").read_text()
    fields = raw[raw.rfind(")") + 2 :].split()
    return dict(
        pid=pid,
        state=fields[0],
        pgid=int(fields[2]),
        sid=int(fields[3]),
        started=int(fields[19]),
        uid=Path(f"/proc/{pid}").stat().st_uid,
    )


def group_members(pgid):
    members = []
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit():
            try:
                item = proc_identity(int(entry.name))
                if item["pgid"] == pgid:
                    members.append(item)
            except (FileNotFoundError, ProcessLookupError):
                pass
    return members


def signal_owned(pid, identity, sig):
    members = group_members(pid)
    if not members:
        return False
    if (
        identity["pgid"] != pid
        or identity["sid"] != pid
        or any(
            member["sid"] != pid
            or member["uid"] != identity["uid"]
            or member["started"] < identity["started"]
            or (member["pid"] == pid and member["started"] != identity["started"])
            for member in members
        )
    ):
        raise Boundary("owned process identity changed; refuse signal")
    os.killpg(pid, sig)
    return True


def cleanup(process, identity, started, clock=time.monotonic):
    # Both deadlines are fixed once; no fresh grace interval on reentry.
    for sig, until in ((signal.SIGTERM, started + 5), (signal.SIGKILL, started + 10)):
        process.poll()  # Reap the leader, but do not confuse it with the group.
        if not group_members(process.pid):
            return True
        signal_owned(process.pid, identity, sig)
        while clock() < until:
            process.poll()
            if not group_members(process.pid):
                return True
            time.sleep(min(0.02, max(0, until - clock())))
    return not group_members(process.pid)


def owned_group_empty(pgid):
    return not group_members(pgid)


def verify_sources(description):
    manifest = description["source_manifest"]
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    if digest != description["source_manifest_sha256"]:
        raise Boundary("source manifest changed")
    for path, expected in manifest.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise Boundary("frozen source/dependency changed: " + path)
    return digest


def validate_child_parent(root, library, control_fd):
    same_sqlite_api()  # In the specified environment this blocks, with zero IO allocation.
    require_start_qualification()
    if os.getsid(0) != os.getpid() or not stat.S_ISFIFO(os.fstat(control_fd).st_mode):
        raise Boundary("child requires launcher's owned session/control pipe")
    command = Path(f"/proc/{os.getppid()}/cmdline").read_bytes().split(b"\0")
    args = [os.fsdecode(part) for part in command if part]
    if (
        str(Path(__file__).resolve()) not in args
        or "--execute-grant" not in args
        or "--output-parent" not in args
    ):
        raise Boundary("direct child entry prohibited")
    grant_path = Path(args[args.index("--execute-grant") + 1]).resolve(strict=True)
    output_parent = Path(args[args.index("--output-parent") + 1]).resolve(strict=True)
    grant = json.loads(grant_path.read_text())
    root = root.resolve(strict=True)
    if (
        root.parent != output_parent
        or root.name != grant["grant_id"]
        or not grant_path.with_name(grant_path.name + ".consumed").is_file()
    ):
        raise Boundary("child grant/root not consumed by parent")
    if {p.name for p in root.iterdir()} != PARENT_FILES:
        raise Boundary("child requires fresh parent-only output set")
    description = json.loads((root / "source-manifest.json").read_text())
    validate_grant(grant, description, time.time())
    if str(Path(library).resolve(strict=True)) != description["native_library"]:
        raise Boundary("child native dependency identity")
    return description, verify_sources(description)


def child(root, library, control_fd):
    description, before_digest = validate_child_parent(root, library, control_fd)
    import resource

    import g0_guard
    import pytest

    sys.dont_write_bytecode = True
    # Only lower child limits. No mount, role, capability, permission or service.
    soft, hard = resource.getrlimit(resource.RLIMIT_FSIZE)
    ceiling = 12 * MIB
    if soft != resource.RLIM_INFINITY:
        ceiling = min(ceiling, soft)
    if hard != resource.RLIM_INFINITY:
        ceiling = min(ceiling, hard)
    resource.setrlimit(resource.RLIMIT_FSIZE, (ceiling, ceiling))
    files = Files(root, set(FILES) - PARENT_FILES)
    native, api = g0_guard.install_vfs(library, root / "fixture.db")
    control = g0_guard.BoundedWriter(os.fdopen(control_fd, "wb", buffering=0), MIB // 16)
    result = {"classification": "UNKNOWN", "real_models": 0}
    try:
        with pytest.MonkeyPatch.context() as patch:
            g0_guard.install_child_io(patch, files, root / "fixture.db")
            from g0_prefix import run_prefix

            result = run_prefix(root, patch, files, control.json, lambda: not native.g0_fault())
        if native.g0_fault() or native.g0_open_handles():
            raise Boundary("native VFS boundary or unclosed handles")
        result["cleanup"] = "THREADS_CLIENTS_CONNECTIONS_CLOSED"
        result["source_digest_before"] = before_digest
        result["source_digest_after"] = verify_sources(description)
    except BaseException as error:
        # Never serialize credentials, arbitrary repr, traceback locals or rows.
        result = {
            "classification": "UNKNOWN",
            "exception_type": type(error).__name__,
            "error_chain": g0_guard.exception_chain(error),
            "boundary": str(error)[:512] if isinstance(error, Boundary) else "unexpected error",
            "native_fault": native.g0_fault(),
            "native_handles": native.g0_open_handles(),
            "business_acceptance": "INTERRUPTED",
            "real_models": 0,
        }
    try:
        files.writer("diagnostic.json").json({"event": "child_final", **result})
        control.json({"event": "finished", "classification": result["classification"]})
    finally:
        files.close()
        control.stream.close()
    return 0 if result["classification"].startswith("G0_") else 2


def execute(grant_path, output_parent, library):
    description = describe(library)
    grant_path = Path(grant_path).resolve(strict=True)
    if grant_path.stat().st_size > 16384:
        raise Boundary("grant too large")
    grant = json.loads(grant_path.read_text())
    validate_grant(grant, description, time.time())
    # Consume atomically *before* allocating the fresh run; failed setup also
    # consumes this one grant. Never retry using a different root or Run.
    consumed = grant_path.with_name(grant_path.name + ".consumed")
    fd = os.open(consumed, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    root = Path(output_parent).resolve(strict=True) / grant["grant_id"]
    root.mkdir(mode=0o700)
    files = Files(root, PARENT_FILES)
    files.writer("source-manifest.json").json(description)
    read_fd, write_fd = os.pipe()
    environment = {
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "TZ": "UTC",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": os.pathsep.join(
            map(str, (REPO / "scripts/diagnostics", REPO / "tests", REPO / "src"))
        ),
    }
    started = time.monotonic()
    budget = Budget(started)
    process = None
    selector = None
    receipt = {
        "classification": "UNKNOWN",
        "scope": SCOPE,
        "head": description["head"],
        "limits": LIMITS,
    }
    try:
        process = subprocess.Popen(
            [sys.executable, "-B", __file__, "--child", str(root), str(library), str(write_fd)],
            cwd=REPO,
            env=environment,
            pass_fds=(write_fd,),
            start_new_session=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
        )
        os.close(write_fd)
        write_fd = None
        identity = proc_identity(process.pid)
        if identity["pgid"] != process.pid or identity["sid"] != process.pid:
            raise Boundary("dedicated process group required")
        receipt["identity"] = identity
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ, "output")
        selector.register(read_fd, selectors.EVENT_READ, "control")
        pending = b""
        finished = None
        while selector.get_map():
            budget.check()
            for key, _ in selector.select(
                timeout=min(0.05, max(0, budget.deadline - time.monotonic()))
            ):
                chunk = os.read(key.fd, 8192)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                files.writer("output.log" if key.data == "output" else "control.jsonl").write(chunk)
                if key.data == "control":
                    pending += chunk
                    if len(pending) > MIB // 16:
                        raise Boundary("control message bound")
                    while b"\n" in pending:
                        line, pending = pending.split(b"\n", 1)
                        message = json.loads(line)
                        if message.get("event") == "g0_enter" and finished is None:
                            budget.enter_g0(message["at"])
                        elif message.get("event") == "finished" and finished is None:
                            finished = message["classification"]
                        else:
                            raise Boundary("unexpected control event")
        if (
            pending
            or process.wait(timeout=max(0.001, budget.deadline - time.monotonic())) != 0
            or finished not in {"G0_ORIGINAL_REJECTION_NO_W5", "G0_COMPLETED_NO_W5"}
            or budget.g0_at is None
        ):
            raise Boundary("child incomplete or unknown")
        receipt["classification"] = finished
    except BaseException as error:
        receipt.update(
            classification="UNKNOWN",
            error_type=type(error).__name__,
            boundary=str(error)[:512]
            if isinstance(error, Boundary)
            else "unexpected launcher error",
        )
    finally:
        if process is not None:
            identity = receipt.get("identity")
            if identity is None:
                # Popen created the child, but ownership could not be proven.
                receipt["cleanup"] = "UNKNOWN_IDENTITY_REFUSE_SIGNAL"
            else:
                try:
                    clean = cleanup(process, identity, min(time.monotonic(), started + 600))
                    clean = clean and owned_group_empty(process.pid)
                except BaseException as cleanup_error:
                    clean = False
                    receipt["cleanup_error_type"] = type(cleanup_error).__name__
                receipt["cleanup"] = "OWNED_GROUP_EMPTY" if clean else "UNKNOWN_RESIDUAL"
                if not clean:
                    receipt["classification"] = "UNKNOWN"
        else:
            receipt["cleanup"] = "CHILD_NOT_CREATED"
        if selector is not None:
            selector.close()
        if write_fd is not None:
            os.close(write_fd)
        os.close(read_fd)
        if process is not None and process.stdout is not None:
            process.stdout.close()
        evidence = {}
        try:
            receipt["source_digest_after_parent_cleanup"] = verify_sources(description)
        except BaseException as freeze_error:
            receipt.update(classification="UNKNOWN", freeze_error_type=type(freeze_error).__name__)
        for path in root.iterdir():
            info = path.lstat()
            cap = 12 * MIB if path.name in DB_FILES else FILES.get(path.name, -1)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > cap:
                receipt.update(classification="UNKNOWN", evidence="unexpected file/size/type")
                continue
            evidence[path.name] = {
                "bytes": info.st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        # receipt.json was preallocated empty; exclude its self-referential hash.
        evidence.pop("receipt.json", None)
        receipt.update(
            evidence=evidence,
            work_wall_seconds=time.monotonic() - started,
            no_resume=True,
            business_acceptance="INTERRUPTED",
        )
        if receipt["work_wall_seconds"] >= 610:
            receipt.update(classification="UNKNOWN", budget="WORK_PLUS_CLEANUP_EXCEEDED")
        files.writer("receipt.json").json(receipt)
        files.close()
    print(json.dumps({"root": str(root), "classification": receipt["classification"]}))
    return 0 if receipt["classification"].startswith("G0_") else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--describe", metavar="NATIVE_LIBRARY")
    parser.add_argument("--execute-grant")
    parser.add_argument("--output-parent")
    parser.add_argument("--native-library")
    parser.add_argument("--child", nargs=3, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        return child(Path(args.child[0]), args.child[1], int(args.child[2]))
    if args.describe and not args.execute_grant:
        print(json.dumps(describe(args.describe), ensure_ascii=False, indent=2))
        return 0
    if args.execute_grant and args.output_parent and args.native_library and not args.describe:
        return execute(args.execute_grant, args.output_parent, args.native_library)
    parser.error(
        "read-only --describe, or a separately authorized exact --execute-grant is required"
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Boundary as error:
        print(json.dumps({"classification": "BLOCKED", "boundary": str(error)}))
        raise SystemExit(2) from None
