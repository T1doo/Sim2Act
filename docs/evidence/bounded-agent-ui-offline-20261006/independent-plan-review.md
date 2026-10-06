# bounded-agent UI 实施前独立审查

基线 4e7010b3a5e2697fa3bf45a53e0b992f71f6f7c5。计划范围可实施：接既有认证、Release/Instance/AppRun 和只读 literal checker，不扩 Grant、工具、身份、表或发布能力。此次仅静态设计审查，没有执行功能测试、网络、模型或浏览器；不是对尚未实现代码的签收。

建议 HTTP agent 缺少 offline_replay 时在所属实例/当前 Release 授权验证后、创建 Run 前拒绝 INVALID_INPUT；CSV 带 Replay 同样拒绝。缺少执行适配器与原 CSV 领域输入错误不同，原 CSV 已接受后 FAILED 行为及 Python 显式 Replay legacy 可保持。

实施必要边界：两条有限 JSON wire response 共享严格形状和 UTF8 字节上限；不接 client gold/provider 选项。新 Replay 必须进入接受请求、binding 与 Run 三层指纹，冷读重建一致；旧无字段 binding 不能被悄悄补 Replay。冷 worker 从冻结值构造新 exact ReplayModel，即使 worker 配置其他 model 也不能覆盖或 fallback。每次实际 read/current grant 与 checker 保持，sample 审批保留 input/output/protocol 证据，semantic UNKNOWN 不改。

UI 文件读取与审批须绑定独立输入代次；term/file 改变立即废弃批准，并阻断旧 await 回写。原请求重试保存原 term、Replay、key 的不可变副本；不能用改后的表单覆盖 pending 意图。token/project/app/instance 选择更换清除受保护材料，每 await 后重验；到期批准不可提交。agent 引用用 textContent，CSV 原路径回归。

完整检查与源码哈希见同目录 JSON。原生浏览器/SUID 阻塞不是本审查独立执行结果，后续 HTTP/jsdom 应明确独立等级、截图 NOT_RUN；不得用 CI 或改变 sandbox 绕过父检查。
