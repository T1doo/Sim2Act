# 本地交付候选冻结独审（静态、轻测及实际包核验）

审查源码：0f0819a6a481841a0221cc69f75959326f264529。
基线：986799d766e98744e29e038543299af13785ea36。
分支：dev/local-delivery-candidate-20261016。独立审查前后工作区干净。

有限结论：在本报告明确检查的范围内，无剩余阻断问题。只读检查五个新增文件，产品src相对基线无任何差异；独立10项轻测通过，实际候选zip/manifest/wheel匹配固定Git源。根线程完整prepare与独立进程verify回执尚未提供本审查者，不能由本报告替代完整链验收或称浏览器体验已实测。

## 源码及安全边界

scripts/local_candidate_demo.py复用原API工厂、Store(test_only=True)、Worker和原模型生成/逐次使用/人工验收控制器；没有新executor、Grant或产品API，没有更改lease/fence/预算/幂等。settings_for直接构造mock、live_enabled=False、token空、provider intern-s2，不调用Settings.from_env。所有自然模型响应来自明确httpx.MockTransport，CSV通用provider为NeverModel。Mock响应是独立JSON文件中固定手写合成材料/引用，不是模型语义验收或真实理解。

prepare只接受不存在的新目录，mkdir(exist_ok=False)，数据目录及所有父组件拒符号链接；所有写入位于本次新目录。失败保留现场，不删除已有目录、不重排或重试失败任务。每个预期Run只原Worker.once一次，并核原fence1/claim一次。每次自然逐次提交重复发送同intent核同Run，未改变后端durable安全边界。

checked_directory要求精确公开合成marker、普通fixture/db/demo-receipt文件，拒这些文件和cold-read输出的符号链接。write_json先拒目标link，写本目录自有唯一临时文件后原子替换，不打开或跟随输出link；只清理自己创建的临时文件。公开marker是工程目录类型检查，不是生产权限或不可信数据库的真实性签名。

loopback预留实际监听socket且仅127.0.0.1，服务失败只收尾本次server线程。httpx客户端trust_env=False，request hook在每次发送前核精确http/127.0.0.1/原监听端口，修改receipt成外部绝对URL也不能发送；默认不跟随重定向。只读serve/verify middleware只允许GET/HEAD，拦截POST/PUT/PATCH/DELETE；无Worker启动。独立轻测真实启动该loopback普通首页、授权projects GET，拒四种外部origin、四种写方法，并比较全部持久表行不变。该项不等于实际浏览器JavaScript交互验收。

verify另核已有CSV=30、P-A/P-B artifact完整hash/result_version与同Run owner PENDING，前后比较全部meta表持久行；其cold-read-receipt输出允许重复verify更新自身派生回执，不修改业务表。自然结果保持semantic NOT_RUN / owner PENDING / formal_publication false。

## 本次发现与修正

初WIP有两项具体边界缺口，已在冻结前修复并纳入轻测：

1. verify的cold-read-receipt可能跟随既有symlink覆盖外部文件，且只检查最后目录组件。现输出拒link、原子替换并逐父组件拒link。
2. httpx base_url不限制receipt中绝对URL，trust_env=False也不限制目的地址。现新增精确origin发送前guard，四种foreign origin均拒绝。

包根README初始复制docs说明导致相对安装文档链接失效，已改独立根索引指向docs/LocalCandidate.md。我的最小symlink反例实际执行时已加载修复后的WIP字节并正确拒绝，未形成旧版本独立复现证据；初版结论来源为源码静读，不冒称完成旧反例实跑。首轮WIP独立轻测7PASS/2.54秒保留，但运行期间源/测试修改，因此不计冻结验收。

## 包内容及同源核验

scripts/package_local_candidate.py要求干净checkout，从一次固定HEAD Git blob读取src及明确18文件白名单，只接收100644普通文件；不复制工作区、tests、历史evidence、.git、私有.env、数据库、日志、venv、node_modules。独立README和逐文件manifest进入候选zip。wheel在同一contents构成的临时staging使用原pyproject+锁定setuptools构建，并设置SOURCE_DATE_EPOCH。构建依赖仍需网络或事先wheelhouse，非完全离线安装包。build.log位于zip外，不作为可分享deliverable；只分享候选zip、manifest、wheel。现有安装文档保留其历史普通安装说明，候选主命令以LocalCandidate.md为准。

独立读取根已实际生成的/workspace/local-candidate-artifacts/Sim2Act-local-candidate-0f0819a6a481.zip，不解压、不安装、不启动Worker：

- 134个zip条目 = 133个manifest条目 + manifest本身；无重复路径、绝对路径、..、symlink或额外条目。
- manifest中每项bytes/SHA256与实际zip内容全部吻合，manifest内外副本相同。
- 131个应来自Git的条目逐字匹配冻结commit；README是审过的固定索引，wheel另验。
- wheel全部113个产品文件逐字匹配zip内src/sim2act，余项仅该distribution的dist-info；没有缺漏或额外产品文件。
- 目录过滤无.env私密配置、DB、logs、tests或历史evidence。此为允许条目和字节核验，不是对未知私有数据的全面扫描承诺。

候选zip SHA256：00315c17bfcdc91c28384a5675e32590a19ffd5047761de7fb962adc325fe216。
wheel SHA256：23fcbd6fd1a49de28899fae40e99c879aa2bb54ca04e40d94da3855ea0194323。
manifest SHA256：72bb83be7289c34184bd85ce81cc5b617b8a3364b11bf091e03460a66b8c6f0f。

## 独立实际执行

命令：/workspace/sim2act-venv/bin/python -m pytest -q tests/test_local_candidate_demo.py --basetemp=/tmp/f2-local-candidate-independent-0f0819a6 --junitxml=/tmp/f2-local-candidate-independent-0f0819a6.xml。
结果：10PASS、0FAIL、0ERROR、0SKIP、RC0、JUnit1.919秒（终端1.92秒）。仅已有FastAPI/Starlette测试客户端弃用warning，未安装/升级依赖。

实际覆盖：已有目录不初始化/不删除；真实配置环境哨兵不被读取、普通Store仍拒SQLite；marker/db/receipt/root/parent/output link六类拒绝；原子writer不跟随外部link；真实loopback首页和授权GET、foreign origin拒绝、写方法拒绝、全库行不变。

原始证据：

- /tmp/f2-local-candidate-independent-0f0819a6.xml，SHA256 19b6117d5e7b2b207c32e09ecf09bf2ddcf7cd2a19f482692d12c55da48091ab。
- /tmp/f2-local-candidate-independent-0f0819a6.log，SHA256 b675b16d3f37d5cf52e2eff0ddf83f5de9fe3d93a7b6ca144ea620c418cf7c2a。
- /tmp/f2-local-candidate-independent-0f0819a6-package-proof.json，SHA256 29fc8770857cf8c1134705689b41c5fba2844e25271679e3c6707c3db8210f29。
- /tmp/f2-local-candidate-independent-0f0819a6-review-manifest.json记录冻结五文件hash与上述原件hash。
- WIP原件 /tmp/f2-local-candidate-independent-wip.xml 和 .log 单独保留，不算冻结通过。

## 未执行与历史事实

本审查者未执行完整prepare自然Worker链、真实模型或token探测、PostgreSQL、Windows、原生浏览器、远端CI、部署、旧锁恢复矩阵。普通Settings.from_env/Store仍要求PostgreSQL；自然P-A/P-B仍无可执行专用LIVE批准门/跨Run总账，真实额度0，token或通用live开关不能开放自然家族。仅列最低未来批准要求，没有配置或调用真实模型。

前轮45PASS/1FAIL、测试断言修正后定向2PASS、独立新增模块9PASS均保持分期。自然双Run成功但没有触发recovered恢复分支，旧F9自然失败时序未复现；不由本候选宣称修复全部SQLite争锁或补回旧满盘未落盘独审。
