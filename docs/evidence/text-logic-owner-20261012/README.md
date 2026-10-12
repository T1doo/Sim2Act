# 独立文本应用自有目标与精确版本签收：有限通过

合同见 [TextLogicOwner20261012](../../F2/TextLogicOwner20261012.md)。基线 `233ba9618ba462aad19e1ca16f085cd0d7242632`，开发分支 `dev/text-logic-owner-20261012`；root 唯一产品作者，独审仅写自己的 `/tmp`。本轮实现新的完整原生 GoalCard、适用范围、双 seal 版本绑定、精确 Goal 下的新 Worker 证据与完整逐项人工声明，不继承原来源或原目标应用的 GoalCard/签收。

## 最终实际结果

| 执行 | PASS | FAIL / ERROR | SKIP | 证据 |
| --- | ---: | ---: | ---: | --- |
| 作者最终新核心（candidate5） | 34 | 0 / 0 | 0 | [log](candidate5.log)、[JUnit](candidate5.xml) |
| 独立同版新核心 | 34 | 0 / 0 | 0 | [审查](independent/candidate5/FINAL_REVIEW.md)、[JUnit](independent/candidate5/new-mainline.xml) |
| 独立新增 API / 容量 / 事务探针 | 9 | 0 / 0 | 0 | [原探针](independent/candidate5/test_independent_owner.py)、[JUnit](independent/candidate5/independent-api.xml) |
| 作者受影响原家族回归，152 selected | 147 | 0 / 0 | 5 | [log](final-regression.log)、[JUnit](final-regression.xml) |

作者新34与独立新34是同一选集；独审43=34+独立9。原家族147P5S另次执行，不加总成一次完整工程或唯一用例总数。五SKIP需要真实PG应用角色。回归范围为原owner、持久Worker、独立text logic、文本Goal应用及其普通HTTP/JSDOM页面。另五个旧读取错误顺序测试是受控本地调度，不能宣称真实HTTP/Worker。

作者四个新页面场景（accept/reject/goal-lost/decision-lost）均完整PASS、Node exit0、stderr为空，每页20个实际HTTP加载的HTML/CSS/JS、两个新SUCCEEDED Worker及typed v1/v2，检查分别40/40/42/41，共163；所有可见动作均检查可见且可用。正常interval保留，等待在途HTTP/IPC及当前成功详情结束后断言；未停止poll或替换执行器。独审四页独立取得同样完整PASS。原来源私有内容及来源/初始目标两张GoalCard snapshot的受保护单元求值均0。页面证据分别在 `candidate5-ui/`、`independent/candidate5/ui-artifacts/`；原家族34页面/调度proof在 `final-regression-goal-ui/`。

独立新增证明实际第64/65版本边界、原key历史读取、两正常版本writer一成功一拒绝、第二seal后全事务回滚、任一seal缺失/单边bool污染拒绝；撤销target user/runtime权限后旧决定拒绝，metadata CANCEL/REVOKE仍可用。预算由实际51200 authority变为仍覆盖cap的63000时，旧PREPARE/DECIDE失效且0错误写入，新明确PREPARE可行。

## 冻结与历史

最终 [冻结](candidate5-freeze.json)及 [全部测试后冻结](candidate5-after-all-freeze.json)完全一致：377个Git可交付src/tests，规范map `f5a800b8c355d9ed38355c258073c28fe30f0199ffbdacacdd1270d4570d7a52`；5个ignored、未提交egg-info元数据单列排除。独审四次前后逐文件同样一致。最终独审报告SHA256 `25fe69bc04d5c5538f3e8888c17c6aafdcf612e57df563773f2fc6cac6bf09c9`。

全部红轮保留，不倒签通过：作者candidate1=18P；candidate2=22P6F（含修订后UI无法新PREPARE的实际缺口及测试预期错误）；candidate3=22P11F（屏障配置/清理顺序与污染后读取预期错误）；candidate4=27P6F（错误要求旧typed历史为空、driver提前读poll暂态）；独审candidate4=31P11F，详见其原报告。原家族首次113P34F5S的34F均为作者漏设已有NODE_PATH、驱动未启动的 `Cannot find module jsdom`，正确环境最终147P5S。对应全部源码冻结、log/XML、stderr、proof与原探针均保留。

新模块初次全mypy新增2处None收窄错误，最小修复后恢复原5处基线；全ruff仍10处基线，本轮改动检查PASS。见 `mypy-full.log`、`mypy-final.log`、`ruff-full.log`、`ruff-changed-final.log`。这两项全仓库检查仍为FAIL，不能称全静态或CI绿。

SQL原始JSON无损gzip封存，`sql-archives.json`列原路径、原SHA/字节及压缩SHA/字节；解压字节校验通过。两次独审原36产物manifest按解压字节逐项相同，原 `/tmp`文件仍保留。可以用 `gzip -dc <path>-sql.json.gz` 查看原JSON；没有截断trace。先前取消的五份原raw文件SHA仍与baseline一致。

233ba9的远端src/tests此前实际验证为373/373；378是本地373+5 ignored元数据，旧32是独审41子集，另2与84P1S分开记。纠正见 `prior-scope-correction.json`，未修改旧sealed/raw证据。

## 验收边界

本接受仅当前软件、SQLite、进程内TestClient HTTP、离线可见JSDOM与普通NoModel Worker；模拟provider初始fixture及全部人工选择均SIMULATED。技术语义UNKNOWN，LIVE0，正式发布false。新增Python改变现有all-py软件指纹，233软件签发的旧authority失败关闭；未自动重签/迁移，也未运行旧实库升级。

真实人类/语义、正式发布、真实或付费模型、PG、Windows、native浏览器、设备崩溃、旧源码升级、完整P-A/P-B、部署均NOT_RUN。既有CI Forbidden保持STOPPED，没有再查询；旧取消精确安装竞态永久NOT_VERIFIED，没有重试或替代。本轮无新的工具/平台拒绝。普通开发分支push及保护refs、377远端Git文件、工作区/未推差异另由最终交付回执核实。
