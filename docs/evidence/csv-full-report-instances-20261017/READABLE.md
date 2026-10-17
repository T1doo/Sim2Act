# a05 原始证据的可读副本

本补充仅修复交付证据的可读取性，不修改产品、测试、原 tar 或原始记录。129个UTF-8文本原件从原归档逐字节复制；每件SHA256/字节与原155件完整清单相同。其余26个二进制原件仍保留在原tar，未伪装成文本。没有补造JUnit或重新运行测试。

## 直接读取的原件

| 范围 | 直接可读原件 |
| --- | --- |
| 最终cc858可见页面、原Worker、完整MD、采用及cold Store后验 | [实际JUnit](readable/final-cc858-page.xml)、[HTTP请求响应](readable/final-cc858-page/test_visible_complete_md_inter0/actual-http.json)、[页面结果与加载资源哈希](readable/final-cc858-page/test_visible_complete_md_inter0/page-result.json)、[实际下载MD字节文本](readable/final-cc858-page/test_visible_complete_md_inter0/page-result.download.md) |
| d22权限三项及页面后验字段错误的原批次 | [实际JUnit，含原FAIL](readable/qualified-d22.xml)、[原日志](readable/qualified-d22.log) |
| d2独立后端两例 | [实际JUnit](readable/independent-seals/junit.xml)、[HTTP：类型重签](readable/independent-seals/pytest/test_release_numeric_type_cann0/actual-http.json)、[HTTP：重标历史](readable/independent-seals/pytest/test_successful_result_cannot_0/actual-http.json)、[独审证明](readable/independent-seals/final-review-proof.json) |
| d22独立丢回执与导航两例 | [实际JUnit](readable/independent-pages/junit.xml)、[丢回执HTTP](readable/independent-pages/data/test_visible_complete_md_inter0/actual-http.json)、[丢回执页面结果](readable/independent-pages/data/test_visible_complete_md_inter0/page-result.json)、[导航HTTP](readable/independent-pages/data/test_visible_complete_md_inter1/actual-http.json)、[导航页面结果](readable/independent-pages/data/test_visible_complete_md_inter1/page-result.json)、[独审证明](readable/independent-pages/independent-proof.json) |
| 两次新CSV、原键、批准/CAS和旧历史的主后端批次 | [HTTP请求响应](readable/backend-pass-candidate/test_complete_md_internal_rele0/actual-http.json)、[实际日志](readable/backend-pass-candidate.log) |

MD副本保持原UTF-8字节、换行和内容；下载Blob的实际字节/hash核验在对应页面结果中。此处不把Markdown渲染后的外观当作Blob证据。HTTP和页面文件均为原有合成夹具数据，无真实用户数据/模型调用或生产凭据。

## 完整哈希与冻结输入

- [原155件完整清单](raw-inventory.json)：包括二进制原件的原始哈希。
- [本次完整复制清单](readable-manifest.json)：129个文本的原member、路径、SHA256和字节，以及仍在tar内的26个二进制member。
- [610个生产/测试冻结输入](readable/code-freeze-cc858.json)：生产冻结 `cc85862a98b983b1665e9676640a8817e5840b1f`；a05只增加证据。
- [d2至d22字节桥接](readable/post-backend-byte-bridge.json)、[d22至cc858仅局部import排序的AST桥接](readable/import-order-only-bridge.json)。
- [独立页面656份输入前](readable/independent-pages/source-before.json)、[输入后](readable/independent-pages/source-after.json)。其他独立完整输入及原件清单保留在对应readable子目录与本次清单中。
- [分批覆盖说明](coverage.json)：17个唯一定向用例有通过证据，并非单次最终SHA的17项全绿套件。没有JUnit的原批次只提供真实日志/HTTP，不新造汇总JUnit。

## 原最终推送核验的缺口修复

[final-delivery-verification.json](final-delivery-verification.json)现已纳入提交。它逐字节复制自此前实际保存的 `/workspace/csv-full-report-instances-evidence-20261017/final-delivery-verification.json`，记录当时a05的远端同SHA、工作区干净和0/0提交差异。原清单/tar确实没有此文件；本次明确补入既有记录，没有重写其中时间或SHA。这是a05的历史核验，不声称它是本补充提交的新推送回执。

原开发期FAIL、SQL空探测观察器误报、修正后的真实PASS以及原缺失旧满盘独审报告的说明均保留；未把任何静态复核、后验重分类或语法检查当作新运行通过。

原 `evidence-checksums.json` 保留为a05历史清单（其中README哈希对应a05版本）；本补充变动及可读原件的当前哈希见 [readable-supplement-checksums.json](readable-supplement-checksums.json)，不覆盖原始清单。
