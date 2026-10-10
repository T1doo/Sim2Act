# 有限证据：native剩余11入口与历史PG两节点

最终源码180a4710405b9c06d1e7cc7213b3ffd073d05567，363冻结文件，69产品文件逐字节等于47388f573746daa27f8d5790ca358eef91378ad5。

- `author/`：作者固定入口测试、20PASS及保留的错误测试预期日志、三个源码冻结。早期collection/collect-only不是测试通过，按对应源码/阶段读取。
- `independent-d49-BLOCK/`：原55文件白名单及原独审BLOCK，未单独推送/触发native。
- `independent-5385-BLOCK/`：原64文件白名单及原独审BLOCK，未单独推送/触发native。
- `independent-180a-LIMITED_PASS/`：原83文件白名单，17实际Report CLI+2旧源码敏感性+3Recorder接线检查，不能替代实际Windows测试。
- `historical-pg/`：作者原same-checks页面/原resources-history各一次真实PG执行，2PASS/0SKIP；被动计数、metadata及0|0|0/容器卷清理结果。根因仍OPEN。
- `native/`：唯一180a run38031437108/job114153034590/attempt1终态SUCCESS，11PASS/0SKIP/33phase/2250fullcollection/2239explicitdeselected；实际Edge结果与6截图共9个chunk/hash验证文件，job359s/Edge141s，非完整验收。

各子目录COPY_WHITELIST以私有原件逐字节复制，名单本身另保留。私有venv、npm modules/cache、临时数据库目录、旧工作区、完整临时PG服务器日志/fixture配置未公开复制。native完整decoded UTF8/CRLF日志4,797,111字节及JSON transport私下保全，SHA5d4dc70dbeebccd4e704f3fe65c366f99221691b9878fad6fa6449a0cf37ecd5。公开excerpt明确为LF行摘录，不冒充完整原件。浏览器原JSON/PNG字节保持，原visualReview NOT_REVIEWED保留；作者有限末态截图观察另存，不晋升Win11/semantic/owner验收。原26结果分次来自旧run15和新run11，不是单run26通过。

对应[执行说明](../../F2/NativeRemaining11Execution20261010.md)。全套预算端到端900s，无多个900s作业或隐藏未执行。全套NOT_ACCEPTED；Report idle6/PG Future10 OPEN；HTTP200损坏响应提示边界保留；Windows900/Edge240/Node150未验收；PROJECT PENDING/BLOCKED_PARTIAL，LIVE0/真实模型0。
