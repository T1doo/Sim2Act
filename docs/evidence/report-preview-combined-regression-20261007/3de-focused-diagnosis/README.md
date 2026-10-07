# 一次 PG 定向诊断：3de10cca

精确 source `3de10cca0e12ecd506bbd3fc802861062b267690`，225追踪源码文件及隔离解释器/clean child来源预检见 preflight.json。仅执行一次两个case，14:32:05Z开始、14:33:24Z自然结束，1 PASS / 1 FAIL / 1 warning，77.56秒；原Node90秒及全部49检查/14POST断言均未改。完整-ra/durations30、JUnit及controller保留。

named Report case通过：18 driver检查、6 Mock请求、LIVE0；ORDER BY id后的完整principal/grant行比较通过。旧e4权限比较失败的原始行映射未留存，所以不回溯宣称其已证明只有排序原因。

ReportManifest case在第38个检查后，bad-open showApp的预期VERSION_CONFLICT拒绝没有发生（line50），51.907秒case终态；本次不是90秒超时。driver-progress.jsonl完整598行，仅含路径/状态/序号/时间，无request body或response。driver-failure-safe.json保留错误、38项检查及加载源码hash，不复制原requests bodies。

实际补充sidecar观察为6 RECEIVED：source2 / extract1 / cold3；7是完整49检查最终预期，尚未到达。旁账不替代fixture数据库实际回执；fixture已自动drop，未重造持久结果。根已独立定位2.5秒poll与explicit showApp竞争全局fault mode的post-await消费，下一修片将增加request-start定位；本片不改fixture或产品、不再运行。**旧e4 Node90超时原因仍UNKNOWN**，其7 RECEIVED另存e4-full-failed，不能由本次竞争诊断推断旧超时原因。

限定清理已完成：专属schema/role/public table/controller及children全部0，精确自有label容器已删除，private DSN、原private日志/JUnit、focused tmp及旧private sidecar tmp均删除。其他owner资源、共享venv及源码未动。LIVE0，无push/CI/权限扩大。后续仅等待新源码冻结及明确GO，不自动重试。
