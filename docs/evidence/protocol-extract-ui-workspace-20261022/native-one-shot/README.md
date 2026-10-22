# 单次 GitHub 窗口：checkout 超时，原生 UI 未执行

冻结源码 `3d4313cba1daf716d19ef2b3a7ed39ad0231982f`，独立只读启动限定 ACK 后，一次普通开发分支 push 触发 [run 39738030637](https://github.com/T1doo/Sim2Act/actions/runs/39738030637)，attempt1。结果 **CI failure / 原生 UI NOT_RUN**，不是产品或浏览器通过。

工作预算在07:04:47 UTC第一步开始。checkout 于07:05:47达到自身1分钟上限；原日志显示约48% / 48,479个文件。Python设置与自有受保护Edge启动器都 skipped；原全量 native-mock job同样 skipped。无新 SDK/浏览器安装、API或合成事实副本，无 Source/extract/Worker/Mock/模型；业务GET/完成POST/截图均0。没有自动或手动重跑，没有更换环境或安全设置。

checkout post清理实际success，07:05:50 runner记录 `Cleaning up orphan processes`。这不等同于独立查询所有进程终态；本片自有API/Edge/fixture未创建，故没有其真实退出回执。Windows启动器、sandbox/token审计、实际DOM差分及其资源清理均未获运行证据。既有2项本地定向PASS与此次CI failure分开，不相互替代；本地sandbox阻塞仍保持。

`job.log` 为下载的完整原始job日志，`run.json/jobs.json/watch.log/result.json`保全真实终态，`manifest.json`绑定原件。失败是本片checkout粒度与1分钟上限不匹配，不是访问拒绝或新许可缺失；Node运行时弃用警告不是本次错误原因。没有在窗口中修改冻结源码。

最小剩余技术条件是先闭合运行读取路径，再把窄job checkout限定为这些路径，保留原180+10总预算和所有业务/保护上限。初步tree列举179文件仅覆盖全部src、现有browser-ci包、必要启动/audit脚本、原lock及封存3件，**不是完整白名单证明**；至少还须包含 `.gitattributes`、`protocol_reviews.ASSETS` 固定的 `docs/evidence/protocol-store-loop-20261006/evaluation/{a-source,a-cold,b-source,b-cold}.json` 等真实读取，不可把整个证据树纳入或误用旧materials目录。原fetch本身也约41.4秒，因此不能只归因文件展开；该固定checkout action的sparseCheckout会自动使用blob:none，可减少无关抓取/工作树，但不能保证60秒或原生测试成功。此条件尚未实施/实测，本轮不再开启第二窗口。原产品工作区ABA修复已正常推送，原生验收是独立未闭项。
