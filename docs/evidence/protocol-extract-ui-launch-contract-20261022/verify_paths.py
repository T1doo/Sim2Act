"""Offline path/data checks, deliberately not Windows execution qualification."""
import hashlib
import importlib.util
import json
import re
import subprocess
import tempfile
import time
from pathlib import Path, PureWindowsPath

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
LOG = REPO / "docs/evidence/protocol-extract-ui-sparse-20261022/native-one-shot/job.log"
raw = LOG.read_bytes()
log = re.sub(r"\x1b\[[0-9;]*m", "", raw.decode("utf-8-sig"))
selected = re.search(r"  pythonLocation: (.+)", log).group(1).strip()
python = str(PureWindowsPath(selected) / "python.exe")
assert python in log and "WindowsApps\\python.exe" in log
assert '"started":false' in log and "system cannot find the file specified" in log
ps = (REPO / "scripts/WindowsExtractCompletionUI.ps1").read_text()
assert "Get-Command python" not in ps
assert "Join-Path $env:pythonLocation 'python.exe'" in ps
assert "[IO.Path]::IsPathFullyQualified($Python)" in ps
assert "[IO.Path]::GetFullPath($Python)" in ps
assert "[string]::IsNullOrWhiteSpace($env:pythonLocation)" in ps
assert "$env:pythonLocation -match '[\\r\\n]'" in ps

# Windows path algebra plus real Python UTF-8 JSON -> Node JSON/argv handoff.
# No fake SDK executables and no claim that Windows files exist on this host.
vectors = [selected, r"C:\Program Files\Python 3.12", r"D:\工具\Python"]
paths = [str(PureWindowsPath(value) / "python.exe") for value in vectors]
assert all(PureWindowsPath(value).is_absolute() for value in paths)
assert all(not PureWindowsPath(value).is_absolute() for value in ("", "relative", "C:relative"))
payload = dict(paths=paths, argv=[r"D:\a\Sim2Act\Sim2Act\scripts\protocol_completion_browser_ci.py", r"D:\a\临时 目录\sim2act-extract-ui-39740895401-1"], selected=python)
spec = importlib.util.spec_from_file_location("launch_helper", REPO / "scripts/protocol_completion_browser_ci.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
with tempfile.TemporaryDirectory(prefix="sim2act-launch-paths-") as directory:
    root = Path(directory)
    helper.write(root, "handoff.json", payload)
    encoded = subprocess.check_output(["node", "-e", "const fs=require('fs'),p=require('path').win32;const v=JSON.parse(fs.readFileSync(process.argv[1],'utf8'));for(const s of v.paths)if(!p.isAbsolute(s))throw Error(s);process.stdout.write(JSON.stringify(v));", str(root / "handoff.json")], timeout=5)
    assert json.loads(encoded) == payload
    # This Linux host must refuse the actual Windows tool contract before pip.
    try:
        helper.launch_paths(root, time.monotonic() + 5)
    except RuntimeError as error:
        assert str(error).startswith("Launch contract incomplete:")
    else:
        raise AssertionError("Unexpected Windows qualification on Linux")
    refusal = json.loads((root / "launch-contract.json").read_text())
    assert refusal["status"] == "FAIL"
    assert {"pwsh", "node", "npm_cmd", "git", "selected_python"} <= {item["path"] for item in refusal["errors"]}
    files = [name for name in refusal["paths"] if name not in {"python", "pwsh", "node", "npm_cmd", "npm_cli", "git"}]
    assert len(files) == 23
    workflow = (REPO / ".github/workflows/windows-native-mock.yml").read_text()
    patterns = re.findall(r"^\s+(/[^\s]+)$", workflow, re.M)
    assert len(patterns) == 19
    for name in files:
        assert any(name == pattern[1:] or (pattern.endswith("/") and name.startswith(pattern[1:])) for pattern in patterns), name

report = dict(status="PASS_OFFLINE_ONLY", failed_run=39740895401, failure_log_sha256=hashlib.sha256(raw).hexdigest(), selected_python=python, path_vectors=payload, required_files=len(files), sparse_patterns=len(patterns), linux_expected_refusal=refusal["errors"], new_mock=0, business_http=0, browser_started=False, unverified=["PowerShell/.NET execution and Windows argv", "actual runner npm/tool layout", "Windows sidecar lock", "protected Edge DOM and cleanup handles"])
report["source_sha256"] = {name: hashlib.sha256((REPO / name).read_bytes()).hexdigest() for name in ("scripts/WindowsExtractCompletionUI.ps1", "scripts/OwnedBrowserSetup.ps1", "scripts/protocol_completion_browser_ci.py", "scripts/browser-ci/extract-completion.cjs", ".github/workflows/windows-native-mock.yml")}
(HERE / "offline.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({key: report[key] for key in ("status", "required_files", "sparse_patterns", "browser_started")}))
