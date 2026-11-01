"""Build an allowlisted local candidate from an exact clean Git commit.

Reuses the existing setuptools pyproject/wheel and installation scripts. Does not
package a checkout wholesale, install dependencies, contact models or deploy.
Only the existing pinned backend is used; the build cannot fetch dependencies.
"""

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import subprocess
import sys
import shutil
import tempfile
import zipfile
from pathlib import Path

ROOT = Path('/workspace/Sim2Act')
FILES = [
    "setup.py",
    "pyproject.toml",
    "requirements.lock",
    "requirements-windows.lock",
    ".env.example",
    "docs/Installation.md",
    "docs/ProductionConnection.md",
    "docs/FirstUse.md",
    "docs/LocalCandidate.md",
    "docs/PreviewRelease.md",
    "docs/LimitedTextCandidate.md",
    "docs/F2/BlankSyntheticWorkspaceQuickstart.md",
    "scripts/Common.ps1",
    "scripts/Setup.ps1",
    "scripts/Doctor.ps1",
    "scripts/Start.ps1",
    "scripts/Status.ps1",
    "scripts/Stop.ps1",
    "scripts/manage.py",
    "scripts/install_preflight.py",
    "scripts/local_candidate_demo.py",
    "scripts/local-candidate/mock-fixtures.json",
    "scripts/package_local_candidate.py",
    "scripts/candidate_wheel.py",
    "scripts/package_windows_portable.py",
    "scripts/portable_desktop.py",
    "scripts/windows/Sim2ActDesktop.cs",
    "scripts/windows/Build-Desktop.ps1",
    "scripts/windows/Test-OrdinaryPaths.ps1",
    "scripts/windows/desktop.manifest",
    "scripts/windows/README.md",
]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="NEW output directory")
    parser.add_argument(
        "--python-preview",
        action="store_true",
        help="Explicit fallback preview; never native performance acceptance",
    )
    args = parser.parse_args()
    if importlib.metadata.version("setuptools") != "82.0.1":
        parser.error("Existing setuptools==82.0.1 required; this command will not download it")
    helper = importlib.util.spec_from_file_location(
        "candidate_wheel", ROOT / "scripts/candidate_wheel.py"
    )
    wheel_tools = importlib.util.module_from_spec(helper)
    helper.loader.exec_module(wheel_tools)
    if git("status", "--porcelain").strip():
        parser.error("Commit all candidate source before packaging; clean checkout required")
    output = Path(os.path.abspath(args.output))
    if output.exists() or any(part.is_symlink() for part in [output, *output.parents]):
        parser.error("Output must be a new directory; existing files are preserved")
    output.mkdir(parents=True)
    commit = git("rev-parse", "HEAD").decode().strip()
    names = git("ls-tree", "-r", "--name-only", commit, "src").decode().splitlines() + FILES
    contents = {}
    # Git blobs, not local workspace files: no untracked configuration/data enters.
    for name in sorted(set(names)):
        mode = git("ls-tree", commit, "--", name).decode().split()[0]
        if mode != "100644":
            parser.error("Only ordinary tracked files can be packaged: " + name)
        contents[name] = git("show", commit + ":" + name)
    contents["README.md"] = (
        "# Sim2Act 限制本地候选\n\n"
        "正常入口、已有依赖环境的安装／启动／退出／重开见 [限制候选步骤](docs/LimitedTextCandidate.md)。\n"
        "历史 mock 演示见 [本地候选说明](docs/LocalCandidate.md)。\n"
        "精确源码和文件校验值见 candidate-manifest.json。\n"
        "不含真实凭据、数据库或历史大证据；默认不启用模型，显式参数只开放单文本逐字合同。\n"
    ).encode()
    # Reuse the EXACT wheel already installed and exercised; no second build.
    source = Path('/workspace/scratch/graph-resolve-wheel-build-35eaa941-20261101/wheels/sim2act-0.1.0-cp312-cp312-linux_x86_64.whl')
    accepted = json.loads(Path('/workspace/scratch/installed-graph-resolve-cli-35eaa941-20261101/report.json').read_text())
    assert commit == accepted['candidate_source'] == '35eaa941f544ca016ddeeefb839178d316fc1c6b'
    assert accepted['status'] == 'PASS' and accepted['csv_reopen_same_result'] and accepted['csv_sum'] == '30'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == 'e5cb821f14f26261ae6a9272608b2ce1d82abd2874ad2f82e87ebec00727f68a'
    shutil.copyfile(source, output/source.name)
    wheels = list(output.glob("sim2act-*.whl"))
    if len(wheels) != 1:
        parser.exit(1, "Expected one built wheel; output preserved\n")
    wheel = wheels[0]
    wheel_data = wheel.read_bytes()
    profile = wheel_tools.wheel_profile(wheel.name, wheel_data)
    source = {
        name[4:]: wheel_tools.record(value)
        for name, value in contents.items()
        if name.startswith("src/sim2act/")
    }
    wheel_tools.verify_source(wheel_data, source, profile)
    if args.python_preview and (
        profile["tags"] != ["py3-none-any"]
        or not profile["root_is_purelib"]
        or profile["native_artifacts"]
    ):
        parser.exit(
            1, "Python preview requires a pure py3-none-any wheel with no native artifacts\n"
        )
    if not args.python_preview and len(profile["native_artifacts"]) != len(wheel_tools.MODULES):
        parser.exit(
            1, "Native candidate requires all configured compiled extensions; build output preserved\n"
        )
    contents["wheels/" + wheel.name] = wheel_data
    manifest = dict(
        format="sim2act-local-candidate.v1",
        source_commit=commit,
        build_backend="setuptools==82.0.1",
        python="3.12",
        mode="SYNTHETIC_MOCK_DEMO",
        opt_in_capabilities=["exact-resource-read.v1"],
        default_model_enabled=False,
        artifact_profile="python-preview.v1" if args.python_preview else "native-candidate.v1",
        wheel_profile=profile,
        build_platform=sys.platform,
        qualification="INSTALLED_LIMITED_CSV_VERIFIED_NOT_FULL_PRODUCT",
        accepted_scope=["isolated installed package", "four native imports", "CSV sum 30/v1", "same-key no duplicate", "normal stop and first reopen"],
        accepted_model_scope="default disabled; no new real-model acceptance in this package test",
        real_model_requests=0,
        env_template_only=True,
        excluded=[
            ".git",
            "private configuration",
            "database",
            "logs",
            "docs/evidence",
            "tests",
            "node_modules",
            "virtual environments",
        ],
        files={
            name: dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            for name, data in sorted(contents.items())
        },
    )
    manifest_data = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    (output / "candidate-manifest.json").write_bytes(manifest_data)
    contents["candidate-manifest.json"] = manifest_data
    archive = output / ("Sim2Act-local-candidate-" + commit[:12] + ".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, data in sorted(contents.items()):
            info = zipfile.ZipInfo("Sim2Act-local-candidate/" + name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, data)
    print(
        json.dumps(
            dict(
                source_commit=commit,
                archive=archive.name,
                wheel=wheel.name,
                archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),
                files=len(contents),
                bytes=archive.stat().st_size,
            )
        )
    )


if __name__ == "__main__":
    main()
