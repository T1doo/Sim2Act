"""Exact raw-capture function frozen from 6e46f871 for differential tests."""
from typing import Any

from sim2act.natural_live_admission import _trial_pure_mapping, require


def _trial_pure_data(value):
    """Copy only complete controlled data; never equality/iteration on strangers."""
    from sqlalchemy.engine import RowMapping

    active = set()

    def visit(item):
        result: Any
        kind = type(item)
        if any(kind is allowed for allowed in (str, int, float, bool, bytes, type(None))):
            return item
        require(any(kind is allowed for allowed in (dict, RowMapping, list, tuple)),
            'Unsupported nested trial raw data')
        identity = id(item)
        require(identity not in active, 'Cyclic trial raw data')
        active.add(identity)
        if kind is dict or kind is RowMapping:
            raw = _trial_pure_mapping(item)
            result = {key: visit(child) for key, child in dict.items(raw)}
        elif kind is list:
            result = [visit(child) for child in item]
        else:
            result = tuple(visit(child) for child in item)
        active.remove(identity)
        return result

    return visit(value)
