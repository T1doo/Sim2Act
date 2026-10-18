# 最终有限独审：App追加CSV材料业务授权

**LIMITED_PASS_APP_MATERIAL_BUSINESS_AUTHORIZATION。** 在单个已有Goal CSV App追加一份同项目B的选定范围内，未发现剩余阻断性P1/P2。既有用户/项目权限是前置，实际仅新增App runtime对B的READ/SUM两项24h业务Grant，不新增主体、executor、凭据或系统权限。

本人只做源码/AST与闭合文件、ZIP、哈希、JSON表数据复算，未执行产品、pytest、HTTP、Worker/model、DB/SQL、Git或网络。最终9项源哈希已实读匹配；运行142项before/after/当前一致，wheel140文件与冻结哈希及实际安装字节相同。轮子952178B，SHA256 `0f581efd1c296ae43357cefdf99bb84afaa8cb867004f2ff4d43a9053b9f1e60`。完整机器证据见[final-verification.json](final-verification.json)，可复算脚本与实际stdout/stderr均保留。

最终作者API为4例PASS（pytest8.88s，外层11.587746884s），48条ASGI/TestClient结构化请求，非socket/wire资格；独立复算55表导出、scope/fullbodyFP/双锚，确认授权恰两App/B行、撤回仅原组rev+1，权限/范围拒绝无写。后台到期窗口为合成权限时钟验证，未等待真实24小时。已有accepted key变体没有ABSENT证明；明确未受理仅在owner/project/App作用域和原两锚ABSENT、事务回滚完成后获得证明。

最终安装包三个页面均PASS：新页29检查/102请求/133.274952915s，冷页9/56/41.903051300s，撤回页13/61/29.996130266s，三个owned服务均exit0且clean。独立重构219/219响应SHA（JSON、原首页banner和静态资源）及75份JS资产SHA。每页有一个可选protocol/contracts的400，不能称HTTP全成功。页面请求合计204GET、15POST，包含显式fixture控制调用，检查数不是pytest用例数。

从0 App/B Grant的原spec1/Goal1开始，先正常A30/v1；错误纯GET键不锁写，过期权限基线409在54个非heartbeat表零写且核完整NOT_ACCEPTED证明后，只能重新读取、选择并勾选。随后明确授权仅两Grant与两seal，新周期使用新baselineKey并保留旧键，再沿原CHECK B350→新Release→同iid采纳→显式新B350/v2。三个普通Run均SUCCEEDED/fence1，3claims，模型Attempt/Reservation均0；隔离CHECK的typed版本是1，不冒充业务v2。Goal1、旧Release/Run/typed原行保留，冷读54个非heartbeat表相等，人工入口PENDING，语义UNKNOWN，没有PREPARE/DECIDE。

失去原A-owner READ后，真实403清私有结果/列/Goal修订正文，metadata入口仍可达；选定B两项Grant同TX撤回为rev2。旧ACTIVE GET在替代视图撤回之后投递，不重新装入页面或恢复Grant；原授权键回读REVOKED。独立复算该组、另外唯一A-owner READ撤回及其余52个非授权/heartbeat表保持。B结果403发生在A失权与B撤回组合之后，不据此声称隔离验证了B单独失权的因果。

三项UI P2（纯GET误升级未知写、403残留私有UI、明确拒绝误锁UNKNOWN）及后台到期复查均已保留早期发现与修后记录。初UI快照已包含并行修复，修前仅早期工具文本；没有补造修前文件。三次本独审纯观察器错误（行顺序、猜测不存在源码副本、BANNER字符串AST）保留原脚本/实际或明确转录stderr，只修纯文件审计后通过，不计产品/pytest失败。修复前qualified-installed三页成功窗口保留为SUPERSEDED，不充当最终源资格。

限制：只验单App新增一份B。AUTH64请求、控制列表64材料（含A）不等于支持已验64份新增B；满额边界NOT_RUN，既有项目Grant列表/逐gid撤回仍保留。未动态注入丢POST回执；原键恢复为静审与后端重放证据。账号/项目/工作区/实例围栏为本轮静审，本轮动态迟到对象是同App替代视图。无Windows、PG、原生浏览器/视觉、真实模型/语义/用户场景/真人签收、远端CI、LIVE或整体F2资格。共享既有锁定依赖，不签干净机器依赖安装。没有打开或重算物理DB；不背书后续归档、提交、推送或当前远端HEAD，未恢复旧满盘缺失报告。
