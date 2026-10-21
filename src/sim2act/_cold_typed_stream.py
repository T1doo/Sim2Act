"""Fresh, complete typed-cohort comparisons without recursive value copies.

This is a local comparison, not ownership, a permission or a cached PASS.
The original graph/SQL/authority boundaries live in the caller. Only the fixed
standard serializer may use the streaming bridge; overridden serializers keep
the original snapshot bridge, including its pre-serialization raw semantics.
"""

from collections.abc import Iterator
from inspect import getattr_static
from typing import Any

from pydantic import BaseModel
from pydantic_core import SchemaSerializer
from sqlalchemy.engine import RowMapping

from .natural_live_admission import require

_STANDARD_DUMP = BaseModel.model_dump
_MISSING = object()


def _model_children(raw, omitted):
    for key, child in dict.items(raw):
        if key != omitted:
            yield child


def _mapping_pairs(left, right, omitted):
    for key, value in dict.items(left):
        if key != omitted:
            yield value, right[key]


def _raw_mapping_pairs(left, right, omitted):
    for key, value in dict.items(right):
        yield (_MISSING if key == omitted else left.get(key, _MISSING)), value


def _unpaired(children):
    for child in children:
        yield _MISSING, child


class _Comparison:
    def __init__(self, allowed):
        self.allowed = allowed
        # Invocation-local projections retain their sources. These are not
        # validation results carried to another pin, call, transaction or scope.
        self.models: dict[int, tuple[Any, dict, str | None]] = {}
        self.raw_maps: dict[int, tuple[Any, dict]] = {}

    def model_fields(self, value):
        from .contracts import BranchCondition, WorkflowStep

        kind = type(value)
        raw = object.__getattribute__(value, '__dict__')
        fields = type.__getattribute__(kind, '__pydantic_fields__')
        selected = object.__getattribute__(value, '__pydantic_fields_set__')
        require(type(raw) is dict and all(type(key) is str for key in raw)
            and type(fields) is dict and all(type(key) is str for key in fields)
            and raw.keys() == fields.keys()
            and type(selected) is set and all(type(key) is str for key in selected)
            and selected <= fields.keys()
            and object.__getattribute__(value, '__pydantic_extra__') is None
            and object.__getattribute__(value, '__pydantic_private__') is None,
            'Complete fixed typed trial storage required')
        omitted = ('value' if kind is BranchCondition and raw['value'] is None else
                   'when' if kind is WorkflowStep and raw['when'] is None else None)
        self.models[id(value)] = value, raw, omitted
        return raw, omitted

    def raw_mapping(self, value):
        from .natural_live_admission import _trial_pure_mapping

        # The native common case needs no tuple(items), new names or dict.
        # Gate every key before any membership/hash/equality operation.
        if type(value) is dict and all(type(key) is str for key in value):
            return value
        result = _trial_pure_mapping(value)
        self.raw_maps[id(value)] = value, result
        return result

    def validate_model(self, root):
        """Complete original actual storage gate, in original DFS order.

        Iterators and completed-node metadata replace copied containers. Active
        nodes are tested before completed nodes, so DAG reuse cannot hide cycles.
        No object identity is an equality/PASS shortcut.
        """
        active: set[int]
        done: set[int]
        active, done = set(), set()
        frames: list[tuple[int | None, Iterator[Any]]] = [(None, iter((root,)))]
        while frames:
            try:
                value = next(frames[-1][1])
            except StopIteration:
                identity, _ = frames.pop()
                if identity is not None:
                    active.remove(identity)
                    done.add(identity)
                continue
            kind = type(value)
            if (kind is str or kind is int or kind is float or kind is bool
                    or kind is bytes or kind is type(None)):
                continue
            require(kind is dict or kind is list or kind is tuple
                or any(kind is item for item in self.allowed),
                'Unsupported nested typed trial fact')
            identity = id(value)
            require(identity not in active, 'Cyclic typed trial fact')
            if identity in done:
                continue
            if kind is list or kind is tuple:
                children = iter(value)
            else:
                if kind is dict:
                    require(all(type(key) is str for key in value),
                        'Exact typed trial JSON keys required')
                    children = iter(dict.values(value))
                else:
                    raw, omitted = self.model_fields(value)
                    children = _model_children(raw, omitted)
            active.add(identity)
            frames.append((identity, children))

    def raw_equal(self, actual, saved):
        """Gate ALL raw data while comparing; defer mismatch until gate ends.

        Raw validation and equality have independent completed sets. A raw DAG
        node's previous validation does not prove it equals another actual
        node. Missing/mismatched actual data never causes a lookup or early
        return that could hide a later raw cycle/unknown/key/index rejection.
        """
        matching = True
        active: set[int]
        raw_done: set[int]
        pairs_done: set[tuple[int, int, str | None]]
        active, raw_done, pairs_done = set(), set(), set()
        frames: list[tuple[int | None, tuple[int, int, str | None] | None, Iterator[Any]]] = [
            (None, None, iter(((actual, saved),)))]
        while frames:
            try:
                left, right = next(frames[-1][2])
            except StopIteration:
                identity, pair, _ = frames.pop()
                if identity is not None:
                    active.remove(identity)
                    raw_done.add(identity)
                    if pair is not None:
                        pairs_done.add(pair)
                continue
            kind = type(right)
            if (kind is str or kind is int or kind is float or kind is bool
                    or kind is bytes or kind is type(None)):
                if matching and (type(left) is not kind or left != right):
                    matching = False
                continue
            require(kind is dict or kind is RowMapping or kind is list or kind is tuple,
                'Unsupported nested trial raw data')
            identity = id(right)
            require(identity not in active, 'Cyclic trial raw data')
            pair = None
            if matching:
                left_kind, omitted = type(left), None
                header = self.models.get(id(left))
                if header is not None and header[0] is left:
                    _, left, omitted = header
                    left_kind = dict
                if kind is dict or kind is RowMapping:
                    mapped = self.raw_mapping(right)
                    if (left_kind is not dict
                            or not all(type(key) is str for key in left)
                            or len(left) - (omitted is not None) != len(mapped)):
                        matching = False
                    else:
                        children = _raw_mapping_pairs(left, mapped, omitted)
                elif left_kind is not kind or len(left) != len(right):
                    matching = False
                else:
                    children = iter(zip(left, right, strict=True))
                if matching:
                    pair = id(left), identity, omitted
                    if pair in pairs_done:
                        continue
            if not matching:
                if identity in raw_done:
                    continue
                if kind is dict or kind is RowMapping:
                    children = _unpaired(dict.values(self.raw_mapping(right)))
                else:
                    children = _unpaired(right)
            active.add(identity)
            frames.append((identity, pair, children))
        return matching

    def equal(self, actual, saved, *, typed):
        """Strict complete virtual projection equality; no recursive copy.

        Both source graphs were gated in full before this comparison. Pair memo
        is local and only completed container pairs are reused. Scalars always
        compare by exact type/value (including NaN, bool/int and signed zero).
        """
        active: set[tuple[int, int, str | None]]
        done: set[tuple[int, int, str | None]]
        active, done = set(), set()
        frames: list[tuple[tuple[int, int, str | None] | None, Iterator[Any]]] = [
            (None, iter(((actual, saved),)))]
        while frames:
            try:
                left, right = next(frames[-1][1])
            except StopIteration:
                pair, _ = frames.pop()
                if pair is not None:
                    active.remove(pair)
                    done.add(pair)
                continue
            kind, omitted = type(left), None
            if (kind is str or kind is int or kind is float or kind is bool
                    or kind is bytes or kind is type(None)):
                if kind is not type(right) or left != right:
                    return False
                continue
            if typed and kind is not dict and kind is not list and kind is not tuple:
                header = self.models.get(id(left))
                if header is not None and header[0] is left:
                    _, left, omitted = header
                    kind = dict
            mapped = self.raw_maps.get(id(right))
            if mapped is not None and mapped[0] is right:
                right = mapped[1]
            if kind is not type(right):
                return False
            if kind is dict:
                if (not all(type(key) is str for key in left)
                        or not all(type(key) is str for key in right)
                        or len(left) - (omitted is not None) != len(right)
                        or not all(key == omitted or key in right for key in left)):
                    return False
                children = _mapping_pairs(left, right, omitted)
            elif kind is list or kind is tuple:
                if len(left) != len(right):
                    return False
                children = iter(zip(left, right, strict=True))
            else:
                return False
            pair = id(left), id(right), omitted
            if pair in active:
                return False
            if pair in done:
                continue
            active.add(pair)
            frames.append((pair, children))
        return True

    def standard_serializers(self):
        # Any-valued fields can dispatch a nested model's serializer, so root
        # qualification alone is insufficient. Freshly inspect every visited
        # fixed schema, once per class in this invocation, without descriptors.
        checked = set()
        for model, _, _ in self.models.values():
            kind = type(model)
            if kind in checked:
                continue
            checked.add(kind)
            namespace = type.__getattribute__(kind, '__dict__')
            serializer = namespace.get('__pydantic_serializer__')
            if (getattr_static(kind, 'model_dump') is not _STANDARD_DUMP
                    or type(serializer) is not SchemaSerializer
                    or SchemaSerializer.__reduce__(serializer)[1][0]
                        is not namespace.get('__pydantic_core_schema__')):
                return False
        return True


def _stream_values(expected, model, raw):
    """Return False only for the original snapshot serializer bridge.

    The fixed catalog has standard Pydantic serializers and precisely two pure
    `is None` exclusion hooks. No SQL, user callback or IO occurs between the
    complete gates and comparisons. A replaced serializer is not assumed pure:
    the caller retains the old pre-serializer snapshot behavior for it.
    """
    from .natural_live_admission import _trial_typed_classes, _trial_typed_nested_classes

    require(any(expected is kind for kind in _trial_typed_classes()) and type(model) is expected,
        'Exact typed trial fact required')
    comparison = _Comparison(_trial_typed_nested_classes())
    comparison.validate_model(model)
    require(type(raw) is dict, 'Complete typed trial raw pin required')
    require(comparison.raw_equal(model, raw),
        'Typed trial storage changed after its complete raw proof')
    # No descriptor dispatch before the original complete gates/comparison.
    # A same-extension-type replacement can carry arbitrary callbacks; its
    # constructor schema must also be this fixed class's actual schema object.
    # __reduce__ is the pinned extension's metadata operation, not serialization
    # or pickle loading. It retains the constructor's schema reference.
    if not comparison.standard_serializers():
        return False
    value = expected.model_dump(model, warnings=False)
    require(comparison.equal(value, raw, typed=False),
        'Typed trial fact changed after its complete raw proof')
    return True
