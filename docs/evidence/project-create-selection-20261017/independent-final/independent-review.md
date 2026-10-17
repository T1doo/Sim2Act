冻结源 `2acb62e5bcc2c596bcb591d109433243691aeecb` 独立同3参数一次：3 PASS / 0 FAIL / 0 ERROR / 0 SKIP，JUnit 13.112s，RC0。无重试或额外节点；重复作者用例，unique+0。静态审查在本修改范围无新阻断：真实change及等待保留现有listeners，项目ABA/连接/列表代次隔离，旧回调只释放自身pending。

| Case | Checks | Product API HTTP / POST | Static responses |
|---|---:|---:|---:|
| create-save | 10 | 36 / 2 | 21 |
| late-manual | 6 | 59 / 1 | 21 |
| late-identity | 5 | 29 / 1 | 21 |

真实ASGI + 全served JS/JSDOM + 合成SQLite。create-save通过注入合成File、真实JSDOM FileReader解码和显式Save，确认返回B==当前B，资源POST/SQL均归B且UTF8/CRLF不变；pending的disabled click和submit仅1次创建。late-manual在POST及列表GET两阶段other→A，B可发现且不劫持；late-identity保持第二真实合成身份的项目/列表。原始result保留实际ID、options和响应；未记录单独门耗时，不声称该数据。

48表原行全保留，A作用域精确相等；新增project/runtime/grants及唯一保存资源仅归B，沿用服务器原授权政策。Worker/model均0，无Run/Release/approval POST。13文件前后匹配冻结Git，完整src无差异。44份原件见manifest/sums；21静态拷贝明确为Git源、匹配实际served响应SHA，非传输原件。

基线未独立复跑。父另批background在17b基线亦失败、未计通过，本审未执行/复核其原件。PG/native/Windows/原生文件选择器、模型/真实语义、CI、unknown创建回执恢复及其他矩阵均NOT_RUN。仓库只读。
