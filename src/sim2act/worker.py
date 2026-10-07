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
        goal_planner_transport=None,
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
        if protocol_runner_factory is not None and (not store.test_only or settings.mode != "mock"):
            raise DomainError("PERMISSION_DENIED", "Protocol injection is test-only and offline")
        self.protocol_runner_factory = protocol_runner_factory
        if protocol_clock is not None and (not store.test_only or settings.mode != "mock"):
            raise DomainError("PERMISSION_DENIED", "Synthetic protocol clock is test-only")
        self.protocol_clock = protocol_clock
        self.stop = threading.Event()

    def reserve(self, run_id, fence, context, *, request_tools=None, verify_goal_source=False,
                planner_request=False):
        s = self.s
        protocol_request = request_tools is not None and not planner_request
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
        if protocol_request or planner_request:
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
            if planner_request:
                from .goal_planner import check_sender, request_messages

                check_sender(self, self.store.frozen_contract(c, run))
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
            now = time.time()
            count = len(
                c.execute(
                    select(reservations.c.id).where(
                        reservations.c.subject == s.quota_subject,
                        reservations.c.created_at > now - 60,
                    )
                ).all()
            )
            if q["blocked_until"] > now or count >= s.rpm:
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
                        "request_fingerprint": fingerprint(
                            {
                                "messages": context["messages"],
                                "tools": request_tools,
                                "model": s.model,
                            }
                        ),
                        **({"planning_wire" if planner_request else "protocol_wire": wire_seal}
                           if wire_seal is not None else {}),
                    },
                )
            )
            if wire_seal is not None:
                self.store.event(
                    c,
                    run_id,
                    "NL_PLANNING_WIRE_RESERVED" if planner_request else "PROTOCOL_WIRE_RESERVED",
                    {"attempt_id": aid, "fence": fence, "wire": wire_seal},
                )
            context["requests"] += 1
            context["reserved_tokens"] += envelope
            c.execute(update(runs).where(runs.c.id == run_id).values(context=context))
            self.store.event(c, run_id, "MODEL_RESERVED", {"attempt_id": aid, "mode": s.mode})
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
            if verify_goal_source:
                owner = c.execute(select(runs.c.principal_id, runs.c.project_id).where(
                    runs.c.id == run_id,
                )).mappings().one()
                self.store.lock_project(c, owner["principal_id"], owner["project_id"])
            run = self.store.guard(c, run_id, fence)
            if verify_goal_source:
                frozen = self.store.frozen_contract(c, run)
                if frozen.natural_planning is not None and result is not None:
                    from .goal_planner import verify_result

                    verify_result(self.store, c, run, result)
            if run["status"] == "CANCEL_REQUESTED":
                state = "CANCELLED"
            elif run["status"] == "PAUSE_REQUESTED":
                state = "PAUSED"
            if self.store.has_unknown(c, run_id):
                state = "RECONCILING" if run["cancel_intent"] else "WAITING_RESOURCE"
            if state in {"SUCCEEDED", "PARTIAL"}:
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

    def process(self, run):
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
        self.s = replace(
            self.s,
            **{
                key: min(getattr(self.s, key), value)
                for key, value in contract.limits.model_dump().items()
            },
        )
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
                          {"resource.read", "data.aggregate_csv"}]
            goal_input["saved_goal"] = contract.source_goal_card.model_dump()
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
                    if any(call["function"]["name"] not in {"resource.read", "data.aggregate_csv"} for call in pending):
                        raise DomainError("UNSUPPORTED_CAPABILITY", "Saved-goal task is read-only")
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
        run = self.store.claim(self.id, self.s.lease_seconds)
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
                    current = c.execute(select(runs).where(runs.c.id == run["id"])).mappings().one()
                    if current["fence"] == run["fence"]:
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
