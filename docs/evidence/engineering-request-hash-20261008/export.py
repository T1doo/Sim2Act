"""Export only a completed owned run, preserving raw bytes after decompression."""

import gzip
import hashlib
import json
import sys
from pathlib import Path

source, target = map(Path, sys.argv[1:3])
result = json.loads((source / "result.json").read_text())
cleanup = json.loads((source / "cleanup.json").read_text())
assert result["complete"] and result["pytest_exit_code"] == 0
assert cleanup["owner_label_verified"] and cleanup["owned_container_absent"]
assert all(row["absent"] for row in cleanup["owned_volume_absence"])
assert all(v == 0 for v in json.loads((source / "census-after.json").read_text()).values())
target.mkdir(parents=True, exist_ok=False)
paths = [p for p in source.iterdir() if p.is_file()]
for path in (source / "fixtures").rglob("*"):
    if (
        path.is_file()
        and path.name in {"driver.log", "results.json", "pg-control-race.json", "pg-rollback.json"}
        and "current" not in path.relative_to(source / "fixtures").parts
    ):
        paths.append(path)
rows = []
for path in sorted(paths):
    relative = path.relative_to(source)
    data = path.read_bytes()
    compressed = path.suffix == ".jsonl" or path.name in {
        "snapshot-hashes.json",
        "hotspot-groups.json",
    }
    output = target / (str(relative) + (".gz" if compressed else ""))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(gzip.compress(data, mtime=0) if compressed else data)
    assert (gzip.decompress(output.read_bytes()) if compressed else output.read_bytes()) == data
    rows.append(
        {
            "source": str(relative),
            "artifact": str(output.relative_to(target)),
            "raw_bytes": len(data),
            "raw_sha256": hashlib.sha256(data).hexdigest(),
            "artifact_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        }
    )
(target / "export-manifest.json").write_text(
    json.dumps({"source": str(source), "files": rows}, indent=2) + "\n"
)
print(json.dumps({"files": len(rows), "target": str(target)}))
