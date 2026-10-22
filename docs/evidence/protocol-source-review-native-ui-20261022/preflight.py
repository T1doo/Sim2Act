"""Offline sparse/file contract only. No browser, SDK, application or model run."""

import gzip
import hashlib
import importlib.util
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[3]


def main():
    spec = importlib.util.spec_from_file_location(
        "source_ui_helper", REPO / "scripts/protocol_completion_browser_ci.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    workflow = (REPO / ".github/workflows/windows-native-mock.yml").read_text()
    block = workflow.split("sparse-checkout: |", 1)[1].split("      - uses:", 1)[0]
    patterns = [line.strip().lstrip("/") for line in block.splitlines() if line.strip()]
    tracked = subprocess.check_output(["git", "ls-files"], cwd=REPO, text=True).splitlines()
    selected = [
        name
        for name in tracked
        if any(name.startswith(p) if p.endswith("/") else name == p for p in patterns)
    ]
    assert "run: ./scripts/WindowsExtractCompletionUI.ps1 -SourceReview" in workflow
    assert "[source-review-ui-once-20261022]" in workflow
    assert not any("protocol-extract-process-recovery" in p for p in patterns)
    with tempfile.TemporaryDirectory(prefix="sim-source-ui-layout-") as temporary:
        root = Path(temporary)
        checkout = root / "checkout"
        checkout.mkdir()
        for name in selected:
            target = checkout / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / name, target)
        tools = root / "tool-paths"
        tools.mkdir()
        # These are file-layout witnesses, never executable substitutes.
        for name in (
            "python.exe",
            "pwsh.exe",
            "node.exe",
            "npm.cmd",
            "git.exe",
            "node_modules/npm/bin/npm-cli.js",
        ):
            file = tools / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b"")
        output = root / "output"
        output.mkdir()
        with (
            patch.object(helper, "REPO", checkout),
            patch.object(sys, "executable", str(tools / "python.exe")),
            patch.object(helper.shutil, "which", side_effect=lambda name: str(tools / name)),
            patch.dict(helper.os.environ, {"pythonLocation": str(tools)}),
        ):
            paths = helper.launch_paths(output, time.monotonic() + 10, "source", review=True)
            assert not any("protocol-extract-process-recovery" in key for key in paths)
            assert all(
                (checkout / name).is_file()
                for name in paths
                if name.startswith(("src/", "scripts/", "docs/"))
            )
            try:
                helper.launch_paths(output, time.monotonic() + 10, "unknown")
            except ValueError:
                pass
            else:
                raise AssertionError("Unknown phase was accepted")
        evidence = checkout / "docs/evidence/protocol-source-process-recovery-20261022"
        original = json.loads((evidence / "original.json").read_text())
        database = root / "after.sqlite"
        with gzip.open(evidence / "after.sqlite.gz", "rb") as src, database.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        with sqlite3.connect(
            "file:" + str(database) + "?mode=ro&immutable=1", uri=True
        ) as connection:
            connection.execute("PRAGMA query_only=ON")
            jobs = connection.execute(
                "SELECT run_id, accepted_snapshot FROM protocol_jobs"
            ).fetchall()
            assert len(jobs) == 1 and jobs[0][0] == original["run"]
            assert json.loads(jobs[0][1])["phase"] == "source"
            assert len(connection.execute(
                "SELECT id FROM events WHERE run_id=? AND kind='PROTOCOL_COMPLETED'",
                (original["run"],),
            ).fetchall()) == 1
            assert connection.execute("SELECT status, version, fence FROM runs WHERE id=?", (original["run"],)).fetchone() == ("WAITING_APPROVAL", 2, 2)
            assert connection.execute("SELECT count(*) FROM protocol_reviews").fetchone() == (0,)
            assert connection.total_changes == 0
        assert (
            hashlib.sha256((evidence / "original-received-sidecar.json").read_bytes()).hexdigest()
            == original["sidecar_sha256"]
        )
    print(
        json.dumps(
            dict(
                status="PASS",
                selected_files=len(selected),
                sparse_patterns=len(patterns),
                qualified_path_entries=len(paths),
                phase="source",
                action="review",
                fixture_state="WAITING_APPROVAL/v2/f2, completed, no review",
                fixture_protocol_runs=1,
                other_run_required=False,
                unknown_phase_rejected=True,
                model_requests=0,
                application_requests=0,
                browser="NOT_RUN",
                powershell="NOT_AVAILABLE_LOCAL_NOT_QUALIFIED",
                scope="offline file paths/sparse closure/read-only sealed SQLite, not Windows or native DOM",
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
