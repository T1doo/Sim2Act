"""Permanent owner-authorized closure of an unused P-B extraction key.

Browser identity hashes describe the owner's original intent, not authorization.
Only the existing source gates and the shared project transaction grant access.
"""

from typing import Literal

from pydantic import Field
from sqlalchemy import or_, select

from .contracts import Strict
from .db import app_drafts, fingerprint, grants, principals, task_extractions
from .db import delivery_graph_requests as journal
from .delivery_graph_apps import HASH, controlled
from .errors import DomainError
from .pa_material_bindings import Metadata
from .text_logic_reuse import KEY, pair, remember, require

KIND = "pb_natural_spec_terminal"
VERSION = "pb-natural-spec-extraction-terminal.v1"
CONSENT = "CLOSE_ONLY_THIS_UNACCEPTED_PB_EXTRACTION_KEY"
MAX = 64


class RecoveryIdentity(Strict):
    namespace: Literal["pb-natural-extraction-recovery.v1"]
    principal_id: str = Field(pattern=r"^user_[a-f0-9]{32}$")
    project_id: str = Field(pattern=r"^proj_[a-f0-9]{32}$")
    source_app_id: str = Field(pattern=r"^app_[a-f0-9]{32}$")
    source_instance_id: str = Field(pattern=r"^iinstance_[a-f0-9]{32}$")
    source_run_id: str = Field(pattern=r"^run_[a-f0-9]{32}$")
    source_app_run_id: str = Field(pattern=r"^iapprun_[a-f0-9]{32}$")
    source_release_id: str = Field(pattern=r"^irelease_[a-f0-9]{32}$")
    source_release_fingerprint: str = Field(pattern=HASH)
    source_result_version: int = Field(strict=True, ge=1)
    request_key: str = Field(pattern=KEY)
    request_fingerprint: str = Field(pattern=HASH)
    review_fingerprint: str = Field(pattern=HASH)
    candidate_fingerprint: str = Field(pattern=HASH)
    app_id: str = Field(pattern=r"^app_[a-f0-9]{32}$")
    runtime_id: str = Field(pattern=r"^appruntime_[a-f0-9]{32}$")
    source_proof_fingerprint: str = Field(pattern=HASH)


class CloseInput(Strict):
    identity: RecoveryIdentity
    consent: Literal["CLOSE_ONLY_THIS_UNACCEPTED_PB_EXTRACTION_KEY"]


def _headers(rid, key):
    # Even a partial/foreign malformed terminal blocks a new extraction. It
    # cannot, by itself, authorize a CLOSED receipt or browser forget operation.
    snapshot = journal.c.snapshot
    anchors = or_((journal.c.app_id == rid) & (journal.c.request_key == key),
        (snapshot["request"]["identity"]["source_run_id"].as_string() == rid)
            & (snapshot["request"]["identity"]["request_key"].as_string() == key),
        (snapshot["response"]["source_run_id"].as_string() == rid)
            & (snapshot["response"]["request_key"].as_string() == key),
        (snapshot["response"]["identity"]["source_run_id"].as_string() == rid)
            & (snapshot["response"]["identity"]["request_key"].as_string() == key))
    return select(journal.c.principal_id, journal.c.app_id, journal.c.kind,
        journal.c.request_key).where(anchors, journal.c.kind.in_([KIND, KIND + "_seal"]))


def fenced(c, rid, key):
    return c.execute(_headers(rid, key).limit(1)).first() is not None


def _unknown(message):
    raise DomainError("OUTCOME_UNKNOWN", message)


def _identity_scope(identity, user, pid, rid, key):
    require(identity.principal_id == user and identity.project_id == pid
        and identity.source_run_id == rid and identity.request_key == key,
        "Extraction closure identity differs from its authorized scope")
    require(identity.app_id != identity.source_app_id)


def _source(store, c, user, pid, rid, key, body, limits):
    from . import pb_natural_specs as pb

    binding, proof = pb.source(store, c, user, pid, rid, limits)
    identity = body.identity
    _identity_scope(identity, user, pid, rid, key)
    expected = {"source_app_id": "source_app_id", "source_instance_id": "instance_id",
        "source_run_id": "source_run_id", "source_app_run_id": "app_run_id",
        "source_release_id": "release_id", "source_release_fingerprint": "release_fingerprint",
        "source_result_version": "result_version"}
    require(all(getattr(identity, field) == proof[name] for field, name in expected.items())
        and identity.source_proof_fingerprint == fingerprint(proof)
        and identity.runtime_id != binding["draft"]["runtime_id"],
        "Original successful source no longer matches this closure identity")


def _absent(store, c, user, pid, rid, key, identity):
    """No absence from a missing marker alone; independent remnants also block.

    Related identities are discovered using scalar metadata only. If another
    accepted key must be checked, its existing target/source gate precedes its
    full request pair. An inaccessible sibling conservatively blocks closure.
    """
    from . import pa_spec_apps as spec
    from . import pb_natural_specs as pb

    markers = c.execute(select(task_extractions.c.app_id, task_extractions.c.principal_id,
        task_extractions.c.request_key, task_extractions.c.request_fingerprint)
        .where(task_extractions.c.task_id == rid)
        .limit(MAX + 1)).mappings().all()
    if len(markers) > MAX:
        _unknown("Extraction identity scan budget exhausted")
    if any(row["request_key"] == key for row in markers):
        raise DomainError("VERSION_CONFLICT", "Accepted extraction cannot be closed; read its original key")
    if (c.execute(select(app_drafts.c.id).where(app_drafts.c.id == identity.app_id)).first()
            or c.execute(select(principals.c.id).where(principals.c.id == identity.runtime_id)).first()):
        _unknown("Prospective application or runtime already exists")
    kinds = [pb.META, pb.META + "_seal", pb.EXTRACT, pb.EXTRACT + "_seal"]
    # Source pointers from each independent journal half, without reading any
    # name, recipe, target Goal, candidate, material or result body at discovery.
    links = c.execute(select(journal.c.app_id, journal.c.principal_id,
        journal.c.kind, journal.c.request_key).where(journal.c.kind.in_(kinds), or_(
            journal.c.snapshot["request"]["source_run_id"].as_string() == rid,
            journal.c.snapshot["request"]["review"]["source_run_id"].as_string() == rid,
            journal.c.snapshot["response"]["source_run_id"].as_string() == rid))
        .limit(4 * MAX + 1)).mappings().all()
    if len(links) > 4 * MAX:
        _unknown("Extraction journal scan budget exhausted")
    if any(row["principal_id"] != user for row in links):
        _unknown("Conflicting extraction journal ownership")
    exact = c.execute(select(journal.c.app_id).where(
        journal.c.kind.in_([pb.EXTRACT, pb.EXTRACT + "_seal"]), or_(
            (journal.c.snapshot["request"]["review"]["source_run_id"].as_string() == rid)
                & (journal.c.snapshot["request"]["review"]["request_key"].as_string() == key),
            (journal.c.snapshot["response"]["source_run_id"].as_string() == rid)
                & (journal.c.snapshot["response"]["request_key"].as_string() == key)))).first()
    if exact or any(row["request_key"] == key and row["kind"] in [pb.EXTRACT, pb.EXTRACT + "_seal"]
            for row in links):
        _unknown("Independent accepted-key evidence remains")
    apps = c.execute(select(app_drafts.c.id).where(app_drafts.c.project_id == pid, or_(
        app_drafts.c.candidate["spec_task"]["source_run_id"].as_string() == rid,
        app_drafts.c.candidate["manifest"]["source_run_ref"].as_string() == rid))
        .limit(MAX + 1)).scalars().all()
    related = set(apps) | {row["app_id"] for row in markers} | {row["app_id"] for row in links}
    if len(related) > MAX:
        _unknown("Related extraction identity scan budget exhausted")
    for aid in sorted(related):
        matches = [row for row in markers if row["app_id"] == aid]
        if len(matches) != 1 or matches[0]["principal_id"] != user:
            _unknown("Related application lost its independent extraction identity")
        marker = matches[0]
        try:
            headers = c.execute(select(journal.c.principal_id, journal.c.kind, journal.c.request_key)
                .where(journal.c.app_id == aid, journal.c.kind.in_(kinds)).limit(5)).all()
            require(len(headers) == 4 and set(headers) == {
                (user, pb.META, "scope"), (user, pb.META + "_seal", "scope"),
                (user, pb.EXTRACT, marker["request_key"]),
                (user, pb.EXTRACT + "_seal", marker["request_key"])})
            actual = c.execute(select(app_drafts.c.project_id, app_drafts.c.runtime_id,
                app_drafts.c.fingerprint).where(app_drafts.c.id == aid)).mappings().first()
            require(actual is not None and actual["project_id"] == pid)
            # Preserve the old target READ/SAVE gate before complete wire reads.
            require(spec.scope_gate(store, c, user, aid))
            marker_snapshot = c.execute(select(task_extractions.c.snapshot).where(
                task_extractions.c.task_id == rid, task_extractions.c.app_id == aid,
                task_extractions.c.principal_id == user,
                task_extractions.c.request_key == marker["request_key"])).scalar_one()
            meta, meta_seal = pair(c, user, aid, pb.META, "scope", Metadata)
            original, frozen = pair(c, user, aid, pb.EXTRACT, marker["request_key"], pb.ExtractInput)
            require(meta.model_dump() == meta_seal and meta.principal_id == user
                and meta.project_id == pid and meta.source_run_id == rid and meta.app_id == aid
                and actual["project_id"] == pid and actual["runtime_id"] == meta.runtime_id
                and original.review.source_run_id == rid
                and original.review.request_key == marker["request_key"] != key
                and fingerprint(original.model_dump()) == marker["request_fingerprint"]
                and frozen == marker_snapshot and frozen["app_id"] == aid
                and frozen["principal_id"] == user and frozen["project_id"] == pid
                and frozen["source_run_id"] == rid and frozen["request_key"] == marker["request_key"]
                and frozen["request_fingerprint"] == marker["request_fingerprint"]
                and frozen["runtime_id"] == meta.runtime_id
                and frozen["candidate_fingerprint"] == actual["fingerprint"])
        except (DomainError, ValueError, KeyError, TypeError) as exc:
            raise DomainError("OUTCOME_UNKNOWN", "Related accepted extraction cannot be safely classified") from exc
    # A suspicious project-local orphan cannot be treated as proof of absence.
    # Name/Grant hints only reject; they never prove ownership or completeness.
    orphan = c.execute(select(principals.c.id).join(grants,
        grants.c.principal_id == principals.c.id).where(grants.c.project_id == pid,
        principals.c.name == "P-B natural spec target runtime",
        ~select(app_drafts.c.id).where(app_drafts.c.runtime_id == principals.c.id).exists())
        .limit(1)).first()
    if orphan:
        _unknown("Unclassified project runtime evidence remains")


def _receipt(body):
    identity = body.identity.model_dump()
    value = dict(namespace=VERSION, status="CLOSED_NOT_ACCEPTED", acceptance="NOT_ACCEPTED",
        principal_id=identity["principal_id"], project_id=identity["project_id"],
        source_run_id=identity["source_run_id"], request_key=identity["request_key"], identity=identity,
        request_fingerprint=identity["request_fingerprint"],
        close_request_fingerprint=fingerprint(body.model_dump()), new_model_requests=0,
        project_writes=0, metadata_writes=2, formal_publication_enabled=False)
    return {**value, "receipt_fingerprint": fingerprint(value)}


@controlled
def read(store, c, user, pid, rid, key):
    from . import pb_natural_specs as pb

    pb.source_gate(store, c, user, pid, rid)
    headers = c.execute(_headers(rid, key).limit(3)).all()
    if not headers:
        return None
    require(len(headers) == 2 and set(headers) == {
        (user, rid, KIND, key), (user, rid, KIND + "_seal", key)},
        "Permanent extraction closure headers differ or are incomplete")
    body, frozen = pair(c, user, rid, KIND, key, CloseInput)
    _identity_scope(body.identity, user, pid, rid, key)
    _absent(store, c, user, pid, rid, key, body.identity)
    require(frozen == _receipt(body), "Permanent extraction closure metadata differs")
    return frozen


@controlled
def close(store, user, pid, rid, key, body, limits):
    with store.tx() as c:
        store.lock_project(c, user, pid)
        _source(store, c, user, pid, rid, key, body, limits)
        previous = read(store, c, user, pid, rid, key)
        if previous:
            require(previous == _receipt(body), "Original closure intent differs")
            return previous
        _absent(store, c, user, pid, rid, key, body.identity)
        keys = c.execute(select(journal.c.request_key).where(journal.c.app_id == rid,
            journal.c.kind.in_([KIND, KIND + "_seal"])).distinct().limit(MAX + 1)).all()
        if len(keys) >= MAX:
            raise DomainError("BUDGET_EXHAUSTED", "Finite extraction closure metadata capacity exhausted")
        value = _receipt(body)
        remember(c, user, rid, KIND, key, body, value)
        # Recheck current source after both metadata writes; no target replay.
        _source(store, c, user, pid, rid, key, body, limits)
        return read(store, c, user, pid, rid, key)
