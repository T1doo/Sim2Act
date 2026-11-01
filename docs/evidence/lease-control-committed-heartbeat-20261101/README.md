# 独立心跳真实提交：仍非默认大型Cold验收

前保全6c70a954344e0a784cc7e6a71d97c2c7de5b546c。显式provision的新marker Run现接Store.heartbeat：fresh main只读核owner/version/fence/source/frozen/原resources.read，控制库Session.renew独立真实提交，不写main Run历史lease。控制提交后再鲜读owner及完整原授权，末尾核原节点wall/本次node-mono和首次claim固定absolute_mono。心跳只证明liveness，不产生Grant/PASS；后续业务必须保留自己的完整图校验和提交屏障。

v7同一组真实69检查通过，25.38秒、零跳过，另foreign-runtime专属检查通过。fixture使用1秒原租期而非放大常量；main读快照/已持写锁各8个真实续租提交跨过旧租期，main Run逐字段不变，G0读快照可成功升级。读组1.5109秒，续租19.79至52.46ms；写组1.4501秒，续租18.05至23.87ms。不是大型30秒性能成绩，无模型调用。

反例包括版本/owner变化、cancel intent、缺原版本、节点deadline、末次read跨deadline、控制提交后另一main连接撤权、控制文件消失不重建、旧owner到期不复活。真实续租已提交但最后期限/授权失败的案例保留sequence=1，不伪称rollback。固定absolute_mono续租不延长，过期续租拒绝。v2两个失败为新fixture直接修改frozen Settings；后改dataclasses.replace，原日志保留。

独审已复核尾窗与absolute_mono闭合。软件资格重新核PASS。0live/PG/WindowsCI/新增包。原Source/PB和旧路径不改变租约语义，新协议仍显式且Store.guard执行入口关闭。尚缺原DBAPI最终提交屏障、Worker/全部租约消费者接线、两次大型原30秒正常保存/首次重开/持锁取消，不能称整体完成；旧5af已验小型候选保留。
