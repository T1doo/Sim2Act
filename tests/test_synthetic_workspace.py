"""Finite boundaries of the explicit blank synthetic entry, no model or provider."""

import json

import pytest
from test_local_record_apps import snapshot

from sim2act import synthetic_workspace as workspace
from sim2act.db import Store
from sim2act.errors import DomainError
from sim2act.worker import Worker


def test_new_is_empty_and_reopen_does_not_initialize_or_mutate(tmp_path, monkeypatch):
    root, store, marker = workspace.open_workspace(tmp_path / "空白 工程", new=True)
    before = snapshot(store)
    assert len(before["principals"]) == 1 and len(before["quotas"]) == 1
    assert all(not rows for name, rows in before.items() if name not in {"principals", "quotas"})
    assert store.authenticate(workspace.TOKEN) == marker["principal_id"]
    store.engine.dispose()
    monkeypatch.setattr(Store, "initialize", lambda *_: pytest.fail("reopen must not migrate"))
    _, cold, restored = workspace.open_workspace(root)
    try:
        assert restored == marker and snapshot(cold) == before
    finally:
        cold.engine.dispose()
    with pytest.raises(workspace.WorkspaceError, match="NEW_DIRECTORY_REQUIRED"):
        workspace.open_workspace(root, new=True)


def test_unknown_and_linked_paths_preserve_foreign_data(tmp_path):
    root = tmp_path / "foreign"
    root.mkdir()
    original = root / "keep.txt"
    original.write_text("unrelated data")
    for new in (False, True):
        with pytest.raises(workspace.WorkspaceError):
            workspace.open_workspace(root, new=new)
    linked = tmp_path / "link"
    linked.symlink_to(root, target_is_directory=True)
    with pytest.raises(workspace.WorkspaceError, match="LINKED_DIRECTORY"):
        workspace.open_workspace(linked)
    assert list(root.iterdir()) == [original] and original.read_text() == "unrelated data"


def test_changed_marker_rejected_before_database_constructor(tmp_path, monkeypatch):
    root, store, _ = workspace.open_workspace(tmp_path / "marked", new=True)
    store.engine.dispose()
    marker = json.loads((root / workspace.MARKER).read_text())
    marker["mode"] = "production"
    (root / workspace.MARKER).write_text(json.dumps(marker))
    db = (root / workspace.DATABASE).read_bytes()
    monkeypatch.setattr(workspace, "Store", lambda *_a, **_k: pytest.fail("unknown marker must not open DB"))
    with pytest.raises(workspace.WorkspaceError, match="UNKNOWN_WORKSPACE"):
        workspace.open_workspace(root)
    assert (root / workspace.DATABASE).read_bytes() == db


def test_settings_and_never_model_do_not_consume_real_configuration(tmp_path, monkeypatch):
    for key in ("SIM2ACT_DATABASE_URL", "SIM2ACT_INTERN_TOKEN", "INTERN_API_TOKEN", "SIM2ACT_LIVE_ENABLED"):
        monkeypatch.setenv(key, "synthetic-environment-value-must-not-be-used")
    monkeypatch.setattr(workspace.Settings, "from_env", lambda: pytest.fail("no environment discovery"))
    settings = workspace.settings_for(tmp_path)
    assert settings.mode == "mock" and not settings.live_enabled and settings.token == ""
    assert settings.goal_planner_provider == "disabled" and not settings.natural_activation_enabled
    assert not settings.application_generation_activation_enabled and not settings.application_generation_live_id
    with pytest.raises(ValueError, match="PostgreSQL"):
        Store(settings.database_url)
    with pytest.raises(DomainError) as caught:
        workspace.NeverModel().request({})
    assert caught.value.code == "UNSUPPORTED_CAPABILITY" and not caught.value.retryable


@pytest.mark.parametrize("definition", [
    "id VARCHAR NOT NULL, name VARCHAR NOT NULL, token_hash VARCHAR",
    "id VARCHAR NOT NULL PRIMARY KEY, name INTEGER NOT NULL, token_hash VARCHAR UNIQUE",
])
def test_cold_open_rejects_same_column_names_with_changed_constraints_or_types(tmp_path, definition):
    root, store, _ = workspace.open_workspace(tmp_path / "changed", new=True)
    with store.engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE principals")
        connection.exec_driver_sql("CREATE TABLE principals (" + definition + ")")
    store.engine.dispose()
    before = (root / workspace.DATABASE).read_bytes()
    with pytest.raises(workspace.WorkspaceError, match="SCHEMA_CHANGED"):
        workspace.open_workspace(root)
    assert (root / workspace.DATABASE).read_bytes() == before


def test_ambiguous_url_directory_is_rejected_before_creation(tmp_path):
    root = tmp_path / "engineering?not-a-query"
    with pytest.raises(workspace.WorkspaceError, match="AMBIGUOUS_DIRECTORY"):
        workspace.open_workspace(root, new=True)
    assert not root.exists() and not (tmp_path / "engineering").exists()


def test_forbidden_model_task_fails_without_stopping_ordinary_worker(env):
    store, settings, _client, principal, _other, project, resource = env
    run = store.submit(principal, project, "Synthetic model task must be refused", [resource], "no-model")
    worker = Worker(store, settings, workspace.NeverModel())
    assert worker.once()
    result = store.inspect(principal, run)
    assert result["status"] == "FAILED" and result["error"]["code"] == "UNSUPPORTED_CAPABILITY"
    assert not worker.once()  # It remains available, with no queued synthetic work.
