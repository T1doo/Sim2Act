"""Optional native code family is independent of original Source/PB families."""

import subprocess
import sys

import pytest

from sim2act import _lease_control as control
from test_lease_control_primitives import owner


def test_static_builtin_class_witness_refuses_without_native_crash():
    script = """
from sim2act import _cold_source_owned_impl as native
record=(object,type,object.__mro__,tuple(vars(object).items()),())
native.register_code(0,((),(record,),()))
assert native.verify_code() is False
print('PASS_STATIC_CLASS_FAIL_CLOSED')
"""
    result = subprocess.run([sys.executable, "-X", "faulthandler", "-c", script],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    assert result.stdout.strip() == "PASS_STATIC_CLASS_FAIL_CLOSED"


@pytest.mark.parametrize("role", ["time-module", "wall-clock", "mono-clock", "connect", "wrapper-code"])
def test_native_entry_rejects_foreign_code_or_clock_before_call(tmp_path, monkeypatch, role):
    authority, row, session = owner(tmp_path)
    calls = []
    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError("Foreign lease role was executed")
    with monkeypatch.context() as patch:
        if role == "time-module":
            from types import SimpleNamespace
            patch.setattr(control, "time", SimpleNamespace(time=foreign, monotonic=foreign))
        elif role == "wall-clock":
            patch.setattr(control.time, "time", foreign)
        elif role == "mono-clock":
            patch.setattr(control.time, "monotonic", foreign)
        elif role == "connect":
            patch.setattr(control.sqlite3, "connect", foreign)
        else:
            function = control.Session.check
            patch.setattr(function, "__code__", function.__code__.replace(co_name="changed_wrapper"))
        with pytest.raises(ValueError, match="Lease control entry code or role changed"):
            session.renew()
    assert calls == []
    assert session.check() > 0
