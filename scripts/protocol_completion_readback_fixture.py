"""Two independent sealed completed stores; no merging or new business facts."""

import gzip
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def required_files():
    return ["scripts/protocol_completion_readback_fixture.py"] + [
        f"docs/evidence/protocol-{phase}-process-recovery-20261022/{name}"
        for phase in ("source", "extract")
        for name in (
            "MANIFEST.json",
            "original.json",
            "after.sqlite.gz",
            "original-received-sidecar.json",
        )
    ]


def prepare(root):
    originals, sidecars = [], []
    for phase, database in (("source", "fixture.sqlite"), ("extract", "extract.sqlite")):
        evidence = REPO / f"docs/evidence/protocol-{phase}-process-recovery-20261022"
        manifest = json.loads((evidence / "MANIFEST.json").read_text())

        def sealed(name, evidence=evidence, manifest=manifest):
            data = (evidence / name).read_bytes()
            witness = manifest[name]
            digest = witness if isinstance(witness, str) else witness["sha256"]
            assert hashlib.sha256(data).hexdigest() == digest
            return data

        original = json.loads(sealed("original.json"))
        (root / database).write_bytes(gzip.decompress(sealed("after.sqlite.gz")))
        sidecar = root / (original["run"] + ".json")
        sidecar.write_bytes(sealed("original-received-sidecar.json"))
        sidecar.with_suffix(".lock").write_bytes(b"")
        originals.append(original)
        sidecars.append(sidecar)
    return originals, sidecars


def cases(stores, settings, originals):
    from sim2act.protocol_completion_readback import read_receipt
    from sim2act.protocol_jobs import inspect

    output = []
    for phase, store, config, original in zip(
        ("source", "extract"), stores, settings, originals, strict=True
    ):
        locator = read_receipt(
            store, original["user"], original["project"], original["run"], config
        )
        current = inspect(store, original["user"], original["run"])
        assert locator["phase"] == current["phase"] == phase and locator["state"] == "FOUND"
        assert current["status"] == ("WAITING_APPROVAL" if phase == "source" else "SUCCEEDED")
        assert (
            current["owner_semantic_acceptance"] == "PENDING"
            and current["formal_publication_enabled"] is False
        )
        output.append(dict(project=original["project"], current=current, locator=locator))
    return output
