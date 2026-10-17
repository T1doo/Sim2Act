# CSV Goal 修订：确认前离开再返回

修复 `6edb626c4203def2a735006e860dcbca807315df` 的三个实际页面阻断：草案已保存而 CHECK 未提交、Release 批准已准备而未保存、CAS 批准已准备而未采用。返回时原控制器缓存仍在，但可见证据和两列选择为空，重新勾选却能提交下一步。

在“使用已保存的本地应用”选择原 CSV 实例后，返回上述阶段会先重新 GET 当前基线及原键的完整冻结对象，核对归属、版本、权限和批准有效期，恢复 Goal、材料、amount→quantity、实际 CHECK、Release 及保留数据预检。旧勾选清除，阅读后可重新明确确认，继续到原实例新 Run 的实际合计 5 和独立人工 PENDING；原合计 30 与旧 Goal 历史保留。返回本身不 POST。

UNKNOWN 保留原键和冻结请求，只 GET 恢复；CAS 恢复检查原批准、from/target Release、实例版本和数据版本的精确历史。仅基线新增结果的变化允许阅读差异后显式提交原 CHECK，由既有服务端未受理证明决定能否重新准备。没有新 executor、Grant、runtime、权限或后端变更。产品边界仍是同卡下一版本、同材料、有限列映射，内部未发布、语义 UNKNOWN。

## 精确来源与结果

| 来源 | 作者运行 | 独立运行 |
| --- | --- | --- |
| 生产修复 `776d76581c7f811f39af584283578d9b252a994b` | 完整21项：20 PASS、1 FAIL、0 SKIP | 完整21项：19 PASS、1 FAIL、1 SKIP |
| 测试修正 `849a931f7dbb8926ca9cbe166c3cfba3527dbf0a` | CAS 返回定向1 PASS | CAS 返回与旧实际 HTTP 使用入口定向2 PASS |
| 最终有效覆盖 | 21个唯一用例；22次 pytest 用例调用 | 21个唯一用例；23次调用，含1次未执行业务的 SKIP；实际执行22次 |

未声称在 `849a931f` 或最终证据提交上全21项重跑。两个来源的126份生产文件字节完全相同；`849a931f` 仅修正测试 oracle：adoption POST 只返回最小提示，完整冻结内容应取导航前的 GET 回执，并绑定同一批准 id/fingerprint。原 FAIL 保留。独立 SKIP 是 jsdom 探测路径缺失，接好现有本地依赖路径后补跑；没有安装依赖或改变 tracked 源码。

21项包含8个 API 用例、9个完整页面流程及4个原有回归，覆盖三阶段确认前返回、目录中 CHECK 实例的排除、同视图轮询、账号/项目/实例迟到隔离、CHECK 丢回执、已证明拒绝后的明确新意图、基线新增结果、CAS 丢回执、旧/新结果与人工验收分离、版本/CAS/权限/材料/锁边界。新 CSV Worker 使用 NoModel；旧回归使用本地 mock/NoProvider。没有真实模型请求。

- [作者有效覆盖及来源](author-originals/author-effective-coverage.json)、[776完整运行](author-originals/author-776d7658/report.json)、[849定向运行](author-originals/author-refined-849a931f/report.json)。作者607份输入各次前后不变；源码连续性另见 [证明](author-originals/source-continuity.json)。
- [独立最终报告](independent-849/independent-review.md)、[逐用例证明](independent-849/independent-proof.json)。两快照636份输入各自前后不变，并逐文件比对 Git 对象；额外包含32份同 SHA 的 docs gold。初次 collection 缺 gold 的错误原件保留，未计入用例执行。
- 返回后新 GET 有额外严格顺序断言：限定第二次 `/context` 到下一次明确 POST 之间，不能由离开前的 GET 满足。[作者原始顺序核验](author-originals/author-fresh-get-proof.json)、[独立顺序核验](independent-849/strict-return-sequence-proof.json)。采用用最终849完整成功流程，未用776的部分失败片段代替。
- [固定修复合同静审](author-originals/contract-review/f2-csv-goal-confirmation-776d-static-review.md) 无剩余必须修复项；[6ed三阶段真实反例](author-originals/pre-fix-counterexample/counterexample-review.md) 是1 FAIL，三个空证据但可启用提交的反例均实际复现，CAS未发。

## 原件与限制

271份原始文件、51份 SQLite 副本按原路径和解码后 SHA256 列于 [ORIGINALS.json](ORIGINALS.json)。数据库、原始日志/XML及大文件用 gzip 保存，编码和存储 SHA 单列；全部解码后逐字节校验。[归档统计](archive-report.json)。保留正式日志、JUnit、真实请求/回执、完整页面输出、静态资源哈希、数据库、前后输入指纹及开发失败原件；不含 snapshot 源码副本、依赖或缓存。源码由两个精确 Git 提交重建。开发运行发生于修改中的 WIP，不能按最终 SHA 算通过。

作者10次新页面尝试共767个实际 API 回执，只有2个预期 CHECK 409。独立相应原件另有25个旁路 `/protocol/contracts` GET 400：选择性快照缺 protocol evaluation 资源；该缺失未在运行中补齐，逐条披露，不能声称全部 HTTP 成功。两方都保留2个预期 CHECK 409。原始失败、跳过、collection 错误与这些400均未从证据中移除。

这是合成数据下的 SQLite、ASGI/TestClient、完整产品 DOM/JSDOM、原 Worker 及旧 localhost 实际 HTTP 回归；JSDOM 不等于原生浏览器。未运行真实模型/真实语义或用户场景、Windows、PG、远端 CI 或部署。没有声明补回原旧满盘环境未落盘的独审报告；该历史证据缺口仍存在。下一功能未开始实现。

`SHA256SUMS` 覆盖本目录除其自身外的全部文件。最终远端 HEAD、原远端分支不变、干净 checkout 及未推送差异，以推送后 `/workspace/csv-goal-confirmation-return-evidence-20261017/final-delivery-verification.json` 为准；该含最终提交 SHA 的验证文件不放入自身提交，避免自引用。
