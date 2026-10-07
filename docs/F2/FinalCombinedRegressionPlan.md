# 最终组合源码完整回归（实施前，等待最终冻结）

2026-10-07，父授权组合全量，准备基线root `9dc833ab68e56075a4e76927001c728a4d73c8e8`。新专属 `/workspace/Sim2Act-final-combined-regression` / `dev/final-combined-regression-local`，不改root/原core/native/sharedvenv。此计划不是最终源码冻结；父仍在合入真实原生Run链与预算优化，必须收到精确最终合并SHA后才跑全量，不能把eb90或native历史结果相加算组合通过。源码最终实际HEAD与src/tests/scripts/.github全树SHA、父冻结SHA逐文件相等再开测；计划作为docs-only独立commit保存，若HEAD仅因计划不同必须明确父source SHA与docs HEAD并保存空产品diff。

独立controller准备venv `/tmp/final-combined-regression-venv`；最终SQLite与PG分别 `/tmp/final-combined-sqlite-venv`、`/tmp/final-combined-pg-venv`，localpth先本树src后共享deps路径，不处理共享旧editable pth/finder、不安装或修改依赖。每种数据库controller与完全干净env child核sys.executable/sys.prefix/sim2act及关键Python模块实际路径/SHA；scripts/tests动态import只读探测，src/tests/scripts/.github追踪文件全树manifest/static导入与硬编码旧树路径审计。Python子进程仍用sys.executable和本cwd，Node/browser模块从本树静态路由/相对路径加载。NODE_PATH固定现只读 `/workspace/browser-tools/node_modules:/opt/codex/runtimes/cua/lib/node_modules`，nodev24.19.0/jsdom30.1.2；不安装cache、不处理SUID或sandbox。

专属PG容器名`sim2act-final-combined-regression-20261007`、label`sim2act.final-combined-regression=20261007`，PostgreSQL17/随机127.0.0.1端口。私有mode0600 JSON持url/password，只向自身PG子进程env传，所有公开日志sanitize。仅创建空测试database，不提前Store.initialize/seedpool/Grant；测试fixture显式owner初始化schema及合成角色/pool，业务CRUD role无DDL初始化。每fixture独立schema/角色并清理，PG源/角色/实际进程锁分支必须真实PG；明示SQLite-only/pure unit分支不冒称PG SQL。SQLite使用独立basetemp文件，与PG基于不同venv/tmp并行，不并发写共享DB、sharedvenv或其他线资源。

父最终freeze后：记录精确SHA/current全树manifest与导入provenance、先`pytest --collect-only -q`保存全集（不根据旧计数推测）。最终各跑完整`python -m pytest -q -ra --durations=30 --junitxml=<owned path> --basetemp=<sqlite|pg distinct>`，保存完整-ra、最慢30项、JUnit、退出码/命令/环境安全摘要/collection，不得测试选择代替全量。两套并行仅各自独立数据；真实Model预算LIVE0，测试仅Mock，权限无产品新增；原生/像素按当前能力真实skip，不用另一线结果冒称同源。独审已存在只引用明确SHA范围，组合回归仍需真实新完整结果。

若独审/全量发现真实源码缺陷：先有序SIGINT仅owned精确controller、保存STOP_SOURCE_DEFECT/partial/exit2和旧SHA，不边跑边改源；确认owned进程/DBschema/role0后由父修合并/重冻，再对新SHA重跑，保留旧错误，不把旧通过重标。源码本agent不得改，无push/CI/LIVE/Grant/真实身份/准备器/发布/新表或schemaAPI。最终ownschema/role/publictable/controller/children0，检查label再删仅owned容器、再次inspect不存在/label0；删私有URL/rawlog，sanitized证据/docs本地commit独立交付父。

当前状态PREPARED，最终combined full NOT_RUN；等待父通知冻结SHA。历史core eb90的976/1012以及native的旧全量仅历史，不签最终组合。
