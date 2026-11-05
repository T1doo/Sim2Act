"""Versioned natural extraction wire; old receipts retain their exact bytes."""

import httpx

from .errors import DomainError
from .model import InternModel

VERSION = "natural-spec-request.v2"
INDEXED_VERSION = "natural-spec-request.v3"
CURRENT_VERSION = "natural-spec-request.v4"
INDEXED_PROTOCOLS = (INDEXED_VERSION, CURRENT_VERSION)
PROTOCOLS = (VERSION, *INDEXED_PROTOCOLS)


def protocol(meta):
    if "request_protocol" not in meta:
        return None
    value = meta["request_protocol"]
    if type(value) is not str or value not in PROTOCOLS:
        raise DomainError("VERSION_CONFLICT", "Unknown natural request protocol")
    return value


def body(messages, tools, max_output, *, request_protocol=None):
    if request_protocol is not None:
        protocol({"request_protocol": request_protocol})
    payload = dict(model="intern-s2", messages=messages, tools=tools,
        stream=False, max_tokens=max_output)
    if request_protocol in PROTOCOLS:
        if tools != []:
            raise DomainError("VERSION_CONFLICT", "Natural extraction has no tools")
        payload["thinking_mode"] = False
    return httpx.Request("POST", InternModel.ENDPOINT, json=payload).content


def coordinates(content):
    """Complete mechanical codepoint positions, no quote choice or correction."""
    if type(content) is not str:
        raise DomainError("INVALID_INPUT", "Exact current source text required")
    return [[index, char] for index, char in enumerate(content)]


def indexed_lines(content):
    from .natural_specs import source_line_index

    return [dict(span_id=index, **span)
        for index, span in enumerate(source_line_index(content)["lines"], 1)]


def resolve_line_citations(value, content):
    """Resolve explicit references to source spans before the original checks."""
    if not isinstance(value, dict) or not isinstance(value.get("items"), list):
        return
    spans = indexed_lines(content)
    for item in value["items"]:
        if not isinstance(item, dict) or not isinstance(item.get("citations"), list):
            continue
        for index, citation in enumerate(item["citations"]):
            if not isinstance(citation, dict) or "span_id" not in citation:
                continue
            span_id = citation["span_id"]
            if set(citation) != {"span_id"} or type(span_id) is not int or not 1 <= span_id <= len(spans):
                raise DomainError("VERIFICATION_FAILED", "Citation does not name one exact current source span")
            item["citations"][index] = {key: val for key, val in spans[span_id - 1].items()
                if key != "span_id"}
