"""Output protocol byte compatibility and fail-closed existing fixture Worker guard."""

import ast
import base64
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest


def load_emit(source):
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)
                and n.name == "emit")
    namespace = {"base64": base64, "hashlib": hashlib, "json": json}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "emit-only", "exec"), namespace)
    return namespace["emit"]


def test_buffered_emission_preserves_every_line_and_bound(tmp_path):
    # Independent original line protocol, self-contained for depth-one CI checkout.
    def before(root):
        names = ["browser-results.json", "desktop.png", "mobile.png", "failure.png",
                 "agent-results.json", "agent-desktop.png", "agent-narrow.png", "agent-failure.png",
                 "protocol-results.json", "protocol-desktop.png", "protocol-narrow.png"]
        for name in names:
            target = root / ("protocol" if name.startswith("protocol-") else "") / name
            if not target.exists():
                continue
            data = target.read_bytes()
            assert len(data) <= 2_000_000
            encoded = base64.b64encode(data).decode()
            chunks = [encoded[n:n + 4000] for n in range(0, len(encoded), 4000)]
            print("SIM2ACT_BROWSER_FILE " + json.dumps({"name": name, "bytes": len(data),
                  "sha256": hashlib.sha256(data).hexdigest(), "chunks": len(chunks)}))
            for index, chunk in enumerate(chunks):
                print(f"SIM2ACT_BROWSER_CHUNK {name} {index} {chunk}")
    after = load_emit(Path("scripts/windows_browser_ci.py").read_text())
    (tmp_path / "protocol").mkdir()
    for name in ["browser-results.json", "desktop.png", "failure.png",
                 "protocol/protocol-results.json", "protocol/protocol-narrow.png"]:
        (tmp_path / name).write_bytes(bytes(range(256)) * 200)
    (tmp_path / "secret-not-allowed.json").write_text("must not emit")
    outputs = []
    for emit in [before, after]:
        out = io.StringIO()
        with redirect_stdout(out):
            emit(tmp_path)
        outputs.append(out.getvalue())
    assert outputs[0] == outputs[1] and "secret-not-allowed" not in outputs[1]
    (tmp_path / "desktop.png").write_bytes(b"x" * 2_000_001)
    for emit in [before, after]:
        with redirect_stdout(io.StringIO()), pytest.raises(AssertionError):
            emit(tmp_path)


def test_owned_worker_without_queued_run_refuses_without_preparation(tmp_path):
    subprocess.run([sys.executable, "scripts/protocol-ui/fixture.py", "--root", str(tmp_path),
                    "--port", "12345", "--action", "seed"], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    sys.path.insert(0, str(Path("scripts/conditional-ui").resolve()))
    spec = importlib.util.spec_from_file_location("owned_native_control", "scripts/conditional-ui/fixture.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    before = fixture.action(tmp_path, "snapshot")
    with pytest.raises(ValueError, match="oldest queued Run"):
        fixture.action(tmp_path, "run-source")
    assert fixture.action(tmp_path, "snapshot") == before


@pytest.mark.parametrize("mode", ["missing-root", "wrong-owner", "no-queued"])
def test_optimized_run_control_refuses_invalid_owned_context(tmp_path, mode):
    if mode != "missing-root":
        subprocess.run([sys.executable, "scripts/protocol-ui/fixture.py", "--root", str(tmp_path),
                        "--port", "12345", "--action", "seed"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        if mode == "wrong-owner":
            info = json.loads((tmp_path / "info.json").read_text())
            info["bearer"] = "synthetic-unrelated"
            (tmp_path / "info.json").write_text(json.dumps(info))
    out = subprocess.run([sys.executable, "-O", "scripts/conditional-ui/fixture.py", "--root",
                          str(tmp_path), "--session"], input='{"action":"run-source"}\n',
                         text=True, capture_output=True, timeout=10)
    assert out.returncode != 0 and out.stdout == ""
