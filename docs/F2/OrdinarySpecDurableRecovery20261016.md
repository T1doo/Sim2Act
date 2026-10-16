2026-10-16 普通规范应用的跨页面原请求恢复。

产品实现提交 `2361e0c5fc218767a6ae14d9d1d5feaac3eb6801`，基于父级已验 `2ebc7d27af8f2032cf831bd5446987437d6b4bfb`。范围为原有 MODEL_SPEC_CHECKLIST 的 spec-run-requests 路径；没有扩展其他执行器、Trial 资格或人工语义验收。

在当前身份已获准读取实例之后，才按 principal/project/app/instance 的稳定范围读 localStorage。POST 前必须成功保存并读回白名单恢复记录。实际记录只有 namespace、principal_id、project_id、app_id、instance_id、release_id、expected_revision、expected_release_fingerprint、request_key 九个字段；可选 owner-goal 仅允许指纹字段。input 在该协议中固定为空对象，不存令牌、材料、完整 Goal、模型响应或任意正文。可选指纹的原 DTO 返回及前端请求哈希补齐，但普通 spec 与 owner-goal 组合没有实际 Worker 验收。

同源合作文档使用同一范围的 Web Lock，覆盖读取/保存意图、首次 POST、GET 核对与比较删除。ifAvailable 模式在繁忙时立即拒绝，不排队生成新意图；获得锁后的第一步重验身份和视图代际。缺少 Web Locks、存储失败、坏记录均停止提交。已有持久意图只用原键 GET；404、OUTCOME_UNKNOWN 或其他未知读取不会清记录、自动 POST 或超时新建。只有完整原回执严格匹配（或当前严格未受理证明）才在同锁、同身份和视图下比较删除原记录。迟到回复不能清除别的意图或恢复别的身份内容。切换身份按钮清除页面令牌和视图，保留各自的非敏感恢复记录。

冻结产品主验证在 2361 完成：2 PASS、0 FAIL、0 ERROR、0 SKIP、1 deselected，206.383 秒。协议故障用例有 23 项检查，含跨文档未知结果、缺锁、拒绝存储、配额失败、损坏记录、身份/项目/实例隔离、迟到 POST、竞争成功清记录和通知延迟。真实回环 HTTP 用例有 33 项页面检查：3 个独立 JSDOM 文档、63 次实际资产加载并逐字节对照，Source 被真正受理 202 后控制性丢回执；实际独立 Worker 保存 Source，本轮 API/Worker 停止且后端以新 PID 重启；新 DOM 从恢复存储取原键。第一次成功 GET 在身份切换后迟到，不能绘制或删除；重新登录原身份后第二次 GET 找回同一 Run/AppRun。Cold 独立绑定新材料并保存，Source 两个 VERIFIED Attempt 和实例结果历史保持。两次业务运行各一次 POST，显式 mock 调用为生成/Source/Cold 3/2/2。六个自有进程均结束，清理回执 PASS。520 文件在主验证前后与 2361 Git 字节一致。

JSDOM 使用显式 Storage/Web Locks 测试平台适配，文档间只共享浏览器平台存储和互斥能力，不注入产品 pending Map；存储同时落在本轮文件。它证明新文档恢复，不能冒称原生浏览器、浏览器进程重启或设备关闭重开验收。页面 interval 在夹具中关闭，所有恢复/刷新来自显式动作。前端互斥约束实现新协议的合作文档，不能约束仍运行旧版 2ebc JavaScript 的未刷新标签页；没有新增服务端意图 fence。

失败历史保留：最初协议 JavaScript 18 检查已过，但 Python 写成至少 20，造成 1 FAIL；原测试文件与 XML/日志保留。初版排队 Web Lock 存在成功后重发窗口：同步 storage 通知的首个探测 PASS 掩盖了它；不投递通知的实际反例两方 fulfilled、POST 增量 2，真实失败原件保留。改为 ifAvailable 后，同一竞争第一个成功、另一个 BUSY，只有 1 POST，且验证第一个确已删除其记录。开发主流程另一次 1 PASS/224.13 秒带该已知竞争阻断，不计最终验收。

补充旧 UI 首轮 2 FAIL/121.834 秒也保留：自然规范用例在进入回执污染分支前被旧 owner 文案断言挡住；确定性用例 Node 22 检查已过，但 Python 资产魔数 20 不符实际 21。owner-review.js 对 2ebc 原字节未变，旧版本已经要求先选具体成功结果。仅在 `1d708c38fedb1efdaa871a92e4a0e60832edd0b0` 修三个旧测试文件，检查先选择具体成功结果、两个签收按钮禁用且不自动读 owner API；资产集合由真实 HTML 推导，仍核每个源码哈希。src/pyproject 及主验证实际执行文件对 2361 完全相同。主验证的完整 520 清单与新 HEAD 有这三个仅旧回归测试文件差异，不能宣称整份清单等于新 HEAD；各轮冻结清单分别保留。

Windows、PostgreSQL、原生浏览器、真实模型、人工语义、Trial、新资格证明、完整 P-A/P-B 套件、远端 CI：NOT RUN。三个资格保护文件以及原 WIP HEAD/两个原件 SHA256 均按既有值核对，未改动。未配置凭据、新增费用、扩大安全权限、部署、强推或改 main/core。所有临时数据只在本轮独立 SQLite/进程；归档逐成员核对后才移除本轮已终止的临时目录，不碰旧封存证据。

旧 UI 修正后在 1d708 精确提交另以新目录/SQLite 通过 2 PASS、0 FAIL/ERROR/SKIP，210.210 秒；自然规范回执污染分支确实到达，35 项页面检查，确定性用例 22 项，分别精确核 21 个资产。全 520 文件执行前后保持 1d708 字节；SOURCE_MATRIX 明列与主验证 2361 唯一三个旧测试差异。最终共四个独立 pytest 用例通过，分两轮而非单轮或同一完整源码清单。

[最终独审](../evidence/ordinary-spec-durable-recovery-20261016/FINAL_REVIEW.md)已有限签收。主验证[原始XML](../evidence/ordinary-spec-durable-recovery-20261016/final.xml)与补充回归[原始XML](../evidence/ordinary-spec-durable-recovery-20261016/selected-ui-fixed.xml)，以及[源码矩阵](../evidence/ordinary-spec-durable-recovery-20261016/SOURCE_MATRIX.json)分别保留。

完整包 2269136 字节、90 个外层成员，SHA256 `6b96a866ce5ecdf058c7715f177a96124a988136c17a810c431be009f9109429`。Library原件 `libfile_003840ef25dc8191801773a72c871a71`；[包索引](../evidence/ordinary-spec-durable-recovery-20261016/COMPLETE_BUNDLE_INDEX.json)。完整包、独立索引、两份最终XML、两份失败XML与真实竞争失败日志共7份原件单独上传，全部成功、零warnings；[逐原件ID和内容SHA](../evidence/ordinary-spec-durable-recovery-20261016/LIBRARY_ORIGINALS.json)。返回的Library版本xattr已写入对应本地原件，内容哈希不变。

当前本地完整包：`/tmp/ordinary-spec-durable-recovery-complete-20261016.tar.xz`。已在逐成员核对、独审读取完成且 Library 上传成功后，合并本轮重复临时副本；全部原始字节仍在该完整包和 Library 原件内，旧封存目录未动。
