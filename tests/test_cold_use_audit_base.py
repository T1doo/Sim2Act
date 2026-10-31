"""Original five-Mock prefix, with actual SQL first-publication probes."""
import pytest
from test_cold_binding_graph_integration import test_plain_pb_first_binding_producer_equals_public_complete_ancestry as original
from sim2act import _cold_source_packet as owned, pb_natural_specs as pb, pb_natural_uses as use
from sim2act.errors import DomainError


def test_old_sql_producer_alias_cannot_change_owned_audit(tmp_path,monkeypatch):
    probe={'mode':'producer-alias'}
    original(tmp_path,monkeypatch,_base_probe=probe)
    assert probe['injected'] and probe['complete_hidden_storage_checked']
    assert probe['unknown_callbacks']==[]
    assert not probe['graph'].active


@pytest.mark.parametrize('mode',['flag','holder','pin-rebind'])
def test_first_base_boundary_rejects_foreign_config_or_binding(tmp_path,monkeypatch,mode):
    probe={'mode':mode}
    with pytest.raises(DomainError):original(tmp_path,monkeypatch,_base_probe=probe)
    assert probe['injected'] and probe['unknown_callbacks']==[]
    if 'graph' in probe:assert not probe['graph'].active


def test_postpublication_capacity_error_is_not_normalized_or_replayed(tmp_path,monkeypatch):
    error=owned.image.Bounds('synthetic late boundary failure')
    probe={'mode':'late-bounds','error':error}
    with pytest.raises(owned.image.Bounds) as caught:original(tmp_path,monkeypatch,_base_probe=probe)
    assert caught.value is error
    assert probe['injected'] and probe['complete_hidden_storage_checked']
    assert not probe['graph'].active and probe['unknown_callbacks']==[]


@pytest.mark.parametrize('module,name',[(owned,'current'),(owned,'own_fact'),
    (pb,'_audit_prefix'),(pb,'_cold_audit_prefix'),(pb._ColdExtractionAuditPrefix,'fields')])
def test_use_base_producer_consumer_code_is_qualified_before_dispatch(monkeypatch,module,name):
    calls=[]
    def replaced(*args,**kwargs):calls.append(True);return None
    monkeypatch.setattr(module,name,replaced)
    check,code,defaults=use._USE_OWNED_CHECK
    with pytest.raises(DomainError):check()
    assert calls==[]
