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
            if (name.is_absolute() or ".." in name.parts or "\\" in member.filename
                    or ":" in member.filename or (member.external_attr >> 16) & 0o170000 == 0o120000):
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
        if (specification["product_commit"] != "7794748c78041682c82f0e7fda239d2601dc91b5"
                or digest(data) != "29c344e4d5931a2b8c9a97fb1d1ae222356bbbd6a2b58a928f960fb443f0aad5"):
            raise ValueError("Unreviewed app wheel; exact candidate manifest required")
        return data, None
    record_bytes = candidate_manifest.read_bytes()
    candidate = json.loads(record_bytes)
    commit = candidate.get("source_commit")
    if (candidate.get("format") != "sim2act-local-candidate.v1"
            or type(commit) is not str or re.fullmatch(r"[0-9a-f]{40}", commit) is None
            or commit != specification["product_commit"]
            or candidate.get("mode") != "SYNTHETIC_MOCK_DEMO"
            or candidate.get("python") != "3.12"
            or type(candidate.get("files")) is not dict):
        raise ValueError("App candidate source binding mismatch")
    records = candidate["files"]
    wheel_record = records.get("wheels/" + app_wheel.name)
    if type(wheel_record) is not dict:
        raise ValueError("App candidate wheel record missing")
    data = read_asset(app_wheel, wheel_record)
    # These are the only source files intentionally omitted by the existing
    # pyproject package-data contract. Neither native experiment is enabled.
    omitted = {"src/sim2act/_cold_row_native_impl.c",
               "src/sim2act/_cold_typed_native_impl.c"}
    source = {name[4:]: record for name, record in records.items()
              if name.startswith("src/sim2act/") and name not in omitted}
    metadata = {"sim2act-0.1.0.dist-info/" + name for name in
                ("METADATA", "RECORD", "WHEEL", "entry_points.txt", "top_level.txt")}
    import io

    with zipfile.ZipFile(io.BytesIO(data)) as wheel:
        names = [item.filename for item in wheel.infolist() if not item.is_dir()]
        if (not source or "sim2act/__init__.py" not in source
                or len(names) != len(set(names)) or set(names) != set(source) | metadata):
            raise ValueError("App wheel source inventory mismatch")
        for name, record in source.items():
            value = wheel.read(name)
            if len(value) != record["bytes"] or digest(value) != record["sha256"]:
                raise ValueError("App wheel source bytes mismatch: " + name)
    return data, digest(record_bytes)


def build(inputs, assets, app_wheel, output, *, candidate_manifest=None):
    if output.exists():
        raise ValueError("Output already exists; do not overwrite a candidate")
    specification = json.loads(inputs.read_text(encoding="utf-8"))
    # Complete app/version qualification before reading or assembling runtime
    # archives. A mismatch cannot produce a partially relabelled output.
    app, candidate_digest = checked_app(app_wheel, specification, candidate_manifest)
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
        merge_archive(files, read_asset(assets / "runtime-wheels" / wheel["filename"], wheel),
                      "runtime/Lib/site-packages/")
        selected.append({key: wheel[key] for key in ("name", "version", "url", "sha256",
                                                    "license", "license_expression", "source_distribution_urls")})
    merge_archive(files, app, "runtime/Lib/site-packages/")
    files["runtime/python312._pth"] = b"python312.zip\n.\nLib\\site-packages\nimport site\n"
    files["runtime/LOCAL-CHANGES.txt"] = (
        b"Only python312._pth adds private Lib/site-packages. Binaries and packages are unchanged.\n"
        b"This isolated synthetic SQLite preview omits PostgreSQL drivers.\n")
    files["desktop.py"] = Path(__file__).with_name("portable_desktop.py").read_bytes()
    files["Start-Sim2Act.cmd"] = (
        '@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\n'
        'set "TEMP=%~dp0temp"\r\nset "TMP=%~dp0temp"\r\n'
        'set "PYTHONPATH="\r\nset "PYTHONNOUSERSITE=1"\r\n'
        'if not exist "%~dp0temp" mkdir "%~dp0temp"\r\n'
        '"%~dp0runtime\\python.exe" -I -B -X utf8 "%~dp0desktop.py"\r\n'
        'set "SIM2ACT_PREVIEW_EXIT=%ERRORLEVEL%"\r\n'
        'echo.\r\necho Preview stopped. Close the test Edge window before deleting this folder.\r\n'
        'pause\r\nexit /b %SIM2ACT_PREVIEW_EXIT%\r\n').encode("ascii")
    files["READ-ME-FIRST.txt"] = (
        "Sim2Act Windows x64 - OFFLINE SYNTHETIC PREVIEW\n\n"
        "Unzip to a new ordinary folder. Double-click Start-Sim2Act.cmd.\n"
        "No Python, SDK, compiler, Node, pip or database install is needed.\n"
        "An existing Microsoft Edge and the Windows Universal C Runtime are required.\n"
        "Do not bypass SmartScreen/signature/security refusals or install missing system components.\n"
        "The browser opens only after the local API and Worker are ready.\n"
        "Synthetic login: public-synthetic-blank-workspace\n"
        "Use non-sensitive synthetic data only. No real model, production account, PostgreSQL or formal publication.\n"
        "Keep the console open; Ctrl+C once stops the server. Wait for clean:true.\n"
        "Close the separate test Edge window. Start again to reopen the same local data.\n"
        "Delete this folder only after its own server and browser have exited.\n"
        "If startup fails, preserve the error; do not reset the database or delete a running claim.\n"
        "Application data, temp and browser profile/cache stay in this folder.\n"
        "Windows/Defender/browser OS traces outside it cannot be prevented or promised absent.\n\n"
        "This is an engineering preview, not completed P-A/P-B/G0/R0 production acceptance.\n"
        "Bundled Python 3.12.10 is superseded; short isolated test only, not long-term deployment.\n"
        "License notices remain in runtime/LICENSE.txt and package *.dist-info/licenses.\n"
        "See THIRD-PARTY-SOURCES.json for exact original archives and source links.\n"
    ).encode("utf-8")
    files["THIRD-PARTY-SOURCES.json"] = (json.dumps(dict(python=runtime, wheels=selected), indent=2) + "\n").encode()
    manifest = dict(format="sim2act-offline-windows-sqlite-preview.v1",
                    product_commit=specification["product_commit"], python=runtime["version"],
                    status="BUILT_NOT_WINDOWS_EXECUTED", installed_runtime_wheels=len(selected),
                    omitted=["psycopg", "psycopg-binary"],
                    app_wheel_sha256=digest(app),
                    files={name: dict(bytes=len(data), sha256=digest(data)) for name, data in sorted(files.items())})
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
    return dict(archive=output.name, bytes=output.stat().st_size, sha256=digest(output.read_bytes()),
                files=len(files), uncompressed_bytes=sum(map(len, files.values())),
                manifest_sha256=digest(manifest_bytes), product_commit=specification["product_commit"],
                windows_execution="NOT_RUN")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--app-wheel", type=Path, required=True)
    parser.add_argument("--candidate-manifest", type=Path,
                        help="Exact package_local_candidate manifest for a new app revision")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.inputs, args.assets, args.app_wheel, args.output,
                           candidate_manifest=args.candidate_manifest), indent=2))
