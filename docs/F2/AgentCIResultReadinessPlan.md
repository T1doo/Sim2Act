# Agent 原生结果回读 oracle：本地修正候选

冻结源82ffe61的唯一WindowsCI37576109066整体FAIL，工程904PASS7SKIP、历史39PASS，后续agent14项后v2结果断言失败。实际截图列表结果版本2/详情读回中；独立真实HTTP/JSDOM复现终态poll先发实例GET且清空instance，手动刷新捕获undefined id仅完成列表，busy=false提前满足旧idle；同一个真实回包释放后v1/v2都显示。

只修scripts/browser-ci/agent-ui.cjs的结果检查等待：以当前身份/项目/app及精确实例ID、期望data_version、实际结果条数/版本标题为就绪信号，然后保留原v1/v2和零重复Run断言。只等待现有读回，不增加GET/POST/重试，不提高原150秒/helper、4分钟browser、15分钟job时限；不改product busy/权限/worker/fixture账本、不伪造结果。v1和v2两处都使用同一有界就绪逻辑。

验证保留独立原FAIL、原GET回包v2/2条、释放后同iid成功；旧idle在pending时true，新就绪false，在原回包释放后true。错误版本/实例/记录数/缺v1/v2标题/当前身份项目不匹配均不可就绪。静态确认原断言/脚本安全边界不变、实际HTTP/DOM兼容回归。此为同型时序根因复现和oracle修正，不证明它唯一解释Windows瞬间的全部时序。新候选仅本地，未经新CI/native验证；不自动push/rerun，不模型或实验身份，不提升完整P-B/F1/AT02/Win11/Release。
