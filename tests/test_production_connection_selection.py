"""Explicit configuration and existing trial selection; no model/network calls."""

import importlib.util
import json
import os
from dataclasses import replace
from pathlib import Path

import pytest
from test_natural_trial_preparation import business, consent, scope
from test_natural_trial_preparation import prepared_data as prepared_data

from sim2act import natural_trial_preparation as prep
from sim2act import spec_production as production
from sim2act.errors import DomainError
from sim2act.production_evidence import ACCOUNT_ID
from sim2act.production_trial_admission import canonical_quota_subject

spec = importlib.util.spec_from_file_location(
    "local_manage", Path(__file__).parents[1] / "scripts/manage.py"
)
manage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manage)


def selection():
    return dict(
        user="user_" + "a" * 32,
        project="proj_" + "b" * 32,
        trial="saved-trial",
        approval="saved-approval",
        account=ACCOUNT_ID,
    )


def test_explicit_selection_rejects_duplicates_unknown_credentials_and_partial(tmp_path):
    path = tmp_path / "selection.json"
    for value in [
        [],
        {},
        dict(selection(), token="SYNTHETIC-PRIVATE"),
        dict(selection(), account="other"),
        dict(selection(), user="other"),
    ]:
        path.write_text(json.dumps(value))
        with pytest.raises(ValueError, match="five-field"):
            manage.production_selection(path)
    path.write_text('{"user":"first","user":"second"}')
    with pytest.raises(ValueError):
        manage.production_selection(path)
    path.write_text(json.dumps(selection()))
    selected = manage.production_selection(path)
    assert selected == selection()
    command = manage.selection_worker_arguments(selected)
    assert len(command) == 10 and dict(zip(command[::2], command[1::2], strict=True)) == {
        "--spec-production-" + k: v for k, v in selected.items()
    }


def test_config_is_explicit_atomic_and_does_not_execute_values(tmp_path, monkeypatch):
    path = tmp_path / "private.env"
    marker = tmp_path / "must-not-exist"
    monkeypatch.delenv("SIM2ACT_DATA_DIR", raising=False)
    path.write_text("SIM2ACT_DATA_DIR=$(touch " + str(marker) + ")\nBAD KEY=secret\n")
    with pytest.raises(ValueError):
        manage.import_config(path)
    assert "SIM2ACT_DATA_DIR" not in os.environ and not marker.exists()
    path.write_text("SIM2ACT_DATA_DIR=first\nSIM2ACT_MODEL_MODE=live\x00bad\n")
    with pytest.raises(ValueError):
        manage.import_config(path)
    assert "SIM2ACT_DATA_DIR" not in os.environ
    path.write_text("SIM2ACT_DATA_DIR=first\nSIM2ACT_DATA_DIR=second\n")
    with pytest.raises(ValueError):
        manage.import_config(path)
    path.write_text("SIM2ACT_DATA_DIR=$(touch " + str(marker) + ")\n")
    manage.import_config(path)
    assert os.environ["SIM2ACT_DATA_DIR"].startswith("$(touch ") and not marker.exists()


def test_bounded_validation_preserves_existing_connection_options(tmp_path):
    from sqlalchemy.engine import make_url

    from sim2act.config import Settings

    settings = Settings(
        "postgresql+psycopg://synthetic-app@127.0.0.1/fixture?options=-c+search_path%3Dexisting&sslmode=require",
        tmp_path,
    )
    store = manage.validation_store(settings)
    try:
        q = make_url(store.engine.url).query
        assert q["sslmode"] == "require" and q["connect_timeout"] == "5"
        assert (
            q["options"] == "-c search_path=existing -c statement_timeout=5000 -c lock_timeout=1000"
        )
    finally:
        store.engine.dispose()


def test_live_preparation_cannot_use_test_sqlite_or_silently_fall_back(prepared_data):
    data, body = prepared_data
    before = business(data[0])
    settings = replace(data[1], mode="live", live_enabled=True)
    with pytest.raises(DomainError, match="postgresql_application_database"):
        prep.prepare(
            data[0], data[3], data[4], "live-blocked", prep.PrepareInput(**body), settings=settings
        )
    assert business(data[0]) == before
    from sqlalchemy import select

    from sim2act.db import delivery_graph_requests

    with data[0].tx() as c:
        assert not c.execute(
            select(delivery_graph_requests).where(delivery_graph_requests.c.kind == prep.PREPARE)
        ).first()


def test_old_key_is_not_rebound_and_new_server_branch_exports_only_approved_selection(
    prepared_data, monkeypatch
):
    data, body, base, old = scope(prepared_data)
    assert old["contract"]["quota_subject"] == "unconfigured:" + data[3]
    assert old["worker_selection"] is None
    settings = replace(
        data[1], mode="live", live_enabled=True, quota_subject=canonical_quota_subject(ACCOUNT_ID)
    )
    calls = []
    # Synthetic branch exercise ONLY. Genuine PG/LIVE entry remains closed below.
    with monkeypatch.context() as branch:
        branch.setattr(production, "environment", lambda *args: calls.append(args))
        replay = prep.prepare(
            data[0],
            data[3],
            data[4],
            "original-preparation",
            prep.PrepareInput(**body),
            settings=settings,
        )
        assert replay == old and not calls
        new = prep.prepare(
            data[0],
            data[3],
            data[4],
            "new-configured",
            prep.PrepareInput(**body),
            settings=settings,
        )
        assert len(calls) == 1 and calls[0][1] is settings
    assert new["contract"]["quota_subject"] == canonical_quota_subject(ACCOUNT_ID)
    assert new["worker_selection"] is None
    route = base.replace("original-preparation", "new-configured")
    approved = data[2].post(route + "/consent", json=consent(new))
    assert approved.status_code == 200, approved.text
    recovered = data[2].get(route + "/preparation").json()
    expected = dict(
        user=data[3],
        project=data[4],
        trial="new-configured",
        approval=prep.approval_key(prep.gate.parse_contract(new["contract"])),
        account=ACCOUNT_ID,
    )
    assert recovered["worker_selection"] == expected
    assert recovered["live_allowed"] is False and recovered["actual_model_requests"] == 0
    with pytest.raises(DomainError, match="disabled"):
        production.install(
            data[0],
            settings,
            user=data[3],
            project_id=data[4],
            trial_key="new-configured",
            approval_key=expected["approval"],
            account_id=ACCOUNT_ID,
        )
    revoked = data[2].post(
        route + "/withdrawal", json=dict(review_token=new["review_token"], confirm_withdrawal=True)
    )
    assert revoked.status_code == 200
    assert data[2].get(route + "/preparation").json()["worker_selection"] is None
    assert business(data[0])["runs"] == business(data[0])["attempts"] == []


def test_rejected_selection_starts_no_api_or_worker(tmp_path, monkeypatch, capsys):
    from sim2act.config import Settings

    path = tmp_path / "selection.json"
    path.write_text(json.dumps(selection()))
    data = tmp_path / "not-created"
    settings = Settings("postgresql+psycopg://synthetic@127.0.0.1/fixture", data)
    monkeypatch.setattr(Settings, "from_env", lambda: settings)
    monkeypatch.setattr(manage.sys, "argv", ["manage.py", "start", "--spec-selection", str(path)])

    def rejected(*args):
        raise DomainError("PERMISSION_DENIED", "SYNTHETIC-PRIVATE-NOT-PRINTED")

    monkeypatch.setattr(manage, "check_selection", rejected)

    def forbidden(*args, **kwargs):
        pytest.fail("Rejected trial must not start even the API")

    monkeypatch.setattr(manage.subprocess, "Popen", forbidden)
    with pytest.raises(SystemExit) as stopped:
        manage.main()
    assert stopped.value.code == 1
    output = capsys.readouterr()
    assert "No process started" in output.err
    assert "SYNTHETIC-PRIVATE-NOT-PRINTED" not in output.err + output.out
    assert not data.exists()


def test_original_selection_must_have_existing_quota_without_inserting(tmp_path, monkeypatch):
    from sqlalchemy import select

    from sim2act.config import Settings
    from sim2act.db import Store, quotas

    store = Store("sqlite:///" + str(tmp_path / "synthetic.db"), test_only=True)
    store.initialize("old-default")
    subject = canonical_quota_subject(ACCOUNT_ID)
    settings = Settings(store.engine.url.render_as_string(), tmp_path, quota_subject=subject)
    calls = []
    # Fixture isolates the extra read-only quota check, not production authority.
    monkeypatch.setattr(production, "install", lambda *a, **kw: calls.append(kw))
    with pytest.raises(ValueError, match="QUOTA_SUBJECT_NOT_INITIALIZED"):
        manage.check_selection(store, settings, selection())
    with store.engine.connect() as c:
        assert list(c.execute(select(quotas.c.subject)).scalars()) == ["old-default"]
    assert len(calls) == 1
    store.initialize(subject)  # Explicit synthetic migration, never done by check.
    manage.check_selection(store, settings, selection())
    store.engine.dispose()
