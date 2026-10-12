"""Optional dependency absence is a skip; execution timeout remains a failure."""
import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize('target', ['native', 'http', 'progress'])
@pytest.mark.parametrize('outcome', ['timeout', 'missing'])
def test_optional_dom_probe_keeps_failure_boundary(env, tmp_path, monkeypatch, target, outcome):
    filename = {'native': 'test_registered_generation_native_dom.py',
                'http': 'test_registered_run_generation_http.py',
                'progress': 'test_task_progress.py'}[target]
    spec = importlib.util.spec_from_file_location('dependency_probe_' + target, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(shutil, 'which', lambda _name: 'synthetic-node-present')
    seen = []

    def dependency(command, **kwargs):
        seen.append(command)
        assert kwargs['timeout'] == 10  # Existing deadline is a boundary, not a tuning knob.
        assert kwargs['stdout'] == subprocess.DEVNULL and kwargs['stderr'] == subprocess.DEVNULL
        if outcome == 'timeout':
            raise subprocess.TimeoutExpired(command, kwargs['timeout'])
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(subprocess, 'run', dependency)
    expected = subprocess.TimeoutExpired if outcome == 'timeout' else pytest.skip.Exception
    with pytest.raises(expected):
        if target == 'native':
            module.test_registered_generation_direct_actual_http_dom(tmp_path, False)
        elif target == 'http':
            module.test_real_http_dom_generation_entry_and_lost_receipt(env)
        else:
            module.test_task_progress_actual_worker_and_ui_boundaries(env, tmp_path)
    assert seen == [['node', '-e', "require.resolve('jsdom')"]]
