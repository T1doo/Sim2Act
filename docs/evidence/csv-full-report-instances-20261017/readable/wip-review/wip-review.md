# Full CSV report internal delivery: bounded WIP static review

Base HEAD: `44acab540dda5d090eccc21f07d461e2e4462d0c`. Source is uncommitted WIP; exact sampled bytes are in `wip-review-proof.json`. Root is the sole repository writer. This reviewer wrote only its own `/tmp` artifacts.

## Conclusion

No remaining definite blocker was found in the sampled backend after the root fixes below. This is a static WIP conclusion, not final frozen-source acceptance or an independent test pass.

## Resolved findings checked in current source

- New full-report workflow uses reject a preexisting predictable ordinary Run before prospective prepare; existing accepted original keys retain their own receipt recovery.
- New instance uses also reject a preexisting derived workflow-use key, preventing retroactive attachment of an already accepted workflow Run.
- Accepted instance UseInput is strict and matches revision, release fingerprint, resource, column, key and the actual ordinary contract; reconstructed original workflow-use key/fingerprint must agree.
- Closed typed schemas reject altered scalar types; canonical fingerprints tie AppRun.output and typed data to the original successful ordinary result. Contract fingerprints use the same exclude_none form as the frozen contract.
- Release snapshot fingerprints agree with both the consumed approval snapshot and the reconstructed recipe snapshot, so Python numeric equality cannot weaken the independent immutable anchor.
- Every binding revision maps to the exact adopted Release in instance history. Surrounding switch approval data_version boundaries constrain historical binding bases; successful typed versions also obey the successor switch upper bound.
- Original instance creation GET uses deterministic instance identity plus history[0] and returns the original creation receipt with explicit current release/revision after later adoption.

## Other reviewed boundaries

The adapter creates no AppManifest executor, Grant, identity or ordinary tool implementation. New uses are prospective ordinary CSV contracts with original explicit confirmation; Worker finalization commits typed data inside the original terminal transaction and leaves lease/fence/deadline checks in place. Generic app-job/run_instance execution rejects this snapshot family. Release, instance and Run reads retain source/material/artifact authorities before their protected bodies. Independent journal/AppRun/event/context anchors stop a stripped marker from downgrading a bound use. Historical completed Runs remain tied to their original Release after adoption. Switching reuses lifecycle prepare/approval/CAS commit, includes active-Run exclusion and typed-data retention checks, and returns exact original-key receipts.

The new recipe cache is limited by connection transaction identity and write epoch; all non-SELECT statements advance that epoch. It rechecks every collected current authority and returns deep copies. The source recipe ancestry is finite and excludes workflow-use sources, so this cache does not turn recursive current Run proofs into trusted shortcuts. No new busy/lease/deadline budget was introduced.

## Evidence and gaps

`test_complete_report_instance_seals_draft.py` contains two bounded NoModel regressions for Release numeric re-signing and complete adapter-chain re-signing to an unadopted Release. It was AST parsed only and was not executed by this reviewer. The root can integrate and execute these on frozen source.

All ten sampled Python files were AST parsed; no pytest, Worker, model, HTTP service or database fixture was started by this reviewer in this phase. Parent-reported collision and post-cache positive results are recorded as parent evidence only, not independent passes. The first WIP RUNNING observation is not reclassified or hidden. UI, frozen tests, actual raw HTTP/SQLite proof, PG, Windows, real semantic/model and remote CI remain outside this static review.

The prior continuous-CSV stage is not re-run or re-signed here. Its previously reported d74 independent 7-case and later b589 static upgrade conclusions retain their original phased evidence limits.
