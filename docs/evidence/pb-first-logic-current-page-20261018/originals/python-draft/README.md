# P-B first local logic change, current-page acceptance draft

This is an external Python bridge draft for the root writer to adopt as
`tests/test_pb_first_logic_current_page_ui.py`, together with the independently
authored `tests/pb_first_logic_current_page_ui.cjs` (UI draft SHA-256
`e2082f9669973c1edcf76c3e73e867ce41755648b857430c9652a7ef4793d6ea`).
No repository or Git write was performed by this author.

Only Python compilation and Ruff were run. There was no pytest collection,
product HTTP, database fixture, Worker, or model execution in this drafting task.
The following counts are intended assertions, not actual-run claims: fresh normal
parallel generation 3 Mock requests, SOURCE 2, original P-B COLD 2, isolated CHECK
2 and new-instance THIRD use 2, for 11 Mock requests. Real model requests are zero.
Business execution has four stages; each uses the existing maximum-three normal
claim driver and original real lease/deadline gates. Actual claim counts and every
claim header/wire increment are retained. No clock, lease, deadline, budget, or
successful row is changed or fabricated by the test.

The one continuous JSDOM flow discovers the saved P-B app, explicitly selects the
original instance, changes the qualifier dependency from false to true, previews
revision 2 while retaining the other five action definitions, separately consents
to CHECK, explicitly reads the successful CHECK proof, separately obtains and
confirms an internal version approval, selects the new Release to create a new
instance, then explicitly reviews/consents to the already saved THIRD material
and matching Goal and runs it normally. There are no downloads, owner decisions,
response-loss, cancellation, navigation fault matrices, or real semantic claims.

The original P-B COLD result is typed version 1. The CHECK is isolated in another
instance of the old Release and is typed version 1. The new Release's new business
instance is also typed version 1; it is not a second result version in the old
instance. Every original fixture row is preserved byte-for-byte. Baseline tables
include the source, old draft/Release/Goal/material/result/graph/locks. All saved
materials and Goals are created before deriving the graph or opening the page;
no new fixture Grant can invalidate the exact version approval's grant version.

Stage assertions permit exactly the relevant changes. Preview adds one original
and one seal journal row. CHECK acceptance adds the isolated instance, one normal
Run/AppRun/binding/contract and six journal rows; normal two-model completion has
six VERIFIED operations and fourteen journal rows total (six acceptance plus
eight complete offline request/response archive originals/seals). The first
successful CHECK proof GET legitimately adds only CHECKED and CHECKED_seal, two
rows. Version approval adds one approval plus its journal pair. Commit consumes
that approval and adds one Release. Instance creation adds only that instance.
THIRD use acceptance adds its one runtime READ Grant and six journal rows;
completion includes two artifact READ Grants and the same fourteen-row journal
shape. No new executor, app, runtime, SAVE Grant or formal publication is used.

Actual second-model input `prior_items` and `prior_feedback` must equal the first
model operation's actual receipt; the new business model request content must be
THIRD, with no SOURCE/COLD input reuse. Cold page reads both saved business results
and pending owner states through GET only, correlated by exact RPC ids and full
HTTP/resource hashes. Every boot must serve the exact current 27 assets and match
the production source hashes.

Evidence is flushed from fixture setup through finally: raw request and response
bodies and request bytes, complete stage snapshots, per-claim headers, all Mock
wires, page stdout/stderr/progress/HTTP, source manifests, IPC, checkpoint rows and
claims. `_PageObserver` owns only its Node subprocess and applies its existing
900-second Node watchdog. Product settings remain the default run_seconds=300
and lease_seconds=30. The parent's outer whole-case bound may be 1200 seconds.
Windows, native browser, real semantics/scenarios, PostgreSQL and remote CI are
not executed or certified by this draft.
