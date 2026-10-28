"""Versioned natural extraction wire; old receipts retain their exact bytes."""

import httpx

from .errors import DomainError
from .model import InternModel

VERSION = "natural-spec-request.v2"


def protocol(meta):
    if "request_protocol" not in meta:
        return None
    value = meta["request_protocol"]
    if type(value) is not str or value != VERSION:
        raise DomainError("VERSION_CONFLICT", "Unknown natural request protocol")
    return value


def body(messages, tools, max_output, *, request_protocol=None):
    if request_protocol is not None:
        protocol({"request_protocol": request_protocol})
    payload = dict(model="intern-s2", messages=messages, tools=tools,
        stream=False, max_tokens=max_output)
    if request_protocol == VERSION:
        if tools != []:
            raise DomainError("VERSION_CONFLICT", "Natural extraction has no tools")
        payload["thinking_mode"] = False
    return httpx.Request("POST", InternModel.ENDPOINT, json=payload).content


def coordinates(content):
    """Complete mechanical codepoint positions, no quote choice or correction."""
    if type(content) is not str:
        raise DomainError("INVALID_INPUT", "Exact current source text required")
    return [[index, char] for index, char in enumerate(content)]
