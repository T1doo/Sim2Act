"""One-level extraction from independently checked synthetic PREVIEW task receipts.

Never accepts an F1 Run, never infers semantic acceptance or publishes a release.
"""

import copy
import csv
import io
from decimal import Decimal, InvalidOperation

from pydantic import Field
from sqlalchemy import insert, select

from .apps import authorize_source, csv_candidate, load_draft, persist_csv_candidate
from .contracts import Limits, Strict, validate_value
from .db import app_drafts, app_previews, fingerprint, preview_extractions
from .errors import DomainError
from .tools import authorized_read


class ExtractionInput(Strict):
    expected_source_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    name: str = Field(min_length=1, max_length=200)
    request_key: str = Field(min_length=1, max_length=100)


def exact_sum_oracle(content, column, output):
    """Independent row parser and integer-scaled sum; no tool execution/cache reuse.

    Extra extraction bound: <=1000 digits/exponent per number; rounded sums refused.
    """
    try:
        rows = list(csv.reader(io.StringIO(content)))
        header = rows[0]
        if not header or len(header) != len(set(header)) or column not in header:
            raise ValueError("header")
        data = [r for r in rows[1:] if r]  # Same blank-line semantics as CSV reader.
        if len(data) > 1000 or any(len(r) != len(header) for r in data):
            raise ValueError("rows")
        values = [Decimal(r[header.index(column)]) for r in data]
        if any(
            not v.is_finite()
            or len(v.as_tuple().digits) > 1000
            or abs(int(v.as_tuple().exponent)) > 1000
            for v in values
        ):
            raise ValueError("decimal bound")
        scale = min([int(v.as_tuple().exponent) for v in values] + [0])
        total = 0
        for value in values:
            parts = value.as_tuple()
            coefficient = int("".join(map(str, parts.digits))) * (-1 if parts.sign else 1)
            total += coefficient * 10 ** (int(parts.exponent) - scale)
        expected = Decimal((int(total < 0), tuple(map(int, str(abs(total)))), scale))
        if output["count"] != len(data) or Decimal(output["sum"]) != expected:
            raise ValueError("oracle mismatch")
    except (IndexError, KeyError, TypeError, ValueError, InvalidOperation, csv.Error) as exc:
        raise DomainError("VERIFICATION_FAILED", "源回执未通过独立精确数值核查") from exc


def verified_source(store, c, user, preview_id, platform_limits, *, lock=False):
    row = (
        c.execute(
            select(app_previews).where(
                app_previews.c.id == preview_id, app_previews.c.principal_id == user
            )
        )
        .mappings()
        .first()
    )
    if not row:
        raise DomainError("PERMISSION_DENIED")
    raw = c.execute(select(app_drafts.c.candidate).where(app_drafts.c.id == row["app_id"])).scalar()
    if raw and ("extraction" in raw or "task_proof" in raw):
        raise DomainError("UNSUPPORTED_CAPABILITY", "仅支持一层提取，不递归归纳候选")
    draft, manifest, _, _ = load_draft(store, c, user, row["app_id"], platform_limits, lock=lock)
    # load_draft enforces the complete audited fixed wiring for both paths.
    if row["status"] != "SUCCEEDED" or row["error"] is not None or not row["output"]:
        raise DomainError("VERIFICATION_FAILED", "只接受已成功且可核查的PREVIEW回执")
    validate_value(manifest.output_schema, row["output"], "source_output")
    if (
        not isinstance(row["input"], dict)
        or set(row["input"]) != {"column"}
        or not isinstance(row["input"]["column"], str)
        or row["fingerprint"]
        != fingerprint({"candidate": draft["fingerprint"], "input": row["input"]})
    ):
        raise DomainError("VERSION_CONFLICT", "源回执输入或候选版本不一致")
    rid = manifest.data_bindings[0].resource_ref
    source = authorized_read(
        store,
        c,
        user,
        draft["runtime_id"],
        draft["project_id"],
        "resource.read",
        {"resource_id": rid},
    )
    expected_output = authorized_read(
        store,
        c,
        user,
        draft["runtime_id"],
        draft["project_id"],
        "data.aggregate_csv",
        {"resource_id": rid, **row["input"]},
    )
    if expected_output != row["output"]:
        raise DomainError("VERIFICATION_FAILED", "源回执与可信工具回读不一致")
    exact_sum_oracle(source["content"], row["input"]["column"], row["output"])
    evidence = {
        "kind": "verified_preview_task",
        "namespace": "PREVIEW",
        "preview_id": preview_id,
        "source_app_id": draft["id"],
        "source_candidate_fingerprint": draft["fingerprint"],
        "source_receipt": dict(row),
        "source_receipt_fingerprint": fingerprint(dict(row)),
        "source_resource_id": rid,
        "source_hash": source["hash"],
        "tool": {"ref": "data.aggregate_csv", "version": "1", "effect": "read"},
        "oracle": "csv.exact_integer_sum.v1",
        "goal_acceptance": "NOT_RUN",
        "parameter_scope": {"creation": ["new_csv_resource"], "runtime": ["column"]},
        "extractor": "TRUSTED_PREVIEW_CSV_SUM.v1",
        "model_requests": 0,
        "source_goal": draft["candidate"]["goal"],
        "source_generation": draft["candidate"].get("generation"),
    }
    return draft, manifest, evidence


def extracted_template(source_draft, source_manifest, evidence, rid, source_hash, aid, action_id):
    candidate = csv_candidate(
        rid, source_hash, "", Limits(**source_manifest.runtime_limits.model_dump())
    )
    candidate["manifest"].update(
        app_id=aid,
        origin="task_run",
        goal_ref=source_manifest.goal_ref,
        source_run_ref=evidence["preview_id"],
    )
    candidate["actions"][0]["action_id"] = action_id
    candidate["manifest"]["action_bindings"][0]["action_id"] = action_id
    candidate["goal"] = copy.deepcopy(source_draft["candidate"]["goal"])
    candidate["extraction"] = {**evidence, "target_resource_id": rid, "target_hash": source_hash}
    return candidate


def extract_preview(store, user, pid, body, platform_limits):
    with store.tx() as c:
        source_draft, manifest, evidence = verified_source(
            store, c, user, pid, platform_limits, lock=True
        )
        if source_draft["fingerprint"] != body["expected_source_fingerprint"]:
            raise DomainError("VERSION_CONFLICT", "来源候选版本已变化")
        project = store.own_project(c, user, source_draft["project_id"])
        rid = body["resource_id"]
        authorize_source(store, c, user, project, rid, project["runtime_id"])
        target = authorized_read(
            store,
            c,
            user,
            project["runtime_id"],
            project["id"],
            "resource.read",
            {"resource_id": rid},
        )
        if target["format"] != "csv" or target["hash"] == evidence["source_hash"]:
            raise DomainError("INVALID_INPUT", "请选择同项目内容不同的新CSV，不重放旧材料")
        fp = fingerprint(
            {
                **body,
                "source_receipt": evidence["source_receipt_fingerprint"],
                "target_hash": target["hash"],
            }
        )
        old = (
            c.execute(
                select(preview_extractions).where(
                    preview_extractions.c.preview_id == pid,
                    preview_extractions.c.principal_id == user,
                    preview_extractions.c.request_key == body["request_key"],
                )
            )
            .mappings()
            .first()
        )
        if old:
            if old["request_fingerprint"] != fp:
                raise DomainError("VERSION_CONFLICT", "请求键已绑定其他提取输入")
            load_draft(store, c, user, old["app_id"], platform_limits)
            return {"id": old["app_id"], "state": "PREVIEW_ONLY", "publishable": False}
        candidate = csv_candidate(rid, target["hash"], "", manifest.runtime_limits)
        candidate = extracted_template(
            source_draft,
            manifest,
            evidence,
            rid,
            target["hash"],
            candidate["manifest"]["app_id"],
            candidate["actions"][0]["action_id"],
        )
        result = persist_csv_candidate(c, project, body["name"], rid, candidate, platform_limits)
        c.execute(
            insert(preview_extractions).values(
                preview_id=pid,
                principal_id=user,
                request_key=body["request_key"],
                request_fingerprint=fp,
                app_id=result["id"],
                snapshot=candidate["extraction"],
            )
        )
        return result


def validate_extraction(store, c, user, draft, platform_limits):
    origin = draft["candidate"]["extraction"]
    saved = (
        c.execute(
            select(preview_extractions).where(
                preview_extractions.c.app_id == draft["id"],
                preview_extractions.c.principal_id == user,
            )
        )
        .mappings()
        .first()
    )
    if not saved or saved["snapshot"] != origin:
        raise DomainError("VERSION_CONFLICT", "提取来源快照不一致")
    source, manifest, evidence = verified_source(
        store, c, user, saved["preview_id"], platform_limits
    )
    if source["project_id"] != draft["project_id"]:
        raise DomainError("PERMISSION_DENIED")
    target = authorized_read(
        store,
        c,
        user,
        draft["runtime_id"],
        draft["project_id"],
        "resource.read",
        {"resource_id": origin["target_resource_id"]},
    )
    if target["hash"] != origin["target_hash"] or target["format"] != "csv":
        raise DomainError("VERSION_CONFLICT", "新材料版本已变化")
    expected = extracted_template(
        source,
        manifest,
        evidence,
        origin["target_resource_id"],
        origin["target_hash"],
        draft["id"],
        draft["candidate"]["actions"][0]["action_id"],
    )
    if expected != draft["candidate"]:
        raise DomainError("VERSION_CONFLICT", "提取声明、来源或版本已变化")
