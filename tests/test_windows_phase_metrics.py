"""Synthetic optional-diagnostic tests; no PG/network or production configuration."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError
from windows_phase_metrics import Metrics

from sim2act.db import Store, meta


class FakeStore:
    def initialize(self, value=None, *, fail=None):
        if fail is not None:
            raise fail
        return value


def test_wrapped_call_preserves_value_exception_and_restores():
    collector = Metrics()
    original = FakeStore.initialize
    collector.install(FakeStore)
    value = object()
    error = ValueError("SYNTHETIC_SECRET_ERROR")
    try:
        assert FakeStore().initialize(value) is value
        with pytest.raises(ValueError) as failure:
            FakeStore().initialize(fail=error)
        assert failure.value is error
        report = collector.report(2, 0)
        row = next(r for r in report["groups"] if r["family"] == "initialize")
        assert row["count"] == 2 and row["errors"] == 1
        assert "SYNTHETIC_SECRET" not in json.dumps(report)
    finally:
        collector.uninstall()
    assert FakeStore.initialize is original


def test_actual_sqlite_initialization_ddl_existence_errors_and_redaction():
    collector = Metrics()
    store = Store("sqlite:///:memory:", test_only=True)
    collector.install(Store)
    try:
        store.initialize()
        first = collector.report(1, 0)
        assert inspect(store.engine).get_table_names() == sorted(meta.tables)
        store.initialize()  # Original idempotency remains, not checkfirst=False.
        with store.engine.begin() as connection:
            assert (
                connection.execute(
                    text("SELECT :secret"), {"secret": "SYNTHETIC_PARAMETER_SECRET"}
                ).scalar()
                == "SYNTHETIC_PARAMETER_SECRET"
            )
            with pytest.raises(OperationalError):
                connection.execute(text("SELECT * FROM SYNTHETIC_SQL_SECRET_MISSING"))
        final = collector.report(1, 0)
        serialized = json.dumps(final)
        assert "SYNTHETIC" not in serialized and "memory" not in serialized
        assert final["pending_sql"] == 0
        initializations = [r for r in final["groups"] if r["family"] == "initialize"]
        assert sum(r["count"] for r in initializations) == 2
        existence = [
            r
            for r in first["groups"]
            if r["family"] == "sql" and r["labels"] == ["initialization", "sqlite", "existence"]
        ]
        ddl = [
            r
            for r in first["groups"]
            if r["family"] == "sql" and r["labels"] == ["initialization", "sqlite", "ddl"]
        ]
        assert existence and existence[0]["count"] >= len(meta.tables)
        assert ddl and ddl[0]["count"] >= len(meta.tables)
        assert any(r["errors"] == 1 for r in final["groups"] if r["family"] == "sql")
        assert all(r["seconds"] >= 0 and r["max_seconds"] >= 0 for r in final["groups"])
    finally:
        collector.uninstall()
        store.engine.dispose()


def test_uninstall_does_not_clobber_later_test_patch():
    collector = Metrics()
    original = FakeStore.initialize
    collector.install(FakeStore)

    def replacement(*_args, **_kwargs):
        return "test owns this patch"

    FakeStore.initialize = replacement
    try:
        collector.uninstall()
        assert FakeStore.initialize is replacement
    finally:
        FakeStore.initialize = original


def invoke(directory, *extra):
    source = Path(__file__).resolve().parents[1]
    environment = dict(os.environ)
    # Private existing environment values are not passed to diagnostic children.
    environment = {
        key: value
        for key, value in environment.items()
        if not key.startswith("SIM2ACT_") and key != "INTERN_API_TOKEN"
    }
    environment["PYTHONPATH"] = os.pathsep.join([str(source / "tests"), str(source / "src")])
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "--confcutdir",
            str(directory),
            str(directory / "sample.py"),
            *extra,
        ],
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_explicit_plugin_keeps_collection_outcomes_fixtures_and_secrets(tmp_path):
    (tmp_path / "sample.py").write_text("""
import pytest
from sim2act.db import Store
@pytest.fixture(scope="module")
def SYNTHETIC_SECRET_FIXTURE():
    store=Store("sqlite:///:memory:", test_only=True)
    store.initialize()
    yield store
    store.engine.dispose()
def test_ok(SYNTHETIC_SECRET_FIXTURE):
    assert SYNTHETIC_SECRET_FIXTURE.sqlite
def test_original_failure(SYNTHETIC_SECRET_FIXTURE):
    assert False, "original assertion preserved"
""")
    baseline = invoke(tmp_path)
    output = tmp_path / "metrics.json"
    measured = invoke(
        tmp_path, "-p", "windows_phase_metrics", "--windows-metrics-output", str(output)
    )
    assert baseline.returncode == measured.returncode == 1
    assert "1 failed, 1 passed" in baseline.stdout and "1 failed, 1 passed" in measured.stdout
    report = json.loads(output.read_text())
    assert report["collected_cases"] == 2 and report["pytest_exitstatus"] == 1
    assert "SYNTHETIC_SECRET" not in output.read_text()
    fixtures = [r for r in report["groups"] if r["family"] == "fixture_setup"]
    assert any(r["labels"] == ["other", "module"] and r["count"] >= 1 for r in fixtures)
    assert any(r["family"] == "initialize" and r["count"] == 1 for r in report["groups"])


def test_loaded_without_output_is_inert_and_missing_output_path_keeps_test_outcome(tmp_path):
    (tmp_path / "sample.py").write_text("""
from sim2act.db import Store
from windows_phase_metrics import Metrics
def test_inert():
    from pathlib import Path
    assert Path(Store.initialize.__code__.co_filename).name == "db.py"
    store=Store("sqlite:///:memory:",test_only=True)
    store.initialize()
    store.engine.dispose()
""")
    inert = invoke(tmp_path, "-p", "windows_phase_metrics")
    assert inert.returncode == 0
    assert not list(tmp_path.glob("*metrics.json"))
    (tmp_path / "sample.py").write_text("def test_ok():\n    assert True\n")
    failed_output = invoke(
        tmp_path,
        "-p",
        "windows_phase_metrics",
        "--windows-metrics-output",
        str(tmp_path / "SYNTHETIC_PATH_SECRET" / "metrics.json"),
    )
    assert failed_output.returncode == 0
    assert "Phase metrics unavailable (FileNotFoundError)" in failed_output.stdout
    assert "SYNTHETIC_PATH_SECRET" not in failed_output.stdout
