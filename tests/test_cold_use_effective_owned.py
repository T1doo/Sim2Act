"""Complete candidate consumers, retired aliases and publication failures."""
import pytest
import subprocess
import sys
from test_cold_binding_graph_integration import test_plain_pb_first_binding_producer_equals_public_complete_ancestry as original
from sim2act import _cold_source_packet as owned, pb_natural_uses as use
from sim2act.errors import DomainError


@pytest.mark.parametrize('mode', ['producer-alias', 'pre-bounds', 'facet'])
def test_actual_candidate_owner_or_prepublication_fallback_keeps_complete_result(tmp_path, monkeypatch, mode):
    probe = {'mode': mode}
    original(tmp_path, monkeypatch, _effective_probe=probe)
    assert probe['injected'] and probe['consumers_checked']
    if mode == 'facet':assert probe['facet_checked']
    transfers = probe['transfers']
    assert transfers
    for i, left in enumerate(transfers):
        for right in transfers[i + 1:]:
            if left['graph'] is not right['graph'] or left['name'] != right['name']:
                assert left['view'].owner() is not right['view'].owner()
    assert all(not entry['graph'].active for entry in transfers)


def test_actual_candidate_root_rebinding_invalidates_before_return(tmp_path, monkeypatch):
    probe = {'mode': 'pin-rebind'}
    with pytest.raises(DomainError):
        original(tmp_path, monkeypatch, _effective_probe=probe)
    assert probe['injected'] and not probe['graph'].active


def test_candidate_late_capacity_error_is_same_exception_not_raw_replay(tmp_path, monkeypatch):
    error = owned.image.Bounds('synthetic postpublication candidate failure')
    probe = {'mode': 'late-bounds', 'error': error}
    with pytest.raises(owned.image.Bounds) as caught:
        original(tmp_path, monkeypatch, _effective_probe=probe)
    assert caught.value is error
    assert probe['injected'] and not probe['graph'].active


def test_candidate_producer_code_is_qualified_before_dispatch(monkeypatch):
    calls = []
    def changed(*args, **kwargs):calls.append(True)
    monkeypatch.setattr(use, '_cold_effective_candidate', changed)
    with pytest.raises(DomainError):owned.current()
    assert calls == []


def test_missing_optional_native_extension_retains_original_candidate():
    code = r'''
import importlib.abc,sys
class MissingNative(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname=='sim2act._cold_source_owned_impl':raise ImportError('synthetic absent optional extension')
sys.meta_path.insert(0,MissingNative())
from types import SimpleNamespace
from sim2act import pb_natural_uses as use
assert use._USE_OWNED_ENABLED is False
value={'complete':['original','candidate']}
declared=object();published=[]
guard=SimpleNamespace(_accounted_frontier=None,add=lambda *args:published.append(args))
assert use._cold_effective_candidate(guard,'original',value,declared) is value
assert published==[('original:expanded',{'effective_candidate':value,'declared_limits':declared})]
assert published[0][1]['effective_candidate'] is value and published[0][1]['declared_limits'] is declared
'''
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
