"""Read-only local installation checks; Python standard library only.

No subprocesses, imports of application/third-party code, network requests,
configuration exports, filesystem writes, or database connections.
"""

import argparse
import importlib.metadata
import json
import platform
import re
import shutil
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_LINE = re.compile(r"^(SIM2ACT_[A-Z_]+|INTERN_API_TOKEN)=(.*)$")
PIN = re.compile(r"^([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)$")


def result(check, ok, message, action):
    return {
        "check": check,
        "status": "PASS" if ok else "BLOCKED",
        "message": message,
        "next_step": "None." if ok else action,
    }


def config_checks(path):
    """Read only the explicitly selected file. Never include its content in results."""
    try:
        with path.open(encoding="utf-8-sig") as stream:
            content = stream.read(65537)
    except (OSError, UnicodeError, ValueError):
        return [
            result(
                "config_file",
                False,
                "Local configuration is missing or unreadable.",
                "Copy .env.example to .env and edit it privately; select it with --config.",
            )
        ]
    if len(content) > 65536:
        return [
            result(
                "config_format",
                False,
                "Local configuration exceeds the check limit.",
                "Use a small local KEY=value configuration file.",
            )
        ]
    values = {}
    valid = True
    for line in content.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = CONFIG_LINE.fullmatch(line)
        if match is None:
            valid = False
            continue
        values[match[1]] = match[2]
    checks = [
        result(
            "config_format",
            valid,
            "Configuration format matches the PowerShell loader."
            if valid
            else "Configuration contains an unsupported line.",
            "Use unquoted KEY=value lines, without spaces around the key or equals sign.",
        )
    ]
    for key in ("SIM2ACT_DATABASE_URL", "SIM2ACT_DATA_DIR"):
        present = bool(values.get(key, "").strip())
        checks.append(
            result(
                key.lower(),
                present,
                "Required configuration value is present."
                if present
                else "Required configuration value is absent or empty.",
                "Set " + key + " privately in the selected configuration file.",
            )
        )
    return checks


def dependency_checks(lock, version=importlib.metadata.version):
    try:
        lines = lock.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return [
            result(
                "dependency_lock",
                False,
                "Platform dependency lock is unavailable.",
                "Restore the repository lock file from the selected development commit.",
            )
        ]
    pins = []
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = PIN.fullmatch(line.strip())
        if match is None:
            return [
                result(
                    "dependency_lock",
                    False,
                    "Dependency lock format is unsupported.",
                    "Use the repository's exact-version dependency lock.",
                )
            ]
        pins.append(match.groups())
    if not pins:
        return [
            result(
                "dependency_lock",
                False,
                "Dependency lock has no version pins.",
                "Restore the repository lock file.",
            )
        ]
    missing = 0
    mismatched = 0
    try:
        for name, expected in pins:
            try:
                installed = version(name)
            except importlib.metadata.PackageNotFoundError:
                missing += 1
                continue
            if installed != expected:
                mismatched += 1
        version("sim2act")
    except importlib.metadata.PackageNotFoundError:
        missing += 1
    except Exception:
        # Broken local metadata may embed paths or secrets in its exception text.
        return [
            result(
                "dependencies",
                False,
                "Installed package metadata cannot be read.",
                "Review the local environment and run the documented Setup step.",
            )
        ]
    return [
        result(
            "dependencies",
            missing == 0 and mismatched == 0,
            "Locked dependencies and the Sim2Act package are present."
            if missing == 0 and mismatched == 0
            else "Package metadata: %d missing, %d version mismatches." % (missing, mismatched),
            "Run the documented Setup step with this repository's virtual environment.",
        )
    ]


def collect(stage, config, root=ROOT, system=None, which=shutil.which):
    system = platform.system() if system is None else system
    windows = system == "Windows"
    checks = [
        result(
            "python",
            sys.version_info[:2] == (3, 12),
            "Python 3.12 is selected."
            if sys.version_info[:2] == (3, 12)
            else "Selected interpreter is not Python 3.12.",
            "Use py -3.12 on Windows, or python3.12 on Linux/macOS.",
        ),
        result(
            "architecture",
            struct.calcsize("P") == 8
            and (not windows or platform.machine().lower() in {"amd64", "x86_64"}),
            "Interpreter architecture checked (Windows requires x64).",
            "Select Python 3.12 x64 for the Windows native path.",
        ),
    ]
    checks.append(
        result(
            "git",
            which("git") is not None,
            "Git command presence checked.",
            "Install Git using its official installer, then open a new terminal.",
        )
    )
    if windows:
        checks.append(
            result(
                "python_launcher",
                which("py") is not None,
                "Python launcher command presence checked.",
                "Install Python 3.12 x64 with its Windows py launcher; reopen the terminal.",
            )
        )
        checks.append(
            result(
                "powershell",
                which("pwsh") is not None,
                "PowerShell 7 command presence checked; version is not verified.",
                "Install PowerShell 7, reopen the terminal, and check pwsh --version.",
            )
        )
    lock = root / ("requirements-windows.lock" if windows else "requirements.lock")
    checks.append(
        result(
            "repository",
            (root / "pyproject.toml").is_file() and lock.is_file(),
            "Repository installation files checked.",
            "Run this script from a complete Sim2Act checkout.",
        )
    )
    config_path = Path(config)
    if not config_path.is_absolute():
        config_path = root / config_path
    checks.extend(config_checks(config_path))
    if stage == "start":
        selected = Path(sys.prefix).resolve() == (root / ".venv").resolve()
        checks.append(
            result(
                "virtual_environment",
                selected,
                "Repository virtual environment selection checked.",
                "Run with .venv\\Scripts\\python.exe on Windows or .venv/bin/python elsewhere.",
            )
        )
        checks.extend(dependency_checks(lock))
    return checks


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("setup", "start"), default="setup")
    parser.add_argument(
        "--config", default=".env", help="Explicit local file; relative to repository root"
    )
    parser.add_argument(
        "--json", action="store_true", help="Print fixed, shareable diagnostic fields"
    )
    args = parser.parse_args(argv)
    try:
        checks = collect(args.stage, args.config)
    except (OSError, ValueError, RuntimeError):
        checks = [
            result(
                "local_check",
                False,
                "Local checks could not be completed.",
                "Review local file access and the documented installation steps.",
            )
        ]
    blocked = any(item["status"] == "BLOCKED" for item in checks)
    report = {
        "stage": args.stage,
        "status": "BLOCKED" if blocked else "PASS",
        "checks": checks,
        "limitations": "Presence checks only. Database/service, credentials, schema, permissions, "
        "config value validity, imports, and native Win11 usability are NOT verified. "
        "No installation or startup was performed. See docs/Installation.md.",
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        for item in checks:
            print("[{status}] {check}: {message}".format(**item))
            if item["status"] == "BLOCKED":
                print("  Next: " + item["next_step"])
        print("Result: " + report["status"])
        print(report["limitations"])
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
