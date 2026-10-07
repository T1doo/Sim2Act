# 冻结原生条件报告候选：未push/未CI

基线5671d0fdc4797d2cac0be475a9acdf46bf61f637；独立dev/conditional-native-local，源码候选213fe90b734db33317d840e03be273ec7d880b1e。核心Run/DAG绑定线另树/另分支，不在此候选。产品src全部未变；source SHA及[candidate.patch](candidate.patch)给精确源码/CI接线差异。计划992cf57实施前已独立提交。

## CI差异与不变范围

- 只新增共享conditional-checks-ui.cjs、私有既有fixture动作、loopbackDOM适配器/一项测试，internal-ui.cjs在原protocol26及其截图/counts后同page追加phase。结果嵌既有protocol-results.json；无新增服务/资源/身份/Grant/模型请求、PNG或emit槽。
- Windowscaller保持原受保护browser/context/route/清理，并对新phasebefore/after实查renderer token/参数。控制sourcecontent/hash变更→精确恢复→仅撤一条既有用户读Grant/revision+1，无重授。每阶段完整表fingerprint核对，不动旧Run/账本/协议记录。
- workflow、PS/Windows Python runner、150秒Node aggregate、12秒predicate、4分钟browser step、15分钟job、package locks、原emit≤2MB whitelist、旧protocol/helper/assert均逐字不变。console新增仅本项目两个conditional路径403/409；不掩盖pageerror/跨origin/其他项目/source/500/404/旧protocol409。原legacycheck顺序不动。

## 本地实测与独审

共享oracle22check：显式授权内容读取、固定hash/合同/引用、已知报告PASS但业务BLOCK/语义UNKNOWN/ownerPENDING、真实2700ms等待poll保留输入、编辑失效/错误人工报告FAIL、未知事实UNKNOWN、技术请求失读、完整表无写、精确版本变更/恢复、实际200迟响应项目A-B-A、冷文档零POST/旧PASS、实际撤权清引用/metadata、无新身份/Grant/Run/外部请求。

最终相关集40PASS/1SKIP/0FAIL/0ERROR，78.70秒1warning；含相同共享module真实loopbackHTTP/JSDOM、旧协议DOM/集成/应用使用/注册fixture/条件API。Chromium因SUIDhelper配置BLOCKED原skip保留，不修系统/弱化保护。首20check专项1PASS11.63秒不冒充最终22，最终22由相关集与独审实跑。Ruff/Node/diff/SHA PASS。

[独审](independent/review.json)：最终共享22check1PASS13.88秒（module9731ms）；实提console分类10项、fixture精确两字段/全行恢复及重复变更/重复恢复/重复撤权拒绝5项、probe缺依赖与超时2项PASS。旧20check及顺序保留。错误报告覆盖缺口和probe输出管道风险已修为新增两oracle/DEVNULL，timeout10不变，实际driver输出仍捕获。源码SHA与独审一致。

初单选旧registeredfixture5setupERROR（ModuleNotFound integration_fixture）及相关34PASS1SKIP5ERROR保留；原因旧canonical test_product_integration_fixture.py在collection插入scripts/agent-ui路径，单选漏该既有依赖。未改旧test/source，不把错误抹成PASS；包含canonicalfixture完整相关集已40PASS1SKIP。

## 未测/预算

Edge/Windows原生renderer功能与新phaseaudit/截图像素/Win11 NOT_RUN；DOM不是原生。此候选不扩大原PNG签收范围，新phase无截图。复用旧20bb参考124秒protectedhelper/824秒job，仅是旧源码历史，不能签567/此候选。新增phase七个fixtureCLI、两次rendereraudit和真实2700ms等待；本地module时序不证明Windows总helper<150或job<900。预算均未放宽，必须以后实际授权Server终态验证；本轮无push/CI，无真实模型/真实身份/准备器激活。

下一可执行原生片：在明确授权后只取精确本候选到既有分支，正常push单次Server，监督既有15分钟/150秒终态；若预算失败修本候选时序/接线不降旧断言、不加时、不绕保护。核心线不能借此原生候选签收。
