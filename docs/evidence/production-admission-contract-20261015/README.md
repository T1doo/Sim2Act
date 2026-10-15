# 生产准入与P-B来源合同有限工程证据

冻结源码 `206de555e22c9a6e85c1ea87a33c1e55c0780968`，339PASS0FAIL/ERROR/SKIP/deselected。同版339与独立探针不累加，真实LIVE默认拒绝。

[交付报告](../../F2/ProductionAdmissionContract20261015.md)。[归档哈希](ARCHIVES.json)；每包都有逐成员大小/SHA256清单，打包后逐字节读取并与原文件比对。

- [author归档](author-evidence.tar.gz) · [成员清单](author-MANIFEST.json)
- [pb-author归档](pb-author-evidence.tar.gz) · [成员清单](pb-author-MANIFEST.json)
- [regression归档](regression-evidence.tar.gz) · [成员清单](regression-MANIFEST.json)
- [review归档](review-evidence.tar.gz) · [成员清单](review-MANIFEST.json)
- [cold-probe归档](cold-probe-evidence.tar.gz) · [成员清单](cold-probe-MANIFEST.json)
- [integration归档](integration-evidence.tar.gz) · [成员清单](integration-MANIFEST.json)
- [cancel-diagnostic归档](cancel-diagnostic-evidence.tar.gz) · [成员清单](cancel-diagnostic-MANIFEST.json)
- [route-before归档](route-before-evidence.tar.gz) · [成员清单](route-before-MANIFEST.json)
- [route-before2归档](route-before2-evidence.tar.gz) · [成员清单](route-before2-MANIFEST.json)
- [route-fixed归档](route-fixed-evidence.tar.gz) · [成员清单](route-fixed-MANIFEST.json)
- [route-family-fixed归档](route-family-fixed-evidence.tar.gz) · [成员清单](route-family-fixed-MANIFEST.json)
- [route-local-fixed归档](route-local-fixed-evidence.tar.gz) · [成员清单](route-local-fixed-MANIFEST.json)
- [peer-lock-diagnostic归档](peer-lock-diagnostic-evidence.tar.gz) · [成员清单](peer-lock-diagnostic-MANIFEST.json)
- [peer-lock-diagnostic2归档](peer-lock-diagnostic2-evidence.tar.gz) · [成员清单](peer-lock-diagnostic2-MANIFEST.json)
- [budget-cleanup-probe归档](budget-cleanup-probe-evidence.tar.gz) · [成员清单](budget-cleanup-probe-MANIFEST.json)
- [pb-heartbeat-diagnostic归档](pb-heartbeat-diagnostic-evidence.tar.gz) · [成员清单](pb-heartbeat-diagnostic-MANIFEST.json)

regression/final47e保留137PASS1FAIL/180未完成/pytestRC2及494文件封印，不能称318完整通过。regression/local-atomic-probe为206独立35例，不能累加完整339。regression/final5ed保留完整314PASS4FAIL及494文件封印，不能拼接任何独立探针。budget-cleanup-probe为修正后1PASS，pb-heartbeat-diagnostic为正常P-B1PASS并保留证明边界。regression/final保留9f305PASS1FAIL；route-fixed保留a612PASS1FAIL；route-before保存首次受控probe setup ERROR，route-before2保存旧路由受控1FAIL；route-family-fixed为2cb13PASS；route-local-fixed为5ed14PASS。regression/final2cb保留主动中断的123PASS1FAIL、194未完成及runner解析错误，不能计为完整318。peer-lock-diagnostic保留setup ERROR，peer-lock-diagnostic2为2cb正常时钟1PASS且未重现历史。integration含精确冻结/资格/collection/终态审计/旧失败DB只读摘录与全部运行脚本，review含原与恢复后独审。PG/Windows/原生浏览器/真实模型费用/可信真实权益解析器/生产sender/P-B真实归档resolver/完整真实P-A-P-B/人工语义/远端CI/部署NOT RUN或NOT IMPLEMENTED。整体NOT_ACCEPTED。
