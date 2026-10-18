# 私有记录试写：最终有限交付

基线 `a1649ed443280ad16da45a0a55a0f8086889d8fd`；普通分支 `dev/production-trial-stages-20261018`。原 F2-T08 / AT17 要求真正试写只影响预览空间；旧测试注入表、仅意图预览、普通空实例均不能代替。九任务盘点、图表/发布/真实调用前置的实际代码依据在独审档案，不重复CSV、材料授权或旧恢复矩阵。

用户现在可在记录应用目录明确选择内部 Release、单独确认创建私有试写空间，再在“业务实例 / PREVIEW 私有试写”独立分组中选用。原表单、逐次预览确认、Worker、Run/Operation/Intent/Receipt、typed/CAS 将真实JSON保存到私有目标，不新增executor、Grant或表。试写不进业务资源目录、不改变旧业务集合/权限基线；选择业务实例清输入，需重新填写、预览和确认。私有Run/结果/项目历史/导出持续标记PREVIEW，没有晋升或发布接口。

最终资格原件（数量不相加）：

- [安装包API](api-installed-final.log)：6项用例，46.54s，112条实际TestClient/ASGI响应。覆盖真实保存、冷回读、原键重放、严格输入/其他空间及账号拒绝、公共提取拒绝、实际插入后事务回滚、撤权后元数据取消。
- [安装包页面](ui-installed-requalified.log)：1条JSDOM流程，40.95s，75项检查、2boot、174 ASGI响应。其中54静态资源、106页面动作、14fixture检查；200=152/201=11/202=5/400=5/403=1，不能称全HTTP成功。是真实served JS与ASGI IPC，非原生浏览器/网络wire。
- 页面实际完成：创建POST201后受控丢回执→换另一已有业务iid→仍保留原UNKNOWN锁、禁用新建和旧确认→原key单次GET恢复仅一个私有空间；再独立确认CREATE→DONE、原Worker真实写入、冷重开/旧Run/导出、迟到响应与业务实例/工作区/项目/同账号重连隔离、项目历史精确导航、另行明确业务写入；最后撤WRITE→单403清正文→显式读取停止元数据→单次取消同一QUEUED Run，fence0未被Worker执行。
- [55表oracle](private-page-oracle.json)：全部既有行不变，新增账本逐一绑定私有iid/两个Run/Operation，保存两个真实私有对象；resources/Grant/旧业务行保持。后续明确确认的普通Run才产生业务资源和两条派生READ。完整分期55表、HTTP/IPC、正常Worker及API回滚原件在作者档案。
- [wheel](sim2act-0.1.0-py3-none-any.whl)：957688B，SHA256 `993d022e17d445f76c8277f8fb65f92a00e1595b58323e8dbff9db708691facc`。[141包文件](wheel-verification.json)源码/wheel/安装完全相等；[145源/测试并集](source-freeze-qualified.json)冻结后[0变化](source-final-unchanged.json)。[包版本差异](wheel-difference.json)只包含私有入口JS，全部Python相同。
- Ruff/JS语法通过；[同Python的旧2项业务回归](prior-ordinary-regression-2.log)15.53s，作为前轮证据保留，不冒充新执行。focused mypy新4/旧3文件同4条tools历史错，不称全量类型通过；完整基线import另有28条历史问题。实际构建使用现有Python3.12.14/setuptools84、no-index/no-isolation，pin82.0.1构建未执行。

[最终作者原件](author-raw.tar.gz)及[manifest](author-MANIFEST.sha256.json)/[seal](author-SEAL.json)保留492文件/27606087B/8个pytest路径链接；manifest SHA256 `00c71ecfa882bfa0364597ecbb693ec7a936332bf60f769637515f07c0f8ec9c`。原70检查版本在[superseded-70checks](superseded-70checks/README.md)原样保留，明确被替代；其旧作者manifest613文件亦未改。独审先后发现的两次停止入口P2、创建未决锁P2、修复前PASS、实际失败及测试错误均保留。新测试一次误假设丢回执仍保留原业务正文，原控制器实际清正文；修正为selectedIid保留而instance为空，未改产品或重签Release，最终75检查通过。

跨账号API实际拒绝且正文SQL有正向校准；跨账号页面仅静态。冷页成果回读在撤权前，撤权后仅签本页已核Run停止，不签冷页撤权恢复。真实模型0、语义UNKNOWN、人工PENDING；Windows、PG、原生浏览器、真实场景/调用、远端CI、pin82构建未执行。正式AT17/F2/发布未签；chart/发布仍缺合同与代码前置，可信免费零收费账户来源仍SOURCE_MISSING，旧满盘最终独审NOT_RECOVERED。

[独立有限审查](review-final-independent-review.md)结论为 `LIMITED_PASS_PRIVATE_RECORD_WRITE_PREVIEW`，未见剩余确定P1/P2；[机器复算](review-final-verification.json)及[审查原件](review-raw.tar.gz)/[封存清单](review-sealed-manifest.json)保留37文件/398943B，manifest SHA256 `0eee1485296567c063699c1408118d9c1c7bfb24d82163d03410f207c5249ba6`。独审是源码与原件独立重算，未亲跑产品/测试或读DB内容；55表核对对象为作者导出JSON，8个DB只stat。最终无JUnit；正文SQL正向校准在测试内断言，但clear前SQL未另存，保存的是拒绝路径SQL，不能称完整SQL/网络wire重建。审查不背书未来提交或推送；其后由唯一写入者单独核Git blob和封存文件。

本轮远端/auth/推送操作0；最新远端HEAD未知，最后ACK `a7403b379b1278fd1be533ca21d790f0311244af` 后原12本地提交保留，新增本任务本地提交。无main、强推、部署、新增费用凭据或安全权限变更。
