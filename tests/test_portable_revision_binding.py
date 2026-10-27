"""Local byte assembly only; never executes Windows or starts a service."""

import hashlib
import importlib.util
import io
import json
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "portable_revision_builder", ROOT / "scripts/package_windows_portable.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
COMMIT = "c" * 40
META = {"sim2act-0.1.0.dist-info/" + name: b"synthetic packaging test metadata"
        for name in ("METADATA", "RECORD", "WHEEL", "entry_points.txt", "top_level.txt")}


def record(data):
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def archive(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as bundle:
        for name, data in files.items():
            bundle.writestr(name, data)
    return output.getvalue()


@pytest.fixture
def candidate(tmp_path):
    files = {"sim2act/__init__.py": b"", "sim2act/web/index.html": b"<p>synthetic</p>",
             "sim2act/web/app.js": b"void 0;"}
    wheel = tmp_path / "sim2act-0.1.0-py3-none-any.whl"
    wheel.write_bytes(archive({**files, **META}))
    manifest = tmp_path / "candidate-manifest.json"
    data = dict(format="sim2act-local-candidate.v1", source_commit=COMMIT,
                mode="SYNTHETIC_MOCK_DEMO", python="3.12",
                files={"src/" + name: record(value) for name, value in files.items()})
    data["files"]["wheels/" + wheel.name] = record(wheel.read_bytes())
    manifest.write_text(json.dumps(data))
    return wheel, manifest, data, files


def test_current_wheel_requires_manifest_and_matching_commit(candidate):
    wheel, manifest, _, _ = candidate
    with pytest.raises(ValueError, match="exact candidate manifest required"):
        builder.checked_app(wheel, dict(product_commit=COMMIT))
    with pytest.raises(ValueError, match="source binding mismatch"):
        builder.checked_app(wheel, dict(product_commit="d" * 40), manifest)
    value, proof = builder.checked_app(wheel, dict(product_commit=COMMIT), manifest)
    assert value == wheel.read_bytes() and proof == record(manifest.read_bytes())["sha256"]


def test_wheel_digest_cannot_be_replaced_by_matching_source_names(candidate):
    wheel, manifest, _, _ = candidate
    wheel.write_bytes(wheel.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="Frozen input mismatch"):
        builder.checked_app(wheel, dict(product_commit=COMMIT), manifest)


@pytest.mark.parametrize("change", ["modified", "missing", "extra", "duplicate"])
def test_rebuilt_wheel_still_requires_all_source_bytes(candidate, change):
    wheel, manifest, data, files = candidate
    entries = {**files, **META}
    if change == "modified":
        entries["sim2act/web/app.js"] = b"different source"
    elif change == "missing":
        del entries["sim2act/web/index.html"]
    elif change == "extra":
        entries["sim2act/untracked.py"] = b"untracked"
    value = archive(entries)
    if change == "duplicate":
        out = io.BytesIO(value)
        with zipfile.ZipFile(out, "a") as z, pytest.warns(UserWarning):
            z.writestr("sim2act/__init__.py", b"")
        value = out.getvalue()
    wheel.write_bytes(value)
    # Even replacing the outer wheel digest cannot hide a source mismatch.
    data["files"]["wheels/" + wheel.name] = record(value)
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="source (bytes|inventory) mismatch"):
        builder.checked_app(wheel, dict(product_commit=COMMIT), manifest)


def test_full_local_assembly_binds_revision_and_preserves_existing_output(candidate, tmp_path):
    wheel, manifest, _, _ = candidate
    assets = tmp_path / "assets"
    assets.mkdir()
    runtime = archive({"python.exe": b"not executable: synthetic fixture",
                       "LICENSE.txt": b"synthetic license fixture"})
    runtime_file = assets / "runtime.zip"
    runtime_file.write_bytes(runtime)
    inputs = tmp_path / "inputs.json"
    inputs.write_text(json.dumps(dict(product_commit=COMMIT, wheels=[], python={
        **record(runtime), "filename": runtime_file.name, "version": "3.12.10"})))
    output = tmp_path / "preview.zip"
    result = builder.build(inputs, assets, wheel, output, candidate_manifest=manifest)
    assert result["product_commit"] == COMMIT and result["windows_execution"] == "NOT_RUN"
    with zipfile.ZipFile(output) as z:
        m = json.loads(z.read("Sim2Act-preview/portable-manifest.json"))
        assert m["status"] == "BUILT_NOT_WINDOWS_EXECUTED"
        assert m["app_candidate_manifest_sha256"] == record(manifest.read_bytes())["sha256"]
        for name, expected in m["files"].items():
            assert record(z.read("Sim2Act-preview/" + name)) == expected
    previous = output.read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        builder.build(inputs, assets, wheel, output, candidate_manifest=manifest)
    assert output.read_bytes() == previous


def test_source_mismatch_leaves_no_output(candidate, tmp_path):
    wheel, manifest, _, _ = candidate
    inputs = tmp_path / "inputs.json"
    inputs.write_text(json.dumps(dict(product_commit="d" * 40)))
    output = tmp_path / "not-created.zip"
    with pytest.raises(ValueError, match="source binding mismatch"):
        builder.build(inputs, tmp_path / "missing-assets", wheel, output,
                      candidate_manifest=manifest)
    assert not output.exists()
