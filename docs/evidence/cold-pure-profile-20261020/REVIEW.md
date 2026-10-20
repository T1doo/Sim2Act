# Independent pure-profile and C-Pickler diagnostic review

Decision: **ACCEPT_DIAGNOSTIC_C_PICKLER_CORRECTION_AND_LIMITED_OFFLINE_PROFILE_NO_PRODUCTION_OPTIMIZATION**. No remaining blocking finding.

Baseline HEAD: `7da1c2a46b04d3e3e12f6d04acd0539b175a9bc2`. Exact reviewed hashes are in REVIEW.json. The reviewed PLAN hash is `d738bd84efde35cb75405188a2c4c782330303e738d04b450c655dc0fd15b9a3`. PLAN now accurately distinguishes preimplementation ACK of the narrow diagnostic correction from post-execution read-only review of the real profile's exact script and raw artifacts.

The only tracked code changes are cold_scan_standin.py and its test. encode now uses public pickle.Pickler rather than Python fallback pickle._Pickler. It retains the complete header, protocol 5, fresh stream/Pickler/memo and complete field/alias scan on each call; measurement still hashes the completed bytes and explicitly identifies the implementation and absence of production reducers. It does not cache validation, stream into SHA, change production code or promise a performance gain.

I independently ran only:

`PYTHONPATH=scripts/diagnostics .venv/bin/python -B -m unittest test_cold_scan_standin -v`

Result: **4 passed, 0 skipped, exit 0**, 0.271 seconds. The new child runs with a 10-second timeout, asserts public Pickler is the C implementation and matches production's base, prohibits Python fallback and business/transport entrypoints, and compares complete bytes with actual runtime._cold_graph_bytes for 10 primitive/alias/list/tuple/bytes/multiframe vectors. Product imports remain isolated in that child; parent tests verify no Sim2Act import. This proves the selected primitive vectors, not custom-reducer or typed/CGR qualification. Raw output: UNITS-INDEPENDENT.log.

Separately, I read the already-executed profile script, without running it. Its five tasks call actual input_key, typed storage, pure-data copy, typed cohort and initial validator functions on a stored complete contract and synthetic in-memory RowMapping/Limits/envelope. Binding/CGR are explicitly uninitialized no-authority shells; no constructor, check/add, producer, DB or business fixture is invoked. Input size is 61657 bytes, not the original 579257-byte graph. Each task has 1 warmup, 100 unprofiled and 100 cProfile calls.

All 7 archived raw files match their /tmp originals byte for byte. I read all 5 pstats files and verified their total time and every exported top-self/top-cumulative record against PROFILE.json, including call counts and self/cumulative seconds. No profile was rerun. Unprofiled 100-call wall seconds are input_key 0.022940, contract storage 0.011124, pure_data 0.014093, cohort 0.039195 and validator 0.113069. These are fixed pure-input measurements, not G0 or SQL/authorization costs; cProfile overhead is substantial, and cumulative parent/child times must not be added.

No production optimization is approved. Reusing roots would omit the second fresh class-list read after nested_classes imports; import hooks may change schema bindings. That small cost does not justify a semantic change. Repeated storage/copy/comparison/dump passes cannot be removed merely from this profile. Prior rejected validator/SHA/type-dispatch/prefix directions are not repeated. Complete DB/read-set/CAS/memory witness gaps remain outside this patch; no transaction design relies on this calibration.

git diff --exit-code returned 0 for src and all tracked existing evidence. The old Python-Pickler measurement remains unchanged and cannot be directly compared with the real C/reducer profile. Sampling implementation and all existing limits remain unchanged. Parent logs report 43 pure tests = 39 passed + 4 skipped and Ruff success; I did not repeat that wider suite.

This review establishes the diagnostic correction and limited profile provenance. It does not establish production G0 speedup, a 30-second lease pass, complete PB acceptance or authorization for another business window. Reviewer actions: no repository edit, DB open/decompression, profile execution, business fixture, Mock, G0 or launcher execution.

