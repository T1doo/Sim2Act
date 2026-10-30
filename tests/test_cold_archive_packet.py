"""Owned post archive data: complete schema, aliases and all consumer gates."""
from types import SimpleNamespace
import pytest
from sim2act import _cold_archive_packet as packet
from sim2act.errors import DomainError
from sim2act.natural_spec_runtime import _cold_graph_bytes


def values():
    receipt = {k: 'synthetic-' + k for k in packet._RECEIPT_STR}
    receipt.update({k: False for k in packet._RECEIPT_BOOL})
    receipt.update({k: 0 for k in packet._RECEIPT_INT})
    receipt['attempts'] = [{**{k: 'synthetic-'+k+str(i) for k in packet._PROOF_STR},
                            **{k: i+1 for k in packet._PROOF_INT}} for i in range(2)]
    wire = bytes(bytearray(b'original-synthetic-request-body-0000001'))
    body = bytes(bytearray(b'original-synthetic-response-body-000001'))
    return receipt, (wire, wire), (body, wire)


def assert_tree_immutable(value):
    assert type(value) in (tuple, bytes, str, int, bool)
    if type(value) is tuple:
        for child in value:assert_tree_immutable(child)


def test_handoff_owns_all_fields_and_no_mutable_producer_references():
    receipt, requests, responses = values()
    expected_order = tuple(receipt)
    saved = packet.capture(receipt, requests, responses)
    assert_tree_immutable(saved)
    receipt['source_run_id'] = 'changed'
    receipt['attempts'][0]['attempt_id'] = 'changed'
    receipt['attempts'].clear()
    receipt.clear()
    view, req, res = packet.read(saved)
    assert tuple(view) == expected_order
    assert view['source_run_id'] == 'synthetic-source_run_id'
    assert len(view['attempts']) == 2
    assert view['attempts'][0]['attempt_id'] == 'synthetic-attempt_id0'
    assert req[0] is req[1] is res[1] is requests[0]
    assert res[0] is responses[0]
    with pytest.raises((AttributeError,TypeError)):object.__setattr__(view,'anything',{})
    with pytest.raises(TypeError):view['source_run_id'] = 'forged'


def test_mutable_container_alias_partition_and_order_are_encoded():
    receipt, requests, responses = values()
    proof = receipt['attempts'][0]
    receipt['attempts'][1] = proof
    saved = packet.capture(receipt, requests, responses)
    view,_,_ = packet.read(saved)
    first,second = view['attempts']
    assert tuple.__getitem__(first,2) == tuple.__getitem__(second,2)
    assert view['attempts'].index(second) == 0
    receipt['attempts'][1] = dict(proof)
    split = packet.capture(receipt, requests, responses)
    assert saved[1] != split[1]
    receipt['attempts'][1] = dict(reversed(tuple(proof.items())))
    reordered = packet.capture(receipt, requests, responses)
    assert reordered[1] != split[1]


def test_full_pin_keeps_cross_family_immutable_leaf_aliases():
    receipt, requests, responses = values()
    saved = packet.capture(receipt, requests, responses)
    root = dict(owned=saved, outside=requests[0])
    before = _cold_graph_bytes(root)
    clone = bytes(bytearray(requests[0]));assert clone is not requests[0]
    root['outside'] = clone
    assert _cold_graph_bytes(root) != before
    # Equal payload with a split internal alias must also alter complete pin.
    split = packet.capture(receipt, (requests[0], clone), responses)
    assert _cold_graph_bytes(saved) != _cold_graph_bytes(split)


@pytest.mark.parametrize('change', ['extra','missing','proof-extra','bool-counter','tuple-proofs','body-type'])
def test_unknown_complete_shape_never_drops_fields(change):
    receipt, requests, responses = values()
    if change=='extra':receipt['ignored'] = 'must-not-drop'
    if change=='missing':receipt.pop('project_writes')
    if change=='proof-extra':receipt['attempts'][1]['ignored']='must-not-drop'
    if change=='bool-counter':receipt['new_model_requests'] = False
    if change=='tuple-proofs':receipt['attempts'] = tuple(receipt['attempts'])
    if change=='body-type':requests = (bytearray(requests[0]),requests[1])
    with pytest.raises(DomainError):packet.capture(receipt,requests,responses)


def test_capacity_is_prepublication_fallback_and_identity_is_bound():
    receipt,requests,responses=values()
    receipt['version']='x'*(packet._MAX_LEAVES//4+1)
    with pytest.raises(packet.Capacity):packet.capture(receipt,requests,responses)
    saved=packet.capture(*values()); graph=SimpleNamespace(phase='post',inputs={packet.KEY:saved})
    assert packet.bound(graph,saved)[0]['new_reservations']==0
    duplicate=tuple(list(saved));assert duplicate is not saved
    with pytest.raises(DomainError):packet.bound(graph,duplicate)
    graph.phase='pre'
    with pytest.raises(DomainError):packet.bound(graph,saved)


@pytest.mark.parametrize('wire', [b'',b'S2A\x01',b'S2A\x01\x01\x00\x00\x00q\x01\x00\x00\x00',
    b'S2A\x01\x01\x00\x00\x00q\xff\xff', b'S2A\x01\x01\x00\x00\x00z'])
def test_corrupt_metadata_is_rejected_without_dispatch(wire):
    with pytest.raises(DomainError):packet.read((packet.TAG,wire,()))


def test_both_experimental_archive_consumers_explicitly_refuse_new_packet():
    from sim2act import cold_accounted, _cold_accounted_native as native, pa_trial_dispatch as dispatch
    saved=packet.capture(*values())
    for call in (lambda:cold_accounted._archive_chain(None,None,saved),
                 lambda:native._resolved_shape(saved),
                 lambda:dispatch._archive_chain_from_facts(None,None,saved,None)):
        with pytest.raises(DomainError):call()


@pytest.mark.parametrize('change', ['extra','duplicate'])
def test_unused_or_duplicate_leaf_carrier_cannot_smuggle_data(change):
    saved=packet.capture(*values())
    leaves=saved[2]+('unreferenced synthetic leaf',) if change=='extra' else saved[2]+(saved[2][0],)
    with pytest.raises(DomainError):packet.read((saved[0],saved[1],leaves))


@pytest.mark.parametrize('change', ['decoder','defaults','view','join'])
def test_changed_decoder_view_and_consumer_code_is_not_accepted(monkeypatch,change):
    from sim2act import pa_trial_dispatch as dispatch
    saved=packet.capture(*values()); graph=SimpleNamespace(phase='post',inputs={packet.KEY:saved})
    if change=='decoder':monkeypatch.setattr(packet,'read',lambda value: ('forged',))
    if change=='defaults':monkeypatch.setattr(packet.read,'__defaults__',(None,))
    if change=='view':monkeypatch.setattr(packet._View,'__getitem__',lambda self,key:'forged')
    if change=='join':monkeypatch.setattr(dispatch,'_archive_chain_values',lambda *a,**k:None)
    with pytest.raises(DomainError):
        packet.current(packet._CONFIG,dispatch._OWNED_ARCHIVE_CONSUMERS)
        packet.bound(graph,saved)


@pytest.mark.parametrize('replacement',[None, 'legacy', 'tag'])
def test_published_packet_cannot_be_replaced_by_unmigrated_shape(replacement):
    from sim2act import natural_spec_runtime as rt, natural_source_archives as archive
    saved=packet.capture(*values()); g=SimpleNamespace(phase='post',inputs={packet.KEY:saved})
    trial=object.__new__(rt._ColdTrialGraph)
    for k,v in dict(platform=None,trial=None,audit_seed=None,phase='BUILDING',guard=g,
        resolved=saved,context_record=None,authority_record=None).items():setattr(trial,k,v)
    rt._ColdTrialGraph._check_links(trial)
    trial.resolved = None if replacement is None else archive.ResolvedSourceArchive(*values()) if replacement=='legacy' else ('bad-tag',saved[1],saved[2])
    with pytest.raises(DomainError):rt._ColdTrialGraph._check_links(trial)


@pytest.mark.parametrize('change',['class','init','classifier'])
def test_changed_capacity_or_classifier_is_not_executed(monkeypatch,change):
    events=[]
    original_capacity=packet.Capacity
    if change=='class':monkeypatch.setattr(packet,'Capacity',DomainError)
    if change=='init':monkeypatch.setattr(original_capacity,'__init__',lambda *a:events.append('callback'),raising=False)
    if change=='classifier':monkeypatch.setattr(packet,'is_packet',lambda *a:events.append('callback') or True)
    with pytest.raises(DomainError):packet.capture(*values())
    assert events==[]
