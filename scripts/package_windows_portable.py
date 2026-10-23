"""Assemble an offline Windows SQLite preview; no target-side installation.

Inputs are already downloaded official, hash-pinned archives. This builder
never downloads, compiles, executes Windows code or loads private settings.
"""

import argparse
import hashlib
import json
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


def build(inputs, assets, app_wheel, output):
    if output.exists():
        raise ValueError("Output already exists; do not overwrite a candidate")
    specification = json.loads(inputs.read_text(encoding="utf-8"))
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
    app = app_wheel.read_bytes()
    if digest(app) != "29c344e4d5931a2b8c9a97fb1d1ae222356bbbd6a2b58a928f960fb443f0aad5":
        raise ValueError("Unreviewed app wheel")
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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.inputs, args.assets, args.app_wheel, args.output), indent=2))
