# 同一 CSV 实例的授权材料替换：实际证据

产品源码冻结 `805afe60cdd94d6d4679e0da9c1f7fde752f67d2`；最终观察器／夹具修正提交 `ef3615d1f6f9083b55f116a408539e61faa62aca`。129 个产品文件逐件无差异。新严格合同复用原 CHECK、批准和同业务 iid 的 CAS，不创建 executor、App、运行身份或产品 Grant。[已推送源码的实际远端回执](originals/source-delivery-verification.json) 是 ef3615d1 推送后的历史记录，早于本证据提交；最终证据 HEAD 以交付消息和实际远端为准。

## 资格范围

**11 个唯一定向用例合格，分批取得；不是最终 HEAD 一次全绿完整套件。** [逐个真实 JUnit 节点及批次](originals/qualified-coverage.json) 保留实际失败／error，不把修正前的轮次改判。

| 范围 | 合格唯一用例 | 原件 |
| --- | ---: | --- |
| B CHECK、同 iid CAS、新业务 Run 18/count2、PENDING、旧 A 历史与权限计数保持 | 1 | [JUnit](originals/independent-positive/junit.xml)、[完整身份／合同／操作／结果链](originals/independent-positive/pytest-temp/test_authorized_B_same_instanc0/actual-material-delivery.json)、[39 条主 client HTTP](originals/independent-positive/pytest-temp/test_authorized_B_same_instanc0/actual-http.json) |
| A/B 撤权冷读取正文屏障、错误 hash/dataVersion/未授权 B、A/B 内容漂移、双 seal canonical 重签、真实 stale CAS | 7 | [独立报告](originals/independent-contract/independent-review.md)、[原批 6P/1F JUnit](originals/independent-contract/junit.xml)、[纠正 CAS 1P JUnit](originals/independent-contract/corrected-cas/junit.xml)、[实际 A 数据推进后 CAS409](originals/independent-contract/corrected-cas/pytest/test_material_stale_cas_after_0/actual-independent-material-stale-cas.json)、[重签拒绝及原件恢复](originals/independent-contract/pytest/test_material_canonical_json_r0/actual-independent-canonical-json.json) |
| 完整页面流程：明确选择 B／同列、三阶段重新确认、CHECK/CAS 真受理丢回执仅原键恢复、防重复、B 新结果／人工入口 | 1 | [JUnit](originals/qualified-ui-flow/junit-flow-recovery.xml)、[53 项页面检查与实际请求](originals/qualified-ui-flow/pytest/test_visible_material_replacem0/page-result.json)、[真实业务交付](originals/qualified-ui-flow/pytest/test_visible_material_replacem0/actual-browser-delivery.json) |
| 页面账号／项目／实例迟到回调隔离 | 1 | [原批真实 2F/1P JUnit](originals/author-805afe60.xml)、[24 项页面检查与请求](originals/author-805afe60/test_visible_material_replacem1/page-result.json) |
| 原同材料列修订回归，保留 Goal，quantity→amount，新结果30、人工 PENDING | 1 | [独立 JUnit](originals/independent-old-column/qualified/junit-old-column-same.xml) |

全部使用合成 CSV、SQLite、真实 FastAPI TestClient 与原 NoModel Worker；页面运行是实际 HTTP 驱动的 JSDOM。模型 attempts/reservations 为0。人工声明与勾选均为合成测试，不是真实用户签收或语义验收。页面作者的运行不冒称独审；非作者对两 JS 和全部产品差异的有限静态审查在独立报告中。

## 冻结与原始失败

- [614 个源／测试／项目输入的开跑前冻结](originals/code-freeze-805afe60.json)；[扩展 653 输入逐件对 Git 的核验](originals/expanded-inputs-during-805afe60.json)；原批开跑后所有614与653输入零差异的证明在 [批次分类](originals/author-805afe60-classification.json)。
- [52 项实际页面资源字节哈希](originals/qualified-page-assets-proof.json) 均匹配805；[129产品文件与已推送提交桥](originals/pre-source-push-verification.json)、[正例函数 AST 桥](originals/positive-observer-ast-bridge.json)、[纠正 CAS 函数 AST 桥](originals/stale-cas-fixture-ast-bridge.json) 说明测试修正与已运行文件的对应。
- [首个 WIP 产品失败](originals/positive-wip.xml)：采用预检硬编码旧 Preview，已在805修复。该未提交 WIP 只保留597个文本指纹及原始失败／HTTP／DB，不当作完整成功冻结。
- 原805作者批2F/1P：重复 Run 回执 cached:false→true 和 adoption POST最小回执／GET完整批准的观察器假设错误，均只修相应断言后单例重跑；保留全部其它断言与超时。
- 原独立批6P/1F：夹具晚加B授权使旧A2 authority指纹过期，真实A运行在CAS前被现有权限边界拒绝。仅纠正B预置授权先于A2冻结，再以真实A新结果推进dataVersion后取得CAS409；没有放宽 eligibility。
- 两次独立快照缺少传递导入fixture的首轮错误原件完整保留；只补同冻结提交的fixture。完整批次XML在覆盖清单中，不盲目相加成新测试数。
- [只读图影响核对](originals/actual-graph-impact-readback.json)：预期保持的Goal／已注册规则3项零误改，应更新10项零漏改；保守APP重验计划的retained分母为0，记不适用，不填百分百。此为已捕获证据的只读分析，不新增测试。

[逐件文本与字节切片索引](READABLE.md) 可直接打开；[原始清单](raw-manifest.json) 覆盖 161 件、44,618,547 字节：UTF-8文本 144 件、二进制 17 件。`originals/` 提供逐字节原件，关键文本上方可直接读取；大文本的 `text-parts/` 是可按offset拼回原SHA的UTF-8字节切片。另有 [完整原始归档](raw-evidence.tar.gz)，所有member逐项SHA复核；不要求审查者靠读取二进制归档取得关键文本。

原报告中的pytest `current`链接已用[逐字节实体副本](alias-proof.json)保留可读路径，不新增或改写执行证据。

## 先前证据与未验项

此前a05的 [原件可读索引](../csv-full-report-instances-20261017/READABLE.md) 与 README历史回执链接已由db2228修复；[本次独立原件核验](originals/baseline-and-wip-readonly/a05-readable-audit.json) 确认155件归档、129文本／26二进制、36链接和610原输入无差异，没有重跑a05。旧满盘环境最后独审报告仍缺失，未声称补回。

未执行真实模型、真实用户／业务／语义场景、Windows、原生浏览器、PostgreSQL、远端CI、部署、通用DAG或完整回归套件。正例原测试的3次cold GET已实际断言通过，但响应未单独记录；39条主client HTTP和保留DB可检查，未伪造原cold响应。本轮没有改main、强推、部署、工作流或安全权限。
