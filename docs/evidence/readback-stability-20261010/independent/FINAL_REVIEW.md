# 独立审查：LIMITED_PASS

精确冻结 `47388f573746daa27f8d5790ca358eef91378ad5`，base `754f0c61dab111ada2db69bfeb8e8cccdfe2ad95`。358文件before/after实际工作树与Git blob SHA256完全一致；69产品文件冻结一致。实际解析前dev `5427e9844e1d4731ba13987036bf91348d4df87d`：除report_presentations.py外68产品字节相同。scope完整原函数源码逐字节与base一致（SHA256 `5dad1c7872b7536b93e60d705d4684fafb9fee92d67ccfadb2467670d9a9940a`）。未改共享源/作者测试/分支或Git refs，未触作者PG/进程，没有真实模型调用。

## 实际独立范围

SQLite/API自编17用例，147具名检查通过。仅借用冻结Mock fixture建立来源材料，独立断言、Oracle、攻击、观测均自行编写。建立3定义、6checks、2个不同归档输出：原ALLOW及自己手写的另一BLOCK/解释。两次冷HTTP历史逐项核真实独立输出、decision、Run/result/version/fence绑定、精确definition/check键和保守验收flags，全DB快照均不变，SQL写为0。

自有进程观测：每次历史请求3个独立fresh scope、6个matching纯计算检查；fresh scope之后至匹配pure checks没有SQL，pure helper自身没有SQL。所有6个scope对象分别保留并核身份，跨定义/两HTTP请求没有重复；新增写check仍执行load scope和readback scope共2次，正确取第二个真实归档输出，仅写独立check/seal2行，其他全DB表不变。纯helper仅接收当前局部validated结果，无Store/连接参数，不保存跨定义或请求缓存。

反例均冷history与相应写入或受损检查精确重放拒绝且全DB/SQL零写：双seal与内check_fingerprint共同重签的假text、另归档输出/decision跨定义替换、不同check result_binding、不同definition result_binding、来源bytes与SHA256共同更改、other owner、同owner另一project、归档Run归属改变、source owner Grant撤销/过期、PROJECT peer来源改变、Report及PROJECT peer手工VIEW锁、Run version和fence改变。未把当前fresh history输出或一份patch的scope挪到别的定义。

另自编真实HTTP/jsdom2场景、4页、84检查通过：same-checks有效接受晚回执与实际接受后丢回复。真实原POST确认精确patch/key；原页面换代后通过当前GET恢复，零额外POST，busy解除、正确原text、冷重开零POST且不重复开放已完成检查按钮。实际加载每个HTML及12脚本均核冻结SHA256；script样式解释以纯文本显示且未执行。原6秒action/idle、90秒进程预算保留；GET无SQL写、canonical/其他非delivery_graph表不变。

材料只调用MockTransport：seed5次与两个UI fixture各4次，共13次合成交换；真实模型请求0。展示操作本身model_requests0、business_writes0。语义UNKNOWN、材料PENDING和整体NOT_ACCEPTED均保留。

## 首轮夹具错误及修正归属

初轮3个forge反例的history实际正确409，后续自编POST错误地使用全新未受损check key而断言应拒绝；原合同允许当前source/patch合法的新check201，此行为应保留，不是产品阻断，也不新增“全部历史无损才能写新check”全局门。完整保留backend.py/log/results与3初轮失败目录和当时DB JSON。只将这3用例修为受损existing check精确key/body重放，均409零写；backend-corrected及结果另存。又捕获3实际HTTPX r.request.content作为正文证据（corrected-exact-body-capture.json），不算新增unique用例或扩大通过计数。

## 未签范围

这是局部history同定义fresh scope输出纯计算复用的语义稳定性限定通过。不签PG、旧源码升级、native Windows900/Edge240/Node150、全部损坏HTTP200形式或整体项目通过。没有用自身有限通过或作者profile减少SQL/墙钟数据关闭历史失败：807 Report GET idle6 OPEN、resources-history Future10 OPEN原样保留，无根因结论。

PROJECT PENDING/BLOCKED_PARTIAL；semantic UNKNOWN；owner PENDING；overall NOT_ACCEPTED；LIVE=0。

证据根 `/tmp/sim2act-read-stability-independent-20261010`。FINAL_REVIEW.json提供精确范围与原件归属，COPY_WHITELIST.json含全部原始成功/失败日志、自编harness、合成DB JSON、scope/SQL证明、实际正文和358/69字节freeze。排除SQLite二进制、pycache，不引用作者测试通过作独立证据。
