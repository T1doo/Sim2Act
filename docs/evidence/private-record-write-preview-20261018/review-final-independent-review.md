# 私有记录试写：最终有限独审

结论：`LIMITED_PASS_PRIVATE_RECORD_WRITE_PREVIEW`。本片确实通过原工具与 Worker 将 JSON 持久保存到独立私有目标，未把新空业务实例或意图预览冒充写隔离；最终已读源码与原件未发现剩余确定 P1/P2。只对本次有界 T08 切片给有限结论，不签正式 AT17、完整 F2、LIVE 或发布。

执行源由 [145项冻结输入](../private-record-preview-final-20261018/source-freeze-qualified.json)及其逐字副本绑定，本人复算当前文件与副本相同、before/after无变化。wheel **957688B / SHA256 `993d022e17d445f76c8277f8fb65f92a00e1595b58323e8dbff9db708691facc`** 的141包文件与源码、安装目录逐字相等；旧包仅 local-records.js 不同，全部Python相同。无Git/远端操作；尚未背书后续本地提交SHA、打包或推送。

作者最终原件为 `/workspace/private-record-preview-final-20261018`：MANIFEST文件SHA `00c71ecfa882bfa0364597ecbb693ec7a936332bf60f769637515f07c0f8ec9c`；SEAL文件本身SHA `f6497f8a3c6abb4ee10d77195e1b589de5c0a421be528dc7fedf23ea6832e26e`。清单492普通路径/27606087B中，本人重算484非DB文件SHA，8个DB仅stat大小，核8条符号链接目标。两种清单/封存文件hash不混称。

## 实际资格与独立复算

- 最终安装代码API 6个pytest通过（46.54s，112条ASGI响应）；最终安装页面1个pytest通过（40.95s），75项页面检查、2次boot、106页面动作（96GET/10POST）、54静态资源，连同14个fixture检查共174条ASGI响应。状态为152×200、11×201、5×202、5×400、1×403，不能称所有HTTP成功。旧普通记录2个API回归通过（15.53s），按全部Python/相应测试未变桥接，未重跑。共9个唯一节点的分批有限资格，不是75个用例或同批9全绿；作者未提供最终JUnit文件，本人依据闭合pytest原stdout、逐例HTTP/proof与已执行源码核验。
- 本人对实际页面、IPC与ASGI请求/响应文本逐字SHA签名对照，核54个served asset字节。真实201后受控丢创建回执，切第二个既有业务iid不能解除原UNKNOWN；只一条private创建POST，原key显式GET恢复同一私有空间。双创建锚、Run scopeFP、原Operation/Intent/Receipt、typed与私有对象元数据/hash逐项核对；私有CREATE→DONE两次页面Worker成功，冷页读取同原Run与DONE@2，4217B真实Blob以UTF8独立折叠history/records，SHA `da8fa84d9914fcdc43e49a1abffbf8601bf29cd0c6962ddc956abf116b044503`。
- 独立比较作者导出的55表全部JSON：私有阶段所有既有行逐字保持，只增加13类精确私有账本行（含2个app_previews对象、14条双锚journal、2个Run/Operation/typed）。resources/grants没有变化，另一个业务实例保持。后续明确重新填写、确认的普通业务Run才新增1个资源与2条派生READ；私有集合不变。最后额外私有QUEUED Run只增加控制/受理账本，fixture明确撤一条原WRITE Grant（revision+1），正文403清空→显式metadata GET→一次cancel，最终CANCELLED/version2/fence0，无Attempt/Operation/typed或新对象。页面3次Worker成功，加事前fixture1次；被取消Run未claim，均NoModel。
- API原件另证独立私有插入确曾发生，随后注入失败整体回滚：app_previews/resource/Grant/Operation/Intent/effect/typed/iid原行相同，只保留FAILED运行状态、事件和Worker心跳；不将失败状态说成全库零变化。外账号API403、私有/其它空间拒绝与普通资源/旧提取入口拒绝实际可读。正文SELECT屏障具有测试内正向校准assert，但正向SQL在clear前未另存；本人只重核保存的拒绝SQL和实际执行oracle，不冒称亲跑或完整重建SQL日志。

## 发现闭合、历史与限制

原撤权后停止不可达P2、刚接受QUEUED Run不在旧projection的第二遗漏、CREATE_PRIVATE错误按偶然iid过滤未决锁，均保留原静审报告；第二遗漏曾由实际TypeError证实；第一缺口据源码路径发现。最终专用owned元数据GET不读正文，清理保留同实例已验证受理hint，仅取消；切换代次隔离。第三项改为App/Release创建作用域并清旧确认，最终丢201→换iid→原keyGET已动态覆盖。

旧70检查作者目录原封为SUPERSEDED，不计作当前源资格。旧6个setup ERROR（缺evidence fixture）、两轮各5PASS/1错误状态码预期、旧UI P2失败均保留；新版首次UI驱动误以为丢回执后还保留正文，实际应清正文，修正仅测试后最终PASS，未改签失败。构建前两条失败路线保留；实际仅现有Python3.12/setuptools84、no-index/no-isolation wheel通过，pin82.0.1构建NOT_RUN。focused mypy旧3/新4文件同4条tools错误；更宽baseline28错/9文件，不能称类型检查全绿。我的文件观察器语法、形状、旧源切换、检查标签和输出旧计数错误也全保留于 [observer-corrections.json](observer-corrections.json)，修正只做纯文件核验，不计新pytest或产品失败。

本次是源码静审与闭合原件独立计算，未亲跑产品/测试/Worker/SQL/DB/网络，未读私有holdout。55表是作者特权导出JSON，不是独审打开DB重建。动态覆盖是SQLite/test_only/ASGI TestClient+IPC/JSDOM；跨账号页面仅静态，实际迟到覆盖跨实例、项目/工作区ABA和同账号重连。冷页内容读取在撤权前，撤权后只签本页已核Run停止；不签冷页撤权恢复。缺半创建锚实际拒绝，其它删改/混合锚变体仅按源码判断，不扩大为已跑矩阵。PG/Windows/native/远端CI、真实模型/语义/人工签收、生产来源与正式发布均未验；旧满盘最终独审缺失仍未补回。

机器原件：[final-verification.json](final-verification.json)、[final-artifact-audit.py](final-artifact-audit.py)、[最终stdout](final-audit-final.stdout)、[输入hash](final-audit-inputs.json)。本目录最后按所有普通文件及链接生成独审封存清单，封存后停止写入。
