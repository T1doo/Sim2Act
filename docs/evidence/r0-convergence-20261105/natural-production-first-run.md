# 3ec03e25 正式试验首次实测

原同源桌面运行包SHA256：44fc2b3f9709c9b2b18008d95ca745147dd4962a9e27993e3c71767f3eaa195b。使用新建隔离PG安装及用户已授权的DPAPI模型凭据；未操作窗口。

实际通过：原API/Worker启动；两份不同TXT及完整目标保存；正式P-A V2准备；明确批准；原五字段worker-selection回读；第一次会话正常退出。

带正式选择启动被原软件资格门拒绝，未提交Generate Run、未调用模型。错误为VERSION_CONFLICT / Current production software differs from the reviewed target。测试脚本关闭已退出子进程管道时又触发OSError，导致第二周期退出记录不完整。保留原报告，不把它写成正常退出证据。

随后只读核对：原controller PID78640已不存在，隔离数据目录无postmaster.pid。使用同一包、同一原批准执行原check_selection，复现上述资格错误；检查后数据库停止。没有重新准备、批准或提交。

对包内实际字节与旧清单的审计见production-qualification-delta.json：5个新增模块、8个修改模块、0删除。旧清单baseline仍为206153da。不能通过删除_qualified、跳过指纹、把当前哈希写回并沿用旧审阅身份制造通过；下一步须审阅变更、执行相关资格回归并建立明确的新版本审阅清单，保留旧资格及失败证据。新代码资格变化后，已有冻结试验不应自动改绑新软件。

原始记录：managed-natural-production-check.json、natural-selection-preflight.json。本轮证明正式准备/批准可用及资格门拒绝行为，不能证明完整生成或P-A/P-B通过。
