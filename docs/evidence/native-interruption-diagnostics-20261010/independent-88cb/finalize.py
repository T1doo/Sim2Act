import pathlib,json,hashlib
root=pathlib.Path('/tmp/sim2act-native-diagnostics-independent-88cb-20261010');sha='88cb3c64b5dcbaf3df7183ebbf72773547585e15';old='d8f2101b5259be5b51d00eca527db7cf3b4c5b37'
result={'verdict':'LIMITED_PASS','source_sha':sha,'scope':'redaction delta only','independent_real_pytest_materials':6,'new_channel_redaction_checks':18,'pure_boundary_checks':8,'failure_summary_check':1,'total_checks':27,'actual_child_exitstatus':1,'actual_child_expected_failures':6,'freeze_files':360,'before_after_git_worktree_match':True,'unchanged_frozen_vs_d8':358,'changed_paths':['scripts/native_pytest_diagnostics.py','tests/test_native_pytest_diagnostics.py'],'product_files':69,'product_all_identical_to_473':True,'old_review_retained':{'sha':old,'verdict':'BLOCK','root':'/tmp/sim2act-native-diagnostics-independent-20261010','passed_scenarios':3,'passed_checks':15,'rerun':False},'restrictions':{'native_or_PS_runtime_tested':False,'PG_tested':False,'original_26_failures_fixed_or_accepted':False,'CI_operated':False,'real_model_calls':0,'repo_or_refs_modified':False},'remaining':['Windows900/Edge240/Node150 NOT_ACCEPTED','PG resources-history Future10 OPEN','Report GET idle6 OPEN','PROJECT PENDING/BLOCKED_PARTIAL; LIVE0']}
(root/'FINAL_REVIEW.json').write_text(json.dumps(result,indent=2))
(root/'FINAL_REVIEW.md').write_text('''# Independent redaction delta review: LIMITED_PASS

Exact source `88cb3c64b5dcbaf3df7183ebbf72773547585e15`, compared with archived `d8f2101b5259be5b51d00eca527db7cf3b4c5b37`. This is an incremental result for the diagnostic redaction change only.

An independently written private fixture produced six real pytest assertion failures: the original Basic and space-containing password values; escaped quote/backslash values; unquoted Basic authorization and its remaining words; a fully quoted value spanning actual newline characters; JSON credential-key fields; and uppercase PostgreSQL URI plus Bearer. All values are synthetic. Each case is absent from each new JSONL, flushed diagnostic stdout and Report channel: 18 channel checks PASS. Six corresponding pure-function checks, ordinary diagnostic text preservation and the line after a closed multiline credential preservation also PASS. The summary verifies six actual failures, expected exit1 and a complete failing suite: one further check. Total 27 checks.

The real child exit1 and six fixture failures are intentional redaction materials, not regression failures. Original pytest stdout/JUnit are retained raw and contain these synthetic inputs; the redaction claim covers the three newly added diagnostic channels. See `redaction-results.json`, `diagnostic-stdout.log`, `events.jsonl`, `report.log`, `pure-boundaries.json`, `test_fixture.py`, `child.log` and `summary.json`. The independently authored harness is `independent_delta.py`.

All 360 frozen files matched the manifest, exact Git source and worktree before and after. Relative to d8 only `scripts/native_pytest_diagnostics.py` and `tests/test_native_pytest_diagnostics.py` changed; the other 358 frozen files are identical. All 69 src product files remain identical to `47388f573746daa27f8d5790ca358eef91378ad5`. See `source-before.json`, `source-after.json` and `delta-byte-bridge.json`.

The d8 BLOCK and its 3 PASS scenarios/15 transparency, selection, fixture, hard-kill and incomplete-tail checks stay archived under `/tmp/sim2act-native-diagnostics-independent-20261010`. This run does not relabel or repeat those checks. Unchanged observer, summarizer and PowerShell wiring are bridged by the exact byte comparison.

No PowerShell/native Windows/PG or actual model was executed, and no author CI, process, test, shared source or refs were modified. This review neither diagnoses nor accepts the original native 26 failures. Windows900/Edge240/Node150 remain NOT_ACCEPTED; PG resources-history Future10 and Report GET idle6 remain OPEN. PROJECT PENDING/BLOCKED_PARTIAL; LIVE0.

Copy only files explicitly listed with SHA256 in `COPY_WHITELIST.json`. The old BLOCK remains necessary evidence; new output is a bounded redaction-delta LIMITED_PASS.
''')
files=[]
for p in sorted(root.rglob('*')):
 if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts and p.name!='COPY_WHITELIST.json':files.append({'path':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
(root/'COPY_WHITELIST.json').write_text(json.dumps({'artifact_root':str(root),'source_sha':sha,'verdict':'LIMITED_PASS','count':len(files),'files':files},indent=2));print(json.dumps({'verdict':'LIMITED_PASS','sha':sha,'checks':27,'whitelist_count':len(files),'review':str(root/'FINAL_REVIEW.md')}))
