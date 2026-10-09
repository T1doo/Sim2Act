# 本轮失败保全与修复归属

所有下列日志按原字节保存，诊断输出中的空白不作格式修整。先前失败不能计为最终通过。

| 原始文件 | 当轮结果 | 解释与后续处理 |
| --- | --- | --- |
| `first.log` / `first.xml` | 17 PASS / 5 FAIL | 新测试 harness 的错误预期（HTTP400嵌套LOCK错误）、Headers调用、源码篡改的VERIFICATION_FAILED、无id的request表与遗漏limits参数；均保留产品拒绝，并修测试调用 |
| `second.log` / `second.xml` | 21 PASS / 3 FAIL | 一项fixture真实Mock交换数为4而非7；两页面暴露历史PROJECT计划失效会清除已验证当前Report图，阻塞解锁。产品只软化Report锁或精确旧project-binding错误，其他失败仍清图 |
| `page-fix.log` / `page-fix.xml` | 3 PASS | 图保留、页面和冷读增量；不代表最终同页解锁或升级全部验证 |
| `upgrade-first.log` / `upgrade-first.xml` | 1 FAIL | 已归档旧源码fixture依赖文档未复制，子进程尚未执行产品测试；补入旧SHA的精确文档路径 |
| `page-upgrade.log` / `page-upgrade.xml` | 3 PASS | 同页锁冲突后解锁新规划和实际afb旧源码升级的增量 |
| `sqlite-collection-error.log` / `.exit` | exit4、零执行 | 选择了不存在的旧晚回执参数名；NOT_RUN，修成实际收集到的参数后运行 |
| `sqlite-frozen.log` / `.xml` | 501源码84项：81 PASS / 1 FAIL / 2 SKIP | 旧CSV-only测试错误假设Report未派生；实际helper已派生，新增支持应为授权只读200。保留客户端身份字段422与表无写入断言，更新该过时预期 |
| `independent/unknown-probe.*`、`independent/js-501/failure.json` | 实质产品FAIL | 规划真实accepted后响应丢失，peer锁定/重派生导致原键重试HTTP400LOCK；501误删既往UNKNOWN。API同键/同body与原sealed计划仍持久保存证明该路径真实存在 |
| `unknown-fix.log` / `.xml` | 3 PASS / 1 FAIL | 最终恢复修复后的normal/ABA和修正旧测试通过；新增unknown-plan已经通过前8项，测试解锁却使用锁前节点revision，服务端正确拒绝VERSION_CONFLICT。改用重派生节点版本 |
| `unknown-cas.log` / `.xml` | 1 PASS | 同一实际HTTP未知规划场景10检查通过：accepted丢响应→peer锁→原key/原body拒绝保留→peer解锁→项目版本变化继续保留UNKNOWN |
| `independent/pytest.log`、`pytest-fixture-fixed.log`、`pytest-old-negative.log` | 独审初始fixture错误/未通过 | 独审自己的fixture递归、logical-key和peer筛选错误按独审REVIEW_501记录修正，不能归为产品通过或作者独立证明 |
| `independent/pytest-old-negative-final.log` / `.xml` | afb原版2个新增入口预期FAIL，15 deselected | HTTP400UNSUPPORTED_CAPABILITY；证明新Report保护入口负对照有敏感性；故意选择的负例不计最终产品失败 |
| `independent/js-final-negative-501.log` / `js-final-negative-501/failure.json` | 同最终独立driver在501预期FAIL | 再次失败于UNKNOWN意图保留；最终a567同driver42检查PASS |

最终两后端矩阵及冻结源码证据另列 README 与 test-summary；这个台账不追认旧失败为通过。Starlette/httpx弃用警告保留，未以警告代替产品失败处理。
