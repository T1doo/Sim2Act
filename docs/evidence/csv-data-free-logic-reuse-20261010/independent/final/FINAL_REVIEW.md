# Independent review: BLOCK

Exact source `4e66136866d5a46347785af45f517dd75de1aeac`, contract `014dc78e6e29772ce4d37400c0150ed52f7c37adcf8aafc843b3bec768acacd8`. All 378 non-doc files / 72 product files match manifest, Git and worktree before/after. Repo unchanged.

Two independently constructed SQLite and PostgreSQL scenarios created an actual successful canonical three-node CSV DAG Run, sealed Release and explicit logical authorization. Both authorization/seal snapshots were then jointly changed only at request.request_key, with both request/snapshot fingerprints recomputed. The publicly readable authority remained HTTP200 under the original logic ID; deterministic ID derived from the altered request is different. All-table snapshots before/after each GET prove zero product writes. This confirms an original-intent integrity failure; it does not enlarge recipe, scope or permissions.

Require strict recomputation of logic ID from owner, sealed source Release ID and authorization request key in load(). A self-consistent dual request hash is insufficient.

The target metadata prefilter and pre-POST frozen-app/pure-late-receipt seal fixes were read statically. The remaining new-CSV/revocation/expiry/UI matrix was not run after this blocker. This is not PG/UI/native/AT10 overall acceptance. Original OPEN boundaries and LIVE0 remain.

Preserved two independent harness errors: an incorrect stdout flush keyword after SQLite proof was saved; fresh-PG schema name did not meet required test_32hex guard, before table creation. The exact empty owned schema was removed and PG re-run in a valid fresh owned schema, then that schema was removed. Author schemas/container/processes were untouched.

STOP ACK: all reads/runners for this source are complete and its evidence is sealed. Root may edit; new source requires a separate review.
