# Unique Source native window metadata and pending original retrieval

Actual authorized push26ee1cf0120f5d7c3a4ef10fd911469cad951d99 created exactly
run39764605582 / Source job119776830173, attempt1. Run and job metadata both
completed/success. Source job10:38:28–10:39:41 UTC=73s; checkout8s; native Source
step10:38:39–10:39:37=58s. Other native-mock119776831420 skipped. The head SHA is
**metadata head**, not an independently retrieved actual inventory/checkout hash.

No workflow rerun or replacement window was requested. No source was changed
while running. Frozen8 hashes still match the reviewed candidate; ordinary
metadata checks did not start a model, Worker or UI window.

New job's first normal GitHub CLI logs read followed GitHub's temporary storage
redirect, then returned `Forbidden`, exit1 with stdout0. No numeric HTTP code or
separate response body was retained. This does not establish403, token expiry,
missing GitHub scope or a particular denial layer. The signed temporary URL was
redacted in log-read-denial.json; original error is preserved privately at the
recorded local path and hashed. No retry, alternate download/connection or new
credential/permission was attempted. Historical denied downloads were not used.

The normal unauthenticated public job page displayed “Sign in to view logs”.
Parent was asked for original SOURCE_UI FILE/CHUNK records only through its
normal accessible public page, without retrying denied signed storage. These
records are pending at this archive state.

Consequently result.json keeps actual runtime request counts, cleanup and
inventory unconfirmed, local PNG list empty and pixels NOT_REVIEWED. It does not
substitute CI green for native/runtime evidence. The frozen successful-control
path is designed to retain3 PNG files+SHA and bounded base64 originals in logs;
those bytes have not yet been independently retrieved, decoded or viewed here.
No inference from the previous extract Edge PASS or Source process proof fills
this gap. No G0, real model, native cross-Run ABA or visual beauty is signed off.

## Read-only independent review

`/root/source_native_ui_review` inspected these metadata files and all8 current
frozen hashes without network calls, product/test/DB/service/CI execution or repo
writes. It confirmed sole Source job metadata success73s/native58s/checkout8s and
that null counts/cleanup and missing PNG/NOT_REVIEWED accurately reflect the
missing originals. It requested distinguishing metadata head from actual
checkout; result.json now records metadata_head_sha and actual_checkout_sha=null.
Its metadata ACK does not approve runtime assertions or screenshot pixels.
