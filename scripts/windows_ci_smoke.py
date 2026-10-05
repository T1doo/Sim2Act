"""Native Windows Server engineering smoke; no OS substitution or external model client."""

import json
import os
import secrets
import socket
import subprocess
import time
from pathlib import Path

import httpx
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from sim2act.config import Settings
from sim2act.db import Store


def main():
    if os.name != "nt" or os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit("Actual native Windows runner required")
    root = Path(__file__).resolve().parents[1]
    config = os.environ["SIM2ACT_CI_CONFIG"]
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    def powershell(script, *, with_port=False):
        args = ["pwsh", "-NoProfile", "-File", str(root / "scripts" / script), "-Config", config]
        if with_port:
            args += ["-Port", str(port)]
        result = subprocess.run(
            args, cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=40
        )
        if result.returncode:
            # The runner masks generated DB credentials; never print full environment or config.
            raise RuntimeError(script + " failed: " + result.stdout + result.stderr)
        return result.stdout

    # Load only the job-created explicit file; no user dotenv discovery.
    for line in Path(config).read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ[key] = value
    settings = Settings.from_env()
    assert settings.mode == "mock" and not settings.live_enabled and not settings.token
    store = Store(settings.database_url)
    with store.engine.connect() as c:
        row = c.execute(
            text(
                "SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname=current_user"
            )
        ).one()
        assert not any(row)
    try:
        with store.engine.begin() as c:
            c.execute(text("CREATE TABLE public.ci_must_be_denied (id integer)"))
    except DBAPIError as error:
        assert getattr(error.orig, "sqlstate", None) == "42501"
    else:
        raise AssertionError("Application role unexpectedly has DDL")
    bearer = secrets.token_urlsafe(32)  # Private temporary local identity, never printed.
    store.user("SYNTHETIC Windows Server CI", bearer)
    base = f"http://127.0.0.1:{port}"
    try:
        doctor = json.loads(powershell("Doctor.ps1"))
        assert doctor["database"] == "UP" and doctor["mode"] == "MOCK"
        started = json.loads(powershell("Start.ps1", with_port=True))
        assert len({p["pid"] for p in started["processes"]}) == 2
        status = json.loads(powershell("Status.ps1", with_port=True))
        assert status["health"]["worker"] == "UP"
        with httpx.Client(base_url=base, headers={"Authorization": "Bearer " + bearer}) as client:
            project = client.post("/api/projects", json={"name": "中文 空格 CI"})
            assert project.status_code == 201
            pid = project.json()["id"]
            resource = client.post(
                f"/api/projects/{pid}/resources",
                json={"name": "value.txt", "format": "txt", "content": "42"},
            )
            assert resource.status_code == 200
            request = {
                "goal": "read synthetic value",
                "resource_refs": [resource.json()["id"]],
                "request_key": "windows-smoke",
            }
            accepted = client.post(f"/api/projects/{pid}/runs", json=request)
            assert accepted.status_code == 202
            rid = accepted.json()["run_id"]
            assert client.post(f"/api/projects/{pid}/runs", json=request).json()["run_id"] == rid
            for _ in range(60):
                result = client.get(f"/api/runs/{rid}").json()
                if result["status"] == "PARTIAL":
                    break
                time.sleep(0.25)
            assert result["status"] == "PARTIAL", result["status"]
            assert result["result"]["mode"] == "MOCK"
            assert result["result"]["receipts"][0]["data"]["content"] == "42"
            assert result["result"]["goal_acceptance"] == "NOT_RUN"
        powershell("Stop.ps1")
        assert json.loads(powershell("Status.ps1", with_port=True))["health"] == "OFFLINE"
        powershell("Start.ps1", with_port=True)
        with httpx.Client(base_url=base, headers={"Authorization": "Bearer " + bearer}) as client:
            assert client.get(f"/api/runs/{rid}").json()["result"] == result["result"]
        summary = "PASS: native PowerShell Doctor/Start/Status/Stop; separate API-worker; runtime DDL denied; accepted/idempotent/verified42; restart persistence; Chinese spaced data directory. Win11 acceptance NOT_RUN."
        print(summary)
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as f:
            f.write("\n" + summary + "\n")
    finally:
        powershell("Stop.ps1")
        store.engine.dispose()


if __name__ == "__main__":
    main()
