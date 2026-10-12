"""Independent current-source verification of durable literal AppRun history."""

from sqlalchemy import select

from .agent_apps import check_evidence
from .contracts import validate_action_input, validate_value
from .db import (
    fingerprint,
    internal_instance_data,
    internal_run_bindings,
    operation_intents,
    operations,
    runs,
)
from .errors import DomainError
from .tools import authorized_read


def verify(store, c, user, job, limits, *, archival_software=None):
    from .app_jobs import load_binding
    from .lifecycle import read_release

    snapshot, actual = load_binding(store, c, user, job, limits, archival_software=archival_software)
    release = read_release(store, c, user, snapshot["release_id"], limits, archival_software=archival_software)
    draft = release["snapshot"]["draft"]
    candidate = draft["candidate"]
    manifest, action = candidate["manifest"], candidate["actions"][0]
    if action["executor"]["ref"] != "text.literal_evidence":
        raise DomainError("VERSION_CONFLICT", "Literal history executor changed")
    args = {"resource_id": manifest["data_bindings"][0]["resource_ref"], **snapshot["input"]}
    from .contracts import ActionSpec

    validate_value(manifest["input_schema"], snapshot["input"])
    validate_action_input(ActionSpec.model_validate(action), args)
    source = authorized_read(
        store,
        c,
        user,
        draft["runtime_id"],
        draft["project_id"],
        "resource.read",
        {"resource_id": args["resource_id"]},
    )
    check = check_evidence(source, args, actual["output"])
    op = (
        c.execute(
            select(operations).where(
                operations.c.run_id == job["id"], operations.c.call_id == "instance_result"
            )
        )
        .mappings()
        .first()
    )
    if not op:
        raise DomainError("VERSION_CONFLICT", "Actual literal read receipt missing")
    intent = c.execute(
        select(operation_intents.c.request).where(operation_intents.c.operation_id == op["id"])
    ).scalar()
    expected_intent = {"tool": "resource.read", "args": {"resource_id": args["resource_id"]}}
    receipt = {
        "operation_id": op["id"],
        "status": "VERIFIED",
        "app_run_id": actual["id"],
        "instance_id": snapshot["instance_id"],
        "release_id": snapshot["release_id"],
        "result_version": actual["result_version"],
        "output_fingerprint": fingerprint(actual["output"]),
        "data": actual["output"],
        "artifact_refs": [],
        "check_results": [check],
    }
    record = (
        c.execute(
            select(internal_instance_data).where(
                internal_instance_data.c.run_id == actual["id"],
                internal_instance_data.c.instance_id == snapshot["instance_id"],
            )
        )
        .mappings()
        .first()
    )
    data = {"result": actual["output"]}
    if "release_ref" in release["snapshot"]["data_schema"]["properties"]:
        data["release_ref"] = snapshot["release_id"]
    if (
        job["status"] != "SUCCEEDED"
        or job["result"]
        != {
            "app_run_id": actual["id"],
            "instance_id": snapshot["instance_id"],
            "release_id": snapshot["release_id"],
            "result_version": actual["result_version"],
            "receipt_ref": op["id"],
        }
        or actual["status"] != "SUCCEEDED"
        or actual["error"] is not None
        or job["error"] is not None
        or op["status"] != "VERIFIED"
        or op["tool_ref"] != "resource.read"
        or intent != expected_intent
        or op["fingerprint"] != fingerprint(intent)
        or op["receipt"] != receipt
        or not record
        or record["data"] != data
        or record["fingerprint"] != fingerprint(data)
        or record["version"] != actual["result_version"]
        or record["release_id"] != snapshot["release_id"]
        or record["schema_version"] != release["snapshot"]["data_schema_version"]
    ):
        raise DomainError("VERSION_CONFLICT", "Literal history differs from actual checked result")
    validate_value(release["snapshot"]["data_schema"], data)


def verify_records(store, c, user, records, limits):
    for record in records:
        rid = c.execute(
            select(internal_run_bindings.c.run_id).where(
                internal_run_bindings.c.app_run_id == record["run_id"]
            )
        ).scalar()
        if not rid:
            raise DomainError("VERSION_CONFLICT", "Literal result requires actual worker history")
        job = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        verify(store, c, user, job, limits)
