"""Build an allowlisted local candidate from an exact clean Git commit.

Reuses the existing setuptools pyproject/wheel and installation scripts. Does not
package a checkout wholesale, install dependencies, contact models or deploy.
pip may fetch the pinned build backend through the already configured network.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "pyproject.toml", "requirements.lock", "requirements-windows.lock", ".env.example",
    "docs/Installation.md", "docs/FirstUse.md", "docs/LocalCandidate.md",
    "scripts/Common.ps1", "scripts/Setup.ps1", "scripts/Doctor.ps1", "scripts/Start.ps1",
    "scripts/Status.ps1", "scripts/Stop.ps1", "scripts/manage.py", "scripts/install_preflight.py",
    "scripts/local_candidate_demo.py", "scripts/local-candidate/mock-fixtures.json",
    "scripts/package_local_candidate.py",
]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="NEW output directory")
    args = parser.parse_args()
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
        "# Sim2Act 合成 mock 本地候选\n\n"
        "安装、演示命令及限制见 [本地候选说明](docs/LocalCandidate.md)。\n"
        "精确源码和文件校验值见 candidate-manifest.json。\n"
        "不含真实凭据、数据库或历史大证据；不启用真实模型。\n"
    ).encode()
    with tempfile.TemporaryDirectory(prefix="sim2act-candidate-build-") as folder:
        staging = Path(folder)
        for name, data in contents.items():
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        environment = {**os.environ, "SOURCE_DATE_EPOCH": git("show", "-s", "--format=%ct", commit).decode().strip()}
        result = subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps",
            "--wheel-dir", str(output), "."], cwd=staging, env=environment,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        # Build log stays outside the distributable (tool paths are local).
        (output / "build.log").write_bytes(result.stdout)
        if result.returncode:
            parser.exit(1, "Wheel build failed; output/build.log preserved\n")
    wheels = list(output.glob("sim2act-*.whl"))
    if len(wheels) != 1:
        parser.exit(1, "Expected one built wheel; output preserved\n")
    wheel = wheels[0]
    contents["wheels/" + wheel.name] = wheel.read_bytes()
    manifest = dict(format="sim2act-local-candidate.v1", source_commit=commit,
        build_backend="setuptools==82.0.1", python="3.12", mode="SYNTHETIC_MOCK_DEMO",
        real_model_requests=0, env_template_only=True,
        excluded=[".git", "private configuration", "database", "logs", "docs/evidence", "tests",
                  "node_modules", "virtual environments"],
        files={name: dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
               for name, data in sorted(contents.items())})
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
    print(json.dumps(dict(source_commit=commit, archive=archive.name, wheel=wheel.name,
        archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),
        files=len(contents), bytes=archive.stat().st_size)))


if __name__ == "__main__":
    main()
