# F2-T07 有限项目列修改与受影响应用重验

从原 origin/dev/csv-two-sum-instances-20261011 = 3e890e329332d434e8f3aa245cb15f905bb41455 接续，开发分支 dev/project-column-revalidation-20261011。完整产品合同见 [ProjectColumnPatches20261011.md](../../F2/ProjectColumnPatches20261011.md)，单一写入者及远端/祖先核对见 git-before.json。main、core dev/f1-foundation、原 CSV 分支不更新。

## 本轮真实范围

至多 16 个已有 canonical 固定 CSV 单求和草案，全部项目成员可信图完整读取。以指定 CSV 材料定义所有应变应用，只修改其 sum 列绑定及确定性下游的不可变草案 overlay；稳定节点 ID、无关节点、不同材料应用和其人工锁保持。额外 UNKNOWN、PROJECT、SEMANTIC、MODEL_CANDIDATE、非 CSV 成员或应变人工锁均拒绝，既有精确 APP 语义免责声明仍为 UNKNOWN。

每个应变应用实际接受旧列/新列两组原 DAG worker（read→sum→deterministic report），再以既有独立 Fraction oracle 验证来源/行数/求和和 worker 输出。合成例两个共享源应用得到 amount=30、quantity=15；第三无关应用和 VIEW 人工锁保留。冻结项目、身份、对象/授权/来源/锁版本、具体批准和预算，排队/最后提交重验，全组事务保存 receipt+seal。零模型请求、零业务数据写入，不改 canonical manifest/资源/内部版本/发布指针。

页面保存预览、精确确认排队、读取实际结果、再次确认保存整组草案候选。未知结果保留首次 body/key，恢复只 GET 原键；迟到响应和不同定义无法更新当前上下文。首次明确事务拒绝可以改正输入。

## 最终证据

最终冻结关联测试：SQLite 608 PASS、9 SKIP、0 FAIL/ERROR，另 2 deselected，1051.30 秒；新增切片 42 后端 + 4 进程内 HTTP/JSDOM 例全部通过，页面共 62 检查。9 SKIP 均需独立 PostgreSQL/CRUD 角色，2 deselected 均为真实旧源码升级。原 JUnit/日志见 final-frozen.xml / final-frozen.log；实际计数、跳过原因见 validation.json。freeze.json / freeze-after.json 八文件前后 SHA 一致。新增专项包括实际坏求和/真实取消/原始锁 ABA/末尾撤权与期限回滚/跨身份或错项目零 protected ledger 读取。

独审 [FINAL_REVIEW.md](independent/FINAL_REVIEW.md)：LIMITED PASS，后端 11 PASS、离线页面 12 PASS，最后 0 FAIL、0 SKIP。独立脚本、实际哈希、原产品失败和修复后的实证全部保留，未复制 fixture SQLite 数据库。[原失败历史](failure-history.md)区分作者夹具失败、产品漏洞与中途结果。

最终 Ruff 新增 Python/测试 PASS；全树 Ruff 10 项、mypy 5 项既有基线错误逐诊断匹配原 3e890e3，没有新增。详见 static-comparison.json 和各原始 log。Node 产品及测试脚本语法 PASS。复现命令为 reproduce.sh。

## 未执行及验收限制

PostgreSQL/最小 CRUD 角色、Windows、原生浏览器/视觉、真实旧源码升级、完整 P-A/P-B、人工语义/owner、真实模型/付费 API、部署：NOT RUN。只使用 SQLite、原实际 worker、进程内 HTTP/TestClient 与离线 JSDOM 的 IPC，不重试已知拒绝浏览器路径。

没有重写执行器，不关闭原 column_patches 对 PROJECT 依赖的保守拒绝。最后状态 CHECKED_PROJECT_CANDIDATE / finite_revalidation_completed 只认本有限合同，canonical_patch_executed=false、publishable=false、semantic_status=UNKNOWN、owner_acceptance=PENDING。F2-T07 总体验收及 R0/正式发布仍未完成。

本开发分支不在原 Windows push workflow 的分支范围，未派发/改动 CI；精确提交 CI 查询另列实际返回，不称远端 CI 绿。
