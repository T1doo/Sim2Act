# fc69只读serve最终补充独审

来源执行源fc69c863f57f0cdf9a8dbfeaeb5fdc567e42c675。仅只读核原件和数据库文件SHA，没有启动Worker/业务/服务器、没有发送HTTP、没有操作进程或重试受拒/proc路径。

结论：直接CLI的只读HTTP可用性与自有进程最终停止有支持证据；**两次外部启动探针仍FAIL，TTY包装进程exit1，真实server子进程退出码UNAVAILABLE，不能签成serve exit0或把两FAIL改绿。**这不改变prepare-pa/v1v2和冷读的各自实际PASS，也不解释旧0f最初异常。

只读原件/workspace/pa-use-running-clean-install/serve-direct-http.json、serve-direct-session.json、import-timing.json及两次serve日志，彼此一致：

1. serve-smoke.log与serve-retry-smoke.log均RuntimeError: Owned serve startup failed；对应serve.log/serve-retry.log均停在依赖/Pydantic导入并留下探针自有SIGINT的KeyboardInterrupt。原15秒外部窗口两次FAIL单列保留；没有进入API/Worker，不能叫自然业务失败。第二次为串行一次安全重试；未为其改变业务预算或产品lease。
2. 单独只读import exit0，模块wall1.274221秒/CPU1.229547秒，总wall1.536399秒；无app/Store/Worker/model运行。该独立成功不能证明或覆盖前两次启动窗口通过，不用于承诺一般启动延迟。
3. 直接CLI TTY session10136启动普通只读loopback服务（127.0.0.1:53295），8次GET200：首页、app.js/use.js、projects、metadata应用目录、CSV结果、同一PA实例v1/v2各自Run人工入口。目录NATURAL_PA，两个结果version[1,2]；POST /api/projects返回405，Worker/真实模型请求0，native browser仍NOT_RUN。
4. HTTP前后及最终停止后的DB SHA全部32126639abe886f5e3b2f2af1cb76b0365c00890c9a7bbf71fcef18626ac3780；审查者当前读取实际DB文件hash也相同。
5. 向TTY发送Ctrl+C只得到包装进程报告exit1，真实子进程30182仍活。这不是正常子进程exit0证据。/proc/30182/cwd读取EACCES被拒，原件明确未重试/未升级；本审查者亦未访问该路径。
6. 根记录用ps精确已知argv与Fri Oct16 20:45:38启动时间核其自有子进程，经pidfd SIGINT停止；pidfd观测退出、端口关闭、DB不变。因它已非执行包装器可reap的child，无法获得真实exitcode。只签“进程退出及端口关闭已观测”，不猜0或其他数值，不把包装进程exit1当server最终退出码。

serve-direct-session.json明确是“Transcribed from tool outputs; not a process log”；本报告保留这一证据类型，不冒称它是原始进程stdout日志。HTTP与清理结论来自这些原回执的一致性核对，审查者没有独立再次启动或停止服务。

独立proof：/tmp/f2-pa-service-fc69-serve-final-independent-proof.json，含8原件SHA256、HTTP/停止/拒绝/未知退出码边界和实际DB hash。

本轮完整范围仍只签合成mock PA第一次新材料base0→v1、同实例base1→v2、保留旧成果、独立冷读，以及脚本普通服务生命周期合同；实际4Run均单claim/fence1，没有自然重领。旧0f FAIL/最初异常未知、旧F9时序未复现均保持；既往45P1F/定向2P/独立9P不合并全绿。真实模型、Windows、PG、真实场景/语义/人工验收、原生浏览器、CI和部署均NOT_RUN。
