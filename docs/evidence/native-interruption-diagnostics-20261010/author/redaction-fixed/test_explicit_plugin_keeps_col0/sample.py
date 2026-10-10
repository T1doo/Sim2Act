
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
