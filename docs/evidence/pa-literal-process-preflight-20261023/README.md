# 旧红轮进程前置核查：未满足启动条件

核查基线 `ee293fcef903e6e9f399a5c82956e953f9aec7be`。本轮模型请求、信号发送、锁删除均为 0。没有执行新候选窗口或重复旧测试。

## 可追溯的历史范围

原 `red-tests.xml` 的 KeyboardInterrupt 失败节点明确创建 `[sys.executable, "-c", "import time; time.sleep(10)"]`，不是模型、数据库或业务 worker。suite 起点为 `2026-10-23T04:58:06.572893+00:00`。原失败断言是 `child_stopped` 为假；不能靠命令写着 sleep(10)、经过时间、后续 34 PASS 或 Git 干净来追认退出。

原 `/tmp/pytest-of-agent/pytest-14` 及其 `test_supervisor_keyboard_inter0/output/supervisor.json` 均已不存在，XML 没有保存旧 child PID/start identity。因此历史进程身份无法精确追溯，历史终态继续 **NOT_INDEPENDENTLY_VERIFIED**。最终七份清理记录只绑定最终测试调用，不能替代旧原件。

## 当前只读观察

`process-snapshot.json` 保留本次原始结果。扫描按当前 UID 读取 `/proc` 元数据，只计划输出与项目、候选 runner 或上述精确 sleep 命令相关的非敏感身份字段，不输出任意命令行或凭据。扫描在 PID 1 的元数据读取中触发 `PermissionError` 后立即停止，未换工具/路径读取该进程。原记录没有保存失败的具体子路径，不能追加伪造为 stat/cmdline/cwd 中某一个。

**实际完成进程数为 0，扫描不完整。** `old_command_matches=[]` 和其他空列表不是“当前无残留”的证据，当前残留状态仍 UNKNOWN。无权限或进程被拒读不等于它就是旧 child，不能据此终止它。

`collaboration.list_agents` 当时仅本 root 为 running，同树 reviewer 为 completed；这证明本协作树没有第二个运行写入者，不证明整个环境没有其他进程或线程。核查前工作区干净、本地 ahead/behind 0/0，正常 GitHub 分支只读接口返回同一基线 SHA。这些也不能替代 OS 残留检查。

## 当前决定

**不确认新有限窗口可安全启动，本轮不启动。** 尚需在原环境、现有授权的正常只读进程查看范围内获得与精确命令/项目 runner 相关的当前身份及终态快照；若能找回历史 PID/start identity 原件，再单独核历史。不得通过新增安全权限、改 PID 所有权、删锁、杀未知 PID 或换环境补证。历史原件找不回时，只能接受“当前限定范围无残留”的新证据，不能改写历史 UNKNOWN。
