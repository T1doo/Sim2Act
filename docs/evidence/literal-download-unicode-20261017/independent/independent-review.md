# Unicode 下载边界：独立有限审查

冻结修复源 `ba74572af2722ed38d763316603548417000d7dc`；旧red源 `968144fe3083fda7a58924f5abce17cadfb87ea5`。源码只将下载validator的UTF16长度判断改为Array.from计Unicode码点，与Python服务端len上限80一致；服务端、权限、合同均不改。新增测试字节与red轮保持一致。独立实际只重复unicode参数：**1 PASS / 0 FAIL / 0 ERROR / 0 SKIP**，RC0，JUnit 37.552秒。不是新增唯一节点，没有重跑其他3参数或旧red。

实际合成ASGI HTTP、完整服务页面JSDOM及3个冷NoModel Worker：41/80个非BMP码点均SUCCEEDED并保存v1/v2空引文；81为INVALID_INPUT/FAILED且无成果版本，数据表仅v1/v2。页面两个按钮分别fresh鉴权GET导出精确原JSON UTF-8 Blob；同绑定80允许/81拒绝。2个Blob均回收、所有产品动作GET无body，48表只读阶段checkpoint不变；原始执行仅既有MockTransport2次，runtime模型0。

已只读核对作者旧red原件：实际持久41/80合法结果存在，但页面没有两个下载按钮而失败，1FAIL33.73秒。其原SHA并列在proof中，不能用现在绿色覆盖旧失败或先前遗漏的边界。

完整原件manifest含data/info、结果、stderr、实际Blob、合成fixture.db及原log/XML/source前后文件的大小/SHA，见raw-manifest.json与raw-SHA256SUMS。本审查未写仓库；root证据目录差异原样记录，产品/测试文件前后与冻结Git一致。

限定范围是通过HTTP建立已有合法结果后的下载，不是原生输入框体验；index.html既有maxlength=80仍有UTF16输入限制，本轮未证明能在真实浏览器键入80个非BMP码点。不扩改相邻入口。PG、browser/root cache探针、真实浏览器落盘、Windows、真实模型/语义、远端CI及原CSV四步均未执行。
