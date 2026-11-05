# HTTP期限修复目标回归

审阅候选f79b3e1dd8f02a07e01e759be354f4303e2a535e；目标差异及12项期限/实际Mock HTTP捕获测试见generation-http-deadline-fix.md。qualification pair、期限、原sender回归首次50 PASS、2 FAIL；两项失败的崩溃子进程因Python嵌入式._pth忽略PYTHONPATH，加载旧desktop-test-source，触发Trial software changed。

测试启动器改为显式传入父进程实际sim2act包根和测试根，保留隔离环境。只重测这两个失败节点，2 PASS；保留首次失败XML。因此为52个唯一节点经修正环境后通过，不是一次完整52 PASS，也不重复累加12项早期测试。source业务源码没有因测试启动器变化而修改。

production v3/literal v2目标指向上述候选并闭合完整字节，旧a0534197清单归档superseded-a0534197-*。尚未证明真实模型问题解决，P-B两个完整用例的失败亦保留。
