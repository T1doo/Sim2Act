# 已有应用使用 JSDOM 驱动生命周期修复

2026-10-07，独立 `dev/application-use-jsdom-lifecycle`，正常 fetch 的 FETCH_HEAD/ls-remote 基线 `de907327dd5b3105c169008a9fe0c90dcc353a8b`。主线明确将 `tests/application_use.cjs` 交本线修；只修改它及本说明/独立证据。产品 app.js/use.js/API/Store/Worker/数据库、Python 测试条件和CI不改。

## RED 与原因

完整测试 `tests/test_application_use.py::test_application_use_actual_http` 原断言第68行要求 Node 驱动退出码0，实际1。堆栈 `app.js:18` 的 `$()` 读已销毁的document，`safe` 第25行catch再读DOM，遮住原始异步异常。此前de907的三项focused结果2PASS/1FAIL原JUnit保留；本线另在精确e828旧树单次复现1FAIL/2.13秒。测试Python、driver及use.js在e828/de907/本次修前字节相同；问题不是首次体验说明引入。

旧driver冷setup直接 `dom.window.close()`，但点击事件是异步函数，UI某个字段出现不等于该动作/请求及后续微任务完成；旧窗口销毁后仍有Node I/O/事件Promise引用旧document。旧driver原始异常的精确phase未记录，不伪称知道所有旧oracle已完成。它阻断该工程测试；真实原生用户页面关闭/导航是否有同类问题NOT_RUN。

## 最小修复与错误保留

每个页面单独记录HTTP请求和onclick/onchange/onsubmit返回Promise。普通HTTP body读完才释放计数，故障注入/断言保持原样；事件拒绝记录原Error。`idlePage` 等请求/事件完成，再跨一个setImmediate回合检查，无轮询睡眠放宽原6秒等待。每次cold页面更换与最终close先drain；故障mode切换前等待上一动作结束，不让上一请求误消耗下一次注入。

原驱动 `setInterval=()=>0` 保留，interval从页面创建即禁用，无活动周期计时器要留给旧页面；不冒称管理原本不存在的timer集合。新助手只追踪实际HTTP与事件Promise，不改产品timer/安全设置。异步拒绝/同步抛错仍使测试失败，不能通过吞异常修绿；独审负例确认原Error被idlePage原样抛出。

原29项oracle文本、双击单POST、未知回执/原key重试、版本与结果绑定、失败不借历史、late项目/身份清理、4POST、正常worker3Run/2结果、Grant/Principal完整行比较，以及原Python45秒timeout/退出码/结果/权限断言均保留。新增仅两个页面close时零pending/noError的生命周期断言（汇总为第30项）；技术成功、语义NOT_RUN/ownerPENDING/正式发布关闭的原边界不变。

## GREEN、重复与边界

[证据目录](../evidence/application-use-jsdom-lifecycle-20261007/README.md) 保存原始RED/GREEN JUnit、日志及实际results。开发者第一次1PASS/2.35秒，删除无用timer集合后的最终源码连续两次1PASS/2.13、2.32秒；每次3Run/2result/完整权限校验实际执行，两个页面pending requests/actions/errors均0。独审最终另跑1PASS/2.26秒（前版另1PASS/2.42秒），并从最新源码提取helper执行同步抛错/异步拒绝原Error负例通过。

Linux/Python3.12.14/Node24.19.0/jsdom26.1.0，临时SQLite/loopback API，真实正常Worker，合成数据0模型。显式移除SIM2ACT_TEST_DATABASE_URL避免进入其它数据库；显式PYTHONPATH绑定本工作树、NODE_PATH绑定独立开发工具。没有Chromium重启、sandbox绕过、LIVE、权限变更或新模型配置。

```bash
env -u SIM2ACT_TEST_DATABASE_URL NODE_PATH=/自己的工具/node_modules PYTHONPATH=src \
  python -m pytest -q -p no:cacheprovider \
  tests/test_application_use.py::test_application_use_actual_http --junitxml=/tmp/application-use.xml
node --check tests/application_use.cjs
```

Node语法/diff whitespace通过。原Python文件及产品源码SHA保持基线；本分支普通push不匹配仅dev/f1-foundation的workflow。主线cherry-pick本提交，仅driver一处接线变化。该GREEN不关闭PG Report90秒、全量回归/Windows预算、受保护浏览器像素、Win11、F1/完整P-B或用户语义签收门。
