import importlib.util
import io
import json
import zipfile
from pathlib import Path

import pytest


def load(name):
    p = Path(__file__).resolve().parents[1] / "scripts" / (name + ".py")
    s = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


h = load("candidate_wheel")
builder = load("package_windows_portable")
META = {
    h.META_PREFIX + n: b"synthetic metadata"
    for n in ("METADATA", "RECORD", "entry_points.txt", "top_level.txt")
}


def archive(source, tag, pure, natives=None):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name, value in {
            **source,
            **META,
            h.META_PREFIX
            + "WHEEL": f"Wheel-Version: 1.0\nRoot-Is-Purelib: {str(pure).lower()}\nTag: {tag}\n".encode(),
            **(natives or {}),
        }.items():
            z.writestr(name, value)
    return out.getvalue()


def make(tmp_path, tag="cp312-cp312-win_amd64"):
    suffix = ".cp312-win_amd64.pyd" if "win" in tag else ".cpython-312-x86_64-linux-gnu.so"
    source = {
        "sim2act/__init__.py": b"",
        **{
            "sim2act/" + n: b"synthetic C source"
            for n in (
                "_raw_snapshot.c",
                "_cold_graph_structure.c",
                "_cold_row_native_impl.c",
                "_cold_typed_native_impl.c",
            )
        },
    }
    native = {
        "sim2act/" + n + suffix: b"not executed: synthetic compiled bytes " + n.encode()
        for n in h.MODULES
    }
    data = archive(source, tag, False, native)
    wheel = tmp_path / ("sim2act-0.1.0-" + tag + ".whl")
    wheel.write_bytes(data)
    profile = h.wheel_profile(wheel.name, data)
    record = dict(
        format="sim2act-local-candidate.v1",
        source_commit="c" * 40,
        python="3.12",
        mode="SYNTHETIC_MOCK_DEMO",
        artifact_profile="native-candidate.v1",
        wheel_profile=profile,
        files={
            **{"src/" + k: h.record(v) for k, v in source.items()},
            "wheels/" + wheel.name: h.record(data),
        },
    )
    manifest = tmp_path / "candidate-manifest.json"
    manifest.write_text(json.dumps(record))
    return wheel, manifest, record, source, native


def test_native_windows_complete_c_and_native_inventory(tmp_path):
    wheel, manifest, m, source, native = make(tmp_path)
    actual, _ = builder.checked_app(wheel, dict(product_commit="c" * 40), manifest)
    assert actual == wheel.read_bytes()


@pytest.mark.parametrize(
    "change", ["missing_c", "missing_native", "native_sha", "unknown_pyd", "linux_so", "tag", "root", "duplicate"]
)
def test_malformed_native_candidate_refuses_before_output(tmp_path, change):
    wheel, manifest, m, source, native = make(tmp_path)
    if change == "missing_c":
        del source["sim2act/_cold_typed_native_impl.c"]
    elif change == "native_sha":
        m["wheel_profile"]["native_artifacts"][next(iter(native))]["sha256"] = "0" * 64
    elif change == "missing_native":
        native.pop("sim2act/_cold_typed_cohort.cp312-win_amd64.pyd")
    elif change == "unknown_pyd":
        native["sim2act/unlisted.cp312-win_amd64.pyd"] = b"unknown"
    elif change == "linux_so":
        native["sim2act/_raw_snapshot.cpython-312-x86_64-linux-gnu.so"] = b"wrong target"
    data = archive(
        source,
        "py3-none-any" if change == "tag" else "cp312-cp312-win_amd64",
        change == "root",
        native,
    )
    if change == "duplicate":
        out = io.BytesIO(data)
        with zipfile.ZipFile(out, "a") as z, pytest.warns(UserWarning):
            z.writestr("sim2act/__init__.py", b"")
        data = out.getvalue()
    wheel.write_bytes(data)
    if change == "missing_native":
        m["wheel_profile"] = h.wheel_profile(wheel.name, data)
    m["files"]["wheels/" + wheel.name] = h.record(data)
    manifest.write_text(json.dumps(m))
    output = tmp_path / "absent.zip"
    inputs = tmp_path / "inputs.json"
    inputs.write_text(json.dumps(dict(product_commit="c" * 40)))
    with pytest.raises(ValueError):
        builder.build(inputs, tmp_path / "missing", wheel, output, candidate_manifest=manifest)
    assert not output.exists()


def test_linux_wheel_cannot_be_assembled_for_windows(tmp_path):
    wheel, manifest, *_ = make(tmp_path, "cp312-cp312-linux_x86_64")
    with pytest.raises(ValueError, match="target platform"):
        builder.checked_app(wheel, dict(product_commit="c" * 40), manifest)


def test_local_builder_keeps_setup_c_sources_and_forbids_downloads(tmp_path, monkeypatch):
    local = load("package_local_candidate")
    repository = tmp_path / "repo"
    (repository / "scripts").mkdir(parents=True)
    helper_bytes = (Path(__file__).resolve().parents[1] / "scripts/candidate_wheel.py").read_bytes()
    (repository / "scripts/candidate_wheel.py").write_bytes(helper_bytes)
    source = {
        "src/sim2act/__init__.py": b"",
        **{
            "src/sim2act/" + name: b"synthetic C source"
            for name in (
                "_raw_snapshot.c",
                "_cold_graph_structure.c",
                "_cold_row_native_impl.c",
                "_cold_typed_native_impl.c",
            )
        },
    }
    blobs = {name: b"synthetic packaging input" for name in local.FILES}
    blobs.update(source)
    blobs["scripts/candidate_wheel.py"] = helper_bytes
    commit = "e" * 40

    def git(*args):
        if args[0] == "status":
            return b""
        if args[0] == "rev-parse":
            return (commit + "\n").encode()
        if args[:3] == ("ls-tree", "-r", "--name-only"):
            return ("\n".join(source) + "\n").encode()
        if args[0] == "ls-tree":
            return ("100644 blob " + "0" * 40 + "\t" + args[-1] + "\n").encode()
        if args[0] == "show" and "-s" in args:
            return b"1793180000\n"
        if args[0] == "show":
            return blobs[args[1].split(":", 1)[1]]
        raise AssertionError(args)

    def built(command, cwd, env, **kwargs):
        assert all(flag in command for flag in ("--no-index", "--no-build-isolation", "--no-deps"))
        assert (Path(cwd) / "setup.py").read_bytes() == blobs["setup.py"]
        assert all((Path(cwd) / name).read_bytes() == value for name, value in source.items())
        natives = {
            "sim2act/" + name + ".cpython-312-x86_64-linux-gnu.so": b"synthetic native"
            for name in h.MODULES
        }
        data = archive(
            {name[4:]: value for name, value in source.items()},
            "cp312-cp312-linux_x86_64",
            False,
            natives,
        )
        output = Path(command[command.index("--wheel-dir") + 1])
        (output / "sim2act-0.1.0-cp312-cp312-linux_x86_64.whl").write_bytes(data)
        from types import SimpleNamespace

        return SimpleNamespace(returncode=0, stdout=b"synthetic no-download build")

    monkeypatch.setattr(local, "ROOT", repository)
    monkeypatch.setattr(local, "git", git)
    monkeypatch.setattr(local.subprocess, "run", built)
    monkeypatch.setattr(local.importlib.metadata, "version", lambda name: "82.0.1")
    monkeypatch.setattr(
        local.sys, "argv", ["package_local_candidate.py", "--output", str(tmp_path / "out")]
    )
    local.main()
    manifest = json.loads((tmp_path / "out/candidate-manifest.json").read_text())
    assert "setup.py" in manifest["files"]
    assert manifest["artifact_profile"] == "native-candidate.v1"
    assert len(manifest["wheel_profile"]["native_artifacts"]) == 4


def test_native_allowlist_covers_every_declared_setup_extension():
    import ast
    tree=ast.parse((Path(__file__).resolve().parents[1]/'setup.py').read_bytes())
    names={n.args[0].value.removeprefix('sim2act.') for n in ast.walk(tree)
           if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='Extension'}
    assert set(h.MODULES)==names


def test_python_preview_profile_rejects_native_wheel(tmp_path):
    wheel, manifest, data, _, _ = make(tmp_path)
    data["artifact_profile"] = "python-preview.v1"
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="pure py3-none-any"):
        builder.checked_app(wheel, dict(product_commit="c" * 40), manifest)


def test_explicit_python_preview_with_complete_c_sources_is_portable(tmp_path):
    _, manifest, data, source, _ = make(tmp_path)
    payload = archive(source, "py3-none-any", True)
    wheel = tmp_path / "sim2act-0.1.0-py3-none-any.whl"
    wheel.write_bytes(payload)
    data["artifact_profile"] = "python-preview.v1"
    data["wheel_profile"] = h.wheel_profile(wheel.name, payload)
    data["files"]["wheels/" + wheel.name] = h.record(payload)
    manifest.write_text(json.dumps(data))
    assert builder.checked_app(wheel, dict(product_commit="c" * 40), manifest)[0] == payload
