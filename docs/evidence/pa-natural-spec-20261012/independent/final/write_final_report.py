from pathlib import Path
import json,hashlib,xml.etree.ElementTree as ET
p=Path(__file__).resolve().parent
r=json.loads((p/'final-result.json').read_text());q=json.loads((p/'qualification-static.json').read_text())
s=r['source'];over=r['overlap'];counts=r['combined_counts']
expected={line.strip() for line in (p/'collection.stdout').read_text().splitlines() if line.startswith('tests/') and '::' in line}
actual={x['classname'].replace('.','/')+'.py::'+x['name'] for x in r['selected']['nodes']}
assert actual==expected and len(actual)==77
assert counts=={'PASS':79,'FAIL':0,'ERROR':0,'SKIP':0}
assert r['selected_exit']['returncode']==r['extra_exit']['returncode']==r['extra_graph_exit']['returncode']==0
assert s['entries_before']==s['entries_after']==434 and not s['differences']
assert s['head_before']==s['head_after']=='82717272e61c2fa174ad8772e54cd9e9eb947c49'
assert not r['own_active_processes']
assert len(r['ui'])==5 and all(x['status']=='PASS' and not x['asset_mismatches'] for x in r['ui'])
raws=[q for q in (p/'extra-fixtures').glob('*/raw-response-barrier.json') if not q.parent.is_symlink()]
assert len(raws)==1;fault=json.loads(raws[0].read_text())
assert not fault['product']['evaluated'] and not fault['product']['blocked']
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
ui='\n'.join('| '+x['scenario']+' | '+str(x['checks'])+' | '+str(x['assets'])+' | PASS |' for x in r['ui'])
modules={}
for n in r['selected']['nodes']:modules[n['classname']]=modules.get(n['classname'],0)+1
modulelines='\n'.join('- '+k+': '+str(v)+' PASS' for k,v in sorted(modules.items()))
report=f"""# Independent final review: LIMITED PASS

Frozen HEAD `{s['head_after']}`, branch `{s['branch_after']}`. Baseline `259f583eba6dd6c5580834878da6bd3cb1f648a7`. Repository writer is root; reviewer changed only this task's workspace evidence. No current core blocker was identified in this finite engineering scope.

## Actual terminal tests

**79 unique named test nodes: 79 PASS, 0 FAIL, 0 ERROR, 0 SKIP.** This consists of selected77, reviewer raw-response extra1 and reviewer PASS-graph extra1 in three separate completed processes, not one 79-node execution. Selected returncode0, wall {r['selected_exit']['wall_seconds']:.3f}s; extra returncode0, wall {r['extra_exit']['wall_seconds']:.3f}s; PASS-graph extra returncode0, wall {r['extra_graph_exit']['wall_seconds']:.3f}s. Complete separate stdout, stderr, JUnit, commands, exit records and fixed SQLite fixture directories are retained. Collection77 was checked against exact terminal JUnit identities; no unnamed placeholders or progress dots were counted. No test/assertion/lease/budget was altered by reviewer.

{modulelines}
- Reviewer-only response-cell revocation probe: 1 PASS.\n- Reviewer-only checker-PASS graph-replacement probe: 1 PASS.

Actual intersection with author/final-collection.json ({over['author_collected']} collected nodes) is **75**. Reviewer additionally ran historical233/a747 cold-continuation representatives2 and custom probes2. Author and independent totals are not added. The intersection is an identity comparison, not a claim about the author's eventual outcome.

## Tested engineering behavior

Actual SQLite/Worker tests exercise single-model, two logically independent model nodes, and sequential-feedback nodes, each with initial PASS and one-repair paths. The recipe selects node IDs/operators/edges; current read feedback is consumed and the additional controlled probe confirms checker-PASS single graph cannot be replaced in the final response by another legal sequential graph (VERSION_CONFLICT, no app, three synthetic requests). A separate Store reads a new neutral synthetic material and produces its own model-node receipts/JSON artifact rather than returning the saved sample. The current implementation dispatches independent logical DAG branches serially; simultaneous model dispatch is not claimed.

Controlled callback/data mutations cover cancel/revocation/Goal/fence/stop, final node version/created_at/lease changes, unchanged-audit enforcement, unused parameter/audit fields, fake rejection, typed/terminal changes, operation Run linkage and AppRun instance scope. The relevant transactions reject malformed or late evidence, and save rollback preserves no partial artifact/grant/effect/typed success. Default-off and reduced-budget cases reject execution. Unknown outcome recovery uses the original key and does not resend the uncertain model node. Malformed quote/usage/model identity/extra/truncated response and preservation bounds reject; Unicode coordinates, unassigned relations, uncovered source and all16 human Goal unresolved remain represented. Actual old literal continuation requires exact instance consent and cold NoModel worker; qualification does not replace that consent. The two accepted compressed historical SQLite fixtures use process-local synthetic replay clocks within their original TTL; no old software was installed, no old seal was re-signed, and expired wall-clock grants were not revived.

## Actual offline page evidence

| Scenario | Recorded checks | Distinct actual asset hashes | Result |
| --- | ---: | ---: | --- |
{ui}

Pages use real in-process HTTP TestClient bridged by IPC to JSDOM, with local MockTransport synthetic model shape; no listening socket or native browser. Each asset hash was compared against the complete frozen source map. Raw checks/requests/actions/HTTP static loads and model wire are preserved. Lost binding responses use original-key GET recovery; editor undo makes the delayed response ineligible to paint/open; both poisoned sample body and poisoned sample_nodes prevent confirmation. These controlled malicious-200 fixtures demonstrate the specific tested integrity behavior, not a real attack or production incident.

## Independent actual private-cell calibration

The extra probe protects original/current Attempt parameters, usage and **nonempty raw response**, plus the original/current Run, contract, resource and operation/intent private cells. Intentional full response SELECT before and after the product flow each triggered actual SQLite cell denial. Product full private cell evaluations0 and blocked0 after source revocation, including inspection403. The received response survives in owned `REJECTED_KNOWN` Attempt history with a nonrefundable reservation; one synthetic send, typed0, artifact-save operations0.

Exactly one owned UPDATE is allowed to evaluate the response's SQL **NULL-presence predicate** for its ID/Run/state CAS. This is not a full response projection; this review does not claim zero every backing JSON/null-flag evaluation. The barrier's guarded TEMP views/UDF/authorizer are controlled test instruments, not a production authorization mechanism. Raw trace is `{raws[0].relative_to(p)}`. The wider family-marker stripping space was statically reviewed, not exhaustively dynamically tested in this selected run.

## Frozen source and history

Complete recursive src/tests including fixture files plus pyproject closure: **434 entries before and after, 0 differences**, exact HEAD/branch unchanged. Review snapshot11 actual files match both frozen entries and checkout bytes. Source-before SHA `{s['before_sha256']}`; source-after SHA `{s['after_sha256']}`. Qualification pin/JSON SHA `{q['qualification_sha256']}` matches the exact73 implementation file map. Only its sole pin literal is normalized to zero64 to avoid a hash cycle; runtime implementation approval fingerprints remain actual full bytes. Original CHANGED/ANCHOR_HASH/old anchor bytes are unchanged. Qualification22 exercises known accepted sources and exact-mutation/unknown-source closed rejection. Static findings S1–S6 and the addressed frozen checks are documented in STATIC_FINAL_ADDENDUM.md; static observations are not counted as failed tests.

The earlier design and mutable code-r1 reports/manifests match their original recorded hashes (history-preservation.json). They contain design/static findings, not reviewer dynamic red counts. No final-round reviewer test FAIL or fixture error occurred. Parent's separate author red/repair history remains its own evidence and is not deleted or relabelled here. Earlier labelled-spec task evidence, disk recovery, failures and superseded reports were not edited. Current reviewer performed no escalation, permissions/environment change, cleanup, dependency installation or repository write.

Own selected, raw extra and graph extra processes are terminal; own active pytest/node/runner processes0 at final evidence capture. Parent's distinct test processes are outside this statement.

## Not run / limits

Real network/model calls, paid API, credentials, semantic gold acceptance, real business data, PG, Windows, native browser, CI, wheel build, deployment, owner semantic acceptance, full P-A/P-B and permanently cancelled exact install/cancel race: **NOT_RUN / NOT_VERIFIED**. This is a bounded synthetic engineering qualification with model execution disabled by default, semantic UNKNOWN/NOT_RUN, owner PENDING and publication disabled. It does not certify citation completeness as meaning or a general old-database migration. No production data or private source exploitation is claimed.

Primary raw evidence: selected.xml/extra.xml/extra-graph.xml, selected.stdout/stderr, extra.stdout/stderr and extra-graph.stdout/stderr, selected-exit.json/extra-exit.json/extra-graph-exit.json, source-before.json/source-after.json, final-result.json, author-overlap.json, qualification-static.json, selected-fixtures, extra-fixtures, extra-graph-fixtures and final manifest.json.
"""
(p/'FINAL_REVIEW.md').write_text(report)
print(json.dumps({'report':str(p/'FINAL_REVIEW.md'),'sha256':sha(p/'FINAL_REVIEW.md'),'unique':r['combined_unique']}))
