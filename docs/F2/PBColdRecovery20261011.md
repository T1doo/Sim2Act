# 有限文本提取的跨页面原请求恢复

基线 d5b3f47dbb14ce7d11e822b1ce37cac02e3eb408，继续当前 dev/pb-text-extraction-20261011。依据原 F2-T09、AT-05/18 与 V5 产品 §5.6/6.4/8.3。root 唯一产品作者，既有独审只读；本合同不扩展算子、来源退休、真实模型或发布。

只扩展已登记的有限文本成功 AppRun 提取。新增受保护服务端请求 journal，持久化主体/项目/源应用/实例/Run、原 key、完整请求指纹、前序 key、单调序列和状态历史。正文及名称仅在服务端保存；浏览器不新增 localStorage/sessionStorage/IndexedDB、URL正文或秘密持久存储。先持久准备请求，再执行原提取事务；候选、task_extractions 回执与 COMMITTED 状态在同一事务提交。裸新文本提取不得绕过准备记录，CSV 合同不变。

冷页面只 GET 发现服务端最小索引，再由原 key GET 读取当前授权后的冻结请求并核对既有 extraction-receipts；不得自动 POST prepare/extract 重放。当前主体/项目、源版本与证明、目标指纹和权限、候选真实 hash、完整原 key 请求与已有 app/回执必须全部匹配才安装；技术结果仍 UNKNOWN，新 owner PENDING、正式发布 false。

PREPARED 没有提交回执不等于安全失败。继续阻止重复安装及普通保存，保留原 key。用户明确结束未受理请求时，服务端只取归属与 journal 元数据，在同项目锁事务检查真实 task_extractions：已提交只返 COMMITTED；否则追加 CLOSED 墓碑，拒绝迟到原 key 提取。该关闭控制可以在材料撤权后执行，不读取旧请求正文或完整 Run 私有内容。

明确的新请求先核对/关闭前序请求。COMMITTED 必须重新 GET 核验当前候选，不能冒称服务端知道浏览器已经安装；PREPARED 必须显式关闭。新 prepare 的 expected_latest_key 与前序候选指纹在事务内 CAS，拒绝迟到旧准备、并发新意图和跨页 ABA。同 key 不同请求指纹冲突；取消选择、撤权、版本变化与编辑撤销后的迟到 UI 响应不接管选择或焦点。

旧已提交 task_extractions 保持原 key GET 仅读兼容，不自动制造 journal 或更改旧来源历史。新协议后的冷恢复以实际 SQLite、独立新页面/新 Node 进程、真实进程内 HTTP 资源/API 和冷正常 Worker 验证。未跑 PG、Windows、原生浏览器、旧源码升级、真实模型/人工语义、完整 P-A/P-B/AT-05/18 或部署即 NOT RUN；不能以本有限工程签完整原方案。

新增表 registered_extraction_requests 仅由既有迁移命令 `python -m sim2act.cli migrate` 显式创建；API/worker 不隐式建表。本轮不配置凭据或权限，不在生产数据库执行迁移。新文本裸 extract 必须已有准备记录；旧已提交原 key 不能回填伪造 PREPARED，保留原 GET 回执兼容。源主体/项目与绑定在读取完整 Run 或 journal 正文前核验；目标当前授权先于正文 SELECT。服务端恢复 GET 返回 Cache-Control:no-store，恢复 fetch 指定 no-store；原生浏览器缓存实现未验。

项目 metadata 索引在返回任何恢复项前以真实 Run→AppRun→Release/Instance 元数据核对身份/项目/instance/source-app，不能信任 journal 自述。页面打开源应用前另取 source-scoped 索引对账；候选 hash 校验后、安装前最后一次原 key GET 使用 require_latest，在同项目事务核验当前授权、来源、最新 COMMITTED 与真实 app/指纹。普通历史 GET 保留已提交旧回执；最新请求资格不等于历史被删除。

候选与请求hash必须在最后require_latest GET之前完成；最后回执返回后同步核对，不再await自身WebCrypto hash。维护实际并发probe以另一个同owner会话prepare新key201，再由原key final GET409阻止旧应用安装。网络GET与浏览器安装不组成跨设备原子事务，不将瞬时查询签为此类保证。

预算为每项目最多64个持久来源Run、每来源最多64个请求历史。新来源的首prepare在同项目事务锁内检查项目发现预算，拒绝任何使来源数超过64的写入，确保所有已受理身份仍可由metadata索引发现。已有来源在单来源预算内可明确CLOSE/新请求，CLOSED历史不删除以腾空预算；超额拒绝不修改任何对象。


2026-10-12 证据边界纠正：e2b856最终作者与独审late-latest-digest原trace均latest_reads=0，只有一次require_latest409，未证明已到候选安装阶段。撤回其对原安装异步窗口已精准动态复验的具体推论；当前JS的先hash、最后GET、同步校验顺序可见，不直接认定产品漏洞仍在。原492分母及其他授权路径仍在父级独审，不由本跟进改签；旧红绿/原trace全部保留。必须取得首require_latest200→精确安装候选GET/真实hash→并发prepare201→最后require_latest409、前端零POST且不安装，并用同一probe对照旧源失败/当前通过，才恢复该具体资格。当前精确委派遇平台风险筛查拒绝，已停止且未换名/代理/工具/环境重试，独审与动态probe尚未运行；可审纠正和完整错误见[新目录](../evidence/pb-exact-install-window-20261012/README.md)。

2026-10-12 用户后续明确取消被拒的精确旧/新候选安装竞态对照：该具体资格永久NOT_VERIFIED，不再等待解除或改换代理/工具/框架重做。原拒绝、trace与未提交纠正保留，取消回执见[记录](../evidence/pb-exact-install-window-20261012/cancellation-20261012.json)。主线转入独立F2-T03文本无旧内容逻辑复用，不以新功能测试替代此项。
