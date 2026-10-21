# Authorized once-only attempt: independent read-only result review

Decision: **CONFIRMED_PRE_PREFIX_ENTRY_FAILURE / UNKNOWN; NO_G0_OR_CANDIDATE_QUALIFICATION**.

Attempt root: `/tmp/sim2act-authorized-native-g0-f530f82674b34cea90ef0d1bcace9d81`; sole run: `runs/native-g0-f530f82674b34cea90ef0d1bcace9d81`. Frozen/current code HEAD: `b4bac26b5ecbb98c864407170a94c202deee427a`; worktree was clean when read. This reviewer read original authorization/grant/description/log/receipt files, source, hashes and process identity listings only. No code, tests, DB, product, Worker, Mock/model, G0, prepare/commit, signals, retry or new grant/window was executed or created. Only this `/tmp` review was written.

## Actual failure and causal boundary

The child output is exactly `BLOCKED / direct child entry prohibited`; the parent log/receipt is **UNKNOWN**, with parent reason `child incomplete or unknown`. The parent receipt records **0.1406026889999339 seconds**, not a completed G0 or candidate elapsed time.

`validate_child_parent` reads the parent's `/proc/<ppid>/cmdline` and requires an argument exactly equal to `str(Path(__file__).resolve())`, as well as the execute/output flags. The root agent reports the actual parent invocation used relative `scripts/diagnostics/g0_bounded.py`; that relative argv token does not satisfy this exact absolute-script-path condition. The observed message and source are consistent with that trigger. The historical parent argv itself was not preserved in this artifact directory and is no longer available from that exited process, so this reviewer distinguishes the root's actual-command report from the independently read failure evidence. No command was reconstructed or rerun to prove it.

This is an invocation/preflight-compatibility failure. It is not an original business G0 refusal, a candidate admission/performance result, a provider/account failure or a resource-budget rejection. The security check was retained and stopped the child; it was not weakened or bypassed to make the attempt proceed.

The source calls `validate_child_parent` **before** child `Files` construction, child-I/O installation, importing the prefix, `candidate_config`, or `run_prefix`. The sole run directory contains only the four parent-created files: source manifest, zero-byte control log, 75-byte child output and parent receipt. There is no `fixture.db`, diagnostic, Mock-exchange log or prefix proof. Therefore prefix/producers/Mock/candidate selection/first binding/G0/both commits/W5 were **NOT_REACHED**. No business counter was initialized/observed here; absence of execution plus source order supports no business exchange, rather than a fabricated measured zero-count success. The profile copied into the receipt is configuration, not an instantiated/qualified candidate.

## Once-only consumption and no retry

The authorization record identifies one attempt and no automatic retry. `grant.json.consumed` exists as an empty mode0600 marker. Source atomically creates it with `O_EXCL|O_NOFOLLOW` before creating the run directory or child. Failed setup is intentionally consumed, so the pre-prefix failure does not leave this grant reusable. There is one run under this attempt's `runs` directory; no retry record/new grant appears in the reviewed attempt root, and the launcher has no automatic re-execute branch. This review did not create or authorize any replacement.

The description, grant, run manifest and receipt consistently record HEAD above, candidate profile SHA256 `f8758c85952d55e8d5ad8e257db62a20ba9cb7365deb15f94cd636da035f227f` and recorded source-manifest digest `39190dfc45d353346bf41c1c12786e02e94d652c603331bf8bc9569c348efedd`. The receipt records that digest again after parent cleanup. Authorization's description-file SHA matches the actual description bytes. Relevant actual launcher/guard/prefix hashes match the frozen source entries. This reviewer hashed the listed artifacts and relevant sources, but did not independently recompute the canonical all-dependency manifest or rehash every dependency entry.

## Monitoring, cleanup and limits

The parent receipt records dedicated PID/PGID/SID **39573**, same uid1000, cleanup **OWNED_GROUP_EMPTY**, `finalization_errors=[]`, `no_resume=true`, `business_acceptance=INTERRUPTED`. Source validates ownership/session before signaling and only addresses the recorded owned group. At review time `/proc/39573` was absent and an independent read-only process listing had no PID/PGID/SID39573 entry. This corroborates current empty-group status; it is not a new signal or cleanup action.

The parent monitor ran **3 samples**. Peaks were logical **633411 bytes** and allocated **638976 bytes**, below **67108864 bytes**. Observed completion intervals count2, min0.023489661 seconds, max0.114887513 seconds; the recorded policy remains every supervisor iteration plus finalization, selector cap0.05 seconds, configured0.1 seconds unscheduled. This is sampled disk accounting, not a hard quota or an RSS observation. The recorded peak is before final receipt bytes, so it is not mislabeled as a final all-artifact size.

No wall/disk/native budget triggered the failure: parent work is far below outer480/600 limits and sampled disk below64 MiB; G0's120-second timer, original business lease/Run/TTL checks and native ledger did not start. Their absence is not a pass. In particular child-I/O/SQLite G0 authorizer/network instrumentation and native OWNED eligibility were not exercised in this attempt because the earlier entry check refused first. The parent monitor and owned cleanup evidence should not be relabeled as broad runtime protection validation.

Final result remains **UNKNOWN / pre-prefix blocked / one authorization consumed**, with no candidate route, no G0 start, no complete commit evidence, no speedup/RSS/production qualification and no automatic retry. Existing safety/authority/resource gates were not relaxed. Any later work must preserve this failed original evidence and cannot silently reuse this consumed attempt.

Artifact/source SHA256 bindings are in the companion JSON.
