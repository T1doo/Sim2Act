# 普通 Goal 事前标准与同 Run 人工签收：有限工程验收

产品源码：`a3a4f4a524a8eb39f14be7109dabfdd475c7d7e3`。来自已接受的 `83d716fcab99cffec99e07c867e6114c64e17f9b`，普通分支 `dev/ordinary-goal-human-review-20261017`；其后仅归档证据和使用说明。最终交付 SHA 以 Git 提交及外部推送核对为准。

[使用说明](../../ordinary-goal-human-review.md)：已有目标卡 → 保存明确标准和材料 → 核对已保存完整版本 → 明确冻结标准并启动新普通 Run → 同 Run 结果读取证据 → 逐项接受/拒绝和理由 → 用户明确提交。人工声明不改变技术 `PARTIAL`、自动 `NOT_RUN`、语义 `UNKNOWN` 或关闭的发布状态。模型没有签收工具，旧 Run 不补签。

## 实际执行

| 批次 | 产品输入 | 唯一节点 | 结果 | JUnit 秒 |
| --- | --- | ---: | --- | ---: |
| 作者正式批次 | 584 个 src/tests/schema/pyproject 文件，前后 SHA256 一致 | 24 | 24 PASS，0失败/错误/跳过 | 370.384 |
| 独立 Git 快照 | 同 SHA 的585输入；额外一项为明确导出的既有 gold fixture，逐项 Git blob/SHA256 匹配，前后不变 | 同24，额外 unique 0 | 24 PASS，0失败/错误/跳过 | 367.820 |

24项 = 13新后端 + 5新完整页面 + 6必要兼容回归。完整节点和实际命令：[作者收集清单](raw/author-meta/final-collected.json)、[执行命令/RC](raw/author-meta/final-execution.json)、[JUnit](raw/author-meta/final-junit.xml)、[原始日志](raw/author-meta/final-pytest.log)；[独审结论](raw/independent-final/review.json)、[独立命令](raw/independent-final/commands.json)、[独立JUnit](raw/independent-final/junit.xml)、[独立原始清单](raw/independent-final/raw-manifest.json)。独审没有自动重跑。

新后端覆盖执行前完整 Goal/非空标准冻结、接受与拒绝的完整有序选择、原 key 幂等与变体拒绝、旧 Run 禁止补签、错误身份、运行中禁止签收、Goal/结果/权限变化、过期、密封损坏、提交前独立重验和事务回滚、并发两声明只能一份成功，以及 SQLite 合成旧表范围的增量建表/旧 Run 不补签。当前项目所有者、Run 创建者和冻结 Goal 所有者必须一致，正文前及最终提交重新核对本人/原运行身份的当前权限和真实读取回执。

5新页面逐条实际服务HTML/CSS/JS、authenticated ASGI和冷 Worker；共121断言、308页面API（291GET/17POST）、115资产响应。每例一个实际 Worker、两次计数 MockModel请求，合计10次，0真实模型。覆盖事前明确提交、同一Run精确结果/人工入口、无默认接受、逐项理由、显式勾选、接受/拒绝和撤回、账号/项目/Run/工作区导航、迟到GET/POST、双击防重复、丢失实际提交回执后的原 key GET恢复、较早回执不得删除较晚意图、撤权后立即清除正文和缓存、历史403后仅元数据 STOP，以及旧元数据控件失效/新控件可用。[页面计数](raw/author-meta/final-new-page-counts.json)，逐次请求和资产哈希在各页 result.json。

6兼容节点：既有保存目标的实际 Worker、既有27断言的受控API/JSDOM组件、既有自然 P-A 接受与 P-B 拒绝、既有通用文本签收、CSV未确认合同工作区返回。旧目标UI组件不是实际ASGI或原生浏览器。没有追加相邻故障矩阵，也未重复之前全部恢复矩阵。此前599源码仍有24个旧节点没有在当前源码复跑，其原有归因保持独立。

作者全批 instrumented MockModel 40次，其中包含上述新页面10次，不能相加；这个计数不包括既有自然/文本回归的离线 MockTransport调用，不能冒称全部模型总量。独审确认5新页面的10次计数，不把作者全批40冒称其独立计数。[计数原件](raw/author-meta/final-mock-boundary.json)。所有模型响应均为合成 Mock/MockTransport，0真实模型。

## 来源、失败原件与保存范围

首个真实缺口红例：产品代码与已接受83d逐字相同，测试提交 `9f295ab4` 的新接口请求实际404。[红例](raw/author-meta/initial-red.log)、[来源](raw/author-meta/initial-red-provenance.json)。开发中的失败和修正过程保留为单独原件，不计正式通过次数；开发重复不增加unique节点。

本目录保存 **286份原始输出**，包括作者开发/正式批次和独立封存输出，原路径、长度、SHA256和压缩方式见 [artifact-map.json](artifact-map.json)。`.db`及大于1MB的输出采用mtime0 gzip，解压后与原始字节一致；其他原件不改换行、不消除尾空白。snapshot和node_modules为可重建输入，不冒充执行输出；精确输入在before/after清单。独立封存69项manifest逐项核验，另manifest与sums共71个原件；[独审封存核对](raw/author-meta/independent-seal-verified.json)。

作者测试期间仅另外编写未跟踪的产品使用说明，故原始 execution 的 worktree_clean=false；584个代码/测试/schema输入前后一致，保留 [解释及实际路径](raw/author-meta/final-worktree-interpretation.json)。最终交付另核干净工作区与远端差异。开工 [checkout/容量/默认Git网络/19受保护远端引用](raw/author-meta/preflight.json) 有实际核对；没有访问或写入旧满盘实例，也没有恢复旧线程未落盘的独审报告。

## 明确未执行

真人签收、真实语义/业务场景、真实模型、PostgreSQL或真实用户历史库迁移、原生浏览器、Windows、远端CI、部署均为 NOT_RUN。SQLite增量建表只是在合成夹具上运行既有初始化命令，不证明PG迁移或真实应用角色权限。自动验收仍NOT_RUN，人工选择全为合成测试模拟；这些结果不是真人签收或生产语义验收。
