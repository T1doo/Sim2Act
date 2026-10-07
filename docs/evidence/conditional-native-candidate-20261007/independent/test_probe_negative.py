import importlib.util
import subprocess
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('native_actual_test', '/workspace/Sim2Act-conditional-native/tests/test_conditional_native_oracle.py')
actual=importlib.util.module_from_spec(spec)
spec.loader.exec_module(actual)

@pytest.mark.parametrize('case',['timeout','missing'])
def test_actual_probe_no_false_pass(tmp_path,monkeypatch,case):
    calls=[]
    monkeypatch.setattr(actual.shutil,'which',lambda _: '/synthetic/node')
    def run(cmd,**kwargs):
        calls.append((cmd,kwargs))
        assert cmd==['node','-e',"require.resolve('jsdom')"]
        assert kwargs['timeout']==10
        assert kwargs['stdout']==subprocess.DEVNULL and kwargs['stderr']==subprocess.DEVNULL
        assert 'capture_output' not in kwargs
        if case=='timeout':raise subprocess.TimeoutExpired(cmd,10)
        return subprocess.CompletedProcess(cmd,1)
    monkeypatch.setattr(actual.subprocess,'run',run)
    with pytest.raises(subprocess.TimeoutExpired if case=='timeout' else pytest.skip.Exception):
        actual.test_conditional_native_shared_module_existing_fixture(tmp_path)
    assert len(calls)==1
