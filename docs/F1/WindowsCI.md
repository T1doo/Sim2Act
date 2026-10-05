# 有界 Windows Server 云 CI

范围：公共仓库dev/f1-foundation窄路径push；标准GitHub-hosted windows-2025，单job、15分钟上限、同分支并发取消；contents:read，无缓存/构建产物上传，无模型请求，API只绑定localhost。依赖安装与临时测试资源仅存当次job；不合并main、不创建Secret、不改Actions设置、OAuth、UAC、防火墙或预装服务。

首轮运行[37280680166](https://github.com/T1doo/Sim2Act/actions/runs/37280680166)（067b6dd）FAIL：原生PG/Setup完成，smoke误将资源创建HTTP201断言为200；工程回归SKIPPED，清理成功。修正断言后待复测，不能预写PASS。Windows Server不是Win11，Win11产品AT-01仍NOT_RUN/BLOCKED。

官方[镜像清单](https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-Readme.md)列有PostgreSQL17及PGBIN；服务默认disabled/stopped。使用预装原生二进制创建RUNNER_TEMP下临时localhost/SCRAM集群与随机job测试账户，不启动预装服务、不用Linux容器。启动使用PostgreSQL官方pg_ctl的Windows restricted-process路径，未自行关闭安全保护或赋予额外Windows特权。

执行顺序：

1. 记录真实OS caption/build、镜像、PowerShell、Python3.12 x64、commit、管理员/UAC上下文。首轮实测Server2025 Datacenter 10.0.26100、镜像20260925.250.1、PowerShell7.6.6、Python3.12.10 x64、PG17.11、管理员上下文true、EnableLUA=1；不能推导普通Win11用户通过。
2. 独立临时PG集群；现有Setup.ps1安装锁与显式迁移；分离测试迁移角色和无DDL运行角色。随机口令只存在job临时文件/环境，日志注册遮罩，不上传产物。
3. 小型原生smoke通过实际Doctor/Start/Status/Stop、独立API-worker、权限DDL拒绝、幂等接受、注册resource.read/42回执、重启回读、中文空格数据目录。
4. 现有Test.ps1 Engineering运行静态检查与相关工程pytest；模拟模型，含合成MockTransport身份检查，不发真实模型请求。JUnit只作job临时计数，结果写Actions日志/step summary。
5. always清理自有API-worker、临时PG与job目录。被取消job最终由hosted VM销毁，不承诺其step summary完成。

复现：向该开发分支提交触及workflow/src/scripts/tests/锁文件的授权改动，打开对应commit的Actions运行。无需配置账号或GitHubSecret；文档-only变更不触发、不重复消耗runner。workflow固定checkout/setup-python为已核查官方tag的完整SHA，不使用larger runner、cache/upload-artifact action。

代码入口：.github/workflows/windows-native-mock.yml、scripts/WindowsCI.ps1、scripts/windows_ci_smoke.py。Windows测试child_env仅补SystemRoot/WINDIR/COMSPEC/TEMP/TMP必要系统路径，不继承用户凭据、不spoof os.name。

Win11剩余：目标Win11 build、普通用户/UAC权限、真实本机安装条件与六脚本完整首次安装/启停/恢复，需要另行原生实测。Mac本地后端、iOS/Android浏览器/触控也未从Server CI推导通过。真实模型独立验收已有证据，本CI不占用其调用预算。
