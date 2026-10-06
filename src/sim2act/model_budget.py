"""Explicit experimental provider boundary; no API wiring or implicit LIVE activation.

The private file ledger supplements, never replaces, Run/Attempt/permission ledgers.
Deleting/replacing its directory is an administrative reset, not a supported recovery.
"""
import hashlib
import importlib
import json
import math
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import httpx

from .contracts import strict_json
from .db import fingerprint
from .errors import DomainError
from .model import InternModel, normalize_usage, require_returned_model, returned_model_identity
from .tools import definitions

ENDPOINT = "https://chat.intern-ai.org.cn/api/v1/chat/completions"
READ_TOOL_FINGERPRINT = fingerprint([x for x in definitions() if x["function"]["name"] == "resource.read"])
STAGES = {f"{phase}_{kind}": cap for kind in ("a", "b")
          for phase, cap in (("source", 3), ("extract", 1), ("cold", 3))}


@contextmanager
def _locked(path):
    # Nonblocking: a concurrent sender fails closed instead of waiting across network IO.
    with open(path, "a+b") as lock:
        if os.name == "nt":
            win_lock: Any = importlib.import_module("msvcrt")
            if lock.tell() == 0:
                lock.write(b"0")
                lock.flush()
            lock.seek(0)
            try:
                win_lock.locking(lock.fileno(), win_lock.LK_NBLCK, 1)
            except OSError as e:
                raise DomainError("LOCK_CONFLICT") from e
        else:
            import fcntl
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as e:
                raise DomainError("LOCK_CONFLICT") from e
        try:
            yield
        finally:
            if os.name == "nt":
                lock.seek(0)
                win_lock.locking(lock.fileno(), win_lock.LK_UNLCK, 1)
            else:
                fcntl.flock(lock, fcntl.LOCK_UN)


def _save(path, data):
    temporary = path.with_suffix(".pending")
    with open(temporary, "w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    if os.name != "nt":
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)


def initialize_ledger(path, scope):
    """Controller-only explicit initialization. Existing approval is never overwritten."""
    path = Path(path)
    if not path.parent.is_dir():
        raise DomainError("RESOURCE_UNAVAILABLE", "Create owned private ledger directory first")
    with _locked(path.with_suffix(".lock")):
        if path.exists():
            raise DomainError("VERSION_CONFLICT", "Budget ledger already exists")
        _save(path, {"version": 1, "scope_fingerprint": fingerprint(scope),
                     "reserved": 0, "known_tokens": 0, "halted": False, "stage_started": {}, "slots": []})


class BudgetedProvider:
    """One explicit stage of the fixed two-shape experiment, all sharing one ledger.

    authorize must check current user/runtime/resource intersection and return True.
    No retries, pauses, waits, granting, credential lookup or recovery resend occurs here.
    """
    def __init__(self, model, path, scope, stage, *, authorize, approved=False, clock=time.time):
        fields = {"approval_id", "project_id", "resource_ids", "tool_refs", "max_requests", "mode", "model"}
        if (set(scope) != fields or scope.get("model") != "intern-s2"
                or scope.get("tool_refs") != ["resource.read"]
                or type(scope.get("max_requests")) is not int
                or not 1 <= scope["max_requests"] <= 3):
            raise DomainError("PERMISSION_DENIED", "Closed read-only approval scope required")
        if type(model) is not InternModel or stage not in STAGES:
            raise DomainError("UNSUPPORTED_CAPABILITY")
        if scope.get("mode") == "offline":
            if not isinstance(model.transport, httpx.MockTransport):
                raise DomainError("PERMISSION_DENIED", "Offline requires zero-network MockTransport")
        elif scope.get("mode") != "live" or approved is not True or not scope.get("approval_id"):
            raise DomainError("PERMISSION_DENIED", "LIVE requires separate explicit approval")
        if model.settings.model != "intern-s2" or model.settings.max_output_tokens != 1024:
            raise DomainError("BUDGET_EXHAUSTED", "Frozen experiment output/model mismatch")
        self.model, self.path, self.scope, self.stage = model, Path(path), scope, stage
        self.authorize, self.clock = authorize, clock
        self.transport = model.transport
        self.require_scope(scope)

    def _load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if (data["version"] != 1 or data["scope_fingerprint"] != fingerprint(self.scope)
                    or type(data["halted"]) is not bool or not isinstance(data["slots"], list)
                    or type(data["reserved"]) is not int or type(data["known_tokens"]) is not int
                    or data["reserved"] != sum(x["reserved"] for x in data["slots"])
                    or data["known_tokens"] != sum(x.get("tokens", 0) for x in data["slots"])
                    or len(data["slots"]) > 14 or data["reserved"] > 64000
                    or data["known_tokens"] > 64000
                    or data["reserved"] < 0 or data["known_tokens"] < 0
                    or any(x["stage"] not in STAGES
                           or x["status"] not in {"STARTED", "RECEIVED", "FAILED_OR_UNKNOWN"}
                           or type(x["reserved"]) is not int or x["reserved"] < 1024
                           or type(x.get("tokens", 0)) is not int or x.get("tokens", 0) < 0
                           or type(x["time"]) not in {int, float} or not math.isfinite(x["time"])
                           for x in data["slots"])):
                raise ValueError("ledger mismatch")
            if (not isinstance(data.get("stage_started"), dict)
                    or any(k not in STAGES or type(v) not in {int, float} or not math.isfinite(v)
                           for k, v in data["stage_started"].items())):
                raise ValueError("stage clock mismatch")
            for stage, cap in STAGES.items():
                slots = [x for x in data["slots"] if x["stage"] == stage]
                if len(slots) > cap or sum(x["reserved"] for x in slots) > (8000 if stage.startswith("extract") else 24000):
                    raise ValueError("stage mismatch")
            return data
        except (OSError, ValueError, KeyError, TypeError) as e:
            raise DomainError("OUTCOME_UNKNOWN", "Budget ledger missing/corrupt; no reset or send") from e

    def require_scope(self, scope):
        if fingerprint(scope) != fingerprint(self.scope):
            raise DomainError("PERMISSION_DENIED", "Approval scope mismatch")
        with _locked(self.path.with_suffix(".lock")):
            data = self._load()
            if data["halted"] or any(x["status"] == "STARTED" for x in data["slots"]):
                raise DomainError("OUTCOME_UNKNOWN", "Stopped experiment cannot execute tools or models")
            if self.stage not in data["stage_started"]:
                data["stage_started"][self.stage] = self.clock()
                _save(self.path, data)
            if self.clock() - data["stage_started"][self.stage] > 300:
                data["halted"] = True
                _save(self.path, data)
                raise DomainError("BUDGET_EXHAUSTED", "Stage wall time exhausted")

    def call(self, messages, tools):
        if (type(self.model) is not InternModel or self.model.transport is not self.transport
                or self.model.settings.model != "intern-s2"
                or self.model.settings.max_output_tokens != 1024
                or (self.scope["mode"] == "offline"
                    and not isinstance(self.model.transport, httpx.MockTransport))):
            raise DomainError("PERMISSION_DENIED", "Frozen provider changed")
        if fingerprint(tools) not in {fingerprint([]), READ_TOOL_FINGERPRINT}:
            raise DomainError("PERMISSION_DENIED", "Only frozen read tool schema may be sent")
        # httpx uses exactly this encoding for InternModel's complete JSON body.
        payload = {"model": "intern-s2", "messages": messages, "tools": tools,
                   "stream": False, "max_tokens": 1024}
        try:
            body = httpx.Request("POST", ENDPOINT, json=payload).content
            chars = len(body.decode("utf-8"))
        except (ValueError, TypeError, UnicodeError) as e:
            raise DomainError("INVALID_INPUT") from e
        # Private JSON copies break aliases to caller-owned input and authorization hooks.
        frozen = json.loads(body)
        messages, tools = frozen["messages"], frozen["tools"]
        reserve = len(body) + 1024
        with _locked(self.path.with_suffix(".lock")):
            data = self._load()
            if data["halted"] or any(x["status"] == "STARTED" for x in data["slots"]):
                raise DomainError("OUTCOME_UNKNOWN", "Prior unknown request stops all experiment stages")
            if self.clock() - data["stage_started"][self.stage] > 300:
                data["halted"] = True
                _save(self.path, data)
                raise DomainError("BUDGET_EXHAUSTED", "Stage wall time exhausted")
            own = [x for x in data["slots"] if x["stage"] == self.stage]
            if (chars > 8000 or len(body) > 10000 or len(data["slots"]) >= 14
                    or len(own) >= min(STAGES[self.stage], self.scope["max_requests"]) or data["reserved"] + reserve > 64000
                    or sum(x["reserved"] for x in own) + reserve > (8000 if self.stage.startswith("extract") else 24000)):
                raise DomainError("BUDGET_EXHAUSTED", "Frozen complete body/global/stage cap exceeded")
            if data["slots"] and self.clock() - data["slots"][-1]["time"] < 6:
                raise DomainError("RATE_LIMITED", "No automatic wait/retry")
            if self.authorize(json.loads(json.dumps(self.scope))) is not True:
                raise DomainError("PERMISSION_DENIED")
            if (self.model.transport is not self.transport
                    or self.model.settings.model != "intern-s2"
                    or self.model.settings.max_output_tokens != 1024):
                raise DomainError("PERMISSION_DENIED", "Provider changed during authorization")
            slot = {"stage": self.stage, "status": "STARTED", "time": self.clock(),
                    "reserved": reserve, "body_sha256": hashlib.sha256(body).hexdigest(),
                    "chars": chars, "bytes": len(body)}
            data["slots"].append(slot)
            data["reserved"] += reserve
            _save(self.path, data)  # Crash after this point consumes a slot, never resend.
            try:
                raw = self.model.request(messages, tools)
                require_returned_model(returned_model_identity("intern-s2", raw.get("model")))
                usage = normalize_usage(raw)
                if usage["status"] != "known":
                    raise DomainError("OUTCOME_UNKNOWN", "Unknown model usage stops all stages")
                slot["tokens"] = usage["tokens"]["total_tokens"]
                data["known_tokens"] += slot["tokens"]
                actual_stage = sum(x.get("tokens", 0) for x in data["slots"]
                                   if x["stage"] == self.stage)
                if (self.clock() - data["stage_started"][self.stage] > 300
                        or data["known_tokens"] > 64000 or actual_stage > (8000 if self.stage.startswith("extract") else 24000)
                        or usage["tokens"]["completion_tokens"] > 1024
                        or slot["tokens"] > slot["reserved"]):
                    # Keep actual over-limit usage instead of inventing a capped value.
                    raise DomainError("BUDGET_EXHAUSTED")
                choices = raw.get("choices", [])
                if len(choices) == 1:
                    msg = choices[0].get("message", {})
                    if isinstance(msg.get("content"), str) and not msg.get("tool_calls"):
                        try:
                            slot["response_json_fingerprint"] = fingerprint(strict_json(msg["content"]))
                        except DomainError:
                            pass  # The protocol will reject/halt any malformed final response.
                slot["status"] = "RECEIVED"
                _save(self.path, data)
                return raw
            except BaseException:
                slot["status"] = "FAILED_OR_UNKNOWN"
                data["halted"] = True
                _save(self.path, data)
                raise

    def halt(self):
        """Protocol/semantic failure stops the entire approved experiment, no refunds."""
        with _locked(self.path.with_suffix(".lock")):
            data = self._load()
            data["halted"] = True
            _save(self.path, data)


    def accept_candidate(self, candidate_fingerprint, source_proof_fingerprint):
        """Bind the validated model JSON to its actual accepted extraction response."""
        self.require_scope(self.scope)
        if not self.stage.startswith("extract_"):
            raise DomainError("PERMISSION_DENIED")
        with _locked(self.path.with_suffix(".lock")):
            data = self._load()
            if not data["slots"]:
                raise DomainError("VERIFICATION_FAILED")
            slot = data["slots"][-1]
            if (slot["stage"] != self.stage or slot["status"] != "RECEIVED"
                    or slot.get("response_json_fingerprint") != candidate_fingerprint
                    or "candidate_receipt" in slot):
                raise DomainError("VERIFICATION_FAILED", "Candidate is not the accepted model response")
            receipt = {"scope_fingerprint": fingerprint(self.scope), "stage": self.stage,
                       "slot": len(data["slots"]) - 1, "candidate_fingerprint": candidate_fingerprint,
                       "source_proof_fingerprint": source_proof_fingerprint}
            slot["candidate_receipt"] = receipt
            _save(self.path, data)
            return receipt

    def verify_candidate_receipt(self, receipt, candidate_fingerprint, source_proof_fingerprint):
        """Cold controllers re-read the durable receipt; caller hashes cannot rebind it."""
        self.require_scope(self.scope)
        with _locked(self.path.with_suffix(".lock")):
            data = self._load()
            if (not isinstance(receipt, dict) or type(receipt.get("slot")) is not int
                    or not 0 <= receipt["slot"] < len(data["slots"])):
                raise DomainError("VERIFICATION_FAILED")
            slot = data["slots"][receipt["slot"]]
            expected = {"scope_fingerprint": fingerprint(self.scope),
                        "stage": "extract_" + self.stage[-1], "slot": receipt["slot"],
                        "candidate_fingerprint": candidate_fingerprint,
                        "source_proof_fingerprint": source_proof_fingerprint}
            if (fingerprint(receipt) != fingerprint(expected)
                    or fingerprint(slot.get("candidate_receipt")) != fingerprint(expected)
                    or slot.get("response_json_fingerprint") != candidate_fingerprint
                    or slot["status"] != "RECEIVED"):
                raise DomainError("VERIFICATION_FAILED", "Accepted extraction receipt mismatch")
            if self.authorize(json.loads(json.dumps(self.scope))) is not True:
                raise DomainError("PERMISSION_DENIED")
            return True
