"""Initialization argument plumbing only: no PG, new identity or credential."""

import sys
from types import SimpleNamespace

import pytest

from sim2act import cli


@pytest.mark.parametrize(
    "command", ["migrate", "init-user", "probe", "schemas", "synthetic-workspace"]
)
def test_explicit_empty_config_never_falls_back_to_inherited_authority(monkeypatch, command):
    monkeypatch.setattr(sys, "argv", ["sim2act", command, "--config", ""])
    monkeypatch.setattr(cli.Settings, "from_env", lambda: pytest.fail("must not inherit settings"))
    monkeypatch.setattr(cli, "Store", lambda *_: pytest.fail("must not open inherited database"))
    monkeypatch.setattr(
        cli.secrets, "token_urlsafe", lambda *_: pytest.fail("must not create token")
    )
    with pytest.raises(SystemExit) as stopped:
        cli.main()
    assert stopped.value.code == (1 if command in {"migrate", "init-user"} else 2)


def test_installed_migration_uses_explicit_existing_config_and_original_quota(
    tmp_path, monkeypatch, capsys
):
    path = tmp_path / "private.env"
    path.write_text("SIM2ACT_DATA_DIR=selected\n")
    calls = []
    monkeypatch.setenv("SIM2ACT_DATA_DIR", "before")
    monkeypatch.setattr(sys, "argv", ["sim2act", "migrate", "--config", str(path)])

    def settings():
        import os

        assert os.environ["SIM2ACT_DATA_DIR"] == "selected"
        return SimpleNamespace(database_url="synthetic-no-connect", quota_subject="fixed-subject")

    monkeypatch.setattr(cli.Settings, "from_env", settings)
    monkeypatch.setattr(
        cli,
        "Store",
        lambda url: SimpleNamespace(
            initialize=lambda subject: calls.append(("initialize", subject)),
            engine=SimpleNamespace(dispose=lambda: calls.append(("dispose",))),
        ),
    )
    monkeypatch.setattr(
        cli.secrets, "token_urlsafe", lambda *_: pytest.fail("migration cannot create credentials")
    )
    cli.main()
    assert calls == [("initialize", "fixed-subject"), ("dispose",)]
    assert "Schema initialized" in capsys.readouterr().out


@pytest.mark.parametrize("command", ["probe", "schemas", "synthetic-workspace"])
def test_private_config_is_rejected_before_static_or_synthetic_entry(
    tmp_path, monkeypatch, command
):
    path = tmp_path / "must-not-read.env"
    monkeypatch.setattr(sys, "argv", ["sim2act", command, "--config", str(path)])
    monkeypatch.setattr(cli.Settings, "from_env", lambda: pytest.fail("must not read settings"))
    monkeypatch.setattr(
        cli.secrets, "token_urlsafe", lambda *_: pytest.fail("must not create a credential")
    )
    with pytest.raises(SystemExit) as stopped:
        cli.main()
    assert stopped.value.code == 2 and not path.exists()


@pytest.mark.parametrize("failure", ["config", "store", "cleanup"])
def test_initialization_failure_never_prints_private_exception_or_claims_rollback(
    tmp_path, monkeypatch, capsys, failure
):
    path = tmp_path / "selected.env"
    path.write_text("invalid line\n" if failure == "config" else "SIM2ACT_DATA_DIR=selected\n")
    monkeypatch.setenv("SIM2ACT_DATA_DIR", "before")
    monkeypatch.setattr(sys, "argv", ["sim2act", "migrate", "--config", str(path)])
    monkeypatch.setattr(
        cli.Settings,
        "from_env",
        lambda: SimpleNamespace(database_url="synthetic", quota_subject="fixed"),
    )

    def fail():
        raise RuntimeError("PRIVATE_SENTINEL_DSN_OR_PASSWORD")

    monkeypatch.setattr(
        cli,
        "Store",
        lambda url: (
            fail()
            if failure == "store"
            else SimpleNamespace(initialize=lambda _: None, engine=SimpleNamespace(dispose=fail))
        ),
    )
    monkeypatch.setattr(
        cli.secrets, "token_urlsafe", lambda *_: pytest.fail("never create a credential")
    )
    with pytest.raises(SystemExit) as stopped:
        cli.main()
    assert stopped.value.code == 1
    output = capsys.readouterr()
    assert "PRIVATE_SENTINEL" not in output.out + output.err and "not confirmed" in output.err
