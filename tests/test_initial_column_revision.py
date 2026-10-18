"""First spec keeps its original Goal; no new resource or permission fixture."""

import copy
import json

from test_csv_goal_revisions import baseline
from test_local_record_apps import snapshot


def test_original_goal_first_column_preview_and_precise_noop_rejection(env, tmp_path):
    data, aid, release, instance, _cid, _content, app = baseline(env)
    client = data[2]
    derived = client.post(f"/api/projects/{data[5]}/apps/{aid}/delivery-graph/derive", json={
        "request_key": "initial-column-anchor", "expected_candidate_fingerprint": app["fingerprint"],
    })
    assert derived.status_code == 201, derived.text
    path = f"/api/internal/instances/{instance['id']}/csv-goal-revisions"
    context = client.get(path + "/context")
    assert context.status_code == 200, context.text
    ctx = context.json()
    assert ctx["goal"]["version"] == ctx["original_goal_version"] == 1
    body = dict(request_key="first-column", expected_revision=1,
                expected_release_fingerprint=release["fingerprint"], expected_graph_fingerprint=ctx["graph_fingerprint"],
                goal_version=1, goal_fingerprint=ctx["goal"]["fingerprint"], baseline_column="amount", column="quantity")
    before = snapshot(data[0])
    for change in [dict(column="amount"), dict(goal_fingerprint="0" * 64)]:
        rejected = client.post(path + "/previews", json={**body, **change})
        assert rejected.status_code == 409, rejected.text
        assert rejected.json()["error"]["submission_rejection"]["acceptance"] == "NOT_ACCEPTED"
        assert snapshot(data[0]) == before
    accepted = client.post(path + "/previews", json=body)
    assert accepted.status_code == 201, accepted.text
    value = accepted.json()
    action = next(n for n in value["baseline_graph"]["graph"]["nodes"] if n["key"] == "action:aggregate")
    assert value["impact"]["changed_nodes"] == [action["id"]]
    assert value["impact"]["revalidation_scope"] == "APP"
    assert value["context"]["goal"]["snapshot"] == app["candidate"]["generation"]["goal_snapshot"]
    assert value["effective_candidate"]["goal"] == app["candidate"]["goal"]
    after = snapshot(data[0])
    for table in ["principals", "grants", "resources", "goal_cards", "goal_card_versions", "app_drafts"]:
        assert after[table] == before[table]
    assert client.get(path + "/previews/first-column").json() == copy.deepcopy(value)
    (tmp_path / "initial-column-preview-proof.json").write_text(json.dumps(dict(
        before=before, after=after, context=ctx, preview=value, noops_preserve_all55=True), ensure_ascii=False, indent=2))
