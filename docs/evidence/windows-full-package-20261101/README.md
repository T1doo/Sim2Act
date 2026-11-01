# 同版本Windows完整装配：构建、失败与修复

本轮是用户再次明确授权的普通免费Windows构建，不是重跑旧900秒批次。总运行预算不超过480秒。使用公共仓库标准Windows Server2025 runner，只做普通编译、原生模块加载、合成SQLite协议／后台检查；不运行桌面EXE、浏览器、PG或真实模型，不改系统安全配置、不用用户电脑、不改main／Release。

## 第一次真实Windows运行

源码 `57ecb98fafbe1d3b7369d2a8c56a3dbb59cb04da`；[run41322277031](https://github.com/T1doo/Sim2Act/actions/runs/41322277031)，job124894829879，15:38:52–15:40:47 UTC，共115秒。

四枚CPython3.12.10 x64扩展和wheel真实编译成功，非editable安装成功；逐模块PE32+／AMD64、PyInit导出、python312.dll导入、SOURCE_SHA与完整源码组合匹配；`_qualified()`、Source `available/current`和精确依赖版本检查通过。原生记录及二进制摘要在`attempt-1/report.json`，不是Linux交叉编译结论。

随后协议测试54通过、6失败、0跳过，所以停止，没有带失败继续装配；C#新Windows编译、最终私有runtime、全包与桌面均未在此运行完成。制品原件51425字节、SHA256 `80d7f92f580600d71d01f19cb76d364179ce4a1e3cb3b1bd5fa7dc536b39c868`，artifact13089955289。11份原始诊断已完整取回和核摘要，见`attempt-1/`。

## 六项失败的具体判定

1. `test_business_commit_success_ack_failure_is_not_a_rollback`：旧故障注入在业务`main.commit()`之后，重命名还被控制writer打开的SQLite文件。Windows正确返回WinError32，delegate未正常返回，生产代码正确分类`CommitOutcomeUnknown`；旧测试却期待`CommittedAckPending`。这不是产品丢失提交或应该绕开Windows锁。修正为在实际主库提交返回后，只对实际控制连接的后续ACK UPDATE施加SQLite authorizer拒绝；仍必须`CommittedAckPending`，再核持久收据、ACK恢复及delegate仅调用一次。另保留提交后delegate抛错的独立参数，必须`CommitOutcomeUnknown`，同样核不重放。
2. 五个`test_runtime_rejects_store_method_shadow_before_foreign_dispatch[tx/guard/owns_connection/frozen_contract/event]`：Windows锁定pytest9.0.2的`setattr` undo留下原bound method的实例属性。原C协议`lease_store_fields_current`明确禁止任何固定actor方法的实例影子，因此恢复后被拒是正确行为。官方pytest9.0.2 wheel SHA已核并实际复现`namespace_after_setattr_undo=['guard']`，见`pytest-902-undo-reproduction.json`；本地pytest9.2.0的undo则清理该key。修正为对实例字典setitem并精确撤销，外来方法必须拒，原bound method的实例影子也继续明确拒绝，foreign调用数仍为0；未改生产门。

修复后当前本地两文件43项通过；在实际锁定pytest9.0.2下，相关7个参数化反例全部通过，均0跳过，XML及原日志保留。这仍不是新版Windows通过，必须再核新源码。

## 下一验证与包身份

第一次已用115秒，剩365秒。完成必要独审后只对修复源码验证一次：job硬上限5分钟，编译步骤4分钟，内部子进程剩余门210秒；即使该job用满300秒，累计415秒仍低于480秒。不是原失败源码自动重试，不增加付费／安全权限。最终状态须按该次实际结果记录，不能预置成功。

控制器在成功wheel生成后立即保全wheel、候选manifest与原build.log，避免后续测试失败丢失已编译字节。最终装配只复用旧固定镜像中的1554个已核运行库／依赖文件，完整剔除旧Sim2Act和旧dist-info，再加入本次同SHA wheel和四pyd、同SHA C# EXE。旧依赖ZIP、内部manifest、全部文件和21个依赖的版本／provenance都必须匹配，不将重新压缩文件冒充原wheel。

最终私有Python必须在`-I -B`下再次实际核四pyd路径／二进制摘要／SOURCE_SHA／资格／ABI、全部22份发行元数据（21依赖+本应用），然后执行两次CSV=30/v1、15/v2、原键去重、EOF clean退出和首次同origin重开。普通PE导入表和未打包的系统DLL需求单列，不把它当delay-load/API-set或干净机器完整验收。正常桌面入口仍是原WinForms/WebView2 EXE，浏览器只是显式开发预览；不新增失败壳或换后端。

本地真实后台driver已完成上述CSV／同键／同origin／双EOF操作，相关本地70项回归通过；它只是触发前检查，绝不替代Windows最终全包装配。当前应用src、C和C#业务代码相较7bf基线未变，保持已修READY、权威续租、提交屏障与取消；本轮没有重新打Linux包。

## 传输与剩余边界

通用GitHub fetch拒绝job日志URL（400，未支持的参数端点）后不重试该调用；云端直接HTTP制品下载在代理CONNECT处403，未取得字节，该传输保持停止。随后发现并使用现有GitHub连接器的专用日志／artifact工具，正常已有应用授权成功；通过其返回的授权文件引用取回原件并核SHA，没有改代理、认证或权限。未发布临时签名URL到仓库。未来读回应优先这些专用工具，不再尝试已拒HTTP路线。

Windows本机正式传输helper是否恢复由唯一协调任务另行核实；文件未跨机共享，也未把本机连接当输入可用。本轮只能准备完整源码／包／manifest／摘要，不能绕旧传输拒绝、私自使用用户电脑或宣称桌面窗口已验收。

长写锁仍是已知未解风险：`advance_model`的W5后仍在写事务内调用`_model_settlement_read`重建post图并执行完整权限／回执／绑定复核。本轮只核源码位置，没有新的大型Cold性能计时，也没有删检查、扩大30秒租约／300秒截止或缓存授权PASS。正式PG、任意自然目标、Windows真实模型与当前桌面运行仍按各自证据边界保留。

## 第二次真实Windows终态与下一窗口检查

源码 `042ab21c4fa9c7e5ba70c4e2877fb7060d962422`，[run41325692393](https://github.com/T1doo/Sim2Act/actions/runs/41325692393)，job124905034942，16:19:01–16:21:32 UTC，151秒，SUCCESS。上述61项协议测试0失败0跳过；四扩展、私有runtime、完整同源包、两次CSV30/v1和15/v2、同键不重放、EOF clean退出及首次新进程同origin/principal重开均实际完成。原始日志、XML、完整清单及本地逐文件复核在`attempt-2/`。应用src/C/C#业务字节与7bf6fd基线一致。

完整包 `deliverables/windows-full-20261101/Sim2Act-win64-042ab21c4fa9.zip` 19,745,959字节，SHA256 `cc177eeb8815194a4f1e973e146ce7dd95c2949350745a296c4d6a9bfcd38027`。1779个清单成员及whole-zip、wheel/source/native一致性已独立复核，未含DB、私有env/私钥或托管token模式。此时原EXE尚未执行，状态严格为ASSEMBLY_AND_BACKEND_ONLY，不是整体交付。

本批累计115+151=266秒，余214秒。按用户新增独立窗口与截图要求，下一次仅对这份精确原包做普通窗口/登录/关闭重开与自身像素检查，job硬上限180秒；即使用满累计446秒也小于480秒。仅用已有交互桌面/稳定WebView2；缺失或拒绝则停止，不安装Runtime、修改sandbox/ACL/会话/显示设置、不启Edge浏览器/CDP，也不使用用户电脑。新的测试提交不改变已冻结包身份。结果须追加真实终态，不预置通过。
