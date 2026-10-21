# Callback-counter test addendum

Decision: **ACK for this test-only increment**. The prior TAIL-OBSERVER-CLOSURE-REVIEW remains an accurate record of its then-frozen test version and 66-test batch. This addendum binds the final test version; it does not claim that the 66-test batch ran against this newer test hash.

The three diagnostic source hashes are unchanged: tail observer `b23c45591ca71b98d04a3c38fa5ccaf0141adf66476edae31ee33b37e8efc4a8`, stage observer `adacdff642f9dc30693df817c49c28e87114a14e813d7143e323ed14eab00d03`, prefix `dfe1299c28746db393afa3c26340c87792e7b39d665548f093c1b472151647d4`. Final `tests/test_cold_tail_diagnostics.py` SHA-256 is `f60cc0865a42070cdfd2b7f10ce93f13f96b63d888498dfcb6e98cb146c780be`; current files and callback before/after manifests agree.

Read-only inspection confirms foreign metaclass/key/prefix/boundary/error/report callbacks now increment external lists before raising; assertions outside the observer require the lists remain empty. An observer swallowing `pytest.fail` can therefore no longer by itself make these zero-callback assertions pass. The RowMapping control additionally arms a foreign index key only after safe insertion and independently verifies zero hash/equality callbacks. This remains a narrow local representation test, not a production input or G0 qualification.

Author `callback-final.log` reports **9 passed, 25 deselected, one existing warning, 0.18 s**. XML independently reports tests=9, errors=0, failures=0, skipped=0, time=0.176. Author callback-after manifest records Ruff passed and unchanged four hashes. The earlier 66-pass batch and these nine selected cases are separate executions of overlapping cases, **not 75 distinct tests** and not a final-version full-suite execution.

Reviewer read only the increment, hashes, author manifests/log/XML. No reviewer code, test, DB, product, Mock, G0, window or signal was executed, and no repository file was changed. No new window or grant is authorized by this ACK.
