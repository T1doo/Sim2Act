# Authorized once-only candidate attempt — read-only result review

2026-10-21. Reviewer: independent_gap_review. Result: **PREPREFIX_BLOCKED_PARENT_UNKNOWN_NO_RETRY**. This is a result/evidence review, not permission to launch, retry, replace a grant or change code.

## Reviewed attempt

Evidence root: `/tmp/sim2act-authorized-native-g0-f530f82674b34cea90ef0d1bcace9d81`.
Run root: `runs/native-g0-f530f82674b34cea90ef0d1bcace9d81` under it.
Frozen HEAD: `b4bac26b5ecbb98c864407170a94c202deee427a` (also current HEAD at review).

`authorization.json` records one bounded attempt and no automatic retry. The grant's zero-byte `.consumed` marker exists. Parent launcher output and receipt are UNKNOWN, with boundary `child incomplete or unknown`, business_acceptance INTERRUPTED and no_resume true. Child `output.log` is exactly the BLOCKED/direct child entry prohibited JSON (75 bytes). There is no child completion event: control.jsonl is empty.

Receipt wall time is 0.1406026889999339 seconds, not a G0 or candidate performance measurement. The run directory contains exactly source-manifest.json, output.log, control.jsonl and receipt.json. No fixture database, diagnostic.json, Mock exchange file or prefix proof was created.

## Root cause and zero-business-execution boundary

`g0_bounded.validate_child_parent` reads `/proc/<parent>/cmdline` and requires the exact absolute `str(Path(__file__).resolve())` to be an argv item, as well as execute-grant/output-parent flags. The execution author reports that the actual parent invocation used relative `scripts/diagnostics/g0_bounded.py`. That literal is not the required absolute `/workspace/Sim2Act/scripts/diagnostics/g0_bounded.py`; the first parent-argv condition therefore rejects even though this is the launcher's own child. This matches the exact child output. The evidence files do not independently archive complete parent argv or a failing-clause index, so the relative-invocation fact is attributed to the execution author, while source and output independently establish the parent-entry check failure location.

`child()` calls validate_child_parent before importing pytest, installing child I/O or importing/invoking run_prefix. The rejection occurs even before its consumed-root/source verification section. Consequently the original production-shaped fixture, Generate/Source/Cold exchanges, G0 context, candidate staging/selection, original two commits, W5 and downstream complete guards were not reached. Mock/real-model/production-prefix/G0/commit calls for this attempt are zero by the failed control-flow path; no runtime Mock counter was instantiated or sampled. This must not be described as an original admission rejection, a candidate routing failure, OWNED/LEGACY selection, a deadline result, or a candidate G0 performance result.

## Description, source and cleanup evidence

Reviewer canonicalized read-only JSON with jq and compared description.json with the run's source-manifest.json: equal. After excluding source_manifest from description and expires_at/grant_id from grant, fields compare equal. Description file SHA matches authorization's description_sha256. Initial source_manifest_sha256 `39190dfc45d353346bf41c1c12786e02e94d652c603331bf8bc9569c348efedd` equals receipt.source_digest_after_parent_cleanup. This latter receipt value comes from the parent executing verify_sources over its frozen source/dependency manifest. Reviewer did not rehash the entire dependency tree; current bounded/prefix/native/cold_accounted source hashes were independently computed and match the frozen manifest and prior closure review.

Receipt records cleanup OWNED_GROUP_EMPTY and finalization_errors=[], with no cleanup error. Source cleanup checks owned process-group membership after leader polling rather than relying on leader exit alone. At this review, `/proc/39573` is absent and read-only process listing shows no PGID 39573 member, supporting the recorded closed owned group. No database was created to clean or inspect. The receipt does not assert deletion of the evidence root; those evidence files remain intentionally present. Sampled disk peak is 633411 logical / 638976 allocated bytes, not a hard-quota proof.

## Static absolute-command form only

The invocation mismatch needs no safety-gate relaxation. If a future separately authorized and reviewed execution ever exists, its parent command must contain the exact absolute script token, for example this **non-executed template**:

```text
/workspace/Sim2Act/.venv/bin/python -B /workspace/Sim2Act/scripts/diagnostics/g0_bounded.py --candidate --execute-grant <ABSOLUTE_NEW_SEPARATELY_AUTHORIZED_GRANT_JSON> --output-parent <ABSOLUTE_NEW_REVIEWED_OUTPUT_PARENT>
```

This is syntax/cause analysis only. The current grant is consumed; do not reuse it, allocate another directory, generate a replacement grant or treat this template as authorization. No retry was performed by reviewer and none is approved.

## Original-file hashes

| Evidence relative to evidence root | SHA256 |
|---|---|
| authorization.json | `b6696bcccd20b48d294f2e562079a565831a9198a5eeda4e493bd700b7523002` |
| description.json | `ff1f5c9aa40b285de80713d7b445e11c204c60f365abe8c7f821ed7a636f753d` |
| grant.json | `9588782cc64852c6326ee854db789c29db4e3c257a6efcf21162da572ae943f4` |
| grant.json.consumed | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| launcher.log | `d9a0d3b958b7c036dea26edb7422b89e702f74bbbf61f805379a43428b87d827` |
| runs/native-g0-f530f82674b34cea90ef0d1bcace9d81/receipt.json | `8c5958780fc5a400a130f663d89aca9ef8378a035ae3243e5737c250ae589122` |
| runs/native-g0-f530f82674b34cea90ef0d1bcace9d81/output.log | `6c26f5d7bc0deebedbc68b4a956393d03db7e0d70f830127d3e3018cef7a3106` |
| runs/native-g0-f530f82674b34cea90ef0d1bcace9d81/control.jsonl | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| runs/native-g0-f530f82674b34cea90ef0d1bcace9d81/source-manifest.json | `5d3e512c43921ae9af68b62a1556bc712560600d3f19df3c43b37fdcdd85bfb7` |

Reviewer activity: source/evidence/hash/JSON/process reads and /tmp report writes only; no code/product imports, tests, database access, Worker, Mock, G0, prefix, launcher, producer or commit execution; no repository edits, grant or execution-directory creation.
