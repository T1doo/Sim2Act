"""Decode the authorized job-log originals; no network or application execution."""

import base64
import hashlib
import json
import re
import sys
from pathlib import Path

LOG_SHA = "3dc44d4d43e23532a33ad20b6502ed7ede2ae749671d218ebf202e074f224dda"
EXPECTED = {
    "launch-contract.json": 3540,
    "inventory.json": 1269,
    "result.json": 2205,
    "browser.json": 14290,
    "initial.png": 68833,
    "unknown.png": 70477,
    "completed.png": 60155,
}


def main(log, output):
    raw = log.read_bytes()
    assert len(raw) == 318247 and hashlib.sha256(raw).hexdigest() == LOG_SHA
    text = raw.decode("utf-8")
    headers, chunks = {}, {}
    for match in re.finditer(r"SIM2ACT_SOURCE_UI_FILE ", text):
        value, _ = json.JSONDecoder().raw_decode(text[match.end() :])
        name = value["name"]
        assert name in EXPECTED and name not in headers
        assert value["bytes"] == EXPECTED[name]
        headers[name] = value
    for match in re.finditer(r"SIM2ACT_SOURCE_UI_CHUNK (\S+) (\d+) ([A-Za-z0-9+/=]+)", text):
        name, index, content = match.groups()
        assert name in EXPECTED
        parts = chunks.setdefault(name, {})
        assert int(index) not in parts
        parts[int(index)] = content
    assert set(headers) == set(chunks) == set(EXPECTED)
    output.mkdir(exist_ok=False)
    result = {}
    for name, header in headers.items():
        parts = chunks[name]
        assert set(parts) == set(range(header["chunks"]))
        data = base64.b64decode("".join(parts[i] for i in range(header["chunks"])), validate=True)
        assert len(data) == EXPECTED[name] and hashlib.sha256(data).hexdigest() == header["sha256"]
        (output / name).write_bytes(data)
        result[name] = dict(bytes=len(data), sha256=header["sha256"], chunks=header["chunks"])
    (output / "decoded-manifest.json").write_text(json.dumps(result, indent=2))
    print(
        json.dumps(
            dict(status="VERIFIED", files=len(result), log_bytes=len(raw), log_sha256=LOG_SHA)
        )
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
