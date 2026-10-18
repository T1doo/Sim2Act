import json
from pathlib import Path

repo = Path('/workspace/Sim2Act')
dest = repo / 'docs/evidence/pb-extraction-close-20261018'
summary = json.loads(Path('/workspace/pb-extraction-close-evidence-20261018/execution-summary.json').read_text())
package = json.loads((dest / 'package-summary.json').read_text())
source = summary['final_execution_source']
reports = {row['batch']: row for row in summary['reports']}
pages = [row for row in summary['pages'] if row['batch'] == 'qualified-ui-data']
metrics = {key: sum(row[key] for row in pages) for key in ['checks', 'actions', 'api', 'assets', 'boots']}
assert len(pages) == 2 and all(row['status'] == 'PASS' for row in pages)
assert summary['model_requests_total'] == 24 and summary['source_worker_calls'] == 6
table = []
for label, backend, ui in [('首轮 f0652b42', 'backend', 'ui'),
        ('第二轮 ce407aae', 'final-backend', 'final-ui'),
        ('最终 f7a48c06', 'qualified-backend', 'qualified-ui')]:
    b, u = reports[backend], reports[ui]
    describe = lambda row: f"{sum(c['result']=='PASS' for c in row['cases'])}PASS/{sum(c['result']=='FAIL' for c in row['cases'])}FAIL"
    seconds = lambda row: float(row['suite_attributes'][0]['time'])
    table.append(f'| {label} | {describe(b)} / {seconds(b):.2f}s | {describe(u)} / {seconds(u):.2f}s |')
readme = f'''# P-B 未受理原 key 安全关闭：有限交付证据

最终执行源码 `{source}`，普通分支 `dev/pb-extraction-close-20261018`，从父级有限通过的 `3d1a3160fda6e9bfead96fae8a40935617270da4` 接续；原远端8fc仍为可见祖先。root唯一仓库写入者，外部测试草稿/只读独审并行；旧满盘实例和bundle未使用。文档/原件提交不改变此执行字节。

新增可见按钮仅关闭原17字段票据所指的未受理key。服务端同项目事务重核成功来源和独立受理残留，写既有账本双封存；先受理则close409，先close则原/改body同key迟到POST409。普通POST与close均使用有界30秒SQLite锁等待；共享提取函数、trial controller、Store及PG策略不变。页面closePOST保原raw，另一次显式原GET核独立17字段、完整CloseInput和15字段receipt实际SHA后才忘记票据。新key仍需用户重新审阅/确认，无自动重发/新执行器/新Grant种类/模型调用。

## 实际资格及原失败

| 冻结 | 后端7节点 | 页面2节点 |
| --- | --- | --- |
{chr(10).join(table)}

最终9个唯一节点全通过；三轮共27次节点执行，最终通过不覆盖前两轮3次失败。每批外层900秒、页面自有Node900秒，实际exit和原JUnit分别保存。三轮各685项输入运行前后0漂移，133项生产；f065→ce仅close等待与测试精确撤权码，ce→f7仅普通extract wrapper等待变化。

首轮post-first中原POST201、等待close500，第二连接未完成SQLite BEGIN IMMEDIATE；实际403 GRANT_REVOKED被测试硬写为PERMISSION_DENIED导致另一次失败。只修close等待后，第二轮反向close-first出现POST500、close200，同样为未获锁。最终对称30秒等待修复两个普通HTTP入口；不改业务时钟/lease/deadline，不假装任意重负载永不超时。超时或403/404仍不能证明未受理、不能清票据。全部原件保留。

最终页面合计{metrics['checks']}检查、{metrics['actions']}交互、{metrics['api']}页面API、{metrics['assets']}实际资产、{metrics['boots']}个完整DOM；{metrics['api']+metrics['assets']}实际HTTP不含两个seed的HTTP。覆盖pre-API受控失败→闭旧页→冷页未知→closePOST保票据→另原GET核验→真实完整terminal SHA已计算后受控延迟投递/关闭旧面板不忘票据、不paint→重开显式GET→fixture一次投递原exact UTF8 bytes409→用户明确新审阅/确认201；另例实际201后受控丢回执，冷页close409后原GET/fresh app恢复，原受理保持。每boot实际服务27资源逐hash核对。受控网络投递/真实SHA结果投递不冒充原生网络并发。

后端包括真正两个独立DBAPI连接/线程：第一项目锁已持有、第二BEGIN实际尝试但未完成时证明重叠，再释放，分别取得close200/POST409及POST201/close409。另验冷Store持久/幂等、目标后来失效可关闭、已受理不可取消、完整accepted sibling允许不同key关闭/其目标READ撤销后保守UNKNOWN、跨主体/项目/来源/严格17字段、单半封存及错位PK/多余半账本/受理残留与插入后失败回滚。故障注入仅改明确合成已受理记录，不伪造成功。

六个独立正常fresh来源seed，每个正常生成3Mock+来源Worker1Mock，实际本阶段总24Mock、6次来源Worker/各一次真实claim；case/页面Worker0、真实模型0。DB关闭后逐字复制，旧行/原来源claim和clock及新app/runtime/既有2Grant/原4journal精确增量均留证。页面新app未运行，语义UNKNOWN/人工PENDING保持；不能称新的P-B运行语义验收。

## 独审、限制和原件

非作者静态独审发现并促成三处修正：授权前不得整行读共享marker；封存残留须用PK及独立wire锚failclosed；额外接受半账本不能被完整sibling掩盖。修前首次独立本地源码快照实际已赶上修后，修前证据仅可见工具源码/即时静态报告，未伪称保存了修前字节。最终源码/冻结映射与三轮原件由非作者纯文件复算，未新增产品复跑。独审自身首HTML响应解析JSON错误脚本和stderr保留，修正纯解析后继续，非产品失败。

当前读屏障动态覆盖resource/run等正文；完整journal/marker正文在target gate后读取是源码顺序独审，不冒称动态journal-cell屏障。已受理sibling失去目标权限会保守阻止本来源其它key关闭；每Run最多64关闭key及有界残留扫描。来源权限/版本不再有效时仍锁定，不以旧票据恢复权限。不承诺检测所有独立锚同时协调删除的任意DB伪造。

实际采用CJS SHA `5647ac9c97a1029d39a7572b2d2223315035b03df301b1dc29ac83c0a1257916`，后到ff50草稿未采用/未执行。Windows/native、PG、真实模型/语义/场景、远端CI、部署均未执行。本分支不触发现有仅dev/f1-foundation的push工作流。永久取消的旧安装digest窗口、旧exit139因果Unknown、旧满盘独审未落盘缺证保持，不声称补回。

- [完整计算汇总](originals/author/execution-summary.json)、[原命令/隔离范围](originals/author/execution-command-spec.json)
- [首轮backend JUnit](originals/author/backend-junit.xml)、[首轮UI JUnit](originals/author/ui-junit.xml)
- [第二轮backend JUnit](originals/author/final-backend-junit.xml)、[第二轮UI JUnit](originals/author/final-ui-junit.xml)
- [最终backend JUnit](originals/author/qualified-backend-junit.xml)、[最终UI JUnit](originals/author/qualified-ui-junit.xml)
- [可直接阅读的全部原件与大文本无损分段](READABLE.md)、[原件逐文件清单](raw-manifest.json)、[SHA256SUMS](SHA256SUMS)
- [有界合同/执行说明](../../F2/PBNaturalExtractionClose20261018.md)、[原始bundle](raw-evidence.tar.gz)

原件{package['raw_files']}文件/{package['raw_bytes']}bytes；bundle {package['bundle_bytes']}bytes，SHA256 `{package['bundle_sha256']}`。原始bytes、tar成员和大UTF8分段逐字复算。源码正常push回执在author原件；文档最终push/HEAD与remote/clean/0未推送证明另落外部最终交付目录，避免本提交引用自身SHA形成循环。
'''
(dest / 'README.md').write_text(readme)
contract = repo / 'docs/F2/PBNaturalExtractionClose20261018.md'
contract.write_text(contract.read_text() + f'\n最终源码 `{source}` 同9唯一节点已全部通过；每轮685输入0漂移。六fresh种子共24Mock/6来源Worker、页面Worker0、真实模型0；最终页面{metrics["checks"]}检查/{metrics["api"]+metrics["assets"]}实际HTTP。三轮原失败及非作者源码/原件复核、正常dev推送和范围见[交付证据](../evidence/pb-extraction-close-20261018/README.md)。Win/native/PG/真实/CI门仍未执行。\n')
plan = repo / 'docs/F2/Plan.md'
text = plan.read_text()
first, rest = text.split('\n', 1)
plan.write_text(first + f'\n\nP-B未受理原key关闭最终源码 `{source}`：七后端+两完整页面共9唯一节点当前通过，含两连接实际双向并发及独立terminal SHA迟到投递；三轮685输入各0漂移，共24Mock/6来源Worker、真实0。首轮后端5PASS/2FAIL、第二轮6PASS/1FAIL，页面每轮2PASS；原锁等待500与撤权断言错误全留证，最终普通POST/close对称有界30秒等待。非作者有限独审、原件和[交付范围](../evidence/pb-extraction-close-20261018/README.md)保留，未关闭Win/native/PG/真实/CI或旧取消门。\n' + rest)
print(json.dumps(dict(source=source, metrics=metrics, docs_written=True)))
