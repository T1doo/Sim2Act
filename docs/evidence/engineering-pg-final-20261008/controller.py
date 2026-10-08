"""One frozen-source complete PG Engineering verification, captured before start.

No retry/restart/selection change. Raw server streams remain in the owned output
directory. Diagnostic fixture spans do not alter assertions or product source.
"""

import datetime
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
import traceback
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

REPO = Path.cwd()
ROOT = Path(sys.argv[1])
FROZEN = "d85f6f5ceb05972171a84f5aa72f821b39fcb226"
IMAGE = "sha256:327daa8fae7178d61f93142f146b098467b345e10997b9eb79f63bd58e5c8f3c"
OWNER = "sim2act-final-pg-20261008"
NAME = "sim2act-final-pg-" + secrets.token_hex(6)
PASSWORD = secrets.token_hex(32)
EXPECTED_NODES = REPO / "docs/evidence/engineering-pg-phase-20261008/first/collection.json"
START = time.perf_counter()


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def record(kind, **values):
    entry = {
        "utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "elapsed_seconds": time.perf_counter() - START,
        "kind": kind,
        **values,
    }
    with (ROOT / "timeline.jsonl").open("a", encoding="utf-8") as log:
        log.write(json.dumps(entry) + "\n")


def command(args, *, check=True, timeout=10, env=None):
    record("command-start", argv=args)
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env)
    record(
        "command-end",
        argv=args,
        exit_code=result.returncode,
        stdout=result.stdout.replace(PASSWORD, "<synthetic-password>"),
        stderr=result.stderr.replace(PASSWORD, "<synthetic-password>"),
    )
    if check and result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}); timeline retained")
    return result


def state(container):
    # Deliberately omit Config.Env: runtime password must not enter state exports.
    result = command(
        [
            "docker",
            "inspect",
            container,
            "--format",
            '{"id":{{json .Id}},"state":{{json .State}},'
            '"labels":{{json .Config.Labels}},"mounts":{{json .Mounts}},'
            '"ports":{{json .NetworkSettings.Ports}}}',
        ]
    )
    value = json.loads(result.stdout)
    assert value["labels"]["sim2act.owner"] == OWNER
    record("container-state", value=value)
    return value


def source_snapshot():
    paths = subprocess.check_output(["git", "ls-files", "-z"], text=True).split("\0")
    rows = []
    for path in paths:
        if not (
            path.startswith(("src/", "scripts/", "tests/", ".github/"))
            or path
            in {
                ".gitattributes",
                "pyproject.toml",
                "requirements.lock",
                "requirements-windows.lock",
            }
        ):
            continue
        data = (REPO / path).read_bytes()
        frozen = subprocess.check_output(["git", "show", FROZEN + ":" + path])
        assert data == frozen, path
        rows.append(
            {"path": path, "sha256": hashlib.sha256(data).hexdigest(), "matches_baseline": True}
        )
    return rows


def census(engine):
    with engine.connect() as connection:
        return {
            "test_schemas": connection.execute(
                text("SELECT count(*) FROM pg_namespace WHERE nspname LIKE 'test_%'")
            ).scalar_one(),
            "test_roles": connection.execute(
                text("SELECT count(*) FROM pg_roles WHERE rolname LIKE 'test_%'")
            ).scalar_one(),
            "public_tables": connection.execute(
                text("SELECT count(*) FROM pg_tables WHERE schemaname='public'")
            ).scalar_one(),
        }


def main():
    ROOT.mkdir(parents=True, exist_ok=False)
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() == FROZEN
    save("source-before.json", source_snapshot())
    save(
        "instrumentation-sha256.json",
        [
            {"path": str(p.relative_to(REPO)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in [
                Path(__file__).resolve(),
                Path(__file__).resolve().parent / "exception_audit.py",
                REPO
                / "docs/evidence/engineering-pg-phase-20261008/full-verification/engineering_phase_audit.py",
                REPO / "tests/windows_phase_metrics.py",
            ]
        ],
    )
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("SIM2ACT_", "INTERN_", "PG"))
        and k not in {"PYTEST_ADDOPTS", "PYTHONPATH", "NODE_PATH", "NODE_OPTIONS"}
    }
    env.update(
        {
            "SIM2ACT_MODEL_MODE": "mock",
            "SIM2ACT_LIVE_ENABLED": "false",
            "SIM2ACT_INTERN_TOKEN": "",
            "INTERN_API_TOKEN": "",
            "PYTHONPATH": os.pathsep.join(
                [
                    str(REPO / "tests"),
                    str(REPO / "src"),
                    str(Path(__file__).resolve().parent),
                    str(REPO / "docs/evidence/engineering-pg-phase-20261008/full-verification"),
                ]
            ),
            "NODE_PATH": "/tmp/sim2act-pg-phase-20261008/node-tools/node_modules",
            "SIM2ACT_EXCEPTION_AUDIT_ROOT": str(ROOT),
        }
    )
    save(
        "intent.json",
        {
            "source_sha": FROZEN,
            "image": IMAGE,
            "owner": OWNER,
            "name": NAME,
            "selection": "actual default collection; preserve original1586 + new5",
            "start_attempt_limit": 1,
            "first_connection_attempt_limit": 1,
            "full_suite": "explicitly authorized single original Engineering run",
            "live": 0,
            "ci": "NOT_RUN",
            "models": "MOCK",
            "threshold_seconds": {"Windows_job": 900, "Edge": 240, "Node": 150},
        },
    )
    container = None
    attached = None
    engine = None
    summary = {
        "minimal_start_healthy": False,
        "pytest_exit_code": None,
        "source_sha": FROZEN,
        "stages": [],
        "complete": False,
    }
    cleanup = {}
    result_exit = 1
    # Open both streams before the only start; docker start -a attaches at start.
    stdout = (ROOT / "server-attached.stdout.log").open("w", encoding="utf-8")
    stderr = (ROOT / "server-attached.stderr.log").open("w", encoding="utf-8")
    try:
        command(["docker", "image", "inspect", IMAGE, "--format", "{{.Id}} {{json .RepoDigests}}"])
        create_env = dict(env, POSTGRES_PASSWORD=PASSWORD)
        created = command(
            [
                "docker",
                "create",
                "--pull=never",
                "--name",
                NAME,
                "--label",
                "sim2act.owner=" + OWNER,
                "-e",
                "POSTGRES_PASSWORD",
                "-p",
                "127.0.0.1::5432",
                IMAGE,
            ],
            env=create_env,
        )
        container = created.stdout.strip()
        save("state-before-start.json", state(container))
        record("only-start-issued", container=container, argv=["docker", "start", "-a", container])
        attached = subprocess.Popen(
            ["docker", "start", "-a", container], stdout=stdout, stderr=stderr, env=env
        )
        record("attached-process", pid=attached.pid)
        deadline = time.perf_counter() + 30
        ready = False
        while time.perf_counter() < deadline:
            current = state(container)
            if current["state"]["Status"] in {"exited", "dead"} or attached.poll() is not None:
                raise RuntimeError("Owned PG exited during startup; no restart")
            if current["state"]["Running"]:
                probe = command(
                    [
                        "docker",
                        "exec",
                        container,
                        "pg_isready",
                        "-h",
                        "127.0.0.1",
                        "-p",
                        "5432",
                        "-U",
                        "postgres",
                    ],
                    check=False,
                    timeout=5,
                )
                if probe.returncode == 0:
                    ready = True
                    break
                if probe.returncode not in {1, 2}:
                    raise RuntimeError("Readiness command failed; no bypass/restart")
            time.sleep(0.2)
        if not ready:
            raise RuntimeError("Single owned PG readiness deadline exceeded; no restart")
        save("state-ready.json", state(container))
        port = command(["docker", "port", container, "5432/tcp"]).stdout.strip().rsplit(":", 1)[1]
        url = URL.create(
            "postgresql+psycopg",
            username="postgres",
            password=PASSWORD,
            host="127.0.0.1",
            port=int(port),
            database="postgres",
        )
        engine = create_engine(url, connect_args={"connect_timeout": 3})
        record("first-authenticated-host-connect-start", host="127.0.0.1", port=int(port))
        connection_start = time.perf_counter()
        # One attempt, no business tables or data; only intrinsic server values.
        with engine.connect() as connection:
            value = (
                connection.execute(
                    text(
                        "SELECT 1 AS value, pg_backend_pid() AS backend_pid, "
                        "pg_postmaster_start_time() AS started, version() AS version"
                    )
                )
                .mappings()
                .one()
            )
            minimal = {
                **value,
                "started": value["started"].isoformat(),
                "connect_and_select_seconds": time.perf_counter() - connection_start,
            }
        save("minimal-select.json", minimal)
        record("first-authenticated-host-connect-success", **minimal)
        summary["minimal_start_healthy"] = True
        summary["minimal_start_wall_seconds"] = time.perf_counter() - START
        save("census-before.json", census(engine))
        env["SIM2ACT_TEST_DATABASE_URL"] = url.render_as_string(hide_password=False)
        commands = [
            (
                "collection",
                [
                    "-m",
                    "pytest",
                    "--collect-only",
                    "-q",
                    "-p",
                    "engineering_phase_audit",
                    "--engineering-audit-output=" + str(ROOT / "collection.json"),
                ],
            ),
            ("ruff", ["-m", "ruff", "check", "src", "scripts", "tests"]),
            ("mypy", ["-m", "mypy", "src"]),
            (
                "pytest",
                [
                    "-m",
                    "pytest",
                    "-q",
                    "--durations=30",
                    "-ra",
                    "--basetemp=" + str(ROOT / "fixtures"),
                    "--junitxml=" + str(ROOT / "engineering.xml"),
                    "-p",
                    "windows_phase_metrics",
                    "--windows-metrics-output=" + str(ROOT / "pg-metrics.json"),
                    "-p",
                    "exception_audit",
                    "-p",
                    "engineering_phase_audit",
                    "--engineering-audit-output=" + str(ROOT / "phase-audit.json"),
                ],
            ),
        ]
        for stage, arguments in commands:
            argv = [sys.executable, *arguments]
            save("current-stage.json", {"stage": stage, "source_sha": FROZEN})
            record("stage-start", stage=stage, argv=argv)
            before = time.perf_counter()
            with (ROOT / (stage + ".log")).open("w", encoding="utf-8") as log:
                child = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT)
                record("stage-process", stage=stage, pid=child.pid)
                while child.poll() is None:
                    try:
                        child.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        observed = state(container)
                        if not observed["state"]["Running"]:
                            record(
                                "owned-server-stopped-during-stage",
                                stage=stage,
                                state=observed["state"],
                            )
            exit_code = child.returncode
            summary["stages"].append(
                {
                    "name": stage,
                    "arguments": arguments,
                    "exit_code": exit_code,
                    "wall_seconds": time.perf_counter() - before,
                }
            )
            record("stage-end", stage=stage, **summary["stages"][-1])
            save("controller.json", summary)
            if stage == "collection" and exit_code == 0:
                collected = json.loads((ROOT / "collection.json").read_text())["nodes"]
                expected = json.loads(EXPECTED_NODES.read_text())["nodes"]
                from collections import Counter

                new = [n for n in collected if n not in set(expected)]
                assert Counter(collected) - Counter(new) == Counter(expected)
                assert len(new) == 5 and all(
                    n.startswith("tests/test_resources_project_lock.py::") for n in new
                )
                assert Counter(collected) == Counter(
                    json.loads(
                        (
                            REPO
                            / "docs/evidence/engineering-pg-hotspots-20261008/default-collection.json"
                        ).read_text()
                    )["nodes"]
                )
                save(
                    "collection-equality.json",
                    {
                        "count": len(collected),
                        "original1586_multiset_preserved": True,
                        "added_nodes": new,
                    },
                )
            if stage != "pytest" and exit_code != 0:
                raise RuntimeError(stage + " failed; stop without repetition")
            if stage == "pytest":
                summary["pytest_exit_code"] = exit_code
                result_exit = exit_code
        save("census-after.json", census(engine))
        save("source-after.json", source_snapshot())
        summary["complete"] = True
    except Exception as error:
        summary["error_type"] = type(error).__name__
        summary["error"] = str(error).replace(PASSWORD, "<synthetic-password>")
        (ROOT / "failure.log").write_text(
            traceback.format_exc().replace(PASSWORD, "<synthetic-password>")
        )
        record("failure", error_type=type(error).__name__, error=summary["error"])
    finally:
        if engine is not None:
            engine.dispose()
        if container is not None:
            owned = state(container)
            save("state-before-cleanup.json", owned)
            logs = command(["docker", "logs", "--timestamps", container], check=False)
            # Preserve exact complete server stdout/stderr separately before removal.
            (ROOT / "server-timestamped.stdout.log").write_text(logs.stdout, encoding="utf-8")
            (ROOT / "server-timestamped.stderr.log").write_text(logs.stderr, encoding="utf-8")
            cleanup["container_id"] = container
            cleanup["owner_label_verified"] = True
            cleanup["owned_mounts"] = owned["mounts"]
            record("owned-cleanup-start", container=container)
            command(["docker", "rm", "-f", "-v", container])
            gone = command(["docker", "ps", "-aq", "--filter", "id=" + container])
            cleanup["owned_container_absent"] = not gone.stdout.strip()
            cleanup["owned_volume_absence"] = []
            for mount in owned["mounts"]:
                if mount["Type"] == "volume":
                    volume = command(
                        [
                            "docker",
                            "volume",
                            "ls",
                            "--format",
                            "{{.Name}}",
                            "--filter",
                            "name=" + mount["Name"],
                        ]
                    )
                    cleanup["owned_volume_absence"].append(
                        {"name": mount["Name"], "absent": not volume.stdout.strip()}
                    )
            if attached is not None:
                cleanup["attached_process_exit"] = attached.wait(timeout=10)
            record("owned-cleanup-complete", **cleanup)
        stdout.close()
        stderr.close()
        save("cleanup.json", cleanup)
        save("controller.json", summary)
        save("result.json", summary)
    print(
        json.dumps(
            {
                "minimal_start_healthy": summary["minimal_start_healthy"],
                "pytest_exit_code": summary["pytest_exit_code"],
                "complete": summary["complete"],
                "owned_container_absent": cleanup.get("owned_container_absent"),
                "output": str(ROOT),
            }
        )
    )
    return result_exit


if __name__ == "__main__":
    sys.exit(main())
