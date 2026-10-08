"""Owned Linux PG diagnostic run, original complete Engineering selection.

Run with this checkout's isolated .venv Python. No existing database credentials
are read. Credentials remain in memory and owned container runtime only.
"""

import hashlib
import importlib.metadata
import json
import os
import platform
import secrets
import subprocess
import sys
import time
from pathlib import Path

from sqlalchemy import create_engine, text

REPO = Path.cwd()
ROOT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/sim2act-pg-phase-20261008")
EVIDENCE = Path(__file__).resolve().parent
BASE = sys.argv[1] if len(sys.argv) > 1 else "5c06520bc31269d11b9bf2786b9e18ed89333a28"
OWNER = "engineering-pg-phase-20261008"


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def run(args, **kwargs):
    return subprocess.run(args, capture_output=True, text=True, check=True, **kwargs)


def source_manifest():
    paths = run(["git", "ls-files", "-z"]).stdout.split("\0")
    paths = [p for p in paths if p and (
        p.startswith(("src/", "scripts/", "tests/", ".github/"))
        or p in {"pyproject.toml", "requirements.lock", "requirements-windows.lock",
                 ".gitattributes"})]
    rows = []
    for path in paths:
        actual = (REPO / path).read_bytes()
        original = subprocess.run(["git", "show", BASE + ":" + path],
                                  check=True, capture_output=True).stdout
        rows.append({"path": path, "sha256": hashlib.sha256(actual).hexdigest(),
                     "matches_baseline": actual == original})
    assert all(row["matches_baseline"] for row in rows)
    return rows


def census(url):
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            return {
                "test_schemas": connection.execute(text(
                    "SELECT count(*) FROM pg_namespace WHERE nspname LIKE 'test_%'"
                )).scalar_one(),
                "test_roles": connection.execute(text(
                    "SELECT count(*) FROM pg_roles WHERE rolname LIKE 'test_%'"
                )).scalar_one(),
                "public_tables": connection.execute(text(
                    "SELECT count(*) FROM pg_tables WHERE schemaname='public'"
                )).scalar_one(),
            }
    finally:
        engine.dispose()


def main():
    assert run(["git", "rev-parse", "HEAD"]).stdout.strip() == BASE
    save("source-before.json", source_manifest())
    clean_environment = {k: v for k, v in os.environ.items()
                         if not k.startswith(("SIM2ACT_", "INTERN_", "PG"))
                         and k not in {"PYTEST_ADDOPTS", "PYTHONPATH", "NODE_PATH"}}
    clean_environment.update({
        "SIM2ACT_MODEL_MODE": "mock", "SIM2ACT_LIVE_ENABLED": "false",
        "SIM2ACT_INTERN_TOKEN": "", "INTERN_API_TOKEN": "",
        "PYTHONPATH": os.pathsep.join([str(EVIDENCE), str(REPO / "tests"),
                                       str(REPO / "src")]),
        "NODE_PATH": "/tmp/sim2act-pg-phase-20261008/node-tools/node_modules",
    })
    dependencies = {d.metadata["Name"]: d.version
                    for d in importlib.metadata.distributions()}
    image = run(["docker", "image", "inspect", "postgres:17.11", "--format",
                 "{{.Id}} {{json .RepoDigests}}"])
    save("environment.json", {
        "source_sha": BASE, "platform": platform.platform(),
        "python": sys.version, "node": run(["node", "--version"]).stdout.strip(),
        "python_distributions": dependencies, "postgres_image": image.stdout.strip(),
        "native_windows": "NOT_RUN", "models": "MOCK; real provider calls 0",
        "budget_seconds": {"windows_job": 900, "edge_step": 240, "node_driver": 150},
    })
    name = "sim2act-engineering-phase-" + secrets.token_hex(5)
    password = secrets.token_hex(32)
    docker_environment = dict(clean_environment, POSTGRES_PASSWORD=password)
    started = False
    summary = {"source_sha": BASE, "stages": [], "complete": False}
    cleanup = {}
    cluster_start = time.perf_counter()
    try:
        run(["docker", "run", "-d", "--name", name, "--label", "sim2act.owner=" + OWNER,
             "-e", "POSTGRES_PASSWORD", "-p", "127.0.0.1::5432", "postgres:17.11"],
            env=docker_environment)
        started = True
        port = run(["docker", "port", name, "5432/tcp"]).stdout.strip().rsplit(":", 1)[1]
        for _ in range(150):
            ready = subprocess.run(["docker", "exec", name, "pg_isready", "-U", "postgres"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if ready.returncode == 0:
                break
            time.sleep(.2)
        else:
            raise RuntimeError("Owned PostgreSQL readiness timed out")
        summary["owned_pg_start_seconds"] = time.perf_counter() - cluster_start
        url = f"postgresql+psycopg://postgres:{password}@127.0.0.1:{port}/postgres"
        clean_environment["SIM2ACT_TEST_DATABASE_URL"] = url
        save("census-before.json", census(url))
        save("postgres-version.json", {
            "version": run(["docker", "exec", name, "postgres", "--version"]).stdout.strip()
        })
        commands = [
            ("collection", ["-m", "pytest", "--collect-only", "-q", "-p",
                            "engineering_phase_audit", "--engineering-audit-output=" +
                            str(ROOT / "collection.json")]),
            ("ruff", ["-m", "ruff", "check", "src", "scripts", "tests"]),
            ("mypy", ["-m", "mypy", "src"]),
            ("pytest", ["-m", "pytest", "-q", "--durations=30", "-ra",
                        "--basetemp=" + str(ROOT / "fixtures"),
                        "--junitxml=" + str(ROOT / "engineering.xml"),
                        "-p", "windows_phase_metrics", "--windows-metrics-output=" +
                        str(ROOT / "pg-metrics.json"), "-p", "engineering_phase_audit",
                        "--engineering-audit-output=" + str(ROOT / "phase-audit.json")]),
        ]
        for stage, arguments in commands:
            save("current-stage.json", {"stage": stage, "source_sha": BASE})
            before = time.perf_counter()
            with (ROOT / (stage + ".log")).open("w", encoding="utf-8") as log:
                result = subprocess.run([sys.executable, *arguments], env=clean_environment,
                                        stdout=log, stderr=subprocess.STDOUT)
            summary["stages"].append({"name": stage, "arguments": arguments,
                                      "exit_code": result.returncode,
                                      "wall_seconds": time.perf_counter() - before})
            save("controller.json", summary)
            if result.returncode != 0 and stage != "pytest":
                raise RuntimeError(stage + " failed; log retained")
        summary["complete"] = True
        save("source-after.json", source_manifest())
        cleanup.update(census(url))
        save("census-after.json", cleanup)
    finally:
        before = time.perf_counter()
        if started:
            label = run(["docker", "inspect", name, "--format",
                         '{{index .Config.Labels "sim2act.owner"}}']).stdout.strip()
            assert label == OWNER
            run(["docker", "rm", "-f", name])
            absent = subprocess.run(["docker", "inspect", name],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            cleanup["owned_container_removed"] = absent.returncode != 0
            cleanup["owned_container_label_checked"] = True
        cleanup["container_cleanup_seconds"] = time.perf_counter() - before
        save("cleanup.json", cleanup)
        save("controller.json", summary)
    print("Complete Engineering diagnostic finished; see owned logs and cleanup receipt.")


if __name__ == "__main__":
    main()
