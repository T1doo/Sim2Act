# 普通集成与精确来源

候选分支 `dev/csv-dag-internal-reuse-20261010`，起点开发SHA `67c6ccc8ad7d6f132205c2ac4f33b10defca5da7`。最终357源码/测试冻结 `d716feda486fd6f0322c11b2e1b5112f718a94fa`，产品与039全同字节。所有必要作者测试及独审按README读取，807 BLOCK和全部失败保持原归属；文档或快进不重复运行相同产品字节的测试。

普通fetch确认远端dev仍为67c6，main仍为 `6f688e4dd80b5c81d41aecde90e360d3629f9c21`；本轮没有main改动。合成测试PG前后0|0|0，普通stop/rm-v后自有容器与卷不存在。

候选原件先按嵌套.gitattributes保持原始字节，随后用verify.py检查全部357冻结文件和241复制原件的工作树及Git index/blob，再普通推送候选。开发分支仅使用普通fetch与ff-only集成，集成后再次核验同一字节和两个白名单；此记录的后续开发文档提交补记实际推送SHA。禁止强推、部署及真实模型调用，LIVE=0和整体未验收边界保留。
