"""Assemble an offline Windows SQLite preview; no target-side installation.

Inputs are already downloaded official, hash-pinned archives. This builder
never downloads, compiles, executes Windows code or loads private settings.
"""

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path, PurePosixPath


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_asset(path, expected):
    data = path.read_bytes()
    if len(data) != expected["bytes"] or digest(data) != expected["sha256"]:
        raise ValueError("Frozen input mismatch: " + path.name)
    return data


def merge_archive(files, data, prefix):
    import io

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for member in archive.infolist():
            name = PurePosixPath(member.filename)
            if (
                name.is_absolute()
                or ".." in name.parts
                or "\\" in member.filename
                or ":" in member.filename
                or (member.external_attr >> 16) & 0o170000 == 0o120000
            ):
                raise ValueError("Unsafe archive entry")
            if member.is_dir():
                continue
            target = prefix + member.filename
            if target in files:
                raise ValueError("Overlapping archive member: " + target)
            files[target] = archive.read(member)


def checked_app(app_wheel, specification, candidate_manifest=None):
    """Bind a new application to its exact source candidate, never a relabel.

    This is a local assembly integrity check, not software/production authority.
    Keep the historical fixed-wheel route for the original frozen package.
    """
    if candidate_manifest is None:
        data = app_wheel.read_bytes()
        if (
            specification["product_commit"] != "7794748c78041682c82f0e7fda239d2601dc91b5"
            or digest(data) != "29c344e4d5931a2b8c9a97fb1d1ae222356bbbd6a2b58a928f960fb443f0aad5"
        ):
            raise ValueError("Unreviewed app wheel; exact candidate manifest required")
        return data, None
    record_bytes = candidate_manifest.read_bytes()
    candidate = json.loads(record_bytes)
    commit = candidate.get("source_commit")
    if (
        candidate.get("format") != "sim2act-local-candidate.v1"
        or type(commit) is not str
        or re.fullmatch(r"[0-9a-f]{40}", commit) is None
        or commit != specification["product_commit"]
        or candidate.get("mode") != "SYNTHETIC_MOCK_DEMO"
        or candidate.get("python") != "3.12"
        or type(candidate.get("files")) is not dict
    ):
        raise ValueError("App candidate source binding mismatch")
    records = candidate["files"]
    wheel_record = records.get("wheels/" + app_wheel.name)
    if type(wheel_record) is not dict:
        raise ValueError("App candidate wheel record missing")
    data = read_asset(app_wheel, wheel_record)
    # A profile is byte assembly integrity, never production/Windows authority.
    import importlib.util

    helper = importlib.util.spec_from_file_location(
        "candidate_wheel", Path(__file__).with_name("candidate_wheel.py")
    )
    wheel_tools = importlib.util.module_from_spec(helper)
    helper.loader.exec_module(wheel_tools)
    profile = wheel_tools.wheel_profile(app_wheel.name, data, target="windows")
    kind = candidate.get("artifact_profile")
    if kind is None:
        # Historical pure preview manifests predate qualified C package-data.
        omitted = {"src/sim2act/_cold_row_native_impl.c", "src/sim2act/_cold_typed_native_impl.c"}
        if profile["native_artifacts"]:
            raise ValueError("Historical manifest cannot qualify native artifacts")
    elif kind in ("native-candidate.v1", "python-preview.v1"):
        omitted = set()
        if candidate.get("wheel_profile") != profile:
            raise ValueError("Candidate native/wheel metadata mismatch")
        if kind == "python-preview.v1" and (
            profile["tags"] != ["py3-none-any"]
            or not profile["root_is_purelib"]
            or profile["native_artifacts"]
        ):
            raise ValueError("Python preview requires a pure py3-none-any wheel")
        if kind == "native-candidate.v1" and len(profile["native_artifacts"]) != 2:
            raise ValueError("Native candidate requires both compiled extensions")
    else:
        raise ValueError("Unknown candidate artifact profile")
    source = {
        name[4:]: value
        for name, value in records.items()
        if name.startswith("src/sim2act/") and name not in omitted
    }
    wheel_tools.verify_source(data, source, profile)
    return data, digest(record_bytes)


def checked_desktop_inputs(candidate_manifest):
    if candidate_manifest is None:
        raise ValueError("Native host stage requires an exact current candidate manifest")
    records = json.loads(candidate_manifest.read_bytes())["files"]
    root = Path(__file__).resolve().parents[1]
    names = ["scripts/portable_desktop.py", "scripts/package_windows_portable.py", "docs/PreviewRelease.md"]
    names += ["scripts/windows/" + name for name in ("Sim2ActDesktop.cs", "Build-Desktop.ps1", "desktop.manifest", "README.md")]
    result = {}
    for name in names:
        if type(records.get(name)) is not dict:
            raise ValueError("Native host candidate input missing: " + name)
        result[name] = read_asset(root / name, records[name])
    return result


def build(inputs, assets, app_wheel, output, *, candidate_manifest=None):
    if output.exists():
        raise ValueError("Output already exists; do not overwrite a candidate")
    specification = json.loads(inputs.read_text(encoding="utf-8"))
    # Complete app/version qualification before reading or assembling runtime
    # archives. A mismatch cannot produce a partially relabelled output.
    app, candidate_digest = checked_app(app_wheel, specification, candidate_manifest)
    desktop_inputs = checked_desktop_inputs(candidate_manifest)
    files = {}
    runtime = specification["python"]
    merge_archive(files, read_asset(assets / runtime["filename"], runtime), "runtime/")
    selected = []
    # PG drivers are not reachable from the explicit SQLite-only preview.
    # Do not distribute a dormant LGPL driver/bundled libpq without its full
    # source/relinking obligations, or pretend this is a production PG package.
    for wheel in specification["wheels"]:
        if wheel["name"].replace("_", "-") in ("psycopg", "psycopg-binary"):
            continue
        merge_archive(
            files,
            read_asset(assets / "runtime-wheels" / wheel["filename"], wheel),
            "runtime/Lib/site-packages/",
        )
        selected.append(
            {
                key: wheel[key]
                for key in (
                    "name",
                    "version",
                    "url",
                    "sha256",
                    "license",
                    "license_expression",
                    "source_distribution_urls",
                )
            }
        )
    merge_archive(files, app, "runtime/Lib/site-packages/")
    files["runtime/python312._pth"] = b"python312.zip\n.\nLib\\site-packages\nimport site\n"
    files["runtime/LOCAL-CHANGES.txt"] = (
        b"Only python312._pth adds private Lib/site-packages. Binaries and packages are unchanged.\n"
        b"This isolated synthetic SQLite preview omits PostgreSQL drivers.\n"
    )
    files["desktop.py"] = desktop_inputs["scripts/portable_desktop.py"]
    files["使用说明.md"] = desktop_inputs["docs/PreviewRelease.md"]
    # Native desktop is the product entry. Browser access is explicit developer preview.
    for name in ("Sim2ActDesktop.cs", "Build-Desktop.ps1", "desktop.manifest", "README.md"):
        files["desktop-build/" + name] = desktop_inputs["scripts/windows/" + name]
    files["Start-Sim2Act.cmd"] = (
        '@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\n'
        'if not exist "%~dp0Sim2Act.exe" (echo Native desktop build required. See desktop-build/README.md & exit /b 1)\r\n'
        '"%~dp0Sim2Act.exe"\r\nexit /b %ERRORLEVEL%\r\n'
    ).encode("ascii")
    files["Developer-Browser-Preview.cmd"] = (
        '@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\n'
        '"%~dp0runtime\\python.exe" -I -B -X utf8 "%~dp0desktop.py" --browser-preview\r\n'
        'exit /b %ERRORLEVEL%\r\n'
    ).encode("ascii")
    files["READ-ME-FIRST.txt"] = (
        "Sim2Act Windows x64 - NATIVE DESKTOP BUILD INPUT\n\n"
        "This assembled stage needs the pinned application WebView2 SDK and existing C# compiler.\n"
        "See desktop-build/README.md. Build in this new candidate folder; do not reuse an old EXE.\n"
        "After building, Sim2Act.exe owns its independent window and taskbar entry.\n"
        "No Chrome/Edge browser fallback and no system runtime installation.\n"
        "Existing Windows x64, .NET Framework 4.6.2+ and WebView2 Runtime are required.\n"
        "Do not bypass SmartScreen/signature/security refusals or install missing system components.\n"
        "The native view loads only after actual API/Worker READY. Close the window to stop its own backend.\n"
        "Data, WebView profile, temp, exports and logs stay in this ordinary application folder.\n"
        "An unconfirmed exit retains data/claim/logs; do not delete a running claim or reset the database.\n"
        "Synthetic login: public-synthetic-blank-workspace. Use non-sensitive synthetic data only.\n"
        "This local SQLite workspace is not formal PG/live-model acceptance.\n"
        "Windows/Defender OS traces outside this folder cannot be promised absent.\n"
        "Developer-Browser-Preview.cmd is an explicit development aid, not the product entry.\n"
        "Bundled Python 3.12.10 is superseded; engineering candidate, not long-term deployment.\n"
        "Exact archive/license/source records remain in THIRD-PARTY-SOURCES.json and runtime notices.\n"
    ).encode("utf-8")
    files["THIRD-PARTY-SOURCES.json"] = (
        json.dumps(dict(python=runtime, wheels=selected), indent=2) + "\n"
    ).encode()
    manifest = dict(
        format="sim2act-offline-windows-sqlite-preview.v1",
        product_commit=specification["product_commit"],
        python=runtime["version"],
        status="NATIVE_HOST_BUILD_REQUIRED_NOT_WINDOWS_EXECUTED",
        desktop_entry="Sim2Act.exe",
        installed_runtime_wheels=len(selected),
        omitted=["psycopg", "psycopg-binary"],
        app_wheel_sha256=digest(app),
        files={
            name: dict(bytes=len(data), sha256=digest(data)) for name, data in sorted(files.items())
        },
    )
    if candidate_digest is not None:
        manifest["app_candidate_manifest_sha256"] = candidate_digest
    manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode()
    files["portable-manifest.json"] = manifest_bytes
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo("Sim2Act-preview/" + name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return dict(
        archive=output.name,
        bytes=output.stat().st_size,
        sha256=digest(output.read_bytes()),
        files=len(files),
        uncompressed_bytes=sum(map(len, files.values())),
        manifest_sha256=digest(manifest_bytes),
        product_commit=specification["product_commit"],
        windows_execution="NOT_RUN",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--app-wheel", type=Path, required=True)
    parser.add_argument(
        "--candidate-manifest",
        type=Path,
        help="Exact package_local_candidate manifest for a new app revision",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            build(
                args.inputs,
                args.assets,
                args.app_wheel,
                args.output,
                candidate_manifest=args.candidate_manifest,
            ),
            indent=2,
        )
    )
