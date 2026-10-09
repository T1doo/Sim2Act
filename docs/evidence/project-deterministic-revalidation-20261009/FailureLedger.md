# 保留的失败与阻断

本账目与最终通过矩阵分别记录，先前通过不替代最终冻结测试。
私有完整日志根 `/tmp/sim2act-project-checks-20261009`；独审根
`/tmp/sim2act-project-revalidation-independent-20261009`。

- `first.log`：作者新选择 quantity，但旧 fixture 只有 amount，正确拒绝400。
  修正拥有的fixture为两数值列；产品未放宽输入。
- `extra.log/xml`：新成员Grant改变了旧根图 authority，测试错误使用旧图。
  明确重新派生现有canonical peers后建立新PROJECT计划。
- `underived.log/xml`：测试错误假定create-app响应含runtime_id；改为读取真实app_drafts。
  两次测试失败均保留；权限硬门不绕过。
- `cbdc06135d30d7d8f73d9428b78d88a3590a03b7`：独审首次收集失败，Pydantic2.12
  判别字段kind不允许继承通配mode=before校验。此前作者测试在该最终修改之前，
  不能归属cbdc。修复为实际字符串字段显式名单、排除kind；eafea08重新冻结。
- 独审静态发现已接受POST后GET422可能释放原键，随后实页复现且已修复，见追加最终结果。
  eafea08矩阵只能作为修复前范围记录，不作为最终通过。

初期 Ruff/mypy诊断（unused imports、validated类型、Decimal exponent）已修正；
最终检查另记。旧源码否定、主动注入损坏与权限冲突是预期负例，不能作为产品成功。
任何独审新增阻断和最终矩阵失败须追加具体记录。

长期边界：PG resources-history超时OPEN；HTTP200损坏响应的人类提示限制保留；
Windows900/Edge240/Node150未验收；LIVE=0，semantic UNKNOWN、owner PENDING、
overall NOT_ACCEPTED、PROJECT PENDING/BLOCKED_PARTIAL，正式发布关闭。

追加独立实际API：eafea的escaped JSON kind、extra值/extra键/nested extra键
在错误JSONResponse编码时UnicodeEncodeError。须以根级before model validator
遍历原JSON键和值解决，不能仅避开判别字段冲突。作者独立临时proposal测试
首次5个fixture ERROR（临时路径未加载tests/conftest），-p conftest补齐后
实际负例结果另保留，不能伪记API失败/通过。

修复前完整eafea矩阵自然结束：SQLite49PASS/1SKIP/1FAIL（481.66秒），
PG50PASS/1FAIL（772.15秒），每库51收集。唯一作者FAIL是HTTPX本地编码
Unicode、请求未发到API；不能替代独审另已确认的四种服务器500和GET422缺口。
348字节前后匹配，所有结果以eafea-*保留。临时proposal补加载fixture后
3PASS/2FAIL：真正escaped kind/extra到API后服务器响应编码失败。

修复冻结429a62a418748822d51d9e930ec05f8b560c5ef2：迭代before model validator
在完整原JSON含dict keys/values和list上拦截surrogate；JS区分POST阶段和已接受
后的GET阶段，不释放GET422原键。新增真实escaped JSON与已接受POST201后
GET422恢复、实际极端精度NOT_RUN回归。最终44用例矩阵只重复必要范围，
旧晚回执限定lost_response两phase，不重复修前已有14个参数全组。

执行器连接再次中断后，20:45:40UTC实际只读核验HEAD eafea、348字节、
预期docs-only未跟踪、原matrix自然exit1及无活动作者测试，owned PG容器
ID/owner/network none/状态均匹配，随后才修源并启动最终matrix。
未把丢失的tool wait cell84当作测试失败、未复启动旧任务。

最终作者429矩阵44每库：SQLite43PASS/1SKIP/0FAIL，PG44PASS/0SKIP/0FAIL；
Junit/exit/source-command及新终态mtime已核对。旧eafea退出文件在本轮运行中
直到自然结束才覆盖，未误读旧exit1为当前失败。348前后匹配；scopecheck GET422
与Unicode/精度新回归均通过。本轮没有新增产品失败。

20:57:58UTC只读发现独审目录最后更新20:40，agent实际pending_init。
前述send_message并不证明最终复核已运行；已followup重新触发同一审查者，
作者最终通过不代独立结论，不补写LIMITED_PASS。

独审恢复后最终429实际35 SQLite/API PASS，2真实HTTP/JSDOM页PASS（30checks）；
68产品源before/after gitblob字节匹配。三个独立阻断（import/四Unicode500/
POST201后GET422丢原键）均复验关闭。最终LIMITED_PASS只签独立有限scope，
未运行PG/角色/两连接竞争/旧库升级/native；不代作者或完整验收。
45artifact独立SHA256清单及全部原始失败/最终harness已逐一哈希核对后归档。
