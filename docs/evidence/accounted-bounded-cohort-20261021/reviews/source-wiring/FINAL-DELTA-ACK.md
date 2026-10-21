# 最终冻结后的来源/默认范围增量确认

**FINAL_DELTA_SOURCE_WIRING_AND_RECORDED_RESULTS_ACK_UNINSTALLED_ONLY**。本文件独立追加，原 FINAL-CODE-REVIEW 为 earlier review，其旧 SHA 不冒充本次已审代码。

只读核查当前 8 文件与 `/tmp/sim2act-accounted-cohort-20261021/final-source-hashes.json`：逐字节 SHA 全匹配。budget 最终为 8064435c5a0e4c286a9b7db7781d42986ada3f0e7cc104c1b1b4662c970c2dda，cold_accounted 为 6bc0a72bcb84d3b18f171f7991bc4bb50804a36b644ab3ca5344841d95d594ab；完整清单见同名 JSON。

本次增量核对结果：

- raw/native `copy(..., typed=False)` 不会把 hidden Pydantic 值悄悄规范为字典；typed=True 仅用于已固定校验的 Slot/Capture/BodyArchive 及 Slot/Ledger snapshot。memo 按 `(id, typed)` 隔离，因此同一容器先在 typed 域复制不能污染 native 域的资格判断。新测试明确先 typed 成功，再 native 应 Unsupported；既有 codec 可处理的 hidden Limits 走整族未发行 LEGACY，仍是同批 producer 结果且无重读。
- `_source_exchange` 在读取 family.scope/_allocation 前先检查 exact Family、exact Scope、exact str role，拒绝 forged family 的 foreign 属性回调；旧业务体 `_source_exchange_value` 未改。
- `_Value._check` 先 exact family/node、packet、exact ref/range，再 sentinel 检查 allocation，避免旧 forged/missing-allocation 节点导致非预期 AttributeError。generation 锚点也用 sentinel。合法旧 allocation=None 节点仍匹配；带 ledger 的 OWNED view 仍不能换成 None 绕过预算。
- 再次仅以 AST/字节读取对账：`_freeze`、`_equal` 全函数 AST 与 e617 相同，提取后的 Source 业务体（仅统一函数名）相同；natural_spec_runtime/natural_live_admission/pa_trial_dispatch/natural_source_archives 全文件与 e617 字节相同。默认 `_prepare`、SQL、原 full guards、旧 codec 继续保留，默认 runtime 未安装此分流。

未发现上述来源/默认兼容范围未闭 P1/P2。monitor 的预算数值及 allocation 覆盖限定结论不由本报告扩张，也不重新声称 RSS/原 guard/DB decode 全域有界。

只读核 `verified-junit.xml` 原件：181 testcase，0 failure/error/skip，suite time 128.098s；`verified-pytest.log` 为 181 passed, 1 warning in 128.10s。此为核查根侧已运行原件，不是独审自己执行。前一失败轮不删、不当作最终通过。本次未重跑任何测试、未导入产品、未开 DB、未执行 Worker/Mock/PB/G0，仓库写入 0。

结论仅限未安装组件的来源/默认范围和上述记录一致性；不构成产品 bounds 资格、性能改善或安装/运行窗口批准。
