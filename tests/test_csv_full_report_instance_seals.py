"""Independent synthetic counterexamples for immutable Release and result lineage."""

import copy
import json

from sqlalchemy import select, update
from test_csv_full_report_instances import complete, delivered
from test_csv_goal_revisions import raw_trace as raw_trace
from test_natural_receipt_candidate import table_snapshot

from sim2act.csv_full_report_instances import EVENT, JOB
from sim2act.db import (
    delivery_graph_requests,
    events,
    fingerprint,
    internal_app_runs,
    internal_instance_data,
    internal_releases,
    runs,
)


def _save(tmp_path, name, evidence):
    (tmp_path / name).write_text(json.dumps(evidence, ensure_ascii=False, indent=2, default=str))


def _second_release(client, root, release_body):
    prepared = client.post(
        root + "/release-approvals",
        json={**release_body, "request_key": "unadopted-second-release"},
    )
    assert prepared.status_code == 201, prepared.text
    prepared = prepared.json()
    committed = client.post(
        f"/api/internal/approvals/{prepared['id']}/commit",
        json={"fingerprint": prepared["fingerprint"]},
    )
    assert committed.status_code == 200, committed.text
    return committed.json()


def test_release_numeric_type_cannot_be_resigned_without_the_approval(env, tmp_path):
    *_, release, instance, root, release_body, approval = delivered(env)
    store, _, client, *_ = env
    altered = copy.deepcopy(release["snapshot"])
    assert type(altered["definition_version"]) is int
    altered["definition_version"] = float(altered["definition_version"])
    assert altered == release["snapshot"]  # Python equality must not be the immutable anchor.
    assert fingerprint(altered) != fingerprint(release["snapshot"])
    with store.tx() as c:
        c.execute(
            update(internal_releases)
            .where(internal_releases.c.id == release["id"])
            .values(snapshot=altered, fingerprint=fingerprint(altered))
        )
    before = table_snapshot(store)
    response = client.get(f"/api/internal/releases/{release['id']}")
    after = table_snapshot(store)
    _save(
        tmp_path,
        "resigned-release-type.json",
        {
            "release_id": release["id"],
            "approval_id": approval["id"],
            "changed_snapshot": altered,
            "status": response.status_code,
            "response": response.json(),
            "before_fp": fingerprint(before),
            "after_fp": fingerprint(after),
        },
    )
    assert response.status_code == 409, response.text
    assert before == after


def test_successful_result_cannot_be_relabelled_to_an_unadopted_release(env, tmp_path):
    source, original, recipe, material, release, instance, root, release_body, _ = delivered(env)
    store, _, client, *_ = env
    _, receipt, completed = complete(env, instance["id"], release, material, "before-any-adoption")
    target = _second_release(client, root, release_body)
    rid, app_run_id = receipt["run_id"], receipt["app_run_id"]
    # All new adapter copies agree after the edit. The independent instance
    # creation history and actual ordinary workflow contract remain untouched.
    with store.tx() as c:
        rows = (
            c.execute(
                select(delivery_graph_requests).where(
                    delivery_graph_requests.c.app_id == rid,
                    delivery_graph_requests.c.kind.in_([JOB, JOB + "_seal"]),
                )
            )
            .mappings()
            .all()
        )
        assert len(rows) == 2
        accepted = copy.deepcopy(rows[0]["snapshot"])
        accepted["request"]["expected_release_fingerprint"] = target["fingerprint"]
        binding = accepted["response"]
        binding.update(
            release_id=target["id"],
            release_fingerprint=target["fingerprint"],
            request_fingerprint=fingerprint(accepted["request"]),
        )
        seal = fingerprint(binding)
        c.execute(
            update(internal_app_runs)
            .where(internal_app_runs.c.id == app_run_id)
            .values(release_id=target["id"], input=binding, fingerprint=seal)
        )
        context = copy.deepcopy(
            c.execute(select(runs.c.context).where(runs.c.id == rid)).scalar_one()
        )
        context["csv_full_report_instance"] = {"app_run_id": app_run_id, "fingerprint": seal}
        c.execute(update(runs).where(runs.c.id == rid).values(context=context))
        c.execute(
            update(events)
            .where(events.c.run_id == rid, events.c.kind == EVENT)
            .values(data=binding)
        )
        for row in rows:
            c.execute(
                update(delivery_graph_requests)
                .where(
                    delivery_graph_requests.c.app_id == rid,
                    delivery_graph_requests.c.principal_id == row["principal_id"],
                    delivery_graph_requests.c.kind == row["kind"],
                    delivery_graph_requests.c.request_key == row["request_key"],
                )
                .values(
                    snapshot=accepted,
                    request_fingerprint=fingerprint(accepted["request"]),
                    fingerprint=fingerprint(accepted),
                )
            )
        value = copy.deepcopy(
            c.execute(
                select(internal_instance_data.c.data).where(
                    internal_instance_data.c.run_id == app_run_id
                )
            ).scalar_one()
        )
        value["release_ref"] = target["id"]
        c.execute(
            update(internal_instance_data)
            .where(internal_instance_data.c.run_id == app_run_id)
            .values(release_id=target["id"], data=value, fingerprint=fingerprint(value))
        )
    before = table_snapshot(store)
    response = client.get(root)
    after = table_snapshot(store)
    _save(
        tmp_path,
        "resigned-unadopted-history.json",
        {
            "source_run_id": source,
            "ordinary_result": completed["result"],
            "instance_id": instance["id"],
            "created_release_id": release["id"],
            "unadopted_release_id": target["id"],
            "resigned_binding": binding,
            "status": response.status_code,
            "response": response.json(),
            "before_fp": fingerprint(before),
            "after_fp": fingerprint(after),
        },
    )
    assert response.status_code == 409, response.text
    assert before == after
