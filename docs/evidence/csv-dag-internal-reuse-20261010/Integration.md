# 普通集成与精确来源

候选分支 `dev/csv-dag-internal-reuse-20261010`，起点开发SHA `67c6ccc8ad7d6f132205c2ac4f33b10defca5da7`。最终357源码/测试冻结 `d716feda486fd6f0322c11b2e1b5112f718a94fa`，产品与039全同字节。所有必要作者测试及独审按README读取，807 BLOCK和全部失败保持原归属；文档或快进不重复运行相同产品字节的测试。

普通fetch确认远端dev仍为67c6，main仍为 `6f688e4dd80b5c81d41aecde90e360d3629f9c21`；本轮没有main改动。合成测试PG前后0|0|0，普通stop/rm-v后自有容器与卷不存在。

候选最终SHA **`d8fd7c016c3f8048204af2702e9c3ad861fa9ec8`**，已普通推送 `dev/csv-dag-internal-reuse-20261010` 并独立ls-remote读回精确相同。候选原件先按嵌套.gitattributes保持原始字节，随后用verify.py检查全部357冻结文件和241复制原件的工作树及Git index/blob；[推送前](integration/pre-push-byte-verification.json)、[候选blob核验](integration/candidate-byte-verification.json)。

初次普通fetch只更新候选FETCH_HEAD，本地未配置候选remote tracking ref，因此集成前rev-parse检查失败，尚未切换或merge。未改配置，随后显式普通fetch `refs/heads/dev/f1-foundation:refs/remotes/origin/dev/f1-foundation` 与对应候选refspec；开发仍67c6、候选精确d8fd。实际证明67c6、原cc368/bf939/51487以及039/d716全为候选祖先，[远端与祖先](integration/pre-integration-remote.json)、[原fetch日志](integration/integration-fetch.log)、[显式fetch日志](integration/integration-explicit-fetch.log)。没有强制fetch或push。

本地 `dev/f1-foundation` 已 **ff-only 67c6→d8fd**，工作树无差异；集成后全部357冻结字节、241复制原件及两白名单Git/worktree再次相同，[集成字节核验](integration/integrated-byte-verification.json)。这次开发文档提交仅补记实际集成与审计文件；源码/测试与d716冻结完全相同，不重复跑已经验证的同一产品字节。最终开发SHA由普通推送后ls-remote、fetch及0/0状态读回记录在执行结果中，避免在提交内容里自引用自身SHA。

测试PG自有容器和卷不存在，前后schema/role/public为0|0|0；只有已知0字节codex-index-refresh.lock保留，无未知锁或Git挂起操作。禁止main写入、强推、部署及真实模型调用，LIVE=0和整体未验收边界保留。
