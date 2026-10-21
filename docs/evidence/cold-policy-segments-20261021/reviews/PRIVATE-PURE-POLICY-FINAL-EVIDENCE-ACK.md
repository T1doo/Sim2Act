# Fixed policy segments: final author-evidence supplement

ACK_LIMITED_FINAL_SOURCE_AND_LOCAL_EVIDENCE. The last combined run is no longer pending. Reviewer only read others' original logs/freeze/source/documentation; no product/import/test/DB/Mock/G0 execution, signal or repository write.

`/tmp/sim2act-policy-segment-20261021/final.log` reports **163 passed in 80.80 seconds**, with the retained client deprecation warning. SHA256: `cfb4b04b08e1334f25e31e601bee220270190a4ee5b0ae1653f47c991d3f45c4`. `freeze-final.json` and `freeze-final-after.json` agree and match direct source reads:

- helper `9d328fd597fbcbc64e80bdfaaef01f829084afbae95861ad92c2daf05301e802`
- runtime `6f91a55bdfbb37fc1b9f571d030692087b664c078dcd9b043844c1e8b379dcc4`
- test `ad2d6f2f14e7704c5ff46481aa57cd14b9a8fd0f7aa6a64a20e5da528a37f76c`

This supersedes only the pending-test status in the final code ACK; its source analysis and closed P2 stand. The final combined batch contains 22 new tests and 141 related regressions. Earlier 20/141 executions are not added to inflate distinct coverage. Initial two failures were confirmed to be frozen Settings assignment errors in the negative-test setup; the retained initial log says FrozenInstanceError for max_output_tokens. Original failures and earlier-byte reviews remain history.

README accurately distinguishes 12-to-4 / 14-to-4 local codec observations from CPU/RSS/G0 performance; the four calls total 52-to-16 only in that local fixture. The normal lower read-scope exit and actual base/check do not prove full binding, actual prepare, both real commits or receipt/full-tail completion. The configured SYNTHETIC route is expressly separate and is not prohibited by the production SOURCE_MISSING boundary. **Full-tail successful differential acceptance remains NOT RUN / NOT SATISFIED; no new G0/Mock window ran in this slice.**

One documentation precision recommendation was sent before sealing this supplement: the README sentence asserting hidden RowMapping storage is covered by both full pins should be limited to RowMapping already present in guard.inputs. A fresh `_recheck` SELECT result passed as a policy argument is not itself necessarily added to the graph. The snapshot copies the original policy-visible projection and does not create a new proof for arbitrary hidden parameter storage. This does not alter the reviewed source's original visible-consumer behavior or code ACK; it prevents overgeneralizing CGR coverage. At the read with that sentence, README SHA256 was `68d22e7f6d4c6b57fa3f97eab99bd433059932f387c1a4a9eb8f3dd60e24f663`.

No further source/testing work is requested by this supplement, and no execution window or complete-tail success is approved.
