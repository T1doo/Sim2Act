"""Ordinary packaged backend check; no desktop EXE/browser/security setter/live model."""

import argparse
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    args.root.mkdir(exist_ok=False)
    workspace = args.root / "workspace"
    report = dict(status="STARTED", model_requests=0, desktop_executed=False, starts=[])
    active = None

    def save():
        (args.root / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    def start(new):
        nonlocal active
        command = [str(args.python), "-I", "-B", "-u", "-m", "sim2act.cli", "synthetic-workspace",
                   "--data-dir", str(workspace), "--control-stdin"] + (["--new"] if new else [])
        child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", cwd=args.root,
            env=dict(os.environ, SIM2ACT_MODEL_MODE="mock", SIM2ACT_LIVE_ENABLED="false",
                     SIM2ACT_INTERN_TOKEN="", INTERN_API_TOKEN=""),
            **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}))
        lines, errors, pending = [], [], queue.Queue()
        def read(stream, result, announce):
            for line in stream:
                result.append(line)
                if announce:
                    pending.put(line)
        readers = [threading.Thread(target=read, args=(child.stdout, lines, True), daemon=True),
                   threading.Thread(target=read, args=(child.stderr, errors, False), daemon=True)]
        for thread in readers:
            thread.start()
        item = dict(command=command, pid=child.pid)
        report["starts"].append(item)
        active = child, lines, errors, readers, item
        save()
        until = time.monotonic() + 25
        while time.monotonic() < until and child.poll() is None:
            try:
                line = pending.get(timeout=.1)
            except queue.Empty:
                continue
            try:
                ready = json.loads(line)
            except ValueError:
                continue
            if ready.get("event") == "SYNTHETIC_WORKSPACE_READY":
                assert ready["control_stdin"] is True
                item["ready"] = ready
                save()
                return ready["url"]
        raise RuntimeError("No actual packaged READY; preserve output, do not restart")

    def stop():
        nonlocal active
        child, lines, errors, readers, item = active
        if not child.stdin.closed:
            child.stdin.close()
        item["exitcode"] = child.wait(timeout=20)
        for thread in readers:
            thread.join(timeout=3)
        item["dual_eof"] = all(not thread.is_alive() for thread in readers)
        receipts = [json.loads(line) for line in lines if line.startswith("{")]
        item["stopped"] = [v for v in receipts if v.get("event") == "SYNTHETIC_WORKSPACE_STOPPED"]
        number = len(report["starts"])
        (args.root / f"start-{number}.stdout.log").write_text("".join(lines), encoding="utf-8")
        (args.root / f"start-{number}.stderr.log").write_text("".join(errors), encoding="utf-8")
        save()
        active = None
        assert item["exitcode"] == 0 and item["dual_eof"] and len(item["stopped"]) == 1
        receipt = item["stopped"][0]
        assert receipt["clean"] and receipt["worker_stopped"] and receipt["data_preserved"]
        assert receipt["worker_id"] == item["ready"]["worker_id"]

    try:
        first = start(True)
        headers = {"Authorization": "Bearer public-synthetic-blank-workspace"}
        with httpx.Client(base_url=first, headers=headers, trust_env=False, timeout=5) as client:
            def request(method, path, body=None, status=200):
                response = client.request(method, path, json=body)
                assert response.status_code == status, (path, response.status_code, response.text)
                return response.json()
            project = request("POST", "/api/projects", dict(name="Packaged synthetic CSV"), 201)
            resource = request("POST", f"/api/projects/{project['id']}/resources",
                dict(name="practice.csv", format="csv", content="item,amount,quantity\nA,10,7\nB,20,8\n"), 201)
            draft = request("POST", f"/api/projects/{project['id']}/apps/csv-preview",
                dict(name="Packaged fixed sum", resource_id=resource["id"], goal="Sum the explicitly selected numeric column"), 201)
            app = request("GET", "/api/apps/" + draft["id"])
            approval = request("POST", f"/api/internal/apps/{app['id']}/release-approvals",
                dict(expected_draft_fingerprint=app["fingerprint"], sample_input=dict(column="amount")), 201)
            release = request("POST", f"/api/internal/approvals/{approval['id']}/commit", dict(fingerprint=approval["fingerprint"]))
            instance = request("POST", f"/api/internal/releases/{release['id']}/instances",
                dict(expected_release_fingerprint=release["fingerprint"], request_key="packaged-instance"), 201)
            route = f"/api/internal/instances/{instance['id']}/runs"
            results, bodies = [], []
            for version, (column, total) in enumerate((("amount", "30"), ("quantity", "15")), 1):
                current = request("GET", f"/api/internal/instances/{instance['id']}")
                body = dict(expected_release_fingerprint=release["fingerprint"], expected_revision=current["revision"],
                            input=dict(column=column), request_key="packaged-" + column)
                accepted = request("POST", route, body, 202)
                until = time.monotonic() + 20
                while time.monotonic() < until:
                    detail = request("GET", route + "/" + accepted["run_id"])
                    if detail["status"] not in {"QUEUED", "RUNNING"}:
                        break
                    time.sleep(.1)
                assert detail["status"] == "SUCCEEDED" and detail["result"]["sum"] == total and detail["result_version"] == version
                assert request("POST", route, body, 202)["run_id"] == accepted["run_id"]
                results.append(detail)
                bodies.append(body)
        stop()
        second = start(False)
        assert first == second, "Owned desktop backend must reopen the same saved origin"
        with httpx.Client(base_url=second, headers=headers, trust_env=False, timeout=5) as client:
            for detail, body in zip(results, bodies):
                rid = detail["id"]
                assert client.get(route + "/" + rid).json() == detail
                assert client.post(route, json=body).json()["run_id"] == rid
                assert client.get(route + "/" + rid).json() == detail
        stop()
        report.update(status="PASS", results=results, same_origin=True, original_keys_same_runs=True,
                      first_process_reopen_same_results=True, database="SYNTHETIC_SQLITE_TEST_ONLY")
    finally:
        if active is not None:
            stop()
        save()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
