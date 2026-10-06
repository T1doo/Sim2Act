import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]/'tests'))
from conftest import env, runtime_role
from test_lifecycle import test_AT05_real_process_stop_accept_restart_reopen as original


@pytest.mark.parametrize('repeat',range(4))
def test_original_at05(env,runtime_role,tmp_path,repeat):
    original(env,runtime_role,tmp_path)
