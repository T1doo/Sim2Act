"""Export a completed owned final run, with reversible compression and hashes."""

import gzip
import hashlib
import json
import sys
from pathlib import Path

source, target = map(Path, sys.argv[1:3])
result = json.loads((source / "result.json").read_text())
cleanup = json.loads((source / "cleanup.json").read_text())
assert result["complete"] and cleanup["owner_label_verified"] and cleanup["owned_container_absent"]
assert all(row["absent"] for row in cleanup["owned_volume_absence"])
assert all(v == 0 for v in json.loads((source / "census-after.json").read_text()).values())
target.mkdir(parents=True, exist_ok=False)
paths = [p for p in source.iterdir() if p.is_file()]
fixture_names = {
    "driver.log",
    "driver-progress.jsonl",
    "resources-graph-pg-lock.json",
    "pg-runtime-role.json",
    "pg-control-race.json",
    "pg-two-workers.json",
    "pg-rollback.json",
}
for path in (source / "fixtures").rglob("*"):
    if (
        path.is_file()
        and (path.name in fixture_names or path.suffix == ".log")
        and "current" not in path.relative_to(source / "fixtures").parts
    ):
        paths.append(path)
rows = []
for path in sorted(paths):
    relative = path.relative_to(source)
    data = path.read_bytes()
    compressed = path.suffix == ".jsonl" or path.name == "exception-audit.json"
    output = target / (str(relative) + (".gz" if compressed else ""))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(gzip.compress(data, mtime=0) if compressed else data)
    check = gzip.decompress(output.read_bytes()) if compressed else output.read_bytes()
    assert check == data
    rows.append(
        {
            "source": str(relative),
            "artifact": str(output.relative_to(target)),
            "raw_bytes": len(data),
            "raw_sha256": hashlib.sha256(data).hexdigest(),
            "artifact_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "byte_equal_after_decompression": True,
        }
    )
(target / "export-manifest.json").write_text(
    json.dumps(
        {
            "source": str(source),
            "files": rows,
            "limits": "Only this completed owned run and selected PG/DOM receipts; raw log/XML whitespace kept. Subprocess HTTP statuses not exhaustively instrumented; fixture-log scan records observable exceptions separately.",
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
