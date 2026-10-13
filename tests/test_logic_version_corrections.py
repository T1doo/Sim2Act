"""Actual modified PA/PB recipe, fresh input, one correction and independent review."""

import json

import pytest
from sqlalchemy import select
from test_logic_version_uses import (
    test_pa_modified_release_third_material_cold_worker_and_fresh_owner as make_pa,
)
from test_logic_version_uses import (
    test_pb_modified_release_third_material_cold_worker_and_fresh_owner as make_pb,
)
from test_natural_spec_corrections import prepare_correction
from test_natural_spec_owner_acceptance import decision, preview, state
from test_spec_app_operations import snapshot

from sim2act.db import fingerprint, internal_app_runs, internal_run_bindings


@pytest.mark.parametrize("family", ["pa", "pb"])
def test_fresh_modified_parent_rejection_freezes_current_recipe(env, tmp_path, family):
    (make_pa if family == "pa" else make_pb)(env, tmp_path)
    proof = json.loads((tmp_path / "third-proof.json").read_text())
    reviewed = proof["review"]
    store, settings, client = env[:3]
    iid = reviewed["instance_id"]
    with store.tx() as c:
        parent = c.execute(
            select(internal_run_bindings.c.run_id)
            .join(internal_app_runs, internal_app_runs.c.id == internal_run_bindings.c.app_run_id)
            .where(internal_app_runs.c.instance_id == iid, internal_app_runs.c.result_version == 1)
        ).scalar_one()
    data = (store, settings, client, reviewed["principal_id"], reviewed["project_id"])
    path = f"/api/internal/instances/{iid}/runs/{parent}/spec-owner-review"
    old = snapshot(store)
    p, _ = preview(data, path, "reject-modified-parent")
    body = decision(p, True)
    body["request_key"] = "reject-modified-parent-decision"
    body["choices"][0]["reason"] = (
        "SIMULATED reconsider this exact new-input result under unchanged criteria"
    )
    r = client.post(path + "-requests", json=body)
    assert r.status_code == 201, r.text
    s = state(data, path)
    prepare = dict(
        request_key="one-modified-correction",
        expected_owner_sequence=s["sequence"],
        declaration_id=s["latest"]["id"],
        declaration_fingerprint=s["latest"]["fingerprint"],
        expected_context_fingerprint=fingerprint(s["current"]),
    )
    base = path.replace("/spec-owner-review", "")
    value, commit = prepare_correction(data, base, prepare)
    assert value["effective_candidate"] == reviewed["effective_candidate"]
    assert value["context"]["source_goal"] == reviewed["target_goal"]
    assert (
        value["context"]["material"]["resource_id"] == reviewed["variable_bindings"]["resource_id"]
    )
    assert value["logic_source"]["origin"] == reviewed["saved_logic_source"]["origin"]
    assert (
        value["effective_candidate"]["logic_revision"]
        == reviewed["effective_candidate"]["logic_revision"]
    )
    assert client.get(base + "/correction-reviews/" + prepare["request_key"]).json() == value
    after = snapshot(store)
    for table in ("internal_instance_data", "natural_owner_records", "natural_owner_seals"):
        assert all(row in after[table] for row in old[table]), table
    for table in ("app_drafts", "internal_releases", "goal_cards", "goal_card_versions"):
        assert after[table] == old[table], table
    (tmp_path / "modified-parent-proof.json").write_text(
        json.dumps(
            dict(
                family=family,
                parent_run_id=parent,
                instance_id=iid,
                project_id=reviewed["project_id"],
                principal_id=reviewed["principal_id"],
                owner_path=path,
                base_path=base,
                prepare=prepare,
                review=value,
                commit=commit,
                per_use=reviewed,
                declaration=s["latest"],
                content=proof["result"]["source_content"],
                real_paid_models=0,
                simulated_human_only=True,
            ),
            indent=2,
        )
        + "\n"
    )
