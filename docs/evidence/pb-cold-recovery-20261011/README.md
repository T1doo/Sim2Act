# 有限文本提取的持久原请求身份与冷恢复

基线 `d5b3f47dbb14ce7d11e822b1ce37cac02e3eb408`，继续授权分支 `dev/pb-text-extraction-20261011`。root 唯一产品作者，既有独审只读产品、只写新 /tmp；旧 P-B 224 档及既有证据均不改。具体边界见 [合同](../../F2/PBColdRecovery20261011.md)。

本切片对应原 F2-T09/AT-05/18 的有限请求恢复缺口。受保护服务端 journal 在实际提取前保存原 key/主体/项目/实例/Run/源应用/目标/完整请求指纹、前序 key/单调序列及状态历史；正文只在服务端。PREPARED、COMMITTED 与 CLOSED 不冒充 Operation 状态或浏览器已安装。候选/task_extractions/COMMITTED 同事务；CLOSED 高水位及 expected_latest_key 防止迟到准备与提取复活。CSV 和既有执行器不扩展。

冷页面通过受保护项目元数据索引发现原 key，再以原 key GET 读取当前 source/target 授权后的冻结请求及既有回执，核对真实候选 hash/身份/项目/原 key/来源/目标/安装资格。恢复不重发 prepare/extract。未受理结果仍保持阻止；用户明确 CLOSE 与真实提取共享项目锁，已有效果返 COMMITTED，不伪造关闭。冷撤权页有可见 metadata-only 停止入口，不读取旧 Run 或正文；旧已提交回执仅原 GET 兼容，无 journal 回填。

浏览器不新增 localStorage/sessionStorage/IndexedDB/cookie/window.name/serviceworker 正文存储或 URL 正文。恢复 GET 明确 no-store，相关 fetch no-store；JSDOM 存储拒绝探针、实际 HTTP header 与请求选项分开核实，不证明原生缓存实现。两次独立 Node 进程、第二轮 fresh Store/API 和实际 SQLite 状态；HTTP 资源每boot19件，仍非原生浏览器。cold 普通 Worker 使用新材料/term，合成来源 provider 仅用于准备 test-only 上游。

候选1冻结 [369源清单](candidate1-source-freeze.json)，SHA-256 `2ba3cf692c0c72ebc9c4393944a4c39b92200e687e76307c7c60a6614e94ac85`，现已 WITHDRAWN。作者完整关联497 collected/496 selected/1 deselected在独审红证据到达后精确SIGINT，健康结束exit2，49个完成命名节点PASS，进程394.27秒；不是完整回归或最终验收。独审两维护组33及43PASS已在停止请求到达前正常结束，实际signals_sent为空，不能补造SIGINT或最终签收。独审2 API元数据FAIL及1实际HTTP冷页FAIL证明instance/source-app不匹配仍被项目索引返回，并把同项目授权target预览安装为source；没有重复POST或跨owner泄密的证明。另2独立门PASS，各旧结果均撤回留档。

修复通过真实Run→AppRun→Release/Instance关系核metadata绑定（不读取snapshot/input/body），并在源showApp之前做实际source-scoped GET；候选安装前最后原key GET require_latest在同事务复核当前授权、来源、最新COMMITTED请求与真实候选，历史普通GET仍可读。metadata-fix-first5FAIL为初稿误用不存在的Release.app_id列，日志保留；纠正为实际Instance.source_app_id后metadata-fix-second5PASS/0FAIL，369源0变化。

候选2冻结 [369源清单](candidate2-source-freeze.json)，SHA-256 `9818e2d75bf02ed26f615700aef6dfa1289bb32850c04a0f434727f087b95312`，现已 WITHDRAWN。独审实际HTTP/真实WebCrypto并发探针1FAIL/12.71秒：最后require_latest GET返回后自身await请求hash期间，另一同owner会话实际prepare新key成功201/sequence2，旧候选仍安装；0提取重发。作者500/501节点（1deselected）精确SIGINT exit2，完成命名38PASS/348.15秒；独审新维护30PASS/219.52秒、既有35PASS/220.34秒均精确SIGINT exit2，匿名中止记录不计命名PASS，369源无变化。独立三旧红复验及control/ABA共5PASS/24.85秒也随候选撤回；不是完整回归或最终签收。精确命令、信号、分母、退出与前后源散列另存。设计只读报告不计执行节点。环境断开通知后，仅一次实际健康核验于2026-10-11 23:21:03 UTC成功，HEAD d5、全部dirty保留、0 pytest/Node；不扩大权限或新建写入者，见 [回执](environment-recheck.json)。

历史逐轮保留：red 1FAIL（旧入口404）；backend-first1PASS；backend-matrix-first15PASS/1真实正文污染FAIL，已补当前授权后的持久正文精确比较；smoke-first2PASS/4FAIL（新驱动2个过宽缓存断言、1个不可用disabled名称动作夹具、1项新请求提示缺少scope文字）；smoke-second3PASS/1FAIL（屏障建视图后追加规则导致清理失败夹具）；smoke-third4PASS/0FAIL，各轮完成期间源0变化。后续最终范围另列，不累计重复PASS为唯一覆盖。

改动Python Ruff与4JS语法检查PASS。全树Ruff10原诊断JSON完全等于d5，mypy5原诊断及note相同，仅 checked source files 从64到65；全树lint/type不是全绿。详见 [静态回执](static-python-results.json)。

新 owner PENDING，语义 UNKNOWN、LIVE0、正式发布 false。原来源授权/证据仍参与审计；不同时做来源退休或扩算子。PG、Windows、native browser/缓存/视觉、旧源码升级、真实模型/付费API、真实owner语义、完整P-A/P-B/AT05/18、部署/正式发布均 NOT RUN。精确新SHA远端CI未验证。原tree/blob保护分别以stage/最终HEAD回执核验；正常分支提交推送的完整SHA/remote refs/零差异另在外部交付回执与最终回复给出。

最终GET之后的异步请求hash缺口修复：候选和原请求hash都先完成，current世代检查后才做最后原key require_latest GET，回执后的核对同步完成。维护冷场景使用真实WebCrypto digest/另会话真实prepare，新key201后最后GET应409，拒绝旧安装，frontend0prepare/extract，0Worker。网络查询与浏览器安装不是跨设备原子事务；只证明当前授权检查与可避免的自身await窗口已收紧，不宣称所有物理并发瞬间不可变。当时该轮结果尚待执行；最终第四轮实际结果见下文。

并发修复定向latest-fix-first3PASS/50.33秒，369源0变化，分别为真实并发新key、lost-commit及explicit-new-committed。候选3冻结[369源清单](candidate3-source-freeze.json)，canonical source-map SHA-256 `c02567c8ecd6b2ba1a56f463fd68789723934db9195ba81e87b762ebf46b54b2`，自候选2仅internal.js及两冷页面维护文件变化。候选3现已 WITHDRAWN：作者完整轮精确SIGINT exit2，完成206命名节点为205PASS/1SKIP/0FAIL/0ERROR，885.21秒，369源0变化。此前独立维护38PASS/407.70秒、既有43PASS/415.64秒、附加6PASS/29.76秒均正常exit0，但第三候选整体资格撤回；733原独审封存与LIMITED_PASS报告原字节不改，后置预算红证据与withdrawal另列。

后置真实预算红：同实例65个实际SUCCEEDED AppRun、结果版本1至65、每Run零Attempt/一个VERIFIED operation/真实typed record。第64来源project index200/64项；第65首prepare201、journal64→65，随后整个project index400 BUDGET_EXHAUSTED。独立1FAIL/63.67秒，正常exit1不造SIGINT；预算红源369及733封存原字节不变。最小修复在既有项目锁内，对新来源首prepare应用与metadata发现一致的64来源预算，超额先拒绝无写入；已有来源仍可显式CLOSE/新key，单来源64请求高水位不变。当时预算修复尚待实测；最终第四轮真实65来源结果见下文。

预算修复budget-fix-first3PASS/71.96秒，源码369无变化。第四候选[369源清单](candidate4-source-freeze.json)，canonical source-map SHA-256 `2c2b69524ac0cd13f384c4d1f4c17170c382444f53131f5922ba07b7ecf7e810`；仅request journal预算模块及对应后端维护变化，冻结当时完整作者/独审尚未结束；最终结果见下文。

第四候选独立最终维护实际39PASS/449.28秒（21后端＋18冷页面）、既有43PASS/389.80秒（34后端＋9页面）、额外6PASS/49.18秒、独立真实65来源预算1PASS/91.74秒，各0FAIL/ERROR/SKIP且正常exit0，0匿名/0活动自有进程，源码369前后一致。两次预算维护为分开的实际运行，不冒称新增语义覆盖。新[终审LIMITED_PASS](independent-final/FINAL_REVIEW.md)和[282档清单](independent-final/archive-manifest.json)SHA-256 `c3994a143af61f17c0f58b6ef9144c6d80b14c4956d5b1c8b1c2afa15a1c58b8`原字节已逐项核验；原[733撤回档](independent/archive-manifest.json)与[11预算红档](independent-budget-red/archive-manifest.json)分立保留，三份清单不改。独审封存当时作者完整关联仍RUNNING；作者随后完成的实际结果另列，不把独审组冒充作者全范围验收。

最终作者完整关联第四轮正常exit0：[XML](candidate4.xml)、[日志](candidate4.log)、[命令](candidate4-command.json)、[实际回执](candidate4-exit.json)。503 collected / 502 selected / 1 deselected，502个唯一命名节点：492PASS/10SKIP/0FAIL/0ERROR/0匿名；pytest1365.67秒，进程墙钟1367.420秒。10SKIP均明确缺孤立PostgreSQL应用角色前提，完整节点/reason见[汇总](final-author-summary.json)；一条既有socket/embedded-DOM驱动明确deselected；已知拒绝浏览器路径不重试或换URL。该轮涵盖18关联模块＋schema constructor节点，不是全库或完整AT。369个源/测试/pyproject路径before==after==freeze4，canonical map SHA-256 `2c2b69524ac0cd13f384c4d1f4c17170c382444f53131f5922ba07b7ecf7e810`，stage再逐项核对Git可重现字节。

最终作者18冷场景两Node进程/新Store共36页381检查、410可见enabled DOM dispatch动作、684实际HTTP资产GET；既有9场景/记录174检查/248动作/18boot/342HTTP资产GET。每boot19项，真实status/MIME/bytes/hash由测试逐项核验；页面与typed Worker结果不能代替真实语义。作者实际65 Worker预算、SQL私有读取及关联原proof（11档）逐字节保存至[raw清单](author-backend-proof-copy.json)；原/tmp不删除。所有原对象/owner/Grant保持断言通过，明确撤权与新增正常结果按原测试合同分别记录。

[中间轮汇总](intermediate-round-history.json)只分列原轮次，不累计重复PASS当唯一覆盖，candidate1/2/3 WITHDRAWN，匿名中止记录排除。全树Ruff10/mypy5仍基线，最终改动Ruff及4JS语法通过，见[candidate4静态](candidate4-static-python.json)。不保证跨设备GET与安装原子性，不签PG/Windows/native browser/设备崩溃/真实OS undo/视觉缓存、完整旧源码升级、真实模型/人工语义/owner、64×64长期容量性能、完整P-A/P-B/AT05/18、source退休、正式发布/部署或新SHA远端CI；均NOT_RUN或NOT_VERIFIED。
