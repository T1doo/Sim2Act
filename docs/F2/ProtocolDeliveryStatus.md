# 协议工程发布状态（2026-10-06）

已发布到既有 dev/f1-foundation 的实现源码为 `0389c871443e5fccb4920427fd4ba93bb3ff650e`。唯一标准 Windows Server CI37533601563 SUCCESS，895PASS/5SKIP；原生 Edge protocol26检查与截图像素审查完成，详见[终态证据](../evidence/windows-protocol-native-0389-20261006/README.md)。Windows workflow实际15分钟，未改为25；无新增权限或真实模型请求。

本次仅把Windows证据文档移到0389之上。原证据提交b9bb8e3的祖先包含尚未发布的production activation68443，因此不能推其整条祖先链；当前文档分支不包含68443，src/scripts/tests/workflow与0389保持精确一致。独立本地activation实现及其947项回归不能视为已发布或被本次Windows CI验证。

真实LIVE额度仍0；production activation及其Windows owner-private ACL/原生worker权限检查 NOT_RUN。原生协议检查是离线Mock/SQLite浏览器fixture，不证明真实书生语义、production activation或全部PG浏览器路径。完整P-B、F1正式签收、完整AT02、Win11及物理移动验收未完成；旧失败37526795142保留。本次纯文档同步不追加手动CI、不激活或发布外部应用。
