"""Explicit MOCK template assembly from a frozen user-authored goal version."""

from typing import Literal

from pydantic import Field
from sqlalchemy import insert, select

from .apps import authorize_source, csv_candidate, load_draft, persist_csv_candidate
from .contracts import Limits, Strict, resource_id
from .db import app_drafts, fingerprint, goal_candidate_requests, resources
from .errors import DomainError
from .goals import load_card
from .tools import TOOLS, authorized_read


class GoalCandidateInput(Strict):
    expected_version: int = Field(ge=1)
    resource_id: str
    capability: Literal["csv.sum"]
    request_key: str = Field(min_length=1, max_length=100)


def generate_candidate(store, user, cid, body, platform_limits):
    resource_id(body["resource_id"])
    with store.tx() as c:
        card, project, history = load_card(store, c, user, cid, lock=True)
        fp = fingerprint({"card_id": cid, **{k: v for k, v in body.items() if k != "request_key"}})
        prior = c.execute(select(goal_candidate_requests).where(
            goal_candidate_requests.c.card_id == cid,
            goal_candidate_requests.c.principal_id == user,
            goal_candidate_requests.c.request_key == body["request_key"],
        )).mappings().first()
        if prior:
            if prior["request_fingerprint"] != fp:
                raise DomainError("VERSION_CONFLICT", "请求键已绑定另一个候选输入")
            draft, _, _, _ = load_draft(store, c, user, prior["app_id"], platform_limits)
            return candidate_result(draft["id"], draft["fingerprint"], draft["candidate"]["generation"])
        if card["version"] != body["expected_version"]:
            raise DomainError("VERSION_CONFLICT", "目标卡已更新，请重新打开后创建候选")
        value = history[0]["snapshot"]
        rid = body["resource_id"]
        if rid not in value["content"]["resource_refs"]:
            raise DomainError("PERMISSION_DENIED", "候选只能使用目标卡已绑定材料")
        if body["capability"] != "csv.sum" or "data.aggregate_csv" not in TOOLS:
            raise DomainError("UNSUPPORTED_CAPABILITY")
        authorize_source(store, c, user, project, rid, project["runtime_id"])
        source = authorized_read(store, c, user, project["runtime_id"], project["id"], "resource.read", {"resource_id": rid})
        if source["format"] != "csv":
            raise DomainError("UNSUPPORTED_CAPABILITY", "本轮仅支持已绑定CSV的数值列求和")
        limits = Limits(max_requests=1, max_tools=1, max_repairs=0, max_total_tokens=1, max_output_tokens=1, run_seconds=1)
        candidate = csv_candidate(rid, source["hash"], value["content"]["goal"], limits)
        candidate["manifest"]["goal_ref"] = cid
        candidate["goal"] = value["content"]
        origin = {
            "kind": "goal_card", "goal_card_id": cid, "goal_version": card["version"],
            "goal_fingerprint": card["fingerprint"], "goal_snapshot": value,
            "generator": "MOCK_DETERMINISTIC_CSV_SUM.v1", "model_requests": 0,
            "goal_acceptance": "NOT_RUN", "capability": "csv.sum",
        }
        candidate["generation"] = origin
        result = persist_csv_candidate(c, project, value["content"]["title"], rid, candidate, platform_limits)
        c.execute(insert(goal_candidate_requests).values(
            card_id=cid, principal_id=user, request_key=body["request_key"],
            request_fingerprint=fp, app_id=result["id"],
        ))
        return candidate_result(result["id"], fingerprint(candidate), origin)


def candidate_result(aid, fp, origin):
    return {
        "id": aid, "candidate_fingerprint": fp, "state": "PREVIEW_ONLY", "publishable": False,
        "generator": origin["generator"], "model_requests": 0,
        "goal_card_id": origin["goal_card_id"], "goal_version": origin["goal_version"],
        "goal_acceptance": "NOT_RUN",
    }


def candidate_options(store, user, cid):
    """Authorized source metadata and fixed catalog; listing is not execution authority."""
    with store.tx() as c:
        card, _, history = load_card(store, c, user, cid)
        refs = history[0]["snapshot"]["content"]["resource_refs"]
        materials = c.execute(select(resources.c.id, resources.c.name, resources.c.format)
                              .where(resources.c.id.in_(refs))).mappings().all()
        rows = c.execute(select(app_drafts.c.id, app_drafts.c.name, app_drafts.c.candidate)
                         .join(goal_candidate_requests, goal_candidate_requests.c.app_id == app_drafts.c.id)
                         .where(goal_candidate_requests.c.card_id == cid,
                                goal_candidate_requests.c.principal_id == user)
                         .order_by(app_drafts.c.created_at.desc()).limit(50)).mappings().all()
        capabilities = [{
            "id": "csv.sum", "name": "CSV 数值列求和", "tool_ref": "data.aggregate_csv",
            "version": "1", "effect": "read", "generator": "MOCK_DETERMINISTIC_CSV_SUM.v1",
            "model_requests": 0,
        }] if "data.aggregate_csv" in TOOLS else []
        return {
            "goal_version": card["version"], "materials": [dict(m) for m in materials if m["format"] == "csv"],
            "capabilities": capabilities, "state": "PREVIEW_ONLY", "publishable": False,
            "items": [{"id": r["id"], "name": r["name"], "goal_version": r["candidate"]["generation"]["goal_version"]} for r in rows],
        }
