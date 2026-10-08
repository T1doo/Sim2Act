"""Export selected run receipts; redact only temporary URL credentials."""

import hashlib
import json
import re
import sys
from pathlib import Path


def main(root, destination):
    destination.mkdir(parents=True, exist_ok=False)
    manifest = []
    paths = sorted([*root.glob("*.json"), *root.glob("*.xml"), *root.glob("*.log")])
    paths.extend(p for p in (root / "node-tools").glob("package*.json"))
    for path in paths:
        relative = path.relative_to(root)
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        safe, redactions = re.subn(
            r"(postgres(?:ql)?(?:\+[a-z]+)?://[^:\s/@]+:)[^@\s]+(@)",
            r"\1TEMPORARY_CREDENTIAL_REDACTED\2", text,
        )
        encoded = safe.encode("utf-8")
        output = destination / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encoded)
        assert output.read_bytes() == encoded
        manifest.append({"path": str(relative), "raw_sha256": hashlib.sha256(raw).hexdigest(),
                         "export_sha256": hashlib.sha256(encoded).hexdigest(),
                         "raw_bytes": len(raw), "export_bytes": len(encoded),
                         "temporary_url_credential_redactions": redactions})
    (destination / "export-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print("Verified exports:", len(manifest))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
