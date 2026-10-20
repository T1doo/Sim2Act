# 文档 ACK：仅确认 BLOCKED / 不可启动

ACK。已只读核对 README 唯一要求修正的字段：`receipt.verification=SPEC_PRODUCTION_CONTROLLER_ARCHIVE`，`Capture.provenance=SPEC_PRODUCTION_CONTROLLER`，现与源码字段一致。更新后的 MANIFEST 所列 4 项 bytes/SHA256 全部匹配；原独审副本此前已核一致。

文档准确保留：从新上下文构造起 sender/模型为 0 时，没有找到受支持的原真实 G0 前置构造路径；当前没有 harness、没有新目录或执行，执行预算为 0。120 秒 + TERM5 + KILL5、64 MiB 仅是条件设计，尚未实施/enforce。本 ACK 只确认 BLOCKED/不可启动及设计证据口径，**绝非 runner 批准、可执行预算、重跑或新窗口授权**。

原正常边界仍要求 Cold 接收归档后进入真实五函数、原 second guard 与 scope closure 完整结束后才可称 G0 完成，W5 前截止；不能把 first commit 返回冒充 G0 end，不能用旧库改时/续 lease/伪来源绕过阻塞。独立双求和新材料项仍只是已有原计划产品缺口，未实施/测试。

本轮仅文档与清单只读核查，未重新核环境，未导入/执行产品、测试、producer、Worker、sender、模型，未打开数据库。

冻结文档 SHA256：

- README.md: `f8b38eb4952accf850f7995832ee51319c92fca14afe7e3d3051f71540c56637`
- design.json: `8eb3c5b739e968c04eec58aac569ad7eeee30420dbc367943cf8ab606b14977f`
- MANIFEST.json: `0b7546a85d787c47d8df0e4de229b04d3fc4c69a7d13f60147c625512fcff4fc`
