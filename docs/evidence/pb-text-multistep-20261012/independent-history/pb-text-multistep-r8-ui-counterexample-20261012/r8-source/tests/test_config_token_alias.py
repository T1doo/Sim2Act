"""Synthetic configuration only; no ambient environment, files or live transport."""

import re
from pathlib import Path

import pytest

from sim2act import config


@pytest.mark.parametrize(
    "variables,expected",
    [
        ({}, ""),
        ({"INTERN_API_TOKEN": "SYNTHETIC_ALIAS_ONLY"}, "SYNTHETIC_ALIAS_ONLY"),
        ({"SIM2ACT_INTERN_TOKEN": "SYNTHETIC_DEDICATED_ONLY"}, "SYNTHETIC_DEDICATED_ONLY"),
        (
            {"SIM2ACT_INTERN_TOKEN": "SYNTHETIC_DEDICATED", "INTERN_API_TOKEN": "SYNTHETIC_ALIAS"},
            "SYNTHETIC_DEDICATED",
        ),
        ({"SIM2ACT_INTERN_TOKEN": "", "INTERN_API_TOKEN": "SYNTHETIC_ALIAS"}, "SYNTHETIC_ALIAS"),
        ({"SIM2ACT_INTERN_TOKEN": "", "INTERN_API_TOKEN": ""}, ""),
    ],
)
def test_token_names_priority_and_no_live_enablement(
    monkeypatch, tmp_path, capsys, variables, expected
):
    # Replace the mapping entirely: never examine or inherit actual credentials.
    monkeypatch.setattr(
        config.os,
        "environ",
        {
            "SIM2ACT_DATABASE_URL": "postgresql+psycopg://synthetic.invalid/synthetic",
            "SIM2ACT_DATA_DIR": str(tmp_path),
            **variables,
        },
    )
    settings = config.Settings.from_env()
    assert settings.token == expected
    assert settings.mode == "mock" and settings.live_enabled is False
    assert capsys.readouterr() == ("", "")


def test_explicit_powershell_config_accepts_alias_and_restricts_names():
    # Static parser contract; does not claim native PowerShell execution.
    root = Path(__file__).resolve().parents[1]
    source = (root / "scripts/Common.ps1").read_text()
    pattern = re.search(r"-notmatch '([^']+)'", source).group(1)
    for name in ["SIM2ACT_INTERN_TOKEN", "INTERN_API_TOKEN"]:
        match = re.fullmatch(pattern, name + "=SYNTHETIC_ONLY")
        assert match and match.group(1) == name and match.group(2) == "SYNTHETIC_ONLY"
    for name in ["UNRELATED_TOKEN", "OTHER_INTERN_API_TOKEN", "INTERN_API_TOKEN_SUFFIX"]:
        assert re.fullmatch(pattern, name + "=SYNTHETIC_ONLY") is None
    template = (root / ".env.example").read_text()
    assert "SIM2ACT_INTERN_TOKEN=\n" in template and "INTERN_API_TOKEN=\n" in template
