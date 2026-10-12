# P-A follow-up static review and prepared independent tests

This directory is PREPARED ONLY. No test, SQLite fixture, barrier calibration,
provider request, or NoModel Worker was started in this preparation turn. Do not
use this directory as passing evidence. Wait for the root's final source freeze.
The root is the sole repository writer. Only this new `/tmp` directory is written.

The previous static report and all its original hashes remain unchanged under
`/tmp/pa-intern-provider-static-review-20261012`.

Static follow-up disposition against combined-r1:

- Prepare now obtains only the Goal version's resource-ref projection and
  authorizes it before the full Goal snapshot.
- `source_scope_gate` projects Run identity/ref metadata, exact Frozen identifiers
  and independent ACCEPTED generation identifiers; it authorizes current material
  and the original approval's metadata resource before full private reads. Missing
  or mismatched discriminator, approval or application IDs reject instead of
  interpreting a stripped P-A record as a generic Run.
- The gate now precedes `guard`/`frozen_contract`, `inspect` classifiers, original-key
  API recovery, confirmation and `Worker.finish`'s first full contract read.
- Claim initially selects only an exact queued Run ID. Rejection saves only failure
  metadata and CONTRACT_REJECTED, returns None and does not load its queue payload.
- Activation PARTIAL finalization checks the original guarded lease deadline after
  the current Goal/permission/approval/settings check and after tentative terminal
  writes, all in one transaction. This can roll back the tentative result.
- One static observation was sent to root: `Worker.once`'s exception
  fallback selected a complete Run merely to compare fence. A resource withdrawal
  after claim can reach this after the new authorization gate rejects. A fence-only
  projection preserves its required failure write without private-body evaluation.
  The captured follow-up `worker.py:630` now uses that fence-only projection. Its
  bytes differ from the earlier author combined-r1 source map; the other four
  captured gate files match that map. No tests were run across that change.

These are static observations and source fixes, not a reproduced private-cell FAIL,
response plaintext disclosure, real attack, or provider acceptance result.

`identifier_private_barrier.py` prepares an independent SQLite evaluation barrier.
Full protected Run, frozen Goal/contract, resource and Attempt columns use a cell
UDF which errors on protected selected rows. Exact identifier JSON path projections
use separate enumerated view columns, not a regex bypass of every snapshot read.
Nested JSON_EXTRACT/JSON_QUOTE and bound paths are normalized to dedicated identifier
expressions; their unused binds are removed without changing ordinary value binds.
Returned projections reject objects/body-shaped arrays. Full reads through aliases,
joins, IN, aggregate/no-WHERE forms still use the error UDF. Direct `main` reads are
authorizer denied and reserved/colliding CTE names are rejected. Writes keep main
table semantics. This is instrumentation, never a production security layer.

Backing JSON is necessarily evaluated inside each trusted identifier projection;
the contract permits that narrowly enumerated projection. We will not describe it
as zero underlying JSON evaluation. Its log is separate from complete private cell
evaluation. The calibration must actually prove both permitted output shapes and
deliberate private UDF hits before any zero-private-cell product conclusion.

Prepared test scope (not collected/executed yet): calibration; revoked prepare;
revoked inspect/original-key recover/confirm; stripped P-A version with withdrawal;
claim metadata rejection; direct finish withdrawal and global zero write; explicit
approval withdrawal before first confirmation; unknown usage without resend; final
transaction lease/approval clock edges preserving immutable settlement.

The clock edge is a local post-STATE synthetic fault. It is not the permanently
excluded cancelled installation race. SQLite fixtures are newly constructed here;
no old rejected candidate/probe/artifact is imported. Author helpers may be imported
only after freeze to build real allowed SQLite/MockTransport flows. Their source
maps must match the qualified candidate before and after execution.

The test fixture explicitly constructs SQLite, ignoring any PostgreSQL test URL.
No provider/network/PG/native browser/socket/CI/model/credentials/install/deployment
will be used. Typed new-material acceptance, real provider fees and whole semantic
Goal acceptance remain outside this preparation conclusion.

All dynamic counts, actual calibration and actual SQL barriers: NOT RUN.
