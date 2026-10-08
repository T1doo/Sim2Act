"""Byte-verified export of completed owned runs; no source or DB mutation."""

import gzip
import hashlib
import json
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])
result = json.loads((source / "result.json").read_text())
cleanup = json.loads((source / "cleanup.json").read_text())
assert result["complete"] and cleanup["owned_container_absent"]
assert all(r["absent"] for r in cleanup["owned_volume_absence"])
assert json.loads((source / "census-after.json").read_text()) == {
    "test_schemas": 0,
    "test_roles": 0,
    "public_tables": 0,
}
target.mkdir(parents=True, exist_ok=False)
paths = [p for p in source.iterdir() if p.is_file()]
allowed = {
    "driver.log",
    "driver-progress.jsonl",
    "info.json",
    "results.json",
    "failure.json",
    "resources-graph-pg-lock.json",
}
for directory in (source / "fixtures").iterdir():
    if directory.is_dir() and not directory.is_symlink():
        paths.extend(p for p in directory.iterdir() if p.is_file() and p.name in allowed)
rows = []
for path in sorted(paths):
    relative = path.relative_to(source)
    raw = path.read_bytes()
    compressed = len(raw) > 512_000 or path.suffix == ".jsonl"
    output = target / (str(relative) + (".gz" if compressed else ""))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(gzip.compress(raw, mtime=0) if compressed else raw)
    verified = gzip.decompress(output.read_bytes()) if compressed else output.read_bytes()
    assert verified == raw
    rows.append(
        {
            "source": str(relative),
            "artifact": str(output.relative_to(target)),
            "raw_bytes": len(raw),
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "artifact_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "byte_equal_after_decompression": True,
        }
    )
(target / "export-manifest.json").write_text(
    json.dumps(
        {
            "source": str(source),
            "files": rows,
            "limits": "Only completed owned-run receipts and selected DOM/concurrency fixture artifacts; raw log whitespace retained. No original-instance files.",
        },
        indent=2,
    )
    + "\n"
)
print(
    json.dumps(
        {"files": len(rows), "raw_bytes": sum(r["raw_bytes"] for r in rows), "target": str(target)}
    )
)
