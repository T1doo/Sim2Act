# Background timer coalescing evidence plan

Read-only source/trace: actual8c106 PG full timed out at90s,40/49 checks. Trace817events374starts,22fault targets captured correctly. No caller/timer-iteration labels: causal attribution remains UNKNOWN.

Quantify paths/durations, treat synthetic_later_422 as ended (not real inflight), distinguish mandatory source sequences inferred by unique <=30ms continuations from actual caller instrumentation. Health34,32 inferred full prefixes,18 overlap subsequenthealthstart; medianprefix2726.5ms,max6080. This supports excess overlapping background refreshes, not sole timeout causation.

Root authorized minimal app.js in-flight latch plus finally only around existing2500ms backgroundcallback. Explicit user refresh/open,49checks/14promotionPOST/7Mock/90s,provider/Grant/permission unchanged. Do not reset latch on identity/project clear; old context guards suppress stale data, final completion/error releases latch. No catchup timers/queued retry.

Oracle: actual completeHTML/app.js loaded via script element, original registered callback invoked by controlled scheduler; registrationdelay2500 preserved. Only synthesized deferred API controls health/resources/run pending/errors. Actual production refresh/showRun/clearIdentityView/onchange and ordinarySubmission UNKNOWN map run unmodified. This is explicitly synthesized API/scheduler evidence, not HTTP/PG/native. RED oldsource secondhealth duplicate; GREEN pending/error eachstep, explicitrefresh,project+identityABA,no premature release,UNKNOWNsamebodykey andzeroautomaticPOST. Then one frozen actualSQLite Graph2+Report49+conditionalapp4 regression; root owns separate PGfocused and evidence of real wallclock effect. No new full/CI claimed.
