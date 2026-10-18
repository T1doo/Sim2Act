# 未安装 sender/capture v2 设计独审

**设计可继续离线实现；下列请求/响应和原子边界应落实，不是要求真实 source/LIVE 才能写代码。** 基线 `94fa765de11e1e3cc42dac9070a28ec9c2b47647` 已只读核对clean。现有 journal/InternModel/exact-wire/capture 能力已存在，本片真正新增的是同一 coordinator 的 reserve→不可逆marker→唯一adapter调用→capture+结算原子接收链，不重复重造执行器。

本审只读设计v2、Worker/configured_provider/InternModel、原pa_trial_dispatch与journal；无产品/pytest/HTTP/网络/DB/SQL/模型执行，无仓库或旧sealed写入。本新目录未seal，代码/资格尚未出现，不预写PASS。

## 准入与实际 adapter 复用

严格入口至少在reserve前及wire_guard内再次确认：明确test_only SQLite、原Worker及store/id/设置绑定、Worker.s仍mock/livefalse/token空、exact MockTransport且与provider.transport同一对象。provider仅由现`configured_provider`创建，不接受caller provider/callback/endpoint选择。固定provider/store/worker/transport绑定应留在本次closure，不让回调修改可变Worker属性后另选身份/数据库。

`goal_planner.py:206–219` 的既有synthetic adapter会内部replace设置为live_enabled=True/token固定synthetic占位，原Worker.s不变；这只允许确切离线MockTransport演练，不是新LIVE设置或有效生产凭据。`Worker:29–43` 自身仅isinstance检查，故新入口仍需type精确检查及token空等更窄门。没有Settings.from_env、真实credential或生产source发行者；构造ALLOW仍不是权益事实。fixture实际Run应claim原Worker.id，不能将另一个worker的已领Run当身份资格。

## 请求和响应必须独立核原字节

1. wire SHA/长度只能证明所传字节一致，不能证明请求语义遵守合同。`InternModel._request_serialized:210–229`只核settings.model，不解析wire中的model/stream/max_tokens。建议reserve前用原strict_json解析一次，核实际body.model==原contract.model、stream is False、max_tokens为精确非bool正int且≤原cap，并保持原wire不重建。endpoint/POST/body精确核仍在wire_guard。否则离线演练可接受一个超原cap的真实serialized envelope，不能用来证明发送边界。

2. 接收端只从同一次actual adapter返回的body bytes派生hash/bytes、canonical ASCII及usage，忽略CapturedResponse.parsed与caller Outcome/tokens。原`normalize_usage:125–139`保known分量及partial/null。复用`parse_response:50–121`核choices/finish_reason/business error，再`returned_model_identity/require_returned_model:22–47`；只有合法JSON+usage+model并不足以判正常响应。

3. accounting facts与response verdict分离。坏体、错model、拒绝/截断或adapter错误即便含完整known usage，也不能产生`Outcome(RECEIVED,known)`而被原policy._known接受。capture应记录独立verdict/omission；以UNKNOWN拒接受，同时保真实known usage分量，不补零。缺body/invalid canonical geometry应明确unknown/omission，不把不存在的供应商正文/费用当已知0；raw sha/bytecount只描述实际已保留字节。

现deadline adapter在429/非200时会先raise再读body（model.py:272–300），通常只留下empty/incomplete `_received_body`；本片如实保omission/UNKNOWN即可，不声称已捕获这些错误完整body，也无需扩旧adapter错误矩阵。

## 一次协调、取消与崩溃

reserve的任意原key重复（含未marked pending）即历史退出，这一规则必须位于构造/调用adapter之前。只有本次新reserve且本次新marker成功的coordinator才可进入一次wire_guard；duplicate marker不能转成可缓存send权限。wire_guard对可信当前ledger/slot完整identity/wire/marker/unsettled及currentRun/source重新验证，nested closure只服务同一次adapter请求。

marker commit后、guard前cancel：guard拒绝，handler0；保marker、占槽和UNKNOWN/halt。guard退出至IO之间没有数据库原子保证，v2已正确承认可能出现一次合成handler；后续只记录received事实、acceptedfalse。不要以这个fixture声称生产网络可被取消回收。

两个实际退出窗口是新必要资格：marker后adapter前；body已由handler返回但capture事务前。os._exit/故意异常退出码与pytest PASS分别保存，持久marker和独立sidecar计数应明确flush；恢复进程dispatch原key只读，不因缺archive推断没发/费用0或自动重发。marked但无settlement应明确属于结果未知；保留null而不为凑Outcome伪造received数据。旧12仅新进程读证明不替代本次退出证据。

## 接收事务与锁

抽journal私有`_apply_in_transaction`时必须要求已有TX、无nested Store.tx/commit，保持原public wrappers签名/身份/expected_revision/duplicate/active最后fresh不变。接收事务按既定owner/project→account→ledger顺序；先原owner/scope/wire/marker及Run identity标量核验，再访问私有capture原body，随后固定capture pair和原四镜CAS同commit。capture不在公共事件或receipt输出body/header/token。

迟到cancel/revoke/expiry/fence失效不可阻止保存已接收body/usage；此时fresh失败只使接受false/halt。真正SQL/CAS/副本完整性错误则六行整TX回滚。已settled却缺capture、orphan/partial capture、body/verdict/Outcome不一致均failclosed，不回填或替换证明；完全相同capture/settlement重复只读，不推进revision、不UNKNOWN→KNOWN、不造新Attempt。

## 必要资格范围

v2的7节点（最多加一个partial/null）足够：正常actual InternModel→MockTransport一次及原key重复；新入口production/config/foreign transport拒绝且零预留；两个cancel窗口；两个实际进程退出窗口；capture写后journal CAS失败六行回滚。若用第8项，限定原bytes partial/null事实。原19/12不重跑、不并入分母，不扩其他lease/fence/response故障矩阵。

必须分别报告“实际adapter到MockTransport”和“真实模型/网络0”；旧guard不能禁止所有InternModel方法又宣称本片有调用，run/child guard应只容许本次确切provider+MockTransport并阻真实HTTPTransport/env发现。source/cold完整业务链、PG/Windows/native/CI/真实权益费用语义保持未验。

当前设计无必须先扩大权限的阻断；建议先落实上述边界再静审实际代码。未来生产source/Permit/受审sender仍未安装，v2不能自升级为LIVE。
