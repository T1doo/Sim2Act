# G0 有界保护程序：构建与纯单元交付，指定环境 BLOCKED

本轮沿用[已独审设计](../g0-fresh-mock-prefix-design-20261020/README.md)，只实现、静态核验和纯保护单元验证。没有启动原Generate/Source/Cold前缀、产品fixture/Worker、真实G0、W5、完整PB、真实模型或业务网络服务；没有建立新业务执行窗口、修改旧库、切换产品解释器、安装依赖、扩大权限或开启SQLite扩展加载。main不改，交付走原开发分支。

**当前不能启动候选窗口。** 指定`.venv`的CPython3.12.14使用built-in `_sqlite3` / SQLite3.53.1，没有模块动态库路径；同一进程也不导出`sqlite3_vfs_find/register/libversion_number`。用另一份SQLite库注册保护不会保护实际产品连接，所以程序明确拒绝，不加载第二份库冒充、不启用`enable_load_extension`。此外本次构建在公开入口和内部child入口均固定为`BLOCKED_BUILD_ONLY`，即使另一个解释器可见API或手工提交grant，也不能启用尚未取得运行资格的分支；解除需要后续代码变更及独审，不能仅靠一份执行grant。实际只读`--describe`退出2，记录`loaded SQLite has no public VFS API; native disk closure BLOCKED`，发生在产品导入、grant消费或运行目录分配之前。[原始回执](blocked-preflight.log)及[实际验证记录](VALIDATION.json)可核。

## 实现与限制

- [g0_guard.py](../../../scripts/diagnostics/g0_guard.py)：6实际exchange/8方法入口双计数，Generate3→Source2→Cold1固定顺序；真实HTTP/DNS/连接及MockModel阻断；原body32768字节上限；不可退还的有界writer；同连接SQL authorizer重新安装使缓存语句重授权，禁止DML/DDL/写PRAGMA/ATTACH及Blob/backup/deserialize/扩展等旁路，保留原rollback；专用BaseException只在原G0拒绝完整展开或完整context成功关闭后抛出，绕过原DomainError失败终态写入，在W5下一句之前停止。
- [g0_prefix.py](../../../scripts/diagnostics/g0_prefix.py)：显式组合原夹具的真实生成、Source、提取、发布/实例、冷Store重开、使用评审/同键重放及首Cold收发。不调用完整PB测试或四损坏副本；原三项合成环境/account evidence/software qualification替换及Mock接线沿用；原审批、鉴权、全扫描、期限、预算、账链、Run/version/fence/用量/原请求响应不改。仅额外追踪客户端以收尾，保存最多一个原诊断对象引用；新增保护有非零开销，不能作历史零扰动性能比较。
- [g0_bounded.py](../../../scripts/diagnostics/g0_bounded.py)：无默认运行行为；只读describe和独立授权精确grant分开。校验原开发分支、干净HEAD、源码/测试输入/依赖元数据及二进制hash；消费一次grant后仅建唯一新目录/单子进程。子入口也先核同SQLite API，再核父启动器/继承管道/原grant/新目录/首批source hash，不能裸命令绕开父监督。父进程以monotonic维护480秒前缀、120秒G0、600秒工作、固定5+5秒TERM/KILL；组归属核验包含SID/PGID/UID/出生tick，leader退出不冒充全组退出，异常清理记UNKNOWN。源码/依赖在child前后及parent清理后复核。
- [g0_vfs.c](../../../scripts/diagnostics/g0_vfs.c)：仅接受同一加载SQLite的Linux unix VFS v3。代理四个精确新文件名，各12MiB；拒绝随机temp/其它库、链接/超限原文件、活handle期间unlink。限制xWrite/xTruncate/xShmMap，禁DB mmap与危险filecontrol旁路；原锁、同步、日志和正常共享内存操作仍委托原VFS，不调整journal_mode或temp_store。故障sticky，下一Mock入口也检查健康度。原生接口不满足即BLOCKED，绝不降成轮询目录大小。

这里是冻结工程代码、单一执行者和已知SQLite/依赖边界内的保护，不能称同账户恶意任意原生代码的通用沙箱。源码/ABI变化、额外文件/SQL或护栏/资源/observer/清理失败均UNKNOWN，不冒充原业务拒绝，不重试补齐。可运行分支尚无产品环境综合资格；独立C代理单元不能替代它。

原异常对象在停止信号cause中保留；有界报告保存最多8个cause/context节点、各最多64个frame元数据，不保存locals/Row/正文。原`_cold_admission_diagnostic`、原命名finite/end/stop及五stage差值不重演、不重读DB填补；早拒绝缺失记NOT_REACHED。原G0结果先保存，再做心跳/客户端/连接清理，独立失败不覆盖前一原件。另记录实际authorizer denial计数；`w5_entries`明确标注为控制流静态证明，不能冒充运行测量。未完成业务状态保持INTERRUPTED，不补NS_REJECTED/终态、不续跑该库。

## 实际必要验证

原始日志由subprocess直接捕获，argv、返回码、耗时和源码/原生单元库hash见[VALIDATION.json](VALIDATION.json)。

| 验证 | 实际结果 |
| --- | --- |
| `ruff check`四Python文件 | 通过，exit0；[日志](ruff.log) |
| C代理独立编译，`cc -shared -fPIC -O2 -Wall -Wextra -Werror -Wno-misleading-indentation -pthread` | 通过，exit0；[日志](compile.log)；二进制只在`/tmp/sim2act-g0-protection-unit-build/g0_vfs.so`，不作为产品依赖替换 |
| `unittest discover -s scripts/diagnostics -p test_g0_guard.py -v` | **22 passed**，无skip；[原始日志](pure-units.log) |
| 指定解释器只读describe | **预期BLOCKED，exit2**，没有前缀/产品导入/运行目录 |

22项覆盖：6/8计数关闭和乱序拒绝、不可重置期限、输出预扣及short write、同字节warm-cache UPDATE/CTE/直接DBAPI拒写和rollback、非SQL写API/URI/alias/ATTACH旁路、原异常完整展开/成功完整context结束才停、非DomainError/护栏拒绝不改业务分类、异常cause/context/原diag保全、精确grant过期/源差异拒绝、裸child拒绝、单一dummy进程组清理及leader已退仍检查组、网络/model handler执行前阻断、指定解释器原生API缺失前置拒绝。

其中4个native单元只使用同机已有`/usr/bin/python3` **3.13.5 / 动态SQLite3.46.1**，在独立纯单元临时目录验证：原生正常rollback/WAL双连接、未知路径拒绝、12MiB截断/写入硬限与sticky拒后续open、symlink不触碰原件，以及Python/SQLite入口组合保护。它们不导入产品，不读旧库，不是把指定业务运行环境换成3.13，也不证明内嵌SQLite3.53.1可接入。

指定3.12上的其它单元只使用新`:memory:`数据库、函数替身和一个可回收的无网络dummy子进程；每项核无`sim2act`模块导入。本轮实际业务Mock生产收发、真实G0、产品DB打开和执行窗口均为0。此前单元曾暴露内嵌SQLite假设和未初始化alias连接收尾问题，已改为前置BLOCKED、受保护alias接线、异常路径UNKNOWN；当前22项结果是修正后原件，没有把失败轮算作通过。

## 一次候选执行的精确范围（尚不能批准启动）

| 条目 | 唯一候选范围 |
| --- | --- |
| 路径 | 原本地合成Generate3→Source2→真实提取/发布/实例→Cold首响应1→首次原G0 |
| 收发/停止 | 最多6实际Mock、8方法入口；进入G0后sender永久0；首原拒绝完成展开或完整G0结束立即停于W5之前；无Cold2/W5/G1/finalguard |
| 时间 | 原TTL1800、Run300、lease30、RPM60及完整7槽合同不变；外层480前缀/120G0/600工作+5TERM+5KILL，总候选上限610秒，不续原期限 |
| 输出 | 新目录四DB族文件各12MiB；wire2MiB、artifact2MiB、元数据8MiB、诊断256KiB、控制64KiB、stdout+stderr2MiB、receipt1MiB；总预留63.3125MiB，小于64MiB；不删原件腾空间、不备份旧库 |
| 环境/费用 | 唯一新目录/单自有进程组，原三项合成替换及原Mock接线；真实模型/网络服务/新费用/新凭据/权限扩大均0；不恢复旧PB/JS窗口 |
| 证据 | 原六次接收/账链/批准原字节在新库保留；首末源码/依赖hash、实际计数、原诊断及异常图、清理/文件hash receipt；资源/关键证据/清理失败UNKNOWN，无重试/续跑 |

运行分支的其余未证条件详见[冻结独审](BUILD-ACK.md)：完整VFS/活inode/共享内存及所有writer闭合、原生ABI与指定解释器组合、源码/依赖新增删除与HEAD连续性、FD/stat/hash异常下回执保全、完整600+10秒退出链，以及须独立授权才能核实的实际业务context/五函数identity/heartbeat/第二commit。当前纯单元没有证明完整产品64MiB和610秒全链。

当前最小剩余条件是**指定解释器能公开同一实际SQLite的VFS接口，并在该解释器上补齐上述保护组合复核及独审**；在现有约束内目前没有可启动路径。此次没有更改解释器、安装另一SQLite、开启扩展加载或扩大权限。这个条件未满足前，不请求业务执行窗口；满足后仍需用户另行明确上述一次窗口与原三项合成替换，原完整PB/JS授权不可复用。G0真实拒绝根因依旧未验证，本交付也不代表完整PB或真实生产资格通过。

官方依据：[SQLite authorizer](https://www.sqlite.org/c3ref/set_authorizer.html)限定SQL准备/重准备阶段；[临时文件](https://www.sqlite.org/tempfiles.html)说明原生临时文件不能靠Python open白名单封闭；[VFS](https://www.sqlite.org/c3ref/vfs.html)、[I/O methods](https://www.sqlite.org/c3ref/io_methods.html)提供原生边界ABI。线程等待与单文件限额的官方语义见前一设计。
