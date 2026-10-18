# 已受理修正来源撤权后的停止入口

从 `fe5d640c29533a68f5af77ddd7e4b8ceba27a98b` 接续。实际链核查发现：新修正 Run 已受理后，若来源权限撤回，新入口先读完整实例会被拒绝并清空选择，因此到不了原有 owner `control-status` 分支。用户无法从这个入口停止已知后台任务。

本片仅改 `internal.js` 与 `owner-review.js`。只有本次明确 `PERMISSION_DENIED`/`GRANT_REVOKED`、同实例及本次读取/失效代次、连接/项目/工作区都匹配时，才转项目页的独立已知 Run 停止面板；原私有应用详情被清除，不恢复 cached instance。版本冲突、内容指纹或网络错误不进入这条分支。

面板复用现有 `/control-status` GET 和 `/commands` cancel(version) POST。响应严格核验 namespace、Run/实例、字段白名单、状态、version、cancel_intent 和 content_access=false。只有明确点击可取消；双击有 busy 门，未知结果仅允许原 Run GET 读取，不自动重发，不提供 resume。账号连接、项目、工作区、人为 Run 选择及面板 DOM 共同隔离迟到回调；离开再返回的旧面板明确禁用并提示失效。没有新 API、executor、Grant、表或安全权限。

实际 TestClient HTTP/完整服务页 JSDOM：**PASS153.797秒，10检查、11手势、43前端请求，输入零漂移**。复制当前任务已合法完成的合成测试库（精确SHA另存），再正常接受并执行一个新原始 Run（普通 Worker一次成功、Mock1），模拟人工REJECT，页面明确创建一个新的 QUEUED correction；经实际授权API撤回唯一已知 owner 材料READ后，入口实例GET403 → owner metadata200 QUEUED/version1 → 明确取消POST200 → metadata200 CANCELLED/version2/cancel_intent=true。修正子 Run `run_e912cc36f5694cb5a8af2b90e782b351` 的模型请求/Attempt为0、typed行不变；之后普通Worker.once未领取任何任务、模型调用0。没有改写原状态、时钟、预算或租约，没有重跑gen3或旧故障矩阵。

实际负例后只增加旧面板失效Observer；逐字剥除这个唯一block可恢复实际执行的internal.js输入SHA，其余处理器字节完全相同。最终合成控制器检查30项PASS；pytest包装1PASS/7.94秒（同一合成病例，不另计30病例）；Node语法/Ruff/源码diff检查通过。实际取消路径未在Observer添加后重跑，Observer自身由最终合成导航检查验证。

[原始证据与有限独审](../evidence/correction-known-stop-20261018/README.md)。实际脚本曾静审提示typed列表无ORDER BY的观察器风险，但本次比较实际通过；不能写成产品或wrapper FAIL。DB仅保留于当前实例，提交为封存非DB原件与完整作者前后JSON导出。

这是已知修正的撤权后停止入口闭合，不签新冷页恢复合同、完整故障矩阵或整体F2。真实模型、真人/语义、原生浏览器、Windows、PG、远端CI均未执行。真实账户source/controller缺口不变，零远端认证重试/推送，未改main/部署/凭据/持久安全配置。
