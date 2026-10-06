"""Closed asynchronous offline protocol API and durable test provider adapter."""

import copy
import time

import httpx
from fastapi import Depends
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy import select, update

from .db import attempts, fingerprint, runs
from .errors import DomainError
from .model import (
    InternModel,
    normalize_usage,
    parse_response,
    require_returned_model,
    returned_model_identity,
)
from .model_budget import BudgetedProvider
from .protocol_jobs import ColdInput, ExtractInput, SourceInput


class SourceRequest(SourceInput):
    request_key: str = Field(min_length=1, max_length=100)


class ExtractRequest(ExtractInput):
    request_key: str = Field(min_length=1, max_length=100)


class ColdRequest(ColdInput):
    request_key: str = Field(min_length=1, max_length=100)


FORBIDDEN_CLIENT_KEYS = {
    "replay",
    "responses",
    "candidate",
    "gold",
    "golden",
    "expected_output",
    "expected_answer",
    "oracle_payload",
    "pass",
    "decision",
    "verification",
    "scope",
    "runtime_id",
    "principal_id",
    "permissions",
    "grants",
}


def _closed_client_inputs(value):
    if isinstance(value, dict):
        if any(key.lower() in FORBIDDEN_CLIENT_KEYS for key in value):
            raise DomainError("INVALID_INPUT", "Client execution or semantic evidence is forbidden")
        for child in value.values():
            _closed_client_inputs(child)
    elif isinstance(value, list):
        for child in value:
            _closed_client_inputs(child)


def mount(app, store, limits, identity, settings):
    from .protocol_jobs import enqueue, inspect

    user_dependency = Depends(identity)

    def submit(pid, phase, body, user):
        if settings.mode != "mock":
            raise DomainError("PERMISSION_DENIED", "Protocol LIVE execution is not enabled")
        payload = body.model_dump()
        key = payload.pop("request_key")
        _closed_client_inputs(payload)
        result = enqueue(store, user, pid, phase, payload, key, limits)
        result["semantic_review"] = "WAITING_APPROVAL" if phase != "extract" else "NOT_RUN"
        return JSONResponse(result, status_code=202)

    @app.post("/api/projects/{pid}/protocol/source")
    def source(pid: str, body: SourceRequest, user=user_dependency):
        return submit(pid, "source", body, user)

    @app.post("/api/projects/{pid}/protocol/extract")
    def extract(pid: str, body: ExtractRequest, user=user_dependency):
        return submit(pid, "extract", body, user)

    @app.post("/api/projects/{pid}/protocol/cold")
    def cold(pid: str, body: ColdRequest, user=user_dependency):
        return submit(pid, "cold", body, user)

    @app.get("/api/projects/{pid}/protocol/runs/{rid}")
    def inspect_run(pid: str, rid: str, user=user_dependency):
        with store.tx() as c:
            store.own_project(c, user, pid)
            project = c.execute(select(runs.c.project_id).where(runs.c.id == rid)).scalar()
            if project != pid:
                raise DomainError("PERMISSION_DENIED")
        return inspect(store, user, rid)


class ProtocolAttemptRunner:
    """Explicit offline test adapter; reserves and records actual provider requests.

    The independent BudgetedProvider ledger remains mandatory. No exception path
    repairs, resends, substitutes a provider, or clears an unknown STARTED call.
    """

    def __init__(self, worker, run, snapshot, provider):
        if (
            not worker.store.test_only
            or worker.s.mode != "mock"
            or type(provider) is not BudgetedProvider
            or type(provider.model) is not InternModel
            or not isinstance(provider.model.transport, httpx.MockTransport)
            or provider.scope != snapshot["scope"]
            or provider.scope["mode"] != "offline"
        ):
            raise DomainError("PERMISSION_DENIED", "Explicit test-only offline provider required")
        self.worker, self.run, self.provider = worker, run, provider
        self.snapshot = copy.deepcopy(snapshot)
        self.last_attempt_id = None
        self.request_attempt_ids = {}

    def require_scope(self, scope):
        if (
            not self.worker.store.test_only
            or self.worker.s.mode != "mock"
            or type(self.provider) is not BudgetedProvider
            or type(self.provider.model) is not InternModel
            or not isinstance(self.provider.model.transport, httpx.MockTransport)
            or self.provider.scope != self.snapshot["scope"]
            or self.provider.scope["mode"] != "offline"
        ):
            raise DomainError("PERMISSION_DENIED", "Offline provider boundary changed")
        from .protocol_jobs import verified_pending

        with self.worker.store.tx() as c:
            self.worker.store.lock_project(c, self.run["principal_id"], self.run["project_id"])
            job, _ = verified_pending(
                self.worker.store, c, self.run["principal_id"], self.run["id"]
            )
            self.worker.store.guard(c, self.run["id"], self.run["fence"])
            if job["snapshot"] != self.snapshot:
                raise DomainError("VERSION_CONFLICT", "Accepted protocol scope changed")
        from .protocol_pool import require_pool

        require_pool(self.worker.store, self.snapshot["request_pool_id"])
        self.provider.require_scope(scope)

    def halt(self):
        self.provider.halt()

    def accept_candidate(self, candidate_fingerprint, source_proof_fingerprint):
        receipt = self.provider.accept_candidate(candidate_fingerprint, source_proof_fingerprint)
        if self.last_attempt_id is None:
            raise DomainError("VERIFICATION_FAILED")
        receipt = {
            **receipt,
            "attempt_id": self.last_attempt_id,
            "extraction_run_id": self.run["id"],
            "namespace": "protocol-attempt-receipt.v1",
        }
        with self.worker.store.tx() as c:
            self.worker.store.lock_project(c, self.run["principal_id"], self.run["project_id"])
            self.worker.store.guard(c, self.run["id"], self.run["fence"])
            # Preserve the enforced identity recorded by _record.
            parameters = dict(
                c.execute(
                    select(attempts.c.parameters).where(attempts.c.id == self.last_attempt_id)
                ).scalar_one()
            )
            parameters["protocol_candidate_receipt"] = receipt
            c.execute(
                update(attempts)
                .where(attempts.c.id == self.last_attempt_id)
                .values(parameters=parameters)
            )
        return receipt

    def verify_candidate_receipt(self, receipt, candidate_fingerprint, source_proof_fingerprint):
        from .protocol_jobs import verified_pending

        self.require_scope(self.snapshot["scope"])
        if self.snapshot["phase"] != "cold" or not isinstance(receipt, dict):
            raise DomainError("VERIFICATION_FAILED")
        with self.worker.store.tx() as c:
            self.worker.store.lock_project(c, self.run["principal_id"], self.run["project_id"])
            self.worker.store.guard(c, self.run["id"], self.run["fence"])
            source_id = self.snapshot["payload"]["extraction_run_id"]
            job, source_run = verified_pending(
                self.worker.store, c, self.run["principal_id"], source_id
            )
            plan = job["result"]["compiled_plan"]
            attempt = (
                c.execute(
                    select(attempts).where(
                        attempts.c.id == receipt.get("attempt_id"),
                        attempts.c.run_id == source_id,
                        attempts.c.status == "RECEIVED",
                    )
                )
                .mappings()
                .first()
            )
            if (
                not attempt
                or source_run["status"] != "SUCCEEDED"
                or plan != self.snapshot["compiled_plan"]
                or plan["candidate_receipt"] != receipt
                or receipt.get("namespace") != "protocol-attempt-receipt.v1"
                or receipt.get("extraction_run_id") != source_id
                or receipt.get("candidate_fingerprint") != candidate_fingerprint
                or receipt.get("source_proof_fingerprint") != source_proof_fingerprint
                or attempt["parameters"].get("protocol_candidate_receipt") != receipt
            ):
                raise DomainError("VERIFICATION_FAILED", "Persisted extraction receipt mismatch")
            message, _ = parse_response(attempt["response"])
            from .contracts import strict_json

            if fingerprint(strict_json(message["content"], 32000)) != candidate_fingerprint:
                raise DomainError(
                    "VERIFICATION_FAILED", "Candidate differs from accepted model JSON"
                )
        return True

    def call(self, messages, tools):
        messages, tools = copy.deepcopy(messages), copy.deepcopy(tools)
        self.require_scope(self.snapshot["scope"])
        worker, run = self.worker, self.run
        with worker.store.tx() as c:
            worker.store.lock_project(c, run["principal_id"], run["project_id"])
            current = worker.store.guard(c, run["id"], run["fence"])
            pending = c.execute(
                select(attempts.c.id).where(
                    attempts.c.run_id == run["id"], attempts.c.status == "STARTED"
                )
            ).first()
            if pending:
                raise DomainError("OUTCOME_UNKNOWN", "Unresolved model request cannot be resent")
            context = copy.deepcopy(current["context"])
        self.provider.preflight(messages, tools)
        context["messages"] = copy.deepcopy(messages)
        aid = worker.reserve(run["id"], run["fence"], context, request_tools=tools)
        self.last_attempt_id = aid
        self.request_attempt_ids[len(self.request_attempt_ids)] = aid
        start, raw = time.monotonic(), None
        try:
            raw = self.provider.call(messages, tools)
            identity = returned_model_identity(worker.s.model, raw.get("model"), enforced=True)
            require_returned_model(identity)
            parse_response(raw)
            if normalize_usage(raw)["status"] != "known":
                raise DomainError("OUTCOME_UNKNOWN", "Protocol usage must be known")
            self._record(aid, raw, start, "RECEIVED")
            return raw
        except DomainError as exc:
            raw = raw if raw is not None else self.provider.last_response
            try:
                self._record(aid, raw, start, "FAILED", exc.code)
            except BaseException:
                from .protocol_pool import halt_unknown

                halt_unknown(
                    worker.store, self.snapshot["request_pool_id"], "UNSETTLED_RESPONSE", aid
                )
                raise
            raise
        except BaseException:
            from .protocol_pool import halt_unknown

            halt_unknown(worker.store, self.snapshot["request_pool_id"], "INTERRUPTED_REQUEST", aid)
            raise
        # Process termination leaves STARTED durable and consumes the reservation.

    def _record(self, aid, raw, start, state, error=None):
        worker, run = self.worker, self.run
        with worker.store.tx() as c:
            worker.store.lock_project(c, run["principal_id"], run["project_id"])
            worker.store.guard(c, run["id"], run["fence"])
            parameters = worker.attempt_parameters(c, aid, raw)
            parameters["model_identity"] = returned_model_identity(
                worker.s.model, raw.get("model") if isinstance(raw, dict) else None, enforced=True
            )
            parameters["adapter_version"] = "offline-protocol-attempt.v1"
            parameters["raw_response_fingerprint"] = fingerprint(raw) if raw is not None else None
            safe = None
            if isinstance(raw, dict):
                try:
                    message, _ = parse_response(raw)
                    safe = {
                        "model": raw.get("model"),
                        "usage": raw.get("usage"),
                        "choices": [
                            {
                                "message": message,
                                "finish_reason": raw["choices"][0]["finish_reason"],
                            }
                        ],
                    }
                except DomainError:
                    pass  # Invalid/private output is represented by its fingerprint only.
            parameters["safe_response_fingerprint"] = fingerprint(safe)
            from .protocol_pool import finish_slot

            finish_slot(worker.store, c, run, run["fence"], aid, state, normalize_usage(raw), safe)
            c.execute(
                update(attempts)
                .where(attempts.c.id == aid)
                .values(
                    status=state,
                    error=error,
                    parameters=parameters,
                    response=safe,
                    response_model=raw.get("model") if isinstance(raw, dict) else None,
                    usage=normalize_usage(raw),
                    elapsed=time.monotonic() - start,
                )
            )
