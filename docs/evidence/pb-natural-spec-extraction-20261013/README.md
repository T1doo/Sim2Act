# 自然规范 P-B：最终交付证据

有限工程终态：**155 个唯一 PASS、0 FAIL、0 SKIP**。作者 152 项；独审 5 项，其中 2 门禁重叠，新增 3 个实际冷复用正向。完整通用语义/人工验收仍 UNKNOWN/PENDING，真实模型请求/费用 0。

- [独立闭合报告](FINAL_CLOSEOUT.md)与[机器汇总](FINAL_CLOSEOUT.json)
- [五项冻结独审](INDEPENDENT_REVIEW.md)
- [作者唯一分母/全源码映射/失败历史](FINAL_VALIDATION.json)
- [五种实际 HTTP/JSDOM 场景，89 检查](FINAL_UI_VALIDATION.json)
- [74 文件精确资格](QUALIFICATION.json)与[7 个封存目录完整性核对](SEALED_MANIFEST_VERIFICATION.json)
- [完整原始证据包](complete-evidence.tar.gz)、[逐文件 SHA256 清单](SOURCE_MANIFEST.json)、[包元数据](PACKAGE.json)

包保存 3160 个常规文件、原始 196214757 字节；包括命令/环境约束、stdout/stderr、JUnit、440 文件快照/映射、全部真实 SQLite 测试库/Worker/HTTP/JSDOM 原始材料、历史失败和 cProfile 非验收诊断。临时 pytest symlink 的原目标在清单中记录；常规目标文件全部保存，包不创建这些 symlink。

包 SHA256：`95dbaee934879f6cd44ea75ed2049e902f86729e56ffab470d742a981b4ee973`。解包后可将每个常规成员的 bytes/SHA256 与 SOURCE_MANIFEST.json 核对。包内源树与清单相对路径一致，未改写任何封存独审目录。

产品核心 `e3b4fd84937c05e803f3017e8168130df1395cf8`、资格 `62aa9fd076b3714925f2301028c101d0141d5106`、最终夹具/冻结测试 `507b322e73758f4ad2ae2794382f5dee69760630`。120 回归的产品源码全同，只与最终 3 个 P-B 测试夹具不同；新版负向/页面/独审的完整 440 文件前后均同字节。45 份成功 Run 驱动日志各 1 实际 claim，恢复分支 NOT_EXERCISED，未调大 lease/原 deadline/预算。

历史失败未合并为 PASS。ruff（src 与新 Python tests）和三项 JS 语法检查 PASS；mypy 的 5 个既有错误明确 FAIL。真实模型/API、PG、Windows、原生浏览器、完整旧库升级、完整通用 P-A/P-B、人工业务语义/签收、CI/部署 NOT_RUN；原取消安装窗口 NOT_VERIFIED。Source 仍是当前授权的审计依赖；未知结果保留本页 pending，仅原 key GET 恢复，不宣称刷新后的自动请求发现或来源退休。

正常分支推送后的最终 SHA/远端和未提交未推差异另行核对，避免把自身 commit SHA 写入其内容形成循环。用户手动模型设置保持；实际模型/推理档/Fast/service-tier 不作未验证的切换声明。
