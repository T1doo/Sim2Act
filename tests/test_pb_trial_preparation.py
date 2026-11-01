"""P-B preparation through normal authenticated API; no model/Run dispatch."""

import copy
import json
import subprocess
import sys
import time

import pytest
from sqlalchemy import select
from test_natural_spec_apps import recipe
from test_natural_trial_preparation import business, prepared_data  # noqa: F401

from sim2act import natural_live_admission as gate
from sim2act.db import delivery_graph_requests


@pytest.mark.parametrize("style", ["single", "ordered", "sequential"])
def test_pb_original_contract_exact_replay_approval_reopen_withdraw(prepared_data, style):  # noqa: F811
    data, choices = prepared_data
    store, _, client, user, pid = data[:5]
    before = business(store)
    path = f"/api/projects/{pid}/natural-trials/new-pb-{style}"
    body = dict(choices, path="P-B", extraction_recipe=recipe(style))
    start = time.time()
    made = client.post(path + "/preparation", json=body)
    assert made.status_code == 200, made.text
    result = made.json()
    contract = gate.PBTrialContract.model_validate(result["contract"])
    assert result["path"] == "P-B" and not result["approved"] and not result["live_allowed"]
    assert (
        contract.namespace == gate.VERSION
        and start + 300 <= contract.expires_at <= time.time() + 300
    )
    assert (
        contract.caps == gate.TrialCaps()
        and contract.extraction_recipe.model_dump(exclude_none=True) == body["extraction_recipe"]
    )
    assert contract.extraction_request_key not in contract.stage_keys.model_dump().values()
    assert client.post(path + "/preparation", json=body).json() == result
    different = copy.deepcopy(body)
    different["extraction_recipe"]["steps"][0]["step_id"] = "other"
    assert client.post(path + "/preparation", json=different).status_code == 409
    assert client.post(path + "/preparation", json=choices).status_code == 409
    approval = client.post(
        path + "/consent", json=dict(review_token=result["review_token"], confirm_exact_scope=True)
    )
    assert approval.status_code == 200, approval.text
    assert client.get(path + "/preparation").json()["approved"] is True
    if style == "ordered":
        child = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import json,sys
from pathlib import Path
from fastapi.testclient import TestClient
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store
store=Store(sys.argv[1],test_only=True)
try:
 with TestClient(create_app(store,Settings(sys.argv[1],Path(sys.argv[2]),mode='mock'))) as client:
  client.headers['Authorization']='Bearer synthetic-test-A'
  response=client.get(sys.argv[3]+'/preparation')
  assert response.status_code==200,response.text
  value=response.json()
  print(json.dumps(dict(path=value['path'],approved=value['approved'],review_token=value['review_token'],contract=value['contract'])))
finally:store.engine.dispose()
""",
                data[1].database_url,
                str(data[1].data_dir),
                path,
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        assert child.returncode == 0, child.stderr
        reopened = json.loads(child.stdout)
        assert reopened == dict(
            path="P-B",
            approved=True,
            review_token=result["review_token"],
            contract=result["contract"],
        )
    # Authenticated original scope reader includes PB recipe, never relabelled PA.
    original = client.get(path + "/approvals/" + contract.stage_keys.generate + "_approval")
    assert original.status_code == 200, original.text
    revoked = client.post(
        path + "/withdrawal",
        json=dict(review_token=result["review_token"], confirm_withdrawal=True),
    )
    assert revoked.status_code == 200, revoked.text
    assert (
        client.post(
            path + "/consent",
            json=dict(review_token=result["review_token"], confirm_exact_scope=True),
        ).status_code
        == 409
    )
    assert business(store) == before


@pytest.mark.parametrize(
    "fault", ["cycle", "missing-check", "extra-authority", "wrong-project", "expired-goal"]
)
def test_pb_invalid_scope_never_creates_preparation(prepared_data, fault):  # noqa: F811
    data, choices = prepared_data
    store, _, client, _, pid = data[:5]
    body = dict(choices, path="P-B", extraction_recipe=recipe("ordered"))
    if fault == "cycle":
        body["extraction_recipe"]["steps"][0]["depends_on"] = ["save_pick"]
    elif fault == "missing-check":
        body["extraction_recipe"]["steps"][-2]["operator"] = "artifact.save_text"
    elif fault == "extra-authority":
        body["caps"] = dict(paid_cap=1)
    elif fault == "wrong-project":
        body["bindings"][0]["card_id"] = "goal_" + "0" * 32
    else:
        body["bindings"][0]["expected_version"] += 1
    with store.tx() as c:
        before = list(c.execute(select(delivery_graph_requests)).mappings())
    result = client.post(f"/api/projects/{pid}/natural-trials/invalid-pb/preparation", json=body)
    if fault in {"cycle", "missing-check"}:
        assert result.status_code == 400 and result.json()["error"]["code"] == "INVALID_MANIFEST", (
            result.text
        )
    else:
        assert result.status_code in {403, 409, 422}, result.text
    with store.tx() as c:
        assert before == list(c.execute(select(delivery_graph_requests)).mappings())
