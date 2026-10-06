# 独立最终复验

最终 `spec_checklists.py` SHA256 `69776b104f0f363509d1230410b7c7a735dbc3a8cac223cf9cfbc440609c292c`。独立SQLite专项45PASS/1PGSKIP/1旧Starlette警告，12.41秒；旧F1成果effect相关4PASS，1.67秒。

手工gold精确匹配、同步虚构quote拒绝；额外16-rule正边界及6个parser负例通过。归档脚本实际执行，断言存储output={}为GET/POST400、candidate_json整数为409、存储整数marker为409、公网整数marker为422；proof/receipt非法形状及coherent proof source_hash篡改为400，resource/grant/task数量不变。首次500及中间marker200事实与源码hash保留在JSON报告，不删失败历史。

未发现新增writeGrant/toolref/PermissionRequirement；既有artifact.save_text项目写交集、两个派生成果readGrant和事务内readback保留。保存前检实际授权source的bytes/hash/整资源行号，客户端gold不能替代真实来源。

无新具体未闭合问题。只证明受限标注规范引用/完整覆盖，自然语言语义NOT_RUN，非P-A/P-B或正式发布。独立复验0LIVE/0网络，不读凭据或headers，未执行PG/CI；主开发的aggregate/CI证据需按实际源码版本另核。

## 原始字节冻结复核

复核14a591f/e7eb39f：两个资产的`-text`精确覆盖路径、Git属性实际text unset且eol unspecified；工作副本与HEAD blob原始字节相同，fixture/gold冻结hash不变。测试改`read_bytes().decode("utf-8")`避免read_text通用换行转换，不会把CRLF误当原LF。四产品文件hash不变。

再独立专项45PASS/1PGSKIP/1旧警告，13.01秒。最终测试SHA256 `f6a05ffdeddd4a04ea66091de89802943304d81cdc1731b81bebf8694ac0ca06`，attrs SHA256 `264b18fa068594aecf05cfa3cc17b9a4cb60c64be1878faa8c2ca36fb0d4b5b1`。未独立执行Windows checkout或ServerCI，无新增问题；原finding历史保留。
