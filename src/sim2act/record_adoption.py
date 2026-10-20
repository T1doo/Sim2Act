"""One explicit compatible v1 -> v2 adoption; business history stays immutable.

Only instances created by this exact software are supported. Approval and paired
journal receipts bind the switch; no identity cache, data migration or new grant.
"""

import copy
from typing import Literal

from fastapi import Depends
from pydantic import Field
from sqlalchemy import select, update

from . import lifecycle
from . import local_record_apps as r
from .db import fingerprint
from .errors import DomainError

VERSION = "local-record-release-adoption.v1"
PREPARE = VERSION + ".prepare"
COMMITTED = VERSION + ".committed"


class Adoption(r.CommandBase):
    target_release_id: str = Field(min_length=1, max_length=100)
    target_release_fingerprint: str = Field(pattern=r.HASH)
    consent: Literal["ADOPT_V2_PRESERVE_RECORDS_AND_HISTORY"]


def proposal(c, user, iid, key):
    saved = r.pair(c, user, iid, PREPARE, key)
    if not saved:
        raise DomainError("OUTCOME_UNKNOWN", "Original adoption proposal not found")
    body = Adoption.model_validate(saved["request"]).model_dump()
    r.require(body == saved["request"] and body["request_key"] == key)
    a = c.execute(select(r.approvals).where(r.approvals.c.id == saved["response"]["id"],
        r.approvals.c.principal_id == user)).mappings().first()
    r.require(a is not None)
    a = dict(a)
    p = a["payload"]
    r.require(set(p) == {"snapshot", "approval_id", "principal_id", "project_id", "kind", "expires_at"}
        and a["kind"] == p["kind"] == VERSION and a["id"] == p["approval_id"]
        and p["principal_id"] == user and p["project_id"] == a["project_id"]
        and p["expires_at"] == a["expires_at"]
        and fingerprint(p) == a["fingerprint"] == saved["response"]["fingerprint"])
    return body, a


def snapshot(i, source, target, body, prefix):
    r.require("preview_scope" not in i and i["revision"] == body["expected_revision"] == 1
        and i["data_version"] == body["expected_data_version"]
        and i["release_id"] == source["id"]
        and source["fingerprint"] == body["expected_release_fingerprint"]
        and target["id"] == body["target_release_id"]
        and target["fingerprint"] == body["target_release_fingerprint"]
        and source["id"] != target["id"], "Adoption CAS or source differs")
    for rel in (source, target):
        s = rel["snapshot"]
        r.require(s["app_id"] == i["source_app_id"] and s["principal_id"] == i["principal_id"]
            and s["project_id"] == i["project_id"] and s["runtime_id"] == i["runtime_id"])
    base = source["snapshot"]["definition"]
    r.require(base["typed_mapping_version"] == r.MAPPING and not r.allows_content_edits(base)
        and r.release_definition(base, dict(content_edits="OPEN_RECORD_CONTENT_V1")) == target["snapshot"]["definition"],
        "Only the exact compatible OPEN content correction Release is supported")
    return dict(namespace=VERSION, instance_id=i["id"], principal_id=i["principal_id"],
        project_id=i["project_id"], runtime_id=i["runtime_id"], app_id=i["source_app_id"],
        source_release_id=source["id"], source_release_fingerprint=source["fingerprint"],
        target_release_id=target["id"], target_release_fingerprint=target["fingerprint"],
        previous_revision=1, revision=2, data_version=i["data_version"], prefix_fingerprint=prefix)


def lineage(store, c, user, i, source, target):
    keys = c.execute(select(r.journal.c.request_key).where(r.journal.c.app_id == i["id"],
        r.journal.c.principal_id == user, r.journal.c.kind.in_([COMMITTED, COMMITTED + "_seal"]))).scalars().all()
    if not keys:
        r.require(i["revision"] == 1 and source["id"] == target["id"], "Instance adoption receipt missing")
        return None
    r.require(len(keys) == 2 and len(set(keys)) == 1 and i["revision"] == 2)
    saved = r.pair(c, user, i["id"], COMMITTED, keys[0])
    body, a = proposal(c, user, i["id"], keys[0])
    s = a["payload"]["snapshot"]
    r.require(a["consumed"] and a["project_id"] == i["project_id"]
        and saved["request"] == dict(fingerprint=a["fingerprint"])
        and saved["response"] == dict(approval_id=a["id"], fingerprint=a["fingerprint"], snapshot=s)
        and type(s["data_version"]) is int and 0 <= s["data_version"] <= i["data_version"]
        and isinstance(s["prefix_fingerprint"], str) and len(s["prefix_fingerprint"]) == 64)
    # Rebuild the frozen metadata, without reading business cells or recursing
    # into projection. Projection below separately rechecks the frozen prefix.
    original = dict(i, release_id=source["id"], revision=1, data_version=s["data_version"])
    source_row = dict(source, snapshot=c.execute(select(r.releases.c.snapshot).where(r.releases.c.id == source["id"])).scalar_one())
    target_row = dict(target, snapshot=c.execute(select(r.releases.c.snapshot).where(r.releases.c.id == target["id"])).scalar_one())
    r.require(snapshot(original, source_row, target_row, body, s["prefix_fingerprint"]) == s)
    return copy.deepcopy(s)


def historical_view(i, release_id):
    s = i.get("release_adoption")
    if not s:
        r.require(release_id == i["release_id"])
        return i
    r.require(release_id in {s["source_release_id"], s["target_release_id"]})
    return dict(i, release_id=release_id, revision=1 if release_id == s["source_release_id"] else 2)


def event_view(i, version):
    s = i.get("release_adoption")
    return historical_view(i, s["source_release_id"] if s and version <= s["data_version"] else i["release_id"])


def binding_boundary(i, binding):
    r.require(binding["expected_revision"] == i["revision"]
        and type(binding["expected_data_version"]) is int and 0 <= binding["expected_data_version"] <= i["data_version"])
    s = i.get("release_adoption")
    if s:
        boundary = s["data_version"]
        r.require(binding["expected_data_version"] <= boundary if i["revision"] == 1
            else binding["expected_data_version"] >= boundary, "Run outside its historical Release interval")


def verify_prefix(i, records, history):
    s = i.get("release_adoption")
    if s and len(history) == s["data_version"]:
        r.require(fingerprint(dict(records=list(records.values()), history=history)) == s["prefix_fingerprint"],
            "Frozen pre-adoption collection changed")


def request_state(store, c, user, iid, key, limits):
    i, _ = r.instance_header(store, c, user, iid)
    r.projection(store, c, user, i, limits)
    body, a = proposal(c, user, iid, key)
    r.require(a["project_id"] == i["project_id"] and a["payload"]["snapshot"]["instance_id"] == iid)
    done = r.pair(c, user, iid, COMMITTED, key)
    r.require(bool(a["consumed"]) == bool(done))
    return dict(namespace=r.VERSION, instance_id=iid, app_id=i["source_app_id"], project_id=i["project_id"],
        principal_id=user, request_key=key, request_fingerprint=fingerprint(body), request=body,
        approval=a, adoption=done["response"]["snapshot"] if done else None, formal_publication_enabled=False)


def prepare(store, user, iid, body, limits):
    with store.tx() as c:
        i, _ = r.instance_header(store, c, user, iid)
        records, history = r.projection(store, c, user, i, limits)
        r.no_pending(c, iid)
        old = r.pair(c, user, iid, PREPARE, body["request_key"])
        if old:
            r.require(old["request"] == body)
        else:
            source = r.read_release(store, c, user, i["release_id"], limits)
            target = r.read_release(store, c, user, body["target_release_id"], limits)
            frozen = snapshot(i, source, target, body, fingerprint(dict(records=records, history=history)))
            a = lifecycle.new_approval(c, user, i["project_id"], VERSION, dict(snapshot=frozen))
            r.remember(c, user, iid, PREPARE, body["request_key"], body, dict(id=a["id"], fingerprint=a["fingerprint"]))
        return request_state(store, c, user, iid, body["request_key"], limits)


def commit(store, user, iid, key, body, limits):
    with store.tx() as c:
        current = request_state(store, c, user, iid, key, limits)
        r.require(current["approval"]["fingerprint"] == body["fingerprint"])
        if current["adoption"]:
            return current
        original, a = proposal(c, user, iid, key)
        lifecycle.approval(c, user, a["id"], body["fingerprint"], VERSION)
        i, _ = r.instance_header(store, c, user, iid)
        records, history = r.projection(store, c, user, i, limits)
        r.no_pending(c, iid)
        source = r.read_release(store, c, user, i["release_id"], limits)
        target = r.read_release(store, c, user, original["target_release_id"], limits)
        frozen = snapshot(i, source, target, original, fingerprint(dict(records=records, history=history)))
        r.require(frozen == a["payload"]["snapshot"])
        r.require(c.execute(update(r.instances).where(r.instances.c.id == iid,
            r.instances.c.release_id == source["id"], r.instances.c.revision == 1,
            r.instances.c.data_version == original["expected_data_version"]).values(
                release_id=target["id"], revision=2)).rowcount == 1)
        r.require(c.execute(update(r.approvals).where(r.approvals.c.id == a["id"],
            r.approvals.c.consumed.is_(False)).values(consumed=True)).rowcount == 1)
        r.remember(c, user, iid, COMMITTED, key, body,
            dict(approval_id=a["id"], fingerprint=a["fingerprint"], snapshot=frozen))
        return request_state(store, c, user, iid, key, limits)


def mount(app, store, limits, identity):
    user_dependency = Depends(identity)

    @app.post("/api/internal/record-instances/{iid}/release-adoptions", status_code=201)
    def post_adoption(iid: str, body: Adoption, user=user_dependency):
        return prepare(store, user, iid, body.model_dump(), limits)

    @app.get("/api/internal/record-instances/{iid}/release-adoptions/{key}")
    def get_adoption(iid: str, key: str, user=user_dependency):
        with store.tx() as c:
            return request_state(store, c, user, iid, key, limits)

    @app.post("/api/internal/record-instances/{iid}/release-adoptions/{key}/commit")
    def post_commit(iid: str, key: str, body: r.CommitRelease, user=user_dependency):
        return commit(store, user, iid, key, body.model_dump(), limits)
