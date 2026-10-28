"""Strict local wheel metadata/inventory, never loads a native binary."""

import hashlib
import io
import itertools
import zipfile
from email.parser import BytesParser
from pathlib import Path

MODULES = ("_raw_snapshot", "_cold_graph_structure")
META_PREFIX = "sim2act-0.1.0.dist-info/"
METADATA = {
    META_PREFIX + name
    for name in ("METADATA", "RECORD", "WHEEL", "entry_points.txt", "top_level.txt")
}


def record(value):
    return dict(bytes=len(value), sha256=hashlib.sha256(value).hexdigest())


def wheel_profile(filename, data, *, target=None):
    name = Path(filename).name
    if not name.endswith(".whl"):
        raise ValueError("Wheel filename required")
    parts = name[:-4].rsplit("-", 3)
    if len(parts) != 4 or parts[0] != "sim2act-0.1.0":
        raise ValueError("Exact application wheel filename required")
    expected_tags = {
        "-".join(values) for values in itertools.product(*(part.split(".") for part in parts[1:]))
    }
    with zipfile.ZipFile(io.BytesIO(data)) as wheel:
        names = [item.filename for item in wheel.infolist() if not item.is_dir()]
        if len(names) != len(set(names)):
            raise ValueError("App wheel source inventory mismatch: duplicate members")
        if META_PREFIX + "WHEEL" not in names:
            raise ValueError("Wheel metadata missing")
        header = BytesParser().parsebytes(wheel.read(META_PREFIX + "WHEEL"))
        tags = header.get_all("Tag", [])
        pure = header.get("Root-Is-Purelib")
        if (
            set(tags) != expected_tags
            or len(tags) != len(expected_tags)
            or pure not in ("true", "false")
        ):
            raise ValueError("Wheel filename/metadata tag mismatch")
        if expected_tags == {"py3-none-any"}:
            suffix = None
            if pure != "true":
                raise ValueError("Pure preview wheel metadata mismatch")
        elif expected_tags == {"cp312-cp312-win_amd64"}:
            suffix = ".cp312-win_amd64.pyd"
            if pure != "false":
                raise ValueError("Windows native wheel metadata mismatch")
        elif expected_tags == {"cp312-cp312-linux_x86_64"} and target != "windows":
            suffix = ".cpython-312-x86_64-linux-gnu.so"
            if pure != "false":
                raise ValueError("Linux native wheel metadata mismatch")
        else:
            raise ValueError("Wheel target platform is not supported for this package")
        allowed = set() if suffix is None else {"sim2act/" + module + suffix for module in MODULES}
        native = {}
        for member in names:
            if member.lower().endswith((".so", ".pyd", ".dll")):
                if member not in allowed:
                    raise ValueError("Unlisted or wrong-platform native artifact")
                native[member] = record(wheel.read(member))
        return dict(
            filename=name,
            tags=sorted(tags),
            root_is_purelib=pure == "true",
            native_artifacts=native,
        )


def verify_source(data, source, profile):
    with zipfile.ZipFile(io.BytesIO(data)) as wheel:
        names = [item.filename for item in wheel.infolist() if not item.is_dir()]
        expected = set(source) | METADATA | set(profile["native_artifacts"])
        if not source or len(names) != len(set(names)) or set(names) != expected:
            raise ValueError("App wheel source inventory mismatch")
        for name, expected_record in source.items():
            if record(wheel.read(name)) != expected_record:
                raise ValueError("App wheel source bytes mismatch: " + name)
