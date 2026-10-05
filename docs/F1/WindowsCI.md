# 有界 Windows Server 云 CI

2026-10-05审计修正：[子进程环境隔离本地修复](../evidence/F1-env-isolation-20261005/README.md)。旧df31fe9成功运行不证明owner凭据隔离：owner URL曾经GITHUB_ENV进入API/worker环境，现已本地移除并对白名单环境加真实子进程回归；PG114PASS、修复后Windows NOT_RUN。认证尚未恢复，不重试push。下面111项为旧版本开发方归档计数；审计只独立确认远端commit及公开run成功，未独立重跑或读取需登录的日志。

范围：公共仓库dev/f1-foundation窄路径push；标准GitHub-hosted windows-2025，单job、15分钟上限、同分支并发取消；contents:read，无缓存/构建产物上传，无模型请求，API只绑定localhost。依赖安装与临时测试资源仅存当次job；不合并main、不创建Secret、不改Actions设置、OAuth、UAC、防火墙或预装服务。

最新运行[37282999147](https://github.com/T1doo/Sim2Act/actions/runs/37282999147)（df31fe9b4d4b27db601581cf9763a18d5f0f6366）PASS：首次py-launcher Setup、完整Windows版本锁清单/pip check、原生smoke、ruff、mypy12模块、PG工程111PASS/0FAIL/0SKIP/1已有警告（30.70s），Report与Cleanup成功。[本轮脱敏结果](../evidence/WindowsCI-lock-20261005/results.json)、[精确源码指纹](../evidence/WindowsCI-lock-20261005/source-hashes.json)。Windows Server不是Win11，Win11产品AT-01仍NOT_RUN/BLOCKED。

前轮37281883663（04e7b1d）PASS，111项（34.48s）；更早三轮[结果](../evidence/WindowsCI-20261005/results.json)和[指纹](../evidence/WindowsCI-20261005/source-hashes.json)完整保留。

首轮37280680166（067b6dd）FAIL：smoke误将资源创建HTTP201断言为200，回归SKIPPED；第二轮37281551463（7ab4cfe）smoke PASS、回归110PASS/1FAIL：Windows checkout把冻结原文LF转成CRLF。已修正精确201及V5原文-text属性，原文/manifest字节校验不变。两轮清理成功，历史失败未覆盖。

官方[镜像清单](https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-Readme.md)列有PostgreSQL17及PGBIN；服务默认disabled/stopped。使用预装原生二进制创建RUNNER_TEMP下临时localhost/SCRAM集群与随机job测试账户，不启动预装服务、不用Linux容器。启动使用PostgreSQL官方pg_ctl的Windows restricted-process路径，未自行关闭安全保护或赋予额外Windows特权。

执行顺序：

1. 记录真实OS caption/build、镜像、PowerShell、Python3.12 x64、commit、管理员/UAC上下文。首轮实测Server2025 Datacenter 10.0.26100、镜像20260925.250.1、PowerShell7.6.6、Python3.12.10 x64、PG17.11、管理员上下文true、EnableLUA=1；不能推导普通Win11用户通过。
2. 独立临时PG集群；确认没有.venv，实际py -3.12预检3.12.10 x64，由现有Setup.ps1首次创建venv、安装独立requirements-windows.lock与显式迁移；分离测试迁移角色和无DDL运行角色。随机口令只存在job临时文件/环境，日志注册遮罩，不上传产物。
3. 小型原生smoke通过实际Doctor/Start/Status/Stop、独立API-worker、权限DDL拒绝、幂等接受、注册resource.read/42回执、重启回读、中文空格数据目录。
4. 现有Test.ps1 Engineering运行静态检查与相关工程pytest；模拟模型，含合成MockTransport身份检查，不发真实模型请求。JUnit只作job临时计数，结果写Actions日志/step summary。
5. always清理自有API-worker、临时PG与job目录。被取消job最终由hosted VM销毁，不承诺其step summary完成。

复现：向该开发分支提交触及workflow/src/scripts/tests/锁文件的授权改动，打开对应commit的Actions运行。无需配置账号或GitHubSecret；文档-only变更不触发、不重复消耗runner。workflow固定checkout/setup-python为已核查官方tag的完整SHA，不使用larger runner、cache/upload-artifact action。

代码入口：.github/workflows/windows-native-mock.yml、scripts/WindowsCI.ps1、scripts/windows_ci_smoke.py。Windows测试child_env仅补SystemRoot/WINDIR/COMSPEC/TEMP/TMP必要系统路径，不继承用户凭据、不spoof os.name。

Win11剩余：目标Win11 build、普通用户/UAC权限、真实本机安装条件与六脚本首次安装/启停/恢复，需要另行原生实测；Server首次py-launcher分支现已实际通过。Mac本地后端、iOS/Android浏览器/触控也未从Server CI推导通过。真实模型独立验收已有证据，本CI不占用其调用预算。

Windows完整版本锁：33项运行/测试包及setuptools82.0.1/pip25.0.1，tzdata2026.5/colorama0.4.6均显式固定。原Linux requirements.lock字节不变。Setup仅安装锁内二进制包、不自动解析追加依赖，editable使用锁内backend及no-build-isolation；pip check验证依赖闭合，CI将实际metadata与35项锁加sim2act0.1.0精确比对，拒绝未知包/版本漂移。锁SHA256 a47e5137193a935ba825b213627c962dd315a657d43d087d07a240da208a9f66与Git源码匹配；editable源码由测试commit标识。[pip选项依据](https://pip.pypa.io/en/stable/cli/pip_install/)、[真实launcher依据](https://docs.python.org/3.12/using/windows.html#python-launcher-for-windows)。

复现限制：这是完整版本锁，尚未冻结下载wheel字节哈希或离线镜像；标准runner镜像和预装PGBIN可能更新，实际版本每轮记录。已有Starlette/httpx弃用与旧action Node20被强制Node24执行警告保留，不宣称Win11版本组合永久冻结。实际GitHub连接读取jobs/logs成功，无新增账号/权限/Secret。
