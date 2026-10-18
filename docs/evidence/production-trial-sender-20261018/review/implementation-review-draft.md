# Sender WIP 独立静审

当前有三项局部 P2 待修；均为静态控制流发现，没有动态复现或产品/pytest/DB/HTTP/网络执行。源字节记录与当时实际读取的关键原片段在 implementation-review-draft.json / wip-capture-history-fragment.txt；本目录未seal，旧sealed目录未改。

## P2_CAPTURE_JOURNAL_HISTORY_BINDING

`production_trial_sender.py:137–142` 的 `_history` 丢弃 `_loaded` 返回的 slot，随后 `_captured` 合法即返回。它未核 capture.outcome==原slot.settlement、capture存在时原槽已attempted且settled。两个分别合法sealed但互相分叉的capture/journal，或孤立capture，因而被当普通历史；同文件 `_receive:184–190` 对这些情况反而严格拒绝。

最小修正：history取slot，若capture存在，要求slot.attempted且settlement与capture.outcome完全相等；capture缺失时只容许尚无settlement的pending/marked历史（包括崩溃窗口）。已settled缺capture应明确OUTCOME_UNKNOWN，不能补填或作为完整sender证明。该检查不新增source权限，不改变原key不重发，capture/settlement已有完全对应的cancel拒收历史仍可只读。

## P2_EMPTY_CAPTURE_DERIVATION

`_captured:118–125` 对body_b64=None且raw_bytes=0只要求EMPTY+UNKNOWN，没有核空body的真实SHA及从空bytes应得的null用量等。合法typed/sealed metadata可包含任意64位rawSHA或空体却known token事实，仍通过读取，而 `_derive(b'')` 不会产生这种状态。

最小修正：EMPTY路径同有body路径一样，以 `_derive(b'',complete,received_response)` 精确重验capture；oversize无原body不能重新推导的边界继续如实保留。不要把缺body的元数据当真实权益证明。

## P2_RUN_SCALAR_GATE_BEFORE_HISTORY_BODY

设计要求owner/scope/wire/marker及Run身份标量先于私有capture body。`_receive:179–183`有实际Run principal/project/runtime标量核验，但 `_history:139–141`没有；`_loaded`只依据可信ledger绑定，不核当前Run身份存在性。建议把该原metadata-only核验移至 `_loaded`，供history/guard/receive共同复用。仅核固定owner/project/runtime，不加active fence/Goal授权要求，以保取消/过期后的合法只读和保账。

## 已核正常控制流

- 新offline入口及guard都检查exact Worker/Settings/Store、test_only SQLite、mock/livefalse/token空和exact MockTransport，且provider必须实际configured_provider/InternModel及同transport。原synthetic占位只在既有provider内部，不写回Worker.s。
- wire严格五字段及model/stream/max_tokens限定，原bytes不重建；正常capture只用captured.body，忽略parsed。usage先取原bytes，再parse_response/returned_model判protocol；失败为UNKNOWN并保known分量，不误进入RECEIVED接受。
- 原reserve/marker duplicate立即history退出，无adapter重复。wire_guard当前slot需marked/unsettled/nonhalt且policy._fresh，限定本次请求deadline。guard到IO不可原子保证的窗口仍明确。
- `_receive`将capture双镜与journal四镜放在同Store.tx，通过新private `_apply_in_transaction`，无内层commit。取消/撤权等fresh失效只使late settlement不接受；CAS异常整体回滚。旧已settled无capture不补填；已capture完全同Outcome重复才历史。
- journal `_history_anchor`提取保原双标量锚门；同TX helper保原identity/revision/duplicate和active末fresh。public签名未变；纯参数验证由旧TX外移至TX内，属于可说明的入口时机差异，不是此次确定P1/P2。

源仍WIP，Ruff I001与新测试待作者处理。当前不把静审当实现通过，亦不要求重跑旧19/12或增加故障矩阵；三项校验可用同一新capture正例中的精确控制断言验证，不需扩大业务范围。
