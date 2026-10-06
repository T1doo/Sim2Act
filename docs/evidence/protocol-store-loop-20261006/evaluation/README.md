# Frozen synthetic evaluation registry

These four evaluation assets are service-owned inputs to `protocol_reviews.py`.
They are not resources granted to the model runtime and are never provider
messages. Their registration is a fixed code allowlist with exact byte hashes;
there is no HTTP registration, caller decision, gold upload or checker upload.

The A/B source and cold contracts derive from the independently reviewed draft
gold and rubric in `model-protocol-preparation-20261006/materials`. Each asset
records those source hashes, the independent draft review basis, public goal,
exact input content hashes, and one exact structured output. This permits a
bounded machine oracle for these frozen synthetic inputs. It does not establish
general model semantic correctness or accept alternative equivalent wording.
The original rubric and gold remain evaluation assets. Public model schema
contains types and field names, without expected answer values.

The controller freezes the contract registration before dispatch. Review checks
the frozen registration, actual current authorized byte readback, verified worker
receipts and immutable completion result, then compares the exact structured
output. A mismatch is FAIL; an input outside the contract is UNKNOWN. Neither
decision promotes the run. A PASS atomically changes only the new source/cold
run status/version and creates a separate review record. Technical UNKNOWN
results and job snapshots are unchanged. Later source/cold proof reads recheck
current authorization, unique persisted review, versions, asset pins and oracle.

Deployment currently requires the pinned assets at this repository-relative
path. A code-only installation without the assets fails closed with
RESOURCE_UNAVAILABLE; it is not an evaluation-enabled deployment.

| Contract | Asset byte SHA-256 |
| --- | --- |
| protocol.synthetic.a-source.v1 | 89773350ebef455df85ea93034abb4bdf613d602b15101835f7d472e65ba4acf |
| protocol.synthetic.a-cold.v1 | a1b13eecbd7be479c4b28dad1a9abbf0c7d126b46f4466b58d159d4c0bd58d8b |
| protocol.synthetic.b-source.v1 | ede9a7e5db423b3108e70e49af91433f63efc8bd17226ef902257063b7cd56e1 |
| protocol.synthetic.b-cold.v1 | 73f435ff6934371c50e54776030d3a00de4a54d7d6e071b8c41821bf45f4791e |

Owned-layer validation: `tests/test_protocol_reviews.py`, 39 PASS on 2026-10-06,
with actual local worker/MockTransport/attempt and operation receipts. Negative
coverage includes wrong output, historical non-success states, current grant
revocation, stale fence/version/result, contract and registry tampering, proof
tampering, caller PASS/gold/code, concurrent idempotency, cancel/error state,
and boolean integer substitutions in both caller and stored requests. Persisted
records require a strict canonical payload and separate PROTOCOL_REVIEW event
fingerprint seal; coherently rehashed row-only changes cannot preserve PASS.
No LIVE request, CI, native browser or
PostgreSQL validation was performed by this layer's implementation agent.

Retained failed checks: initial 7 PASS / 20 FAIL exposed backend acceptance-version
validation; after the backend correction 27 PASS. Adding the shared review-proof
reader caused 28 PASS / 6 FAIL from a two-value unpack of a four-value helper;
the corrected implementation subsequently passed all 34 checks. Independent
review then reproduced four stored-record bool/int or nested extra-field gaps.
Strict stored parsing, canonical fingerprint reconstruction and the separate
event seal corrected them; all 39 checks subsequently passed.
