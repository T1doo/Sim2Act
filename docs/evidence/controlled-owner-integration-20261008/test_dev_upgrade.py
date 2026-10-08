"""Integration-only replay of the existing upgrade contract against the prior dev."""
import os

from conftest import env as env
from test_csv_dag_upgrade import (
    test_actual_old_source_upgrade_retains_history_and_requires_new_exact_confirmation as check_upgrade,
)


def test_actual_previous_dev_upgrade(env, tmp_path):
    assert os.environ["SIM2ACT_UPGRADE_DEV_ARCHIVE"]
    check_upgrade(env, tmp_path, "SIM2ACT_UPGRADE_DEV_ARCHIVE", "5bbc462b4ce0027fe9349e4b42064fe75f1470f5",
                  "31a527861308847ef6a2cecc710a542d598377479a914d53e4b1bf63ee1cbb18")
