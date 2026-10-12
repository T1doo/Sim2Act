"""Pure offline approval/charged ledger: actual frozen Runs and Attempt rows."""

import copy
from dataclasses import replace

import pytest
from sqlalchemy import insert, select, update

from sim2act import natural_activations as activation
from sim2act.db import (
    attempts,
    events,
    fingerprint,
    grants,
    natural_activations,
    new_id,
    reservations,
    runs,
)
from sim2act.errors import DomainError
from sim2act.goal_planner import policy
from sim2act.goals import create_card

KNOWN = {
    "status": "known",
    "tokens": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
}
UNKNOWN = {"status": "unknown", "tokens": None}
LIMITS = {
    "max_requests": 1,
    "max_repairs": 0,
    "max_tools": 2,
    "max_total_tokens": 11000,
    "max_output_tokens": 512,
    "run_seconds": 120,
}


def setup(env):
    store, settings, _, user, _, pid, _ = env
    settings = replace(
        settings,
        natural_activation_enabled=True,
        goal_planner_provider="intern-s2",
        max_requests=1,
        max_repairs=0,
        max_tools=2,
        max_total_tokens=11000,
        max_output_tokens=512,
        run_seconds=120,
    )
    rid = store.resource(user, pid, "fixed.csv", "csv", activation.CSV)
    cards = {
        kind: create_card(store, user, pid, activation.synthetic_goal(rid, kind))
        for kind in activation.KINDS
    }
    body = {
        "goal_bindings": [
            {
                "kind": kind,
                "card_id": card["id"],
                "expected_version": card["version"],
                "expected_fingerprint": card["fingerprint"],
            }
            for kind, card in cards.items()
        ],
        "request_key": "fixed-synthetic-scope",
    }
    draft = activation.create(store, user, pid, body, settings)
    approve = {
        "expected_version": 1,
        "expected_scope_fingerprint": draft["scope_fingerprint"],
        "request_key": "explicit-consent",
        "consent": activation.CONSENT,
    }
    approved = activation.approve(store, user, draft["id"], approve, settings)
    return store, settings, user, pid, rid, cards, body, approve, approved


def make_run(value, kind, key=None):
    store, settings, user, pid, _, cards, _, _, approved = value
    card = cards[kind]
    body = {
        "expected_version": card["version"],
        "expected_fingerprint": card["fingerprint"],
        "request_key": key or kind,
    }
    bound = activation.binding_for_run(store, user, approved["id"], card["id"], body, settings)
    rid = store.submit(
        user,
        pid,
        "",
        [],
        body["request_key"],
        policy={
            "limits": LIMITS,
            "mode": "mock",
            "request_model": "intern-s2",
            "natural_planning": {**policy("intern-s2"), "activation": bound},
        },
        goal_source={
            "card_id": card["id"],
            "version": card["version"],
            "fingerprint": card["fingerprint"],
        },
    )
    # Claim the real durable Run, no provider invoked by these module tests.
    run = store.claim("activation-unit-worker", 60)
    assert run["id"] == rid
    return run


def reserve(value, run, envelope=1000, fail=False):
    store, settings, *_ = value
    aid = new_id("attempt")
    with store.tx() as c:
        store.lock_project(c, run["principal_id"], run["project_id"])
        current = store.guard(c, run["id"], run["fence"])
        params = {
            "stream": False,
            "max_tokens": 512,
            "request_fingerprint": "a" * 64,
            "planning_fence": run["fence"],
            "planning_wire": {
                "sha256": "b" * 64,
                "bytes": envelope - 512,
                "characters": min(envelope - 512, 8000),
            },
        }
        c.execute(
            insert(attempts).values(
                id=aid,
                run_id=run["id"],
                mode="MOCK",
                request_model="intern-s2",
                status="STARTED",
                created_at=activation.now(),
                usage=UNKNOWN,
                reserved_tokens=envelope,
                parameters=params,
            )
        )
        c.execute(insert(reservations).values(id=aid, subject=settings.quota_subject,
                  created_at=activation.now(), run_id=run["id"]))
        activation.reserve_slot(store, c, current, run["fence"], aid, envelope, "b" * 64, settings)
        ctx = copy.deepcopy(current["context"])
        ctx["requests"] += 1
        ctx["reserved_tokens"] += envelope
        c.execute(update(runs).where(runs.c.id == run["id"]).values(context=ctx))
        if fail:
            raise RuntimeError("Controlled post-reservation transaction failure")
    return aid


def sending(value, run, aid):
    store, settings, *_ = value
    with store.tx() as c:
        store.lock_project(c, run["principal_id"], run["project_id"])
        current = store.guard(c, run["id"], run["fence"])
        activation.mark_sending(store, c, current, run["fence"], aid, settings)


def settle(value, run, aid, status="RECEIVED", usage=KNOWN):
    store, *_ = value
    with store.tx() as c:
        store.lock_project(c, run["principal_id"], run["project_id"])
        current = store.guard(c, run["id"], run["fence"])
        c.execute(
            update(attempts)
            .where(attempts.c.id == aid)
            .values(
                status=status,
                usage=usage,
                response={"content": "synthetic"},
                response_model="Intern-S2",
            )
        )
        return activation.settle(store, c, current, run["fence"], aid, status, usage)


def test_default_disabled_and_closed_inputs_no_write(env):
    store, settings, _, user, _, pid, _ = env
    with pytest.raises(DomainError) as exc:
        activation.create(store, user, pid, {"request_key": "x", "goal_bindings": []}, settings)
    assert exc.value.code == "RESOURCE_UNAVAILABLE"
    with store.tx() as c:
        assert not c.execute(select(natural_activations)).first()


def test_two_actual_runs_share_two_nonrefundable_slots_and_static_reads(env, monkeypatch):
    value = setup(env)
    store, _, user, _, _, _, _, _, approved = value
    for kind in activation.KINDS:
        run = make_run(value, kind)
        aid = reserve(value, run, envelope=10512)
        sending(value, run, aid)
        settle(value, run, aid)
        current = activation.now()
        monkeypatch.setattr(activation, "now", lambda current=current: current + 60)
    result = activation.inspect(store, user, approved["id"])
    assert result["charged_requests"] == 2 and result["reserved_tokens"] == 21024
    with store.tx() as c:
        assert len(c.execute(select(attempts)).all()) == 2
        assert (
            len(
                c.execute(
                    select(events).where(events.c.kind == "NL_ACTIVATION_SLOT_RESERVED")
                ).all()
            )
            == 2
        )


def test_same_approval_key_does_not_extend_ttl_and_changed_body_conflicts(env, monkeypatch):
    value = setup(env)
    store, settings, user, _, _, _, _, body, approved = value
    old = approved["approval"]
    monkeypatch.setattr(activation, "now", lambda: old["approved_at"] + 7000)
    assert activation.approve(store, user, approved["id"], body, settings)["approval"] == old
    with pytest.raises(DomainError):
        activation.approve(
            store, user, approved["id"], {**body, "request_key": "different"}, settings
        )


@pytest.mark.parametrize(
    "mutation",
    ["unknown_goal", "synthetic_claim", "wrong_bytes", "extra", "bool_version", "duplicate_kind"],
)
def test_scope_is_exact_not_caller_claimed(env, mutation):
    store, settings, _, user, _, pid, _ = env
    settings = replace(settings, natural_activation_enabled=True)
    data = activation.CSV if mutation != "wrong_bytes" else "item,quantity_z\na,999\n"
    rid = store.resource(user, pid, "synthetic.csv", "csv", data)
    content = activation.synthetic_goal(rid, "read_preview")
    if mutation == "unknown_goal":
        content["goal"] = "Run arbitrary task"
    if mutation == "synthetic_claim":
        content["known"] = ["I claim this is synthetic"]
    card = create_card(store, user, pid, content)
    item = {
        "kind": "read_preview",
        "card_id": card["id"],
        "expected_version": card["version"],
        "expected_fingerprint": card["fingerprint"],
    }
    body = {"goal_bindings": [item], "request_key": "reject"}
    if mutation == "extra":
        body["approved"] = True
    if mutation == "bool_version":
        item["expected_version"] = True
    if mutation == "duplicate_kind":
        body["goal_bindings"] *= 2
    with pytest.raises(DomainError):
        activation.create(store, user, pid, body, settings)
    with store.tx() as c:
        assert not c.execute(select(natural_activations)).first()


@pytest.mark.parametrize(
    "reason", ["revoke", "expiry", "disabled", "account", "endpoint", "model", "resource", "grant"]
)
def test_active_gates_deny_without_attempt_or_slot(env, monkeypatch, reason):
    value = setup(env)
    store, settings, user, _, resource, _, _, _, approved = value
    if reason == "revoke":
        activation.revoke(
            store,
            user,
            approved["id"],
            {
                "expected_version": 2,
                "expected_scope_fingerprint": approved["scope_fingerprint"],
                "request_key": "stop",
            },
            settings,
        )
    if reason == "expiry":
        monkeypatch.setattr(activation, "now", lambda: approved["approval"]["expires_at"])
    if reason == "disabled":
        settings = replace(settings, natural_activation_enabled=False)
    if reason == "account":
        settings = replace(settings, quota_subject="another-existing-subject")
    if reason == "endpoint":
        monkeypatch.setattr(activation.InternModel, "ENDPOINT", "https://unregistered.invalid")
    if reason == "model":
        settings = replace(settings, model="another-model")
    if reason == "resource":
        with store.tx() as c:
            c.execute(
                update(activation.resources)
                .where(activation.resources.c.id == resource)
                .values(content=activation.CSV + "c,5\n")
            )
    if reason == "grant":
        with store.tx() as c:
            c.execute(update(grants).where(grants.c.resource_id == resource).values(revoked=True))
    with pytest.raises(DomainError):
        card = value[5]["read_preview"]
        activation.binding_for_run(
            store,
            user,
            approved["id"],
            card["id"],
            {"expected_version": card["version"], "expected_fingerprint": card["fingerprint"]},
            settings,
        )
    with store.tx() as c:
        assert not c.execute(select(attempts)).first()
        assert c.execute(select(natural_activations.c.ledger)).scalar_one() == []


def test_revoke_after_send_still_settles_known_actual_receipt(env):
    value = setup(env)
    store, settings, user, _, _, _, _, _, approved = value
    run = make_run(value, "read_preview")
    aid = reserve(value, run)
    sending(value, run, aid)
    activation.revoke(
        store,
        user,
        approved["id"],
        {
            "expected_version": 2,
            "expected_scope_fingerprint": approved["scope_fingerprint"],
            "request_key": "stop",
        },
        settings,
    )
    assert settle(value, run, aid)["status"] == "RECEIVED"
    assert activation.inspect(store, user, approved["id"])["charged_requests"] == 1


def test_started_unknown_and_per_goal_limit_block_further_sends(env):
    value = setup(env)
    first = make_run(value, "read_preview")
    aid = reserve(value, first)
    second = make_run(value, "sum_quantity_z")
    with pytest.raises(DomainError):
        reserve(value, second)
    sending(value, first, aid)
    settle(value, first, aid)
    # Different Run cannot reset the approved goal's one slot.
    third = make_run(value, "read_preview", key="again")
    with pytest.raises(DomainError):
        reserve(value, third)


@pytest.mark.parametrize(
    "mutation", ["delete_ledger", "parameters", "scope_cap", "approval_ttl", "unknown_usage"]
)
def test_ledger_and_seals_reject_tamper(env, mutation):
    value = setup(env)
    store, _, user, _, _, _, _, _, approved = value
    run = make_run(value, "read_preview")
    aid = reserve(value, run)
    sending(value, run, aid)
    settle(value, run, aid)
    with store.tx() as c:
        row = c.execute(select(natural_activations)).mappings().one()
        if mutation == "delete_ledger":
            c.execute(update(natural_activations).values(ledger=[]))
        elif mutation == "parameters":
            a = c.execute(select(attempts)).mappings().one()
            p = copy.deepcopy(a["parameters"])
            p["max_tokens"] = 999
            c.execute(update(attempts).where(attempts.c.id == aid).values(parameters=p))
        elif mutation == "scope_cap":
            scope = copy.deepcopy(row["scope"])
            scope["caps"]["requests"] = 200
            c.execute(
                update(natural_activations).values(
                    scope=scope, scope_fingerprint=fingerprint(scope)
                )
            )
        elif mutation == "approval_ttl":
            approval = copy.deepcopy(row["approval"])
            approval["expires_at"] += 7200
            c.execute(
                update(natural_activations).values(
                    approval=approval, approval_fingerprint=fingerprint(approval)
                )
            )
        else:
            c.execute(update(attempts).where(attempts.c.id == aid).values(usage=UNKNOWN))
    with pytest.raises(DomainError):
        activation.inspect(store, user, approved["id"])


def test_reservation_failure_rolls_back_attempt_slot_and_events(env):
    value = setup(env)
    store, _, user, _, _, _, _, _, approved = value
    run = make_run(value, "read_preview")
    with pytest.raises(RuntimeError):
        reserve(value, run, fail=True)
    assert activation.inspect(store, user, approved["id"])["charged_requests"] == 0
    with store.tx() as c:
        assert not c.execute(select(attempts)).first()


def test_foreign_owner_and_project_and_secret_are_not_scope(env):
    value = setup(env)
    store, settings, user, _, _, _, _, _, approved = value
    with pytest.raises(DomainError):
        activation.inspect(store, env[4], approved["id"])
    encoded = str(activation.inspect(store, user, approved["id"]))
    assert "token" not in str(approved["scope"]["provider"])
    assert settings.token == ""
    assert "password" not in encoded.lower()


def test_exact_plan_kind_and_limits_guard(env):
    value = setup(env)
    store, _, *_ = value
    run = make_run(value, "sum_quantity_z")
    with store.tx() as c:
        current = store.guard(c, run["id"], run["fence"])
        good = {
            "steps": [
                {
                    "id": "sum",
                    "tool_ref": "data.aggregate_csv",
                    "resource_id": value[4],
                    "column": "quantity_z",
                    "depends_on": [],
                }
            ]
        }
        assert activation.validate_plan(store, c, current, good)["kind"] == "sum_quantity_z"
        with pytest.raises(DomainError):
            activation.validate_plan(
                store, c, current, {"steps": [{**good["steps"][0], "tool_ref": "resource.read"}]}
            )


def test_concurrent_two_goals_serialize_then_share_one_two_request_budget(env, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    value = setup(env)
    store, _, user, _, _, _, _, _, approved = value
    run_list = [make_run(value, kind) for kind in activation.KINDS]

    def attempt(run):
        try:
            return run, reserve(value, run)
        except DomainError as exc:
            return run, exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(attempt, run_list))
    succeeded = [(r, a) for r, a in result if a.startswith("attempt_")]
    denied = [(r, a) for r, a in result if not a.startswith("attempt_")]
    assert len(succeeded) == len(denied) == 1
    assert denied[0][1] == "OUTCOME_UNKNOWN"
    first, aid = succeeded[0]
    sending(value, first, aid)
    settle(value, first, aid)
    current = activation.now()
    monkeypatch.setattr(activation, "now", lambda: current + 60)
    second = denied[0][0]
    aid2 = reserve(value, second)
    sending(value, second, aid2)
    settle(value, second, aid2)
    assert activation.inspect(store, user, approved["id"])["charged_requests"] == 2
    with store.tx() as c:
        assert len(c.execute(select(attempts)).all()) == 2


@pytest.mark.parametrize(
    "usage",
    [
        UNKNOWN,
        {
            "status": "known",
            "tokens": {"prompt_tokens": 1000, "completion_tokens": 1, "total_tokens": 1001},
        },
    ],
)
def test_unknown_or_actual_envelope_overrun_stops_other_goal_without_refund(env, usage):
    value = setup(env)
    store, settings, user, _, _, cards, _, _, approved = value
    run = make_run(value, "read_preview")
    aid = reserve(value, run)
    sending(value, run, aid)
    receipt = settle(
        value, run, aid, status="FAILED" if usage == UNKNOWN else "RECEIVED", usage=usage
    )
    assert receipt["status"] == "UNKNOWN" and receipt["usage"] == usage
    public = activation.inspect(store, user, approved["id"])
    assert public["charged_requests"] == 1 and public["reserved_tokens"] == 1000
    card = cards["sum_quantity_z"]
    with pytest.raises(DomainError) as exc:
        activation.binding_for_run(
            store,
            user,
            approved["id"],
            card["id"],
            {"expected_version": card["version"], "expected_fingerprint": card["fingerprint"]},
            settings,
        )
    assert exc.value.code == "OUTCOME_UNKNOWN"


def test_22000_global_cap_cannot_be_extended_by_larger_envelope(env):
    value = setup(env)
    store, _, user, _, _, _, _, _, approved = value
    run = make_run(value, "read_preview")
    with pytest.raises(DomainError):
        reserve(value, run, envelope=22001)
    assert activation.inspect(store, user, approved["id"])["scope"]["caps"]["tokens"] == 22000
    with store.tx() as c:
        assert not c.execute(select(attempts)).first()


def test_deleted_ledger_and_charge_event_still_fail_actual_attempt_reverse_audit(env):
    from sqlalchemy import delete

    value = setup(env)
    store, _, user, _, _, _, _, _, approved = value
    run = make_run(value, "read_preview")
    aid = reserve(value, run)
    sending(value, run, aid)
    settle(value, run, aid)
    with store.tx() as c:
        c.execute(update(natural_activations).values(ledger=[]))
        c.execute(
            delete(events).where(
                events.c.run_id == approved["id"],
                events.c.kind.in_(
                    [
                        "NL_ACTIVATION_SLOT_RESERVED",
                        "NL_ACTIVATION_SENDING",
                        "NL_ACTIVATION_SETTLED",
                    ]
                ),
            )
        )
    with pytest.raises(DomainError) as exc:
        activation.inspect(store, user, approved["id"])
    assert exc.value.code == "OUTCOME_UNKNOWN"


def test_expired_after_send_or_grant_revoke_does_not_drop_known_settlement(env, monkeypatch):
    value = setup(env)
    store, _, user, _, resource, _, _, _, approved = value
    run = make_run(value, "read_preview")
    aid = reserve(value, run)
    sending(value, run, aid)
    monkeypatch.setattr(activation, "now", lambda: approved["approval"]["expires_at"] + 1)
    with store.tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == resource).values(revoked=True))
    assert settle(value, run, aid)["status"] == "RECEIVED"
    public = activation.inspect(store, user, approved["id"])
    assert not public["approved_not_expired"] and public["charged_requests"] == 1


def test_cross_project_and_offline_activation_cannot_become_live_authority(env):
    value = setup(env)
    store, settings, user, _, _, _, _, _, approved = value
    run = make_run(value, "read_preview")
    with store.tx() as c:
        fake = dict(store.guard(c, run["id"], run["fence"]))
        fake["project_id"] = new_id("proj")
        with pytest.raises(DomainError):
            activation.validate_run(store, c, fake, settings, active=True)
    store.test_only = False  # Test-only scope cannot be reused by a production sender.
    try:
        with store.tx() as c:
            current = store.guard(c, run["id"], run["fence"])
            with pytest.raises(DomainError):
                activation.validate_run(
                    store,
                    c,
                    current,
                    replace(
                        settings,
                        mode="live",
                        live_enabled=True,
                        token="synthetic-only-not-a-credential",
                        natural_activation_live_id=approved["id"],
                    ),
                    active=True,
                )
    finally:
        store.test_only = True


@pytest.mark.parametrize(
    "partial",
    [
        {"status": "partial", "tokens": {"prompt_tokens": 10}},
        {"status": "partial", "tokens": {"prompt_tokens": 10, "completion_tokens": 20}},
        {
            "status": "partial",
            "tokens": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 99},
        },
    ],
)
def test_normalized_partial_usage_is_persisted_unknown_not_rolled_back(env, partial):
    value = setup(env)
    store, _, user, _, _, _, _, _, approved = value
    run = make_run(value, "read_preview")
    aid = reserve(value, run)
    sending(value, run, aid)
    receipt = settle(value, run, aid, status="FAILED", usage=partial)
    assert receipt["status"] == "UNKNOWN" and receipt["usage"] == partial
    assert activation.inspect(store, user, approved["id"])["charged_requests"] == 1
    with store.tx() as c:
        assert (
            c.execute(select(attempts.c.usage).where(attempts.c.id == aid)).scalar_one() == partial
        )
