# Reserve 截止竞态：恢复空间后的离线验收

修复候选冻结首次准入的 execution、Run.created_at+300、原 permit、原 lease 最小截止；实际 quota 操作返回后重新执行完整 admission/fee/Run guard，后续 permit 或续租不能扩大首次截止。quota/ledger 使用同一合法时间记账，写阶段过界也由外层事务完整回滚。原过期精确键继续只读历史、不授权重发。预算、权限、真实模型门及执行器均未扩大或改写。

本次测试 HEAD：`e5344436c67fef6d71a9a4dc54296a3f01f37bd2`。产品源码修复提交：`70e2c7069ed9d3caca94493b39627563be9a5591`；最初发布候选：`fa8487b53771cd20c8158357b619bc7c1fa5b25f`。恢复过程没有修改 src、tests 或 pyproject.toml。

用户明确批准后，仅清理 `/tmp/project-column-baseline/.mypy_cache` 和 `/workspace/Sim2Act-production-gate-author/.mypy_cache`。删除前核对精确路径、CACHEDIR.TAG、JSON/标记文件、非符号链接、单链接及可见进程引用；系统 PID206/257 无法读取且未终止。实际可用空间增加：临时盘53,825,536字节，工作区54,018,048字节。父目录、备用缓存、源码、共享Git、独有成果、失败日志和数据库均保留；工作区6,656字节写入/fsync/读回通过后仅移除本轮自建探针。详见[清理回执](../evidence/pa-trial-reserve-fence-recovered-20261016/cleanup.json)。

空间恢复后只运行一次原相关完整回归：主进程110 PASS/1 deselected，296.00秒；被排除的原始真实RPM=1 cadence用例在独立进程运行一次，1 PASS，361.87秒。合并111个唯一用例，0 FAIL/ERROR/SKIP，整体363.77秒；两进程退出0、无timeout。510份源码/测试/配置前后哈希一致，运行期间HEAD不变、工作区干净。使用原逐例归档hook和导入限制，两进程均无受禁模块导入尝试或加载。这里的“完整”限于已有相关111项选择，不等于全仓或生产验收。

[最终结果](../evidence/pa-trial-reserve-fence-recovered-20261016/RESULT.json)、[主进程原XML](../evidence/pa-trial-reserve-fence-recovered-20261016/final-main.xml)、[真实节奏原XML](../evidence/pa-trial-reserve-fence-recovered-20261016/final-real-cadence.xml)、[源文件前快照](../evidence/pa-trial-reserve-fence-recovered-20261016/source-before.json)、[后快照](../evidence/pa-trial-reserve-fence-recovered-20261016/source-after.json)、[最终独审](../evidence/pa-trial-reserve-fence-recovered-20261016/FINAL_REVIEW.md)。独审核对111个唯一case、111个原case包及223个raw成员、全部容器/文件哈希与源码一致性，限定签收此次离线切片。

已有定向证据只复制发布，没有另行为审查重跑：旧实现8 FAIL/1 PASS；修复后9 PASS加写入边界2 PASS，共11个唯一定向通过。[旧红原XML](../evidence/pa-trial-reserve-fence-recovered-20261016/targeted-red.xml)、[绿原XML](../evidence/pa-trial-reserve-fence-recovered-20261016/targeted-green.xml)、[写入边界原XML](../evidence/pa-trial-reserve-fence-recovered-20261016/targeted-write.xml)。[QUOTA_RACE原件示例](../evidence/pa-trial-reserve-fence-recovered-20261016/QUOTA_RACE.json)、[WRITE_ROLLBACK原件示例](../evidence/pa-trial-reserve-fence-recovered-20261016/WRITE_ROLLBACK.json)明确只是代表例；全8种quota矩阵、两种writer、replay及HTTP/SQLite原件见[索引](../evidence/pa-trial-reserve-fence-recovered-20261016/targeted-index.json)和下述完整包，引用来源见REPRESENTATIVE_REFERENCES.json。

此前两次完整尝试仍为exit120、空XML及F/E输出，历史状态仍未通过；首个F具体原因保持UNKNOWN，不能因本次通过就一并归因磁盘。旧封存236份原文件及manifest逐字节未变。此前合法派生容器转换的raw表示、原container哈希、坏容器原件和恢复说明全部原样保留；本轮没有修改旧封存。旧报告保留原BLOCKED状态，本报告追加新的有范围离线验收，不改写旧历史。

完整原件包包含 previous-sealed-evidence（旧封存全部文件）、targeted-originals（已有XML、22份索引JSON及20原case包）、recovered-run（本次全部命令、stdout/stderr、XML、111原case包、源码快照、回执、审查及封存）。本次111个原case容器本身逐字节保留；旧封存按其既有表示保留，不声称还原此前已转换的历史压缩容器字节。容器内部含实际合成SQLite与TestClient/JSDOM HTTP原文；非虚构HTTP reserve路由，预算使用真实组件。556份regular原文件和54个链接元数据全部校验，内部INTERNAL_MANIFEST.json及外部BUNDLE_CONTENTS.json列出字节数、SHA及链接目标。历史原V1数据库/读回执也保留，未把它冒充完整历史用户升级验收。

[下载完整原件包](../evidence/pa-trial-reserve-fence-recovered-20261016/complete-originals.tar.xz)：6084768字节，SHA256 `3e3f2fe65ec853f5e6a23d901c6e1f471517a40795cec66b648ddcfae793983c`。另见[原件清单](../evidence/pa-trial-reserve-fence-recovered-20261016/BUNDLE_CONTENTS.json)、[包回执](../evidence/pa-trial-reserve-fence-recovered-20261016/BUNDLE_RECEIPT.json)、[发布文件清单](../evidence/pa-trial-reserve-fence-recovered-20261016/PUBLISHED_MANIFEST.json)。

本次未调用真实模型/付费API、配置凭据、改变网络权限、部署或强推。3/2/2=7、RPM=1、paid=0、Run300秒/lease30秒及所有原有权限保持。Windows、PostgreSQL、原生浏览器、真实provider/费用资格、真实并发性能、真实旧用户升级、完整生产P-A/P-B：NOT RUN/NOT ACCEPTED。不声称远端CI绿。
