# Independent disk-report and offline-design review

Decision: **ACCEPT_TRUTHFUL_DISK_REPORT_AND_OFFLINE_DESIGN_ONLY_NO_PRODUCT_OPTIMIZATION_OR_NEW_WINDOW**. No material blocking finding in the frozen patch.

Baseline HEAD: `337569ed731bb806a25f29328a8119e7b40cf2b4`. Exact reviewed hashes are in REVIEW.json and remained unchanged after the independent tests.

The old .1-second field described a configuration value that did not schedule the original monitor. The patch accurately separates that value from actual execution: configured_interval_is_scheduled=false, every supervisor iteration and finalization, selector timeout cap .05 seconds, and observed sample-completion interval/rate statistics. These statistics include scan and processing/cleanup gaps; they are not hard deadlines, scan CPU time, or a reconstructed historical distribution. Zero/single/simultaneous samples do not invent a rate. supervised_select retains the original budget.check → disk.sample → selector.select order, original timeout expression/cap, exception propagation and event return. No scan throttling, count policy, disk limit, byte cap or business budget changed.

I independently ran only the authorized command under CPython 3.12.14:

`PYTHONPATH=scripts/diagnostics .venv/bin/python -B -m unittest test_g0_observer test_cold_scan_standin -v`

Result: **9 passed, 0 skipped, exit 0**, 0.002 seconds. Raw output: UNITS-INDEPENDENT.log. These six fake-clock/selector tests and three primitive-data tests do not call product code, DB, Mock or launcher execution. Importing the launcher module for supervised_select does not execute it. The two new standard-library SQLite mechanism tests were read statically only and were not run by this reviewer. Parent PURE-UNITS.log reports 42 total / 38 passed / 4 skipped, and RUFF.log reports success; I did not rerun those broader checks.

Historical receipt and diagnostic remain separate facts: whole window342.200031355s; G031.125279530s; end-minus-run_check.deadline/lease1.109071970s; stop=false; authorizer denials0. The five observed stages total25.271449465s,5620 check entries and5685 input_key entries, not all G0 time.6795/window-wall is only a coarse ratio; old per-sample intervals were not recorded. Existing journal_wait and reserve enforce last_reserved_at+60/at-least60-second spacing. No evidence establishes the specific background-heartbeat blocking duration or observer CPU cost in this run.

The offline call-chain analysis is source-supported, and the primitive envelope calibration explicitly excludes live typed storage validation, cohorts, SQL and CPU profiling. It retains complete rescans and distinguishes deep changes/new fields/alias structure, without qualifying the production serializer or predicting G0 speedup.

DESIGN.md is appropriately a candidate with unmet conditions. The current G0 store.tx uses SQLite BEGIN IMMEDIATE, and heartbeat uses another write transaction. The single-writer mechanism is consistent with [SQLite transactions](https://www.sqlite.org/lang_transaction.html) and [isolation](https://www.sqlite.org/isolation.html); this does not measure this run's heartbeat delay. ColdGraphRead binds connection/transaction/driver/total_changes/thread/source token/epoch, so moving it unchanged across transactions would fail its contract. A safe future design still needs complete owned immutable inputs, complete DB field/set/existence/phantom coverage by atomic non-bypassable change witnesses, covered mutable memory/alias state, and a short current authorization/deadline/stop/ownership/CAS transaction with original rejection order and all-or-nothing writes. Those proofs and mechanisms do not exist in this patch. Run-version CAS alone, identity caches, a local epoch or an unproven digest would be insufficient. Original lease/finite deadline semantics cannot be silently replaced with a later heartbeat value.

Cold RUNNING/RECEIVED is correctly attributed to the diagnostic StopBoundary converting the original DomainError to G0Stop(BaseException), preserving the scene while ordinary finally cleanup runs; it is not evidence of a production cleanup defect.

git diff --exit-code returned0 for src and tracked original once/path-fix/second-window/PB-envelope evidence. No original failure material was edited by this reviewer. No product path was changed, no DB was opened/decompressed, and no third business window, Mock, G0 or launcher execution occurred. This review does not authorize one or claim that G0 expiry is solved.

