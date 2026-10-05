"""User-authored goal drafts; immutable versions, no executor or release authority."""

import time
from typing import Annotated

from pydantic import Field
from sqlalchemy import insert, select, update

from .contracts import Strict, resource_id
from .db import fingerprint, goal_card_versions, goal_cards, new_id
from .errors import DomainError
from .tools import authorized_read

Line = Annotated[str, Field(min_length=1, max_length=1000)]


class GoalCardInput(Strict):
    title: str = Field(min_length=1, max_length=200)
    goal: str = Field(min_length=1, max_length=4000)
    known: list[Line] = Field(max_length=16)
    assumptions: list[Line] = Field(max_length=16)
    unresolved: list[Line] = Field(max_length=16)
    constraints: list[Line] = Field(max_length=16)
    acceptance_checks: list[Line] = Field(max_length=16)
    resource_refs: list[str] = Field(max_length=8)


class GoalCardUpdate(GoalCardInput):
    expected_version: int = Field(ge=1)


def snapshot(store, c, user, project, content):
    refs = content["resource_refs"]
    if len(refs) != len(set(refs)):
        raise DomainError("INVALID_INPUT", "材料引用不能重复")
    sources = []
    for rid in refs:
        resource_id(rid)
        source = authorized_read(
            store, c, user, project["runtime_id"], project["id"], "resource.read",
            {"resource_id": rid},
        )
        sources.append({"resource_id": rid, "hash": source["hash"], "format": source["format"]})
    return {"schema_version": "F2-goal-card.v1", "content": content, "resource_snapshots": sources}


def create_card(store, user, pid, content):
    with store.tx() as c:
        project = store.own_project(c, user, pid)
        value = snapshot(store, c, user, project, content)
        cid, fp, now = new_id("goal"), fingerprint(value), time.time()
        c.execute(insert(goal_cards).values(
            id=cid, project_id=pid, title=content["title"], version=1, fingerprint=fp, created_at=now,
        ))
        c.execute(insert(goal_card_versions).values(
            card_id=cid, version=1, snapshot=value, fingerprint=fp, created_at=now,
        ))
    return {"id": cid, "version": 1, "fingerprint": fp, "state": "DRAFT", "executable": False}


def load_card(store, c, user, cid, *, lock=False):
    query = select(goal_cards).where(goal_cards.c.id == cid)
    card = c.execute(query.with_for_update() if lock else query).mappings().first()
    if not card:
        raise DomainError("PERMISSION_DENIED")
    project = store.own_project(c, user, card["project_id"])
    history = c.execute(
        select(goal_card_versions).where(goal_card_versions.c.card_id == cid)
        .order_by(goal_card_versions.c.version.desc()).limit(50)
    ).mappings().all()
    if not history or history[0]["version"] != card["version"] or history[0]["fingerprint"] != card["fingerprint"]:
        raise DomainError("VERSION_CONFLICT", "目标卡版本记录不一致")
    for version in history:
        value = version["snapshot"]
        if fingerprint(value) != version["fingerprint"]:
            raise DomainError("VERSION_CONFLICT", "目标卡历史指纹不一致")
        fresh = snapshot(store, c, user, project, value["content"])
        if fresh != value:
            raise DomainError("VERSION_CONFLICT", "材料版本改变，目标卡需重新建立")
    return card, project, history


def inspect_card(store, user, cid):
    with store.tx() as c:
        card, _, history = load_card(store, c, user, cid)
        return {
            **dict(card), "state": "DRAFT", "executable": False, "publishable": False,
            "content": history[0]["snapshot"]["content"],
            "history": [dict(v) for v in history], "history_limit": 50,
        }


def revise_card(store, user, cid, content, expected_version):
    with store.tx() as c:
        card, project, _ = load_card(store, c, user, cid, lock=True)
        if card["version"] != expected_version:
            raise DomainError("VERSION_CONFLICT", "目标卡已更新，请重新打开后再保存")
        value = snapshot(store, c, user, project, content)
        fp, version, now = fingerprint(value), expected_version + 1, time.time()
        changed = c.execute(update(goal_cards).where(
            goal_cards.c.id == cid, goal_cards.c.version == expected_version,
        ).values(version=version, title=content["title"], fingerprint=fp))
        if changed.rowcount != 1:
            raise DomainError("VERSION_CONFLICT")
        c.execute(insert(goal_card_versions).values(
            card_id=cid, version=version, snapshot=value, fingerprint=fp, created_at=now,
        ))
    return {"id": cid, "version": version, "fingerprint": fp, "state": "DRAFT", "executable": False}


def list_cards(store, user, pid):
    with store.tx() as c:
        store.own_project(c, user, pid)
        rows = c.execute(select(
            goal_cards.c.id, goal_cards.c.title, goal_cards.c.version,
        ).where(goal_cards.c.project_id == pid).order_by(goal_cards.c.created_at.desc())).mappings()
        return {"items": [dict(r) for r in rows], "state": "DRAFT"}
