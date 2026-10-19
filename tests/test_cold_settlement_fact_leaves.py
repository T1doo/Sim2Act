"""Batch-one shared predicates only: SQLite/mock facts, no Cold graph or sender."""

import json
from types import SimpleNamespace

import pytest
import test_goal_text_applications as text_fixture
import test_production_trial_policy as policy_fixture
from sqlalchemy import delete, insert, select

from sim2act import goal_applications as generation
from sim2act import production_trial_policy as policy
from sim2act import text_apps
from sim2act.contracts import Limits
from sim2act.db import (
    app_drafts,
    events,
    fingerprint,
    goal_application_candidates,
    new_id,
    operations,
    runs,
)
from sim2act.errors import DomainError

kernel = policy_fixture.kernel


def failure(call):
    with pytest.raises(DomainError) as denied:
        call()
    return denied.value.public()


def test_policy_checked_leaf_keeps_public_normalization_lock_and_binding_order(kernel, monkeypatch):
    data, contract, approval, _, _, _, item, ledger, cursor, wire, _ = kernel
    store, user = data[0], data[3]
    trace = []
    originals = {name: getattr(policy, name) for name in ("_requirements", "_ledger", "_typed")}

    def requirements(*args):
        trace.append("requirements")
        return originals["_requirements"](*args)

    def ledger_read(value):
        trace.append("ledger")
        return originals["_ledger"](value)

    def typed(value, model):
        trace.append(model.__name__)
        return originals["_typed"](value, model)

    lock = store.lock_project

    def locked(*args):
        trace.append("project-lock")
        return lock(*args)

    monkeypatch.setattr(policy, "_requirements", requirements)
    monkeypatch.setattr(policy, "_ledger", ledger_read)
    monkeypatch.setattr(policy, "_typed", typed)
    monkeypatch.setattr(store, "lock_project", locked)
    with store.tx() as c:
        public = policy._bound(store, c, user, contract, approval.request_key,
            ledger, cursor, item, wire)
        assert trace == ["requirements", "ledger", "Ledger", "AccountQuotaCursor",
                         "ReservationIdentity", "project-lock"]
        original, expected = originals["_requirements"](user, contract, approval.request_key)
        state = originals["_ledger"](ledger)
        quota = originals["_typed"](cursor, policy.AccountQuotaCursor)
        identity = originals["_typed"](item, policy.ReservationIdentity)
        trace.clear()
        assert policy._bound_from_checked_facts(store, c, user, original, expected,
            state, quota, identity, wire) == public
        assert trace == ["project-lock"], "Checked facts must not reparse the ledger or types"
        for actual_wire, actual_quota in ((wire + b" ", quota),
                (wire, quota.model_copy(update={"quota_subject": "different-bucket"}))):
            public_error = failure(lambda actual_quota=actual_quota, actual_wire=actual_wire: policy._bound(store, c, user, contract,
                approval.request_key, ledger, actual_quota, item, actual_wire))
            leaf_error = failure(lambda actual_quota=actual_quota, actual_wire=actual_wire: policy._bound_from_checked_facts(store, c, user,
                original, expected, state, actual_quota, identity, actual_wire))
            assert leaf_error == public_error


def test_actual_mock_generation_full_facts_limits_counters_and_confirmation(env, tmp_path):
    data = text_fixture.setup(env)
    store, settings, client, user = data[:4]
    try:
        rid, result, sent = text_fixture.generate(data, repair=True)
        assert result["status"] == "PARTIAL" and len(sent) == 3
        aid, _ = text_fixture.confirm(data, rid, result)
        evidence = []
        with store.tx() as c:
            run = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
            draft = dict(c.execute(select(app_drafts).where(app_drafts.c.id == aid)).mappings().one())
            marker = dict(c.execute(select(goal_application_candidates)
                .where(goal_application_candidates.c.app_id == aid)).mappings().one())
            contract, _ = generation.source(store, c, run)
            _, rows = generation.history(store, c, run)
            assert len(rows) == 3 and all(row["mode"] == "MOCK" for row in rows)
            last = generation._candidate_attempt_from_history(contract, rows)
            anchors = c.execute(select(events.c.data).where(events.c.run_id == rid,
                events.c.kind == "GA_CANDIDATE_VALIDATED")).scalars().all()
            platform = Limits(**{key: getattr(settings, key) for key in Limits.model_fields})
            roles = [None, platform, contract.limits]
            # Every Limits component reaches the original role-specific compiler;
            # frozen generation counters continue to use contract.limits separately.
            for field in Limits.model_fields:
                value = getattr(platform, field)
                changed = 1 - value if field == "max_repairs" else value - 1 if value > 1 else value + 1
                roles.append(Limits(**{**platform.model_dump(), field: changed}))
            for limits in roles:
                def from_facts(limits=limits):
                    value = generation.parse_candidate(store, c, run, last["response"],
                        limits or contract.limits)
                    return generation._candidate_from_checked_facts(value,
                        generation._candidate_validation_seal(rows[-1], value), anchors)

                try:
                    public = generation.verified_candidate(store, c, run, limits)
                except DomainError as exc:
                    assert failure(from_facts) == exc.public()
                    evidence.append({"limits": None if limits is None else limits.model_dump(),
                                     "error": exc.public()})
                else:
                    assert from_facts() == public == result["result"]["candidate"]
                    evidence.append({"limits": None if limits is None else limits.model_dump(),
                                     "complete_candidate_equal": True})
            ops = c.execute(select(operations).where(operations.c.run_id == rid)).mappings().all()
            generation.check_counters(store, c, run, rows)
            generation._check_counter_rows(rows)
            generation._check_counters_from_facts(run["context"], contract.limits, False, rows, ops)
            for field in ("requests", "tools", "repairs", "reserved_tokens"):
                changed = {**run, "context": {**run["context"], field: run["context"][field] + 1}}
                public_error = failure(lambda changed=changed: generation.check_counters(store, c, changed, rows))
                assert failure(lambda changed=changed: generation._check_counters_from_facts(changed["context"],
                    contract.limits, False, rows, ops)) == public_error
            raw = generation.verified_candidate(store, c, run, None)
            confirmation = text_apps._goal_confirmation(marker)
            accepted = text_apps._goal_acceptance_from_facts(user, draft, run, raw, confirmation)
            sealed = c.execute(select(events.c.data).where(events.c.run_id == rid,
                events.c.kind == "GA_APP_CONFIRMED")).scalars().all()
            assert sealed == [accepted]
            assert text_apps.verify_origin(store, c, user, draft, None) is None
            assert text_apps._verify_goal_origin_from_facts(user, draft, marker, run, raw,
                confirmation, accepted, sealed) is None
            for kind in ("GA_CANDIDATE_VALIDATED", "GA_APP_CONFIRMED"):
                for duplicate in (False, True):
                    savepoint = c.begin_nested()
                    try:
                        event = dict(c.execute(select(events).where(events.c.run_id == rid,
                            events.c.kind == kind)).mappings().one())
                        if duplicate:
                            c.execute(insert(events).values({**event, "id": new_id("event")}))
                        else:
                            c.execute(delete(events).where(events.c.id == event["id"]))
                        if kind == "GA_CANDIDATE_VALIDATED":
                            altered = c.execute(select(events.c.data).where(events.c.run_id == rid,
                                events.c.kind == kind)).scalars().all()
                            public_error = failure(lambda: generation.verified_candidate(store, c, run, None))
                            leaf_error = failure(lambda altered=altered: generation._candidate_from_checked_facts(raw,
                                generation._candidate_validation_seal(rows[-1], raw), altered))
                        else:
                            altered = c.execute(select(events.c.data).where(events.c.run_id == rid,
                                events.c.kind == kind)).scalars().all()
                            public_error = failure(lambda: text_apps.verify_origin(store, c, user, draft, None))
                            leaf_error = failure(lambda altered=altered: text_apps._verify_goal_origin_from_facts(user,
                                draft, marker, run, raw, confirmation, accepted, altered))
                        assert public_error == leaf_error
                    finally:
                        savepoint.rollback()
        (tmp_path / "batch1-actual-facts.json").write_text(json.dumps({
            "generation_run": rid, "actual_mock_generation_requests": len(sent),
            "real_model_calls": 0, "cold_graph_enabled": False,
            "full_candidate_and_public_errors": evidence,
            "complete_anchor_missing_and_duplicate_refused": True,
            "all_counter_fields_preserved": True,
        }, indent=2))
    finally:
        client.close()


class ReadSequence:
    """Only the explicitly expected SELECT results for original-order tests."""

    def __init__(self, results, trace):
        self.results, self.trace = list(results), trace

    def execute(self, statement):
        label, value = self.results.pop(0)
        self.trace.append(label)
        return SimpleNamespace(mappings=lambda: SimpleNamespace(first=lambda: value, one=lambda: value),
                               scalars=lambda: SimpleNamespace(all=lambda: value))


def test_generation_structure_parse_anchor_order_and_full_limits(monkeypatch):
    limits = Limits(max_requests=3, max_tools=4, max_repairs=1,
        max_total_tokens=64000, max_output_tokens=1024, run_seconds=300)
    contract = SimpleNamespace(limits=limits,
        application_generation=SimpleNamespace(version="goal-natural-spec-application.v1"))
    rows = [{"id": f"attempt-{i}", "parameters": {}, "response": {"index": i}} for i in range(3)]
    value, run, trace = {"complete": ["synthetic candidate facts"]}, {"id": "run-facts"}, []
    monkeypatch.setattr(generation, "source", lambda *args: (trace.append("source") or (contract, None)))
    monkeypatch.setattr(generation, "history", lambda *args: (trace.append("history") or ([], rows)))
    received_limits = []

    def parse(*args):
        trace.append("parse")
        received_limits.append(args[-1])
        rows[-1] = {**rows[-1], "id": "after-parse"}
        return value

    monkeypatch.setattr(generation, "parse_candidate", parse)
    seal = {"attempt_id": "after-parse", "candidate_fingerprint": fingerprint(value)}
    for role in (None, limits.model_copy(update={"max_requests": 4, "run_seconds": 299})):
        trace.clear()
        c = ReadSequence([("anchor-read", [seal])], trace)
        assert generation._verified_candidate(None, c, run, role) == value
        assert trace == ["source", "history", "parse", "anchor-read"]
        assert received_limits[-1] is (limits if role is None else role)
    cases = [(rows[:1], "VERIFICATION_FAILED"), (rows[:2], "VERSION_CONFLICT"),
             (rows + rows[:1], "VERIFICATION_FAILED"),
             ([*rows[:2], {**rows[-1], "parameters": {"generation_diagnostic": False}}],
              "VERIFICATION_FAILED")]
    for history, code in cases:
        monkeypatch.setattr(generation, "history", lambda *args, history=history: ([], history))
        trace.clear()
        error = failure(lambda: generation._verified_candidate(None, ReadSequence([], trace), run, None))
        assert error == failure(lambda history=history: generation._candidate_attempt_from_history(contract, history))
        assert error["code"] == code and trace == ["source"]


def test_text_owner_candidate_confirmation_and_seal_order(monkeypatch):
    raw = {"full": ["candidate"]}
    user = "owner"
    run = {"id": "run-facts", "version": 1, "principal_id": user, "project_id": "project",
        "status": "PARTIAL", "cancel_intent": False, "error": None,
        "result": {"candidate": raw, "candidate_fingerprint": fingerprint(raw),
                   "goal_acceptance": "NOT_RUN", "semantic_status": "UNKNOWN", "app_created": False}}
    request = {"expected_version": 1, "candidate_fingerprint": fingerprint(raw),
               "request_key": "confirm", "name": "Synthetic app"}
    marker = {"principal_id": user, "run_id": run["id"], "confirmation": request,
              "candidate_fingerprint": fingerprint(raw)}
    expected = {**raw, "goal_application": {"run_id": run["id"], "candidate_fingerprint": fingerprint(raw)}}
    draft = {"id": "app-facts", "project_id": "project", "runtime_id": "app-runtime",
             "candidate": expected, "fingerprint": fingerprint(expected)}
    trace = []
    monkeypatch.setattr(generation, "verified_candidate", lambda *args: (trace.append("candidate") or raw))
    confirmation = text_apps._goal_confirmation(marker)
    accepted = text_apps._goal_acceptance_from_facts(user, draft, run, raw, confirmation)
    c = ReadSequence([("marker", marker), ("run", run), ("seal", [accepted])], trace)
    assert text_apps.verify_origin(None, c, user, draft, None) is None
    assert trace == ["marker", "run", "candidate", "seal"]
    trace.clear()
    wrong_owner = {**marker, "principal_id": "another-owner"}
    error = failure(lambda: text_apps.verify_origin(None,
        ReadSequence([("marker", wrong_owner)], trace), user, draft, None))
    assert error["message"] == "Independent goal generation marker required" and trace == ["marker"]
    trace.clear()
    broken = {**marker, "confirmation": {}}
    public = failure(lambda: text_apps.verify_origin(None,
        ReadSequence([("marker", broken), ("run", run)], trace), user, draft, None))
    assert public == failure(lambda: text_apps._goal_confirmation(broken))
    assert trace == ["marker", "run", "candidate"]
