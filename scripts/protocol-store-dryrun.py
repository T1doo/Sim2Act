"""Two synthetic task forms through durable authenticated HTTP, with ZERO NETWORK.

Run: PYTHONPATH=src python scripts/protocol-store-dryrun.py --output /tmp/protocol-demo
A fresh temporary SQLite Store is migrated explicitly. Private oracle answers construct
MockTransport RESPONSES only; persisted review evaluates them independently. This is
synthetic engineering evidence, never owner acceptance or real model semantics.
"""

import argparse
import copy
import hashlib
import json
import tempfile
from dataclasses import replace
from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import (
    Store,
    attempts,
    fingerprint,
    grants,
    operations,
    principals,
    protocol_jobs,
    protocol_request_slots,
)
from sim2act.model import InternModel
from sim2act.model_budget import ENDPOINT, BudgetedProvider, initialize_ledger
from sim2act.protocol_api import ProtocolAttemptRunner
from sim2act.protocol_pool import OFFLINE_POOL, initialize_pools, inspect_pool
from sim2act.protocol_readiness import candidate_for, prepare_handoff, require_handoff
from sim2act.protocol_reviews import contract_snapshot, evaluation_contract
from sim2act.worker import Worker

ROOT = Path(__file__).resolve().parents[1]
MATERIALS = ROOT / "docs/evidence/model-protocol-preparation-20261006/materials"
INPUTS = {"format": "JSON with line evidence and explicit UNKNOWN"}


def mock_response(value=None, resource_ids=()):
    message = {"role": "assistant", "content": json.dumps(value, ensure_ascii=False)}
    if resource_ids:
        message.update(
            content="",
            tool_calls=[
                {
                    "id": f"read-{i}",
                    "type": "function",
                    "function": {
                        "name": "resource.read",
                        "arguments": json.dumps({"resource_id": rid}),
                    },
                }
                for i, rid in enumerate(resource_ids)
            ],
        )
    return {
        "model": "intern-s2",
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        "choices": [
            {"finish_reason": "tool_calls" if resource_ids else "stop", "message": message}
        ],
    }


def wire_values(value):
    """Decode nested JSON message strings so escaping cannot hide answer/material reuse."""
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from wire_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from wire_values(child)
    elif isinstance(value, str):
        try:
            decoded = json.loads(value)
        except (ValueError, RecursionError):
            return
        if isinstance(decoded, (dict, list)):
            yield from wire_values(decoded)


def assert_isolated_wire(wire, texts=(), answer=None):
    for value in wire_values(wire):
        if isinstance(value, str):
            assert all(text not in value for text in texts), (
                "Private or unrelated material in request"
            )
        if answer is not None and isinstance(value, dict):
            assert fingerprint(value) != fingerprint(answer), "Source answer reused in cold request"


class NoLegacyProvider:
    def request(self, *_):
        raise AssertionError("The default provider cannot send this demonstration")


def authority_summary(store):
    with store.tx() as c:
        identities = [
            {"id": r["id"], "name": r["name"]} for r in c.execute(select(principals)).mappings()
        ]
        rights = [dict(r) for r in c.execute(select(grants)).mappings()]
    return {
        "principal_count": len(identities),
        "grant_count": len(rights),
        "principal_fingerprint": fingerprint(sorted(identities, key=lambda x: x["id"])),
        "grant_fingerprint": fingerprint(sorted(rights, key=lambda x: x["id"])),
    }


def demonstrate(*, fail_source=None):
    if fail_source not in {None, "a", "b"}:
        raise ValueError("Failure injection is limited to synthetic source a/b")
    manifest = json.loads((MATERIALS / "manifest.json").read_text())
    packages = {p["package_id"]: p for p in manifest["packages"]}
    wire, families, submissions, handoffs, handoff_checks = [], [], [], [], []
    with tempfile.TemporaryDirectory(prefix="sim2act-store-demo-") as owned:
        directory = Path(owned)
        url = "sqlite:///" + str(directory / "store.sqlite")
        store = Store(url, test_only=True)
        store.initialize()  # Explicit controller migration, never API construction.
        initialize_pools(store, offline_limit=14)  # Synthetic test controller, LIVE stays zero.
        user = store.user("offline demo", "synthetic-protocol-demo")
        settings = Settings(url, directory, max_requests=3, max_repairs=0)
        try:
            with TestClient(create_app(store, settings)) as client:
                client.headers["Authorization"] = "Bearer synthetic-protocol-demo"
                project = client.post(
                    "/api/projects", json={"name": "synthetic two-form demo"}
                ).json()["id"]
                base = f"/api/projects/{project}/protocol"
                resources, material_texts = {}, {}
                for package_id, package in packages.items():
                    resources[package_id], material_texts[package_id] = [], []
                    for resource in package["resources"]:
                        raw = (MATERIALS / resource["path"]).read_bytes()
                        assert hashlib.sha256(raw).hexdigest() == resource["sha256"]
                        text = raw.decode()
                        response = client.post(
                            f"/api/projects/{project}/resources",
                            json={"name": resource["path"], "format": "txt", "content": text},
                        )
                        assert response.status_code == 201, response.text
                        resources[package_id].append(response.json()["id"])
                        material_texts[package_id].append(text)
                before = authority_summary(store)

                def current(rid):
                    response = client.get(base + "/runs/" + rid)
                    assert response.status_code == 200, response.text
                    return response.json()

                def submit(phase, payload):
                    submissions.append({"phase": phase, "payload": copy.deepcopy(payload)})
                    response = client.post(base + "/" + phase, json=payload)
                    assert response.status_code == 202, response.text
                    repeated = client.post(base + "/" + phase, json=payload)
                    assert (
                        repeated.status_code == 202
                        and repeated.json()["run_id"] == response.json()["run_id"]
                    )
                    rid = response.json()["run_id"]
                    queued = current(rid)
                    handoffs.append(
                        prepare_handoff(
                            store,
                            user,
                            rid,
                            {
                                "expected_version": queued["version"],
                                "expected_fence": queued["fence"],
                                "request_key": "offline-handoff-" + rid,
                            },
                        )
                    )
                    return rid

                def execute(rid, stage, replies):
                    queued = copy.deepcopy(replies)

                    def factory(worker, run, snapshot):
                        assert run["id"] == rid
                        scope = snapshot["scope"]
                        ledger = directory / (rid + ".json")
                        initialize_ledger(ledger, scope)
                        ticks = [1000.0]

                        def transport(request):
                            assert str(request.url) == ENDPOINT and queued
                            raw = request.content
                            wire.append(
                                {
                                    "stage": stage,
                                    "run_id": rid,
                                    "body": json.loads(raw),
                                    "chars": len(raw.decode()),
                                    "bytes": len(raw),
                                    "sha256": hashlib.sha256(raw).hexdigest(),
                                }
                            )
                            ticks[0] += 7
                            return httpx.Response(200, json=queued.pop(0))

                        def authorize(_):
                            with store.tx() as c:
                                store.guard(c, rid, run["fence"])
                                for resource_id in scope["resource_ids"]:
                                    store.authorize(
                                        c,
                                        run["principal_id"],
                                        run["runtime_id"],
                                        project,
                                        resource_id,
                                        "resource.read",
                                    )
                            return True

                        model = InternModel(
                            replace(settings, live_enabled=True, token="MOCK_ONLY"),
                            httpx.MockTransport(transport),
                        )
                        provider = BudgetedProvider(
                            model, ledger, scope, stage, authorize=authorize, clock=lambda: ticks[0]
                        )
                        runner = ProtocolAttemptRunner(worker, run, snapshot, provider)
                        original_call = runner.call

                        def guarded_call(messages, tools):
                            require_handoff(
                                store, user, rid
                            )  # BEFORE own STARTED slot reservation.
                            handoff_checks.append({"run_id": rid, "stage": stage})
                            return original_call(messages, tools)

                        runner.call = guarded_call
                        return runner

                    assert Worker(
                        store, settings, NoLegacyProvider(), protocol_runner_factory=factory
                    ).once()
                    assert not queued, current(rid)
                    return current(rid)

                def review(rid, completed, contract_id):
                    response = client.post(
                        f"/api/internal/protocol/runs/{rid}/reviews",
                        json={
                            "contract_id": contract_id,
                            "expected_result_fingerprint": completed["result_fingerprint"],
                            "expected_fence": completed["fence"],
                            "expected_version": completed["version"],
                            "request_key": "review-" + rid,
                        },
                    )
                    assert response.status_code == 201, response.text
                    return response.json()["decision"], current(rid)

                for family in ("a", "b"):
                    source_id, cold_id = f"{family}-source", f"{family}-cold"
                    source_contract_id = f"protocol.synthetic.{source_id}.v1"
                    cold_contract_id = f"protocol.synthetic.{cold_id}.v1"
                    public = contract_snapshot(source_contract_id)
                    # Private answers ONLY build the synthetic transport reply; never a caller payload.
                    answer = evaluation_contract(source_contract_id)[0]["expected_output"]
                    rid = submit(
                        "source",
                        {
                            "goal": public["public_goal"],
                            "inputs": INPUTS,
                            "resource_ids": resources[source_id],
                            "contract_id": source_contract_id,
                            "request_key": source_id,
                        },
                    )
                    completed = execute(
                        rid,
                        "source_" + family,
                        [
                            mock_response(resource_ids=resources[source_id]),
                            mock_response({"wrong": True} if fail_source == family else answer),
                        ],
                    )
                    assert (
                        completed["status"] == "WAITING_APPROVAL"
                        and completed["semantic_status"] == "UNKNOWN"
                    )
                    decision, accepted = review(rid, completed, source_contract_id)
                    record = {
                        "form": family,
                        "source_run_id": rid,
                        "source_review": decision,
                        "source_technical_semantic": completed["semantic_status"],
                    }
                    families.append(record)
                    if decision != "PASS":
                        record["stopped_before"] = "extract"
                        break
                    assert accepted["status"] == "SUCCEEDED"
                    extraction = submit(
                        "extract",
                        {
                            "source_run_id": rid,
                            "expected_source_fingerprint": accepted["result_fingerprint"],
                            "request_key": "extract-" + family,
                        },
                    )
                    compiled = execute(
                        extraction,
                        "extract_" + family,
                        [mock_response(candidate_for(public, resources[source_id]))],
                    )
                    assert compiled["status"] == "SUCCEEDED"
                    plan = compiled["result"]["compiled_plan"]
                    cold = submit(
                        "cold",
                        {
                            "extraction_run_id": extraction,
                            "expected_plan_fingerprint": plan["plan_fingerprint"],
                            "inputs": INPUTS,
                            "resource_bindings": {
                                f"material_{i}": ref for i, ref in enumerate(resources[cold_id])
                            },
                            "contract_id": cold_contract_id,
                            "request_key": cold_id,
                        },
                    )
                    cold_answer = evaluation_contract(cold_contract_id)[0]["expected_output"]
                    pending = execute(cold, "cold_" + family, [mock_response(cold_answer)])
                    assert (
                        pending["status"] == "WAITING_APPROVAL"
                        and pending["semantic_status"] == "UNKNOWN"
                    )
                    cold_decision, reviewed = review(cold, pending, cold_contract_id)
                    record.update(
                        extraction_run_id=extraction,
                        cold_run_id=cold,
                        cold_review=cold_decision,
                        plan_fingerprint=plan["plan_fingerprint"],
                        cold_technical_semantic=pending["semantic_status"],
                    )
                    if cold_decision != "PASS":
                        break
                    assert reviewed["status"] == "SUCCEEDED"
                    cold_wire = [item["body"] for item in wire if item["stage"] == "cold_" + family]
                    assert_isolated_wire(cold_wire, material_texts[source_id], answer)
                    for item in wire:
                        if item["stage"] in {"source_" + family, "extract_" + family}:
                            assert_isolated_wire(item["body"], material_texts[cold_id])
                    record["cold_isolation"] = (
                        "source materials/answer absent; unseen resources read"
                    )
                after = authority_summary(store)
                assert before == after
                pool = inspect_pool(store, OFFLINE_POOL)
                with store.tx() as c:
                    actual_attempts = list(c.execute(select(attempts)).mappings())
                    actual_operations = list(c.execute(select(operations)).mappings())
                    jobs = list(c.execute(select(protocol_jobs)).mappings())
                    slots = list(c.execute(select(protocol_request_slots)).mappings())
                assert (
                    pool["slots_count"]
                    == pool["reserved_requests"]
                    == len(actual_attempts)
                    == len(wire)
                )
                assert {s["attempt_id"] for s in slots} == {a["id"] for a in actual_attempts}
                assert all(
                    s["status"] == "RECEIVED" and s["pool_id"] == OFFLINE_POOL for s in slots
                )
                assert all(j["accepted_snapshot"]["request_pool_id"] == OFFLINE_POOL for j in jobs)
                assert all(o["status"] == "VERIFIED" for o in actual_operations)
                denied = [
                    "gold_sha256",
                    "rubric_sha256",
                    "expected_output",
                    "registry_asset_sha256",
                    "exact-json-semantic",
                    "semantic-rubric.md",
                    '"provider_allowed"',
                ]
                encoded = json.dumps([item["body"] for item in wire], ensure_ascii=False)
                assert all(term not in encoded for term in denied)
                for family in ("a", "b"):
                    for phase in ("source", "cold"):
                        contract_id = f"protocol.synthetic.{family}-{phase}.v1"
                        private, asset_hash = evaluation_contract(contract_id)
                        public = contract_snapshot(contract_id)
                        for value in wire_values([item["body"] for item in wire]):
                            if isinstance(value, dict):
                                assert fingerprint(value) != fingerprint(private)
                            if isinstance(value, str):
                                assert asset_hash not in value
                                assert public["gold_sha256"] not in value
                                assert public["rubric_sha256"] not in value
                assert all(w["chars"] <= 8000 and w["bytes"] <= 10000 for w in wire)
                result = {
                    "kind": "SYNTHETIC_STORE_HTTP_WORKER_ZERO_NETWORK",
                    "external_requests": 0,
                    "real_model_semantics": "NOT_RUN",
                    "owner_acceptance": "PENDING",
                    "live_budget": 0,
                    "mock_calls": len(wire),
                    "offline_handoffs": handoffs,
                    "handoff_checks_before_reserve": handoff_checks,
                    "forms": families,
                    "pool": pool,
                    "authority": after,
                    "attempt_count": len(actual_attempts),
                    "operation_count": len(actual_operations),
                    "slot_attempt_bijection": True,
                    "slot_phase_counts": {
                        phase: sum(s["phase"] == phase for s in slots)
                        for phase in ("source", "extract", "cold")
                    },
                    "distinct_job_approvals": len(
                        {j["accepted_snapshot"]["scope"]["approval_id"] for j in jobs}
                    ),
                    "operation_statuses": sorted({o["status"] for o in actual_operations}),
                    "phase_counts": {
                        phase: sum(j["kind"] == phase for j in jobs)
                        for phase in ("source", "extract", "cold")
                    },
                    "request_bounds": {
                        "max_chars": max(w["chars"] for w in wire),
                        "max_bytes": max(w["bytes"] for w in wire),
                        "output_tokens": 1024,
                    },
                    "wire": wire,
                    "submissions": submissions,
                    "limits": [
                        "Mock replies use pinned synthetic checker answers; no real model planning",
                        "Exact registered synthetic review is not owner semantic acceptance",
                        "Actual public source outputs may enter extract; private gold assets never do",
                        "SQLite temporary Store; no native UI, LIVE, publication, or generic recovery",
                    ],
                }
        finally:
            store.engine.dispose()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fail-source", choices=["a", "b"])
    args = parser.parse_args()
    report = demonstrate(fail_source=args.fail_source)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "protocol-store-dryrun.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(f"Mock Store demonstration: {report['mock_calls']} requests; network=0; owner=PENDING")
