"""Offline diagnostic only: identity is insufficient for native eligibility."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from types import FunctionType

from sim2act import _cold_typed_native_candidate as native
from sim2act import natural_live_admission as gate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('database', type=Path)
    parser.add_argument('binary', type=Path)
    args = parser.parse_args()
    before = hashlib.sha256(args.database.read_bytes()).hexdigest()
    with sqlite3.connect(args.database.resolve().as_uri() + '?mode=ro', uri=True) as c:
        c.execute('PRAGMA query_only=ON')
        rows = c.execute('SELECT snapshot FROM delivery_graph_requests '
            'WHERE kind=? AND request_key=?', (gate.SCOPE, 'scope')).fetchall()
    assert len(rows) == 1
    contract = gate.PBTrialContract.model_validate(json.loads(rows[0][0])['request'])
    backend = native.load_candidate(args.binary)
    assert backend is not None
    # Resolve both paths' lazy imports before observing this call. Import-time
    # module qualification invokes require and is not projection work.
    baseline = gate._trial_typed_storage(gate.PBTrialContract, contract)
    assert gate._trial_typed_equal(
        native.select_candidate(backend, gate.PBTrialContract, contract), baseline)
    original = gate.require
    code = original.__code__
    reference = FunctionType(code, original.__globals__, argdefs=original.__defaults__)
    calls = []
    names = ('_slice_reference_require', '_slice_require_calls')
    assert all(name not in original.__globals__ for name in names)
    original.__globals__[names[0]] = reference
    original.__globals__[names[1]] = calls

    def instrumented(ok, message='Exact natural trial changed'):
        _slice_require_calls.append(bool(ok))
        return _slice_reference_require(ok, message)

    try:
        original.__code__ = instrumented.__code__
        assert gate.require is native._REQUIRE
        candidate = native.select_candidate(backend, gate.PBTrialContract, contract)
        assert candidate is not None and backend.native_calls == 2
        native_callback_calls = len(calls)
        calls.clear()
        expected = gate._trial_typed_storage(gate.PBTrialContract, contract)
        python_callback_calls = len(calls)
        assert native_callback_calls == 0 and python_callback_calls > 0
        assert gate._trial_typed_equal(candidate, expected)
    finally:
        original.__code__ = code
        for name in names:
            del original.__globals__[name]
    assert hashlib.sha256(args.database.read_bytes()).hexdigest() == before
    print(json.dumps(dict(
        classification='OFFLINE_EXISTING_CANDIDATE_CALLBACK_COUNTEREXAMPLE',
        current_helper_identity_unchanged=True,
        current_helper_code_changed=True,
        selected_native=True,
        native_success_callback_calls=native_callback_calls,
        python_success_callback_calls=python_callback_calls,
        projected_values_equal=True,
        behavior_equivalent=False,
        database_unchanged=True,
        mock_calls=0,
        real_model_calls=0,
        runtime_enabled=False,
    ), indent=2))


if __name__ == '__main__':
    main()
