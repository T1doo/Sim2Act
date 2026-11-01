"""Bounded original P-B trial orchestration; no direct model HTTP or test authority.

Only called by an explicitly confirmed isolated-PG scope. Imports and unit tests
never execute it. A five-minute V1 contract is never extended to consume 7 slots.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import replace
from pathlib import Path

import httpx

from sim2act import natural_live_admission as gate
from sim2act import natural_specs as natural
from sim2act import pb_natural_specs as pb
from sim2act import pb_natural_uses as use
from sim2act import production_evidence as evidence
from sim2act import production_trial_journal as journal
from sim2act.db import fingerprint
from sim2act.production_evidence import ACCOUNT_ID
from sim2act.production_trial_admission import canonical_quota_subject

MAX_SECONDS = 1080
# This probe narrows the original3/2/2 caps; it does not modify the contract.
STAGE_LIMITS = {"generate": 3, "source": 2, "cold": 1}
TERMINAL = {"SUCCEEDED", "FAILED", "CANCELLED", "PARTIAL"}


class PhaseError(RuntimeError):
    def __init__(self, code, state):
        super().__init__(code)
        self.code = code
        self.state = state


def require(value, code):
    if not value:
        raise ValueError(code)


def request(client, path, body=None, status=200):
    # No automatic mutation retry or provider fallback. Never expose headers,
    # raw server errors, URLs containing credentials or the bearer in diagnostics.
    reply = client.get(path) if body is None else client.post(path, json=body)
    require(reply.status_code == status, "ORIGINAL_HTTP_" + str(reply.status_code))
    return reply.json()


def new_client(url, bearer, checkpoint=None):
    require(url.startswith("http://127.0.0.1:"), "LOOPBACK_ORIGIN_REQUIRED")
    return httpx.Client(
        base_url=url,
        headers={"Authorization": "Bearer " + bearer},
        trust_env=False,
        timeout=5,
        event_hooks={"request": [lambda _: checkpoint()]} if checkpoint else {},
    )


def save_selection(root, value):
    path = Path(root) / "live-selection.json"
    require(
        set(value) == {"user", "project", "trial", "approval", "account"}
        and value["account"] == ACCOUNT_ID,
        "ORIGINAL_SELECTION_REQUIRED",
    )
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as out:
        out.write(json.dumps(value, indent=2) + "\n")
    return path


def prepare(client, recipe, record):
    project = request(
        client, "/api/projects", dict(name="Bounded existing-free Intern synthetic trial"), 201
    )["id"]
    choices = []
    for content in ["The river is blue.", "The tree is green."]:
        material = request(
            client,
            f"/api/projects/{project}/resources",
            dict(name="synthetic-notes.txt", format="txt", content=content),
            201,
        )
        card = request(
            client,
            f"/api/projects/{project}/goal-cards",
            dict(
                title="Synthetic cited notes",
                goal="Extract a finite cited checklist of requirements, conditions, exceptions and undecided choices. Use exactly two model nodes: requirements, then conditions/exceptions/open questions, followed by merge, citation check and save; preserve full source and uncertainty.",
                known=[],
                assumptions=[],
                constraints=["Preserve exact source quotes; do not invent requirements"],
                acceptance_checks=["Human review remains required"],
                unresolved=[],
                resource_refs=[material["id"]],
            ),
            201,
        )
        card = request(client, "/api/goal-cards/" + card["id"])
        choices.append(dict(card_id=card["id"], expected_version=card["version"]))
    key = "bounded-" + uuid.uuid4().hex
    base = f"/api/projects/{project}/natural-trials/{key}"
    state = dict(stage="prepare", trial=key, project=project, base=base, model_requests=0)
    record(state)
    body = dict(bindings=choices, path="P-B", extraction_recipe=recipe)
    receipt = request(client, base + "/preparation", body)
    contract = gate.PBTrialContract.model_validate(receipt["contract"])
    require(
        contract.project_id == project
        and contract.trial_key == key
        and contract.caps == gate.TrialCaps()
        and receipt["path"] == "P-B"
        and receipt["review_token"] == fingerprint(contract.model_dump())
        and receipt["approved"] is False
        and receipt["revoked"] is False
        and receipt["expired"] is False
        and contract.quota_subject == canonical_quota_subject(ACCOUNT_ID)
        and contract.extraction_recipe.model_dump(exclude_none=True) == recipe,
        "ORIGINAL_PREPARATION_MISMATCH",
    )
    state.update(review_token=receipt["review_token"], expires_at=contract.expires_at)
    record(state)  # Preserve original key before consent's potentially unknown effect.
    request(
        client,
        base + "/consent",
        dict(review_token=receipt["review_token"], confirm_exact_scope=True),
    )
    approved = request(client, base + "/preparation")
    require(
        approved["approved"] is True
        and approved["revoked"] is False
        and approved["contract"] == receipt["contract"],
        "ORIGINAL_CONSENT_MISMATCH",
    )
    selection = approved["worker_selection"]
    require(
        selection
        == dict(
            user=contract.principal_id,
            project=project,
            trial=key,
            approval=contract.stage_keys.generate + "_approval",
            account=ACCOUNT_ID,
        ),
        "ORIGINAL_ACCOUNT_SELECTION_MISMATCH",
    )
    state.update(approval=selection["approval"], stage="approved")
    record(state)
    return contract, selection, state


def ledger(client, contract, selection, *, runs=None):
    base = f"/api/projects/{contract.project_id}/natural-trials/{contract.trial_key}"
    raw = request(client, base + "/approvals/" + selection["approval"] + "/production-journal")
    receipt = journal.Receipt.model_validate_json(json.dumps(raw))
    state = receipt.ledger
    slots = state.slots
    expected = evidence.requirements_for(contract.principal_id, contract, selection["approval"])
    require(
        state.scope == expected
        and state.account_id == ACCOUNT_ID
        and receipt.quota.account_id == ACCOUNT_ID
        and receipt.quota.quota_subject == contract.quota_subject,
        "JOURNAL_SCOPE_CHANGED",
    )
    require(
        not state.halted
        and len(slots) <= 7
        and all(
            s.accepted
            and s.attempted
            and s.settlement is not None
            and s.settlement.outcome == "RECEIVED"
            and all(
                type(getattr(s.settlement, k)) is int and getattr(s.settlement, k) >= 0
                for k in ("prompt_tokens", "completion_tokens", "total_tokens")
            )
            and s.settlement.total_tokens
            == s.settlement.prompt_tokens + s.settlement.completion_tokens
            and s.settlement.completion_tokens <= 1024
            for s in slots
        ),
        "JOURNAL_UNKNOWN_OR_UNACCEPTED",
    )
    require(
        sum(s.settlement.completion_tokens for s in slots) <= 7168
        and sum(s.identity.wire_bytes + 1024 for s in slots) <= 192000,
        "TOTAL_MODEL_BUDGET",
    )
    for stage, maximum in STAGE_LIMITS.items():
        own = [s for s in slots if s.identity.stage == stage]
        require(
            len(own) <= maximum and sum(s.identity.wire_bytes + 1024 for s in own) <= 64000,
            "STAGE_MODEL_BUDGET",
        )
        if runs and own:
            require(all(s.identity.run_id == runs.get(stage) for s in own), "JOURNAL_RUN_CHANGED")
        require(
            all(
                s.identity.requirements_fingerprint == fingerprint(expected.model_dump())
                and s.identity.account_id == ACCOUNT_ID
                and s.identity.quota_subject == contract.quota_subject
                for s in own
            ),
            "JOURNAL_IDENTITY_CHANGED",
        )
    return dict(
        reserved_requests=len(slots),
        status="ACCOUNTED",
        last_reserved_at=receipt.quota.last_reserved_at,
        journal=receipt.model_dump(mode="json"),
    )


def enough_window(contract, budget, minimum_requests):
    # A causal lower bound only; never a completion guarantee or extra deadline.
    require(time.time() < contract.expires_at, "ORIGINAL_TRIAL_EXPIRED")
    last = budget.get("last_reserved_at")
    first = max(time.time(), last + 60) if last is not None else time.time()
    require(
        first + (minimum_requests - 1) * 60 < contract.expires_at,
        "ORIGINAL_WINDOW_CANNOT_FIT_NEXT_STAGE",
    )


def release_instance(client, app_id, key):
    app = request(client, "/api/apps/" + app_id)
    approval = request(
        client,
        f"/api/internal/apps/{app_id}/release-approvals",
        dict(expected_draft_fingerprint=app["fingerprint"], sample_input={}),
        201,
    )
    release = request(
        client,
        f"/api/internal/approvals/{approval['id']}/commit",
        dict(fingerprint=approval["fingerprint"]),
    )
    instance = request(
        client,
        f"/api/internal/releases/{release['id']}/instances",
        dict(expected_release_fingerprint=release["fingerprint"], request_key=key),
        201,
    )
    return app, release, instance


def approve_stage(client, contract, selection, stage, run_id, instance, release, app, generation):
    base = f"/api/projects/{contract.project_id}/natural-trials/{contract.trial_key}"
    reviewed = request(
        client,
        base + "/stage-review",
        dict(
            contract=contract.model_dump(),
            approval_key=selection["approval"],
            stage=stage,
            run_id=run_id,
        ),
    )
    authority = gate.StageAuthority.model_validate(reviewed["authority"])
    require(
        authority.contract_fingerprint == fingerprint(contract.model_dump())
        and authority.stage == stage
        and authority.run_id == run_id
        and authority.generation_run_id == generation
        and authority.instance_id == instance["id"]
        and authority.instance_revision == instance["revision"]
        and authority.app_id == app["id"]
        and authority.candidate_fingerprint == app["fingerprint"]
        and authority.release_id == release["id"]
        and authority.release_fingerprint == release["fingerprint"]
        and reviewed["authority_fingerprint"] == fingerprint(authority.model_dump()),
        "ORIGINAL_STAGE_REVIEW_CHANGED",
    )
    approval = gate.StageApproveInput(
        authority=authority,
        expected_authority_fingerprint=reviewed["authority_fingerprint"],
        approval_key=selection["approval"],
        request_key=getattr(contract.stage_keys, stage) + "_phase",
        consent="BIND_ONLY_THIS_ACCEPTED_STAGE_RUN_APP_RELEASE_AND_COMPLETE_GOAL_TO_ORIGINAL_TRIAL",
    )
    bound = request(
        client,
        base + "/stage-approval",
        dict(contract=contract.model_dump(), approval=approval.model_dump()),
    )
    require(
        bound["authority"] == authority.model_dump()
        and bound["authority_fingerprint"] == reviewed["authority_fingerprint"],
        "ORIGINAL_STAGE_BINDING_CHANGED",
    )


def verified_original_run(client, target, rid):
    """Read the server's original key mapping before trusting/cancelling a Run."""
    require(isinstance(rid, str) and rid.startswith("run_"), "ORIGINAL_RUN_ID_REQUIRED")
    recovered = request(client, target["path"])
    if target["stage"] == "generate":
        require(recovered["id"] == rid, "ORIGINAL_RUN_ID_CHANGED")
        frozen = recovered["contract"]["snapshot"]["source_goal_card"]
        require(
            all(frozen[k] == v for k, v in target["source_goal"].items()), "ORIGINAL_GOAL_CHANGED"
        )
    else:
        expected = target["expected"]
        require(
            recovered["run_id"] == rid and all(recovered.get(k) == v for k, v in expected.items()),
            "ORIGINAL_RUN_SCOPE_CHANGED",
        )
    return recovered


def cancel_original(client, state, seconds=20):
    """Exact withdrawal then current Run command; no result/value/fence edits."""
    result = dict(
        status="CANCELLATION_UNKNOWN", trial_key=state.get("trial"), run_id=state.get("active_run")
    )
    if state.get("base") and state.get("review_token"):
        try:
            value = request(
                client,
                state["base"] + "/withdrawal",
                dict(review_token=state["review_token"], confirm_withdrawal=True),
            )
            result["trial_withdrawn"] = value.get("status") == "REVOKED"
        except Exception:
            result["trial_withdrawn"] = False
    rid = state.get("active_run")
    if rid is None or state.get("validated_target") is None:
        return result
    until = time.monotonic() + seconds
    try:
        verified_original_run(client, state["validated_target"], rid)
        current = request(client, "/api/runs/" + rid)
        if current["status"] not in TERMINAL:
            request(
                client,
                "/api/runs/" + rid + "/commands",
                dict(command="cancel", version=current["version"]),
            )
        while True:
            current = request(client, "/api/runs/" + rid)
            if current["status"] in TERMINAL:
                result.update(
                    status="TERMINAL_OBSERVED",
                    run_status=current["status"],
                    result_present=current.get("result") is not None,
                )
                return result
            require(time.monotonic() < until, "CANCEL_DID_NOT_CONVERGE")
            time.sleep(0.1)
    except Exception:
        return result


def run_stages(
    client,
    contract,
    selection,
    state,
    extract_bridge,
    *,
    record=lambda _: None,
    stop=None,
    checkpoint=lambda: None,
    cleanup_client=None,
    generate_only=False,
):
    """Original model lifecycle. Budgets are observed only after terminal stages,
    avoiding a read-lock wait disguised as a provider failure during G0/G1.
    """
    stop = stop or threading.Event()
    runs = {}
    generation = None
    attempted_cleanup = None
    until = min(
        time.monotonic() + MAX_SECONDS - 90,
        time.monotonic() + max(0, contract.expires_at - time.time()),
    )

    def current():
        checkpoint()
        require(not stop.is_set(), "USER_STOP_REQUESTED")
        require(
            time.monotonic() < until and time.time() < contract.expires_at, "ORIGINAL_TRIAL_EXPIRED"
        )

    def save(**fields):
        state.update(fields)
        record(dict(state))

    def accept(stage, create, target):
        current()
        save(
            stage=stage,
            active_run=None,
            validated_target=None,
            pending_request_key=getattr(contract.stage_keys, stage),
            model_requests=None,
        )
        accepted = create()
        rid = accepted["run_id"]
        verified_original_run(client, target, rid)
        runs[stage] = rid
        save(active_run=rid, validated_target=target, pending_request_key=None, runs=dict(runs))
        return rid

    def wait(rid, expected):
        while True:
            current()
            value = request(client, "/api/runs/" + rid)
            if value["status"] in TERMINAL:
                require(value["status"] == expected, "ORIGINAL_STAGE_TERMINAL_" + value["status"])
                return value
            time.sleep(0.25)

    require(
        cleanup_client is not None and cleanup_client is not client,
        "INDEPENDENT_CLEANUP_CLIENT_REQUIRED",
    )

    def hook(_):
        current()

    client.event_hooks["request"].append(hook)
    try:
        current()
        source, cold = contract.bindings
        # natural_spec requires read/checker/final:3 requests even without repair.
        # Source2/Cold1 gives six reservations:300s spacing before computation.
        # Original300s preparation cannot fit full chain; never extend/reapprove.
        enough_window(contract, dict(last_reserved_at=None), 3 if generate_only else 6)
        generation = accept(
            "generate",
            lambda: request(
                client,
                f"/api/projects/{contract.project_id}/goal-cards/{source.card_id}/application-runs",
                dict(
                    expected_version=source.goal_version,
                    expected_fingerprint=source.goal_fingerprint,
                    request_key=contract.stage_keys.generate,
                    family="natural_spec",
                ),
                202,
            ),
            dict(
                stage="generate",
                path=f"/api/projects/{contract.project_id}/goal-cards/{source.card_id}/application-runs?request_key={contract.stage_keys.generate}",
                source_goal=dict(
                    card_id=source.card_id,
                    version=source.goal_version,
                    fingerprint=source.goal_fingerprint,
                ),
            ),
        )
        generated = wait(generation, "PARTIAL")
        budget = ledger(client, contract, selection, runs=runs)
        save(model_requests=budget["reserved_requests"], ledger_status=budget["status"])
        current()
        saved = request(
            client,
            "/api/runs/" + generation + "/confirm-application-candidate",
            dict(
                expected_version=generated["version"],
                candidate_fingerprint=generated["result"]["candidate_fingerprint"],
                request_key=contract.stage_keys.generate + "_confirm",
                name="Bounded generated source application",
                artifact_write_consent=natural.CONSENT,
            ),
        )
        if generate_only:
            save(stage="generation_candidate_saved_cleanup_pending", saved_candidate=saved)
            attempted_cleanup = cancel_original(cleanup_client, state)
            require(
                attempted_cleanup.get("trial_withdrawn") is True
                and attempted_cleanup.get("status") == "TERMINAL_OBSERVED",
                "GENERATION_WITHDRAWAL_UNCONFIRMED",
            )
            cancellation = attempted_cleanup
            save(stage="generation_candidate_saved", active_run=None, cancellation=cancellation)
            return dict(
                status="ORIGINAL_GENERATION_CANDIDATE_SAVED",
                actual_model_requests=budget["reserved_requests"],
                trial_key=contract.trial_key,
                contract_fingerprint=fingerprint(contract.model_dump()),
                runs=runs,
                result=saved,
                cancellation=cancellation,
                source_cold_status="NOT_RUN_SELECTED_GENERATE_ONLY",
                semantic_goal_acceptance="NOT_RUN",
                owner_acceptance="PENDING",
            )
        app, release, instance = release_instance(
            client, saved["id"], contract.stage_keys.generate + "_instance"
        )
        model_count = sum(
            s["operator"].startswith("model.") for s in app["candidate"]["spec_recipe"]["steps"]
        )
        require(model_count == 2, "STRICT_PB_SOURCE_REQUIRES_TWO_MODEL_NODES")
        enough_window(contract, budget, model_count)
        source_run = accept(
            "source",
            lambda: request(
                client,
                f"/api/internal/instances/{instance['id']}/runs",
                dict(
                    expected_revision=instance["revision"],
                    expected_release_fingerprint=release["fingerprint"],
                    input={},
                    request_key=contract.stage_keys.source,
                ),
                202,
            ),
            dict(
                stage="source",
                path=f"/api/internal/instances/{instance['id']}/spec-run-requests/{contract.stage_keys.source}",
                expected=dict(
                    namespace="spec-run-request.v1",
                    principal_id=contract.principal_id,
                    project_id=contract.project_id,
                    instance_id=instance["id"],
                    app_id=app["id"],
                    release_id=release["id"],
                    request_key=contract.stage_keys.source,
                    request=dict(
                        expected_revision=instance["revision"],
                        expected_release_fingerprint=release["fingerprint"],
                        input={},
                        request_key=contract.stage_keys.source,
                    ),
                ),
            ),
        )
        current()
        approve_stage(
            client, contract, selection, "source", source_run, instance, release, app, generation
        )
        wait(source_run, "SUCCEEDED")
        budget = ledger(client, contract, selection, runs=runs)
        save(model_requests=budget["reserved_requests"], ledger_status=budget["status"])
        current()
        base = f"/api/projects/{contract.project_id}/natural-spec-task-runs/{source_run}"
        options = request(client, base + "/extraction-options")
        require(
            options["source_run_id"] == source_run
            and options["source_proof_fingerprint"] == fingerprint(options["source_proof"]),
            "ORIGINAL_SOURCE_PROOF_CHANGED",
        )
        review = pb.ReviewInput(
            source_run_id=source_run,
            expected_source_proof_fingerprint=options["source_proof_fingerprint"],
            expected_source_recipe_fingerprint=options["recipe_fingerprint"],
            card_id=cold.card_id,
            expected_goal_version=cold.goal_version,
            expected_goal_fingerprint=cold.goal_fingerprint,
            expected_source_hash=cold.source_hash,
            recipe=contract.extraction_recipe,
            name="Bounded original-source reuse",
            request_key=contract.extraction_request_key,
        )
        preview = request(client, base + "/extraction-reviews", review.model_dump())
        body = pb.ExtractInput(
            review=review,
            expected_review_fingerprint=preview["review_fingerprint"],
            consent=pb.CONSENT,
            artifact_write_consent=natural.CONSENT,
        )
        save(
            stage="strict_extract",
            pending_request_key=contract.extraction_request_key,
            active_run=None,
        )
        # Never substitute the generic HTTP /extractions endpoint.
        extracted = extract_bridge(selection, source_run, body)
        require(
            extracted["request"] == body.model_dump() and extracted["new_model_requests"] == 0,
            "STRICT_EXTRACTION_CHANGED",
        )
        require(
            ledger(client, contract, selection, runs=runs)["reserved_requests"]
            == budget["reserved_requests"],
            "EXTRACTION_CONSUMED_MODEL_SLOT",
        )
        current()
        app, release, instance = release_instance(
            client, extracted["id"], contract.stage_keys.cold + "_instance"
        )
        enough_window(
            contract,
            budget,
            sum(s.operator.startswith("model.") for s in contract.extraction_recipe.steps),
        )
        target = request(client, "/api/internal/instances/" + instance["id"])
        review = use.ReviewInput(
            expected_revision=target["revision"],
            expected_release_fingerprint=release["fingerprint"],
            expected_app_fingerprint=app["fingerprint"],
            expected_recipe_fingerprint=fingerprint(
                contract.extraction_recipe.model_dump(exclude_none=True)
            ),
            resource_id=cold.resource_id,
            card_id=cold.card_id,
            expected_goal_version=cold.goal_version,
            expected_goal_fingerprint=cold.goal_fingerprint,
            expected_source_hash=cold.source_hash,
            request_key=contract.stage_keys.cold,
        )
        base = "/api/internal/instances/" + instance["id"]
        preview = request(client, base + "/pb-use-reviews", review.model_dump())
        cold_request = dict(
            review=review.model_dump(),
            expected_review_fingerprint=preview["review_fingerprint"],
            consent=use.CONSENT,
        )
        cold_run = accept(
            "cold",
            lambda: request(
                client,
                base + "/pb-use-runs",
                cold_request,
                202,
            ),
            dict(
                stage="cold",
                path=base + "/pb-use-requests/" + contract.stage_keys.cold,
                expected=dict(
                    namespace=use.VERSION,
                    principal_id=contract.principal_id,
                    project_id=contract.project_id,
                    instance_id=instance["id"],
                    app_id=app["id"],
                    release_id=release["id"],
                    request_key=contract.stage_keys.cold,
                    request=cold_request,
                ),
            ),
        )
        current()
        approve_stage(
            client, contract, selection, "cold", cold_run, target, release, app, generation
        )
        wait(cold_run, "SUCCEEDED")
        budget = ledger(client, contract, selection, runs=runs)
        observed = request(client, f"/api/internal/instances/{instance['id']}/runs/{cold_run}")
        require(observed["status"] == "SUCCEEDED", "SAVED_COLD_RESULT_NOT_READABLE")
        save(
            stage="technical_saved",
            model_requests=budget["reserved_requests"],
            ledger_status=budget["status"],
            active_run=None,
        )
        return dict(
            status="ORIGINAL_MODEL_CHAIN_TECHNICALLY_SAVED",
            actual_model_requests=budget["reserved_requests"],
            trial_key=contract.trial_key,
            contract_fingerprint=fingerprint(contract.model_dump()),
            runs=runs,
            result=observed,
            semantic_goal_acceptance="NOT_RUN",
            owner_acceptance="PENDING",
        )
    except Exception as error:
        cancellation = (
            attempted_cleanup
            if attempted_cleanup is not None
            else cancel_original(cleanup_client, state)
        )
        save(
            stage="stopped_or_unknown",
            cancellation=cancellation,
            owned_bridge=error.state if isinstance(error, PhaseError) else None,
        )
        raise PhaseError(
            error.code
            if isinstance(error, PhaseError)
            else str(error)
            if type(error) is ValueError
            else type(error).__name__,
            dict(state),
        ) from None
    finally:
        client.event_hooks["request"].remove(hook)


INFLIGHT_BRIDGES = []


def bounded_extract(
    settings, bearer, selection, source_id, body, *, stop, absolute_deadline, observe_seconds=30
):
    """Bound observation and commit, without killing an unknown owned writer."""
    done = threading.Event()
    abort = threading.Event()
    holder = {}
    until = min(time.monotonic() + observe_seconds, absolute_deadline)

    def guard():
        require(
            not stop.is_set() and not abort.is_set() and time.monotonic() < until,
            "STRICT_EXTRACTION_STOP_OR_DEADLINE",
        )

    def work():
        try:
            holder["result"] = strict_extract(
                settings, bearer, selection, source_id, body, guard=guard
            )
        except BaseException as error:
            holder["error"] = error
        finally:
            done.set()

    thread = threading.Thread(target=work, name="sim2act-private-strict-extraction", daemon=False)
    thread.start()
    while not done.wait(0.02):
        if stop.is_set() or time.monotonic() >= until:
            abort.set()
            identity = dict(
                kind="OWNED_EXTRACTION_THREAD_UNKNOWN",
                pid=os.getpid(),
                thread_ident=thread.ident,
                native_id=thread.native_id,
                trial=selection["trial"],
                source_run_id=source_id,
            )
            INFLIGHT_BRIDGES.append((thread, identity))
            raise PhaseError("STRICT_EXTRACTION_INFLIGHT_UNKNOWN", identity)
    thread.join()
    if "error" in holder:
        raise holder["error"]
    return holder["result"]


def install_sql_guard(engine, guard):
    """Guard every SQL entry and the DBAPI commit; never replace original checks."""
    from sqlalchemy import event

    def guarded(*_):
        guard()

    event.listen(engine, "before_cursor_execute", guarded)
    event.listen(engine, "commit", guarded)


def strict_extract(settings, bearer, selection, source_id, body, *, guard=lambda: None):
    """Private production function bridge, never claims or executes a model Run.

    The original physical endpoint/schema/role is preserved; only this helper's
    session statement/lock waits are shortened. SQL and pre-commit guards prevent
    a late write if observation/cancellation expires while pure proof is running.
    """
    from sqlalchemy.engine import make_url

    from sim2act import pa_trial_dispatch
    from sim2act.db import Store
    from sim2act.spec_production import install

    url = make_url(settings.database_url)
    require(
        url.drivername == "postgresql+psycopg" and type(url.query.get("options", "")) is str,
        "ORIGINAL_POSTGRES_BINDING_REQUIRED",
    )
    original = url.query.get("options", "")
    require(
        "statement_timeout" not in original and "lock_timeout" not in original,
        "AMBIGUOUS_BRIDGE_WAIT_POLICY",
    )
    limited = url.update_query_dict(
        {"options": original + " -cstatement_timeout=2000 -clock_timeout=800"}
    )
    bounded = replace(settings, database_url=limited.render_as_string(hide_password=False))
    store = Store(bounded.database_url)
    worker = None
    clean = True

    install_sql_guard(store.engine, guard)
    try:
        guard()
        user = store.authenticate(bearer)
        require(user == selection["user"], "ORIGINAL_PRINCIPAL_MISMATCH")
        worker = install(
            store,
            bounded,
            user=user,
            project_id=selection["project"],
            trial_key=selection["trial"],
            approval_key=selection["approval"],
            account_id=selection["account"],
        )
        guard()
        return pa_trial_dispatch.extract_pb(
            worker, user, source_id, pb.ExtractInput.model_validate(body.model_dump())
        )
    finally:
        if worker is not None:
            worker.stop.set()
            clean = worker.drain_owned_heartbeats(10)
        if clean:
            store.engine.dispose()
        require(clean, "STRICT_EXTRACTION_BRIDGE_DRAIN_UNKNOWN")
