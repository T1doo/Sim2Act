# 2026-11-06 演示结果前置与 v5 封存

真实书生模型案例通过页面提交：活动交接记录 → resource.read 核验 → 模型执行简报。运行 `run_880358c6e2504a30a7b121e754c54517`，技术状态 PARTIAL，目标语义 NOT_RUN；没有把读取工具成功改成完整任务成功。原始运行和截图暂存在项目内 deliverables/video-model-demo-20261106，最终素材需经新包显示核验后整理。

发现原普通成果页先显示步骤和原文，回答被挤出首屏。app.js 仅将原 renderOrdinaryOutcome 提前到执行记录之前，保留状态、核查、原文、来源和全部操作；未替换或伪造结果。

当前控制 DOM 回归 frontend_day_ui / frontend_result_identity 均 PASS。这些是交互投影验证，不是浏览器或业务验收。

此前待封存的 v5 资格四文件仍针对 a0db14c5 已审 Python 字节；前端顺序变化不改变这些 Python 指纹。补跑 production_trial_admission、text_software_qualification、qualification_pair 共 97 项：96 PASS，1 项测试夹具失败，原记录 demo-v5-qualification.xml 保留。Windows 的 write_text 换行转换导致伪造清单字节与测试声明的哈希不同，提前命中哈希拒绝。将该夹具改成 write_bytes 保持测试自报字节后，原失败项复测 PASS，见 demo-v5-newline.xml。产品拒绝逻辑与授权规则未变。

这不是 v5 真实 P-A 成功证明；新包需继续构建与运行，原 v4 失败记录不更改。
