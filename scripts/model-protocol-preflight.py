"""Reproducible ZERO NETWORK wire preparation, never a LIVE/semantic acceptance runner.

Uses public material allowlist only. Mock replies and verifier are explicitly synthetic.
Run with PYTHONPATH=src; writes bounded diagnostics under the requested owned output dir.
"""
import argparse
import hashlib
import json
import tempfile
from pathlib import Path

import httpx

from sim2act.config import Settings
from sim2act.db import fingerprint
from sim2act.model import InternModel
from sim2act.model_budget import ENDPOINT, BudgetedProvider, initialize_ledger
from sim2act.model_protocol import ModelProtocol, obj

ROOT = Path(__file__).resolve().parents[1]
MATERIALS = ROOT / "docs/evidence/model-protocol-preparation-20261006/materials"


def reply(value=None, calls=None):
    msg = {"role": "assistant", "content": json.dumps(value, ensure_ascii=False)}
    if calls:
        msg = {"role": "assistant", "content": "", "tool_calls": [
            {"id": f"read{i}", "type": "function", "function": {
                "name": "resource.read", "arguments": json.dumps({"resource_id": rid})}}
            for i, rid in enumerate(calls)]}
    return {"model": "Intern-S2", "usage": {"prompt_tokens": 10, "completion_tokens": 10,
            "total_tokens": 20}, "choices": [{"finish_reason": "tool_calls" if calls else "stop",
                                               "message": msg}]}


def prepare(output):
    manifest = json.loads((MATERIALS / "manifest.json").read_text())
    resources, packages = {}, {}
    for package in manifest["packages"]:
        ids = []
        for resource in package["resources"]:
            path = MATERIALS / resource["path"]
            content = path.read_text()
            assert hashlib.sha256(path.read_bytes()).hexdigest() == resource["sha256"]
            rid = "res_" + hashlib.sha256(resource["logical_resource_id"].encode()).hexdigest()[:32]
            resources[rid] = {"resource_id": rid, "content": content,
                              "hash": resource["sha256"], "format": "txt"}
            ids.append(rid)
        packages[package["package_id"]] = {"ids": ids, "goal": package["instruction"]}
    scope = {"approval_id": "MOCK_PREFLIGHT_NOT_AUTHORIZATION", "project_id": "proj_" + "e" * 32,
             "resource_ids": list(resources), "tool_refs": ["resource.read"], "max_requests": 3,
             "mode": "offline", "model": "intern-s2"}
    wire, stages, response_sizes = [], [], []
    queued = []
    stage_now = [""]
    ticks = [100.0]

    def transport(request):
        body = request.content
        wire.append({"stage": stage_now[0], "chars": len(body.decode()), "utf8_bytes": len(body),
                     "sha256": hashlib.sha256(body).hexdigest(), "body": json.loads(body)})
        value = queued.pop(0)
        response_sizes.append(len(json.dumps(value, ensure_ascii=False).encode()))
        return httpx.Response(200, json=value)

    def read_only(tool, args):
        assert tool == "resource.read" and args["resource_id"] in resources
        return resources[args["resource_id"]].copy()  # TEST fixture, not Operation receipt.

    def synthetic_verify(stage, evidence):
        # Protocol shape ONLY: gold never loaded; this does not evaluate task semantics.
        return {"status": "SUCCEEDED", "semantic_status": "PASS",
                "evidence_fingerprint": fingerprint(evidence), "goal_fingerprint": fingerprint(evidence["goal"]),
                "input_fingerprint": fingerprint(evidence["inputs"]), "output_fingerprint": fingerprint(evidence["output"]),
                "trace_fingerprint": fingerprint(evidence["tool_trace"]),
                "checks": [{"check_id": "MOCK_PROTOCOL_SHAPE_ONLY_NOT_OWNER_ACCEPTANCE", "status": "PASS"}]}

    with tempfile.TemporaryDirectory(prefix="sim2act-protocol-preflight-") as owned:
        ledger = Path(owned) / "budget.json"
        initialize_ledger(ledger, scope)
        settings = Settings("unused", Path(owned), live_enabled=True, token="MOCK_ONLY", max_repairs=0)
        provider = InternModel(settings, httpx.MockTransport(transport))

        def protocol(stage):
            stage_now[0] = stage
            ticks[0] += 7
            runner = BudgetedProvider(provider, ledger, scope, stage,
                                      authorize=lambda s: s == scope, clock=lambda: ticks[0])
            return ModelProtocol(runner, scope=scope, enabled=True, independent_verify=synthetic_verify,
                                 read_only=read_only)

        inputs = {"format": "JSON with line evidence and explicit UNKNOWN"}
        for family in ("a", "b"):
            source, cold = packages[f"{family}-source"], packages[f"{family}-cold"]
            queued.extend([reply(calls=source["ids"]), reply({"report": "MOCK SOURCE PLACEHOLDER; no semantic answer"})])
            source_protocol = protocol("source_" + family)
            # Advance between calls without sleeping or contacting a provider.
            source_protocol.runner.clock = lambda: (ticks.__setitem__(0, ticks[0] + 7) or ticks[0])
            completed = source_protocol.complete_task(source["goal"], inputs, source["ids"])
            candidate = {"schema_version": "model-protocol.v1", "input_schema": obj({"format": {"type": "string"}}),
                         "resources": {f"material{i}": rid for i, rid in enumerate(source["ids"])},
                         "steps": [], "output_schema": obj({"report": {"type": "string", "maxLength": 1500}}),
                         "outputs": {"report": {"source": "step", "ref": "compose", "field": "report"}}}
            language_inputs = {"format": {"source": "input", "ref": "input", "field": "format"}}
            for i, _rid in enumerate(source["ids"]):
                candidate["steps"].append({"id": f"read{i}", "kind": "registered_tool", "depends_on": [],
                    "inputs": {"resource_id": {"source": "data", "ref": f"material{i}", "field": "resource_id"}},
                    "tool_ref": "resource.read"})
                language_inputs[f"content{i}"] = {"source": "step", "ref": f"read{i}", "field": "content"}
            candidate["steps"].append({"id": "compose", "kind": "language",
                "depends_on": [f"read{i}" for i in range(len(source["ids"]))], "inputs": language_inputs,
                "instruction": source["goal"], "output_schema": candidate["output_schema"]})
            queued.append(reply(candidate))
            extracted = protocol("extract_" + family).extract_candidate(completed)
            queued.append(reply({"report": "MOCK COLD PLACEHOLDER; not copied source output"}))
            result = protocol("cold_" + family).run_candidate(extracted, inputs,
                {f"material{i}": rid for i, rid in enumerate(cold["ids"])}, source=completed)
            assert result["evidence"]["output"]["report"].startswith("MOCK COLD")
            assert all(resources[rid]["content"] not in json.dumps(wire[-1]["body"], ensure_ascii=False)
                       for rid in source["ids"])
            stages.append({"family": family, "kind": "MOCK_PROTOCOL_ONLY", "owner_semantic": "UNKNOWN",
                           "source_fingerprint": fingerprint(completed), "candidate_fingerprint": extracted["candidate_fingerprint"],
                           "candidate_receipt": extracted["candidate_receipt"], "cold_output_fingerprint": fingerprint(result["evidence"]["output"])})
        data = json.loads(ledger.read_text())
        assert len(data["slots"]) == len(wire) == 8 and not data["halted"]
        assert all(x["chars"] <= 8000 and x["utf8_bytes"] <= 10000 for x in wire)
        output.mkdir(parents=True, exist_ok=True)
        (output / "wire-preflight.json").write_text(json.dumps({"kind": "MOCK_ZERO_NETWORK_COMPLETE_WIRE",
            "external_requests": 0, "provider": ENDPOINT, "model": "intern-s2", "output_cap": 1024,
            "semantic_acceptance": "UNKNOWN_OWNER_PENDING", "future_live_budget": 0,
            "max_chars": max(x["chars"] for x in wire), "max_bytes": max(x["utf8_bytes"] for x in wire),
            "mock_calls": len(wire), "reserved": data["reserved"], "mock_usage_not_real": data["known_tokens"],
            "wire": wire, "stages": stages, "candidate_executable_by_existing_apprun": False,
            "limits": ["Mock candidate and responses are protocol fixtures, not model planning",
                       "Future real public outputs/traces may be larger; every real body still checked before send",
                       "1024 output tokens sufficiency unknown; no tokenizer or price claim",
                       "No AppRun/Operation receipt or semantic owner approval"]}, ensure_ascii=False, indent=2) + "\n")
    return len(wire)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(f"MOCK preflight: {prepare(args.output)} complete wire bodies; external requests 0")
