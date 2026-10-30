# 本地 SQLite 运行中读取与取消：实际工程修复

验收源码 `706a115412ec820bbf9e7f46dd00d1e19a2a43c7`，开发分支 `dev/cloud-g0-live-20261028`。基线为 `26564f01ed8282a77bbd02cfbd4935942b08ce15`。这是云端Linux、实际文件SQLite、原Worker及真实HTTP验证，模型定义用固定MockTransport，运行期NeverModel，0真实模型调用；没有访问用户电脑、部署、main/Release或第四次Windows CI。前三次job累计394秒，剩506秒保留。

原 `synthetic_workspace.serve` 用一个锁包住整次 `worker.once()`；middleware又在该锁后排队所有HTTP。一次Worker包含多个独立事务及事务外计算，因而状态读取、取消、页面甚至不能在事务间进入。现将该额外互斥缩到 `Store.tx()`：只有明确test-only文件SQLite、固定 `timeout=30` 的本地入口启用FIFO，交易提交/回滚/连接释放后放行下一位。默认Store/PG不启用，BEGIN IMMEDIATE、全部授权/内容/版本/租约校验及原子写集未改变。没有WAL、旧快照、缓存PASS或权限旁路。

排队、连接取得后的检查与BEGIN锁等待使用同一个至多30秒准入预算。该模式pool checkout不再另外等待30秒；连接取得后重新扣时，`_cap_wait`和原PRAGMA恢复保留。失败、真实pool耗尽、嵌套拒绝及BEGIN争用均释放FIFO。HTTP断连不等于取消同步endpoint已排队的交易，不作此承诺。异步422错误处理器的原身份/项目/拒收证明查询改在线程池完成，避免同步等待卡住整个事件循环。

FIFO争用超时有独立精确异常，只有同一test-only SQLite Store的同一gate能被原心跳分类器识别。普通RESOURCE_UNAVAILABLE、不同Store、pool失败及嵌套错误不被算作争用。原续约SQL、fence/截止检查、次数和提交后发布逻辑不变；真实测试确认失败不续租，释放后实际fenced SQL提交才更新lease，未伪造SQLITE_BUSY或续约成功。

## 冻结字节的实际业务时序

`actual-http-timings.json`来自最终冻结回归。没有向业务函数插入延时或暂停，也没有替换业务Run状态。固定SOURCE经原定义/确认/Release/实例链，随后启动原Worker，真实并发HTTP读取、取消、无效输入及health。

| 操作/边界 | 实际结果 |
| --- | --- |
| 第一Run运行中原键GET | 1.257秒，HTTP200，RUNNING |
| 取消命令 | 2.077秒，HTTP200，CANCEL_REQUESTED |
| 第一Run最终状态 | CANCELLED，无SAVE操作、无实例成果版本 |
| 并发health | 0.034秒，HTTP200 |
| 并发422拒收证明 | 1.259秒，VALIDATION_NOT_STARTED，未创建第二Run |
| 第二Run运行中GET | 2.035秒，RUNNING，未等整次Worker结束 |
| 第二Run完整执行 | 5.954秒，SUCCEEDED，成果版本1，重开仍为唯一版本1 |
| 最大单次FIFO准入持有 | 1.952秒；包含连接/BEGIN/完整原校验/提交，是SQL持锁时间上界 |
| 最大FIFO排队 | 1.218秒 |
| 运行中最小观测已提交lease余量 | 24.087秒，原30秒租约 |

以上是完整**本地确定性spec链**及原guard，不是大型Cold图G0/G1计时，不能拿它替换历史114秒量级的Cold结果。未对新源码盲重跑没有修改的Cold大图；其原子交易内仍不可抢占，本轮没有拆短该G0，也没有扩大30/120秒租约或事务期限。

## 回归、重开及源码独审

最终 `final.log/xml`：29项通过、0失败/跳过、77.630秒，覆盖真实并发HTTP/SQLite、FIFO失效清理及真实续约、原请求三次后端进程重开、原结算期限检查与私有writer边界。`actual-process-reopen.json`保留原测试实际三轮同origin、POST数1→0→0及三份clean/worker_stopped/data_preserved退出回执；Storage为明确JSDOM适配器，不能称WebView2实测。

中间三源码版本（资格pin14ae993f…12a4）上，原授权/内容/实例版本/取消前SAVE、入口恢复/CSV导出等额外35项已通过；这不是新增心跳分类后最终源码的整组重跑，不能合并计数宣称最终全过。该批唯一失败是旧终端测试强行覆盖NODE_PATH到上一台机器路径；测试改为继承当前明确配置后，原页面协议全部断言单项通过，见保留日志。新增心跳分类后的最终冻结验证以final29项为准。中间字节摘要保留在pre-heartbeat-frozen-bytes.json。早期PRAGMA测试还误把交易内已经扣预算的值当作原值，现从原连接先取原值后检验恢复；原失败日志保留，不删除断言掩盖问题。单独边界测试中人为持有SQLite交易只用于真实争用/超时清理验证，不作为上述业务时序证据。

独立只读审查通过四个实际源码修改、两份回归及资格更新；记录在 `readonly-review.json`。完整资格仍142份、无增删，只改变api/db/synthetic_workspace/text_workflows四项摘要。新固定pin：`57b692e65b6a9991cd27fde98f546c0c22d00ec519343b0116e4f3cdb32b9a71`；原校验器未削弱，已实际通过。源码/测试/manifest八份冻结摘要、原生Linux二进制身份、环境和结果范围见 `frozen-bytes.json`、`qualification.json`、`source-and-results.json`。

此源码的Windows/Edge/EXE/WebView2未验，不能借用旧9bf版本CI22项通过。正式PG/live配置与业务选择缺项没有被更改、伪造或绕过；仍不宣称大型Cold或整体产品验收完成。
