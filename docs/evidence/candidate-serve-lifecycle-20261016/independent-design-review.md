# 8875候选serve完整启停：只读设计审查

基线8875c225561e23d432934599531bbd3e740daa3a；候选执行源fc69c863f57f0cdf9a8dbfeaeb5fdc567e42c675。仅只读源码/既有会话原件，不改仓库，不启动进程、Worker/业务、自然Run、模型、锁矩阵或未知进程，不访问受拒/proc路径。

建议用原CLI作为完整启停验收主体：Popen([candidate_venv_python, '-u', '-X', 'importtime', 'scripts/local_candidate_demo.py', 'serve', '--data-dir', original_synthetic_path, '--port', '0'], cwd=candidate_root, ...)；不要以runpy(non-main)+手动main作为唯一验收。前者走原if __name__=='__main__':main入口，后者改变__name__/sys.modules/argv环境，虽未改payload，仍是instrumented bootstrap。若确需子进程精确import-start/completed wall+mono，可另列纯import诊断或bootstrap诊断；不能用它代替原CLI实际Popen.wait退出码。

原serve四行print实际都flush=True，前两次失败原日志停在import被探针SIGINT中断，没有“输出buffer导致失败”的证据。-u只明确诊断I/O配置，不是已定位修复。-X importtime给模块self/cumulative微秒耗时，**没有绝对wall/monotonic事件**；不能把读到某行的时间当精确子进程导入完成时刻。

最小可核时序：parent在Popen前记录wall+monotonic；记录Popen返回及真实child PID；持续drain stdout/stderr，保存原字节日志并给收到的行标parent-receipt时刻（这是观察上界）；记录原CLI URL行收到；只接受http://127.0.0.1:<动态端口>，认证GET /api/projects成功且预期project ID存在才ready。URL行或worker健康值不能代替该身份/数据验证。保留-X importtime原日志，标为导入耗时诊断；若无exact child导入wall时刻就明确没有，不必为取它改变执行链。

保持全程Popen父子持有关系；不经TTY/session shell包装，不丢失reap权。已有8GET（含NATURAL_PA、同实例v1/v2人工入口）+POST405完成后，Popen.send_signal(SIGINT)，wait(timeout=15)取得真实child.returncode；核端口关闭。原serve已在主线程Event.wait捕KeyboardInterrupt，然后loopback finally设server.should_exit/join10秒，最后Store.dispose。此链可由该诊断验证，不要先假定exit0。

startup60秒/shutdown15秒可作为本轮明确外部诊断窗口，不改产品Run/lease/guard或数据库；旧两次15秒FAIL仍保留，新的60秒成功不意味着旧15秒应通过，也不推断普遍启动延迟。stdout/stderr PIPE必须持续读取，避免-X importtime塞满pipe自己造阻塞。HTTP trust_env=False、无重定向，只向已验证loopback origin发送；就绪轮询只查询只读API，不创建业务。

所有失败路径finally只能清理该Popen保留句柄child并reap。若SIGINT15秒内未退出，probe应FAIL并记录超时；可为自有child作有限terminate/kill清理，但清理成功不改签优雅shutdown或exit0。独立记录是否用了fallback、真正返回码/信号和端口状态。未知进程、PID扫描或/proc受拒读取不需要也不允许。

读取现有合成DB前后整文件SHA与全表行快照使用sqlite mode=ro/query_only，不调用Store.initialize或业务POST。最后再次核32126639abe886f5e3b2f2af1cb76b0365c00890c9a7bbf71fcef18626ac3780或精确beforehash一致；归档仅hash/必要摘要，DB不进入候选payload。核候选ZIP/manifest/脚本hash不变，不重打包。

本次目标仅补齐8875候选serve的完整启动→现有数据只读→SIGINT→真实child退出码→端口关闭证据。未执行任何新探针。旧0f最初异常未知、两15秒FAIL、旧TTY包装exit1与childexit未知、旧F9未复现、无自然重领等原事实不改签。Windows/PG/原生浏览器/真实模型及语义等NOT_RUN继续保留。
