# Old HTTP DOM wait gate

The original complete run remains **704 PASS / 26 SKIP / 1 FAIL**. Its exact
failure interleaving is UNKNOWN. An isolated PASS never replaces that failure.

Parent 7beb20d full default-order regression: **599 PASS / 25 SKIP**, 343.43s.
Unmodified fd25994 original-order related modules: **110 PASS / 1 SKIP**, 120.18s.
The product web files, old harness and fixture are identical across these versions.
Both parent and current controlled real-response order demonstrate a shared old
window: a normal terminal poll begins an instance read and clears run/instance;
manual refresh returns while that read is pending. The original helper then reads
null. Releasing the real instance receipt restores the same IID/RID SUCCEEDED.
These injections establish possibility, not the exact original full-failure cause.

The approved patch changes only the two old harness test files. It preserves the
actual app/IID/RID and waits for matching terminal readback, visible form and no
busy action before dereferencing result. Normal polling, original 12s timeout and
existing wait interval remain. No product response, data, semantic result or
provider is substituted. Normal and explicit poll-refresh-order modes measured
**2 PASS**, 65.60s. Independent review separately measured **2 PASS**, 63.74s and
reproduced the parent timing window; root reported approval.

The isolated corrected fd25994 full default-order run completed **706 PASS /
26 SKIP / 0 FAIL**, 449.06s (4 warnings), including both DOM modes. This establishes
the approved harness fix on that frozen base. Root's combined full regression
after separate shared-budget work remains required. This evidence
makes no native-browser, visual, owner semantic or LIVE claim. No CI/push,
provider network request or role/Grant expansion was performed.

See dom-review.json for exact frozen test hashes and original/safe log hashes.
Fixture info files and credentials are excluded from this directory.
