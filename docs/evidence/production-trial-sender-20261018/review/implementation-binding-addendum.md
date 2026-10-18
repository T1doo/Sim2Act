# WIP addendum：原 Worker 绑定必须冻结

新增 `P2_MUTABLE_WORKER_STORE_AFTER_GUARD`，静态推导，未运行产品/测试。

第一次实际读取的sender字节记录见 implementation-review-draft.json（13473 bytes，SHA f6b01704650ba4610f6d0d50899479e62a5137248fb50911e07201d5d6010f7c）。`dispatch_offline:198–247` 反复动态使用 worker.store，transport也在marker之后才从worker取。guard内只检查当前store仍是一个合法test_only对象，未绑定入口那个对象；返回body之后 `_receive(worker.store,...)`没有再作_binding。

可复现路径描述（未执行）：本来以test_only Store A完成reserve/marker/guard；固定MockTransport handler在guard后将worker.store替换为同一SQLite URL的Store(test_only=False)再返回body。_receive会沿B加载同一持久state并写六行，尽管生产Store不能进入offline边界。没有真实IO，但严格test_only写入边界被绕。

最小修正：入口捕获original store/settings/worker-id/transport对象；reserve、marker、guard、_history和_receive全部使用捕获store，guard核Worker仍指向这些原绑定（Settings不可变，可用identity加已有具体字段）；transport也应在入口捕获而非marker后选。IO后Worker属性漂移不能转向其它数据库或productionStore；late事实仍只记到原授权fixtureStore，不因对象漂移退款/重发。

可以在现有正常/配置测试节点中增加一个控制断言，无需新node或旧矩阵。尚未获得root修复字节/冻结/资格；本新目录未seal。
