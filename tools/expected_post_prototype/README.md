# Expected-post data shadow prototype

This tool is not imported by the application. It cannot grant permission, return a G1 PASS, or enable reuse. `Result.eligible_for_reuse` is always false. The accepted application remains c6a42c783fd92818654b02e5fb469675877c632a.

`Observation` captures the actual G0 connection's complete ordinary main-database logical data and an isolated SQLite backup. A pure `Plan` owns serialized bytes, complete schema/table/typed-row/rowid/index data, selected Python input snapshots and context values. Connection, transaction and clone handles belong only to the short-lived observer, never the plan. The actual five final SQL statements/primitive bindings/rowcounts are replayed only on that isolated backup. Full actual uncommitted data from the same write connection must equal the resulting logical data. This is an **endpoint differential**, not a proof of business intent or identical intermediate effects.

The collector includes internal sequence/stat tables, duplicate rows, missing/range membership, real rowid or WITHOUT ROWID primary keys, types and index definitions. Unknown schema, triggers/views/virtual/shadow tables, attachments/temp objects, added function/collation inventory, extra/reordered writes, unsupported native SQL, changed source inputs/aliases, changed owner/version/fence/epoch, revocation/cancellation flags, changed deadlines and changed observer transaction decline. It never scrubs callbacks, disables security settings, edits SQLite page headers or changes the original journal mode.

The limits are bounded collection limits with cooperative time checks, **not** SQLite statement-interrupt, peak-memory or hard CPU guarantees. A large value can be allocated before its collection-size check. Page/byte preflight bounds precede collection. SQLite callbacks on the original connection have not been proven absent or pure; even diagnostic reads may invoke them.

The data match leaves these dependencies unclosed: complete Python/file inputs; callback/UDF provenance; SQL execution-environment qualification; unobserved raw-driver transaction boundaries; query result sequences without ORDER BY; and all dynamic authorization. Actual SQLAlchemy connection/transaction checks do not make arbitrary raw-driver COMMIT/BEGIN invisible behavior observable. No observed data match can authorize skipping the original G1.

The normal unit suite is:

```sh
python -m pytest tools/expected_post_prototype/test_plan.py -q
```

The explicit one-Cold synthetic probe is separate:

```sh
PYTHONPATH=.:tests python -m pytest tools/expected_post_prototype/probe_actual_g1.py -q
```

It creates new synthetic SQLite data, permits at most six fixed Mock exchanges and forbids real HTTP. Business time and existing account/environment/software/heartbeat fixtures are explicit test substitutes. It is not a real-clock lease, formal PostgreSQL, Windows or live-model acceptance. G0 capture occurs at the original `promote` entry; W5 write recording ends at the original post-reader entry. Actual post collection waits until the **original G1 reaches READY**, preserving its protected-read authorization before the diagnostic collection. Original settlement/tail/CLOSED and commit still execute before the probe stops Cold2. Thus this prototype saves no production writer time.

Before any runtime integration, complete query/data/effect and callback qualification, original-G1 differential behavior and all dynamic failure paths must be proved; then real-clock two-Cold save/reopen/locked-cancel acceptance must be repeated. The tool must not be enabled as a cached verdict.
