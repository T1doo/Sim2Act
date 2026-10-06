"""Offline contract/oracle demonstration for one existing authorized MD section."""

import copy
import hashlib
import json
from pathlib import Path

repo = Path(__file__).resolve().parents[3]
source = repo / "docs/sources/V5/平台产品设计.md"
lines = source.read_text().splitlines()
keys = [
    "release_instance_preview",
    "version_and_dynamic_authorization",
    "compatible_upgrade_rollback",
    "rollback_boundaries",
]
line_numbers = [452, 454, 456, 458]
gold = {
    "source_version": 1,
    "source_hash": hashlib.sha256(source.read_bytes()).hexdigest(),
    "items": [
        {"rule_key": key, "source_line": n, "quote": lines[n - 1]}
        for key, n in zip(keys, line_numbers, strict=True)
    ],
}


def oracle(value):
    # Developer-defined deterministic gold draft for this section; citation existence alone is not semantics.
    assert set(value) == {"source_version", "source_hash", "items"}
    assert value["source_version"] == 1 and value["source_hash"] == gold["source_hash"]
    assert len(value["items"]) == 4 and [x["rule_key"] for x in value["items"]] == keys
    for actual, expected in zip(value["items"], gold["items"], strict=True):
        assert actual == expected and lines[actual["source_line"] - 1] == actual["quote"]


oracle(gold)
negatives = []
for fault in ["wrong_hash", "stale_version", "missing_rule", "wrong_quote", "wrong_span"]:
    value = copy.deepcopy(gold)
    if fault == "wrong_hash":
        value["source_hash"] = "0" * 64
    elif fault == "stale_version":
        value["source_version"] = 2
    elif fault == "missing_rule":
        value["items"].pop()
    elif fault == "wrong_quote":
        value["items"][0]["quote"] = "发布回退可以清空数据"
    else:
        value["items"][0]["source_line"] = 454
    try:
        oracle(value)
    except AssertionError:
        negatives.append({"fault": fault, "status": "REJECTED"})
    else:
        raise AssertionError("bad oracle accepted")
result = {
    "kind": "OFFLINE developer gold draft contract only; no owner/independent acceptance, model extraction or registered product action",
    "source": "docs/sources/V5/平台产品设计.md §10.1 lines450-458",
    "source_authorization": "existing user-provided repo source; authorized local read, future external transmission needs explicit approval",
    "selected_utf8_bytes": len("\n".join(lines[449:458]).encode()),
    "gold": gold,
    "checks": {"valid_developer_gold_draft": "PASS", "negative_cases": negatives},
    "external_model_requests": 0,
    "actual_semantic_extraction": "NOT_RUN",
    "limits": "gold applies to this frozen section; unseen document requires independently frozen gold/manual semantic review",
}
Path(__file__).with_name("noncsv-contract-results.json").write_text(
    json.dumps(result, indent=2, ensure_ascii=False) + "\n"
)
print(
    json.dumps(
        {
            "contract": "PASS",
            "negative_cases": len(negatives),
            "selected_utf8_bytes": result["selected_utf8_bytes"],
            "external_model_requests": 0,
        }
    )
)
