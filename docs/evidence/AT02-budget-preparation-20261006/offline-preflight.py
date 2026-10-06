"""One disposable two-owner fixture; offline shape replay, never live transport."""

import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import (
    Store,
    attempts,
    grants,
    operations,
    principals,
    projects,
    reservations,
    resources,
    runs,
)
from sim2act.errors import DomainError
from sim2act.model import require_returned_model, returned_model_identity
from sim2act.worker import Worker

repo = Path(__file__).resolve().parents[3]
out = Path(__file__).resolve().parent
history = repo / "docs/evidence/LIVE-20261005"
hashes = json.loads((history / "evidence-hashes.json").read_text())["files"]
for item in hashes:
    data = (history / item["path"]).read_bytes()
    assert len(data) == item["bytes"] and hashlib.sha256(data).hexdigest() == item["sha256"]
old = json.loads((history / "dd195681-short-run.json").read_text())
assert old["external_model_requests"] == 2 and old["budget_remaining"] == 0
assert old["run_readback"]["status"] == "PARTIAL"
assert old["run_readback"]["result"]["answer"].strip() == "42"
assert [x["role"] for x in old["persisted_context"]["messages"]] == [
    "system",
    "user",
    "assistant",
    "tool",
    "assistant",
]
assert len(old["operations"]) == 1 and old["operations"][0]["status"] == "VERIFIED"
assert all(x["status"] == "RECEIVED" for x in old["attempts"])

report = {
    "kind": "OFFLINE MOCK shape replay + real local API/worker/store fixture; NOT LIVE acceptance",
    "external_model_requests": 0,
    "approved_live_budget": 0,
    "history_hash_files": len(hashes),
    "history_core_chain": "PASS; historical one-owner initial state still incomplete",
    "cases": [],
    "source_commit": sys.argv[1],
    "checks": [],
}


def check(name, condition):
    assert condition, name
    report["checks"].append(name)


with tempfile.TemporaryDirectory(prefix="sim2act-at02-offline-") as root:
    store = Store("sqlite:///" + str(Path(root) / "fixture.db"), test_only=True)
    store.initialize()  # Explicit owned test fixture, not API DDL.
    settings = Settings(
        str(store.engine.url),
        Path(root),
        mode="mock",
        live_enabled=False,
        max_requests=2,
        max_tools=1,
        max_repairs=0,
        max_output_tokens=512,
        max_total_tokens=5000,
    )
    users = [
        store.user("synthetic A", "synthetic-offline-A"),
        store.user("synthetic B", "synthetic-offline-B"),
    ]
    with TestClient(create_app(store, settings)) as client:
        pids, rids = [], []
        for n in range(2):
            client.headers["Authorization"] = "Bearer synthetic-offline-" + ("A" if n == 0 else "B")
            pid = client.post("/api/projects", json={"name": "synthetic " + str(n)}).json()["id"]
            rid = client.post(
                f"/api/projects/{pid}/resources",
                json={"name": "value.txt", "format": "txt", "content": "42" if n == 0 else "84"},
            ).json()["id"]
            pids.append(pid)
            rids.append(rid)
        # Normal resource intake grants CSV capability too. Revoke it in this owned fixture;
        # retain only active read intersections, do not change product grant behavior.
        with store.tx() as c:
            c.execute(
                update(grants).where(grants.c.tool_ref != "resource.read").values(revoked=True)
            )
            start = {
                table.name: [dict(x) for x in c.execute(select(table)).mappings()]
                for table in [principals, projects, grants, resources]
            }
        runtime = [x["runtime_id"] for x in start["projects"]]
        check(
            "two users / two projects / two distinct runtime identities",
            len(start["principals"]) == 4 and len(set(users + runtime)) == 4 and len(pids) == 2,
        )
        active = [g for g in start["grants"] if not g["revoked"]]
        check(
            "only four active owner/runtime resource.read grants, each project isolated",
            len(active) == 4
            and all(
                g["tool_ref"] == "resource.read"
                and g["principal_id"]
                in [users[pids.index(g["project_id"])], runtime[pids.index(g["project_id"])]]
                and g["resource_id"] == rids[pids.index(g["project_id"])]
                for g in active
            ),
        )
        negatives = []
        for n in range(2):
            other = 1 - n
            client.headers["Authorization"] = "Bearer synthetic-offline-" + ("A" if n == 0 else "B")
            for method, url, body in [
                ("GET", f"/api/resources/{rids[other]}", None),
                ("GET", f"/api/projects/{pids[other]}/runs", None),
                (
                    "POST",
                    f"/api/projects/{pids[other]}/runs",
                    {
                        "goal": "Read; echo.",
                        "resource_refs": [rids[other]],
                        "request_key": "deny-owner",
                    },
                ),
                (
                    "POST",
                    f"/api/projects/{pids[n]}/runs",
                    {
                        "goal": "Read; echo.",
                        "resource_refs": [rids[other]],
                        "request_key": "deny-resource",
                    },
                ),
            ]:
                response = client.request(method, url, **({"json": body} if body else {}))
                negatives.append({"owner": n, "scope": url, "status": response.status_code})
                check(
                    "cross-owner/project/resource rejection " + str(n) + " " + url,
                    response.status_code == 403 and '"content"' not in response.text,
                )
            with store.tx() as c:
                try:
                    store.authorize(c, users[n], runtime[other], pids[n], rids[n], "resource.read")
                except DomainError:
                    pass
                else:
                    raise AssertionError("foreign runtime accepted")
        # Test both halves of the permission intersection within rollback-only transactions.
        for who in [users[0], runtime[0]]:
            with store.tx() as c:
                c.execute(
                    update(grants)
                    .where(grants.c.principal_id == who, grants.c.tool_ref == "resource.read")
                    .values(revoked=True)
                )
                try:
                    store.authorize(c, users[0], runtime[0], pids[0], rids[0], "resource.read")
                except DomainError as error:
                    check("revoked intersection rejects " + who, error.code == "GRANT_REVOKED")
                else:
                    raise AssertionError("revoked intersection accepted")
                c.rollback()
        report["starting_fixture"] = start
        report["negative_http"] = negatives
        client.headers["Authorization"] = "Bearer synthetic-offline-A"
        response = client.post(
            f"/api/projects/{pids[0]}/runs",
            json={"goal": "Read; echo.", "resource_refs": [rids[0]], "request_key": "at02-offline"},
        )
        check("one accepted MOCK intent", response.status_code == 202)
        run_id = response.json()["run_id"]
        seen = []

        class ShapeReplay:
            def request(self, messages, tools):
                check("no third offline round", len(seen) < 2)
                body = {
                    "model": "intern-s2",
                    "messages": messages,
                    "tools": tools,
                    "stream": False,
                    "max_tokens": 512,
                }
                wire = httpx.Request(
                    "POST", "https://chat.intern-ai.org.cn/api/v1/chat/completions", json=body
                ).content
                seen.append(
                    {
                        "characters": len(wire.decode()),
                        "utf8_bytes": len(wire),
                        "body_sha256": hashlib.sha256(wire).hexdigest(),
                        "roles": [m["role"] for m in messages],
                        "max_tokens": 512,
                        "full_body": copy.deepcopy(body),
                    }
                )
                # Historical public message shape only. Resource ID rebound to this fixture.
                msg = copy.deepcopy(
                    old["persisted_context"]["messages"][2 if len(seen) == 1 else 4]
                )
                if len(seen) == 1:
                    msg["tool_calls"][0]["function"]["arguments"] = json.dumps(
                        {"resource_id": rids[0]}
                    )
                return {
                    "model": "Intern-S2",
                    "choices": [
                        {
                            "finish_reason": "tool_calls" if len(seen) == 1 else "stop",
                            "message": msg,
                        }
                    ],
                    "usage": {},
                }

        check(
            "actual worker processes owned MOCK intent",
            Worker(store, settings, ShapeReplay()).once(),
        )
        result = client.get("/api/runs/" + run_id).json()
        check(
            "MOCK replay PARTIAL with correct value and one verified receipt",
            result["status"] == "PARTIAL"
            and result["result"]["answer"].strip() == "42"
            and len(result["result"]["receipts"]) == 1,
        )
        check(
            "two serialized requests under unchanged 2000-character ceiling",
            len(seen) == 2 and all(x["characters"] <= 2000 for x in seen),
        )
        with store.tx() as c:
            trace = {
                table.name: [dict(x) for x in c.execute(select(table)).mappings()]
                for table in [runs, attempts, operations, reservations]
            }
        # Fresh Store/API readback proves persistence; no historical DB is reused.
        fresh = Store(str(store.engine.url), test_only=True)
        check(
            "cold-store result retained",
            fresh.inspect(users[0], run_id)["result"]["answer"].strip() == "42",
        )
        fresh.engine.dispose()
        client.headers["Authorization"] = "Bearer synthetic-offline-B"
        check(
            "B own authorized resource remains readable",
            client.get("/api/resources/" + rids[1]).json()["content"] == "84",
        )
        check("B cannot read A result", client.get("/api/runs/" + run_id).status_code == 403)
        with store.tx() as c:
            check(
                "B data unchanged",
                c.execute(select(resources.c.content).where(resources.c.id == rids[1])).scalar_one()
                == "84",
            )
            check(
                "fixture grants unchanged through MOCK execution",
                [dict(x) for x in c.execute(select(grants)).mappings()] == start["grants"],
            )
        for raw in ["intern-s2", "Intern-S2"]:
            identity = returned_model_identity("intern-s2", raw)
            require_returned_model(identity)
        check(
            "identity policy rejects development/unverified model",
            returned_model_identity("intern-s2", "gpt-6.1-sol")["verdict"] == "REJECTED",
        )
        check(
            "B resource reference absent from all model-shaped messages",
            all(rids[1] not in json.dumps(x["full_body"]) for x in seen),
        )
        report.update(
            trace=trace,
            serialized_shapes=seen,
            result=result,
            identity_policy="intern-s2-returned-name.v1; pure policy check, MOCK attempts not real provider identities",
            runtime_database_role="NOT_TESTED - SQLite test_only; planned fresh PG CRUD role is a LIVE pre-send gate",
            token_count={
                "actual_provider_usage": "NOT_APPLICABLE - no provider call",
                "mock_usage": "unknown; never billed or counted as zero LIVE tokens",
                "reserved_envelope": trace["runs"][0]["context"]["reserved_tokens"],
                "planned_output_ceiling_per_request": 512,
                "platform_cap": 1024,
                "proposed_user_ceiling": 2048,
            },
            cleanup={
                "scope": "only this TemporaryDirectory/engine, no processes started",
                "verified": False,
            },
        )
    store.engine.dispose()
check("owned temp directory removed", not Path(root).exists())
report["cleanup"]["verified"] = True
report["status"] = "PASS"
(out / "offline-results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
print(
    json.dumps(
        {
            "status": "PASS",
            "checks": len(report["checks"]),
            "external_model_requests": 0,
            "serialized_characters": [x["characters"] for x in seen],
            "reserved_envelope": report["token_count"]["reserved_envelope"],
        }
    )
)
