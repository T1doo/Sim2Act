"""Only mutate the existing owned synthetic protocol source; never create authority."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

POLICY = (
    Path(__file__).resolve().parents[2]
    / "docs/evidence/model-protocol-preparation-20261006/materials/a-source/policy.txt"
)


def action(root, name):
    from sqlalchemy import func, select, update

    from sim2act.conditional_checks import SOURCE_HASH
    from sim2act.db import Store, attempts, fingerprint, grants, meta, operations, resources

    root = root.resolve()
    if not (root / "fixture.db").is_file() or not (root / "info.json").is_file():
        raise ValueError("Existing owned fixture required")
    info = json.loads((root / "info.json").read_text(encoding="utf-8"))
    if info["bearer"] != "synthetic-protocol-browser-A":
        raise ValueError("Existing synthetic protocol owner required")
    if name in {"run-source", "run-extract", "run-cold"}:
        from run_fixture import work

        return work(root, name.removeprefix("run-"))
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
                "attempts_count": c.execute(select(func.count()).select_from(attempts)).scalar_one(),
                "resource_reads_count": c.execute(select(func.count()).select_from(operations).where(
                    operations.c.tool_ref == "resource.read", operations.c.status == "VERIFIED"
                )).scalar_one(),
            }
    finally:
        store.engine.dispose()


def session_request(line):
    request = json.loads(line)
    if type(request) is not dict or set(request) != {"action"}:
        raise ValueError("Expected one bounded fixture action")
    if type(request["action"]) is not str or request["action"] not in {
        "snapshot", "change", "restore", "revoke", "run-source", "run-extract", "run-cold"
    }:
        raise ValueError("Unsupported fixture action")
    return request["action"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--action", choices=["snapshot", "change", "restore", "revoke", "run-source", "run-extract", "run-cold"])
    mode.add_argument("--session", action="store_true")
    args = parser.parse_args()
    if args.session:
        # Same bounded actions and transactions; EOF from the owned caller ends the process.
        for line in sys.stdin:
            print(json.dumps(action(args.root, session_request(line))), flush=True)
    else:
        print(json.dumps(action(args.root, args.action)))


if __name__ == "__main__":
    main()
