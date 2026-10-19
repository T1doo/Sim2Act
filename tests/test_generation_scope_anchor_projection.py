"""Scalar eligibility projection only; synthetic markers confer no authority."""

import copy

from sqlalchemy import delete, insert, update

from sim2act import goal_applications as generation
from sim2act.db import attempts, events, fingerprint, run_contracts, runs
from sim2act.spec_production import VERSION


def test_join_preserves_exact_event_and_attempt_cardinality(env):
    store, _, _, user, _, project_id, resource_id = env
    run_id = "synthetic-anchor-only"
    with store.tx() as c:
        project = store.own_project(c, user, project_id)
        owner = dict(principal_id=user, project_id=project_id, runtime_id=project["runtime_id"])
        policy = dict(version="goal-natural-spec-application.v1", app_id="synthetic-app", activation=None)
        saved = dict(application_generation=policy, runtime_id=owner["runtime_id"],
            goal=dict(owner_id=user, project_id=project_id, resource_refs=[resource_id]),
            resources=[dict(resource_id=resource_id)],
            source_goal_card=dict(snapshot=dict(content=dict(resource_refs=[resource_id]))))
        c.execute(insert(runs).values(id=run_id, **owner, resource_refs=[resource_id]))
        c.execute(insert(run_contracts).values(run_id=run_id, snapshot=saved, fingerprint=fingerprint(saved)))
        c.execute(insert(events).values(id="accepted-1", run_id=run_id, kind="ACCEPTED",
            data=dict(application_generation=policy)))
        # Non-ACCEPTED events must not increase or hide the accepted cardinality.
        c.execute(insert(events).values(id="other-event", run_id=run_id, kind="STATE", data={}))
        for i in range(3):
            c.execute(insert(attempts).values(id=f"anchor-attempt-{i}", run_id=run_id,
                mode="LIVE", parameters=dict(pa_trial_binding=dict(version=VERSION))))
        anchor = generation._journal_scope_anchor(store, c, run_id)
        assert anchor == dict(owner=owner, refs=[resource_id], versions=[VERSION] * 3,
            hints=dict(fingerprint=fingerprint(saved), kind=policy["version"], app_id=policy["app_id"],
                aid=None, runtime=owner["runtime_id"], owner=user, project=project_id,
                refs=[resource_id], resource=resource_id, goal_refs=[resource_id]),
            accepted=[dict(id="accepted-1", kind=policy["version"], aid=None, app_id=policy["app_id"])])
        assert generation._journal_scope_anchor(store, c, run_id, expected=owner) == anchor
        assert generation._journal_scope_anchor(store, c, run_id, expected=owner | dict(principal_id="other")) is None

        mutations = [
            delete(run_contracts).where(run_contracts.c.run_id == run_id),
            delete(events).where(events.c.id == "accepted-1"),
            insert(events).values(id="accepted-2", run_id=run_id, kind="ACCEPTED", data=dict(application_generation=policy)),
            delete(attempts).where(attempts.c.run_id == run_id),
            delete(attempts).where(attempts.c.id == "anchor-attempt-2"),
            insert(attempts).values(id="anchor-attempt-3", run_id=run_id, mode="LIVE",
                parameters=dict(pa_trial_binding=dict(version=VERSION))),
            update(attempts).where(attempts.c.id == "anchor-attempt-1").values(parameters={}),
            update(attempts).where(attempts.c.id == "anchor-attempt-1").values(parameters=dict(pa_trial_binding=None)),
            update(attempts).where(attempts.c.id == "anchor-attempt-1").values(parameters=dict(pa_trial_binding=dict(version="unknown"))),
            update(attempts).where(attempts.c.run_id == run_id).values(parameters={}),
        ]
        for statement in mutations:
            savepoint = c.begin_nested()
            try:
                c.execute(statement)
                assert generation._journal_scope_anchor(store, c, run_id) is None
            finally:
                savepoint.rollback()
            assert generation._journal_scope_anchor(store, c, run_id) == anchor
        changed = copy.deepcopy(saved)
        changed["application_generation"]["activation"] = dict(approval_id="not-a-trial")
        savepoint = c.begin_nested()
        try:
            c.execute(update(run_contracts).where(run_contracts.c.run_id == run_id).values(snapshot=changed))
            assert generation._journal_scope_anchor(store, c, run_id) is None
        finally:
            savepoint.rollback()
