"""Local candidate data isolation and loopback read-only boundary; no model."""

import importlib.util
import json
from pathlib import Path

import pytest

from sim2act.db import Store

SPEC = importlib.util.spec_from_file_location(
    "local_candidate_demo", Path(__file__).parents[1] / "scripts/local_candidate_demo.py")
demo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(demo)


def test_existing_directory_never_initialized_or_deleted(tmp_path):
    original = tmp_path / "unknown.txt"
    original.write_text("keep unknown user data")
    with pytest.raises(RuntimeError, match="NEW directory"):
        demo.prepare(tmp_path)
    assert sorted(path.name for path in tmp_path.iterdir()) == ["unknown.txt"]
    assert original.read_text() == "keep unknown user data"


def test_settings_ignore_real_environment(tmp_path, monkeypatch):
    for key, value in {"SIM2ACT_MODEL_MODE": "live", "SIM2ACT_LIVE_ENABLED": "true",
        "SIM2ACT_DATABASE_URL": "postgresql+psycopg://do-not-connect.invalid/private",
        "SIM2ACT_INTERN_TOKEN": "synthetic-must-not-read", "INTERN_API_TOKEN": "ignore-alias",
        "SIM2ACT_APPLICATION_GENERATION_LIVE_ID": "gaapproval_" + "0" * 32}.items():
        monkeypatch.setenv(key, value)
    settings = demo.settings_for(tmp_path)
    assert settings.mode == "mock" and not settings.live_enabled and settings.token == ""
    assert settings.application_generation_live_id == settings.natural_activation_live_id == ""
    assert settings.database_url == "sqlite:///" + str(tmp_path / demo.DATABASE)
    with pytest.raises(ValueError):
        Store(settings.database_url)  # Ordinary Store still refuses SQLite.


@pytest.mark.parametrize("fault", ["marker", "database_link", "receipt_link", "root_link"])
def test_cold_open_rejects_unknown_or_linked_data(tmp_path, fault):
    root = tmp_path / "fixture"
    root.mkdir()
    (root / "fixture.json").write_text(json.dumps(demo.MARKER))
    (root / demo.DATABASE).write_text("placeholder, never opened")
    (root / "demo-receipt.json").write_text("{}")
    target = tmp_path / "foreign"
    target.write_text("private data preserved")
    if fault == "marker":
        (root / "fixture.json").write_text('{"mode":"unknown"}')
    elif fault == "root_link":
        link = tmp_path / "linked"
        link.symlink_to(root, target_is_directory=True)
        root = link
    else:
        name = demo.DATABASE if fault == "database_link" else "demo-receipt.json"
        (root / name).unlink()
        (root / name).symlink_to(target)
    with pytest.raises(RuntimeError):
        demo.checked_directory(root)
    assert target.read_text() == "private data preserved"


def test_cold_server_real_loopback_only_get_and_no_database_writes(tmp_path):
    settings = demo.settings_for(tmp_path)
    store = Store(settings.database_url, test_only=True)
    try:
        store.initialize()
        store.user("public synthetic", demo.PUBLIC_TOKEN)
        before = demo.snapshot(store)
        with demo.loopback(store, settings, read_only=True) as (client, url):
            assert url.startswith("http://127.0.0.1:")
            assert client.get("/").status_code == 200
            assert client.get("/api/projects").json() == []
            for method in ["POST", "PUT", "PATCH", "DELETE"]:
                assert client.request(method, "/api/projects", json={"name": "blocked"}).status_code == 405
        assert demo.snapshot(store) == before
    finally:
        store.engine.dispose()
