import json
import subprocess
from pathlib import Path

from conftest import env as env
from test_conditional_checks_ui import test_conditional_checks_actual_http_dom as actual_dom


def test_independent_aba_edit_and_read_boundaries(env, tmp_path, monkeypatch):
    original = subprocess.run

    def isolated_driver(args, *pos, **kwargs):
        if args[:2] == ['node', 'tests/conditional_checks_ui.cjs']:
            args = ['node', '/tmp/conditional-ui-independent/conditional_checks_ui.cjs', *args[2:]]
        return original(args, *pos, **kwargs)

    monkeypatch.setattr(subprocess, 'run', isolated_driver)
    actual_dom(env, tmp_path)
    results = json.loads((tmp_path/'results.json').read_text())
    Path('/tmp/conditional-ui-independent/dom-results.json').write_text(json.dumps(results,indent=2)+'\n')
    Path('/tmp/conditional-ui-independent/dom-driver.log').write_text((tmp_path/'driver.log').read_text())
