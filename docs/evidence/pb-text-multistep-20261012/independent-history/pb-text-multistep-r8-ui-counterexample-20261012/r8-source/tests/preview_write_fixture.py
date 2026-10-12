"""FAULT_INJECTION adapter for isolated synthetic Store only; no production registration.

The real apps.preview INSERT triggers a controlled SQL business-record write in the
same Connection/transaction. This validates real transaction/namespace observations,
not a production write ActionSpec or gateway capability that does not yet exist.
"""

import json
import re
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import (
    CheckConstraint,
    Column,
    MetaData,
    String,
    Table,
    Text,
    cast,
    event,
    insert,
    select,
)
from sqlalchemy.sql.dml import Insert

from sim2act.apps import load_draft, public_preview
from sim2act.db import app_previews, fingerprint, meta
from sim2act.errors import DomainError

fixture_meta = MetaData()
preview_records = Table(
    "fixture_preview_records",
    fixture_meta,
    Column("preview_id", String, primary_key=True),
    Column("namespace", String, nullable=False),
    Column("project_id", String, nullable=False),
    Column("app_id", String, nullable=False),
    Column("principal_id", String, nullable=False),
    Column("record_text", Text, nullable=False),
    CheckConstraint("namespace = 'PREVIEW'"),
)
preview_receipts = Table(
    "fixture_preview_receipts",
    fixture_meta,
    Column("preview_id", String, primary_key=True),
    Column("namespace", String, nullable=False),
    Column("project_id", String, nullable=False),
    Column("app_id", String, nullable=False),
    Column("principal_id", String, nullable=False),
    Column("request_fingerprint", String, nullable=False),
    Column("record_fingerprint", String, nullable=False),
    CheckConstraint("namespace = 'PREVIEW'"),
)


@dataclass(frozen=True)
class Target:
    namespace: str
    principal_id: str
    project_id: str
    app_id: str
    candidate_fingerprint: str
    instance_id: str | None = None
    release_id: str | None = None


@dataclass
class Observation:
    writes_executed: int = 0
    inside_transaction_readback: str | None = None
    receipts_executed: int = 0
    inside_transaction_receipt: str | None = None
    failed_previews_skipped: int = 0


def require_synthetic(store, temporary_root):
    if not store.test_only:
        raise DomainError("PERMISSION_DENIED", "Controlled writer requires explicit test Store")
    if store.sqlite:
        location = Path(store.engine.url.database).resolve()
        if not location.is_relative_to(Path(temporary_root).resolve()):
            raise DomainError(
                "PERMISSION_DENIED", "Controlled writer requires isolated temporary DB"
            )
    else:
        schema = store.engine.get_execution_options().get("schema_translate_map", {}).get(None, "")
        if not re.fullmatch(r"test_[a-f0-9]{32}", schema):
            raise DomainError(
                "PERMISSION_DENIED", "Controlled writer requires isolated test schema"
            )


@contextmanager
def controlled_writer(store, temporary_root, target, limits, *, fail_after_write=False):
    require_synthetic(store, temporary_root)
    # Fixture Setup only. Not in sim2act.db.meta/CLI migrations/API-worker initialization.
    fixture_meta.create_all(store.engine)
    observed = Observation()

    def after_insert(c, _cursor, _statement, _parameters, context, _executemany):
        compiled = context.compiled
        if (
            not compiled
            or not isinstance(compiled.statement, Insert)
            or compiled.statement.table is not app_previews
        ):
            return
        parameters = context.compiled_parameters
        if len(parameters) != 1:
            raise DomainError("INVALID_INPUT", "Fixture accepts one bound preview INSERT")
        row = (
            c.execute(select(app_previews).where(app_previews.c.id == parameters[0]["id"]))
            .mappings()
            .one()
        )
        if row["status"] != "SUCCEEDED":
            observed.failed_previews_skipped += 1
            return
        if (
            target.namespace != "PREVIEW"
            or target.instance_id is not None
            or target.release_id is not None
        ):
            raise DomainError(
                "PERMISSION_DENIED", "Fixture cannot call an instance/release write target"
            )
        draft, _, _, _ = load_draft(store, c, target.principal_id, target.app_id, limits)
        if (
            row["app_id"] != target.app_id
            or row["principal_id"] != target.principal_id
            or draft["project_id"] != target.project_id
            or draft["fingerprint"] != target.candidate_fingerprint
            or public_preview(row)["namespace"] != "PREVIEW"
        ):
            raise DomainError("VERSION_CONFLICT", "Exact preview namespace binding changed")
        # Controlled mutation is a note record, not the CSV sum/result or old cache.
        text = "controlled note for column=" + row["input"]["column"] + "\n仅预览 Ω"
        record = {
            "preview_id": row["id"],
            "namespace": "PREVIEW",
            "project_id": target.project_id,
            "app_id": target.app_id,
            "principal_id": target.principal_id,
            "record_text": text,
        }
        c.execute(insert(preview_records).values(**record))
        observed.writes_executed += 1
        observed.inside_transaction_readback = c.execute(
            select(preview_records.c.record_text).where(preview_records.c.preview_id == row["id"])
        ).scalar_one()
        if observed.inside_transaction_readback != text:
            raise DomainError("VERIFICATION_FAILED")
        c.execute(
            insert(preview_receipts).values(
                preview_id=row["id"],
                namespace="PREVIEW",
                project_id=target.project_id,
                app_id=target.app_id,
                principal_id=target.principal_id,
                request_fingerprint=row["fingerprint"],
                record_fingerprint=fingerprint(record),
            )
        )
        observed.receipts_executed += 1
        observed.inside_transaction_receipt = c.execute(
            select(preview_receipts.c.record_fingerprint).where(
                preview_receipts.c.preview_id == row["id"]
            )
        ).scalar_one()
        if observed.inside_transaction_receipt != fingerprint(record):
            raise DomainError("VERIFICATION_FAILED")
        if fail_after_write:
            raise DomainError(
                "VERIFICATION_FAILED",
                "FAULT_INJECTION after actual record and receipt before commit",
            )

    event.listen(store.engine, "after_cursor_execute", after_insert)
    try:
        yield observed
    finally:
        event.remove(store.engine, "after_cursor_execute", after_insert)


def production_bytes(store):
    """Raw stored SQL values (JSON cast to text, not parsed/re-serialized) in stable PK order.

    UTF8 byte comparison concerns logical persisted columns, not physical database pages.
    Only legitimate app_previews history is excluded. All permissions/instance/Release/
    resource/operation/checkpoint/event tables are included, not just row counts or hashes.
    """
    with store.tx() as c:
        return {
            table.name: json.dumps(
                [
                    list(row)
                    for row in c.execute(
                        select(
                            *[cast(column, Text).label(column.name) for column in table.columns]
                        ).order_by(*table.primary_key.columns)
                    )
                ],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            for table in meta.sorted_tables
            if table is not app_previews
        }
