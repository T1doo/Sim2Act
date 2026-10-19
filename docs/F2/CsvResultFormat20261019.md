# 图表合同盘点与同 Run CSV 成果格式

接续 `e455a21964cd0e797ceddd9e0e9573f073c2dd40`，原13个本地提交保留，远端/auth不再探测。对照原 F2-T04/T06 与产品 §3.2 F05、§3.3、§5.3：chart 在 `View` 中只有 `component_ref/output_field`；校验仅核输出字段存在，未定义图形类型、x/y角色、序列、单位、排序、缺失值或聚合语义。所有现有chart引用是枚举、未支持说明及负例。字面引用中的 start/end_line 是出处坐标，不是业务量；CSV的 sum/count/column 也没有轴角色合同。因此本轮不画图、不更改chart支持声明。

原 F05/T06 同时要求 MD/JSON/CSV 成果。现 `data.aggregate_csv` 已定义同一材料、列、count及精确十进制sum字符串；`csvRunDownloadValue` 已定义实例/Run/Release/结果版本及该四字段的白名单。当前入口只有结果JSON，原CSV材料下载不等于本次计算成果。选择这个已有数据合同的格式缺口，不重复列修改、授权、私有试写或已交付JSON导出，不新增producer、executor、Grant、接口或账本写入。

## 实现前格式与验收合同

1. 原成功Run旁另列“下载此运行结果 CSV”，JSON按钮和字节合同保持。两格式复用同一fresh/no-store GET、Run/typed AppRun/Release/版本/四字段比对、当前权限与账号/连接/项目/工作区/实例/读取/所选Run围栏；同Run共享in-flight锁，重复/跨格式点击不重复下载。失败或未选Run不提供下载。
2. 文件为UTF-8无BOM，固定八列表头 `instance_id,run_id,release_id,result_version,resource_id,column,sum,count`，随后且仅一行该Run结果；无原材料、账号、权限、完整合同或模型内容。CSV单元格按逗号/双引号/CR/LF做标准引号编码，双引号加倍；记录分隔固定CRLF，末尾CRLF。文件名仅用原实例、Run、结果版本及csv扩展名；MIME `text/csv;charset=utf-8`。
3. sum不经Number/parseFloat/浮点运算，保持原精确字符串（含负号/指数）；count和result_version只序列化既有安全整数。不增加单位、时间轴、额外聚合或取整。CSV解析器可逐格回读原值，不声称外部表格自动类型推断保精度。
4. 文本字段若含Unicode控制/格式字符，或去前导空白后以 `= + - @` 开头，CSV保守拒绝且无Blob；不加apostrophe或改写原值。sum单独要求完整十进制/指数数值形状，合法负数不被当成公式。JSON原值下载保持可用，页面给明确格式限制。正常汉字/逗号/双引号列名可逐字输出。拒绝仍先fresh GET重新鉴权。
5. 一条合成真实HTTP/原NoModel Worker→JSDOM实际下载链核当前与历史Run、超过JS数值精度的sum、Unicode/逗号/引号、负值、CSV危险列名拒绝而JSON不改、双击/跨格式锁、实际迟到读取不下载和真实403。正文反例仅覆盖新格式边界，不重跑旧完整故障矩阵。页面前后55表全等，明确fixture撤权另列；零模型、页面零POST/Worker。

以上是实施前合同，原件保存在证据根 `contract-before-qualification.md`。后续实际执行如下。

## 实际交付与验证

`use.js` 在同一成功Run旁提供独立CSV按钮，沿用原JSON控制器和共享锁，原JSON字节未变。UTF-8无BOM、八列、一条成果、CRLF；精确sum原字符串，危险文本保守拒绝且JSON可用。本次不新增Python运行代码、接口、执行器、权限或数据库结构。

冻结安装包实际运行3个独立pytest节点全部通过，0失败/错误/跳过，总122.999秒：`csv-format`43.170秒（20项页面检查），`csv-boundaries`37.793秒（12项），原`versions-and-rejections`回归41.707秒（52项）。这些页面断言不另计为pytest用例，也不作为独立覆盖数相加。Ruff及两个Node语法检查通过；Python运行文件未变，未重跑mypy或旧完整导航/恢复矩阵。

JSDOM+Node WebBlob捕获接实际loopback Uvicorn HTTP，非原生浏览器保存。每例实载27个页面资产；130次页面GET、81次资产返回、61次fixture TestClient调用分开记录。3次可选protocol资产400明确保留，未证明该功能；唯一真实403来自fixture资源READ撤权。错误Release正文与原JSON反例均标注为实际HTTP之后的合成注入。4份CSV由标准解析器逐格读回并重编码为完全相同字节，保留历史Release、`9007199254740993.123456790`、汉字/逗号/引号及合法负数。实际危险列CSV零Blob且原JSON仍可用；CSV重复/跨格式锁、Run ABA迟到200拒绝、实际403清空保护数据均通过。

fixture的13个原Worker各领取一次（10成功、3预期非数值失败），页面零POST/Worker。55表逐行前后快照：格式例与JSON例全部相同；边界例仅原撤权API修改一个既知Grant的revoked及revision，其余54表与其他Grant不变。未据此声称账户/项目/实例导航在新CSV中重新动态跑完；这些围栏来自未改变的共用控制器并经静态复核。

wheel共958217字节，SHA256 `c3ea694281e2c68791da89bfb8f96632c16f26db4d6216218bb71539cba78195`；141个包文件与源/安装一致，较前包仅`web/use.js`改变，112个Python文件不变。148项冻结输入在执行后无变化，94个已加载sim2act模块全部来自该安装包。离线现有setuptools84构建；固定setuptools82.0.1构建未运行。

作者[资格说明](../evidence/csv-result-format-20261019/README.md)、[JUnit](../evidence/csv-result-format-20261019/qualified-installed.xml)、[逐文件核验](../evidence/csv-result-format-20261019/closed-evidence-verification.json)及[完整原件压缩包](../evidence/csv-result-format-20261019/author-raw.tar.gz)随提交保留。作者manifest SHA256 `df70350e20e5559ac8c4b24a9d3098a651322454e332d6e40687aac32c34ed1b`；包含早期fixture/driver失败和观察器错误，不覆盖或删除失败证据。

[独立报告](../evidence/csv-result-format-20261019/review.md)有限通过 `LIMITED_PASS_CSV_RUN_RESULT_FORMAT`，本片无剩余确定P1/P2；独审未执行产品/pytest/模型/网络，也未读取物理DB内容，独立比较的是完整55表JSON、HTTP/Blob、合同指纹及源/安装字节。独审37文件封存manifest SHA256 `29fb1295e7b0c1a050d4bc9a9fe3b04eefa7444cf589e4f9500d1d0eae187688`，不签整个F2或后续提交/远端状态。原封存机器报告中作者manifest的path标签误写为wheel文件名，bytes/hash均属正确manifest；[独立元数据补充](../evidence/csv-result-format-20261019/review-metadata-addendum.json)更正该标签，原封存报告保持原样，产品及测试结论不变。

真实模型调用0；真实语义/场景UNKNOWN、人工验收PENDING。Windows、PG、原生文件保存、远端CI、真实provider和正式发布NOT_RUN，旧满盘独审报告NOT_RECOVERED。本轮远端/auth/推送操作0；远端当前HEAD与差异UNKNOWN。原13个本地提交保留，新增提交仅本地普通开发分支。

图表后续至少需要producer声明的值类型及x/y角色、图形/系列、单位、排序和缺失值规则，以及可回指原Run/Release的数据示例；在这些合同成立前，枚举`chart`本身不构成可安全作图输入。
