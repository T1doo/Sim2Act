# 冻结生产字节独立轻量动态补证

生产提交：`9b7d30b8f4aec699b1c3b9574b6dc6971ca4262e`。2026-10-16。仓库仅只读，所有本审查者输出位于 /tmp。生产六文件 SHA256 与 `/tmp/f2-first-natural-creation-final-9b7d-review.md` 一致。

实际命令：

```
/workspace/sim2act-venv/bin/python -m pytest -q tests/test_natural_first_creation.py::test_natural_first_creation_navigation_synthesized_api --basetemp=/tmp/f2-first-independent-9b7d-nav --junitxml=/tmp/f2-first-independent-9b7d-nav.xml
```

实际结果：RC0，1 passed / 0 skipped / 0 failures，15.16 秒；JSON PASS，30 项检查。一个已存在的 Starlette/httpx 弃用警告未影响结果。此节点是根线程在生产冻结后追加的测试，实际 driver SHA256 为 `3073933ddeb05e3a3af3d73787b08cb22126a79fcc1166d895bc026257dfc4b2`；不声称该新增测试本身已包含于 9b7d 提交。

实际覆盖：真实共享表单及首次向导脚本 + JSDOM DOM + 合成 API，workspace/project/identity/cancel 导航后的能力回调不建立意图/不 POST/不重启 guide；同 Goal ABA 仅释放旧读取锁、下一显式动作重新 GET；未知 Goal 回执重置不新增写入且结束 guide；合法 140 字符 Goal 的默认应用名限制为 100、完整 Goal 保持；取消恢复原共享 form 节点、格式/accept 与通用 Goal 控件。worker、real_model、native_browser 均明确 NOT_RUN。

原始证据：

- `/tmp/f2-first-independent-9b7d-nav.xml`，SHA256 `203457b33142af1b7f4576f17122461aea0684f32889696cfec69332e6d2ae30`
- `/tmp/f2-first-independent-9b7d-nav.log`，SHA256 `a5e650254ab5dbeecd4fc95b9cd4e1d2036045d0802b98f69ada60ac58d0667a`
- `/tmp/f2-first-independent-9b7d-nav/test_natural_first_creation_na0/navigation.json`，SHA256 `95ade2d282163c664377bbd6cfebe340b3cd866a60191ce8ab0db9e357dc1635`
- `/tmp/f2-first-independent-9b7d-nav/test_natural_first_creation_na0/driver.log`

当前有限结论：未发现行为或安全边界方面的剩余阻断。9b7d HTML 的原生成 fieldset 标题和首段仍只描述“字面引用/逐字匹配/不接受语义推断”，与新向导预置 natural 家族冲突；已向根线程建议在 HTTP 正例完成后做局部静态文案修正。应保留字面与自然家族的区别、自然语义待验和真实请求关闭边界。该文案修正后的 HTML 需单独记录字节和轻量结果，不应把旧完整 HTTP 正例宣称为使用新 HTML。

根线程仍在执行完整从零 PA HTTP mock 链。本独立轻量通过不替代它，不合并成一批完整绿色；未运行旧矩阵、Windows、PG、CI 或真实模型。
