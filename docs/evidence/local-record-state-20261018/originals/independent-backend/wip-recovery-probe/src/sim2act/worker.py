import argparse
import hashlib
import json
import signal
import threading
import time
from dataclasses import replace

from sqlalchemy import insert, select, update

from .config import Settings
from .contracts import strict_json
from .db import Store, attempts, fingerprint, new_id, operations, quotas, reservations, runs
from .errors import DomainError
from .model import (
    MODEL_IDENTITY_POLICY_VERSION,
    SYSTEM_PROMPT,
    InternModel,
    MockModel,
    normalize_usage,
    parse_response,
    require_returned_model,
    returned_model_identity,
)
from .tools import definitions, dispatch


class Worker:
    def __init__(
        self, store, settings, model=None, *, protocol_runner_factory=None, protocol_clock=None,
        goal_planner_transport=None, pa_trial=None,
    ):
        self.store, self.s = store, settings
        self.id = new_id("worker")
        self.model = model or (MockModel() if settings.mode == "mock" else InternModel(settings))
        if goal_planner_transport is not None:
            import httpx

            if (not store.test_only or settings.mode != "mock"
                    or not isinstance(goal_planner_transport, httpx.MockTransport)):
                raise DomainError("PERMISSION_DENIED", "Planner injection requires offline MockTransport")
        self.goal_planner_transport = goal_planner_transport
        self.pa_trial = pa_trial
        if pa_trial is not None:
            from .pa_trial_dispatch import validate
            validate(self)
        if protocol_runner_factory is not None and (not store.test_only or settings.mode != "mock"):
            raise DomainError("PERMISSION_DENIED", "Protocol injection is test-only and offline")
        self.protocol_runner_factory = protocol_runner_factory
        if protocol_clock is not None and (not store.test_only or settings.mode != "mock"):
            raise DomainError("PERMISSION_DENIED", "Synthetic protocol clock is test-only")
        self.protocol_clock = protocol_clock
        self.stop = threading.Event()
        self._project_cancel_scan = {}

    def reserve(self, run_id, fence, context, *, request_tools=None, verify_goal_source=False,
                planner_request=False, generation_request=False, natural_spec_request=None):
        from .natural_trial_runs import check_worker
        check_worker(self, run_id)
        if self.pa_trial is not None:
            from .pa_trial_dispatch import wait_unreserved
            wait_unreserved(self, run_id)
        s = self.s
        if natural_spec_request is not None:
            from .natural_spec_runtime import reservation_settings
            if planner_request or generation_request:
                raise DomainError("PERMISSION_DENIED", "Reservation families cannot be combined")
            s = reservation_settings(self, natural_spec_request)
        protocol_request = request_tools is not None and not planner_request and not generation_request and natural_spec_request is None
        request_tools = definitions() if request_tools is None else request_tools
        wire_seal = None
        # Conservative byte envelope, not a claim of actual tokenizer usage.
        envelope = (
            len(
                json.dumps(
                    {"messages": context["messages"], "tools": request_tools}, ensure_ascii=False
                ).encode()
            )
            + s.max_output_tokens
        )
        if protocol_request or planner_request or generation_request or natural_spec_request is not None:
            import httpx

            serialized = httpx.Request(
                "POST",
                "https://offline.invalid",
                json={
                    "model": s.model,
                    "messages": context["messages"],
                    "tools": request_tools,
                    "stream": False,
                    "max_tokens": s.max_output_tokens,
                },
            ).content
            wire_seal = {
                "sha256": hashlib.sha256(serialized).hexdigest(),
                "bytes": len(serialized),
                "characters": len(serialized.decode("utf-8")),
            }
            envelope = len(serialized) + s.max_output_tokens
        with self.store.tx() as c:
            if protocol_request or verify_goal_source:
                owner = (
                    c.execute(
                        select(runs.c.principal_id, runs.c.project_id).where(runs.c.id == run_id)
                    )
                    .mappings()
                    .one()
                )
                self.store.lock_project(c, owner["principal_id"], owner["project_id"])
            run = self.store.guard(c, run_id, fence)
            from .natural_trial_runs import check_worker_tx
            check_worker_tx(self, c, run_id)
            if self.store.frozen_contract(c, run).ordinary_csv_report is not None:
                raise DomainError("PERMISSION_DENIED", "事前CSV完整报告合同禁止模型请求或预留")
            if self.pa_trial is not None:
                from .pa_trial_dispatch import preflight
                preflight(self, c, run, generation=generation_request,
                          natural=natural_spec_request is not None)
            if natural_spec_request is not None:
                from .natural_spec_runtime import reservation_check
                reservation_check(self, c, run, context, request_tools, natural_spec_request, s)
            if generation_request:
                from .goal_applications import check_sender as check_generation_sender

                check_generation_sender(self, c, run, context["messages"], request_tools)
            if planner_request:
                from .goal_planner import check_sender, request_messages

                check_sender(self, self.store.frozen_contract(c, run), c, run)
                if (request_tools != [] or fingerprint(context["messages"])
                        != fingerprint(request_messages(self.store, c, run))):
                    raise DomainError("VERSION_CONFLICT", "Planner request changed")
            if verify_goal_source:
                self.store.frozen_contract(c, run)
            if run["status"] != "RUNNING":
                raise DomainError("VERSION_CONFLICT")
            for rid in run["resource_refs"]:
                self.store.authorize(
                    c,
                    run["principal_id"],
                    run["runtime_id"],
                    run["project_id"],
                    rid,
                    "resource.read",
                )
            self.store.authorize_receipts(c, run)
            if (
                context["requests"] >= s.max_requests
                or context["reserved_tokens"] + envelope > s.max_total_tokens
            ):
                raise DomainError("BUDGET_EXHAUSTED")
            q = (
                c.execute(
                    select(quotas).where(quotas.c.subject == s.quota_subject).with_for_update()
                )
                .mappings()
                .first()
            )
            if not q:
                raise DomainError(
                    "RESOURCE_UNAVAILABLE", "Quota subject not initialized by migration role"
                )
            activation_request = (planner_request and
                self.store.frozen_contract(c, run).natural_planning.activation is not None)
            generation_activation = (generation_request and
                self.store.frozen_contract(c, run).application_generation.activation is not None)
            if activation_request:
                from .natural_activations import now as activation_now
                now = activation_now()
            elif generation_activation:
                from .generation_approvals import now as generation_now
                now = generation_now()
            else:
                now = time.time()
            count = len(
                c.execute(
                    select(reservations.c.id).where(
                        reservations.c.subject == s.quota_subject,
                        reservations.c.created_at > now - 60,
                    )
                ).all()
            )
            if q["blocked_until"] > now or count >= (min(s.rpm, 1) if activation_request or generation_activation else s.rpm):
                raise DomainError("RATE_LIMITED", "Account-wide quota waiting", retryable=True)
            aid = new_id("attempt")
            if protocol_request:
                from .protocol_pool import reserve_slot

                reserve_slot(
                    self.store,
                    c,
                    run,
                    fence,
                    aid,
                    envelope,
                    fingerprint(
                        {"messages": context["messages"], "tools": request_tools, "model": s.model}
                    ),
                    **({"clock": self.protocol_clock} if self.protocol_clock is not None else {}),
                )
            c.execute(
                insert(reservations).values(
                    id=aid, subject=s.quota_subject, created_at=now, run_id=run_id
                )
            )
            c.execute(
                insert(attempts).values(
                    id=aid,
                    run_id=run_id,
                    created_at=now,
                    mode="MOCK" if s.mode == "mock" else "LIVE",
                    request_model=s.model,
                    status="STARTED",
                    usage={"status": "unknown", "tokens": None},
                    reserved_tokens=envelope,
                    parameters={
                        "stream": False,
                        "max_tokens": s.max_output_tokens,
                        "adapter_version": "1",
                        "model_identity_policy_version": MODEL_IDENTITY_POLICY_VERSION,
                        "weight_version": "unknown",
                        **({"pa_trial_binding": {
                            "version": "pa-trial-dispatch.v1",
                            "trial_fingerprint": self.pa_trial.contract_fingerprint,
                            "approval_key": self.pa_trial.approval_key,
                        }} if self.pa_trial is not None else {}),
                        "request_fingerprint": fingerprint(
                            {
                                "messages": context["messages"],
                                "tools": request_tools,
                                "model": s.model,
                            }
                        ),
                        **({"planning_wire" if planner_request else "protocol_wire": wire_seal}
                           if wire_seal is not None and not generation_request and natural_spec_request is None else {}),
                        **({"natural_spec": natural_spec_request, "natural_spec_wire": wire_seal}
                           if natural_spec_request is not None else {}),
                        **({"planning_fence": fence} if planner_request else {}),
                        **({"generation_wire": (wire_seal or {})["sha256"],
                            "generation_fence": fence,
                            "generation_index": context["requests"]} if generation_request else {}),
                    },
                )
            )
            if planner_request and self.store.frozen_contract(c, run).natural_planning.activation is not None:
                from .natural_activations import reserve_slot as reserve_natural_slot

                assert wire_seal is not None
                reserve_natural_slot(self.store, c, run, fence, aid, envelope, wire_seal["sha256"], s)
            if natural_spec_request is not None:
                from .natural_spec_runtime import reserve_node
                reserve_node(self, c, run, aid, natural_spec_request)
                from .natural_source_archives import record_request
                record_request(self.store, c, run, aid, serialized)
            if wire_seal is not None and not generation_request and natural_spec_request is None:
                self.store.event(
                    c,
                    run_id,
                    "NL_PLANNING_WIRE_RESERVED" if planner_request else "PROTOCOL_WIRE_RESERVED",
                    {"attempt_id": aid, "fence": fence, "wire": wire_seal},
                )
            if generation_request:
                self.store.event(c, run_id, "GA_WIRE_RESERVED", {
                    "attempt_id": aid, "index": context["requests"], "fence": fence, "wire": wire_seal})
                if generation_activation:
                    from .generation_approvals import reserve_slot as reserve_generation_slot

                    if wire_seal is None:
                        raise DomainError("VERSION_CONFLICT", "Missing generation wire proof")
                    reserve_generation_slot(self, c, run, aid, envelope, wire_seal["sha256"])
            context["requests"] += 1
            context["reserved_tokens"] += envelope
            c.execute(update(runs).where(runs.c.id == run_id).values(context=context))
            self.store.event(c, run_id, "MODEL_RESERVED", {"attempt_id": aid, "mode": s.mode,
                **({"planning_fence": fence} if planner_request else {})})
            if self.pa_trial is not None:
                from .pa_trial_dispatch import reserved
                reserved(self, c, run, aid, serialized)
            return aid

    def attempt_parameters(self, c, attempt_id, raw):
        parameters = dict(
            c.execute(select(attempts.c.parameters).where(attempts.c.id == attempt_id)).scalar_one()
        )
        parameters["model_identity"] = returned_model_identity(
            self.s.model,
            raw.get("model") if isinstance(raw, dict) else None,
            enforced=self.s.mode == "live",
        )
        return parameters

    def checkpoint(self, run_id, fence, context):
        with self.store.tx() as c:
            run = self.store.guard(c, run_id, fence)
            # Tool counter may have advanced in the local effect transaction.
            context["tools"] = max(context["tools"], run["context"]["tools"])
            c.execute(update(runs).where(runs.c.id == run_id).values(context=context))

    def finish(self, run_id, fence, state, error=None, result=None, *, verify_goal_source=False):
        with self.store.tx() as c:
            from .db import run_contracts
            from .goal_applications import source_scope_gate

            source_scope_gate(self.store, c, run_id)
            saved = c.execute(select(run_contracts.c.snapshot).where(run_contracts.c.run_id == run_id)).scalar_one_or_none()
            if saved is not None and not isinstance(saved, dict):
                raise DomainError("VERSION_CONFLICT", "Invalid frozen finalization contract")
            verify_goal_source = verify_goal_source or bool(saved and saved.get("natural_planning"))
            csv_report = bool(saved and saved.get("ordinary_csv_report"))
            if verify_goal_source or csv_report:
                owner = c.execute(select(runs.c.principal_id, runs.c.project_id).where(
                    runs.c.id == run_id,
                )).mappings().one()
                self.store.lock_project(c, owner["principal_id"], owner["project_id"])
            run = self.store.guard(c, run_id, fence)
            if verify_goal_source:
                frozen = self.store.frozen_contract(c, run)
                if frozen.application_generation is not None and state in {"SUCCEEDED", "PARTIAL"}:
                    from .goal_applications import check_active, verified_candidate

                    if frozen.application_generation.activation is not None or frozen.application_generation.version in {"goal-spec-checklist-application.v1", "goal-natural-spec-application.v1"}:
                        check_active(self, c, run)
                    candidate = verified_candidate(self.store, c, run, frozen.limits)
                    if state != "PARTIAL" or result != {
                        "candidate": candidate, "candidate_fingerprint": fingerprint(candidate),
                        "goal_acceptance": "NOT_RUN", "semantic_status": "UNKNOWN", "app_created": False}:
                        raise DomainError("VERIFICATION_FAILED", "Generation is candidate-ready only")
                if frozen.natural_planning is not None and state in {"SUCCEEDED", "PARTIAL"} and result is None:
                    raise DomainError("VERIFICATION_FAILED", "Goal finalization requires verified result")
                if frozen.natural_planning is not None and result is not None:
                    from .goal_planner import verify_result

                    if frozen.natural_planning.activation is not None:
                        from .natural_activations import validate_run

                        validate_run(self.store, c, run, self.s, active=True)
                    verify_result(self.store, c, run, result)
                    accepted = result.get("task_acceptance", {}).get("whole_task_accepted") is True
                    if state in {"SUCCEEDED", "PARTIAL"} and (state == "SUCCEEDED") != accepted:
                        raise DomainError("VERIFICATION_FAILED", "Single-step success is not whole-goal acceptance")
            if run["status"] == "CANCEL_REQUESTED":
                state = "CANCELLED"
            elif run["status"] == "PAUSE_REQUESTED":
                state = "PAUSED"
            if self.store.has_unknown(c, run_id):
                state = "RECONCILING" if run["cancel_intent"] else "WAITING_RESOURCE"
            if csv_report:
                # Only the complete independent composite check can authorize success.
                from .ordinary_csv import accepted_result, active, confirmation

                frozen_csv = self.store.frozen_contract(c, run)
                if state == "SUCCEEDED":
                    active(self.store, c, run, frozen_csv, self.s)
                    confirmation(self.store, c, run, frozen_csv)
                    if result != accepted_result(self.store, c, run, frozen_csv):
                        raise DomainError("VERIFICATION_FAILED", "完整事前CSV合同尚未通过")
                else:
                    result = None
            if saved and saved.get("artifact_delivery") and state in {"PARTIAL", "SUCCEEDED"}:
                from .ordinary_artifacts import report

                frozen_md = self.store.frozen_contract(c, run)
                if state != "PARTIAL" or not result or result.get("artifact_delivery") != report(self.store, c, run, frozen_md, required=True):
                    raise DomainError("VERIFICATION_FAILED", "Required same-Run MD is not delivered")
            if saved and saved.get("application_generation") and state != "PARTIAL":
                result = None
            if state in {"SUCCEEDED", "PARTIAL"}:
                from .natural_trial_runs import check_worker_tx
                check_worker_tx(self, c, run_id)
                if self.pa_trial is not None:
                    from .pa_trial_dispatch import check_commit
                    check_commit(self, c, run)
                for rid in run["resource_refs"]:
                    self.store.authorize(
                        c,
                        run["principal_id"],
                        run["runtime_id"],
                        run["project_id"],
                        rid,
                        "resource.read",
                    )
                self.store.authorize_receipts(c, run)
            c.execute(
                update(runs)
                .where(runs.c.id == run_id)
                .values(
                    status=state,
                    result=result,
                    error=error,
                    lease_until=0,
                    version=run["version"] + 1,
                )
            )
            self.store.event(c, run_id, "STATE", {"status": state, "error": error})
            if csv_report:
                from .csv_full_report_instances import finish_tx as finish_report_instance
                finish_report_instance(self.store, c, run_id, state, error)
            if csv_report and state == "SUCCEEDED":
                active(self.store, c, run, frozen_csv, self.s)
                if run["lease_until"] <= time.time():
                    raise DomainError("VERSION_CONFLICT", "Original worker lease expired before final commit")
            if state in {"SUCCEEDED", "PARTIAL"}:
                from .natural_trial_runs import check_worker_tx
                check_worker_tx(self, c, run_id)
            if self.pa_trial is not None and state in {"SUCCEEDED", "PARTIAL"}:
                from .pa_trial_dispatch import check_commit
                check_commit(self, c, run)
            if verify_goal_source and frozen.application_generation is not None and state == "PARTIAL" and (frozen.application_generation.activation is not None or frozen.application_generation.version in {"goal-spec-checklist-application.v1", "goal-natural-spec-application.v1"}):
                check_active(self, c, run)
                if run["lease_until"] <= time.time():
                    raise DomainError("VERSION_CONFLICT", "Original worker lease expired before final commit")
                if frozen.application_generation.version in {"goal-spec-checklist-application.v1", "goal-natural-spec-application.v1"}:
                    current = c.execute(select(runs.c.status, runs.c.cancel_intent, runs.c.fence, runs.c.version)
                        .where(runs.c.id == run_id)).mappings().one()
                    if current["status"] != state or current["cancel_intent"] or current["fence"] != fence or current["version"] != run["version"] + 1:
                        raise DomainError("VERSION_CONFLICT", "Spec generation terminal ownership changed")

    def process(self, run):
        from .natural_trial_runs import check_worker
        check_worker(self, run["id"])
        from .csv_dag import is_job as is_csv_dag
        from .csv_dag import process_job as process_csv_dag

        if is_csv_dag(self.store, run["id"]):
            if self.s.mode != "mock" or self.s.live_enabled:
                raise DomainError("PERMISSION_DENIED", "CSV DAG is offline engineering only")
            process_csv_dag(self, run)
            return
        from .protocol_jobs import is_protocol_job
        from .protocol_jobs import process_job as process_protocol_job

        if is_protocol_job(self.store, run["id"]):
            if self.s.mode != "mock":
                raise DomainError("PERMISSION_DENIED", "Protocol LIVE execution is not enabled")
            process_protocol_job(self, run)
            return
        from .app_jobs import is_app_job, process_job

        if is_app_job(self.store, run["id"]):
            process_job(self, run)
            return
        rid, fence = run["id"], run["fence"]
        with self.store.tx() as c:
            contract = self.store.frozen_contract(c, run)
        if contract.mode != self.s.mode or contract.request_model != self.s.model:
            raise DomainError("VERSION_CONFLICT", "Worker model policy differs from frozen request")
        if contract.ordinary_correction is not None and (self.s.mode != "mock" or self.s.live_enabled):
            raise DomainError("PERMISSION_DENIED", "Ordinary correction real model allowance is zero")
        self.s = replace(
            self.s,
            **{
                key: min(getattr(self.s, key), value)
                for key, value in contract.limits.model_dump().items()
            },
        )
        if contract.ordinary_csv_report is not None:
            from .ordinary_csv import process

            process(self, run, contract)
            return
        if contract.application_generation is not None:
            from .goal_applications import process

            process(self, run, contract)
            return
        if contract.natural_planning is not None:
            from .goal_planner import process

            process(self, run, contract)
            return
        ctx = dict(run["context"])
        ctx["messages"] = list(ctx["messages"])
        goal_tools = definitions()
        goal_input = {"goal": run["goal"], "resource_refs": run["resource_refs"]}
        if contract.source_goal_card is not None:
            goal_tools = [t for t in goal_tools if t["function"]["name"] in
                          ({"resource.read", "data.aggregate_csv", "artifact.save_text"} if contract.artifact_delivery else
                           {"resource.read", "data.aggregate_csv"})]
            goal_input["saved_goal"] = contract.source_goal_card.model_dump()
            if contract.artifact_delivery is not None:
                goal_input["artifact_delivery"] = contract.artifact_delivery.model_dump()
            if contract.ordinary_correction is not None:
                goal_input["human_correction"] = contract.ordinary_correction.model_dump()
            if ctx["messages"]:
                try:
                    original_input = ctx["messages"][1]["content"]
                    valid = (
                        len(ctx["messages"]) >= 2
                        and ctx["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}
                        and ctx["messages"][1]["role"] == "user"
                        and isinstance(original_input, str)
                        and fingerprint(strict_json(original_input, max_bytes=len(original_input.encode())))
                        == fingerprint(goal_input)
                    )
                except (KeyError, IndexError, TypeError, ValueError, DomainError):
                    valid = False
                if not valid:
                    raise DomainError("VERSION_CONFLICT", "Resumed context lost frozen goal conditions")
        if not ctx["messages"]:
            ctx["messages"] = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        goal_input,
                        ensure_ascii=False,
                    ),
                },
            ]
        hb_stop = threading.Event()

        def heartbeat():
            while not hb_stop.wait(self.s.lease_seconds / 3):
                try:
                    self.store.heartbeat(self.id, rid, fence, self.s.lease_seconds)
                except Exception:
                    hb_stop.set()

        hb = threading.Thread(target=heartbeat, daemon=True)
        hb.start()
        try:
            while not self.stop.is_set():
                with self.store.tx() as c:
                    current = self.store.guard(c, rid, fence)
                if current["status"] != "RUNNING":
                    self.finish(
                        rid,
                        fence,
                        "PAUSED" if current["status"] == "PAUSE_REQUESTED" else "CANCELLED",
                    )
                    return
                if time.time() - run["created_at"] > self.s.run_seconds:
                    raise DomainError("BUDGET_EXHAUSTED", "Run wall time exhausted")
                # Resume from recorded assistant calls; no hidden model re-call on safe tool recovery.
                pending = []
                assistant = next(
                    (m for m in reversed(ctx["messages"]) if m["role"] == "assistant"), None
                )
                completed = {m.get("tool_call_id") for m in ctx["messages"] if m["role"] == "tool"}
                unresolved = (
                    assistant
                    and assistant.get("tool_calls")
                    and any(x["id"] not in completed for x in assistant["tool_calls"])
                )
                if unresolved:
                    fake = {"choices": [{"message": assistant, "finish_reason": "tool_calls"}]}
                    _, all_calls = parse_response(fake)
                    pending = [x for x in all_calls if x["id"] not in completed]
                elif ctx["messages"][-1]["role"] == "assistant":
                    # A validated final response imported by reconciliation is already complete.
                    pending = []
                else:
                    aid = self.reserve(rid, fence, ctx, verify_goal_source=contract.source_goal_card is not None)
                    start = time.monotonic()
                    raw = None
                    try:
                        raw = self.model.request(ctx["messages"], goal_tools)
                        msg, pending = parse_response(raw)
                        identity = returned_model_identity(
                            self.s.model, raw.get("model"), enforced=self.s.mode == "live"
                        )
                        require_returned_model(identity)
                        ctx["messages"].append(msg)
                        with self.store.tx() as c:
                            current = self.store.guard(c, rid, fence)
                            ctx["tools"] = max(ctx["tools"], current["context"]["tools"])
                            c.execute(update(runs).where(runs.c.id == rid).values(context=ctx))
                            c.execute(
                                update(attempts)
                                .where(attempts.c.id == aid)
                                .values(
                                    status="RECEIVED",
                                    response_model=raw.get("model"),
                                    parameters=self.attempt_parameters(c, aid, raw),
                                    usage=normalize_usage(raw),
                                    response=msg,
                                    elapsed=time.monotonic() - start,
                                )
                            )
                    except DomainError as e:
                        repair = (
                            e.code
                            in {
                                "MODEL_OUTPUT_INVALID",
                                "MODEL_TIMEOUT_OR_TRUNCATED",
                                "INVALID_INPUT",
                            }
                            and ctx["repairs"] < self.s.max_repairs
                        )
                        if repair:
                            ctx["repairs"] += 1
                            ctx["messages"].append(
                                {
                                    "role": "user",
                                    "content": "Previous attempt failed validation: "
                                    + e.code
                                    + ". Return complete valid parameters; no partial tool was executed.",
                                }
                            )
                        with self.store.tx() as c:
                            self.store.guard(c, rid, fence)
                            c.execute(
                                update(attempts)
                                .where(attempts.c.id == aid)
                                .values(
                                    status="FAILED",
                                    error=e.code,
                                    elapsed=time.monotonic() - start,
                                    usage=normalize_usage(raw),
                                    parameters=self.attempt_parameters(c, aid, raw),
                                    response_model=raw.get("model")
                                    if isinstance(raw, dict) and isinstance(raw.get("model"), str)
                                    else None,
                                )
                            )
                            if repair:
                                c.execute(update(runs).where(runs.c.id == rid).values(context=ctx))
                            if e.code == "RATE_LIMITED":
                                c.execute(
                                    update(quotas)
                                    .where(quotas.c.subject == self.s.quota_subject)
                                    .values(blocked_until=time.time() + 60)
                                )
                        if repair:
                            continue
                        raise
                if time.time() - run["created_at"] > self.s.run_seconds:
                    raise DomainError("BUDGET_EXHAUSTED", "Run wall time exhausted before dispatch")
                if contract.source_goal_card is not None:
                    with self.store.tx() as c:
                        self.store.frozen_contract(c, self.store.guard(c, rid, fence))
                    allowed = {"resource.read", "data.aggregate_csv"} | ({"artifact.save_text"} if contract.artifact_delivery else set())
                    if any(call["function"]["name"] not in allowed for call in pending):
                        raise DomainError("UNSUPPORTED_CAPABILITY", "Saved-goal task is read-only")
                if contract.artifact_delivery is not None:
                    from .ordinary_artifacts import check_pending

                    check_pending(pending)
                if pending:
                    if ctx["tools"] + len(pending) > self.s.max_tools:
                        raise DomainError("BUDGET_EXHAUSTED")
                    completed_ids = {
                        m.get("tool_call_id") for m in ctx["messages"] if m["role"] == "tool"
                    }
                    for call in pending:
                        if call["id"] in completed_ids:
                            continue
                        if contract.source_goal_card is not None:
                            with self.store.tx() as c:
                                self.store.frozen_contract(c, self.store.guard(c, rid, fence))
                        receipt = dispatch(self.store, rid, fence, call)
                        ctx["messages"].append(
                            {
                                "role": "tool",
                                "tool_call_id": call["id"],
                                "content": json.dumps(receipt, ensure_ascii=False),
                            }
                        )
                        self.checkpoint(rid, fence, ctx)
                else:
                    with self.store.engine.connect() as c:
                        verified = (
                            c.execute(
                                select(operations.c.receipt).where(
                                    operations.c.run_id == rid, operations.c.status == "VERIFIED"
                                )
                            )
                            .scalars()
                            .all()
                        )
                    if not verified:
                        raise DomainError(
                            "VERIFICATION_FAILED", "No independently verified tool effect"
                        )
                    artifact_result = {}
                    if contract.artifact_delivery is not None:
                        from .ordinary_artifacts import report

                        with self.store.tx() as c:
                            current = self.store.guard(c, rid, fence)
                            artifact_result["artifact_delivery"] = report(self.store, c, current, contract, required=True)
                    # F1 only: receipts verified, semantic goal acceptance belongs to F2/F3.
                    self.finish(
                        rid,
                        fence,
                        "PARTIAL",
                        result={
                            "mode": self.s.mode.upper(),
                            "answer": ctx["messages"][-1]["content"],
                            "receipts": verified,
                            "goal_acceptance": "NOT_RUN",
                            **artifact_result,
                            "boundary": "F1 tool chain; application/semantic acceptance not yet implemented",
                            **({"source_goal_card": {"card_id": contract.source_goal_card.card_id,
                                 "version": contract.source_goal_card.version,
                                 "fingerprint": contract.source_goal_card.fingerprint}}
                               if contract.source_goal_card is not None else {}),
                        },
                        verify_goal_source=contract.source_goal_card is not None,
                    )
                    return
            self.finish(rid, fence, "PAUSED")
        except DomainError as e:
            state = (
                "WAITING_RESOURCE"
                if e.code
                in {"GRANT_REVOKED", "RESOURCE_UNAVAILABLE", "RATE_LIMITED", "OUTCOME_UNKNOWN"}
                else "FAILED"
            )
            try:
                self.finish(rid, fence, state, e.public())
            except DomainError:
                pass  # Stale worker cannot write any new state; recovery owns reconciliation.
        finally:
            hb_stop.set()
            hb.join(timeout=2)

    def once(self):
        self.store.heartbeat(self.id)
        from .project_check_recovery import recover_cancelled_checks

        if recover_cancelled_checks(self.store, scan=self._project_cancel_scan):
            return True
        run = self.store.claim(self.id, self.s.lease_seconds,
                               **({"trial_binding": self.pa_trial} if self.pa_trial is not None else {}))
        if run:
            original = self.s
            try:
                self.process(run)
            except DomainError as e:
                from .protocol_jobs import fail_job as fail_protocol_job
                from .protocol_jobs import is_protocol_job

                if is_protocol_job(self.store, run["id"]):
                    fail_protocol_job(self, run, e)
                    return True
                from .app_jobs import fail_job, is_app_job

                if is_app_job(self.store, run["id"]):
                    fail_job(self, run, e)
                    return True
                with self.store.tx() as c:
                    current_fence = c.execute(select(runs.c.fence).where(runs.c.id == run["id"])).scalar_one()
                    if current_fence == run["fence"]:
                        c.execute(
                            update(runs)
                            .where(runs.c.id == run["id"])
                            .values(status="FAILED", error=e.public(), lease_until=0)
                        )
                        self.store.event(c, run["id"], "CONTRACT_REJECTED", e.public())
            finally:
                self.s = original
        return run is not None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    s = Settings.from_env()
    w = Worker(Store(s.database_url), s)
    signal.signal(signal.SIGINT, lambda *_: w.stop.set())
    signal.signal(signal.SIGTERM, lambda *_: w.stop.set())
    while not w.stop.is_set():
        w.once()
        if args.once:
            break
        w.stop.wait(1)


if __name__ == "__main__":
    main()
