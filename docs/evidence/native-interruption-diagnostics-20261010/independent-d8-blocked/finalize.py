import pathlib,json,hashlib
root=pathlib.Path('/tmp/sim2act-native-diagnostics-independent-20261010')
sha='d8f2101b5259be5b51d00eca527db7cf3b4c5b37'
review={'verdict':'BLOCK','source_sha':sha,'base_sha':'e4c75fa838064556bcdc972bad93ca9d6149f4d7','independent_scenarios':4,'passed_scenarios':3,'blocked_scenarios':1,'checks_in_passed_scenarios':15,'additional_redaction_prerequisite_passed':1,'redaction_assertion_failed':1,'PS_static_contract_checks':8,'freeze_files':360,'freeze_before_after_git_match':True,'product_files':69,'product_all_identical_to':'47388f573746daa27f8d5790ca358eef91378ad5','finding':{'id':'DIAG-REDACTION-01','severity':'BLOCK','inputs':["authorization='Basic CI_SYNTHETIC_BASIC'","password='first CI_SYNTHETIC_SPACED_PASSWORD'"],'leaked_values':['CI_SYNTHETIC_BASIC','CI_SYNTHETIC_SPACED_PASSWORD'],'channels':['JSONL','flushed diagnostic stdout','Report stdout'],'synthetic_only':True,'evidence':'redaction/redaction-result.json'},'execution_limits':{'PowerShell_runtime':False,'native_Windows_CI':False,'original_26_failures_diagnosed_or_fixed':False,'author_tests_reused_as_independent_evidence':False,'PG':False,'real_models':0,'repo_edits':False,'refs_edits':False},'remaining':['redaction complete quoted/unquoted credential value handling','native Windows900/Edge240/Node150 NOT_ACCEPTED','PG resources-history Future10 OPEN','Report GET idle6 OPEN','PROJECT PENDING/BLOCKED_PARTIAL; LIVE0']}
(root/'FINAL_REVIEW.json').write_text(json.dumps(review,indent=2,ensure_ascii=False))
(root/'FINAL_REVIEW.md').write_text('''# Independent review: BLOCK

Exact candidate: `d8f2101b5259be5b51d00eca527db7cf3b4c5b37`; base `e4c75fa838064556bcdc972bad93ca9d6149f4d7`.

The new diagnostic channels leak part of credential values. An independently authored real pytest failure containing `authorization='Basic CI_SYNTHETIC_BASIC'` and `password='first CI_SYNTHETIC_SPACED_PASSWORD'` leaves both final tokens visible in the closed JSONL append, flushed `SIM2ACT_CI_DIAGNOSTIC` stdout, and subsequent Report stdout. The credential-key regular expression consumes only the first word. All inputs are synthetic; no actual credential was used or disclosed. Database URI, Bearer and simple single-word API/token/secret inputs were redacted in this probe. Evidence: `redaction/redaction-result.json`, `events.jsonl`, `child.log`, `report.log`, `failure.log` and `test_fixture.py`. The raw original pytest traceback is retained separately; the failing oracle evaluates the three newly added diagnostic channels.

Four independent scenarios ran: three PASS with 15 named checks, one BLOCK with one successful prerequisite (actual exit1) followed by the failed redaction oracle. The normal-selection comparison verifies identical baseline exit1, selected three-test set, and fixture setup/teardown effects and order. An owned private child was actually SIGKILLed during its second test: the earlier failed phase and exact active node were already durable in stdout/JSONL, Report recovered them with one not-started test, no session finish, and explicit incomplete status. Missing trace and a partial final JSONL append also remain incomplete and readable. These are self-authored fixtures and assertions, not author test results.

Eight static PowerShell integration contract checks cover the unchanged workflow and setup/cleanup bytes, optional explicit observer CLI, absence of plugin injection into PYTEST_ADDOPTS, original -q selection, retained Ruff/mypy/R0 gates, and direct Report invocation against the owned JobRoot trace/JUnit. PowerShell and Windows were not executed. Existing CI was not started, restarted or accessed by this review.

All 360 frozen paths matched Git, the provided freeze and worktree before execution, after execution and at final seal. The 69 src product files are byte-identical to `47388f573746daa27f8d5790ca358eef91378ad5`. See `source-before.json`, `source-after.json`, `source-final-after.json`, `product-freeze.json` and `PS-contract.json`.

This review does not establish the identities or fix the original native 26 failures, accept Windows900/Edge240/Node150, or close either historical PG resources-history Future10 or Report GET idle6 OPEN. No PG, actual model, shared source/test/ref or author process was touched. PROJECT remains PENDING/BLOCKED_PARTIAL; LIVE0. The redaction issue blocks this diagnostic candidate. Preserve this failed freeze and perform only the corrected redaction delta and necessary boundary checks on a later exact freeze.

Copy only the explicit SHA256-listed relative paths in `COPY_WHITELIST.json`; all raw failures and synthetic harness materials are retained. Cache files are excluded.
''')
files=[]
for p in sorted(root.rglob('*')):
 if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts and p.name!='COPY_WHITELIST.json':
  files.append({'path':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
(root/'COPY_WHITELIST.json').write_text(json.dumps({'artifact_root':str(root),'source_sha':sha,'verdict':'BLOCK','count':len(files),'files':files},indent=2))
print(json.dumps({'verdict':'BLOCK','sha':sha,'whitelist_count':len(files),'review':str(root/'FINAL_REVIEW.md')}))
