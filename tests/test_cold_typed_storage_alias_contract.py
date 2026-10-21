"""Fresh projection obligations on the actual configured PB contract.

No Worker/model/HTTP/Mock is permitted. Unsafe local sketches illustrate why
retained keys or early shallow snapshots cannot replace the original visitor.
"""

import pytest
from conftest import env
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_pb_spec_production_controller import prepare_pb

from sim2act import natural_live_admission as gate
from sim2act import natural_spec_runtime as runtime


@pytest.fixture
def contract(tmp_path, monkeypatch):
    monkeypatch.delenv('SIM2ACT_TEST_DATABASE_URL', raising=False)
    monkeypatch.delenv('SIM2ACT_RECORD_PG_CONFIG', raising=False)
    generator = env.__wrapped__(tmp_path)
    original = next(generator)
    data = None
    try:
        data, binding = prepare_pb(original, tmp_path)
        yield binding.contract
    finally:
        if data is not None and data[2] is not original[2]:
            data[2].close()
        with pytest.raises(StopIteration):
            next(generator)


def project(contract):
    return gate._trial_typed_storage(gate.PBTrialContract, contract)


def wire(contract, shared_key):
    return runtime._cold_graph_bytes(dict(inputs={'shared-key': shared_key},
        binding=dict(contract=contract)))


def test_reusing_actual_caps_dict_merges_an_originally_separate_graph_alias(contract):
    caps = object.__getattribute__(contract.caps, '__dict__')
    current = project(contract)
    assert current['caps'] is not caps
    direct = dict(current, caps=caps)
    assert gate._trial_typed_equal(current, direct)
    def encoded(value):
        return runtime._cold_graph_bytes(dict(inputs={'shared-caps': caps},
            binding=dict(contract=value)))
    assert encoded(current) != encoded(direct)
    original = caps['run_seconds']
    caps['run_seconds'] = original - 1
    try:
        changed = project(contract)
        assert changed['caps'] is not caps
        assert changed['caps']['run_seconds'] == original - 1
        assert current['caps']['run_seconds'] == original
    finally:
        caps['run_seconds'] = original


def test_reused_equal_keys_change_pickle_alias_to_the_current_graph(contract):
    raw = object.__getattribute__(contract, '__dict__')
    old_key = next(key for key in raw if key == 'principal_id')
    new_key = ('fresh-' + old_key)[6:]
    assert new_key == old_key and new_key is not old_key
    retained = project(contract)
    changed = {new_key if key is old_key else key: value for key, value in raw.items()}
    object.__setattr__(contract, '__dict__', changed)
    try:
        current = project(contract)
        # Full current gates/DFS still ran. Updating values cannot replace an
        # existing equal key object in the retained dictionary.
        retained.update(current)
        assert gate._trial_typed_equal(retained, current)
        assert list(retained) == list(current)
        assert next(key for key in current if key == new_key) is new_key
        assert next(key for key in retained if key == new_key) is old_key
        assert wire(retained, new_key) != wire(current, new_key)
    finally:
        object.__setattr__(contract, '__dict__', raw)


def test_copy_before_fresh_dfs_can_hide_a_later_current_scalar(contract):
    raw = object.__getattribute__(contract, '__dict__')
    baseline = project(contract)
    early = dict.copy(raw)
    original = raw['quota_subject']
    # A deterministic interleaving between a proposed copy and its iterator.
    # Same exact storage type; no validation/serializer callback is involved.
    raw['quota_subject'] = original + ':changed'
    try:
        current = project(contract)
        for key, child in raw.items():
            visited = current[key]
            if visited is not child:
                early[key] = visited
        assert current['quota_subject'] == raw['quota_subject']
        assert early['quota_subject'] is original
        assert runtime._cold_graph_bytes(early) == runtime._cold_graph_bytes(baseline)
        assert runtime._cold_graph_bytes(current) != runtime._cold_graph_bytes(baseline)
        # Comparing the INITIAL slot instead repairs this scalar bug, but not
        # the distinct key identity/order bug in the adjacent tests.
        early['quota_subject'] = current['quota_subject']
        assert runtime._cold_graph_bytes(early) == runtime._cold_graph_bytes(current)
    finally:
        raw['quota_subject'] = original


def test_unconditional_patch_does_not_repair_early_key_identity_or_order(contract):
    raw = object.__getattribute__(contract, '__dict__')
    early = dict.copy(raw)
    old_key = next(key for key in raw if key == 'principal_id')
    new_key = ('fresh-' + old_key)[6:]
    changed = {key: value for key, value in raw.items() if key is not old_key}
    changed[new_key] = raw[old_key]
    object.__setattr__(contract, '__dict__', changed)
    try:
        current = project(contract)
        for key in changed:
            early[key] = current[key]
        assert gate._trial_typed_equal(early, current)
        assert list(early) != list(current)
        assert next(key for key in early if key == new_key) is old_key
        assert next(key for key in current if key == new_key) is new_key
        assert wire(early, new_key) != wire(current, new_key)
    finally:
        object.__setattr__(contract, '__dict__', raw)
