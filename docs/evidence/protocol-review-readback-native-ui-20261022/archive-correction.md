# 归档字节校正

浏览器执行与原始本地文件均未改变。首次文档提交 `4af6e3f6d1017b7b142930dadf63736acbb24b2f` 的 Git blob 核验发现两份 Windows 原始 JSON 曾被Git文本转换：inventory.json 从3271B变3234B，launch-contract.json从4778B变4733B。原本地文件及嵌入job.log的Base64始终保留原CRLF。

已加入 `native/*.json -text` 并显式重新索引两份原件，校正提交保留其原字节；不强推改写首次提交。对归档全部文件做 staged Git blob 与MANIFEST长度/SHA一致核验后再提交。此问题不改变CI执行SHA、产品源码、原生断言、截图或清理结果；不启动新CI。
