"""Only mutate the existing owned synthetic protocol source; never create authority."""

import argparse
import hashlib
import json
from pathlib import Path

from sqlalchemy import select, update

from sim2act.conditional_checks import SOURCE_HASH
from sim2act.db import Store, fingerprint, grants, meta, resources

POLICY = (
    Path(__file__).resolve().parents[2]
    / "docs/evidence/model-protocol-preparation-20261006/materials/a-source/policy.txt"
)


def action(root, name):
    root = root.resolve()
    assert (root / "fixture.db").is_file() and (root / "info.json").is_file()
    info = json.loads((root / "info.json").read_text(encoding="utf-8"))
    assert info["bearer"] == "synthetic-protocol-browser-A"
    store = Store("sqlite:///" + str(root / "fixture.db"), test_only=True)
    original = POLICY.read_text(encoding="utf-8")
    assert hashlib.sha256(original.encode()).hexdigest() == SOURCE_HASH
    altered = original + "\nSynthetic native condition source version change."
    altered_hash = hashlib.sha256(altered.encode()).hexdigest()
    try:
        with store.tx() as c:
            row = (
                c.execute(select(resources).where(resources.c.id == info["source"]))
                .mappings()
                .one()
            )
            assert row["project_id"] == info["project"] and row["format"] == "txt"
            assert hashlib.sha256(row["content"].encode()).hexdigest() == row["hash"]
            if name == "change":
                assert row["hash"] == SOURCE_HASH and row["content"] == original
                c.execute(
                    update(resources)
                    .where(resources.c.id == row["id"])
                    .values(content=altered, hash=altered_hash)
                )
            elif name == "restore":
                assert row["hash"] == altered_hash and row["content"] == altered
                c.execute(
                    update(resources)
                    .where(resources.c.id == row["id"])
                    .values(content=original, hash=SOURCE_HASH)
                )
            elif name == "revoke":
                assert row["hash"] == SOURCE_HASH
                existing = (
                    c.execute(
                        select(grants).where(
                            grants.c.project_id == info["project"],
                            grants.c.resource_id == row["id"],
                            grants.c.principal_id == info["user"],
                            grants.c.tool_ref == "resource.read",
                        )
                    )
                    .mappings()
                    .one()
                )
                assert not existing["revoked"]
                c.execute(
                    update(grants)
                    .where(grants.c.id == existing["id"], grants.c.revision == existing["revision"])
                    .values(revoked=True, revision=existing["revision"] + 1)
                )
            else:
                assert name == "snapshot"
            return {
                "kind": "owned-conditional-native-fixture.v1",
                "action": name,
                "tables": {
                    n: fingerprint(
                        [
                            dict(r)
                            for r in c.execute(
                                select(t).order_by(*t.primary_key.columns)
                            ).mappings()
                        ]
                    )
                    for n, t in meta.tables.items()
                },
                "grants": c.execute(select(grants.c.id)).scalars().all(),
                "principals": fingerprint(
                    [
                        dict(r)
                        for r in c.execute(
                            select(meta.tables["principals"]).order_by(
                                meta.tables["principals"].c.id
                            )
                        ).mappings()
                    ]
                ),
                "real_model_requests": 0,
            }
    finally:
        store.engine.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--action", choices=["snapshot", "change", "restore", "revoke"], required=True
    )
    args = parser.parse_args()
    print(json.dumps(action(args.root, args.action)))


if __name__ == "__main__":
    main()
