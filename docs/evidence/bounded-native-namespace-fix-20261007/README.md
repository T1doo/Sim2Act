# Independent namespace blocker correction

Correction Plan `a9e6161`; frozen fix source `31bd41980da49776ed609e3c290a2b47caafcb09`.

Independent actual HTTP probe on the prior composed source showed that the fixture consumed an original `/protocol/source` Run with the same owner/project/kind: QUEUED became WAITING_APPROVAL with two Attempts. `original-independent-failure.json` and `.log` preserve that failure. Prior b69c local PASS evidence did not cover this boundary and cannot certify it.

Only test fixture dispatch is corrected. Before Worker invocation, existing `conditional_runs.validate_snapshot` enforces exact bounded namespace and canonical closed contract/frozen inputs; existing `protocol_jobs.verified_pending` revalidates accepted event seal and Run/job fingerprints, owner/runtime/project, frozen current resource hash/format, authorization and existing source/check/compiled-plan dependency proof. Additional scope guards require the existing fixture owner, same project, exact A-S reference and goal, source payload inputs and cold reference. No snapshot or client marker is rewritten. Normal Worker is called only after all proof checks pass.

`target.log`: **17 PASS / 0 SKIP / 37.38 s** on exact frozen fix. `namespace-refusal-0.json` and `-1.json` come from actual original HTTP enqueue in ordinary and optimized-Python subprocesses: explicit rejection, Run remains QUEUED, Attempts delta zero and every persistent table fingerprint unchanged. The probe uses explicit checks under `-O`. `actual-http-0.json` / `-1.json` retain both legitimate shared source/check/extract/cold/check chains (19 checks, four Mock attempts/two VERIFIED reads) followed by old manual22. Existing malformed input, EOF, child cleanup/timeout and output-protocol guards remain.

Ruff and diff checks PASS. No product source, permissions, model activation, PNG slots or budgets changed by this fix. No push, CI or full-suite run here. Protected Edge/new PNG and the 150/900-second aggregate budgets remain NOT_RUN. Root stopped the prior partial combined suites; those are not successful final-source evidence. Root owns independent review and new combined regression.
