"""Received rejected JSON is preserved; a true lost response invents none."""

import copy
import json

import pytest
import test_goal_text_applications as helper
from sqlalchemy import select

from sim2act.db import attempts


@pytest.mark.parametrize("fault", ["usage", "identity", "truncated", "refusal"])
def test_received_rejected_original_json_is_preserved(env, fault):
    data = helper.setup(env)
    received = {}

    def mutation(raw, index, payload):
        if index != 1:
            return
        if fault == "usage":
            raw.pop("usage")
        elif fault == "identity":
            raw["model"] = "other"
        elif fault == "truncated":
            raw["choices"][0]["finish_reason"] = "length"
        else:
            raw["choices"][0]["message"]["refusal"] = "Synthetic refused fixture; no external model"
        received.update(copy.deepcopy(raw))

    rid, result, sent = helper.generate(data, mutation=mutation)
    assert len(sent) == 1 and result["result"] is None and result["status"] != "PARTIAL"
    with data[0].tx() as c:
        row = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().one()
    original = row["parameters"]["generation_rejected_raw"]
    assert row["status"] == "FAILED"
    assert len(original.encode("ascii")) <= 32768
    assert json.loads(original) == received
    assert (
        json.loads(original)["choices"][0]["message"]["tool_calls"]
        == received["choices"][0]["message"]["tool_calls"]
    )
