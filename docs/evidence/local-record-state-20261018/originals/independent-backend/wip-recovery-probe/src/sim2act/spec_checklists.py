"""Fixed synthetic labeled Markdown citation checking with existing artifact effect.

No natural-language inference, client gold, new tools/permissions, F1 Run promotion,
application extraction or external effect. Coordinates refer to the whole resource.
"""

import hashlib
import html
import json
import re
import unicodedata
from typing import Literal

from pydantic import Field, ValidationError, field_validator
from sqlalchemy import insert, select

from .contracts import Strict, strict_json
from .db import fingerprint, new_id, resources, spec_checklist_tasks
from .errors import DomainError
from .tools import authorized_read, write_text_artifact

CHECK = "spec.labeled_citations.v1"
HEADER = re.compile(r"# Spec (synthetic_[a-z][a-z0-9_]{0,63}) v([1-9][0-9]{0,4})")
RULE = re.compile(r"- \[([a-z][a-z0-9_]{0,63})\] (MUST|MUST_NOT) (\S.{0,299})")


class SpecChecklistInput(Strict):
    resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    expected_source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    candidate_json: str = Field(min_length=1, max_length=8000)
    request_key: str = Field(min_length=1, max_length=100)
    synthetic_fixture: Literal[True]

    @field_validator("synthetic_fixture", mode="before")
    @classmethod
    def actual_boolean_marker(cls, value):
        if value is not True:
            raise ValueError("Synthetic marker must be JSON boolean true")
        return value


def source_checklist(source):
    """Parse only fixed explicit labels; never compare against supplied expected gold."""
    content = source["content"]
    if (
        source["format"] != "md"
        or len(content.encode()) > 4096
        or hashlib.sha256(content.encode()).hexdigest() != source["hash"]
        or any(unicodedata.category(ch).startswith("C") and ch != "\n" for ch in content)
    ):
        raise DomainError("INVALID_INPUT", "需要受限 UTF8/LF 合成规范及一致hash")
    lines = content.split("\n")
    if lines[-1] == "":
        lines.pop()  # Coordinates only: hash always binds original bytes including newline.
    header = HEADER.fullmatch(lines[0]) if lines else None
    if not header or len(lines) > 40:
        raise DomainError("INVALID_INPUT", "仅支持synthetic_规范标题及最多40行")
    rules: list[dict] = []
    seen = set()
    for number, line in enumerate(lines[1:], 2):
        if line == "":
            continue
        match = RULE.fullmatch(line)
        if (
            not match
            or match[1] in seen
            or len(rules) >= 16
            or any(x in line for x in ("<", ">", "`", "://", "javascript:", "file:"))
        ):
            raise DomainError("INVALID_INPUT", "未知、重复或不安全的规范行")
        seen.add(match[1])
        rules.append(
            {
                "rule_id": match[1],
                "line_start": number,
                "line_end": number,
                "quote": line,
                "modality": match[2],
                "statement": match[3],
            }
        )
    if not rules:
        raise DomainError("INVALID_INPUT", "至少需要一条显式规范行")
    return {
        "check_version": CHECK,
        "source": {
            "resource_id": source["resource_id"],
            "hash": source["hash"],
            "document_id": header[1],
            "document_version": int(header[2]),
            "coordinate_space": "whole_resource",
            "line_start": 1,
            "line_end": len(lines),
        },
        "rules": rules,
    }


def verify_candidate(source, candidate_json):
    expected = source_checklist(source)
    candidate = strict_json(candidate_json, 16000)
    # Canonical JSON fingerprints retain integer/bool distinctions unlike dict equality.
    if fingerprint(candidate) != fingerprint(expected):
        raise DomainError("VERIFICATION_FAILED", "候选与当前来源逐字引用/完整覆盖不一致")
    return expected


def markdown_view(checklist):
    """Derived safe plain Markdown view; no model template or raw HTML/link markup."""

    def escape(value):
        value = html.escape(value)
        return re.sub(r"([\\`*_{}\[\]()#!|])", r"\\\1", value)

    rows = ["# 合成规范引用检查", "引用/覆盖已核；自然语言语义验收 NOT_RUN", ""]
    for rule in checklist["rules"]:
        rows.append(f"- [ ] 原行 {rule['line_start']}: {escape(rule['quote'])}")
    return "\n".join(rows) + "\n"


def authorized_source(store, c, user, project, rid):
    source = authorized_read(
        store, c, user, project["runtime_id"], project["id"], "resource.read", {"resource_id": rid}
    )
    store.authorize(
        c, user, project["runtime_id"], project["id"], project["id"], "artifact.save_text"
    )
    return source


def public(row):
    return {
        k: row[k]
        for k in ("id", "status", "output", "receipt", "proof", "proof_fingerprint", "error")
    } | {
        "namespace": "LOCAL_SYNTHETIC_SPEC_CHECKLIST",
        "model_requests": 0,
        "semantic_goal_acceptance": "NOT_RUN",
        "publishable": False,
    }


def verify_saved(store, c, user, project, row, source):
    if row["runtime_id"] != project["runtime_id"] or row["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    if source["hash"] != row["source_hash"]:
        raise DomainError("VERSION_CONFLICT", "来源已变化，不复用旧结果")
    request = row["request"]
    try:
        SpecChecklistInput.model_validate(request)
    except ValidationError as exc:
        raise DomainError("VERSION_CONFLICT", "保存请求结构不一致") from exc
    if (
        request["resource_id"] != row["resource_id"]
        or request["expected_source_hash"] != row["source_hash"]
        or request["request_key"] != row["request_key"]
        or request["synthetic_fixture"] is not True
        or fingerprint(request) != row["request_fingerprint"]
    ):
        raise DomainError("VERSION_CONFLICT")
    if row["status"] == "FAILED":
        if (
            any(row[k] is not None for k in ("output", "receipt", "proof", "proof_fingerprint"))
            or not row["error"]
        ):
            raise DomainError("VERIFICATION_FAILED")
        return
    if row["status"] != "SUCCEEDED" or row["error"] is not None:
        raise DomainError("VERIFICATION_FAILED")
    output = row["output"]
    if (
        not isinstance(output, dict)
        or set(output) != {"resource_id", "hash"}
        or not isinstance(output["resource_id"], str)
        or not re.fullmatch(r"res_[a-f0-9]{32}", output["resource_id"])
        or not isinstance(output["hash"], str)
        or not re.fullmatch(r"[a-f0-9]{64}", output["hash"])
    ):
        raise DomainError("VERIFICATION_FAILED", "保存成果指针结构不一致")
    checked = verify_candidate(source, row["request"]["candidate_json"])
    artifact = authorized_read(
        store,
        c,
        user,
        project["runtime_id"],
        project["id"],
        "resource.read",
        {"resource_id": row["output"]["resource_id"]},
    )
    expected_text = json.dumps(checked, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    expected_output = {
        "resource_id": artifact["resource_id"],
        "hash": hashlib.sha256(expected_text.encode()).hexdigest(),
    }
    receipt, proof = evidence(row["id"], project, user, source, checked, expected_output)
    if (
        artifact["content"] != expected_text
        or row["output"] != expected_output
        or row["receipt"] != receipt
        or row["proof"] != proof
        or row["proof_fingerprint"] != fingerprint(proof)
    ):
        raise DomainError("VERIFICATION_FAILED", "保存成果/检查证明不一致")


def evidence(tid, project, user, source, checked, output):
    receipt = {
        "tool_ref": "artifact.save_text",
        "tool_version": "1",
        "effect": "project_write",
        "task_id": tid,
        "status": "VERIFIED",
        "data": output,
        "check_results": [
            {"check": "receipt.readback.v1", "status": "PASS"},
            {"check": CHECK, "status": "PASS"},
        ],
    }
    proof = {
        "kind": "verified_synthetic_labeled_citations",
        "version": 1,
        "task_id": tid,
        "project_id": project["id"],
        "principal_id": user,
        "runtime_id": project["runtime_id"],
        "source_resource_id": source["resource_id"],
        "source_hash": source["hash"],
        "source_metadata": checked["source"],
        "check_version": CHECK,
        "checked_output_fingerprint": fingerprint(checked),
        "artifact": output,
        "model_requests": 0,
        "semantic_goal_acceptance": "NOT_RUN",
        "parameter_scope": "whole authorized synthetic labeled resource only",
    }
    return receipt, proof


def complete_checklist(store, user, pid, body):
    with store.tx() as c:
        project = store.lock_project(c, user, pid)
        # Project -> source row -> current grants; serializes scope writes and retries.
        c.execute(
            select(resources.c.id)
            .where(resources.c.id == body["resource_id"], resources.c.project_id == pid)
            .with_for_update()
        ).first()
        source = authorized_source(store, c, user, project, body["resource_id"])
        if source["hash"] != body["expected_source_hash"]:
            raise DomainError("VERSION_CONFLICT")
        request_fp = fingerprint(body)
        old = (
            c.execute(
                select(spec_checklist_tasks).where(
                    spec_checklist_tasks.c.project_id == pid,
                    spec_checklist_tasks.c.principal_id == user,
                    spec_checklist_tasks.c.request_key == body["request_key"],
                )
            )
            .mappings()
            .first()
        )
        if old:
            if old["request_fingerprint"] != request_fp:
                raise DomainError("VERSION_CONFLICT")
            verify_saved(store, c, user, project, old, source)
            return public(old)
        tid = new_id("spectask")
        output = receipt = proof = error = None
        try:
            with c.begin_nested():
                checked = verify_candidate(source, body["candidate_json"])
                text = json.dumps(
                    checked, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
                # Same effect; savepoint prevents partial artifact/read-grant leaks on failure.
                output = write_text_artifact(store, c, user, project["runtime_id"], pid, text)
                receipt, proof = evidence(tid, project, user, source, checked, output)
        except DomainError as exc:
            output = receipt = proof = None
            error = exc.public()
        row = {
            "id": tid,
            "project_id": pid,
            "principal_id": user,
            "runtime_id": project["runtime_id"],
            "resource_id": body["resource_id"],
            "source_hash": source["hash"],
            "request_key": body["request_key"],
            "request_fingerprint": request_fp,
            "request": body,
            "status": "FAILED" if error else "SUCCEEDED",
            "output": output,
            "receipt": receipt,
            "proof": proof,
            "proof_fingerprint": fingerprint(proof) if proof else None,
            "error": error,
        }
        c.execute(insert(spec_checklist_tasks).values(**row))
        return public(row)


def inspect_checklist(store, user, tid):
    with store.tx() as c:
        row = (
            c.execute(
                select(spec_checklist_tasks).where(
                    spec_checklist_tasks.c.id == tid,
                    spec_checklist_tasks.c.principal_id == user,
                )
            )
            .mappings()
            .first()
        )
        if not row:
            raise DomainError("PERMISSION_DENIED")
        project = store.lock_project(c, user, row["project_id"])
        source = authorized_source(store, c, user, project, row["resource_id"])
        verify_saved(store, c, user, project, row, source)
        result = public(row)
        if row["status"] == "SUCCEEDED":
            result["markdown_view"] = markdown_view(source_checklist(source))
        return result
