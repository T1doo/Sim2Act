# 完整原生字典投影：一次有界整链复验

验收源码 **72c523608004244d0be94df0ecaf4e4f7f0b00b5**，真实时钟、SQLite3.53.1、7次有限Mock、0次真实模型HTTP。2026-10-28 20:18:29–20:27:37UTC，实际进程退出0，547.751秒；pytest完整原控制器1PASS545.28秒，assert=plain/optimize=0，开始及结束源码均干净且完全相同。先前85835/8e0a通过版和失败证据完整保留，未重复启动测量。

| 实际Cold SQL事务 | 事务终态/秒 | 完整G1/秒 | 事务其余部分/秒 | 距120秒余量 |
| --- | --- | --- | --- | --- |
| 第一次 | COMMITTED / 103.844031 | 完成 / 67.321105 | 36.522926 | 16.155969秒 |
| 第二次 | COMMITTED / 98.382836 | 完成 / 62.073940 | 36.308896 | 21.617164秒 |

“其余部分”含G0及writer进入/退出开销，不能冒称纯G0函数耗时。120秒仍是原显式签署的SQLite合同；本次没有增加它、普通30秒租约或300秒Run预算。旧30秒仍未通过，不能将SQLite合同移植为PG放宽。

生成→Source→明确提取→fresh Cold Store→两次完整G0/五写/G1→最终artifact及typed v1行保存成功，Run为SUCCEEDED/version2，两Cold attempts为VERIFIED，两NS_SETTLED且没有NS_REJECTED。每次Cold仍执行24次原canonical key与392次fresh native完整输入比较，退出清除capsule。`round7-round8-boundaries.json`逐项比较两次原guard及所有G0阶段SQL数量，均与原通过版一致；没有删查询或缓存动态权限/撤权/Run版本/租约结果。

## 修了什么，为什么只做这一处

上一轮第二次事务114.183秒，G1占74.314秒，事务其余部分39.869秒。已有stage计时相互重叠，不能相加后假称精确CPU分摊；例如两轮`graph.commit`合计69.708秒，`post_binding`26.938秒，`proof.check`27.666秒。单独proof输入比较仅1.266秒，继续叠其资格缓存不再是主要方向。

当前局部完整`_base`剖析中，20次调用包含5860次`_trial_pure_mapping`，约0.055秒累计；它对原生字符串键字典也先创建完整tuple(items)，再重复扫描键类型。独立只读审查选择消除这个确定的重复工作。唯一业务变化为7行：原require函数及其code保持原样、输入恰为dict、每个当前键恰为str时，返回原字典。每次都重新完整检查键，不读取/复制值；RowMapping、quoted_name、陌生键或require hook变化仍走原分支。没有新的C代码、Graph/PASS复用、权限接口或超时变化。

同进程9轮交替合成`_base`成本测量：每批60次，原中位0.367629秒，新0.349224秒，8/9批收益，约5.0%。成本实验仅临时交替该私有函数的原/新code；不是完整链验收或资格证明。原件见`base-cost-harness.py`及`base-cost-pair.json`。独立源码审查通过；完整schema、typed/unknown/cycle/原回退/late mutation等定向72PASS，完整callback元数据预检另1PASS。不是全仓测试全部通过。

本次新测量第一事务比原通过版慢9.797秒，第二事务快15.800秒；两事务总和208.230→202.227秒。机器波动和阶段差异存在，**不能将净变化或16秒余量全部归因于7行改动，也不构成生产稳定性保证**。本次按约定只跑一次，没有择优重试。

新增三个被动G1计时目标后，实际两Cold累计：typed参数收集1468次/9.683931秒、typed校验1468次/8.651918秒、`_base`468次/5.611905秒；原`graph.commit`2次/69.450731秒、`post_binding`2次/22.505095秒、receipts6次/15.338757秒、journal_chain12次/6.833248秒、proof.live8次/26.705242秒、proof.check814次/26.824140秒、inputs_current814次/1.240264秒。上述阶段存在包含关系，不得相加。当前重构合成大图局部profile仍以完整native图比较和完整contract投影为主，但它不是实际G1对象，也不能直接折算新整链收益。未据此继续增加未经证明的缓存或新二进制方案。

## 保存及独立重开

新解释器只读SQLite URI、query_only=ON重开，没有启动Worker或新增模型调用。逐项核Run/version、资源存储hash与完整内容SHA、typed v1指向同一资源、两VERIFIED/两SETTLED/无REJECT均通过。DB重开前后SHA相同：`04b09f33bb7f685348c373813bddf72cd311499f1bc1c8b07706ca2fd7fc337d`。artifact为2092 UTF8字节，SHA `4a3db1f48340b25921fdfe094c76173042ecb1600d7f6267d35c8b3815b4bc0a`。每次运行的ID/内容分别验证，不声称与上次artifact逐字节相同。

`round8-originals/manifest.json`保存各原件字节数及SHA；数据库、Mock档案、lease观察、proof和timing均有原件gzip。隐私检查未发现当前配置凭据原值/base64或私钥标记；五个principal均是源码测试常量身份、仅已知合成hash或无token的运行时身份。首次严格扫描把三个无token的运行时身份列为待核，随后对照测试源码逐个确认，未删除或修改数据库。此为有界来源检查，非对任意历史自由文本的全面认证。

实际加载二进制与原通过版相同：LinuxCPython312 `_raw_snapshot` SHA `e494ef17e1b9e96757c3fdcbcacbd6c0c9d9faba8c8f8af0e63b8b96772c6d08`；`_cold_graph_structure` SHA `5982658d5daf172f559a7d2f08c2fbb74a12ab0c029d6960d0b1e34087715587`。正式软件pin为`d612b5c0b6332d07ac8139b4d6932be1570beeb27950d13f7cbfe8aa896efce2`，`_qualified()`正常返回。没有改变UI或Windows宿主，旧EXE不作为新源码验收。

## 保留的真实边界

- 这是合成Mock+SQLite保存工程验收，G0 owned协调器仍显式test-only；不是正式PG/真实Intern整链。既有Intern令牌存在，缺已有应用角色PG连接、结构/权限及固定quota行，以及对应现有principal/project/trial/approval选择。免费授权已有效，无需再次确认费用；未新增凭据、权限、部署或修改main。
- citation PASS、coverage FULL，但semantic UNKNOWN、owner PENDING，未发布，不能据此声称自然语义或owner签收完成。
- 旧15个continuation单测保留为fixture失配债。独审确认其假unit-instance/release/祖先与旧内部次数断言不符合当前完整ColdGraph；仅换Worker、跳eligible、伪Graph、xfail都不算修复。正确修复需复用真实生成/Source/提取/release/instance/PB-use/Cold批准前缀，在Cold尚未claim时克隆，每例由原Worker和有限Mock运行；保留产品完整guard/journal/identity，只在真实阶段注入单一故障且确认命中。不能把RECEIVED DB当可序列化Python continuation重放。
- Windows保持停止，未声称窗口像素/关闭重开/新EXE验收完成。正常dev分支保全；无PR重试、main合并、Release或线上部署。
