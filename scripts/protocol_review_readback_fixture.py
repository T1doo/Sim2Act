"""Exact sealed Source+Cold input for one GET-only native window; no producer."""

import gzip
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / "docs/evidence/protocol-cold-review-http-20261022"


def required_files():
    return ["scripts/protocol_review_readback_fixture.py"] + [
        str((EVIDENCE / p).relative_to(REPO))
        for p in ["fixture.json", "MANIFEST.json", "runtime/after.sqlite.gz"]
        + ["fixture/" + n for n in json.loads((EVIDENCE / "fixture.json").read_text())["sidecars"]]
    ]


def prepare(root):
    fixture = json.loads((EVIDENCE / "fixture.json").read_text())
    manifest = json.loads((EVIDENCE / "MANIFEST.json").read_text())
    archive = (EVIDENCE / "runtime/after.sqlite.gz").read_bytes()
    assert (
        dict(bytes=len(archive), sha256=hashlib.sha256(archive).hexdigest())
        == manifest["runtime/after.sqlite.gz"]
    )
    (root / "fixture.sqlite").write_bytes(gzip.decompress(archive))
    paths = []
    for name, witness in fixture["sidecars"].items():
        data = (EVIDENCE / "fixture" / name).read_bytes()
        assert (
            len(data) == witness["bytes"] and hashlib.sha256(data).hexdigest() == witness["sha256"]
        )
        path = root / name
        path.write_bytes(data)
        path.with_suffix(".lock").write_bytes(b"")
        paths.append(path)
    original = dict(
        run=fixture["source_run"],
        cold=fixture["run"],
        project=fixture["project"],
        user=fixture["user"],
        resume_at=fixture["business_at"],
        settings=fixture["api_settings"],
        captured={},
    )
    return original, paths


def cases(store, original):
    from sim2act.protocol_jobs import inspect
    from sim2act.protocol_reviews import read_receipt

    output = []
    for rid, phase in [(original["run"], "source"), (original["cold"], "cold")]:
        locator = read_receipt(store, original["user"], original["project"], rid)
        current = inspect(store, original["user"], rid)
        assert locator["state"] == "FOUND" and locator["phase"] == current["phase"] == phase
        assert current["status"] == "SUCCEEDED" and current["semantic_status"] == "PASS"
        assert (
            current["owner_semantic_acceptance"] == "PENDING"
            and current["formal_publication_enabled"] is False
        )
        output.append(dict(locator=locator, current=current))
    return output
