# Two fixed policy segments: final limited code ACK

ACK_LIMITED_STATIC_CODE. The initial runtime invalidation P2 is closed. No other P1/P2 source blocker was established for the final hashes below. Final combined author regression is still running at this review and is not declared passed here.

- `_cold_policy_segment.py`: `9d328fd597fbcbc64e80bdfaaef01f829084afbae95861ad92c2daf05301e802`
- `natural_spec_runtime.py`: `6f91a55bdfbb37fc1b9f571d030692087b664c078dcd9b043844c1e8b379dcc4`
- `test_cold_policy_segment.py`: `ad2d6f2f14e7704c5ff46481aa57cd14b9a8fd0f7aa6a64a20e5da528a37f76c`

These hashes directly match `freeze-final.json` and source reads. Both runtime wrapper except blocks now test exact `_ColdGraphRead` before invalidation, set phase INVALID and bare-raise. The new two-entry parameterized foreign-guard test drives the actual graph.check refusal, observes DomainError, phase invalidation and zero foreign attribute callbacks. It addresses the precise reported failure; no product cleanup/transaction behavior was expanded.

The helper and four runtime routes retain the previously reviewed contract: full entry pin, complete private exact-storage clone, fresh fixed schema/code/serializer/validator qualification, unchanged original policy core once with guard=None, full success exit pin before publication; unqualified inputs choose the original guarded policy before execution. Original pure exceptions are not replayed or replaced by a finally pin. Parent/CGR, source/SQL/clock/finite lease/producer/root/transaction boundaries and `_fields` remain in their original locations. The bootstrap witness is code configuration, not a permission, input validation cache or arbitrary process code-edit defense.

Earlier verified author results remain attributable to their earlier test/runtime hashes: 20 target passes and 141 regression passes with unchanged helper; the last two tests and runtime P2 change await the final combined run. The initial report remains an earlier-byte record. No arithmetic aggregation of overlapping or pending batches is made.

The full-tail limitation remains unchanged: the local fixture's actual SQLite/native `_base`/`check`, two requirements constructions, two RunCheck constructions and normal lower read-scope exit are real local evidence; actual `_prepare`, two real coordinator commits, receipt continuation and complete G0/full tail are NOT RUN / not proved by these fixtures. `synthetic_commit` is a stand-in coordinator ordering fixture. This is not an instruction to create replacements or a judgment against the separately authorized configured SYNTHETIC route. No new window is authorized by this ACK.

Reviewer executed zero products/imports, tests, DB, Worker, Mock/G0/PB or launcher and sent zero signals. Repository writes zero; only this `/tmp` report was added.
