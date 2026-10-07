# application_use JSDOM 生命周期 RED/GREEN

契约与范围见 [修复说明](../../F2/ApplicationUseJSDOMLifecycleFix.md)。只修改测试driver；所有旧产品和Python测试断言保留。

- RED e828 单次：1FAIL/2.13秒，原JUnit/pytest log以 `.gz` 原字节压缩保留；`gzip -dc red-e828-junit.xml.gz` 或Python gzip可直接读。不修剪原traceback空白，不把失败改为通过。
- RED de907：此前focused三项2PASS/1FAIL原JUnit，`red-de907-focused-junit.xml.gz`；其中同一application use驱动失败。driver stderr见red-driver.log（e828复现，当前相同堆栈）。原drive/hash可从精确de907测试文件取出。
- GREEN 1：1PASS/2.35秒，修复后初版。
- GREEN 2/3：最终相同driver连续1PASS/2.13秒、1PASS/2.32秒；每次独立临时SQLite，0FAIL/0SKIP，1既有Starlette弃用warning。原始JUnit/log与driver/results逐项保存。
- 独审：最终1PASS/2.26秒；independent-driver.log、independent-results.json为原始driver输出，另有30项check/4POST/两页pending/error为0。独审pytest stdout/JUnit **未保存**，该时长只来自审查工具输出，不冒称全套原始独审artifact。前版独审1PASS/2.42秒未作最终源替代。
- 独立负例：independent-negative.cjs从当前helper提取执行；同步throw/异步reject均原Error对象留在page.errors且idlePage抛同一对象，实际结果见independent-negative.log。负例不访问产品数据库/模型或网络。

每次GREEN含全部原29业务oracle及追加1生命周期oracle，原Python还实际校验3个Run/2个结果版本与完整Grant/Principal行。测试不seed计算结果；3个Run包括两个成功数值列和一个故意无效列失败，4POST含原key重试。

复跑产品测试使用修复说明中的命令；负例以Node+可解析jsdom的开发环境运行，具体脚本路径参数见脚本。Node24.19.0/jsdom26.1.0/Python3.12.14。原45秒Node timeout、原6秒UI等待deadline不改；新增清理只等待实际任务完成，不延长原外层预算。

artifact-hashes.json记录此目录编码文件SHA，压缩RED同时记录解压原始SHA；另记录修复driver、未变Python及产品入口的SHA。文件路径只包含合成测试域/本机诊断路径，无生产配置、秘密或数据库文件。未改安装体验交付分支、主线报告/DB/DeliveryGraph/CI，无Chromium、LIVE、发布或安全配置操作。
