# CSV DAG 目录旧冻结：静态BLOCK，动态4PASS

执行源 `8f7ffd938d0140c2e789b28eac3cdfd6b5a210bc`。独立仅原样新增4节点：**4 PASS / 0 FAIL / 0 ERROR / 0 SKIP**，RC0，JUnit 221.694秒，无重跑。是同作者4节点重复，不能增加unique分母。

整体独审仍BLOCK，两项源码问题已由root确认待修：

1. temporary delivery selection guard对literal/agent等早返回未释放，可能让既有图操作在workspace往返后永久静默失效。应仅作用于此CSV打开链，savedUse自己的持续guard须保留。
2. 已打开saved DAG后刷新目录，若同app权威GET实际拒绝，当前catch只清plain应用缓存，DAG proof/results仍在。应清该protected DAG视图并保留原dagReuseIntents键。现撤权测试只覆盖重新打开入口，不能证明刷新路径。

以上为只读源码审查，不冒称本轮额外动态复现；未扩大用例。动态两步/三步报告目录E2E确有正常NoModel Worker、新列v1/v2、冷同Run历史，guards含迟到/未知hint及明确撤权拒绝。finite typed-bool的PARTIAL只是关闭报告分支，不是异常恢复；条件图不能保存为内部实例的边界已由单Python节点实际验证。允许版本集合有4种，但本轮目录E2E仅两步/三步报告，dual/fixed未重验。

当前9执行源/测试文件前后匹配冻结Git，可在取证后另立新修复冻结。完整原件43项含4合成DB、info/results/branch-proof/stderr/XML/log/source前后，SHA/size见raw-manifest.json及raw-SHA256SUMS。21份statics为与执行HTTP响应SHA一致的源码拷贝，明确不是新增请求或原始流捕获。本审查未写仓库。

PG、真实浏览器/落盘、Windows、真实语义、真实模型、额外权限探针、旧lost/recovery与私有故障矩阵均NOT_RUN。
