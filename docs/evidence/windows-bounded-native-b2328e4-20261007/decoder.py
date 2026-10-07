#!/usr/bin/env python3
"""Bounded decoder for the named SIM2ACT_BROWSER_* GitHub log emissions."""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, Iterable

WORK_ROOT = Path("/tmp/sim2act-native-ci-b2328")
DEFAULT_LOG = WORK_ROOT / "job.log"
OUTPUT_DIR = WORK_ROOT / "emitted-source"
MAX_FILE_BYTES = 2_000_000
MAX_LOG_BYTES = 128 * 1024 * 1024
MAX_LINE_BYTES = 8192
CHUNK_CHARS = 4000
ALLOWED_NAMES = (
    "browser-results.json",
    "desktop.png",
    "mobile.png",
    "failure.png",
    "agent-results.json",
    "agent-desktop.png",
    "agent-narrow.png",
    "agent-failure.png",
    "protocol-results.json",
    "protocol-desktop.png",
    "protocol-narrow.png",
)
ALLOWED = frozenset(ALLOWED_NAMES)
SOURCE = {
    "provider": "GitHub Actions",
    "repository": "T1doo/Sim2Act",
    "commit": "b2328e45e7d80162c9458fabb81cbbf6ae441e76",
    "run_id": 37621453354,
    "run_attempt": 1,
    "job_id": 112792480092,
}
FILE_PREFIX = "SIM2ACT_BROWSER_FILE "
CHUNK_PREFIX = "SIM2ACT_BROWSER_CHUNK "
TIMESTAMP_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z (.*)$")
CHUNK_LINE = re.compile(r"^SIM2ACT_BROWSER_CHUNK ([^ ]+) (0|[1-9][0-9]*) ([A-Za-z0-9+/=]+)$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class DecodeError(Exception):
    """Safe diagnostic for malformed or out-of-scope log emissions."""


@dataclass
class ActiveFile:
    name: str
    byte_count: int
    sha256: str
    chunk_count: int
    chunks: dict[int, str] = field(default_factory=dict)
    next_index: int = 0

    @property
    def encoded_length(self) -> int:
        return 4 * ((self.byte_count + 2) // 3)


@dataclass
class DecodeResult:
    files: dict[str, bytes]
    log_bytes: int
    log_sha256: str
    lines: int
    chunk_lines: int


def _validate_name(name: object) -> str:
    if not isinstance(name, str) or not name:
        raise DecodeError("invalid emitted name")
    if "/" in name or "\\" in name or name in {".", ".."}:
        raise DecodeError("path traversal or path separator in emitted name")
    if name not in ALLOWED:
        raise DecodeError("emitted name is outside the explicit whitelist")
    return name


def _json_without_duplicate_keys(text: str) -> dict:
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise DecodeError("duplicate JSON header field")
            result[key] = value
        return result

    try:
        value = json.loads(text, object_pairs_hook=unique_pairs)
    except DecodeError:
        raise
    except (json.JSONDecodeError, UnicodeError):
        raise DecodeError("malformed emission header JSON") from None
    if not isinstance(value, dict):
        raise DecodeError("emission header is not a JSON object")
    return value


def _parse_header(text: str) -> ActiveFile:
    obj = _json_without_duplicate_keys(text)
    if set(obj) != {"name", "bytes", "sha256", "chunks"}:
        raise DecodeError("emission header fields do not match the source schema")
    name = _validate_name(obj["name"])
    byte_count = obj["bytes"]
    chunk_count = obj["chunks"]
    digest = obj["sha256"]
    if type(byte_count) is not int or byte_count < 0:
        raise DecodeError("invalid declared byte count")
    if byte_count > MAX_FILE_BYTES:
        raise DecodeError("emitted file exceeds the 2,000,000-byte bound")
    if type(chunk_count) is not int or chunk_count < 0:
        raise DecodeError("invalid declared chunk count")
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        raise DecodeError("invalid declared SHA-256")
    encoded_length = 4 * ((byte_count + 2) // 3)
    expected_chunks = (encoded_length + CHUNK_CHARS - 1) // CHUNK_CHARS
    if chunk_count != expected_chunks:
        raise DecodeError("declared chunk count does not match declared size")
    return ActiveFile(name, byte_count, digest, chunk_count)


def _extract_emission_line(line: str) -> str | None:
    # GitHub's concatenated job-log stream can place a UTF-8 BOM before a timestamp.
    if line.startswith("\ufeff"):
        line = line[1:]
    if line.startswith("SIM2ACT_BROWSER_"):
        return line
    match = TIMESTAMP_PREFIX.match(line)
    if match and match.group(1).startswith("SIM2ACT_BROWSER_"):
        return match.group(1)
    if "SIM2ACT_BROWSER_" in line:
        raise DecodeError("malformed or unsupported emission line prefix")
    return None


def _finish_file(active: ActiveFile, files: dict[str, bytes]) -> None:
    if len(active.chunks) != active.chunk_count:
        raise DecodeError("emitted chunk count is incomplete")
    if set(active.chunks) != set(range(active.chunk_count)):
        raise DecodeError("emitted chunk indices are not contiguous")
    encoded = "".join(active.chunks[index] for index in range(active.chunk_count))
    if len(encoded) != active.encoded_length:
        raise DecodeError("encoded payload size does not match the declaration")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise DecodeError("invalid base64 payload") from None
    if base64.b64encode(data).decode("ascii") != encoded:
        raise DecodeError("non-canonical base64 payload")
    if len(data) != active.byte_count:
        raise DecodeError("decoded byte count does not match the declaration")
    actual_sha = hashlib.sha256(data).hexdigest()
    if actual_sha != active.sha256:
        raise DecodeError("decoded SHA-256 does not match the declaration")
    files[active.name] = data


def decode_log(stream: BinaryIO) -> DecodeResult:
    files: dict[str, bytes] = {}
    headers: set[str] = set()
    active: ActiveFile | None = None
    log_hash = hashlib.sha256()
    log_bytes = 0
    lines = 0
    chunk_lines = 0
    saw_marker = False

    while True:
        raw_line = stream.readline(MAX_LINE_BYTES + 1)
        if not raw_line:
            break
        lines += 1
        log_bytes += len(raw_line)
        if log_bytes > MAX_LOG_BYTES:
            raise DecodeError("raw GitHub log exceeds the 128 MiB processing bound")
        if len(raw_line) > MAX_LINE_BYTES:
            raise DecodeError("raw GitHub log contains a line over the 8,192-byte bound")
        log_hash.update(raw_line)
        line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
        message = _extract_emission_line(line)
        if message is None:
            continue
        saw_marker = True

        if message.startswith(FILE_PREFIX):
            if active is not None:
                _finish_file(active, files)
                active = None
            active = _parse_header(message[len(FILE_PREFIX):])
            if active.name in headers:
                raise DecodeError("duplicate emission header")
            headers.add(active.name)
            continue

        if message.startswith(CHUNK_PREFIX):
            parsed = CHUNK_LINE.fullmatch(message)
            if not parsed:
                raise DecodeError("malformed emission chunk line")
            name = _validate_name(parsed.group(1))
            index = int(parsed.group(2))
            encoded_chunk = parsed.group(3)
            if active is None:
                raise DecodeError("chunk appeared without an active file header")
            if name != active.name:
                raise DecodeError("chunk name does not match the active file header")
            if index in active.chunks:
                raise DecodeError("duplicate chunk id")
            if index != active.next_index:
                raise DecodeError("chunk indices are noncontiguous or out of order")
            if index >= active.chunk_count:
                raise DecodeError("chunk index exceeds the declared chunk count")
            expected_chunk_length = (
                CHUNK_CHARS
                if index < active.chunk_count - 1
                else active.encoded_length - CHUNK_CHARS * (active.chunk_count - 1)
            )
            if len(encoded_chunk) != expected_chunk_length:
                raise DecodeError("chunk length does not match its declared position")
            try:
                base64.b64decode(encoded_chunk, validate=True)
            except (binascii.Error, ValueError):
                raise DecodeError("invalid base64 chunk") from None
            if index < active.chunk_count - 1 and "=" in encoded_chunk:
                raise DecodeError("padding appeared before the final base64 chunk")
            active.chunks[index] = encoded_chunk
            active.next_index += 1
            chunk_lines += 1
            continue

        raise DecodeError("unsupported SIM2ACT_BROWSER emission record")

    if active is not None:
        _finish_file(active, files)
    if not saw_marker or not files:
        raise DecodeError("no complete whitelisted emissions were found")
    return DecodeResult(files, log_bytes, log_hash.hexdigest(), lines, chunk_lines)


def _receipt(result: DecodeResult, log_path: Path) -> dict:
    file_records = []
    for name, data in result.files.items():
        file_records.append({
            "name": name,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    return {
        "schema": "sim2act.browser-ci-emission-receipt.v1",
        "source": SOURCE,
        "scope": {
            "description": "Explicitly whitelisted synthetic browser, agent, and protocol CI emissions",
            "allowed_names": list(ALLOWED_NAMES),
            "max_bytes_per_file": MAX_FILE_BYTES,
        },
        "log": {
            "path": str(log_path),
            "bytes": result.log_bytes,
            "sha256": result.log_sha256,
        },
        "files": file_records,
        "checks": {
            "complete_headers": len(file_records),
            "validated_chunks": result.chunk_lines,
            "decoded_files": len(file_records),
            "all_sizes_and_hashes_match": True,
        },
    }


def write_outputs(result: DecodeResult, log_path: Path) -> dict:
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    if os.path.lexists(OUTPUT_DIR):
        raise DecodeError("emitted output directory already exists; refusing to overwrite evidence")
    stage = Path(tempfile.mkdtemp(prefix=".emitted-stage-", dir=WORK_ROOT))
    try:
        for name, data in result.files.items():
            safe_name = _validate_name(name)
            (stage / safe_name).write_bytes(data)
        (stage / "emission-receipt.json").write_text(
            json.dumps(_receipt(result, log_path), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(stage, OUTPUT_DIR)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return _receipt(result, log_path)


def _make_header(name: str, data: bytes, *, byte_count: int | None = None,
                 digest: str | None = None, chunks: int | None = None) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    obj = {
        "name": name,
        "bytes": len(data) if byte_count is None else byte_count,
        "sha256": hashlib.sha256(data).hexdigest() if digest is None else digest,
        "chunks": (len(encoded) + CHUNK_CHARS - 1) // CHUNK_CHARS if chunks is None else chunks,
    }
    return FILE_PREFIX + json.dumps(obj, separators=(",", ":"))


def _make_chunks(name: str, data: bytes) -> list[str]:
    encoded = base64.b64encode(data).decode("ascii")
    return [
        f"{CHUNK_PREFIX}{name} {index} {encoded[start:start + CHUNK_CHARS]}"
        for index, start in enumerate(range(0, len(encoded), CHUNK_CHARS))
    ]


def self_test() -> dict:
    cases: list[dict] = []

    def run_case(name: str, lines: Iterable[str], *, should_pass: bool) -> None:
        content = ("\n".join(lines) + "\n").encode("utf-8")
        try:
            result = decode_log(io.BytesIO(content))
        except DecodeError:
            passed = not should_pass
        else:
            passed = should_pass
            if should_pass:
                passed = result.files == expected
        cases.append({"case": name, "passed": passed, "expected": "accept" if should_pass else "reject"})

    multi = bytes((i % 251 for i in range(5003)))
    empty = b""
    expected = {"desktop.png": multi, "protocol-results.json": empty}
    run_case(
        "valid timestamped multichunk plus empty file",
        [
            "ordinary CI output",
            _make_header("desktop.png", multi),
            *_make_chunks("desktop.png", multi),
            "\ufeff2026-10-07T08:10:11.1234567Z " + _make_header("protocol-results.json", empty),
        ],
        should_pass=True,
    )

    b = b"x"
    base_header = _make_header("desktop.png", b)
    base_chunk = _make_chunks("desktop.png", b)[0]
    negative_cases = [
        ("reject unapproved filename", [_make_header("secrets.env", b), _make_chunks("secrets.env", b)[0]]),
        ("reject path traversal", [_make_header("../desktop.png", b), f"{CHUNK_PREFIX}../desktop.png 0 eA=="]),
        ("reject duplicate header", [base_header, base_chunk, base_header, base_chunk]),
        ("reject duplicate chunk id", [base_header, base_chunk, base_chunk]),
        ("reject invalid base64", [base_header, f"{CHUNK_PREFIX}desktop.png 0 !!!!"]),
        ("reject noncontiguous chunk ids", [
            _make_header("desktop.png", bytes(range(256)) * 28),
            f"{CHUNK_PREFIX}desktop.png 0 " + base64.b64encode(bytes(range(256)) * 28).decode("ascii")[:4000],
            f"{CHUNK_PREFIX}desktop.png 2 " + base64.b64encode(bytes(range(256)) * 28).decode("ascii")[8000:],
        ]),
        ("reject declared chunk count mismatch", [_make_header("desktop.png", b, chunks=0)]),
        ("reject decoded size mismatch", [_make_header("desktop.png", b"xx", byte_count=2, digest=hashlib.sha256(b"xx").hexdigest()), f"{CHUNK_PREFIX}desktop.png 0 eA=="]),
        ("reject hash mismatch", [_make_header("desktop.png", b, digest="0" * 64), base_chunk]),
        ("reject per-file size bound", [_make_header("desktop.png", b"", byte_count=MAX_FILE_BYTES + 1, digest="0" * 64, chunks=667)]),
        ("reject duplicate JSON header field", [FILE_PREFIX + '{"name":"desktop.png","name":"desktop.png","bytes":1,"sha256":"' + hashlib.sha256(b).hexdigest() + '","chunks":1}', base_chunk]),
    ]
    expected = {}
    for name, lines in negative_cases:
        run_case(name, lines, should_pass=False)

    failed = sum(not case["passed"] for case in cases)
    return {"self_test": True, "passed": len(cases) - failed, "failed": failed, "cases": cases}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run offline synthetic parser checks")
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG, help="raw GitHub job log path")
    args = parser.parse_args(argv)
    if args.self_test:
        report = self_test()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["failed"] == 0 else 1
    try:
        with args.log.open("rb") as stream:
            result = decode_log(stream)
        receipt = write_outputs(result, args.log)
    except (OSError, DecodeError) as exc:
        print(json.dumps({"decoded": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps({"decoded": True, "receipt": receipt}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
