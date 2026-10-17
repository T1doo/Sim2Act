冻结源 `3e2ea675d3849181170a03f6f4f1dbda469bfcae`：独立仅 tests/test_background_poll.py 一次，1 PASS / 0 FAIL / 0 ERROR / 0 SKIP，JUnit 3.597s，RC0；与作者同节点重复，unique+0，无额外测试。

静态核实产品/API均要求健康api=UP、worker=UP或OFFLINE；目录请求为/api/apps?metadata_only=true并读items。仅夹具两处UP和精确metadata URL匹配修复，trace为被动旁录。完整执行场景body字节相同（SHA 9febe9bef5b4921797c5b4f387ddf0ceab7d08ef3caa3da1e245339dec0ae746），21谓词/释放顺序、50次setImmediate、2500ms注册及Python30s/21计数不变；src相对2aac无差异，健康段同17b。6文件前后匹配冻结Git，无新静态阻断。

21检查全部完成；本次trace 122合成请求条目、20阶段条目、11个DOM场景、10个门均到达。原始results.json含完整requestTimeline/phaseTimeline；driver.log、命令、JUnit/log、前后哈希及静态核对见10项manifest/sums。

SYNTHESIZED_NOT_HTTP：合成fetch和手动scheduler，无真实HTTP/DB/Worker/模型/网络。未独立重跑旧基线或父额外Node比较；新诊断时间线不是历史原件，历史缺失时间戳未补写。PG/native/Windows/其他节点/矩阵/远端CI均NOT_RUN。仓库只读，旧失败未动。
