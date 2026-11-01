"""Explicit isolated PG CORE_MODEL0 controller. Default plan is read-only.

Execution is separately confirmed, never run by tests/preflight. This is a probe,
not an alternative product or permission to provision anything. No live phase is
implemented here; its missing stage automation is reported, never mocked as PG.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import os
import queue
import re
import secrets
import shutil
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
from sqlalchemy.engine import URL

from sim2act.desktop_protocol import CONFIGURED, PROTOCOL, ordinary, parse
from sim2act.process_env import system_environment

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = Path(__file__).resolve()
BASE = Path("/workspace/scratch")
DIGEST = "sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3"
IMAGE = "postgres@" + DIGEST
DOCKER = ["docker", "--host=unix:///var/run/docker.sock"]
CORE_SECONDS = 660
CLEANUP_SECONDS = 90
DEADLINE = None
INFLIGHT = []


class ProbeError(RuntimeError):
    """Constant public failure codes only; never raw driver/command exceptions."""


def require(condition, code):
    if not condition:
        raise ProbeError(code)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked_source(source):
    require(re.fullmatch("[a-f0-9]{40}", source or "") is not None, "SOURCE_SHA_REQUIRED")
    paths = [
        "src/sim2act",
        "scripts/candidate_wheel.py",
        "requirements.lock",
        "setup.py",
        str(SCRIPT.relative_to(ROOT)),
    ]
    probe = subprocess.run(
        ["git", "cat-file", "-e", source + "^{commit}"], cwd=ROOT, capture_output=True, timeout=5
    )
    require(probe.returncode == 0, "SOURCE_COMMIT_UNAVAILABLE")
    probe = subprocess.run(
        ["git", "diff", "--exit-code", source, "--", *paths],
        cwd=ROOT,
        capture_output=True,
        timeout=5,
    )
    require(probe.returncode == 0, "FROZEN_SOURCE_CHANGED")
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(SCRIPT.relative_to(ROOT))],
        cwd=ROOT,
        capture_output=True,
        timeout=5,
    )
    require(tracked.returncode == 0, "CONTROLLER_NOT_FROZEN")
    from sim2act.production_trial_admission import _qualified

    _qualified()  # Exact complete Python/native-source manifest, no DB or account authority.


def manifest_check(path):
    """Exact content digest, not a changed tag, author-supplied PASS or endpoint."""
    if path is None:
        return False
    raw = Path(path).read_bytes()
    require(len(raw) <= 262144, "MANIFEST_TOO_LARGE")
    require("sha256:" + hashlib.sha256(raw).hexdigest() == DIGEST, "PINNED_MANIFEST_MISMATCH")
    value = json.loads(raw)
    platform = [
        m
        for m in value.get("manifests", [])
        if m.get("platform", {}).get("os") == "linux"
        and m.get("platform", {}).get("architecture") == "amd64"
    ]
    require(
        len(platform) == 1 and re.fullmatch("sha256:[a-f0-9]{64}", platform[0].get("digest", "")),
        "PINNED_AMD64_MANIFEST_UNCONFIRMED",
    )
    return True


def resources():
    available = shutil.disk_usage(BASE).free
    limit_text = Path("/sys/fs/cgroup/memory.max").read_text().strip()
    current = int(Path("/sys/fs/cgroup/memory.current").read_text())
    stats = dict(
        line.split() for line in Path("/sys/fs/cgroup/memory.stat").read_text().splitlines()
    )
    reclaimable = int(stats.get("inactive_file", 0))
    capacity = max(0, int(limit_text) - current + reclaimable) if limit_text.isdecimal() else 0
    return dict(
        disk_available_bytes=available,
        memory_available_or_inactive_bytes=capacity,
        disk_ready=available >= 2 * 1024**3,
        memory_ready=capacity >= 4 * 1024**3,
    )


def dependencies():
    expected = {}
    for line in (ROOT / "requirements.lock").read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^ ;]+)", line.strip())
        require(match is not None, "UNSUPPORTED_DEPENDENCY_LOCK_SYNTAX")
        expected[match[1]] = match[2]
    found = {}
    for name in expected:
        try:
            found[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            found[name] = None
    helper = ROOT / "scripts/candidate_wheel.py"
    spec = importlib.util.spec_from_file_location("sim2act_probe_native_inputs", helper)
    group_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(group_module)
    native = {}
    for name, inputs in group_module.NATIVE_SOURCE_GROUPS.items():
        try:
            module = importlib.import_module("sim2act." + name)
            witness = hashlib.sha256(
                b"".join((ROOT / "src/sim2act" / n).read_bytes() for n in inputs)
            ).hexdigest()
            native[name] = getattr(module, "SOURCE_SHA256", None) == witness
        except (ImportError, OSError):
            native[name] = False
    names = [
        "sim2act",
        "sim2act.cli",
        "sim2act.desktop_protocol",
        "sim2act.desktop_service",
        "sim2act.api",
        "sim2act.worker",
        "sim2act.natural_trial_preparation",
    ]
    expected_paths = {
        name: str(
            (
                ROOT
                / "src/sim2act"
                / ("__init__.py" if name == "sim2act" else name.rsplit(".", 1)[1] + ".py")
            ).resolve()
        )
        for name in names
    }
    current = {name: str(Path(importlib.import_module(name).__file__).resolve()) for name in names}
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            "import importlib,json,pathlib;names="
            + repr(names)
            + ";print(json.dumps({n:str(pathlib.Path(importlib.import_module(n).__file__).resolve()) for n in names}))",
        ],
        cwd=ROOT,
        env=system_environment(),
        capture_output=True,
        text=True,
        timeout=10,
    )
    child_binding = (
        child.returncode == 0
        and len(child.stdout) <= 8192
        and json.loads(child.stdout) == expected_paths
    )
    return dict(
        python_import_binding_verified=current == expected_paths and child_binding,
        python_invocation=sys.executable,
        python_prefix=sys.prefix,
        python_executable=str(Path(sys.executable).resolve()),
        versions=found,
        versions_match=found == expected,
        native_source_hash_matches=native,
        native_ready=all(native.values()),
        requirements_sha256=digest(ROOT / "requirements.lock"),
        native_input_recipe_sha256=digest(helper),
    )


def finite_pb_recipe():
    def port(step, field):
        return dict(source="step", ref=step, field=field)

    source = {k: port("core_read", k) for k in ("resource_id", "content", "hash", "format")}
    return dict(
        version="natural-spec-recipe.v1",
        steps=[
            dict(
                step_id="core_read",
                operator="resource.read",
                depends_on=[],
                inputs=dict(resource_id=dict(source="data", ref="source", field="resource_id")),
            ),
            dict(
                step_id="core_all",
                operator="model.spec.all",
                depends_on=["core_read"],
                inputs=source,
            ),
            dict(
                step_id="core_check",
                operator="spec.verify_citations",
                depends_on=["core_read", "core_all"],
                inputs={**source, "items": port("core_all", "items")},
            ),
            dict(
                step_id="core_save",
                operator="artifact.save_text",
                depends_on=["core_check"],
                inputs=dict(text=port("core_check", "text")),
            ),
        ],
    )


def plan(source, manifest=None):
    facts = resources()
    return dict(
        version="sim2act.isolated-pg-core.v1",
        source_sha=source,
        controller_sha256=digest(SCRIPT),
        image=IMAGE,
        platform="linux/amd64",
        mode="CORE_MODEL0",
        model_requests=0,
        max_seconds=CORE_SECONDS,
        cleanup_reserve_seconds=CLEANUP_SECONDS,
        dependency_manifest_verified=manifest_check(manifest),
        local_dependencies=dependencies(),
        preconditions=facts,
        temporary_secrets=4,
        network="one nonce-labelled bridge",
        publish="127.0.0.1:assigned:5432",
        user="999:999",
        memory_bytes=512 * 1024**2,
        root_filesystem_readonly=True,
        capabilities="drop ALL",
        no_new_privileges=True,
        pgdata="512MiB tmpfs; destroyed only after known clean app/PG shutdown",
        no_trust=True,
        no_force_cleanup=True,
        unknown_preserved=True,
        optional_live=dict(
            implemented=False,
            max_requests=7,
            generate=3,
            source=2,
            cold=2,
            max_seconds=1080,
            reason="normal exact stage scheduling/extraction controller not closed; NOT_RUN",
        ),
    )


def plan_hash(value):
    # Resource observations fluctuate; approval binds thresholds and concrete
    # operations, and execution rechecks current resources independently.
    bound = {k: v for k, v in value.items() if k != "preconditions"}
    return hashlib.sha256(
        json.dumps(bound, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def write_private(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(value)


def run(argv, *, timeout=10, input_text=None, collect_stderr=False):
    process = None
    try:
        if DEADLINE is not None:
            timeout = min(timeout, max(0.01, DEADLINE - time.monotonic()))
            require(time.monotonic() < DEADLINE, "COMMAND_DEADLINE")
        process = subprocess.Popen(
            argv,
            cwd=ROOT,
            env=system_environment(),
            stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        output, errors = process.communicate(input_text, timeout=timeout)
        require(
            process.returncode == 0 and len(output) <= 262144 and len(errors) <= 262144,
            "COMMAND_REFUSED_OR_UNCONFIRMED",
        )
        return output + errors if collect_stderr else output
    except subprocess.TimeoutExpired:
        # No subprocess.run timeout kill; preserve the actual owned handle.
        import psutil

        try:
            created = psutil.Process(process.pid).create_time()
        except psutil.Error:
            created = None
        INFLIGHT.append(
            (process, dict(pid=process.pid, created_at=created, program=Path(argv[0]).name))
        )
        raise ProbeError("COMMAND_INFLIGHT_UNKNOWN") from None
    except ProbeError:
        raise
    except Exception:
        raise ProbeError("COMMAND_UNCONFIRMED") from None


class OwnedDesktop:
    """Bounded original protocol; actual exit/dual EOF, no terminate/kill fallback."""

    def __init__(self, command, *, backend=CONFIGURED):
        self.backend = backend
        self.started = time.monotonic()
        self.events = queue.Queue(maxsize=64)
        self.records = collections.deque(maxlen=64)
        self.failed = threading.Event()
        self.eof = set()
        self.process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=system_environment(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.session = None
        self.ready = None
        self.readers = [
            threading.Thread(target=self.read, args=(name,), daemon=True)
            for name in ("stdout", "stderr")
        ]
        for thread in self.readers:
            thread.start()

    def read(self, name):
        try:
            stream = getattr(self.process, name)
            while True:
                line = stream.readline(8193)
                if not line:
                    break
                if len(line) > 8192 or not line.endswith("\n"):
                    self.failed.set()
                    continue
                if name == "stdout":
                    try:
                        value = parse(line)
                        self.records.append(value)
                        self.events.put_nowait(value)
                    except Exception:
                        self.failed.set()
            self.eof.add(name)
        except Exception:
            self.failed.set()

    def event(self, name, seconds=30):
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            require(not self.failed.is_set(), "OWNED_PROTOCOL_FAILED")
            try:
                value = self.events.get(timeout=min(0.1, max(0.001, until - time.monotonic())))
            except queue.Empty:
                require(self.process.poll() is None, "OWNED_PROCESS_EXITED")
                continue
            require(
                value.get("protocol") == PROTOCOL and value.get("backend") == self.backend,
                "OWNED_PROTOCOL_IDENTITY",
            )
            require(
                re.fullmatch("[a-f0-9]{32}", value.get("session", "")) is not None,
                "OWNED_SESSION_INVALID",
            )
            if self.session is None:
                self.session = value["session"]
            require(value["session"] == self.session, "OWNED_SESSION_CHANGED")
            if value.get("event") == name:
                if name == "DESKTOP_SERVICE_READY":
                    require(
                        value.get("api_pid") != value.get("worker_pid")
                        and self.process.pid not in {value.get("api_pid"), value.get("worker_pid")},
                        "OWNED_ROLE_PID_IDENTITY",
                    )
                    require(
                        re.fullmatch(r"http://127\.0\.0\.1:[0-9]+", value.get("url", ""))
                        is not None,
                        "OWNED_ORIGIN_INVALID",
                    )
                if name == "DESKTOP_SERVICE_READY":
                    self.ready = value
                return value
        raise ProbeError("OWNED_EVENT_TIMEOUT")

    def close(self):
        try:
            if not self.process.stdin.closed:
                if self.session:
                    self.process.stdin.write(
                        json.dumps(dict(command="stop", session=self.session)) + "\n"
                    )
                    self.process.stdin.flush()
                self.process.stdin.close()  # EOF is required even before session/READY.
            code = self.process.wait(timeout=22)
            for thread in self.readers:
                thread.join(2)
            stopped = [v for v in self.records if v.get("event") == "DESKTOP_SERVICE_STOPPED"]
            require(
                not self.failed.is_set()
                and code == 0
                and self.eof == {"stdout", "stderr"}
                and not any(t.is_alive() for t in self.readers)
                and len(stopped) == 1,
                "OWNED_STOP_UNKNOWN",
            )
            final = stopped[0]
            require(
                final.get("session") == self.session
                and final.get("clean") is True
                and final.get("claim_preserved") is False
                and final.get("preflight_stopped") is True,
                "OWNED_STOP_UNKNOWN",
            )
            roles = final.get("roles", {})
            require(
                set(roles) == {"api", "worker"}
                and all(
                    v.get("exitcode") == 0
                    and v.get("stdout_eof") is True
                    and v.get("stderr_eof") is True
                    and v.get("receipt", {}).get("clean") is True
                    for v in roles.values()
                ),
                "OWNED_ROLES_NOT_DRAINED",
            )
            if self.ready is not None:
                require(
                    final.get("ready_seen") is True
                    and all(
                        v["pid"] == self.ready[role + "_pid"]
                        and v["receipt"].get("session") == self.session
                        and v["receipt"].get("role") == role
                        and v["receipt"].get("pid") == v["pid"]
                        and v["receipt"].get("backend") == self.backend
                        and v["receipt"].get("protocol") == PROTOCOL
                        for role, v in roles.items()
                    ),
                    "OWNED_STOP_IDENTITY_CHANGED",
                )
            self.process.stdout.close()
            self.process.stderr.close()
            return final
        except Exception:
            raise ProbeError("OWNED_STOP_UNKNOWN") from None


def http(client, path, body=None, status=200):
    response = client.get(path) if body is None else client.post(path, json=body)
    require(response.status_code == status, "PRODUCT_HTTP_REFUSED")
    return response.json()


def core_flow(service_factory, bearer, checkpoint=lambda: None):
    """Only public product identity/material/approval/runtime APIs, no SQL grants."""
    running = service_factory()
    try:
        ready = running.event("DESKTOP_SERVICE_READY")
        with httpx.Client(
            base_url=ready["url"],
            headers={"Authorization": "Bearer " + bearer},
            trust_env=False,
            timeout=5,
            event_hooks={"request": [lambda _: checkpoint()]},
        ) as client:
            checkpoint()
            project = http(client, "/api/projects", dict(name="Isolated PG synthetic core"), 201)[
                "id"
            ]
            resource = http(
                client,
                f"/api/projects/{project}/resources",
                dict(name="values.csv", format="csv", content="item,amount\nA,10\nB,20\n"),
                201,
            )
            app = http(
                client,
                f"/api/projects/{project}/apps/csv-preview",
                dict(name="Sum amount", resource_id=resource["id"], goal="Sum amount"),
                201,
            )
            app = http(client, "/api/apps/" + app["id"])
            approval = http(
                client,
                f"/api/internal/apps/{app['id']}/release-approvals",
                dict(
                    expected_draft_fingerprint=app["fingerprint"],
                    sample_input=dict(column="amount"),
                ),
                201,
            )
            release = http(
                client,
                f"/api/internal/approvals/{approval['id']}/commit",
                dict(fingerprint=approval["fingerprint"]),
            )
            instance = http(
                client,
                f"/api/internal/releases/{release['id']}/instances",
                dict(
                    expected_release_fingerprint=release["fingerprint"], request_key="core-instance"
                ),
                201,
            )
            request = dict(
                expected_release_fingerprint=release["fingerprint"],
                expected_revision=instance["revision"],
                input=dict(column="amount"),
                request_key="core-run",
            )
            route = f"/api/internal/instances/{instance['id']}/runs"
            accepted = http(client, route, request, 202)
            until = time.monotonic() + 30
            while True:
                checkpoint()
                result = http(client, route + "/" + accepted["run_id"])
                if result["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
                    break
                require(time.monotonic() < until, "PRODUCT_RUN_NOT_TERMINAL")
                time.sleep(0.05)
            require(
                result["status"] == "SUCCEEDED" and result["result"]["sum"] == "30",
                "PRODUCT_RESULT_MISMATCH",
            )
            require(
                http(client, route, request, 202)["run_id"] == accepted["run_id"],
                "ORIGINAL_KEY_DUPLICATED",
            )
            cancelled = http(
                client,
                f"/api/projects/{project}/csv-report-runs",
                dict(resource_id=resource["id"], column="amount", request_key="core-cancel"),
                202,
            )
            cancel_route = "/api/runs/" + cancelled["run_id"]
            pending = http(client, cancel_route)
            require(pending["status"] == "WAITING_APPROVAL", "CANCEL_PRECONDITION")
            http(
                client,
                cancel_route + "/commands",
                dict(command="cancel", version=pending["version"]),
            )
            cancelled = http(client, cancel_route)
            require(
                cancelled["status"] == "CANCELLED" and cancelled["result"] is None,
                "CANCEL_NOT_FINAL",
            )
            repeated = client.post(
                cancel_route + "/commands",
                json=dict(command="cancel", version=cancelled["version"]),
            )
            require(
                repeated.status_code == 409
                and repeated.json().get("error", {}).get("code") == "VERSION_CONFLICT",
                "TERMINAL_CANCEL_MUST_NOT_REPLAY",
            )
            require(http(client, cancel_route) == cancelled, "TERMINAL_CANCEL_CHANGED")
            checkpoint()
    finally:
        first_stop = running.close()
    reopened = service_factory()
    try:
        current = reopened.event("DESKTOP_SERVICE_READY")
        require(current["url"] == ready["url"], "PERSISTENT_ORIGIN_CHANGED")
        with httpx.Client(
            base_url=current["url"],
            headers={"Authorization": "Bearer " + bearer},
            trust_env=False,
            timeout=5,
            event_hooks={"request": [lambda _: checkpoint()]},
        ) as client:
            require(
                http(client, route + "/" + accepted["run_id"]) == result, "REOPEN_RESULT_CHANGED"
            )
            require(http(client, cancel_route) == cancelled, "REOPEN_CANCEL_CHANGED")
            require(
                http(client, route, request, 202)["run_id"] == accepted["run_id"],
                "REOPEN_KEY_REPLAYED",
            )
            require(
                http(client, "/api/resources/" + resource["id"])["content"]
                == "item,amount\nA,10\nB,20\n",
                "REOPEN_MATERIAL_CHANGED",
            )
            # Both normal seven-slot preparation/consent APIs, no model/source mocks.
            choices = []
            for text in ["The river is blue.", "The tree is green."]:
                material = http(
                    client,
                    f"/api/projects/{project}/resources",
                    dict(name="synthetic.txt", format="txt", content=text),
                    201,
                )
                card = http(
                    client,
                    f"/api/projects/{project}/goal-cards",
                    dict(
                        title="Synthetic notes",
                        goal="Extract cited notes",
                        known=[],
                        assumptions=[],
                        constraints=[],
                        acceptance_checks=["Human review"],
                        unresolved=[],
                        resource_refs=[material["id"]],
                    ),
                    201,
                )
                card = http(client, "/api/goal-cards/" + card["id"])
                choices.append(dict(card_id=card["id"], expected_version=card["version"]))
            preparation_results = []
            for label, extra in [
                ("pa", {}),
                ("pb", dict(path="P-B", extraction_recipe=finite_pb_recipe())),
            ]:
                exact = f"/api/projects/{project}/natural-trials/core-{label}"
                prepared = http(client, exact + "/preparation", dict(bindings=choices, **extra))
                require(
                    prepared["path"] == "P-" + label[-1].upper()
                    and prepared["live_allowed"] is False
                    and prepared["actual_model_requests"] == 0,
                    "PREPARE_DISPATCHED_OR_WRONG_PATH",
                )
                http(
                    client,
                    exact + "/consent",
                    dict(review_token=prepared["review_token"], confirm_exact_scope=True),
                )
                original = http(client, exact + "/preparation")
                require(
                    original["approved"] is True and original["contract"] == prepared["contract"],
                    "APPROVAL_NOT_SAVED",
                )
                key = original["contract"]["stage_keys"]["generate"] + "_approval"
                selection = http(client, exact + "/approvals/" + key + "/worker-selection")
                require(
                    selection["worker_selection"] is None
                    and selection["selection_blocked_reason"]
                    == "ORIGINAL_SCOPE_NOT_CONFIGURED_ACCOUNT",
                    "MODEL0_SCOPE_MUST_NOT_BECOME_LIVE_ACCOUNT_AUTHORITY",
                )
                http(
                    client,
                    exact + "/withdrawal",
                    dict(review_token=prepared["review_token"], confirm_withdrawal=True),
                )
                require(
                    http(client, exact + "/preparation")["revoked"] is True, "WITHDRAWAL_NOT_SAVED"
                )
                preparation_results.append(
                    dict(
                        path=prepared["path"],
                        prepared=True,
                        approved=True,
                        withdrawn=True,
                        model_requests=0,
                    )
                )
            grants = http(client, f"/api/projects/{project}/grants")
            selected = [
                g for g in grants if g["resource_id"] == resource["id"] and not g["revoked"]
            ]
            require(bool(selected), "ORIGINAL_RESOURCE_GRANT_MISSING")
            for grant in selected:
                http(
                    client,
                    "/api/grants/" + grant["id"] + "/revoke",
                    dict(command="revoke", version=grant["revision"]),
                )
            denied = client.get("/api/resources/" + resource["id"])
            require(denied.status_code == 403, "REVOKED_READ_NOT_DENIED")
            checkpoint()
            return dict(
                status="CORE_MODEL0_PASSED",
                project_id=project,
                run_id=accepted["run_id"],
                result_sum="30",
                same_origin=True,
                original_key_same=True,
                cancel_final=True,
                read_revoked=True,
                pa_pb_preparations=preparation_results,
                actual_model_requests=0,
                first_stop=first_stop,
                backend=running.backend,
            )
    finally:
        reopened.close()


def password_rejected(error, port, user):
    if getattr(error, "sqlstate", None) == "28P01":
        return True
    if getattr(error, "sqlstate", None) is not None:
        return False
    # libpq connect() failures can have no SQLSTATE in psycopg 3.3.3. Match only
    # the complete one-target FATAL authentication diagnostic, privately.
    expression = (
        r'(?:connection failed: )?connection to server at "127\.0\.0\.1", port '
        + str(port)
        + r' failed: FATAL:\s+password authentication failed for user "'
        + re.escape(user)
        + r'"\s*'
    )
    return re.fullmatch(expression, str(error)) is not None


def execute(source, manifest, expected_hash):
    """No effects before all exact source/dependency/resource/confirmation gates."""
    global DEADLINE
    checked_source(source)
    value = plan(source, manifest)
    require(value["dependency_manifest_verified"], "DEPENDENCY_NOT_VERIFIED")
    require(
        value["preconditions"]["disk_ready"] and value["preconditions"]["memory_ready"],
        "RESOURCE_NOT_READY",
    )
    require(
        value["local_dependencies"]["versions_match"]
        and value["local_dependencies"]["native_ready"]
        and value["local_dependencies"]["python_import_binding_verified"],
        "LOCAL_DEPENDENCIES_UNCONFIRMED",
    )
    require(expected_hash == plan_hash(value), "EXACT_PLAN_CONFIRMATION_REQUIRED")
    started = time.monotonic()
    DEADLINE = started + CORE_SECONDS - CLEANUP_SECONDS
    root = None
    root_identity = None
    prior_state = None
    network = None
    container = None
    pg = None
    passwords = []
    bearer = None
    safe = False
    state = dict(
        status="PREPARING", source_sha=source, plan_sha256=plan_hash(value), model_requests=0
    )

    def checkpoint():
        require(time.monotonic() < started + CORE_SECONDS - CLEANUP_SECONDS, "CORE_DEADLINE")

    def root_current():
        require(root is not None and root_identity is not None, "PRIVATE_ROOT_UNOWNED")
        st = root.lstat()
        require(
            stat.S_ISDIR(st.st_mode)
            and not stat.S_ISLNK(st.st_mode)
            and (st.st_dev, st.st_ino) == root_identity
            and st.st_uid == os.geteuid(),
            "PRIVATE_ROOT_CHANGED",
        )

    def record():
        nonlocal prior_state
        if root is None or root_identity is None:
            return
        root_current()
        destination = root / "public-state.json"
        if prior_state is None:
            write_private(destination, json.dumps(state, indent=2) + "\n")
        else:
            require(
                not destination.is_symlink()
                and destination.is_file()
                and destination.stat().st_nlink == 1
                and destination.read_bytes() == prior_state,
                "PUBLIC_STATE_CHANGED",
            )
            temporary = root / "public-state.next"
            write_private(temporary, json.dumps(state, indent=2) + "\n")
            root_current()
            os.replace(temporary, destination)
        prior_state = destination.read_bytes()

    try:
        # First mutating action: only reached following separate concrete confirmation.
        nonce = secrets.token_hex(16)
        candidate = ordinary(BASE / ("sim2act-pg-probe-" + nonce))
        candidate.mkdir(mode=0o700, exist_ok=False)
        st = candidate.lstat()
        require(
            stat.S_ISDIR(st.st_mode) and not stat.S_ISLNK(st.st_mode), "PRIVATE_ROOT_CREATE_UNKNOWN"
        )
        root = candidate
        root_identity = (st.st_dev, st.st_ino)
        state.update(nonce=nonce, private_root=str(root))
        record()
        checkpoint()
        run([*DOCKER, "pull", "--platform", "linux/amd64", IMAGE], timeout=300)
        info = json.loads(run([*DOCKER, "image", "inspect", IMAGE]))[0]
        require(
            info["Os"] == "linux"
            and info["Architecture"] == "amd64"
            and IMAGE in info["RepoDigests"],
            "IMAGE_IDENTITY",
        )
        state["image_id"] = info["Id"]
        record()
        passwords = [secrets.token_urlsafe(32) for _ in range(3)]
        name = "sim2act-pg-probe-" + nonce
        schema = "probe_" + nonce[:12]
        bootstrap = "probe_admin"
        migration = "probe_m_" + nonce[:12]
        app = "probe_a_" + nonce[:12]
        envfile = root / "bootstrap.env"
        write_private(
            envfile,
            "PGDATA=/var/lib/postgresql/data/pgdata\nPOSTGRES_DB=sim2act_probe\nPOSTGRES_USER="
            + bootstrap
            + "\nPOSTGRES_PASSWORD="
            + passwords[0]
            + "\nPOSTGRES_INITDB_ARGS=--auth-host=scram-sha-256 --auth-local=scram-sha-256\n",
        )
        checkpoint()
        network = run(
            [
                *DOCKER,
                "network",
                "create",
                "--driver",
                "bridge",
                "--label",
                "sim2act.probe=" + nonce,
                name,
            ]
        ).strip()
        require(re.fullmatch("[a-f0-9]{64}", network) is not None, "NETWORK_IDENTITY")
        state["network_id"] = network
        record()
        command = 'test "$(id -u)" = 999 && test "$(id -g)" = 999 && test "$(id -u postgres)" = 999 && exec /usr/local/bin/docker-entrypoint.sh postgres "$@"'
        checkpoint()
        container = run(
            [
                *DOCKER,
                "run",
                "--detach",
                "--name",
                name,
                "--label",
                "sim2act.probe=" + nonce,
                "--network",
                name,
                "--user",
                "999:999",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--memory",
                "512m",
                "--cpus",
                "1",
                "--pids-limit",
                "128",
                "--tmpfs",
                "/var/lib/postgresql/data:rw,uid=999,gid=999,mode=0700,size=512m",
                "--tmpfs",
                "/var/run/postgresql:rw,uid=999,gid=999,mode=0700,size=16m",
                "--tmpfs",
                "/tmp:rw,uid=999,gid=999,mode=0700,size=32m",
                "--publish",
                "127.0.0.1::5432",
                "--env-file",
                str(envfile),
                "--entrypoint",
                "/bin/sh",
                IMAGE,
                "-ec",
                command,
                "--",
                "-c",
                "max_connections=16",
                "-c",
                "shared_buffers=32MB",
                "-c",
                "max_wal_size=64MB",
                "-c",
                "min_wal_size=32MB",
                "-c",
                "password_encryption=scram-sha-256",
            ]
        ).strip()
        require(re.fullmatch("[a-f0-9]{64}", container) is not None, "CONTAINER_IDENTITY")
        state["container_id"] = container
        record()
        mapped = run([*DOCKER, "port", container, "5432/tcp"]).strip()
        require(re.fullmatch(r"127\.0\.0\.1:[0-9]+", mapped) is not None, "LOOPBACK_BINDING")
        port = int(mapped.split(":")[1])
        import psycopg
        from psycopg import sql

        until = time.monotonic() + 45
        while pg is None:
            checkpoint()
            try:
                pg = psycopg.connect(
                    host="127.0.0.1",
                    port=port,
                    dbname="sim2act_probe",
                    user=bootstrap,
                    password=passwords[0],
                    connect_timeout=2,
                    autocommit=True,
                    options="-cstatement_timeout=3000 -clock_timeout=1000",
                )
            except psycopg.OperationalError:
                require(time.monotonic() < until, "PG_TCP_NOT_READY")
                time.sleep(0.2)
        version, user, database = pg.execute(
            "select version(),current_user,current_database()"
        ).fetchone()
        require(
            version.startswith("PostgreSQL 17.11 ")
            and user == bootstrap
            and database == "sim2act_probe",
            "PG_SERVER_IDENTITY",
        )
        rules = pg.execute("SELECT DISTINCT auth_method,error FROM pg_hba_file_rules").fetchall()
        require(
            bool(rules)
            and all(
                error is None and method in {"scram-sha-256", "reject"} for method, error in rules
            )
            and any(method == "scram-sha-256" for method, _ in rules),
            "PG_SCRAM_RULES_UNCONFIRMED",
        )
        try:
            rejected = psycopg.connect(
                host="127.0.0.1",
                port=port,
                dbname="sim2act_probe",
                user=bootstrap,
                password="not-a-valid-probe-password",
                connect_timeout=2,
            )
        except psycopg.OperationalError as error:
            require(
                password_rejected(error, port, bootstrap), "PG_WRONG_PASSWORD_REFUSAL_UNCONFIRMED"
            )
            state["wrong_password_refused"] = True
        else:
            rejected.close()
            raise ProbeError("PG_WRONG_PASSWORD_NOT_REFUSED")
        for role, password in zip([migration, app], passwords[1:], strict=True):
            pg.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
                ).format(sql.Identifier(role), sql.Literal(password))
            )
        pg.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        pg.execute("REVOKE CONNECT ON DATABASE sim2act_probe FROM PUBLIC")
        for role in [migration, app]:
            pg.execute(
                sql.SQL("GRANT CONNECT ON DATABASE sim2act_probe TO {}").format(
                    sql.Identifier(role)
                )
            )
        pg.execute(
            sql.SQL("CREATE SCHEMA {} AUTHORIZATION {}").format(
                sql.Identifier(schema), sql.Identifier(migration)
            )
        )
        from sim2act.production_evidence import ACCOUNT_ID
        from sim2act.production_trial_admission import canonical_quota_subject

        def config(role, password, path):
            url = URL.create(
                "postgresql+psycopg",
                username=role,
                password=password,
                host="127.0.0.1",
                port=port,
                database="sim2act_probe",
                query={"options": "-csearch_path=" + schema, "connect_timeout": "2"},
            ).render_as_string(hide_password=False)
            write_private(
                path,
                "SIM2ACT_DATABASE_URL="
                + url
                + "\nSIM2ACT_DATA_DIR="
                + str(root / "app")
                + "\nSIM2ACT_MODEL_MODE=mock\nSIM2ACT_LIVE_ENABLED=false\nSIM2ACT_QUOTA_SUBJECT="
                + canonical_quota_subject(ACCOUNT_ID)
                + "\n",
            )

        config(migration, passwords[1], root / "migration.env")
        config(app, passwords[2], root / "app.env")
        checkpoint()
        run(
            [
                sys.executable,
                "-m",
                "sim2act.cli",
                "migrate",
                "--config",
                str(root / "migration.env"),
            ],
            timeout=30,
        )
        pg.execute(
            sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                sql.Identifier(schema), sql.Identifier(app)
            )
        )
        pg.execute(
            sql.SQL("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA {} TO {}").format(
                sql.Identifier(schema), sql.Identifier(app)
            )
        )
        pg.execute(
            sql.SQL("GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA {} TO {}").format(
                sql.Identifier(schema), sql.Identifier(app)
            )
        )
        checkpoint()
        reply = run(
            [
                sys.executable,
                "-m",
                "sim2act.cli",
                "init-user",
                "--config",
                str(root / "app.env"),
                "--name",
                "Isolated synthetic PG probe",
            ],
            timeout=10,
        )
        match = re.fullmatch(
            r"Local UI bearer token \(shown once; store privately, never commit\): ([A-Za-z0-9_-]{40,60})\n",
            reply,
        )
        require(match is not None, "ORIGINAL_INIT_USER_UNCONFIRMED")
        bearer = match[1]
        write_private(root / "application-bearer", bearer + "\n")
        pg.close()
        pg = None
        checkpoint()
        result = core_flow(
            lambda: OwnedDesktop(
                [
                    sys.executable,
                    "-u",
                    "-m",
                    "sim2act.desktop_service",
                    "--supervise",
                    "--control-stdin",
                    "--config",
                    str(root / "app.env"),
                ]
            ),
            bearer,
            checkpoint,
        )
        state.update(status="CORE_PASSED_CLEANUP_PENDING", core=result)
        record()
        safe = True
    except Exception as error:
        state.update(
            status="UNKNOWN_RETAINED",
            error=str(error) if isinstance(error, ProbeError) else type(error).__name__,
            inflight=[identity for _, identity in INFLIGHT],
        )
        if container is not None and root is not None:
            try:
                root_current()
                boot = run(
                    [*DOCKER, "logs", "--tail", "200", container], timeout=3, collect_stderr=True
                )
                for secret in [*passwords, bearer]:
                    if secret:
                        boot = boot.replace(secret, "[REDACTED]")
                write_private(root / "postgres-startup.redacted.log", boot)
                state["startup_log"] = (
                    "private bounded known-secret-redacted tail saved; not printed"
                )
            except Exception:
                state["startup_log"] = "UNCONFIRMED"
        record()
        raise ProbeError("PROBE_FAILED_PRIVATE_STATE_RETAINED") from None
    finally:
        if pg is not None:
            pg.close()
        if safe and container is not None:
            DEADLINE = started + CORE_SECONDS
            # No implicit SIGKILL: normal PostgreSQL fast shutdown, exact owned IDs.
            try:
                info = json.loads(run([*DOCKER, "inspect", container]))[0]
                require(
                    info["Id"] == container
                    and info["Image"] == state["image_id"]
                    and info["Config"]["Labels"].get("sim2act.probe") == state["nonce"],
                    "CLEANUP_OWNER_CHANGED",
                )
                run(
                    [
                        *DOCKER,
                        "exec",
                        container,
                        "pg_ctl",
                        "-D",
                        "/var/lib/postgresql/data/pgdata",
                        "-m",
                        "fast",
                        "-w",
                        "-t",
                        "30",
                        "stop",
                    ],
                    timeout=35,
                )
                until = time.monotonic() + 5
                while True:
                    info = json.loads(run([*DOCKER, "inspect", container]))[0]
                    if not info["State"]["Running"]:
                        break
                    require(time.monotonic() < until, "PG_STOP_UNKNOWN")
                    time.sleep(0.1)
                run([*DOCKER, "rm", container])
                net = json.loads(run([*DOCKER, "network", "inspect", network]))[0]
                require(
                    net["Id"] == network
                    and net["Labels"].get("sim2act.probe") == state["nonce"]
                    and not net["Containers"],
                    "NETWORK_OWNER_OR_ENDPOINT_CHANGED",
                )
                run([*DOCKER, "network", "rm", network])
                root_current()
                for name in ["bootstrap.env", "migration.env", "app.env", "application-bearer"]:
                    path = root / name
                    require(
                        not path.is_symlink() and path.is_file() and path.stat().st_nlink == 1,
                        "PRIVATE_FILE_CHANGED",
                    )
                    path.unlink()
                state.update(
                    status="CORE_MODEL0_COMPLETE",
                    cleanup="normal app STOP/dualEOF + pg_ctl fast + nonforce exact container/network remove; private credentials removed",
                    image_cache="retained; no image removal authority",
                )
                record()
            except Exception:
                state.update(status="CLEANUP_UNKNOWN_RETAINED")
                record()
                raise ProbeError("CLEANUP_UNKNOWN_RETAINED") from None
    require(state["status"] == "CORE_MODEL0_COMPLETE", "CLEANUP_NOT_CONFIRMED")
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirmed-plan-sha256")
    args = parser.parse_args()
    try:
        if args.execute:
            # This checksum is an exact-scope tripwire, not permission by itself.
            value = execute(args.source_sha, args.manifest, args.confirmed_plan_sha256)
        else:
            checked_source(args.source_sha)
            value = plan(args.source_sha, args.manifest)
            value["plan_sha256"] = plan_hash(value)
            value["execution_performed"] = False
        print(json.dumps(value, indent=2))
    except Exception as error:
        print(
            json.dumps(
                dict(
                    status="REFUSED_OR_UNCONFIRMED",
                    code=str(error) if isinstance(error, ProbeError) else type(error).__name__,
                    values_suppressed=True,
                )
            ),
            file=sys.stderr,
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
