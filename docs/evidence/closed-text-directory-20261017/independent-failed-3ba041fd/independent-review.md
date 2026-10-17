# 四步目录旧冻结源：独立未通过记录

执行源 `3ba041fd945223e27b789f2260c1b16a40937b30`，独立原样执行同2节点：**1 FAIL(use) / 1 PASS(guards) / 0 ERROR / 0 SKIP**，RC1，JUnit 25.616秒。没有重跑，不能报告动态通过。

use在首个实际SUCCEEDED/v1后的“successful history retained without extra partial result”断言失败：driver第60行使用literal分支“历史结果 v1”，但workflow经internalResult普通分支显示“结果 v1”。第66行冷重开也有同类标签，尚未执行到。产品首个Run的状态/步骤/引用长度/v1断言先前已过；false分支及冷重开本轮没有完成，不可补认通过。该标签差异在我的初始静态审查中漏检。guards参数独立通过，但不能替代use。

原log/XML、两合成DB/info/result/stderr和成功guards数据库证明原样保留；失败use未产生database-proof.json，未伪造。35项原件/源码拷贝的完整SHA/size在raw-manifest.json及raw-SHA256SUMS。statics明确为与记录HTTP SHA一致的冻结源码拷贝，不是额外请求或原始流捕获。source-before/after证明执行相关8源/测试文件字节与冻结Git一致；未写仓库，root可在取证后修正driver标签并另立新冻结。

这是ASGI/JSDOM/合成SQLite工程执行，不是PG或真实浏览器。没有扩大测试、PG/browser/cache/权限探针或私有矩阵；真实模型0。
