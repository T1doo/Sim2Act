# DeliveryGraph UI staged log

Plan cbd675c preceded UI source. Independent UI tree normally merged backend/API 8e038c5 and backend final89f23ae; no backend/core/API edits by UI owner.

First actual CSV/Report run: 2 FAIL /9.31s. CSV UI incorrectly used Report-only project-scoped inspect; Report comparison incorrectly treated transient `cached` as part of saved anchor. Changed inspect to existing generic GET with exact app/project/runtime/candidate pin, removed only transient cached from anchor comparison. Second actual run 2 PASS/21.93s, 26 checks each.

Added public candidate digest, exact public MANIFEST binding, source-version/node binding and adapter context digest. Third run 2 FAIL/6.13s: valid FieldBinding omits ref, while core model explicitly normalizes it to null. Normalized only this documented default; fourth actual run 2 PASS/21.53s, 26 checks each, final89f backend. These are historical targeted results, not final-source signoff. Subsequently added fresh-page source-version tamper and actual identity ABA permanent cases (28 expected checks); await final core integration before final target. No full/PG/native/CI performed.

Each graph request adds zero model calls. Report baseline setup uses existing promoted helper, 3 fixed offline Mock source/check/extract requests before authority baseline. CSV baseline uses existing trusted template. Test intentionally revokes exactly one existing owner grant through existing API at the end; asserts exact row change revoked=true/revision+1 and all other authority/Attempt rows identical. No new authority or model requests after fixture baseline.

UI is planning only: graph save, stable sealed logical source versions, selection of existing node changes, persisted pure plan receipts, pending or permission/version blocked scope jobs, explicit partial omissions. No patch/execution/publication/PASS claim. Lost/malformed accepted replies retain original key/body in page memory; reload reads durable history but does not promise client retry-key persistence. Scope/version/identity/project invalidation clears protected evidence. Text rendering uses textContent.
