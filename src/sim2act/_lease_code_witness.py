"""Import-time code metadata only; no imports of application lifecycle modules."""
from types import FunctionType
from builtins import type, id, set, tuple, vars, classmethod, staticmethod, property


def function_state(function, active=None):
    active = set() if active is None else active
    active.add(id(function))
    closure = function.__closure__
    cells = []
    for cell in closure or ():
        value = cell.cell_contents
        child = function_state(value, active) if type(value) is FunctionType and id(value) not in active else None
        cells.append((cell, value, child))
    active.remove(id(function))
    return (function, function.__code__, function.__defaults__, function.__kwdefaults__,
            tuple((function.__kwdefaults__ or {}).items()), closure, tuple(cells))


def class_state(cls):
    methods = []
    for name, value in vars(cls).items():
        functions = ((value,) if type(value) is FunctionType else
                     (value.__func__,) if type(value) in (classmethod, staticmethod) else
                     tuple(f for f in (value.fget, value.fset, value.fdel) if type(f) is FunctionType)
                     if type(value) is property else ())
        if functions:
            methods.append((name, value, tuple(function_state(f) for f in functions)))
    return cls, type(cls), cls.__mro__, tuple(vars(cls).items()), tuple(methods)
