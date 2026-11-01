"""Assemble an offline Windows build input; no target-side installation.

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
        if kind == "native-candidate.v1" and len(profile["native_artifacts"]) != len(wheel_tools.MODULES):
            raise ValueError("Native candidate requires all configured compiled extensions")
    else:
        raise ValueError("Unknown candidate artifact profile")
    source = {
        name[4:]: value
        for name, value in records.items()
        if name.startswith("src/sim2act/") and name not in omitted
    }
    wheel_tools.verify_source(data, source, profile)
    return data, digest(record_bytes)


def checked_desktop_inputs(candidate_manifest, *, configured_runtime=False):
    if candidate_manifest is None:
        raise ValueError("Native host stage requires an exact current candidate manifest")
    records = json.loads(candidate_manifest.read_bytes())["files"]
    root = Path(__file__).resolve().parents[1]
    names = ["scripts/portable_desktop.py", "scripts/package_windows_portable.py", "docs/PreviewRelease.md",
             "docs/F2/BlankSyntheticWorkspaceQuickstart.md", "docs/LimitedTextCandidate.md"]
    names += ["scripts/windows/" + name for name in ("Sim2ActDesktop.cs", "Build-Desktop.ps1", "desktop.manifest", "README.md")]
    if configured_runtime:
        names.append("docs/ConfiguredDesktop.md")
    result = {}
    for name in names:
        if type(records.get(name)) is not dict:
            raise ValueError("Native host candidate input missing: " + name)
        result[name] = read_asset(root / name, records[name])
    return result


def checked_runtime_image(path, specification):
    """Reuse only the exact prior dependency image, never its application bytes."""
    import io

    data = read_asset(path, dict(bytes=18974609,
        sha256="05933fea0ab45831dc0a5e28165979ba2aa718a3a0000f18fc22551a9e592f0c"))
    prefix = "Sim2Act-preview/"
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        raw = archive.read(prefix + "portable-manifest.json")
        if digest(raw) != "2d655d1b86e48a4e62bc23d58e8180328f53169d57a50440d8fc19e300252efa":
            raise ValueError("Historical dependency image manifest mismatch")
        manifest = json.loads(raw)
        provenance = json.loads(archive.read(prefix + "THIRD-PARTY-SOURCES.json"))
        selected = [w for w in specification["wheels"]
                    if w["name"].replace("_", "-") not in ("psycopg", "psycopg-binary")]
        keys = ("name", "version", "url", "sha256", "license", "license_expression", "source_distribution_urls")
        if provenance != dict(python=specification["python"],
                              wheels=[{k: w[k] for k in keys} for w in selected]):
            raise ValueError("Dependency image versions/provenance do not match frozen inputs")
        files = {}
        for name, expected in manifest["files"].items():
            if not name.startswith("runtime/"):
                continue
            value = archive.read(prefix + name)
            if dict(bytes=len(value), sha256=digest(value)) != expected:
                raise ValueError("Dependency image file mismatch: " + name)
            if name.startswith(("runtime/Lib/site-packages/sim2act/", "runtime/Lib/site-packages/sim2act-0.1.0.dist-info/")):
                continue
            files[name] = value
        if not {"runtime/python.exe", "runtime/python312.dll", "runtime/python312.zip"} <= set(files):
            raise ValueError("Complete historical Python runtime required")
        return files


def build(inputs, assets, app_wheel, output, *, candidate_manifest=None, runtime_image=None,
          configured_runtime=False):
    if type(configured_runtime) is not bool:
        raise ValueError("Explicit configured runtime profile required")
    if output.exists():
        raise ValueError("Output already exists; do not overwrite a candidate")
    specification = json.loads(inputs.read_text(encoding="utf-8"))
    # Complete app/version qualification before reading or assembling runtime
    # archives. A mismatch cannot produce a partially relabelled output.
    app, candidate_digest = checked_app(app_wheel, specification, candidate_manifest)
    provenance = None
    if candidate_manifest is not None:
        raw = candidate_manifest.read_bytes()
        if digest(raw) != candidate_digest:
            raise ValueError("Candidate changed during assembly")
        candidate = json.loads(raw)
        provenance = dict(source_commit=candidate["source_commit"],
            artifact_profile=candidate.get("artifact_profile"),
            native_reuse=candidate.get("native_reuse"),
            status="BUILD_INPUT_NOT_CURRENT_WINDOWS_EXECUTION")
    desktop_inputs = checked_desktop_inputs(candidate_manifest, configured_runtime=configured_runtime)
    files = {} if runtime_image is None else checked_runtime_image(runtime_image, specification)
    runtime = specification["python"]
    if runtime_image is None:
        merge_archive(files, read_asset(assets / runtime["filename"], runtime), "runtime/")
    selected = []
    pg_inputs = {}
    # Historical SQLite builds keep their profile. The explicit
    # configured build needs the ORIGINAL pinned driver archives, not the old
    # dependency image's intentionally incomplete PostgreSQL inventory.
    for wheel in specification["wheels"]:
        is_pg = wheel["name"].replace("_", "-") in ("psycopg", "psycopg-binary")
        if is_pg and not configured_runtime:
            continue
        if runtime_image is None or is_pg:
            original = read_asset(assets / "runtime-wheels" / wheel["filename"], wheel)
            merge_archive(
                files,
                original,
                "runtime/Lib/site-packages/",
            )
            if is_pg:
                # Keep the complete unmodified archive for provenance and
                # dependency replacement, including every supplied license.
                import io
                with zipfile.ZipFile(io.BytesIO(original)) as archive:
                    notices = {n: record for n in archive.namelist()
                        if not n.endswith("/") and any(s in n.lower() for s in ("license", "copying", "notice"))
                        for record in [dict(bytes=len(archive.read(n)), sha256=digest(archive.read(n)))]}
                if not notices:
                    raise ValueError("Original PostgreSQL dependency license files missing")
                files["dependency-inputs/" + wheel["filename"]] = original
                pg_inputs[wheel["name"].replace("_", "-")] = dict(filename=wheel["filename"],
                    bytes=len(original), sha256=digest(original), original_notices=notices,
                    source_distribution_urls=wheel["source_distribution_urls"])
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
    if configured_runtime:
        if set(pg_inputs) != {"psycopg", "psycopg-binary"}:
            raise ValueError("Both exact PostgreSQL dependency archives required")
        # Mechanically verified input provenance is not a legal opinion or
        # release approval. Do not invent a project license or redistribution PASS.
        files["PG-RUNTIME-INPUTS.json"] = (json.dumps(dict(
            status="ORIGINAL_DRIVER_INPUTS_ONLY_NOT_PG_OR_RELEASE_ACCEPTANCE",
            distribution_review="NOT_EVALUATED", project_license="UNSPECIFIED_UNCHANGED",
            dependencies=pg_inputs), indent=2, sort_keys=True) + "\n").encode()
    merge_archive(files, app, "runtime/Lib/site-packages/")
    if provenance is not None:
        files["app-build-provenance.json"] = (json.dumps(provenance, indent=2, sort_keys=True) + "\n").encode()
    files["runtime/python312._pth"] = b"python312.zip\n.\nLib\\site-packages\nimport site\n"
    files["runtime/LOCAL-CHANGES.txt"] = (
        b"Only python312._pth adds private Lib/site-packages. Binaries and packages are unchanged.\n"
        + (b"Configured runtime includes original pinned PostgreSQL driver archives and supplied notices; execution and redistribution review remain separate.\n"
           if configured_runtime else b"This isolated synthetic SQLite preview omits PostgreSQL drivers.\n")
    )
    files["desktop.py"] = desktop_inputs["scripts/portable_desktop.py"]
    files["使用说明.md"] = desktop_inputs["docs/PreviewRelease.md"]
    for name in ("docs/F2/BlankSyntheticWorkspaceQuickstart.md", "docs/LimitedTextCandidate.md"):
        files[name] = desktop_inputs[name]
    if configured_runtime:
        files["docs/ConfiguredDesktop.md"] = desktop_inputs["docs/ConfiguredDesktop.md"]
    # Native desktop is the product entry. Browser access is explicit developer preview.
    for name in ("Sim2ActDesktop.cs", "Build-Desktop.ps1", "desktop.manifest", "README.md"):
        files["desktop-build/" + name] = desktop_inputs["scripts/windows/" + name]
    files["Start-Sim2Act.cmd"] = (
        '@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\n'
        'if not exist "%~dp0Sim2Act.exe" (echo Native desktop build required. See desktop-build/README.md & exit /b 1)\r\n'
        '"%~dp0Sim2Act.exe"\r\nexit /b %ERRORLEVEL%\r\n'
    ).encode("ascii")
    if configured_runtime:
        files["Start-Configured-Sim2Act.cmd"] = (
            '@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\n'
            'if "%~1"=="" (echo Supply an existing private config file, then optionally the existing approved selection file. & exit /b 1)\r\n'
            'if not exist "%~dp0Sim2Act.exe" (echo Matching native desktop build required. & exit /b 1)\r\n'
            'if "%~2"=="" ("%~dp0Sim2Act.exe" --config "%~1") else ("%~dp0Sim2Act.exe" --config "%~1" --spec-selection "%~2")\r\n'
            'exit /b %ERRORLEVEL%\r\n'
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
    if configured_runtime:
        files["CONFIGURED-BUILD-INPUT.txt"] = (
            "INTERNAL CONFIGURED DESKTOP BUILD INPUT - NOT R0 OR RELEASE ACCEPTANCE\n"
            "Use the newly compiled same-revision EXE and Start-Configured-Sim2Act.cmd with an existing private config.\n"
            "Configured uses original API/Worker processes, existing PostgreSQL app-role URL, login and approvals.\n"
            "No database/user/grant/token/runtime is created or installed by the launcher.\n"
            "Default Start-Sim2Act.cmd remains the explicit synthetic local workspace.\n"
            "The PG wheels and supplied license files are original pinned archives; source provenance is in PG-RUNTIME-INPUTS.json.\n"
            "Project licensing and full dependency redistribution review remain unresolved; no license or review PASS is invented here.\n"
            "Configured PG, native Windows and P-A/P-B/R0 acceptance must be separately established.\n"
        ).encode()
    files["THIRD-PARTY-SOURCES.json"] = (
        json.dumps(dict(python=runtime, wheels=selected), indent=2) + "\n"
    ).encode()
    manifest = dict(
        format=("sim2act-offline-windows-configured-build.v1" if configured_runtime
                else "sim2act-offline-windows-sqlite-preview.v1"),
        product_commit=specification["product_commit"],
        python=runtime["version"],
        status="NATIVE_HOST_BUILD_REQUIRED_NOT_WINDOWS_EXECUTED",
        desktop_entry="Sim2Act.exe",
        installed_runtime_wheels=len(selected),
        omitted=[] if configured_runtime else ["psycopg", "psycopg-binary"],
        configured_backend="SOURCE_INTEGRATED_NOT_POSTGRESQL_OR_WINDOWS_ACCEPTED" if configured_runtime else "NOT_INCLUDED",
        app_wheel_sha256=digest(app),
        files={
            name: dict(bytes=len(data), sha256=digest(data)) for name, data in sorted(files.items())
        },
    )
    if candidate_digest is not None:
        manifest["app_candidate_manifest_sha256"] = candidate_digest
    if runtime_image is not None:
        manifest["dependency_image_sha256"] = digest(runtime_image.read_bytes())
        manifest["dependency_image_role"] = "UNCHANGED_RUNTIME_DEPENDENCIES_ONLY_OLD_APP_EXCLUDED"
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
    parser.add_argument("--runtime-image", type=Path,
                        help="Exact frozen prior dependency image; all old application bytes excluded")
    parser.add_argument(
        "--candidate-manifest",
        type=Path,
        help="Exact package_local_candidate manifest for a new app revision",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--configured-runtime", action="store_true",
                        help="Include original pinned PG drivers; not PG/native/Release acceptance")
    args = parser.parse_args()
    print(
        json.dumps(
            build(
                args.inputs,
                args.assets,
                args.app_wheel,
                args.output,
                candidate_manifest=args.candidate_manifest,
                runtime_image=args.runtime_image,
                configured_runtime=args.configured_runtime,
            ),
            indent=2,
        )
    )
