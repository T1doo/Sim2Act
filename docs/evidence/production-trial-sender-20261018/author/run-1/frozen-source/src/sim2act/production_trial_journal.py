"""Uninstalled durable policy journal. No source, sender or execution authority.

Only this controller loads ledger/cursor state. Caller snapshots cannot replace
it. The new namespace is separate from historical synthetic accounting; API and
Worker do not install it. All receipts remain non-executable. PostgreSQL SQL is
supported by the existing Store, but SQLite tests do not qualify PG concurrency.
"""

import hashlib
import json
from typing import Literal

from pydantic import Field, ValidationError
from sqlalchemy import select, update

from . import natural_trial_budget as budget
from . import production_trial_policy as policy
from .db import delivery_graph_requests as rows
from .db import fingerprint
from .errors import DomainError

KIND = "uninstalled-production-trial-journal.v1"
QUOTA = KIND + ".quota"


class Receipt(policy.evidence.EvidenceData):
    ledger: policy.Ledger
    quota: policy.AccountQuotaCursor
    revision: int = Field(ge=0)
    quota_revision: int = Field(ge=0)
    duplicate: bool = False
    changed: bool = False
    scope: Literal["UNINSTALLED_DURABLE_JOURNAL_ONLY"] = "UNINSTALLED_DURABLE_JOURNAL_ONLY"
    live_allowed: Literal[False] = False
    dispatch_authorized: Literal[False] = False
    real_source_verified: Literal[False] = False


def _require(ok, code="VERSION_CONFLICT"):
    if not ok:
        raise DomainError(code, "Uninstalled durable policy journal boundary")


def _pair(c, owner, entity, kind, key):
    try:
        return budget._load(c, owner, entity, kind, key)
    except (KeyError, TypeError, ValueError, AttributeError):
        _require(False)


def _snapshot(request, response):
    return dict(request=request, response=response)


def _values(snapshot):
    return dict(snapshot=snapshot, fingerprint=fingerprint(snapshot),
                request_fingerprint=fingerprint(snapshot["request"]))


def _cas_pair(c, owner, entity, kind, key, previous, current):
    """Both mirrors use the exact previously loaded revision-bearing snapshot."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    insert = sqlite_insert if c.dialect.name == "sqlite" else pg_insert
    for tag in (kind, kind + "_seal"):
        if previous is None:
            result = c.execute(insert(rows).values(principal_id=owner, app_id=entity,
                kind=tag, request_key=key, **_values(current)).on_conflict_do_nothing())
        else:
            result = c.execute(update(rows).where(rows.c.principal_id == owner,
                rows.c.app_id == entity, rows.c.kind == tag, rows.c.request_key == key,
                rows.c.fingerprint == fingerprint(previous),
                rows.c.request_fingerprint == fingerprint(previous["request"]))
                .values(**_values(current)))
        _require(result.rowcount == 1)


def _context(store, c, user, contract, key, account):
    original, scope = policy._requirements(user, contract, key)
    _require(type(account) is str, "PERMISSION_DENIED")
    from .production_trial_admission import canonical_quota_subject

    _require(scope.quota_subject == canonical_quota_subject(account), "PERMISSION_DENIED")
    project = store.lock_project(c, user, scope.project_id)
    _require(project["runtime_id"] == scope.runtime_id, "PERMISSION_DENIED")
    request = dict(namespace=KIND, scope=scope.model_dump(mode="json"), account_id=account)
    quota_request = dict(namespace=QUOTA, account_id=account, quota_subject=scope.quota_subject)
    quota_entity = "policyquota_" + hashlib.sha256(scope.quota_subject.encode()).hexdigest()
    return original, scope, request, quota_request, quota_entity


def _quota(c, request, entity, *, create):
    prior = _pair(c, QUOTA, entity, QUOTA, "quota")
    seeded = False
    if prior is None and create:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        insert = sqlite_insert if c.dialect.name == "sqlite" else pg_insert
        cursor = policy.AccountQuotaCursor(account_id=request["account_id"],
            quota_subject=request["quota_subject"])
        initial = _snapshot(request, dict(revision=0, cursor=cursor.model_dump(mode="json")))
        counts = [c.execute(insert(rows).values(principal_id=QUOTA, app_id=entity,
            kind=tag, request_key="quota", **_values(initial)).on_conflict_do_nothing()).rowcount
            for tag in (QUOTA, QUOTA + "_seal")]
        # Never repair a pre-existing half-pair, including concurrent creation.
        _require(counts in ([1, 1], [0, 0]))
        seeded = counts == [1, 1]
        prior = _pair(c, QUOTA, entity, QUOTA, "quota")
    if prior is None:
        return None, policy.AccountQuotaCursor(account_id=request["account_id"],
            quota_subject=request["quota_subject"]), 0
    _require(prior["request"] == request and type(prior["response"]) is dict
             and set(prior["response"]) == {"revision", "cursor"})
    revision = prior["response"]["revision"]
    _require(type(revision) is int and revision >= (0 if seeded else 1))
    try:
        cursor = policy.AccountQuotaCursor.model_validate(prior["response"]["cursor"])
    except ValidationError:
        _require(False)
    _require(cursor.account_id == request["account_id"]
             and cursor.quota_subject == request["quota_subject"])
    return prior, cursor, revision


def _ledger(c, scope, request, cursor, quota_revision):
    prior = _pair(c, scope.principal_id, scope.project_id, KIND, scope.trial_key)
    if prior is None:
        return None, policy.Ledger(scope=scope, account_id=request["account_id"]), 0
    _require(prior["request"] == request and type(prior["response"]) is dict
             and set(prior["response"]) == {"revision", "quota_revision", "ledger"})
    body = prior["response"]
    _require(type(body["revision"]) is int and body["revision"] >= 1
             and type(body["quota_revision"]) is int
             and 1 <= body["quota_revision"] <= quota_revision)
    try:
        ledger = policy._ledger(policy.Ledger.model_validate_json(json.dumps(body["ledger"])))
    except (ValidationError, ValueError, TypeError):
        _require(False)
    _require(ledger.scope == scope and ledger.account_id == request["account_id"]
             and (not ledger.slots or cursor.last_reserved_at is not None
                  and cursor.last_reserved_at >= ledger.slots[-1].reserved_at))
    return prior, ledger, body["revision"]


def _receipt(state, cursor, revision, quota_revision, *, duplicate=False, changed=False):
    return Receipt(ledger=state, quota=cursor, revision=revision, quota_revision=quota_revision,
                   duplicate=duplicate, changed=changed)


def _history_anchor(c, user, scope, request):
    # Scalar ownership precedes cursor reads; no ledger lock-order inversion.
    anchors = c.execute(select(rows.c.kind, rows.c.request_fingerprint).where(
        rows.c.principal_id == user, rows.c.app_id == scope.project_id,
        rows.c.request_key == scope.trial_key,
        rows.c.kind.in_([KIND, KIND + "_seal"]))).mappings().all()
    _require(len(anchors) == 2 and {a["kind"] for a in anchors} == {KIND, KIND + "_seal"}
             and all(a["request_fingerprint"] == fingerprint(request) for a in anchors),
             "OUTCOME_UNKNOWN")


def read(store, user, contract, key, account_id):
    """Owned metadata only; no seed, recovery action, automatic mark or send."""
    with store.tx() as c:
        _, scope, request, quota_request, entity = _context(store, c, user, contract, key, account_id)
        _history_anchor(c, user, scope, request)
        _, cursor, quota_revision = _quota(c, quota_request, entity, create=False)
        _, state, revision = _ledger(c, scope, request, cursor, quota_revision)
        return _receipt(state, cursor, revision, quota_revision)


def _persist(c, scope, request, quota_request, entity, previous, quota_previous,
             transition, revision, quota_revision):
    _cas_pair(c, scope.principal_id, scope.project_id, KIND, scope.trial_key, previous,
        _snapshot(request, dict(revision=revision + 1, quota_revision=quota_revision + 1,
                               ledger=transition.ledger.model_dump(mode="json"))))
    _cas_pair(c, QUOTA, entity, QUOTA, "quota", quota_previous,
        _snapshot(quota_request, dict(revision=quota_revision + 1,
                                     cursor=transition.quota.model_dump(mode="json"))))


def _apply_in_transaction(store, c, user, contract, key, identity, wire, source, expected_revision, operation, outcome=None):
    _require(c.in_transaction(), "PERMISSION_DENIED")
    _require(type(expected_revision) is int and expected_revision >= 0)
    item = policy._typed(identity, policy.ReservationIdentity)
    supplied = policy._typed(source, policy.SourceVerificationResult)
    received = None if outcome is None else policy._typed(outcome, policy.Outcome)
    _require(operation in ("reserve", "record_attempt", "settle"))
    _require((operation == "settle") == (received is not None))
    original, scope, request, quota_request, entity = _context(
        store, c, user, contract, key, item.account_id)
    quota_previous, cursor, quota_revision = _quota(c, quota_request, entity, create=operation == "reserve")
    previous, state, revision = _ledger(c, scope, request, cursor, quota_revision)
    # Full original owner/scope/wire binding precedes every history shortcut.
    policy._bound(store, c, user, original, key, state, cursor, item, wire)
    slot = next((s for s in state.slots if s.identity.attempt_id == item.attempt_id), None)
    if slot is not None:
        _require(slot.identity == item)
        duplicate = (operation == "reserve" or operation == "record_attempt" and slot.attempted
                     or operation == "settle" and slot.settlement == received)
        if duplicate:
            return _receipt(state, cursor, revision, quota_revision, duplicate=True)
    _require(revision == expected_revision)
    _require(operation == "reserve" or previous is not None)
    if operation == "reserve":
        result = policy.reserve(store, c, user, original, key, state, cursor, item, wire, supplied)
    elif operation == "record_attempt":
        result = policy.record_attempt(store, c, user, original, key, state, cursor, item, wire, supplied)
    else:
        result = policy.settle(store, c, user, original, key, state, cursor, item, wire, supplied, received)
    _persist(c, scope, request, quota_request, entity, previous, quota_previous,
             result, revision, quota_revision)
    if operation != "settle":
        # Account locking/CAS work cannot renew a stale context or deadline.
        policy._fresh(store, c, user, original, key, result.ledger, item, supplied)
    return _receipt(result.ledger, result.quota, revision + 1, quota_revision + 1, changed=True)


def _apply(store, user, contract, key, identity, wire, source, expected_revision, operation, outcome=None):
    with store.tx() as c:
        return _apply_in_transaction(store, c, user, contract, key, identity, wire, source,
                                     expected_revision, operation, outcome)


def reserve(store, user, contract, key, identity, wire, source, *, expected_revision):
    return _apply(store, user, contract, key, identity, wire, source, expected_revision, "reserve")


def record_attempt(store, user, contract, key, identity, wire, source, *, expected_revision):
    return _apply(store, user, contract, key, identity, wire, source, expected_revision, "record_attempt")


def settle(store, user, contract, key, identity, wire, source, outcome, *, expected_revision):
    return _apply(store, user, contract, key, identity, wire, source, expected_revision, "settle", outcome)
