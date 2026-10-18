# 自然规范成果版本与同 Run 人工导航

基线为已交付的 `0a0430223be5bf27d8dc72ee33a4a479bfd92fdc`，普通分支 `dev/natural-owner-run-navigation-20261018`，root唯一仓库写入者；开工HEAD与远端一致、工作树干净，约24GB可用。旧封存独审及原始执行文件不改写，不重跑关闭流程。

原V5 F2-T03/T05/T06要求新输入产生实际新成果、统一入口复用权限网关、历史与本次可辨认。现有 `test_same_saved_logic_third_material_cold_worker` 已证明同一P-B应用/Release/实例新增v2并保持v1，现有成果卡也已有JSON/Markdown下载；本轮不声称这些从未实现。此前完整P-B页面资格仅首次v1，继续补同一使用路径的第二次输入及两版本实际下载。

核得的真实功能缺口在 `owner-review.js`：运行详情/成果卡→同Run人工验收已接通，而人工Run下拉仅对workflow调用 `showInternalRun`，自然spec直接读人工合同。因此可以出现人工合同及清单已指B、上方机器运行详情仍A或为空。仅让自然spec与原workflow复用同一运行详情入口；不新建控制器/API，不修改权限、验收、运行器、Release或数据版本合同。

`showInternalRun` 使用原实例/Run/身份连接/项目/工作区选择代际，先清旧人工内容，读取机器Run后才选择其人工合同；`selectOwnerRun` 赋下拉值不派change，不递归调用onchange。原Pending按Run保留，切换和冷页导航不自动写入。旧v1在v2后仍按服务端当前版本门拒绝完整验收，历史声明不能变为新结果的接受。

## 定向资格

一条fresh实际HTTP/JSDOM连续P-B用例：正常生成3次Mock→来源Worker1次→原成功来源提取/保存内部Release和实例→P-B v1正常Worker1次。该v1由fixture正常API/Worker建立，不能说它由页面提交；fixture另外以既有owner API PREPARE一条，未DECIDE，不代表真人签收。页面从统一目录选择此P-B与实例，显式选择已保存的第三材料/Goal、预览、单独确认并仅提交一次v2；正常Worker1次保存新Run/AppRun/typed v2。预期共6个Mock、3次业务Worker，以原始wire和claim实际计数为准，不改时钟/lease/deadline。

验证同app/runtime/Release/iid、v1原typed/artifact与owner行完整保持；v2人工合同绑定本次Goal/材料/version2，序列0/PENDING不继承。下拉v1/v2时机器Run、详情与人工选择同步，v1原PREPARE为STALE metadata-only且不可prepare。只新增一个受控迟到machine-Run GET响应投递边界：取得原200后切另一Run，再释放旧响应，不覆盖新Run或追加旧owner请求；这是客户端投递控制，不称实际网络并发。

冷页经统一目录重开同一实例，分别下载v1/v2的JSON及Markdown共4个真实Blob，逐字比对各次新 `spec-artifact` GET、原Run/版本/source、独立SHA和canonical内容；下载与历史导航全库只读、零POST。每boot服务27资产核SHA，保留真实请求/响应bytes、阶段、全表状态、模型wire/Worker claim、完整执行输入前后映射和失败finally原件。再运行一个受影响的原自然目录/控制器合成导航回归；其API为synthetic，不能计成实际HTTP或Worker证据。

源码/测试完整冻结后执行，实际结果另附，不预写PASS。Windows/native、PG、真实模型/语义/场景、远端CI、部署未因此验收；永久取消旧安装digest窗口、旧exit139因果Unknown与原满盘独审缺证保持。关闭回执准确性疑点仅收窄文档：完整来源指纹在CLOSE事务写入前后重核，后续terminal GET核当前访问门和历史封存，不承诺逐次fullsource重验或一切闭后版本漂移均锁定；该漂移时序未实测，不追加关闭测试。

首轮冻结 `c068e165f7ac6bc38a5d474f26e7a99f8e0bac4c` 的两个节点均失败，原件保留。实际用例在v2提交前因fixture先PREPARE后保存THIRD而新增4条既有材料权限、使原人工合同grant_version失效，页面正确返回STALE；完成8项页面检查、5次Mock、页面Worker0，未完成v2或下载。只将THIRD/Goal正常保存提前到PREPARE之前，不改变业务时钟或断言。旧synthetic探针在32项后因缺精确Release响应及instance.release_fingerprint，触发现行版本门而清实例；只补匹配的合成metadata，原36项断言保持。首轮687输入/133生产前后0漂移；修正后重新冻结两测试，生产一行不变。
