# 修后实现及定向测试源码：有限静态复核

2026-10-18，未冻结WIP，基线494cf2e1490967f8cf8621bb48b52fa00713436d。只读源码/Git，未运行产品、pytest/collect、HTTP、Worker/模型、DB/SQL或网络，未写仓库。目录未seal，原draft P2记录保留。

结论：**原P2静态收敛，未发现剩余确定P1/P2或测试设计阻塞，可进入冻结及计划定向实际资格。** 这不是实际测试PASS，不声称动态复现修前回调。

修复依据：production_evidence.py:89–129的_model_data限定raw声明字段全集、额外/私有存储None，_contract_data仅接exact primitive、内建list/dict与固定受信嵌套schema，未知对象不触及属性/serializer；requirements_for:139–153通过该数据再原parse_contract重建，只对新建受信original调用model_dump。原顶层或nested model_copy增加model_dump值在原字段集合门被拒；callback藏入声明字段也不属于primitive/白名单，先拒绝。V1/V2/PB现合同树使用的MaterialGoal/GoalSnapshot/SourceSnapshot/GoalCardInput、StageKeys/TrialCaps和Recipe/Step/FieldSource均列白名单；正常深度在16以内。没有接受任意模型子类、容器子类或注册安装入口。

原flat候选/requirements仍重新严格校验；未知bool、未知撤销或False/REVOKED/非RECEIVED均不当安全事实。匹配数据只返回SOURCE_UNVERIFIED/NOT_VERIFIED/livefalse/dispatchfalse的非权威Diagnostic，不返回AccountEvidence/FeeProof/Permit。唯一quota算法函数内import，当前模块定义阶段没有反向调用validate_candidate，未见循环导入阻塞。

preflight只增import及原_approved后的缺源resolver调用/注释；_qualified/admit原样保留但当前NOT_REACHED。新resolver不接任何记录/来源/registry/callback/发送器，恒缺源拒绝；旧offline._resolve和test_only隔离不变。缺来源先于具体Run/软件资格拒绝不表示这些条件通过，也未泄露新Run数据或授予权限。

测试源码已核：tests/test_production_evidence.py包含非权威完整候选、作用域与30秒/期限/unknown/False拒绝、严格primitive/paidcap/额外字段/无repr与callback、三原合同版本投影及顶层/nested shadow拒绝。末一节点使用真实认证API handler/ASGI TestClient（不是原生浏览器/远端HTTP），原精确approve及fixture claim后，两admission route各原请求两次恒400缺源，额外字段422、foreign身份/项目403、READ撤销后先拒且source调用数不增；原_qualified只观测未到达，provider/Settings.from_env为测试trap。55表原行在两个明确窗口内比较；撤销本身是窗口之间显式fixture变更，不能把它混称全程零变更。当前所有这些仍待实际执行，不提前签通过。

没有发现需要扩大源/资格pin/预算/租约/网络/真实模型或旧恢复矩阵的理由。真实生产来源与权益仍未注册/验证。

本次实际读取字节（不是Git freeze）：

```json
[
  {
    "path": "src/sim2act/production_evidence.py",
    "bytes": 9568,
    "sha256": "0276d55f8997ce1ad3f947f4a191f2ffcf7aee27f9f6093245b683a480aad3fa"
  },
  {
    "path": "src/sim2act/production_trial_admission.py",
    "bytes": 15124,
    "sha256": "a4afcbdd720d13ff9cde5e744ecb3d98b71e03e783217392a0ccaa2b006a85a9"
  },
  {
    "path": "tests/test_production_evidence.py",
    "bytes": 13287,
    "sha256": "81c9b1ea422c2d6a0b935d5799d1f6b652a1e44664123be22258ba00ae3347b9"
  }
]
```
