# Avoid redundant original-pointer map lookup, retain the full comparison

B2/9a prior accepted full-chain version remains preserved. Failed raw warm-up2 candidate f9 is recorded in cloud-warmup-20261028 and reverted; both raw/frontier frequency hints are4.

New C change only: for a memoized node whose CURRENT object pointer equals that node original, capture's unique baseline-map invariant means its old ordinal is exactly the current id. Use that id for the SAME assigned conflict/write checks, instead of computing a pointer hash and searching Tree.map. All other current objects use original find/changed logic; actual strong reference, full mutable/reducer/type/order/alias/scalar traversal and exception/unknown cleanup remain original. Matching identity NEVER accepts content by itself. No permissions, SQL, lease, graph scope or complete calibration are removed. Original pointers remain strongly owned by Tree, preventing address reuse.

Independent readonly review confirmed invariants and actual diff.115 existing structure/frontier/fingerprint/row-storage tests pass21.35s;4 new bytes/str/list/dict alias merge/reverse/swap/unchanged-pointer mutation tests pass.30s.137 source-qualification hashes and literal pin match.

A nine-batch alternating native-only reconstructed600KB graph probe against the EXACT frozen B2 binary measured median.220196→.148029s/150iterations(~32.8%). This is not full Graph.check or controller evidence. Compiler uses existing cc, no tool installation or permissions change. New structure binary8dd6dccf64148c1a402f7def0dc662691ba3590448fe0d5e810e73178bb72b4d, rawsnapshot unchangede494ef17e1b9e96757c3fdcbcacbd6c0c9d9faba8c8f8af0e63b8b96772c6d08.

Next is exactly one frozen real-clock full-controller run,7finite MockTransport/0real requests, actual test_onlySQLite, unchanged signed120s settlement/original300s Run deadlines. Do not infer old30s, PG/LIVE, Windows or semantic acceptance. Outcome pending.
