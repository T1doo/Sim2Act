# 15项continuation失败：逐项对照与fixture修正

本轮没有修改生产源码。基线 `bee40b5fbe0a91519a8a5e9a3bc93bdbf5619db3`、修前 `f41d2ffe947cc5a239f2797459c88dff2dc7d85a`；实际测试fixture及34条有序原断言摘要见 `per-case-comparison.json`。不是把失败删掉或改成skip后称全绿。

## 实际基线对照

将bee40的Git对象导出为只读验证工件，不创建开发checkout或另一个writer。文件缓存写入关闭，数据库/日志输出单独scratch目录；C源码逐字相同后才只读引用原两枚扩展。实际Python导入来自归档，原143项资格检查通过，见 `continuation-baseline-import-20261030.json`。

| 运行 | 实际结果 | 范围 |
| --- | --- | --- |
| bee40原fixture，完整归档生产源码 | 15失败，0通过，21.68秒 | 原15项均复现 |
| f41修前fixture，实际f41生产字节 | 15失败，1通过，19.03秒 | 新增pending取消握手通过 |
| 修正fixture后 | 17通过，0失败，21.53秒 | 原15项、pending握手、生产类型门负例 |

各运行的原始日志/XML以gzip保留，命令/归档hash/实际导入路径另存。首次归档少了gold输入文件导致收集失败，该次记录也保留；补齐的是同一Git基线已存在的本地测试输入，不是修改基线或放宽门。

## 逐项判断与修复

原fixture明确把recipe/phase ancestry、sender、journal ledger和非trial guard作为单元stub，并用SimpleNamespace worker及占位instance/release。它却调用已升级为完整Cold祖先图装配的生产context：原exact Worker门先拒绝，预期组件故障多数没有到达。相同失败在bee40和f41均真实复现；两版本对应完整图入口和装配函数AST相同。它们属于既有fixture范围/入口假设错误，未发现由本轮WAL产生的新类型回归。每项修前原文、底层error、post-admission计数及修后实际错误/trace均独立列在 `per-case-comparison.json`，便览见 `case-table.md`。

修正采用**仅测试内的continuation组件装配边界**，不伪造Graph、不改生产类型门或资格判断。admission仍通过原spec.commit_guard/_model_out产生，输入来自真实SQLite当前行、原request/response archive和原限额；真实 `_ModelSettlementRead.check/live/settle/tail/tail_row`继续执行。authorities收集、raw配对、audit指纹、实际Run/Grant/时间校验保留。只有live通过后进入READY，SETTLED/TAIL_DONE仍由原生命周期方法产生，退出必须TAIL_DONE。

主用例仅把整体图装配的fixture引用指向这个明确组件边界；AST对照确认原34条有序assert完全相同，原15个故障注入段未改。真实advance_model五写、回滚、REJECTED_KNOWN/RECEIVED的区别、拒绝CAS、SQL语句顺序断言保留。新增负例直接调用生产 `_ColdGraphRead`，确认它仍拒绝SimpleNamespace，不能借fixture修正削弱正式入口。

具体检测仍来自真实proof：grant_expiry/tail_extra_expiry报GRANT_REVOKED；raw_pair在原归档配对处失败；first_proof在明确注入的post-admission处失败；source_identity/source_deadline分别在来源身份和有限期限处失败；limits/RowMapping/audit漂移及失败SQLepoch由完整输入或生命周期pin发现；tail重入由原状态机拒绝；reject_owner保留RECEIVED/DISPATCHED，不覆盖被竞争的拒绝回执。success仍实际原子完成五写并关闭proof。源码和逐项trace可据此定位，而非只报一个通过数量。

**组件单元不再声称覆盖完整Cold G1祖先、recipe或真实ledger装配。** 这些由原真实Worker完整P-B控制器独立验收，前一阶段四条大型输入证据在 `../cloud-cold-snapshot-20261030/`；新性能改动仍需独立大图验证。修正fixture不是完整产品或生产验收。

独立只读reviewer `/root/desktop_final_review` 已核具体adapter、34条原assert和实际前后日志，无剩余组件审查阻塞。无真实/Mock transport调用于这些continuation单元（全被明确禁止）；未调用用户电脑、第四次CI、PG、部署、main或Release。
