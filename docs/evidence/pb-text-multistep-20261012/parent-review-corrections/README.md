# 父复审两处页面 P2 纠正（2026-10-12）

Open同时冻结workspace与单调edit generation。showApp同步清除旧表单的合法reset由onSelectionStart即时采纳；异步GET期间的资源工作区切换或输入ABA令旧回包失去安装/导航资格。原代码2FAIL；修复3PASS（合法打开＋workspace迟到＋edit ABA迟到），实际进程内HTTP/JSDOM，合法实例运行使用冷SQLite普通NoModel Worker。

内部运行回包仅在Map仍保存同一pending对象且原request_key未变时清除恢复键。实际生产函数受控调度：R1延迟→同实例新view仅原key GET恢复R1→新R2→迟到R1；旧代码1FAIL/正常R1 1PASS，修复2PASS。此受控调度无HTTP/Worker/native资格；每份JSON明确NOT_RUN。

[完整汇总与源码桥](summary.json)；原失败、日志/XML/页面JSON及修复前两JS原字节均保存。仅页面两JS与定向测例改动，69后端PY（含config；68实现PY）和pyproject不变；未重复全仓测试。原r11 55/56与r10 535各属于原历史冻结，不能加总或称新全仓资格。SKIP纠正阶段先于此次UI修改，见[原分类证据](../skip-classification-correction/README.md)。

PG、Windows、native、真实owner/语义/模型、旧源码升级、部署NOT_RUN；Forbidden CI停止，旧精确取消候选窗口永久NOT_VERIFIED。

独立同冻结5PASS/0FAIL/ERROR/SKIP（受控pending2＋实际HTTP/JSDOM3），两个进程exit0，416源/tests前后零差异；见[独立计数](independent/completed-counts.json)与[冻结](independent/source-after.json)。作者＋独审5例重叠，不加总为10唯一。
