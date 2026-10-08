"""Fixed pure CSV receipt projection; no reads, model tools, grants or artifacts."""

from decimal import Decimal, DecimalException

from .errors import DomainError

REF = "intern.csv_report.v1"


def obj(fields):
    return dict(type="object", properties=fields, required=list(fields), additionalProperties=False)


FIELDS = {"resource_id": {"type": "string"}, "column": {"type": "string"},
          "count": {"type": "integer"}, "sum": {"type": "string"},
          "source_hash": {"type": "string"}}
INPUT = obj(FIELDS)
OUTPUT = obj({**FIELDS, "text": {"type": "string"}})


def check_action(action):
    if (action.input_schema != INPUT or action.output_schema != OUTPUT
            or action.allowed_tool_refs or action.dependencies or action.permission_requirements
            or action.preconditions or action.postcheck_refs != ["receipt.readback.v1"]
            or action.effect != "read" or action.idempotency != "read_only"):
        raise DomainError("INVALID_MANIFEST", "CSV formatter is an exact pure typed projection")


def render(value):
    from .contracts import resource_id, validate_value

    validate_value(INPUT, value)
    resource_id(value["resource_id"])
    try:
        valid = Decimal(value["sum"]).is_finite()
    except DecimalException:
        valid = False
    if (not valid or not 0 <= value["count"] <= 1000 or len(value["sum"]) > 256
            or len(value["column"]) > 200
            or len(value["source_hash"]) != 64
            or any(c not in "0123456789abcdef" for c in value["source_hash"])):
        raise DomainError("VERIFICATION_FAILED", "Invalid typed CSV report provenance")
    return {**value, "text": f"列 {value['column']}；行数 {value['count']}；合计 {value['sum']}"}
