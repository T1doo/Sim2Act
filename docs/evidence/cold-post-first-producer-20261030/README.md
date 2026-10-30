# Cold post first-producer transfer

The post/G1 graph is created after the original five writes and rereads its own SQL facts. This change transfers only this epoch's detached facts and completed intent/receipt/node data using the existing complete Source ownership protocol. The entry Run retains its original object identity and normal graph root. Actual Run, counter-manifest and receipt-binding checks remain original; G0's fixed receipt continuation/frontier is unchanged. No earlier graph, authority verdict or PASS crosses W5.

The same actual Cold completes two fixed Mock model nodes, then the new reader checks full counters, verified node proofs and owned receipt-result against the complete original public result. A separate passive observation at the original writer entry reads actual RECEIVED data and validates the pending consumer before allowing that original worker to finish. This observation uses a normal BEGIN IMMEDIATE transaction with no increase in total_changes; it is not a mode=ro connection, actual W5/G1 acceptance or performance measurement. No clock/callee/row/authorization result is replaced.

The original full queued-Cold prefix and actual typed collector also pass without the special early-return data scenario. The exact-list counter fast path remains strict and can MISS into the original complete counter validation. No overall performance improvement is claimed until the frozen same-large-input run completes.

Prior complete-source candidate 3fbcda8a still rolled back at 120.0113 seconds (G0 47.5296, writer G1 72.4807); its unmodified evidence is preserved in the Generation evidence folder. No 30-second success, complete save/reopen, live Intern, PostgreSQL or Windows result is claimed here.
