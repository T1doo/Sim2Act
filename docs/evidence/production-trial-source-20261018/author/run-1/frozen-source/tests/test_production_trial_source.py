"""Fixed server fixture evidence; no real source or model qualification."""

import base64
import copy
import hashlib
import json
import time
from dataclasses import replace

import httpx
import pytest
from sqlalchemy import delete, event, select, update
from test_production_trial_sender import prepare
from test_spec_app_operations import snapshot

from sim2act import production_evidence as evidence
from sim2act import production_trial_admission as admission
from sim2act import production_trial_journal as journal
from sim2act import production_trial_sender as sender
from sim2act import production_trial_source as source
from sim2act.db import delivery_graph_requests as rows
from sim2act.db import fingerprint
from sim2act.errors import DomainError


def scope_for(t):
    return evidence.requirements_for(t["data"][3], t["contract"], t["approval"].request_key)


def bundle_for(t, scope=None):
    expected = scope or scope_for(t)
    common = dict(
        issuer=source.ISSUER,
        requirements_fingerprint=fingerprint(expected.model_dump()),
        account_id=t["identity"].account_id,
        provider=expected.provider,
        model=expected.model,
        endpoint=expected.endpoint,
        observed_at=time.time() - 600,
        expires_at=expected.expires_at,
    )
    return dict(
        version="UNINSTALLED_SYNTHETIC_ACCOUNT_SOURCE_V1",
        identity=dict(common, role="identity", identity_confirmed=True),
        entitlement=dict(common, role="entitlement", legal_free_entitlement=True),
        enforcement=dict(
            common,
            role="enforcement",
            enforced_zero_charge=True,
            paid_cap=0,
            billable_fallback_disabled=True,
        ),
        status=dict(common, role="status", revoked=False),
    )


def seed(t, bundle, *, scope=None, provenance="UNINSTALLED_SYNTHETIC_FIXTURE"):
    expected = scope or scope_for(t)
    payload = json.dumps(bundle, indent=1).encode()
    request = source.request_for(expected, t["identity"].account_id)
    response = dict(provenance=provenance, raw_b64=base64.b64encode(payload).decode("ascii"))
    with t["data"][0].tx() as c:
        prior = journal._pair(
            c, expected.principal_id, expected.project_id, source.KIND, expected.trial_key
        )
        journal._cas_pair(
            c,
            expected.principal_id,
            expected.project_id,
            source.KIND,
            expected.trial_key,
            prior,
            journal._snapshot(request, response),
        )
    return payload


def remove_source(t):
    with t["data"][0].tx() as c:
        c.execute(
            delete(rows).where(
                rows.c.principal_id == t["data"][3],
                rows.c.app_id == t["contract"].project_id,
                rows.c.kind.in_([source.KIND, source.KIND + "_seal"]),
                rows.c.request_key == t["contract"].trial_key,
            )
        )


def load(t):
    with t["data"][0].tx() as c:
        return source.load_offline(
            t["data"][0],
            c,
            t["data"][3],
            t["contract"],
            t["approval"].request_key,
            t["identity"].account_id,
        )


def dispatch(t):
    return sender.dispatch_from_source_offline(
        t["worker"],
        t["contract"],
        t["approval"].request_key,
        t["identity"],
        t["wire"],
        expected_revision=0,
    )


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


@pytest.fixture
def trial(env, tmp_path):
    t = prepare(env)
    other = t["data"][2].post("/api/projects", json=dict(name="Other synthetic source scope"))
    assert other.status_code == 201
    with t["data"][0].tx() as c:
        project = t["data"][0].own_project(c, t["data"][3], other.json()["id"])
    t["other_project"] = dict(project)
    t["raw_bundle"] = bundle_for(t)
    t["raw_source"] = seed(t, t["raw_bundle"])
    before = snapshot(t["data"][0])
    yield t
    after = snapshot(t["data"][0])
    for table in before:
        if table == rows.name:

            def unrelated(values):
                return [
                    v
                    for v in values
                    if not v["kind"].startswith((journal.KIND, sender.CAPTURE, source.KIND))
                ]

            assert unrelated(before[table]) == unrelated(after[table])
        else:
            assert before[table] == after[table], table
    with t["data"][0].tx() as c:
        mirrors = [
            dict(r)
            for r in c.execute(
                select(rows.c.kind, rows.c.fingerprint).where(
                    rows.c.kind.in_(
                        [
                            source.KIND,
                            source.KIND + "_seal",
                            journal.KIND,
                            journal.KIND + "_seal",
                            journal.QUOTA,
                            journal.QUOTA + "_seal",
                            sender.CAPTURE,
                            sender.CAPTURE + "_seal",
                        ]
                    )
                )
            ).mappings()
        ]
    write_json(
        tmp_path / "source-state.json",
        dict(
            scope="UNINSTALLED_SYNTHETIC_ONLY",
            mirrors=mirrors,
            protected_other_54_tables_strict_equal=True,
            mock_handler_calls=len(t["state"]["sent"]),
            real_provider_calls=0,
            source_rows_are_fixtures_not_provenance=True,
        ),
    )
    t["data"][2].close()


def test_owned_raw_source_contract_flows_through_original_sender_and_history(
    trial, monkeypatch, tmp_path
):
    t = trial
    resolved = load(t)
    (tmp_path / "raw-synthetic-source.json").write_bytes(t["raw_source"])
    assert resolved.source.decision == "ALLOW"
    assert resolved.source.observed_at < time.time() - 590
    assert resolved.raw_sha256 == hashlib.sha256(t["raw_source"]).hexdigest()
    assert resolved.source.evidence_fingerprint == resolved.raw_sha256
    assert resolved.raw_bytes == len(t["raw_source"])
    assert (
        resolved.real_source_verified
        is resolved.live_allowed
        is resolved.dispatch_authorized
        is False
    )
    public = resolved.model_dump(mode="json")
    assert "raw_b64" not in json.dumps(public) and "identity_confirmed" not in json.dumps(public)
    trace, last = [], {}
    original_load, original_apply = source.load_offline, journal._apply_in_transaction

    def observed_load(store, c, *args):
        assert c.in_transaction() and c.engine is store.engine
        result = original_load(store, c, *args)
        last[c] = result.source
        trace.append(dict(step="source_load", connection=id(c), decision=result.source.decision))
        return result

    def observed_apply(*args, **kwargs):
        assert args[1].in_transaction() and last[args[1]] == args[7]
        trace.append(dict(step=args[9], connection=id(args[1])))
        return original_apply(*args, **kwargs)

    monkeypatch.setattr(source, "load_offline", observed_load)
    monkeypatch.setattr(journal, "_apply_in_transaction", observed_apply)
    result = dispatch(t)
    assert len(t["state"]["sent"]) == 1 and result.journal.ledger.slots[0].accepted
    assert result.journal.ledger.slots[0].settlement.total_tokens == 8
    assert len(last) == 4
    assert [v["step"] for v in trace] == [
        "source_load",
        "reserve",
        "source_load",
        "record_attempt",
        "source_load",
        "source_load",
        "settle",
    ]
    assert result.business_accepted is result.live_allowed is result.real_source_verified is False
    variants = []
    for part, field, value, decision in (
        ("identity", "identity_confirmed", None, "UNKNOWN"),
        ("entitlement", "legal_free_entitlement", None, "UNKNOWN"),
        ("enforcement", "enforced_zero_charge", None, "UNKNOWN"),
        ("enforcement", "billable_fallback_disabled", False, "DENY"),
        ("status", "revoked", None, "UNKNOWN"),
        ("identity", "issuer", "fabricated-real-provider", "UNKNOWN"),
    ):
        changed = copy.deepcopy(t["raw_bundle"])
        changed[part][field] = value
        seed(t, changed)
        check = load(t)
        assert check.source.decision == decision
        if part == "enforcement" and value is None:
            assert check.source.enforced_non_chargeable is None
        variants.append(
            dict(part=part, field=field, decision=check.source.decision, reason=check.reason)
        )
    forged = dict(t["raw_bundle"], decision="ALLOW")
    seed(t, forged)
    assert load(t).source.decision == "UNKNOWN"
    seed(t, t["raw_bundle"], provenance="PRODUCTION_VERIFIED")
    assert load(t).source.decision == "UNKNOWN"
    remove_source(t)
    baseline = snapshot(t["data"][0])

    def no_source_lookup(*args, **kwargs):
        raise AssertionError("Original history must not read unavailable source")

    monkeypatch.setattr(source, "load_offline", no_source_lookup)
    duplicate = dispatch(t)
    assert duplicate.journal.duplicate and not duplicate.adapter_entered
    assert snapshot(t["data"][0]) == baseline and len(t["state"]["sent"]) == 1
    write_json(
        tmp_path / "source-to-sender.json",
        dict(
            resolution=public,
            trace=trace[:7],
            receipt=result.model_dump(mode="json"),
            duplicate=duplicate.model_dump(mode="json"),
            complete_history_55_tables_strict_equal=True,
            source_reads_for_send=4,
            raw_sha256=resolved.raw_sha256,
            raw_bytes=resolved.raw_bytes,
            bounded_contract_variants=variants,
            fabricated_allow_and_production_label_rejected=True,
            source_missing_duplicate_lookup_calls=0,
        ),
    )


@pytest.mark.parametrize(
    "case", ["missing", "wrong_account", "cross_project", "expired", "revoked", "inconsistent"]
)
def test_unusable_server_source_never_commits_budget_or_sends(trial, case, tmp_path):
    t = trial
    changed = copy.deepcopy(t["raw_bundle"])
    if case == "missing":
        remove_source(t)
    elif case == "wrong_account":
        for part in ("identity", "entitlement", "enforcement", "status"):
            changed[part]["account_id"] = "another-synthetic-account"
        seed(t, changed)
    elif case == "cross_project":
        other = t["other_project"]
        foreign_scope = scope_for(t).model_copy(
            update=dict(project_id=other["id"], runtime_id=other["runtime_id"])
        )
        changed = bundle_for(t, foreign_scope)
        payload_reads = []

        def sql_observer(conn, cursor, statement, parameters, context, many):
            if "delivery_graph_requests.snapshot" in statement and source.KIND in parameters:
                payload_reads.append(statement)

        event.listen(t["data"][0].engine, "before_cursor_execute", sql_observer)
        try:
            assert load(t).source.decision == "ALLOW" and payload_reads
            calibrated_payload_reads = len(payload_reads)
            seed(t, changed, scope=foreign_scope)
            remove_source(t)
            payload_reads.clear()
            assert load(t).reason == "SOURCE_MISSING" and payload_reads == []
        finally:
            event.remove(t["data"][0].engine, "before_cursor_execute", sql_observer)
        # Copying a different project's raw proof into the owned pair is still denied.
        seed(t, changed)
    elif case == "expired":
        for part in ("identity", "entitlement", "enforcement", "status"):
            changed[part]["expires_at"] = time.time() - 1
        seed(t, changed)
    elif case == "revoked":
        changed["status"]["revoked"] = True
        seed(t, changed)
    else:
        changed["enforcement"]["requirements_fingerprint"] = "b" * 64
        seed(t, changed)
    before = snapshot(t["data"][0])
    resolution = load(t)
    if case != "missing":
        (tmp_path / "raw-synthetic-source.json").write_bytes(json.dumps(changed, indent=1).encode())
    assert resolution.source.decision in ("DENY", "UNKNOWN")
    with pytest.raises(DomainError) as error:
        dispatch(t)
    assert error.value.code == "LIVE_BLOCKED"
    assert snapshot(t["data"][0]) == before and t["state"]["sent"] == []
    mirror_case = None
    if case == "inconsistent":
        # Even two freshly recomputed mirrors cannot make conflicting roles true.
        with t["data"][0].tx() as c:
            assert journal._pair(
                c, t["data"][3], t["contract"].project_id, source.KIND, t["contract"].trial_key
            )
        valid_raw = seed(t, t["raw_bundle"])
        (tmp_path / "raw-valid-before-mirror-corruption.json").write_bytes(valid_raw)
        with t["data"][0].tx() as c:
            broken = c.execute(
                update(rows)
                .where(
                    rows.c.principal_id == t["data"][3],
                    rows.c.app_id == t["contract"].project_id,
                    rows.c.kind == source.KIND,
                    rows.c.request_key == t["contract"].trial_key,
                )
                .values(fingerprint="d" * 64)
            )
            assert broken.rowcount == 1
        corrupted = snapshot(t["data"][0])
        unknown = load(t)
        assert unknown.reason == "SOURCE_INTEGRITY" and unknown.source.decision == "UNKNOWN"
        with pytest.raises(DomainError) as mirror_error:
            dispatch(t)
        assert mirror_error.value.code == "LIVE_BLOCKED"
        assert snapshot(t["data"][0]) == corrupted and not t["state"]["sent"]
        mirror_case = dict(
            resolution=unknown.model_dump(mode="json"),
            error=mirror_error.value.public(),
            one_pair_fingerprint="d" * 64,
            request_fingerprint_anchors_unchanged=True,
            all_55_tables_strict_equal=True,
            handler_calls=0,
            no_auto_repair=True,
        )
    write_json(
        tmp_path / "source-rejection.json",
        dict(
            case=case,
            resolution=resolution.model_dump(mode="json"),
            error=error.value.public(),
            all_55_tables_strict_equal=True,
            handler_calls=0,
            sql_observer_positive_payload_reads=calibrated_payload_reads
            if case == "cross_project"
            else None,
            foreign_source_payload_reads=0 if case == "cross_project" else None,
            one_corrupt_mirror=mirror_case,
        ),
    )


def test_source_revoked_after_guard_preserves_received_facts_and_stops_acceptance(trial, tmp_path):
    t = trial
    trace = []

    def handler(request):
        assert len(t["state"]["sent"]) == 1
        trace.append("mock_handler_after_guard")
        changed = copy.deepcopy(t["raw_bundle"])
        changed["status"]["revoked"] = True
        seed(t, changed)
        trace.append("server_status_revoked_committed")
        return httpx.Response(200, content=t["state"]["reply"])

    t["state"]["hook"] = handler
    result = dispatch(t)
    slot = result.journal.ledger.slots[0]
    assert slot.attempted and slot.settlement.total_tokens == 8
    assert (
        slot.settlement.outcome == "RECEIVED" and not slot.accepted and result.journal.ledger.halted
    )
    assert result.capture_bytes == len(t["state"]["reply"])
    assert load(t).source.decision == "DENY"
    before = snapshot(t["data"][0])
    duplicate = dispatch(t)
    assert snapshot(t["data"][0]) == before and duplicate.journal.duplicate
    assert len(t["state"]["sent"]) == 1 and not duplicate.adapter_entered
    write_json(
        tmp_path / "source-late-revocation.json",
        dict(
            trace=trace,
            receipt=result.model_dump(mode="json"),
            duplicate=duplicate.model_dump(mode="json"),
            same_original_key_handler_calls=1,
            recovery_55_tables_strict_equal=True,
            zero_refund_or_resend=True,
        ),
    )


def test_new_entry_stays_offline_and_default_production_resolver_still_denies(
    trial, monkeypatch, tmp_path
):
    t = trial
    worker, store = t["worker"], t["data"][0]
    before = snapshot(store)
    settings, transport = worker.s, worker.goal_planner_transport
    store.test_only = False
    try:
        with pytest.raises(DomainError):
            dispatch(t)
        with store.tx() as c, pytest.raises(DomainError):
            source.load_offline(
                store,
                c,
                t["data"][3],
                t["contract"],
                t["approval"].request_key,
                t["identity"].account_id,
            )
    finally:
        store.test_only = True
    for changed in (
        replace(settings, live_enabled=True),
        replace(settings, token="synthetic-disallowed-token"),
    ):
        worker.s = changed
        try:
            with pytest.raises(DomainError):
                dispatch(t)
        finally:
            worker.s = settings
    worker.goal_planner_transport = object()
    try:
        with pytest.raises(DomainError):
            dispatch(t)
    finally:
        worker.goal_planner_transport = transport
    with pytest.raises(DomainError) as default:
        admission.production_preflight(
            store, t["data"][3], t["contract"], t["approval"].request_key, None
        )
    assert default.value.code == "LIVE_BLOCKED"
    original_pair = journal._pair

    def actual_permission_failure(*args, **kwargs):
        raise DomainError(
            "PERMISSION_DENIED", "Synthetic observer: real permission class must propagate"
        )

    monkeypatch.setattr(journal, "_pair", actual_permission_failure)
    try:
        with pytest.raises(DomainError) as owner_error:
            load(t)
        assert owner_error.value.code == "PERMISSION_DENIED"
    finally:
        monkeypatch.setattr(journal, "_pair", original_pair)
    assert snapshot(store) == before and not t["state"]["sent"]
    # Small compatibility check for the extracted original data-only entry,
    # not a rerun of the old eight-node sender window matrix.
    result = sender.dispatch_offline(
        worker,
        t["contract"],
        t["approval"].request_key,
        t["identity"],
        t["wire"],
        t["source"],
        expected_revision=0,
    )
    assert result.journal.ledger.slots[0].accepted and len(t["state"]["sent"]) == 1
    write_json(
        tmp_path / "source-boundary.json",
        dict(
            default_error=default.value.public(),
            new_entry_refusals_55_tables_strict_equal=True,
            refusals_handler_calls=0,
            source_permission_error_propagated=owner_error.value.public(),
            original_data_entry_compatibility=result.model_dump(mode="json"),
            original_data_entry_mock_handler_calls=1,
            real_provider_calls=0,
        ),
    )
