"""Read-only local status diagnostics; never echo response bodies or process commands."""

import json
from pathlib import Path

import httpx


def unavailable_health(reason, http_status=None):
    """Keep the legacy OFFLINE value, with explicit unknown component states."""
    return {
        "health": "OFFLINE",
        "health_check": {
            "status": reason,
            "api": "OFFLINE" if reason == "CONNECTION_FAILED" else "UNKNOWN",
            "database": "UNKNOWN",
            "worker": "UNKNOWN",
            "http_status": http_status,
        },
    }


def parse_health(response):
    """Validate the existing public /health contract before reporting any UP state."""
    code = response.status_code
    if not 200 <= code < 300:
        return unavailable_health("HTTP_ERROR", code)
    try:
        payload = response.json()
    except (ValueError, RecursionError):
        return unavailable_health("INVALID_JSON", code)
    allowed = {
        "api": ("UP",),
        "database": ("UP",),
        "worker": ("UP", "OFFLINE"),
        "mode": ("MOCK", "LIVE"),
        "live_acceptance": ("BLOCKED",),
    }
    if not isinstance(payload, dict) or any(
        not isinstance(payload.get(key), str) or payload[key] not in values
        for key, values in allowed.items()
    ):
        return unavailable_health("INVALID_STRUCTURE", code)
    # Extra response fields are deliberately discarded, including diagnostics/secrets.
    health = {key: payload[key] for key in allowed}
    return {
        "health": health,
        "health_check": {
            "status": "HEALTHY" if health["worker"] == "UP" else "WORKER_OFFLINE",
            "api": health["api"],
            "database": health["database"],
            "worker": health["worker"],
            "http_status": code,
        },
    }


def _valid_records(records):
    if not isinstance(records, list) or len(records) > 2:
        return False
    kinds = set()
    for record in records:
        if not isinstance(record, dict):
            return False
        kind = record.get("kind")
        if kind not in ("api", "worker") or kind in kinds:
            return False
        kinds.add(kind)
        pid, created = record.get("pid"), record.get("created_at")
        if type(pid) is not int or not 0 < pid <= 2**31 - 1:
            return False
        if type(created) not in (int, float) or not 0 < created < 1e12:
            return False
        command = record.get("command")
        if command is not None and (
            not isinstance(command, list) or not all(isinstance(item, str) for item in command)
        ):
            return False
        # Retain the existing verifier's legacy command reconstruction.
        if kind == "api" and not command:
            port = record.get("port")
            if type(port) is not int or not 1 <= port <= 65535:
                return False
    return True


def collect_status(state: Path, observe_process, get_health):
    """Read state, call the unchanged identity verifier, and query health exactly once.

    The callbacks permit entirely synthetic observations and HTTP transports in tests.
    Health NEVER changes the local process identity/alive result.
    """
    records = []
    try:
        records = json.loads(state.read_text(encoding="utf-8"))
        state_status = "VALID" if _valid_records(records) else "INVALID_STRUCTURE"
    except FileNotFoundError:
        state_status = "MISSING"
    except (ValueError, RecursionError):
        state_status = "INVALID_JSON"
    except OSError:
        state_status = "UNREADABLE"
    output = {
        kind: {"pid": None, "alive": None, "identity": "NOT_RECORDED"}
        for kind in ("api", "worker")
    }
    output["process_state"] = state_status
    if state_status == "VALID":
        for record in records:
            result = {"pid": record["pid"], "alive": None, "identity": "UNVERIFIABLE"}
            try:
                result["alive"] = observe_process(record) is not None
                result["identity"] = "VERIFIED" if result["alive"] else "NOT_VERIFIED"
            except (RuntimeError, OSError):
                pass
            output[record["kind"]] = result
    elif state_status != "MISSING":
        for kind in ("api", "worker"):
            output[kind]["identity"] = "UNVERIFIABLE"
    try:
        output.update(parse_health(get_health()))
    except httpx.HTTPError:
        output.update(unavailable_health("CONNECTION_FAILED"))
    return output
