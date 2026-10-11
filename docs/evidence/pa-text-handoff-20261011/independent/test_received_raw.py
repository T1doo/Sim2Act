"""Independent actual SQLite/Worker evidence; synthetic provider only."""
import copy
import hashlib
import json

import pytest
from sqlalchemy import select, update
import test_goal_text_applications as helper
from sim2act.db import attempts, app_drafts, operations, events


def archive(raw):
    saved = json.dumps(raw, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    encoded = saved.encode("ascii")
    return saved, {"status": "COMPLETE" if len(encoded) <= 32768 else "OMITTED_OVERSIZE", "bytes": len(encoded), "sha256": hashlib.sha256(encoded).hexdigest()}


def complete_json_values(parameters):
    values = []
    for value in parameters.values():
        if not isinstance(value, str):
            continue
        try:
            decoded = json.loads(value)
        except (ValueError, TypeError):
            continue
        if isinstance(decoded, dict) and "choices" in decoded:
            values.append((value, decoded))
    return values


@pytest.mark.parametrize("fault", ["wrong-source", "candidate-tools", "invalid-manifest"])
def test_received_rejections_preserve_every_original_json(env, fault):
    data = helper.setup(env)
    received = []
    def mutation(raw, index, payload):
        if fault == "wrong-source" and index == 1:
            raw["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = json.dumps({"resource_id": "res_" + "0" * 32})
        elif fault == "candidate-tools" and index == 2:
            raw["choices"][0]["message"]["tool_calls"] = [{"id": "unapproved-second-read", "type": "function", "function": {"name": "resource.read", "arguments": json.dumps({"resource_id": data[5]})}}]
        elif fault == "invalid-manifest" and index >= 2:
            value = json.loads(raw["choices"][0]["message"]["content"])
            value["manifest"]["workflow"][0]["inputs"].pop("term")
            raw["choices"][0]["message"]["content"] = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        raw["provider_extra"] = {"actual_index": index, "opaque_note": "Retain this unmodeled received field"}
        received.append(copy.deepcopy(raw))
    rid, result, sent = helper.generate(data, mutation=mutation)
    assert result["status"] != "PARTIAL" and result["result"] is None
    assert len(sent) == {"wrong-source": 1, "candidate-tools": 2, "invalid-manifest": 3}[fault]
    with data[0].tx() as c:
        rows = c.execute(select(attempts).where(attempts.c.run_id == rid).order_by(attempts.c.created_at, attempts.c.id)).mappings().all()
        public = c.execute(select(events.c.data).where(events.c.run_id == rid)).scalars().all()
        assert c.execute(select(app_drafts.c.id)).first() is None
    assert len(rows) == len(received)
    for row, original in zip(rows, received):
        assert row["status"] in {"RECEIVED", "FAILED"}
        saved = complete_json_values(row["parameters"])
        expected, metadata = archive(original)
        assert saved, "Every received JSON must have a complete protected representation"
        assert all(text == expected and value == original for text, value in saved)
        assert row["parameters"]["generation_raw_evidence"] == metadata
        if row["status"] == "RECEIVED":
            assert row["parameters"]["generation_received_raw"] == expected
        if row["error"]:
            assert row["parameters"]["generation_rejected_raw"] == expected
    assert "Retain this unmodeled received field" not in json.dumps(public)


@pytest.mark.parametrize("oversize_index", [1, 2])
def test_oversized_raw_does_not_execute_or_save_opaque_content(env, oversize_index):
    data = helper.setup(env)
    received = []
    needle = "UNTRUSTED_OVERSIZED_OPAQUE_PAYLOAD_" * 1600
    def mutation(raw, index, payload):
        if index == oversize_index:
            raw["extra_opaque"] = needle
            received.append(copy.deepcopy(raw))
    rid, result, sent = helper.generate(data, mutation=mutation)
    assert len(sent) == oversize_index and result["status"] != "PARTIAL" and result["result"] is None
    with data[0].tx() as c:
        rows = c.execute(select(attempts).where(attempts.c.run_id == rid).order_by(attempts.c.created_at, attempts.c.id)).mappings().all()
        ops = c.execute(select(operations).where(operations.c.run_id == rid)).mappings().all()
        assert c.execute(select(app_drafts.c.id)).first() is None
    row = rows[-1]
    _, expected = archive(received[0])
    assert expected["status"] == "OMITTED_OVERSIZE"
    assert row["parameters"]["generation_raw_evidence"] == expected
    assert complete_json_values(row["parameters"]) == []
    assert needle not in json.dumps(row["parameters"])
    assert len(ops) == oversize_index - 1, "Overbound source stage executes no read; overbound candidate executes no extra operation"


@pytest.mark.parametrize("archive_index", [0, 1])
def test_resigned_raw_envelope_still_conflicts_with_independent_received_anchor(env, archive_index):
    data = helper.setup(env)
    def mutation(raw, index, payload):
        raw["unmodeled_original"] = {"actual_index": index, "not_normalized": "Keep original"}
    rid, result, sent = helper.generate(data, mutation=mutation)
    aid, _ = helper.confirm(data, rid, result)
    with data[0].tx() as c:
        rows = c.execute(select(attempts).where(attempts.c.run_id == rid).order_by(attempts.c.created_at, attempts.c.id)).mappings().all()
        row = rows[archive_index]
        params = copy.deepcopy(row["parameters"])
        value = json.loads(params["generation_received_raw"])
        value["unmodeled_original"]["not_normalized"] = "Forged independently of normalized message"
        params["generation_received_raw"], params["generation_raw_evidence"] = archive(value)
        c.execute(update(attempts).where(attempts.c.id == row["id"]).values(parameters=params))
    recovered = data[2].get(f"/api/apps/{aid}")
    assert recovered.status_code == 409, recovered.text
    assert recovered.json()["error"]["code"] == "VERSION_CONFLICT"
