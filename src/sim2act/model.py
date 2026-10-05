"""Only Intern live transport, plus explicitly synthetic mock transport."""

import json

import httpx

from .contracts import strict_json
from .errors import DomainError
from .tools import validate_call


def parse_response(raw):
    try:
        if "error" in raw:
            raise DomainError("MODEL_OUTPUT_INVALID", "Upstream returned a business error")
        choice = raw["choices"][0]
        reason = choice["finish_reason"]
        if reason not in {"stop", "tool_calls"}:
            raise DomainError(
                "MODEL_TIMEOUT_OR_TRUNCATED", "Output incomplete or finish reason unknown"
            )
        msg = choice["message"]
        if msg.get("role") != "assistant":
            raise ValueError("role")
        calls = msg.get("tool_calls", [])
        if (
            not isinstance(calls, list)
            or len(calls) > 4
            or len({x["id"] for x in calls}) != len(calls)
        ):
            raise ValueError("tool ids")
        parsed = []
        for call in calls:
            if (
                call.get("type") != "function"
                or not isinstance(call["id"], str)
                or not 1 <= len(call["id"]) <= 100
            ):
                raise ValueError("tool type")
            fn = call["function"]
            args = strict_json(fn["arguments"], 32768)
            validate_call(fn["name"], args)
            parsed.append({"id": call["id"], "function": fn, "args": args})
        if not calls and (
            reason != "stop"
            or not isinstance(msg.get("content"), str)
            or not msg["content"].strip()
        ):
            raise ValueError("empty completion")
        # Do not store private reasoning_content or unknown upstream fields.
        safe = {"role": "assistant", "content": msg.get("content") or ""}
        if calls:
            safe["tool_calls"] = [
                {"id": x["id"], "type": "function", "function": x["function"]} for x in parsed
            ]
        return safe, parsed
    except DomainError:
        raise
    except (KeyError, IndexError, TypeError, ValueError) as e:
        raise DomainError(
            "MODEL_OUTPUT_INVALID", "Invalid model response; no tool dispatched"
        ) from e


class InternModel:
    def __init__(self, settings, transport=None):
        self.settings = settings
        self.transport = transport

    def request(self, messages, tools):
        s = self.settings
        if not s.live_enabled or not s.token:
            raise DomainError(
                "RESOURCE_UNAVAILABLE", "LIVE requires local token and approved finite budget"
            )
        if s.model != "intern-s2":
            raise DomainError("UNSUPPORTED_CAPABILITY")
        try:
            with httpx.Client(
                timeout=130, transport=self.transport, follow_redirects=False
            ) as client:
                response = client.post(
                    "https://chat.intern-ai.org.cn/api/v1/chat/completions",
                    headers={"Authorization": "Bearer " + s.token},
                    json={
                        "model": s.model,
                        "messages": messages,
                        "tools": tools,
                        "stream": False,
                        "max_tokens": s.max_output_tokens,
                    },
                )
                if response.status_code == 429:
                    raise DomainError("RATE_LIMITED", "Upstream quota denied", retryable=True)
                if response.status_code != 200:
                    raise DomainError("RESOURCE_UNAVAILABLE", "Upstream rejected request")
                return strict_json(response.content, 131072)
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            raise DomainError(
                "MODEL_TIMEOUT_OR_TRUNCATED", "Request failed; usage may be unknown"
            ) from e


class MockModel:
    """Engineering fixture only; never presented as actual autonomous model evidence."""

    def request(self, messages, tools):
        first = next(m for m in messages if m["role"] == "user")
        request = json.loads(first["content"])
        feedback = [m for m in messages if m["role"] == "tool"]
        if not feedback:
            rid = request["resource_refs"][0] if request["resource_refs"] else None
            fn = (
                {"name": "resource.read", "arguments": json.dumps({"resource_id": rid})}
                if rid
                else {
                    "name": "artifact.save_text",
                    "arguments": json.dumps({"text": "MOCK 工程成果：" + request["goal"]}),
                }
            )
            msg = {
                "role": "assistant",
                "content": "MOCK: choose a trusted tool",
                "tool_calls": [{"id": "mock-call-1", "type": "function", "function": fn}],
            }
            reason = "tool_calls"
        else:
            msg = {
                "role": "assistant",
                "content": "MOCK: result revised using persisted tool feedback. "
                + feedback[-1]["content"],
            }
            reason = "stop"
        return {
            "model": "MOCK-intern-contract",
            "choices": [{"finish_reason": reason, "message": msg}],
            "usage": None,
        }
