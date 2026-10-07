# Recovery correction before changing frozen named draft UI

Frozen product da81199c0e18b084d99f282efe976543c9e53117 is NOT_ACCEPTED for complete
recovery boundaries. Independent controlled-DOM review found that runReportApp cleared
unknown pending state on any 422. A lost accepted response followed by same-key retry 422
could unlock a new key despite the earlier request being accepted. Previous 62-family/DOM and
16 initial cases do not sign off this missing composition; their evidence remains unchanged.

Minimal correction: only a first submission without earlier uncertainty may clear its key after
an explicit authoritative 422. A retry following lost response or malformed 200 must retain its
original immutable body/key and block new intent, regardless of a later 422. No backend, authority,
provider, native, parent frozen CI source or other family changes are authorized by this correction.

Independent oracle: actual HTTP first invalid typed facts returns 422 and permits correction;
actual accepted cold POST then synthetic lost receipt followed by the actual cached retry response
replaced at the transport boundary with 422 retains exact key/body and pending lock; another
explicit same-key successful receipt maps to the original persisted Run. Repeat uncertainty with
malformed accepted 200 followed by retry 422. There must be no additional Run or provider call.
Only focused recovery probes and static checks, no long DOM/family/full rerun during parent full.
Owner acceptance remains PENDING; overall NOT_ACCEPTED/UNKNOWN; independent review must
confirm final source hash separately from the former frozen test hashes.
