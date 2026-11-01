"""Compile the existing Windows host on Linux with verified local Microsoft tools.

No downloader, installer, Windows execution, application runtime assembly or CI
dispatch is included. Output is a host component, not a complete product package.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
LOCK = Path(__file__).with_name("cross-build-tools.json")


def record(value):
    return dict(bytes=len(value), sha256=hashlib.sha256(value).hexdigest())


def ordinary(path):
    path = Path(os.path.abspath(path))
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Linked build path refused: " + str(path))
    return path


def checked_tools(path):
    path = ordinary(path)
    lock = json.loads(LOCK.read_bytes())
    actual = {str(p.relative_to(path)) for directory in ("dotnet", "compiler", "net462")
              for p in (path / directory).rglob("*") if p.is_file()}
    if actual != set(lock["files"]):
        raise ValueError("Exact pinned Microsoft build tool inventory required")
    for name, expected in lock["files"].items():
        if record(ordinary(path / name).read_bytes()) != expected:
            raise ValueError("Pinned build tool bytes changed: " + name)
    return path


def pe_profile(value):
    if value[:2] != b"MZ":
        raise ValueError("Missing DOS header")
    start = struct.unpack_from("<I", value, 60)[0]
    if value[start:start + 4] != b"PE\0\0":
        raise ValueError("Missing PE header")
    machine, sections = struct.unpack_from("<HH", value, start + 4)
    size = struct.unpack_from("<H", value, start + 20)[0]
    optional = start + 24
    if machine != 0x8664 or struct.unpack_from("<H", value, optional)[0] != 0x20B:
        raise ValueError("Windows x64 PE32+ required")
    if struct.unpack_from("<H", value, optional + 68)[0] != 2:
        raise ValueError("Windows GUI subsystem required")
    cli, cli_size = struct.unpack_from("<II", value, optional + 112 + 14 * 8)
    location = None
    for index in range(sections):
        offset = optional + size + index * 40
        virtual_size, rva, raw_size, raw = struct.unpack_from("<IIII", value, offset + 8)
        if rva <= cli and cli + cli_size <= rva + min(virtual_size, raw_size):
            location = raw + cli - rva
    if location is None or cli_size < 72:
        raise ValueError("Missing bounded CLI header")
    flags, entry = struct.unpack_from("<II", value, location + 16)
    if not flags & 1 or flags & 0x12 or entry >> 24 != 6 or not entry & 0xFFFFFF:
        raise ValueError("Managed IL method entry point required")
    return dict(machine="AMD64", format="PE32+", subsystem="WINDOWS_GUI",
                managed_il=True, entry_point_token=hex(entry))


def build(source_commit, tools, sdk, output):
    if len(source_commit) != 40 or any(c not in "0123456789abcdef" for c in source_commit):
        raise ValueError("Full lowercase Git source commit required")
    tools = checked_tools(tools)
    sdk, output = ordinary(sdk), ordinary(output)
    if record(sdk.read_bytes()) != dict(bytes=9818548, sha256="90778deb1b77e36292828b4b5833c9255c27533f40e0ddd55891ae718944edc4"):
        raise ValueError("Exact Microsoft WebView2 SDK 1.0.4314.35 required")
    if output.exists():
        raise ValueError("New output directory required; existing results preserved")
    # Read immutable Git blobs, never pretend dirty working files are the commit.
    sources = {name: subprocess.check_output(["git", "show", source_commit + ":scripts/windows/" + name], cwd=ROOT)
               for name in ("Sim2ActDesktop.cs", "desktop.manifest")}
    output.mkdir()
    files = dict(sources)
    with zipfile.ZipFile(sdk) as archive:
        for name in ("lib/net462/Microsoft.Web.WebView2.Core.dll", "lib/net462/Microsoft.Web.WebView2.WinForms.dll",
                     "runtimes/win-x64/native/WebView2Loader.dll", "LICENSE.txt"):
            files["WEBVIEW2-SDK-LICENSE.txt" if name == "LICENSE.txt" else Path(name).name] = archive.read(name)
    for name, value in files.items():
        (output / name).write_bytes(value)
    references = [str(tools / "net462" / name) for name in ("mscorlib.dll", "System.dll", "System.Core.dll",
        "System.Drawing.dll", "System.Windows.Forms.dll", "System.Web.Extensions.dll", "System.Xml.dll", "Microsoft.CSharp.dll")]
    references += [str(output / name) for name in ("Microsoft.Web.WebView2.Core.dll", "Microsoft.Web.WebView2.WinForms.dll")]
    command = [str(tools / "dotnet/dotnet"), str(tools / "compiler/csc.dll"), "/nologo", "/noconfig", "/nostdlib+",
        "/target:winexe", "/platform:x64", "/optimize+", "/langversion:5", "/codepage:65001", "/deterministic+",
        "/pathmap:" + str(output) + "=/src/sim2act-desktop", "/win32manifest:" + str(output / "desktop.manifest"),
        "/out:" + str(output / "Sim2Act.exe")]
    command += ["/reference:" + name for name in references] + [str(output / "Sim2ActDesktop.cs")]
    (output / "command.json").write_text(json.dumps(command, indent=2) + "\n")
    env = dict(os.environ, DOTNET_ROOT=str(tools / "dotnet"), DOTNET_CLI_HOME=str(tools / "cli-home"),
               DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_SKIP_FIRST_TIME_EXPERIENCE="1")
    result = subprocess.run(command, cwd=output, env=env, capture_output=True, timeout=90)
    for name, value in (("compile.stdout.log", result.stdout), ("compile.stderr.log", result.stderr)):
        (output / name).write_bytes(value)
    (output / "compile-exit-code.json").write_text(json.dumps(dict(returncode=result.returncode)) + "\n")
    if result.returncode:
        raise ValueError("Actual desktop compilation failed; preserve command and compiler logs")
    value = (output / "Sim2Act.exe").read_bytes()
    profile = pe_profile(value)
    files.update({"Sim2Act.exe": value, "compile.stdout.log": result.stdout, "compile.stderr.log": result.stderr})
    files["README.md"] = ("# Sim2Act compiled desktop host component\n\n"
        "Exact host source: `" + source_commit + "`.\n\n"
        "CROSS_COMPILED_NOT_WINDOWS_EXECUTED. This is the real WinForms/WebView2 host, not a browser launcher. "
        "It is a maintainer build component, not a complete installer or ready-to-use product. "
        "It does not include the private Windows Python runtime, matching Windows application wheel/four native extensions, "
        "or a desktop execution acceptance. Assemble only with the same exact application revision and preserve its "
        "READY/STOPPED, authorization, origin, lease, cancellation and persistence checks. "
        "No Windows runtime or system permission is installed by this build.\n").encode()
    manifest = dict(format="sim2act-cross-compiled-desktop-host.v1", source_commit=source_commit,
        status="CROSS_COMPILED_NOT_WINDOWS_EXECUTED", artifact_scope="HOST_COMPONENT_ONLY_NOT_INSTALLER",
        runtime_execution="NOT_RUN", compiler="Microsoft.Net.Compilers.Toolset/4.11.0",
        target=".NETFramework/4.6.2", webview2_sdk="1.0.4314.35", pe=profile,
        tool_lock_sha256=record(LOCK.read_bytes())["sha256"], files={n: record(v) for n, v in sorted(files.items())})
    files["host-manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    (output / "host-manifest.json").write_bytes(files["host-manifest.json"])
    archive = output / ("Sim2Act-desktop-host-" + source_commit[:12] + ".zip")
    with zipfile.ZipFile(archive, "x") as zipped:
        for name, value in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zipped.writestr(info, value)
    report = dict(source_commit=source_commit, returncode=result.returncode, pe=profile,
                  exe=record(value=(output / "Sim2Act.exe").read_bytes()), archive=dict(name=archive.name, **record(archive.read_bytes())),
                  status=manifest["status"])
    (output / "build-result.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--tools", type=Path, required=True)
    parser.add_argument("--sdk-package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.source_commit, args.tools, args.sdk_package, args.output), indent=2))


if __name__ == "__main__":
    main()
