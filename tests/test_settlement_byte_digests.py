"""Arithmetic reuse is limited to exact immutable bytes in one proof."""

from sim2act import natural_spec_runtime as runtime


def proof(inputs):
    p = object.__new__(runtime._ModelSettlementRead)
    p.inputs = inputs
    p._byte_digests = {}
    p.authorities = set()
    return p


def test_repeated_bytes_hash_matches_fresh_and_mutable_parents_are_revisited():
    wire = bytes(bytearray(b"complete wire"))
    p = proof({"wire": wire, "nested": [{"version": 1}]})
    expected = runtime._model_inputs(p.inputs)
    assert p._inputs_key() == expected
    assert p._byte_digests[id(wire)][0] is wire
    assert p._inputs_key() == expected
    p.inputs["nested"][0]["version"] = 2
    assert p._inputs_key() != expected
    assert p._inputs_key() == runtime._model_inputs(p.inputs)


def test_replacing_bytes_recomputes_and_prunes_removed_identity():
    old = bytes(bytearray(b"old wire"))
    new = bytes(bytearray(b"new wire"))
    p = proof({"wire": old})
    before = p._inputs_key()
    p.inputs["wire"] = new
    assert p._inputs_key() != before
    assert p._inputs_key() == runtime._model_inputs(p.inputs)
    assert id(old) not in p._byte_digests and p._byte_digests[id(new)][0] is new
    p.invalidate()
    assert p._byte_digests == {} and p.active is False


def test_no_digest_shared_across_proofs():
    wire = b"same wire"
    a = proof({"wire": wire})
    b = proof({"wire": wire})
    assert a._inputs_key() == b._inputs_key()
    assert a._byte_digests is not b._byte_digests
