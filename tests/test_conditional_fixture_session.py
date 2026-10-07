"""Bounded protocol stays closed under -O; owned children collected on every failure."""
import importlib.util
import os
import subprocess
import sys

import pytest

PAYLOADS = ['not-json', '[]', '{"action":"snapshot","extra":1}',
            '{"action":null}', '{"action":"unknown"}']
SPEC = importlib.util.spec_from_file_location('conditional_fixture_control',
                                             'scripts/conditional-ui/fixture.py')
FIXTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)


@pytest.mark.parametrize('payload', PAYLOADS)
def test_fixture_session_rejects_invalid_protocol(payload):
    with pytest.raises(ValueError):
        FIXTURE.session_request(payload)


def test_protocol_is_closed_under_optimized_python(tmp_path):
    # One fresh import for all five validator negatives, then the actual stdin loop.
    code = """
import importlib.util,json
s=importlib.util.spec_from_file_location('f','scripts/conditional-ui/fixture.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
for payload in ['not-json','[]','{"action":"snapshot","extra":1}','{"action":null}','{"action":"unknown"}']:
    try:m.session_request(payload)
    except ValueError:pass
    else:raise RuntimeError('invalid request accepted under -O')
"""
    out = subprocess.run([sys.executable,'-O','-c',code], capture_output=True, text=True,
                         timeout=10, env={**os.environ,'PYTHONPATH':'src'})
    assert out.returncode == 0, out.stderr
    output = subprocess.run([sys.executable, '-O', 'scripts/conditional-ui/fixture.py',
                             '--root', str(tmp_path), '--session'], input='not-json\n',
                            capture_output=True, text=True, timeout=10,
                            env={**os.environ, 'PYTHONPATH':'src'})
    assert output.returncode != 0 and output.stdout == ''
    assert not list(tmp_path.iterdir())


def test_fixture_session_eof_exits_without_preparation(tmp_path):
    output = subprocess.run([sys.executable, 'scripts/conditional-ui/fixture.py', '--root',
                             str(tmp_path), '--session'], input='', capture_output=True,
                            text=True, timeout=10, env={**os.environ,'PYTHONPATH':'src'})
    assert output.returncode == 0 and output.stdout == ''
    assert not list(tmp_path.iterdir())


def test_owned_session_child_failures_and_timeout():
    output = subprocess.run(['node','tests/conditional_fixture_session.cjs',sys.executable],
                            capture_output=True,text=True,timeout=15)
    assert output.returncode == 0, output.stdout+output.stderr
    assert '"status":"PASS"' in output.stdout
