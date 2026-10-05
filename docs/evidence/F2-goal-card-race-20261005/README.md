# 目标卡异步选择竞态修复证据

2026-10-05，修复基线0382b91361d099b4af5ddcdc41cb5c101de41b12独立审查问题。在一次性SQLite/同一合成owner的A/B项目，真实API GET延迟2秒后，实际Chromium按钮/项目切换复现：B界面被A卡恢复，保存将A改到v2；New已输入文字被A迟到响应覆盖。before-fix.json记载实际观察；没有真实用户数据事故证据。

选择generation在打开/导航/New时失效旧请求，读取期禁保存，响应校验project_id，活动卡保留project_id并提交前核对；提交时冻结选择/版本，重复提交保护，完成时只有原选择仍有效才重新打开。项目刷新各异步边界拒绝跨项目迟到材料/列表响应。后端权限与CAS契约不变，不依赖前端校验代替后端授权。

browser-regression.js使用真实浏览器/正常API，仅扣留实际HTTP响应制造确定交错，不替换服务端数据。11项PASS：延迟GET导航后保存B不改A、New文字保留、后选/重复打开优先、双提交一次PUT、保存完成保留New/导航、提交及响应项目校验、旧版本409且文字保留、正常修订。两项目都属同一owner是本问题关键；跨owner仍原后端阻断。LinuxChromium，非Win11或其他浏览器引擎验收。

复跑：在项目锁环境执行`python docs/evidence/F2-goal-card-race-20261005/browser-fixture.py`，获得一次性mock SQLite服务127.0.0.1:8070；agent-browser打开页面、填写脚本公开合成身份`synthetic-candidate-browser`并连接，运行`agent-browser eval --stdin < docs/evidence/F2-goal-card-race-20261005/browser-regression.js`。每次使用全新fixture，完成关闭browser/server。脚本仅定义/创建合成测试数据，不读取真实令牌；无模型或外部写入。读取/保存项目校验两项显式构造不一致的前端状态以验证纵深保护，其余交错使用正常响应。

本地完整SQLite147PASS/3平台SKIP/1旧Starlette警告9.19秒；JS语法/diff/ruff/mypy通过。此次本地后端工作树保留下一MOCK候选未提交改动（mypy16模块），未混入本竞态修复提交；精确源码CI独立验证已提交版本。精确源码22f352b4f2868c924834eecb546242c5246b8291的[ServerCI37325580965](https://github.com/T1doo/Sim2Act/actions/runs/37325580965)/job111815358944已completed/success（2m03s）：PG150PASS/0FAIL/0SKIP/1旧警告40.98秒，ruff/mypy15模块、Setup/原生F1应用角色smoke/Report/Cleanup均PASS，server stopped。Server2025Datacenter/build26100/镜像20260925.250.1/PS7.6.6/Python3.12.10/PG17.11/admin=true/EnableLUA1；目标卡PG专项仍用隔离test-owner schema，浏览器11检查为Linux实测，不声称CI跑浏览器、Win11 UI或独立复跑。实际run/job及脱敏结果/精确提交源码hash已归档；文档收尾普通push不重跑CI。F1未签收/F2正式发布BLOCKED/LIVE预算0不变。
