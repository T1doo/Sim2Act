# Natural trial admission interface and P-B contract

This change mounts authenticated HTTP engineering interfaces in the normal API.
It does not register a sender or a production fee authority, and does not enable
LIVE. Approval, stage approval and budget receipts remain consent/accounting,
not permission to dispatch. The admission endpoint always invokes the existing
fresh guard without an authority and therefore refuses LIVE. Request DTOs cannot
supply FeeProof, arbitrary authority, `free` or `live_allowed` overrides.

Endpoints beneath `/api/projects/{pid}/natural-trials/{trial_key}`:

- POST `approval`, `revocation`, `stage-review`, `stage-approval`, `admission`.
- GET `approvals/{approval_key}`, `approvals/{approval_key}/budget`,
  `approvals/{approval_key}/stages/{stage}/{request_key}`.

All use the existing authenticated identity dependency and exact project/user/
trial key comparison. Original GET recovery loads no caller-provided replacement
contract. It checks project and scalar material authorization before loading the
private paired original contract, then rechecks exact current material/Goal and
permissions. No recovery endpoint creates a Run, reserves a slot or extends
expiry. Stop retains the existing metadata-only revocation implementation.

`PBTrialContract` extends the original P-A contract with `path="P-B"`, a distinct
exact extraction request key and the complete reviewed edited Recipe. Existing
P-A serialized contracts remain unchanged. P-B consumes the same finite seven
slots: three actual Generate requests, two requests for the successful original
source task, and two for the extracted app on the different complete cold Goal
and material. Source still uses the original generated P-A application. Cold
requires the existing full `pb.verify` source/receipt/extraction/review/metadata
proofs, exact extraction key/Recipe and the same trial ledger's original source
Run. Its two source Attempts must be VERIFIED, MOCK, known/accounted, with exact
reservation wire and raw response hashes/bytes matching the independently
verified actual Attempt evidence. Unknown or rejected accounting never qualifies.
Original stage authority, precise app/instance/release/current version, approvals,
revocation, lease, software and total nonrefundable budget guards remain active.

Local evidence is retained in `/workspace/pa-pb-contract-evidence-20261015`.
First HTTP round was 3 PASS / 2 FAIL because the new test expected HTTP409 for
LIVE_BLOCKED; the existing unified error handler uses HTTP400. Corrected round
was 5 PASS. The original P-A short suite was 33 PASS, with its seven-slot slow
case explicitly deselected. First P-B actual seven-slot attempt failed after
302.41 seconds at cold stage review after successful Generate/source and P-B
extraction: a new source accounting guard incorrectly expected RECEIVED rather
than the runtime's final VERIFIED status. The complete failed candidate snapshot,
XML/log and independent fixture are preserved. The guard is corrected and the
source wire/raw correlation strengthened; corrected complete P-B execution is
NOT RUN in this child and must pass in the parent's single-source integration.
Final corrected-source HTTP round was 6 PASS, including revoked-resource
refusal before any private pair read. Scoped Ruff passed. Full mypy reported
only the five existing errors in status_report.py/tools.py across 83 source files.
No old/final-source passing counts are combined.

Production still needs a trusted account-to-quota resolver (caller-provided
`quota_subject` is only a frozen offline identifier), legally valid free
entitlement plus enforced nonchargeable authority, and reviewed sender wiring.
Neither HTTP caller consent nor a quota label proves any of those. Real model,
credentials, fees, PostgreSQL, Windows/native browser and human semantic
acceptance are NOT RUN. Synthetic known usage is not proof of real zero cost.
