# 字面成果 JSON 下载：独立有限审查

执行源 `12a57e0ed0cf8085e28c09ddfec1a684b65194c4`。实现与实际鉴权读取路径静态审查未见阻断缺陷：normal Run.id与typed AppRun分别绑定、实例/Release/结果版本核对，fresh GET经现有scope_run和text_run_checks重新授权/独立完整引文验证；导出固定白名单，不导出材料全文字段、合同、events或鉴权信息。源码显式source_hash字符串校验已在冻结源。

独立实际只执行新增3参数节点：**3 PASS / 0 FAIL / 0 ERROR / 0 SKIP**，RC0，JUnit 193.015秒。是作者同3节点的重复，不增加唯一用例分母。bytes/navigation/revocation覆盖UTF-8实际Blob字节、Unicode与HTML字面引文、v1/v2/v3无命中、fresh no-store与错误绑定/结果拒绝、导航代次/refresh防重/403清内容、链接及Blob URL回收。每例合成SQLite48表只读阶段checkpoint不变；仅明确撤权场景改变既有Grant。

每例正常冷NoModel Worker3次，共9次，生成仅既有MockTransport每例2次共6次；runtime模型0。原始证据在pytest.log/junit.xml/data各场景结果、database-proof及captured-blob；完整SHA见independent-proof.json。测试无失败，无重跑。开始后产品/测试/鉴权6源文件逐字节保持冻结Git；仓库状态原样记录，仅根写者可整理证据，本审查未写仓库。

这是实际ASGI HTTP + 完整服务页面JSDOM + Node Blob适配器工程验证；不证明真实浏览器落盘或PG。PG、原CSV四步、Windows、真实语义/真实模型、远端CI均未执行。本审查未执行其他相关模块，不能代签其门状态。
