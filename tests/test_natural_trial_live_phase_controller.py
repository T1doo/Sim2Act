"""Controlled protocol/gate tests only: no PG or real model calls/credentials."""

import importlib.util
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from test_natural_trial_preparation import prepared_data  # noqa: F401

ROOT = Path(__file__).parents[1]
sp = importlib.util.spec_from_file_location(
    "live_phase_unit", ROOT / "scripts/diagnostics/natural_trial_live_phase.py"
)
live = importlib.util.module_from_spec(sp)
sp.loader.exec_module(live)
cp = importlib.util.spec_from_file_location(
    "pg_controller_unit", ROOT / "scripts/diagnostics/isolated_pg_probe.py"
)
controller = importlib.util.module_from_spec(cp)
cp.loader.exec_module(controller)


def test_new_client_checkpoint_prevents_post_before_transport():
    def stopped():
        raise ValueError("STOP")

    with live.new_client(
        "http://127.0.0.1:9", "unit-not-a-credential", checkpoint=stopped
    ) as client:
        with pytest.raises(ValueError, match="STOP"):
            client.post("/must-not-connect", json={})


def test_seven_slots_do_not_fit_original_five_minute_window(monkeypatch):
    monkeypatch.setattr(live.time, "time", lambda: 1000.0)
    contract = SimpleNamespace(expires_at=1300.0)
    with pytest.raises(ValueError, match="CANNOT_FIT"):
        live.enough_window(contract, dict(last_reserved_at=1000.0), 7)
    assert contract.expires_at == 1300.0
    live.enough_window(SimpleNamespace(expires_at=2200.0), dict(last_reserved_at=1000.0), 7)


def test_bounded_bridge_retains_actual_owned_thread_without_kill(monkeypatch):
    entered = threading.Event()
    release = threading.Event()

    def held(*a, **kw):
        entered.set()
        release.wait(2)
        kw["guard"]()  # Deadline/abort still prevents a late commit.

    monkeypatch.setattr(live, "strict_extract", held)
    monkeypatch.setattr(live, "INFLIGHT_BRIDGES", [])
    try:
        with pytest.raises(live.PhaseError, match="INFLIGHT_UNKNOWN"):
            live.bounded_extract(
                None,
                "unit",
                dict(trial="unit-scope"),
                "run_unit",
                None,
                stop=threading.Event(),
                absolute_deadline=time.monotonic() + 1,
                observe_seconds=0.03,
            )
        assert entered.is_set()
        thread, identity = live.INFLIGHT_BRIDGES[0]
        assert thread.is_alive() and identity["kind"] == "OWNED_EXTRACTION_THREAD_UNKNOWN"
    finally:
        release.set()
        for thread, _ in live.INFLIGHT_BRIDGES:
            thread.join(2)
    assert all(not thread.is_alive() for thread, _ in live.INFLIGHT_BRIDGES)


def test_terminal_result_is_preserved_on_cancel_race():
    calls = []

    class Client:
        def post(self, path, json):
            calls.append(path)
            return httpx.Response(200, json=dict(status="REVOKED"))

        def get(self, path):
            if path == "/original-key":
                return httpx.Response(200, json=dict(run_id="run_known", request_key="original"))
            return httpx.Response(200, json=dict(status="SUCCEEDED", result={"saved": True}))

    result = live.cancel_original(
        Client(),
        dict(
            base="/scope",
            review_token="f" * 64,
            active_run="run_known",
            validated_target=dict(
                stage="source", path="/original-key", expected=dict(request_key="original")
            ),
        ),
    )
    assert result["run_status"] == "SUCCEEDED" and result["result_present"] is True
    assert calls == ["/scope/withdrawal"]


def test_unknown_run_identity_is_not_guessed_or_replayed():
    calls = []

    class Client:
        def post(self, path, json):
            calls.append(path)
            return httpx.Response(409, json={})

        def get(self, path):
            pytest.fail("cannot infer a Run for an unknown POST")

    result = live.cancel_original(
        Client(),
        dict(base="/scope", review_token="f" * 64, pending_request_key="original", active_run=None),
    )
    assert result["status"] == "CANCELLATION_UNKNOWN" and result["trial_withdrawn"] is False
    assert calls == ["/scope/withdrawal"]


def test_nested_public_output_does_not_expose_known_secret_or_change_business_object():
    original = {
        "live_result": {"result": "unit-private-value echoed"},
        "unit-private-value": "key",
        "count": 2,
    }
    result = controller.redact_strings(original, ["unit-private-value"])
    assert "unit-private-value" not in str(result) and result["count"] == 2
    assert original["live_result"]["result"] == "unit-private-value echoed"


@pytest.mark.parametrize("bad_source_receipt", [False, True])
def test_protocol_stub_runs_all_stages_and_never_calls_generic_extraction(
    prepared_data,  # noqa: F811
    bad_source_receipt,
):
    # Structured wire replay only. No production account source, provider IO or PG.
    from test_natural_spec_apps import recipe

    from sim2act import natural_live_admission as gate
    from sim2act import production_evidence as evidence
    from sim2act import production_trial_journal as journal
    from sim2act import production_trial_policy as policy
    from sim2act.db import fingerprint

    data, choices = prepared_data
    made = data[2].post(
        f"/api/projects/{data[4]}/natural-trials/protocol-stub/preparation",
        json=dict(
            choices,
            path="P-B",
            extraction_recipe=recipe("single"),
            scope_window="NEW_EXACT_SEVEN_SLOT_1200_SECONDS",
        ),
    )
    assert made.status_code == 200, made.text
    contract = gate.PBTrialContract.model_validate(made.json()["contract"]).model_copy(
        update={"quota_subject": live.canonical_quota_subject(live.ACCOUNT_ID)}
    )
    selection = dict(
        user=contract.principal_id,
        project=contract.project_id,
        trial=contract.trial_key,
        approval=contract.stage_keys.generate + "_approval",
        account=live.ACCOUNT_ID,
    )
    scope = evidence.requirements_for(contract.principal_id, contract, selection["approval"])
    ids = {stage: "run_" + str(i) * 32 for i, stage in enumerate(["generate", "source", "cold"], 1)}
    apps = ["app_" + "4" * 32, "app_" + "5" * 32]
    releases = ["irelease_" + "6" * 32, "irelease_" + "7" * 32]
    instances = ["iinstance_" + "8" * 32, "iinstance_" + "9" * 32]
    shapes = {
        apps[0]: recipe("ordered"),
        apps[1]: contract.extraction_recipe.model_dump(exclude_none=True),
    }
    calls = []
    slots = []
    bridges = []
    approved_stages = set()
    dispatched = set()
    original_requests = {}

    class Wire:
        def __init__(self):
            self.event_hooks = {"request": []}

        def reply(self, path, body=None):
            for hook in self.event_hooks["request"]:
                hook(None)
            calls.append((path, body))
            status = 200
            if path.endswith("/application-runs"):
                stage = "generate"
            elif path.endswith("/pb-use-runs"):
                stage = "cold"
            elif path.endswith("/runs") and body is not None:
                stage = "source"
            else:
                stage = None
            if stage:
                original_requests[stage] = body
                return httpx.Response(
                    202,
                    json=dict(
                        run_id="run_unrelated"
                        if bad_source_receipt and stage == "source"
                        else ids[stage]
                    ),
                )
            if "/application-runs?request_key=" in path:
                return httpx.Response(
                    200,
                    json=dict(
                        id=ids["generate"],
                        contract=dict(
                            snapshot=dict(
                                source_goal_card=dict(
                                    card_id=contract.bindings[0].card_id,
                                    version=contract.bindings[0].goal_version,
                                    fingerprint=contract.bindings[0].goal_fingerprint,
                                )
                            )
                        ),
                    ),
                )
            if "/spec-run-requests/" in path or "/pb-use-requests/" in path:
                stage = "source" if "/spec-run-requests/" in path else "cold"
                i = 0 if stage == "source" else 1
                return httpx.Response(
                    200,
                    json=dict(
                        run_id=ids[stage],
                        namespace="spec-run-request.v1" if stage == "source" else live.use.VERSION,
                        request_key=getattr(contract.stage_keys, stage),
                        request=original_requests[stage],
                        principal_id=contract.principal_id,
                        project_id=contract.project_id,
                        app_id=apps[i],
                        release_id=releases[i],
                        instance_id=instances[i],
                    ),
                )
            if path.startswith("/api/runs/") and body is None:
                rid = path.rsplit("/", 1)[1]
                stage = next(k for k, value in ids.items() if value == rid)
                if stage != "generate":
                    assert stage in approved_stages, (
                        "Polling execution before original stage binding"
                    )
                if stage not in dispatched:
                    dispatched.add(stage)
                    count = {"generate": 3, "source": 2, "cold": 1}[stage]
                    for _ in range(count):
                        n = len(slots) + 1
                        identity = policy.ReservationIdentity(
                            requirements_fingerprint=fingerprint(scope.model_dump()),
                            approval_fingerprint="a" * 64,
                            stage=stage,
                            stage_fingerprint=None if stage == "generate" else "b" * 64,
                            run_id=ids[stage],
                            runtime_id=contract.runtime_id,
                            version=1,
                            fence=1,
                            worker_id="unit-worker",
                            account_id=live.ACCOUNT_ID,
                            quota_subject=contract.quota_subject,
                            attempt_id="attempt_" + format(n, "032x"),
                            wire_sha256="c" * 64,
                            wire_bytes=100,
                        )
                        slots.append(
                            policy.Slot(
                                identity=identity,
                                reserved_at=time.time() - 600 + n * 60,
                                attempted=True,
                                accepted=True,
                                settlement=policy.Outcome(
                                    outcome="RECEIVED",
                                    response_sha256="d" * 64,
                                    response_ascii_bytes=10,
                                    prompt_tokens=1,
                                    completion_tokens=1,
                                    total_tokens=2,
                                ),
                            )
                        )
                return httpx.Response(
                    200,
                    json=dict(
                        version=1,
                        status="PARTIAL" if rid == ids["generate"] else "SUCCEEDED",
                        result=dict(candidate_fingerprint="e" * 64),
                    ),
                )
            if path.endswith("/production-journal"):
                value = journal.Receipt(
                    ledger=policy.Ledger(
                        scope=scope, account_id=live.ACCOUNT_ID, slots=tuple(slots)
                    ),
                    quota=policy.AccountQuotaCursor(
                        account_id=live.ACCOUNT_ID,
                        quota_subject=contract.quota_subject,
                        last_reserved_at=slots[-1].reserved_at,
                    ),
                    revision=1,
                    quota_revision=1,
                )
                result = value.model_dump(mode="json")
            elif path.endswith("/confirm-application-candidate"):
                result = dict(id=apps[0])
            elif path.startswith("/api/apps/"):
                aid = path.rsplit("/", 1)[1]
                result = dict(
                    id=aid,
                    fingerprint=fingerprint(shapes[aid]),
                    candidate=dict(spec_recipe=shapes[aid]),
                )
            elif path.endswith("/release-approvals"):
                i = 0 if apps[0] in path else 1
                result = dict(id="approval_" + str(i), fingerprint="f" * 64)
                status = 201
            elif path.endswith("/commit"):
                i = 0 if "approval_0" in path else 1
                result = dict(id=releases[i], fingerprint="1" * 64)
            elif path.endswith("/instances"):
                i = 0 if releases[0] in path else 1
                result = dict(id=instances[i], revision=1)
                status = 201
            elif path.endswith("/stage-review"):
                stage = body["stage"]
                i = 0 if stage == "source" else 1
                authority = gate.StageAuthority(
                    contract_fingerprint=fingerprint(contract.model_dump()),
                    stage=stage,
                    run_id=ids[stage],
                    accepted_fingerprint="1" * 64,
                    app_run_id="unit-app-run",
                    instance_id=instances[i],
                    instance_revision=1,
                    runtime_id=contract.runtime_id,
                    app_id=apps[i],
                    candidate_fingerprint=fingerprint(shapes[apps[i]]),
                    recipe_fingerprint=fingerprint(shapes[apps[i]]),
                    release_id=releases[i],
                    release_fingerprint="1" * 64,
                    generation_run_id=ids["generate"],
                    generation_candidate_fingerprint="e" * 64,
                    target_goal_fingerprint=contract.bindings[i].goal_fingerprint,
                    authorization_fingerprint=contract.authorization_fingerprint,
                )
                result = dict(
                    authority=authority.model_dump(),
                    authority_fingerprint=fingerprint(authority.model_dump()),
                )
            elif path.endswith("/stage-approval"):
                approved_stages.add(body["approval"]["authority"]["stage"])
                result = dict(
                    authority=body["approval"]["authority"],
                    authority_fingerprint=body["approval"]["expected_authority_fingerprint"],
                )
            elif path.endswith("/extraction-options"):
                proof = dict(source_run_id=ids["source"])
                result = dict(
                    source_run_id=ids["source"],
                    source_proof=proof,
                    source_proof_fingerprint=fingerprint(proof),
                    recipe_fingerprint="2" * 64,
                )
            elif path.endswith("/extraction-reviews") or path.endswith("/pb-use-reviews"):
                result = dict(review_fingerprint="3" * 64)
            elif "/api/internal/instances/" in path and "/runs/" not in path:
                result = dict(id=instances[1], revision=1)
            elif "/runs/" in path:
                result = dict(status="SUCCEEDED", result={"synthetic_protocol_only": True})
            elif path.endswith("/withdrawal"):
                result = dict(status="REVOKED")
            else:
                raise AssertionError("Unexpected protocol route " + path)
            return httpx.Response(status, json=result)

        def get(self, path):
            return self.reply(path)

        def post(self, path, json):
            return self.reply(path, json)

    def bridge(chosen, rid, body):
        assert (
            chosen == selection
            and rid == ids["source"]
            and body.review.recipe == contract.extraction_recipe
        )
        bridges.append(body)
        return dict(id=apps[1], request=body.model_dump(), new_model_requests=0)

    state = dict(
        base=f"/api/projects/{contract.project_id}/natural-trials/{contract.trial_key}",
        trial=contract.trial_key,
        review_token=fingerprint(contract.model_dump()),
    )
    try:
        result = live.run_stages(Wire(), contract, selection, state, bridge, cleanup_client=Wire())
    except live.PhaseError as error:
        if bad_source_receipt:
            assert error.code == "ORIGINAL_RUN_SCOPE_CHANGED"
            assert error.state["active_run"] is None and error.state["validated_target"] is None
            assert error.state["model_requests"] is None
            assert error.state["cancellation"]["trial_withdrawn"] is True
            assert dispatched == {"generate"} and not bridges
            assert not any(p.endswith("/commands") for p, _ in calls)
            return
        pytest.fail("Controlled protocol fixture failure: " + str(error.__context__))
    assert not bad_source_receipt
    assert result["status"] == "ORIGINAL_MODEL_CHAIN_TECHNICALLY_SAVED"
    assert (
        len(bridges) == 1 and result["actual_model_requests"] == 6
    )  # Stub records, NOT real calls.
    assert not any(p.endswith("/extractions") or p.endswith("/budget") for p, _ in calls)
    assert [p.rsplit("/", 1)[-1] for p, b in calls if p.endswith("/stage-review")] == [
        "stage-review",
        "stage-review",
    ]


def test_real_sql_commit_guard_rolls_back_before_dbapi_commit():
    from sqlalchemy import create_engine, text

    engine = create_engine("sqlite://")
    stop = threading.Event()
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE guarded_value (value INTEGER)"))

    def guard():
        if stop.is_set():
            raise ValueError("OWNED_STOP_BEFORE_COMMIT")

    live.install_sql_guard(engine, guard)
    with pytest.raises(ValueError, match="OWNED_STOP_BEFORE_COMMIT"):
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO guarded_value VALUES (1)"))
            stop.set()
    stop.clear()
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM guarded_value")) == 0
    engine.dispose()


def test_mismatched_original_key_never_cancels_other_run():
    commands = []

    class Client:
        def post(self, path, json):
            commands.append(path)
            return httpx.Response(200, json=dict(status="REVOKED"))

        def get(self, path):
            assert path == "/original-key"
            return httpx.Response(200, json=dict(run_id="run_other", request_key="original"))

    state = dict(
        base="/scope",
        review_token="f" * 64,
        active_run="run_old",
        validated_target=dict(
            stage="source", path="/original-key", expected=dict(request_key="original")
        ),
    )
    result = live.cancel_original(Client(), state)
    assert result["status"] == "CANCELLATION_UNKNOWN" and result["trial_withdrawn"] is True
    assert commands == ["/scope/withdrawal"]


def test_unvalidated_accepted_id_can_only_withdraw_original_trial():
    class Client:
        def post(self, path, json):
            assert path == "/scope/withdrawal"
            return httpx.Response(200, json=dict(status="REVOKED"))

        def get(self, path):
            pytest.fail("an unvalidated accepted id is not a cancellation target")

    result = live.cancel_original(
        Client(), dict(base="/scope", review_token="f" * 64, active_run="run_unvalidated")
    )
    assert result["status"] == "CANCELLATION_UNKNOWN" and result["trial_withdrawn"] is True
