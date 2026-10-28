"""Owned content plan for the existing complete public G0 validators.

No Graph, connection, row mapping, mutable model, permission or PASS is stored
in a plan.  The public validators and complete postwrite G1 stay authoritative.
"""

from __future__ import annotations

import base64
import json
import struct
from dataclasses import dataclass, field
from inspect import getattr_static
from types import FunctionType, MemberDescriptorType

from .errors import DomainError

_JSON_LOADS = json.loads
_JSON_LOADS_CODE = json.loads.__code__
_JSON_DECODER = json._default_decoder
_JSON_DECODE = type(json._default_decoder).decode
_JSON_RAW_DECODE = type(json._default_decoder).raw_decode


def _codec_current():
    from sqlalchemy.sql.elements import quoted_name

    from . import natural_spec_runtime as runtime

    descriptor = getattr_static(quoted_name, "quote")
    if (
        type(descriptor) is not MemberDescriptorType
        or descriptor.__objclass__ is not quoted_name
        or descriptor.__name__ != "quote"
        or getattr_static(quoted_name, "__str__") is not str.__str__
        or getattr_static(quoted_name, "__hash__") is not str.__hash__
        or getattr_static(quoted_name, "__eq__") is not str.__eq__
        or any(
            getattr_static(kind, name, runtime._RAW_READ_MISS) is not expected
            for kind, name, expected in runtime._RAW_READ_ROW_SLOTS
        )
        or any(runtime.__dict__.get(name) is not fn for name, fn in runtime._RAW_READ_CODEC)
        or any(fn.__code__ is not code for fn, code in runtime._RAW_READ_CODE)
        or json.dumps is not runtime._COUNTER_PACKET_JSON[0]
        or json.JSONEncoder is not runtime._COUNTER_PACKET_JSON[1]
        or json.loads is not _JSON_LOADS
        or _JSON_LOADS.__code__ is not _JSON_LOADS_CODE
        or json._default_decoder is not _JSON_DECODER
        or type(_JSON_DECODER).decode is not _JSON_DECODE
        or type(_JSON_DECODER).raw_decode is not _JSON_RAW_DECODE
    ):
        raise UnsupportedPlan("Unknown owned data codec configuration")


class UnsupportedPlan(ValueError):
    """Qualification failed before any planned business call; use legacy."""


@dataclass(frozen=True, slots=True, repr=False)
class OwnedValue:
    """Complete typed/ordered/aliased data, owned as immutable bytes only."""

    _data: bytes = field(repr=False)

    @classmethod
    def capture(cls, value):
        _codec_current()
        from sqlalchemy.engine import RowMapping
        from sqlalchemy.sql.elements import quoted_name

        from .contracts import Limits
        from .natural_spec_runtime import _cold_graph_limit_values, _cold_graph_row_storage

        nodes, memo, active, held = [], {}, set(), []
        work = size = 0

        def visit(item, depth=0):
            nonlocal work, size
            work += 1
            if work > 1_000_000 or depth > 64 or len(nodes) >= 100_000:
                raise UnsupportedPlan("Owned content limit")
            kind = type(item)
            if kind is type(None):
                tag, content = "none", None
            elif kind is bool:
                tag, content = "bool", item
            elif kind is int:
                tag, content = "int", str(item)
                size += len(content)
            elif kind is float:
                tag, content = "float", struct.pack("!d", item).hex()
            else:
                key = id(item)
                if key in active:
                    raise UnsupportedPlan("Cyclic content")
                if key in memo:
                    return memo[key]
                ordinal = len(nodes)
                memo[key] = ordinal
                held.append(item)  # Prevent temporary projection id reuse.
                nodes.append(None)
                active.add(key)
                if kind is str:
                    size += len(item) * 4
                    tag, content = "str", item
                elif kind is bytes:
                    size += len(item)
                    tag, content = "bytes", base64.b64encode(item).decode("ascii")
                elif kind is quoted_name and (type(item.quote) is bool or item.quote is None):
                    size += len(item) * 4
                    tag, content = "quoted", [str(item), item.quote]
                elif kind is dict:
                    if not all(type(k) is str or type(k) is quoted_name for k in item):
                        raise UnsupportedPlan("Only exact data keys")
                    tag, content = (
                        "dict",
                        [[visit(k, depth + 1), visit(v, depth + 1)] for k, v in dict.items(item)],
                    )
                elif kind is list or kind is tuple:
                    tag, content = (
                        ("list" if kind is list else "tuple"),
                        [visit(v, depth + 1) for v in item],
                    )
                elif kind is Limits:
                    _cold_graph_limit_values(item)
                    selected = object.__getattribute__(item, "__pydantic_fields_set__")
                    if type(selected) is not set or not all(type(v) is str for v in selected):
                        raise UnsupportedPlan("Unknown Limits storage")
                    tag, content = (
                        "limits",
                        [
                            visit(object.__getattribute__(item, "__dict__"), depth + 1),
                            visit(selected, depth + 1),
                        ],
                    )
                elif kind is set:
                    if not all(type(v) is str for v in item):
                        raise UnsupportedPlan("Only exact field name sets")
                    tag, content = "field-set", [visit(v, depth + 1) for v in sorted(item)]
                elif kind is RowMapping:
                    index = object.__getattribute__(item, "_key_to_index")
                    if type(index) is not dict or not all(
                        type(k) is str or type(k) is quoted_name for k in dict.keys(index)
                    ):
                        raise UnsupportedPlan("Foreign SQL row lookup")
                    storage = _cold_graph_row_storage(item)
                    keys, data, lookup = storage
                    # Foreign/hidden/non-visible columns keep the legacy path.
                    if (
                        len(keys) != len(data)
                        or len(set(map(str, keys))) != len(keys)
                        or set(lookup) != set(map(str, keys))
                    ):
                        raise UnsupportedPlan("Noncanonical SQL row")
                    tag, content = "row", visit((keys, data, index), depth + 1)
                else:
                    raise UnsupportedPlan("Unknown content type")
                active.remove(key)
                if size > 16 * 1024 * 1024:
                    raise UnsupportedPlan("Owned content size")
                nodes[ordinal] = [tag, content]
                return ordinal
            if size > 16 * 1024 * 1024:
                raise UnsupportedPlan("Owned content size")
            ordinal = len(nodes)
            nodes.append([tag, content])
            return ordinal

        root = visit(value)
        data = json.dumps(
            [root, nodes], ensure_ascii=True, separators=(",", ":"), allow_nan=False
        ).encode()
        if len(data) > 32 * 1024 * 1024:
            raise UnsupportedPlan("Owned encoding size")
        return cls(data)

    def matches(self, current):
        return OwnedValue.capture(current)._data == self._data

    def materialize(self):
        """Fresh private values; no mutable original is retained or returned."""
        from sqlalchemy.engine import RowMapping
        from sqlalchemy.engine.result import SimpleResultMetaData
        from sqlalchemy.sql.elements import quoted_name

        from .contracts import Limits

        _codec_current()
        root, nodes = json.loads(self._data)
        memo = {}

        def build(index):
            if index in memo:
                return memo[index]
            tag, raw = nodes[index]
            if tag == "none":
                value = None
            elif tag == "bool":
                value = raw
            elif tag == "int":
                value = int(raw)
            elif tag == "float":
                value = struct.unpack("!d", bytes.fromhex(raw))[0]
            elif tag == "str":
                value = raw
            elif tag == "bytes":
                value = base64.b64decode(raw, validate=True)
            elif tag == "quoted":
                value = quoted_name(*raw)
            elif tag == "dict":
                value = {}
                memo[index] = value
                for key, item in raw:
                    value[build(key)] = build(item)
            elif tag == "list":
                value = []
                memo[index] = value
                value.extend(build(v) for v in raw)
            elif tag == "tuple":
                value = tuple(build(v) for v in raw)
            elif tag == "field-set":
                value = {build(i) for i in raw}
            elif tag == "limits":
                value = object.__new__(Limits)
                object.__setattr__(value, "__dict__", build(raw[0]))
                object.__setattr__(value, "__pydantic_fields_set__", build(raw[1]))
                object.__setattr__(value, "__pydantic_extra__", None)
                object.__setattr__(value, "__pydantic_private__", None)
            elif tag == "row":
                keys, data, lookup = build(raw)
                parent = SimpleResultMetaData(keys)
                parent._keys = keys
                value = RowMapping(parent, None, lookup, data)
            else:
                raise UnsupportedPlan("Unknown owned node")
            memo[index] = value
            return value

        value = build(root)
        # A singleton/interning/metadata quirk must never silently lose alias
        # semantics. Reject before any business computation can consume it.
        if not self.matches(value):
            raise UnsupportedPlan("Owned roundtrip changed complete data")
        return value


@dataclass(frozen=True, slots=True, repr=False)
class ContentPlan:
    """Pure compilation data. Dynamic approval/lease facts are never fields."""

    inputs: OwnedValue = field(repr=False)
    candidate: OwnedValue = field(repr=False)
    compiled: OwnedValue = field(repr=False)
    call_values: OwnedValue = field(repr=False)
    compilation_seconds: float

    @classmethod
    def compile(cls, inputs):
        from time import perf_counter

        from . import pa_spec_apps as spec
        from .contracts import Limits

        started = perf_counter()
        saved = OwnedValue.capture(inputs)
        private = saved.materialize()
        candidate = private["candidate"]
        limits = Limits(**private["platform"])
        manifest, action, report = spec.compile_candidate(candidate, limits)
        # These are data outputs, not cached validation/PASS or live models.
        compiled = OwnedValue.capture(
            dict(manifest=manifest.model_dump(), action=action.model_dump(), report=report)
        )
        if not saved.matches(private) or not saved.matches(inputs):
            raise DomainError("VERSION_CONFLICT", "Pure compiler changed owned inputs")
        return cls(
            saved,
            OwnedValue.capture(candidate),
            compiled,
            OwnedValue.capture(dict(call=private["call"], platform=private["platform"])),
            perf_counter() - started,
        )

    def private_inputs(self):
        return self.inputs.materialize()

    def check_current(self, original):
        if not self.inputs.matches(original):
            raise DomainError("VERSION_CONFLICT", "Complete settlement plan inputs changed")

    def read_current(self, store, connection, principal, job, platform):
        """Reconstruct full original binding in THIS transaction, never a PASS.

        Admission/lease/commit guards remain separate original public calls;
        this data comparison cannot supply any of those dynamic decisions.
        """
        from . import pa_spec_apps as spec

        current = spec.bound(store, connection, principal, job, platform)
        self.check_binding(current)
        return current

    def check_binding(self, current):
        # Complete original public bound has already recompiled and checked all
        # current database lineage/permissions. Only compare its exact data here.
        if not self.candidate.matches(current["draft"]["candidate"]):
            raise DomainError("VERSION_CONFLICT", "Current candidate differs from owned plan")
        expected = self.compiled.materialize()
        if current["plan"]["definition"]["manifest"] != expected["manifest"]:
            raise DomainError("VERSION_CONFLICT", "Current manifest differs from owned compilation")
        if current["report"] != expected["report"]:
            raise DomainError("VERSION_CONFLICT", "Current report differs from owned compilation")


# Bootstrap code/descriptor witnesses only. They retain no plan, Worker, current
# input or successful validation, and are checked before explicit candidate use.
_OWNED_CLASSES = tuple((kind, tuple(vars(kind).items())) for kind in (OwnedValue, ContentPlan))
_OWNED_FUNCTIONS = (("_codec_current", _codec_current),)
_OWNED_CODE = tuple(
    (fn, fn.__code__)
    for fn in (
        _codec_current,
        *[
            value.__func__ if type(value) is classmethod or type(value) is staticmethod else value
            for kind, items in _OWNED_CLASSES
            for _, value in items
            if type(value) is classmethod
            or type(value) is staticmethod
            or type(value) is FunctionType
        ],
    )
)
