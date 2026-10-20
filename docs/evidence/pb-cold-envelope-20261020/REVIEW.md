# 独立只读审查摘录

审查者 `/root/codec_review`。由唯一写入者转录已返回结果；reviewer 未修改仓库、Git，未运行产品、测试、模型或基准。此结论不覆盖后续提交/推送，也不是 G0/PB 接受。

开发前 **可实施局部 ACK**：exact BytesIO、原固定前缀、fresh protocol 5 Pickler 不变，允许先写前缀后原 dump。Pickler 的 frame/memo 不依赖外部 offset；getvalue 可调整缓冲，不能称完全零拷贝。输入与 reducer 调用边界保持，所有状态新鲜读取。资源耗尽异常的时点不承诺完全等价。

开发后核验：实际产品 diff 仅预写 prefix / 原 dump / getvalue，符合批准子集；allocation 脚本、baseline 函数、receipt SHA 匹配。baseline AST 与固定 `78ed5bef2da3a175d819eb9a2f58b3bbf097f75b` 一致；三组原始 bin 逐字节相同，长度与 hash 匹配，当前 runtime 源码 hash 匹配。

实际是两个独立子进程，每臂顺序编码三个向量，不是每向量独立进程。tracemalloc 各向量重开；峰值不含输入构造/验证，更非 RSS/G0。小向量 peak 多 29 bytes，中/大向量分别减少 55023 / 504529 bytes。

已核首轮 117 PASS / 1 FAIL / 11.499 秒及修正后 119 PASS / 11.117 秒记录。首轮新 oracle 对 import hook 异常翻译的预期错误；产品不变，修正比较原 Pickler 类型/消息，另加真正 reducer 异常 identity 门。不得隐藏首轮失败或宣称原 import ValueError identity 保持。

结论只涵盖局部字节等价、回调/错误回归与有限合成 traced-allocation 观察；不能升级为实质 G0 改善或完整 PB 修复。
