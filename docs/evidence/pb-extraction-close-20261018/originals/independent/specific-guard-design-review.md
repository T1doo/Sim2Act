# 具体 guard 设计复核（只读，实施前）

总体：CloseInput(identity17,显式consent)、同project锁、专有双journal、receipt分开original fullExtractInput hash/Close DTO hash/receipt hash，以及shared _extract内先source_gate后永久fence的方向可行。Cold metadata不必重建正文；关闭是保留此key永不执行，不是验证丢失的正文。POST已受理不能关闭，terminal与accepted共存应冲突。

**需修的权限风险：拟④在source_gate之后直接pair其它PB app的EXTRACT，读取整个ExtractInput原wire，是新私有读取路径。** 原pb_natural_specs.GET:515先load_draft；apps.load_draft:261先draft_gate；text_continuations:467再到spec/PB.scope_gate；pb.scope_gate:188–204明确在完整candidate/extractionledger之前核target runtime READ与项目SAVE。Source READ只授权来源，不授权另一个目标应用的recipe/name/target引用完整请求。不能因为不读Goal/material/result/candidate正文便跳过原wire门。generic pair通过graph.lookup selects整个snapshot，不是metadata-only。

安全替代：④不调用pair(EXTRACT)，仅选择下列scalar，且将候选相关集合由多个独立锚OR构造，不仅candidate.spec_task单字段；上限65、任何缺失/冲突/overflow保守UNKNOWN。

- task_extractions：task_id/principal_id/request_key/app_id/request_fingerprint，frozen kind/project/runtime/sourceRID/key/fullrequestfp等标量。
- app：id/project/runtime、namespace/origin/spec_task.kind/sourceRID、manifest.source_run_ref；不选candidate整列。
- META两份：PK、request_fingerprint/fingerprint列，request/response中的全部Metadata ID字段；这些本来就是独立权限标识，无recipe/name。
- EXTRACT两份：PK、request_fingerprint/fingerprint列，snapshot.request.review.source_run_id/request_key，response中kind/principal/project/app/runtime/sourceRID/key/fullrequestfp/reviewfp/candidatefp/sourceprooffp。绝不读request.review/name/recipe或snapshot整列。

exact原key任何相关接受残留都不可关闭；其它key的metadata必须完整、唯一并且跨marker/META/EXTRACT/app一致才可视为另一个key。注意两个fingerprint列相等只是metadata一致性，不是独立重新hash完整wire；报告不能冒称fullproof。若设计确实要完整wire重验，先对该app用原scope_gate完成当前target权限，拒绝/撤权/stale时保守UNKNOWN，不可降门兜底。

⑤principal固定name或Grants只可作OR嫌疑阻断，不能作完整family证明或反向判无orphan。还要保留prospective app/runtime精确ID存在即拒，这能挡已知原票据对应接受残留。无法从有限metadata证明absence就保持UNKNOWN，不拿name无命中当NOT_ACCEPTED证明。

其它必要顺序：source tenant/path与identity17完全相等；project锁内任一terminal残留使所有PB _extract调用（包含pa_trial_dispatch:203）在review/oldkey/写入前永久拒。strict可读closed必须验证双pair、receipt自身hash、全部scope/hash与absence一致，损坏或只剩seal不能当未关闭。CLOSE-first与POST-first实际两个DB事务竞争不能只做顺序调用。UI显式CLOSE后仍留票据，另点GET才按本地独立17字段/hash+同WebLock/raw/pending/current忘记；close丢回包不自动清除，accepted控制状态不允许安装/forget。没有模型、executor或Grant扩展。

本加审未执行任何产品/HTTP/Worker/模型，未改repo；上述为实施前具体风险与可行替代，不是实际漏洞复现或新资格PASS。永久取消安装digest双actor窗口仍排除。
