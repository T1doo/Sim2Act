| 用例 | bee40 / f41修前 | 修后实际结果 |
| --- | --- | --- |
| success | 均失败于既有完整图入口；原定组件断言未到达 | 五写原子提交、proof关闭 |
| source_revoke | 均失败于既有完整图入口；原定组件断言未到达 | VERSION_CONFLICT：Model settlement read segment or complete inputs changed |
| grant_expiry | 均失败于既有完整图入口；原定组件断言未到达 | GRANT_REVOKED：GRANT_REVOKED |
| raw_pair | 均失败于既有完整图入口；原定组件断言未到达 | VERSION_CONFLICT：Actual received response belongs to a different handoff |
| first_proof | 均失败于既有完整图入口；原定组件断言未到达 | VERSION_CONFLICT：Full postwrite proof rejected |
| reject_owner | 均失败于既有完整图入口；原定组件断言未到达 | VERSION_CONFLICT：Synthetic owner competition blocks rejection |
| limits_platform | 均失败于既有完整图入口；原定组件断言未到达 | VERSION_CONFLICT：Model settlement read segment or complete inputs changed |
| limits_node | 均失败于既有完整图入口；原定组件断言未到达 | VERSION_CONFLICT：Model settlement read segment or complete inputs changed |
| tail_reentry | 均失败于既有完整图入口；原定组件断言未到达 | VERSION_CONFLICT：Natural model evidence changed |
| output_drift | 均失败于既有完整图入口；原定组件断言未到达 | VERSION_CONFLICT：Model settlement read segment or complete inputs changed |
| failed_write | 均失败于既有完整图入口；原定组件断言未到达 | VERSION_CONFLICT：Model settlement read segment or complete inputs changed |
| tail_extra_expiry | 均失败于既有完整图入口；原定组件断言未到达 | GRANT_REVOKED：GRANT_REVOKED |
| row_mapping_drift | 均失败于既有完整图入口；原定组件断言未到达 | VERSION_CONFLICT：Model settlement read segment or complete inputs changed |
| source_identity_drift | 均失败于既有完整图入口；原定组件断言未到达 | VERSION_CONFLICT：Natural model evidence changed |
| source_deadline_drift | 均失败于既有完整图入口；原定组件断言未到达 | VERSION_CONFLICT：Model settlement final finite interval ended |
