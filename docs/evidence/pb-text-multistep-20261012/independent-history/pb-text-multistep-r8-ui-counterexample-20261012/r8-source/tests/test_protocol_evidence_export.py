"""Only the closed synthetic protocol evidence set may leave the owned CI root."""
import base64
import importlib.util
import json
from pathlib import Path


def test_exact_protocol_outputs_emitted_without_private_files(tmp_path, capsys):
    spec = importlib.util.spec_from_file_location("native_export", Path(__file__).parents[1] / "scripts/windows_browser_ci.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    folder = tmp_path / "protocol"
    folder.mkdir()
    names = ["protocol-results.json", "protocol-desktop.png", "protocol-narrow.png"]
    for name in names:
        (folder / name).write_bytes(b"synthetic pixels")
    (folder / "info.json").write_text("private fixture")
    (folder / "fixture.db").write_text("private database")
    module.emit(tmp_path)
    lines = capsys.readouterr().out.splitlines()
    manifests = [json.loads(line.split(" ", 1)[1]) for line in lines if line.startswith("SIM2ACT_BROWSER_FILE ")]
    assert {x["name"] for x in manifests} == set(names)
    chunks = [line.split(" ", 3)[3] for line in lines if line.startswith("SIM2ACT_BROWSER_CHUNK ")]
    assert all(base64.b64decode(x) == b"synthetic pixels" for x in chunks)
    assert "info.json" not in str(manifests) and "fixture.db" not in str(manifests)
