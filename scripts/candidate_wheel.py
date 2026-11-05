"""Strict local wheel metadata/inventory, never loads a native binary."""

import hashlib
import io
import itertools
import zipfile
from email.parser import BytesParser
from pathlib import Path

MODULES = ("_raw_snapshot", "_cold_graph_structure", "_cold_typed_cohort", "_cold_source_owned_impl")
NATIVE_SOURCE_GROUPS = {
    "_raw_snapshot": ["_raw_snapshot.c"],
    "_cold_graph_structure": ["_cold_graph_structure.c"],
    "_cold_typed_cohort": ["_cold_typed_cohort.c", "_cold_typed_native_impl.c", "_raw_snapshot.c", "_cold_cohort_backend.py"],
    "_cold_source_owned_impl": ["_cold_source_owned_impl.c", "_cold_source_live_match.h", "_cold_source_code.h", "_cold_source_view.h", "_cold_source_shape.h"],
}

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


def reuse_windows_native(pure_filename, pure_data, native_path, setup_bytes, proof_path, *, native_image=False):
    """Repackage current Python with exact unchanged, previously imported PE parts.

    No compiler or Windows execution occurs. The original reviewed build recipe,
    each full native input group, archive, actual-import report and PE ABI must
    all match. Changed native sources require a real new build, never a tag edit.
    """
    import base64
    import csv
    import json

    from windows_pe import inspect

    if record(setup_bytes)["sha256"] != "0bbab56172ee0dab2cf8788eab50b0e9bca18f6286ac4337e3c353a50862dee0":
        raise ValueError("Original native build recipe changed; new compilation required")
    native_data = Path(native_path).read_bytes()
    original_record = record(native_data)
    if native_image:
        if original_record['sha256'] != 'cc177eeb8815194a4f1e973e146ce7dd95c2949350745a296c4d6a9bfcd38027':
            raise ValueError('Original accepted Windows image changed')
        # Normalize only the application members of this exact qualified image.
        # No archive paths are extracted to disk; current Python always comes
        # from the new source wheel below, never from this historical image.
        normalized = io.BytesIO()
        prefix = 'Sim2Act/runtime/Lib/site-packages/'
        with zipfile.ZipFile(io.BytesIO(native_data)) as image, zipfile.ZipFile(normalized, 'w') as output:
            for name in image.namelist():
                if name.startswith(prefix + 'sim2act/') and not name.endswith('/'):
                    output.writestr(name[len(prefix):], image.read(name))
        native_data = normalized.getvalue()
    elif original_record != dict(bytes=1551930, sha256="bbefc8d561d35126164967e4018a9d58337c9fa5aa287469937787060fd959b3"):
        raise ValueError("Original accepted Windows wheel changed")
    proof_raw = Path(proof_path).read_bytes()
    if record(proof_raw)["sha256"] != "406c97ca44922c05a10ae04a873e8f43336e2b2bff3b1dc0c29e61d807eb6b10":
        raise ValueError("Original actual Windows import report changed")
    proof = json.loads(proof_raw)
    if proof["source_commit"] != "042ab21c4fa9c7e5ba70c4e2877fb7060d962422":
        raise ValueError("Original source identity changed")
    if wheel_profile(pure_filename, pure_data)["tags"] != ["py3-none-any"]:
        raise ValueError("Current exact pure Python input required before native reuse")
    if native_image:
        with zipfile.ZipFile(io.BytesIO(native_data)) as image:
            old_profile = {'native_artifacts': {name: record(image.read(name)) for name in image.namelist() if name.endswith('.pyd')}}
    else:
        old_profile = wheel_profile(Path(native_path).name, native_data, target="windows")
    if len(old_profile["native_artifacts"]) != len(MODULES):
        raise ValueError("Original complete Windows native inventory required")
    groups = NATIVE_SOURCE_GROUPS
    with zipfile.ZipFile(io.BytesIO(pure_data)) as current, zipfile.ZipFile(io.BytesIO(native_data)) as old:
        files = {n: current.read(n) for n in current.namelist() if not n.endswith("/")}
        source = {n: record(value) for n, value in files.items() if n.startswith("sim2act/")}
        verify_source(pure_data, source, wheel_profile(pure_filename, pure_data))
        reused = {}
        for module, inputs in groups.items():
            if any("sim2act/" + n not in files or "sim2act/" + n not in old.namelist() for n in inputs):
                raise ValueError("Complete original native dependency inventory required")
            if any(files["sim2act/" + n] != old.read("sim2act/" + n) for n in inputs):
                raise ValueError("Native dependency bytes changed; new compilation required: " + module)
            source_hash = hashlib.sha256(b"".join(files["sim2act/" + n] for n in inputs)).hexdigest()
            observed = proof["native"][module]
            path = "sim2act/" + observed["file"]
            value = old.read(path)
            if source_hash != observed["source_sha256"] or record(value) != old_profile["native_artifacts"][path] or record(value) != {k: observed[k] for k in ("bytes", "sha256")}:
                raise ValueError("Native source/actual import/binary witness mismatch")
            pe = inspect(value)
            if pe != observed["pe"] or pe["machine"] != "0x8664" or not pe["pe32plus"] or not pe["dll"] or "PyInit_" + module not in pe["exports"] or "python312.dll" not in [x.lower() for x in pe["imports"]] or source_hash.encode() not in value:
                raise ValueError("Original native PE/ABI/source witness mismatch")
            files[path] = value
            reused[module] = dict(file=path, inputs=inputs, source_sha256=source_hash, **record(value))
    wheel_header = files[META_PREFIX + "WHEEL"]
    if wheel_header.count(b"Root-Is-Purelib: true") != 1 or wheel_header.count(b"Tag: py3-none-any") != 1:
        raise ValueError("Exact source-only wheel header required")
    files[META_PREFIX + "WHEEL"] = wheel_header.replace(b"Root-Is-Purelib: true", b"Root-Is-Purelib: false").replace(b"Tag: py3-none-any", b"Tag: cp312-cp312-win_amd64")
    files.pop(META_PREFIX + "RECORD")
    rows = io.StringIO(newline="")
    writer = csv.writer(rows, lineterminator="\n")
    for name, value in sorted(files.items()):
        writer.writerow([name, "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(value).digest()).rstrip(b"=").decode(), len(value)])
    writer.writerow([META_PREFIX + "RECORD", "", ""])
    files[META_PREFIX + "RECORD"] = rows.getvalue().encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as zipped:
        for name, value in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zipped.writestr(info, value)
    filename = "sim2act-0.1.0-cp312-cp312-win_amd64.whl"
    result = output.getvalue()
    verify_source(result, source, wheel_profile(filename, result, target="windows"))
    return filename, result, dict(status="REUSED_UNCHANGED_NATIVE_NOT_CURRENT_WINDOWS_EXECUTED",
        original_source=proof["source_commit"], original_input=original_record,
        original_wheel=None if native_image else original_record,
        original_input_kind='qualified-windows-image' if native_image else 'qualified-windows-wheel',
        original_actual_import_report=record(proof_raw), setup=record(setup_bytes), modules=reused)
