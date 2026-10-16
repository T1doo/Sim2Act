"""Bounded read-only acceptance of an existing candidate's original serve CLI.

No fixture generation, Worker, model, runpy shim, environment discovery or /proc.
Import timestamps are parent line-receipt upper bounds, not child wall times.
"""

import argparse
import errno
import hashlib
import json
import os
import queue
import signal
import socket
import sqlite3
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx

STARTUP_SECONDS = 60
SHUTDOWN_SECONDS = 15
HTTP_SECONDS = 60
PUBLIC_TOKEN = "public-synthetic-local-candidate"
URL_PREFIX = "SYNTHETIC MOCK saved results (read-only): "


def stamp():
    return dict(wall_time=time.time(), monotonic=time.monotonic())


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unlinked(path):
    path = Path(os.path.abspath(path))
    require(not any(p.is_symlink() for p in [path, *path.parents]), "Linked path refused")
    return path


def snapshot(root):
    inventory = {}
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), "Linked fixture entry refused")
        if path.is_file():
            inventory[str(path.relative_to(root))] = sha(path)
    with sqlite3.connect((root / "synthetic-demo.db").as_uri() + "?mode=ro", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        tables = db.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        rows = {}
        for name, _ in tables:
            quoted = '"' + name.replace('"', '""') + '"'
            rows[name] = sorted(json.dumps(list(row), default=lambda b: dict(blob_hex=b.hex()))
                                for row in db.execute("SELECT * FROM " + quoted))
    canonical = json.dumps(dict(schema=tables, rows=rows), sort_keys=True).encode()
    return dict(files=inventory, all_table_rows_sha256=hashlib.sha256(canonical).hexdigest(),
                table_counts={name: len(values) for name, values in rows.items()})


def probe(candidate, data, output):
    candidate, data, output = map(unlinked, (candidate, data, output))
    require(candidate.is_dir() and data.is_dir(), "Existing candidate and fixture required")
    require(not output.exists() and not output.is_relative_to(data), "New output outside fixture required")
    receipt = json.loads((data / "demo-receipt.json").read_text())
    require(receipt["mode"] == "SYNTHETIC_MOCK_ONLY" and receipt["scenario"] == "PA_NEW_MATERIAL_TWICE"
            and receipt["status"] == "PASS", "Expected the completed PA v1/v2 synthetic fixture")
    require(receipt["natural_pa_previous"]["instance_id"] == receipt["natural_pa"]["instance_id"]
            and [receipt[key]["result_version"] for key in ["natural_pa_previous", "natural_pa"]] == [1, 2],
            "Expected the preserved same-instance PA versions")
    manifest = json.loads((candidate / "candidate-manifest.json").read_text())
    script = candidate / "scripts/local_candidate_demo.py"
    unlinked(script)
    require(sha(script) == manifest["files"]["scripts/local_candidate_demo.py"]["sha256"], "Candidate script differs")
    before = snapshot(data)
    output.mkdir(parents=True, exist_ok=False)
    report = dict(status="FAIL", candidate_source_commit=manifest["source_commit"],
                  candidate_script_sha256=sha(script), before=before,
                  startup_seconds=STARTUP_SECONDS, shutdown_seconds=SHUTDOWN_SECONDS, http_seconds=HTTP_SECONDS,
                  http_window_meaning="all successful response observations must be within 60s; synchronous per-phase IO timeouts are not hard cancellation",
                  import_timestamp_meaning="parent receipt upper bounds; -X importtime has microsecond durations only",
                  workers_started=0, model_requests=0, natural_runs_created=0,
                  existing_pa_results=[receipt[key] for key in ["natural_pa_previous", "natural_pa"]])
    command = [str(candidate / ".venv/bin/python"), "-u", "-X", "importtime", str(script),
               "serve", "--data-dir", str(data), "--port", "0"]
    report.update(command=command, cwd=str(candidate), spawn_before=stamp())
    lines, events, reader_errors, lock = queue.Queue(), [], [], threading.Lock()
    process, readers, origin = None, [], None

    def drain(pipe, name):
        try:
            with (output / (name + ".log")).open("w", encoding="utf-8") as raw:
                for line in pipe:
                    event = dict(stream=name, line=line.rstrip("\n"), **stamp())
                    raw.write(line)
                    raw.flush()
                    with lock:
                        events.append(event)
                    lines.put(event)
        except BaseException as error:
            with lock:
                reader_errors.append(dict(stream=name, type=type(error).__name__, message=str(error), **stamp()))
        finally:
            try:
                pipe.close()
            except BaseException as error:
                with lock:
                    reader_errors.append(dict(stream=name, type=type(error).__name__, message=str(error), **stamp()))

    try:
        process = subprocess.Popen(command, cwd=candidate, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", bufsize=1,
            env={"PATH": "/usr/bin:/bin", "TMPDIR": "/tmp", "PYTHONDONTWRITEBYTECODE": "1",
                 "PYTHONUNBUFFERED": "1"})
        report.update(pid=process.pid, popen_returned=stamp())
        for pipe, name in [(process.stdout, "stdout"), (process.stderr, "stderr")]:
            reader = threading.Thread(target=drain, args=(pipe, name), daemon=True)
            reader.start()
            readers.append(reader)
        deadline = report["spawn_before"]["monotonic"] + STARTUP_SECONDS
        report["startup_deadline_monotonic"] = deadline
        while origin is None:
            require(process.poll() is None, "Original serve CLI exited before readiness")
            require(not reader_errors, "Diagnostic reader failed; preserve failure without retry")
            require(time.monotonic() < deadline, "Startup diagnostic deadline exceeded")
            try:
                event = lines.get(timeout=min(.1, max(.001, deadline - time.monotonic())))
            except queue.Empty:
                continue
            if event["stream"] == "stdout" and event["line"].startswith(URL_PREFIX):
                origin = event["line"][len(URL_PREFIX):]
                parsed = urlsplit(origin)
                require(parsed.scheme == "http" and parsed.hostname == "127.0.0.1" and parsed.port
                        and parsed.path == "" and not parsed.query and not parsed.fragment
                        and parsed.username is None and parsed.password is None, "Unexpected serve origin")
                report["url_line_received"] = event

        def owned_origin(request):
            require(str(request.url.copy_with(path="", query=None, fragment=None)).rstrip("/") == origin,
                    "Only the owned loopback origin is permitted")

        with httpx.Client(base_url=origin, trust_env=False, follow_redirects=False,
                headers={"Authorization": "Bearer " + PUBLIC_TOKEN},
                event_hooks={"request": [owned_origin]}) as client:
            ready = client.get("/api/projects", timeout=max(.001, min(5, deadline - time.monotonic())))
            require(ready.status_code == 200 and receipt["project_id"] in {p["id"] for p in ready.json()},
                    "Actual authenticated project readiness failed")
            require(time.monotonic() < deadline, "Startup diagnostic deadline exceeded")
            report["ready_http_received"] = dict(status=ready.status_code, project_id=receipt["project_id"], **stamp())
            http_deadline = time.monotonic() + HTTP_SECONDS
            report["http_deadline_monotonic"] = http_deadline
            http = []
            paths = ["/", "/app.js", "/use.js", "/api/projects", "/api/apps?metadata_only=true",
                     receipt["deterministic"]["detail"], receipt["natural_pa_previous"]["manual_review"],
                     receipt["natural_pa"]["manual_review"]]
            for key in ["natural_pa_previous", "natural_pa"]:
                paths.append(f"/api/internal/app-run-jobs/{receipt[key]['run_id']}/spec-artifact")
            for path in paths:
                require(time.monotonic() < http_deadline, "HTTP diagnostic deadline exceeded")
                start = stamp()
                response = client.get(path, timeout=min(10, http_deadline - time.monotonic()))
                http.append(dict(method="GET", path=path, status=response.status_code,
                                 started=start, received=stamp(), body_sha256=hashlib.sha256(response.content).hexdigest()))
                report["http"] = http
                require(time.monotonic() < http_deadline, "HTTP diagnostic deadline exceeded")
                require(response.status_code == 200, "Saved read failed: " + path)
                if path == "/api/apps?metadata_only=true":
                    families = {app["id"]: app["use_family"] for app in response.json()["items"]}
                    require(families[receipt["natural_pa"]["app_id"]] == "NATURAL_PA", "Directory family changed")
                elif path == receipt["deterministic"]["detail"]:
                    require(response.json()["result"]["sum"] == "30", "CSV result changed")
                for key in ["natural_pa_previous", "natural_pa"]:
                    result = receipt[key]
                    if path == result["manual_review"]:
                        require(response.json()["owner_acceptance"] == "PENDING", "Owner state changed")
                    if path == f"/api/internal/app-run-jobs/{result['run_id']}/spec-artifact":
                        artifact = response.json()
                        require(artifact["result_version"] == result["result_version"]
                                and hashlib.sha256(artifact["resource"]["content"].encode()).hexdigest()
                                == result["artifact_sha256"], "PA artifact/version changed")
            remaining = http_deadline - time.monotonic()
            require(remaining > 0, "HTTP diagnostic deadline exceeded")
            response = client.post("/api/projects", json={"name": "must not write"}, timeout=min(5, remaining))
            http.append(dict(method="POST", path="/api/projects", status=response.status_code, received=stamp()))
            require(time.monotonic() < http_deadline, "HTTP diagnostic deadline exceeded")
            require(response.status_code == 405, "Read-only POST guard failed")
            report["http_checks_passed"] = True
    except BaseException as error:
        report["error"] = dict(type=type(error).__name__, message=str(error), **stamp())
    finally:
        if process is not None:
            try:
                require(process.poll() is None, "Original serve exited before requested shutdown")
                report["sigint_sent"] = stamp()
                process.send_signal(signal.SIGINT)
                report["popen_wait_returncode"] = process.wait(timeout=SHUTDOWN_SECONDS)
                report["popen_wait_returned"] = stamp()
            except BaseException as error:
                report["shutdown_error"] = dict(type=type(error).__name__, message=str(error), **stamp())
                if isinstance(error, subprocess.TimeoutExpired) and process.poll() is None:
                    report["owned_cleanup_fallback"] = "terminate own Popen child, then kill only if still alive"
                    try:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=5)
                    except BaseException as cleanup_error:
                        report["owned_cleanup_error"] = dict(type=type(cleanup_error).__name__,
                            message=str(cleanup_error), **stamp())
            report["actual_child_returncode"] = process.returncode
        for reader in readers:
            reader.join(5)
        report["readers_joined"] = all(not reader.is_alive() for reader in readers)
        report["reader_errors"] = reader_errors
        try:
            with (output / "line-receipts.jsonl").open("w", encoding="utf-8") as log:
                for event in sorted(events, key=lambda row: row["monotonic"]):
                    log.write(json.dumps(event) + "\n")
        except BaseException as error:
            report["event_log_error"] = dict(type=type(error).__name__, message=str(error), **stamp())
        import_events = [e for e in events if e["stream"] == "stderr" and e["line"].startswith("import time:")]
        report["import_line_receipts"] = dict(count=len(import_events), first=import_events[:1],
            sim2act_api=[e for e in import_events if e["line"].endswith("| sim2act.api")],
            latest_before_url=[e for e in import_events if e["monotonic"]
                <= report.get("url_line_received", {}).get("monotonic", 0)][-1:])
        if origin:
            try:
                parsed = urlsplit(origin)
                with socket.socket() as connection:
                    connection.settimeout(2)
                    result = connection.connect_ex((parsed.hostname, parsed.port))
                    report["port_connect_errno"] = result
                    report["port_connect_error_name"] = errno.errorcode.get(result, "UNKNOWN")
                    report["port_closed"] = result == errno.ECONNREFUSED
                    require(report["port_closed"], "Port closure unavailable or open; errno=" + str(result))
            except BaseException as error:
                report["port_check_error"] = dict(type=type(error).__name__, message=str(error), **stamp())
        try:
            report["after"] = snapshot(data)
            report["data_unchanged"] = report["before"] == report["after"]
        except BaseException as error:
            report["snapshot_error"] = dict(type=type(error).__name__, message=str(error), **stamp())
        try:
            report["candidate_script_unchanged"] = sha(script) == report["candidate_script_sha256"]
        except BaseException as error:
            report["candidate_hash_error"] = dict(type=type(error).__name__, message=str(error), **stamp())
        if (not any(key in report for key in ["error", "shutdown_error", "owned_cleanup_fallback",
                                             "event_log_error", "port_check_error", "snapshot_error", "candidate_hash_error"])
                and report.get("http_checks_passed") and report.get("popen_wait_returncode") == 0
                and report.get("port_closed") and report.get("data_unchanged")
                and report.get("candidate_script_unchanged") and report["readers_joined"] and not reader_errors):
            report["status"] = "PASS"
        (output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report.get(key) for key in ["status", "pid", "actual_child_returncode", "port_closed", "data_unchanged"]}))
    return report["status"] == "PASS"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if probe(args.candidate_root, args.data_dir, args.output) else 1)
