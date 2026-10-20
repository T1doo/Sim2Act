# 双求和流程换用另一份既有授权 CSV

本轮补齐原方案已确认的有限缺项：已有 `resource.read → 两个 data.aggregate_csv` 成功内部版本，选择同项目另一份已注册、当前已授权的单 CSV，为两个稳定节点分别指定新数值列，保存独立计划，另行确认执行，再保存新版本与实例。新实例在冷页/冷 Store 上重新执行两个求和，写入本次完整双结果；旧版本、实例、结果及已有权限不被改写。原缺口及计划依据见[入口设计的最后一节](../cold-first-admission-entry-design-20261020/README.md)和[原分阶段计划](../../F1/NextPhasePlan.md)。

起点与远端开发分支均为 `903f86bea6009674722e70f7fd6d92a7c05b9e1f`，分支 `dev/production-trial-stages-20261018`；main 为 `6f688e4dd80b5c81d41aecde90e360d3629f9c21`。产品源码提交 `a2b44ef1b4019dc4ff56a7431960bc002a48c23e`（10 个产品/测试文件）。执行前已核命令、文件/Git/网络、HEAD、远端祖先及唯一写入者。根任务是唯一仓库写入者；独审只读源码和证据，在独立 `/tmp` 保存审查记录，没有执行产品、测试、Worker 或数据库。

## 合同与来源

新 `TwoSumMaterialInput` 使用恰好两个稳定 step id 的 `columns` 映射，与旧标量 `MaterialInput` 严格互斥，禁止混合或多余字段。两节点可以选择同一目标数值列，但保留独立终端结果。新 namespace 为 `internal.csv-two-sum-material-reuse.v1`。旧单列请求字段、值与 canonical fingerprint 合同保留；共享基类改变字段声明顺序，因此不承诺 raw JSON 字段顺序逐字节相同。

源版本仍经真实 `read_release` 和 closed-flow 重建，只允许一次材料转移。双结果 schema 必须精确等于两个完整 aggregate tuple；目标仍经过原严格已注册 CSV schema、实际字节/hash、graph、所属项目、当前授权和冻结预算检查。共享 `target_for_schema` 没有放宽，独立 data-free 逻辑仍不支持双求和。成对 origin/seal 与请求从真实源和目标重建；篡改第二列并同时重签两份 response 也会拒绝。

新版本来源从实际 SUCCEEDED Run、三步 VERIFIED 回执、两个完整 sink 输出核验，保存逐节点 `default_columns` 和嵌套结果 schema。新实例 enqueue、冷读和每步执行继续重建原材料来源链、旧源和新目标当前授权。没有用默认列、identity cache 或实例派生计划替代完整扫描。页面逐节点选择、变列清确认，分别确认保存计划、执行、保存版本与实例；晚到/丢失回执按原完整 intent 与原键恢复。

## 实际验证

全部使用合成数据和本地 SQLite。页面使用真实 loopback HTTP、实际 NoModel Worker 与 jsdom 30.1.2/Node 24.19.0，两次独立页面装载；不是原生浏览器、PG 或 CI 验证。本轮主要不重复计数合计 108 PASS、2 SKIP。最终产品及测试精确字节见 [source-freeze.json](quality/source-freeze.json) 和 `frozen-source/`。

| 批次 | 实际结果 | 原件 |
| --- | --- | --- |
| 冻结源码双求和新材料后端 | 20 PASS，0 SKIP，55.827 秒 | `originals/sim2act-two-sum-material-frozen-20261020.xml` |
| 旧单列新材料、独立逻辑、双求和回归 | 73 PASS，2 SKIP，147.702 秒 | `originals/sim2act-two-sum-material-regressions-20261020.xml` |
| 冻结源码页面回归 | 15 PASS，0 SKIP，269.370 秒 | `originals/sim2act-two-sum-material-ui-frozen-20261020.xml` |
| Ruff、三个 Python 文件 mypy、三个 JS 语法检查、diff whitespace | 全部 exit 0 | [checks.json](quality/checks.json) |

73 项回归在最后一个显式字典类型声明修正前执行；该修正保留运行值，最终 20 项后端重新验证冻结字节。两项 SKIP 的原条件是缺少实际 `50b10417a99a070f6bcd614471cc00ec102b7836` 与 fab14d5 旧源码 archive；不能据此声称旧软件真实迁移通过。最后冻结页面运行期间没有修改产品/测试文件。

后端独立 Fraction oracle 核两个结果各自的 resource/hash/column/count/sum：新 CSV 小数列为 `40.000`、整数列为 `17`，冷实例交换后分别为 `17` 和 `40.000`。验证同键幂等/同键异参、错误节点映射/混合标量/非数值列、错误 hash/跨 owner/撤权零写入、冷实例源与目标授权重验、同列双 sink、origin 双重重签拒绝，以及完成第一个求和后撤销源或目标授权时 `WAITING_RESOURCE`、工具数 2、无部分 typed append。正例逐行保留原 Release/Instance/AppRun/typed 历史，并核 principals/grants/app_drafts/resources 无修改。真实完整 proof 保存在 `originals/frozen-backend/` 的 gzip 原样文件。15 个页面病例的实际请求、检查点、每次装载资产 SHA 和冷实例结果见 `originals/frozen-ui/`。

最终独审代码 ACK 见 [CODE-REVIEW.md](independent-review/CODE-REVIEW.md)；冻结运行原件、780 个页面资产哈希及独立 CSV/Fraction 复核见 [RUNTIME-ACK.md](independent-review/RUNTIME-ACK.md)，结论 ACK、无新阻断。独审发现的新材料页面错误使用旧列白名单，以及新冷 Store 测试遗漏 PG schema 隔离映射，均已修正。后者仅补齐测试隔离，本轮未跑 PG。

## 失败历史与范围

`originals/` 保留本轮所有 JUnit（失败原文与补丁使用 gzip 原样压缩，避免修改其原始空白），包括早期 17 个 fixture 字段读取失败、stale claimed-job 无 result、历史表无 id 的测试假设错误；修正后先 17 PASS，再补三项关键行为并通过 20 PASS。页面失败原件包括未设置既有 jsdom 的 NODE_PATH、小数精确格式断言、旧驱动缺 native `structuredClone`，及在先前运行期间修正类型声明触发的严格 `VERSION_CONFLICT`。该轮已停止，冻结后重跑。mypy 原错误与修正后的通过日志均保留，不将失败或未完成轮次算成通过。

参考 [Pydantic 官方 union 文档](https://pydantic.dev/docs/validation/latest/concepts/unions/)与[严格/额外字段配置文档](https://pydantic.dev/docs/validation/latest/api/pydantic/config/)核对两个互斥输入模型的解析边界；以项目锁定的 Pydantic 2.12.5 实测为准，没有更新依赖。

本轮真实模型调用 0、PB/G0 探针 0；没有恢复旧服务或取消窗口，没有改 lease/TTL/安全门、main、凭据或权限，没有发布/部署。最近一次已封存[完整 Mock PB](../pb-full-current-once-20261020/README.md)仍 FAIL_NOT_ACCEPTED：G0 32.041 秒、首 binding 4.368 秒，期限/stop 复合保护拒绝，失败帧具体最小期限或 stop 条件未知；W5/G1/finalguard 仍 NOT_REACHED。更早的 37.279 秒首绑定及[paired 证据](../pb-cold-envelope-paired-20261020/README.md)各保留其历史结论，不混为本轮数据。本交付只闭合该有限工程缺项，不签收完整 P-A/P-B、真实语义、PG、原生界面或生产验收。
