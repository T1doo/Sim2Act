"""Verify complete Windows pins against actual installed metadata, without network calls."""

import hashlib
import importlib.metadata as metadata
import json
import re
import struct
import sys
from pathlib import Path


def canonical(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def main():
    root = Path(__file__).resolve().parents[1]
    lock = root / "requirements-windows.lock"
    expected = {}
    for line in lock.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        name, version = line.split("==")
        key = canonical(name)
        assert key not in expected, "Duplicate Windows pin"
        expected[key] = version
    actual = {}
    for dist in metadata.distributions():
        key = canonical(dist.metadata["Name"])
        # PEP 660 exposes both source egg-info and installed dist-info for this editable project.
        assert key not in actual or (
            key == "sim2act" and actual[key] == dist.version
        ), "Conflicting or unexpected duplicate installed package"
        actual[key] = dist.version
    expected["sim2act"] = "0.1.0"  # Editable source is identified by the tested Git commit.
    assert actual == expected, {"expected": expected, "actual": actual}
    assert sys.version_info[:3] == (3, 12, 10) and struct.calcsize("P") == 8
    summary = {
        "result": "PASS",
        "coverage": "Setup-created venv; exact Windows installed dependency set",
        "python": sys.version.split()[0],
        "base_interpreter": sys.base_prefix,
        "venv": sys.prefix,
        "lock_sha256": hashlib.sha256(lock.read_bytes()).hexdigest(),
        "installed_packages": dict(sorted(actual.items())),
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
