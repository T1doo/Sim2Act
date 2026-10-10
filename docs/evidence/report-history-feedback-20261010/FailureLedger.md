# 本轮失败、跳过与未验范围

作者最终冻结c460的SQLite/PG均13PASS、0产品失败、0跳过。仅既有Starlette/httpx弃用警告；未放宽6秒/90秒页面预算。

新自有PG初始化阶段，pg_isready成功后的一次psql探针exit2。尚未启动测试；后续实际SQL探针成功并确认0|0|0才运行矩阵。镜像临时初始化服务切换至最终服务的完整startup日志和私有preflight-note保留。这是就绪探针事件，未计产品PASS/FAIL，无提权或安全配置修改。

独立私有harness的初次11场景在初始化失败（向已启动TestClient应用追加middleware），没有真实页面执行；修正为新create_app实例后真实页面探针PASS。正式独审11pytest PASS（8新源码页面111检查 +3原112JS预期失败负例），0产品失败/0跳过；三旧页均在精确当前自清页反馈断言失败，先通过8/8/9前置检查，未计为产品PASS。不得用初始harness失败抹去源码缺陷，也不得用probe代替正式复核；原日志将随最终独审归档。

PG resources-history/历史全量/探索超时保持OPEN；其余HTTP200损坏响应形式/入口提示限制保留；Windows900/Edge240/Node150与真实模型、owner/semantic/整体/正式发布未验收。原112JS负对照为静态版本敏感性测试，不是旧数据库升级。

独审51个白名单文件原大小/SHA复制核验，初始失败/探针/3旧版负例raw全部保留。source350与产品68前后Gitblob/hash一致；独审不签PG、实际旧DB升级、其余HTTP200形式、逐item历史map/native/整体。
