# Bounded cleanup of this task's disposable duplicate evidence copies

No source/Git/final package/original evidence/user material/unique dependency was
removed. Only one disposable copied baseline was touched:
`/workspace/scratch/lease-fence-baseline-8172/docs/evidence`.
It is not a registered worktree and contains no .git. The primary tracked copies
remain in `/workspace/Sim2Act/docs/evidence`, with their Git history unchanged.
Other projects, original failures, unrecognized paths, locks and processes were
not modified. No owner/ACL/security settings or credentials changed.

The controller verified no process cwd/fd/maps referenced that exact temporary
subtree; selected regular, non-symlink single-link copies >=1MiB; required an
existing same-path tracked original with equal size and SHA256, rechecked copy
inode/size/mtime and immediately hashed the original before unlink. Explicit
manifest/inventory/wheel/portable/installer names were excluded. Only the copy
was unlinked; unmatched and unique content stayed. The per-file before/after
journal contains original path, byte size, SHA256 and deterministic restoration
from the preserved original. To restore, verify that original SHA256, ensure no
new unknown file occupies the copy path, then copy it back; no Git reset needed.

Actual result: 382 duplicate copies, 2,436,316,793 logical bytes removed. Available
filesystem space increased from 73,084,928 to 2,510,450,688 bytes. Exact controller
and `cleanup.json` are preserved. Independent read-only review checked 382 paths,
tracked originals, sizes and total; it did not independently rehash all 2.4GB.
The original controller performed each full-byte comparison. No original failure
or final artifact was erased and no unknown process was stopped.

This resolves the immediate disk emergency, not PostgreSQL/Windows acceptance.
The old PG-plan resource snapshot remains its historical pre-cleanup observation.
The >=2GiB disk condition now passes at this observation; image validation,
other resource/dependency checks and explicit narrow setup confirmation remain.
No PG image pull/container/DB/role/credential/model operation has been performed.
Windows CI remains 487/900 seconds; no new run and no budget reset.
