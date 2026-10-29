# 桌面完整重启后的同源原键恢复

基线 `0459a266e2c35c83b8f1995cc60b8b92f1ebbdce`，实现 `b6c9627126f241aa8fc83a6957f399ea71e85a1a`。根因是后台每次随机端口改变origin，同一WebView profile也不能因此读取旧origin的localStorage。没有改UI恢复协议、API/schema、角色、审批、模型开关或usable_product。

## 实际实现

仅显式 `--control-stdin` 桌面入口在已认证工作区保存 `desktop-origin.json`：固定127.0.0.1，记实际已绑定端口及marker/principal身份。重开先独占绑定该端口，Windows用SO_EXCLUSIVEADDRUSE；占用就报PORT_UNAVAILABLE，无扫描、重绑、访问占用者或杀进程。未持有实际listener时不能发布记录或READY。

记录严格限制普通路径（含symlink/junction拒绝）、大小、字段、类型、规范JSON与身份。完整临时文件fsync后，Windows用无覆盖rename，POSIX用link加目录fsync；并发首次发布只有一个胜者。发布后检查自有临时文件dev/inode，READY前复核记录原身份与字节。失败保留已有记录与数据，不覆盖猜测。普通非桌面serve入口不改。此元数据不提供读取、执行或模型权限，原spec当前授权与原key校验照旧。

synthetic_workspace.py在原142文件精确资格集合内，因此按其实际源码更新qualification及归一化pin，值为`9a42cce90b7c9592fe6c0ad96258b5af31e3e4ee2c73ed60090dbb525365eb8f`；没有删文件、排除启动模块或弱化_qualified。最终回归后_qualified正常返回，六份冻结文件摘要一致。

## 真实关闭重开证据

既有唯一回归日志27通过/0失败/0错误/0skip，100.24秒。容量中断后先读回原日志/JUnit及无自有运行进程，未重复启动。旧exec session已不可查询，因此不补造该句柄退出码；完整结果在functional.log/xml。

核心链从真实合成SQLite准备一份已批准的固定规范应用，准备阶段3次MockTransport，子进程运行阶段0模型调用。三个不同Python后端进程各发真实READY、完整EOF关闭及clean STOPPED，再由下一新进程重开同库。三次地址都是`http://127.0.0.1:43107`，前端提交次数`1 → 0 → 0`：首次受理后故意丢响应；第二次重开按原keyGET但故意损坏releaseID，保持原存储；第三次完整重开按原keyGET成功，仍同Run/AppRun并清原键。冷库该实例始终只有1条AppRun/1条绑定，SUCCEEDED；全部业务表逐一精确fingerprint相等，唯正常Worker心跳表允许新worker记录。每次真实DB摘要均保留，没有谎称整库字节一致。

占用同端口的真实listener未收到任何连接；再次启动明确失败，DB及origin原件未改。并发发布、同字节替换、损坏/超大/错类型/错host/链接/外国工作区记录负例通过。另执行原永久关闭键与身份/撤权/绑定损坏的后端回归，以及现有Storage/WebLocks协议负例；未放宽授权。回执原件在restart-proof.json.gz，来源/摘要/分层范围在summary.json；真实READY/STOPPED及占用失败日志一并保留。

第一次试跑仅HTTPX默认5秒观察窗口超时，后台正常SUCCEEDED/clean，后改为显式20秒有界读取观察，产品租约/事务/时限未变。第二次三轮恢复均通过，但把含新Worker心跳的整库误判应字节相等；已改成全业务表逐一精确比较，同时保留所有真实DB hash。旧失败数据和日志仍在`/workspace/scratch/desktop-origin-r1-20261029`和`desktop-origin-r2-20261029`，未覆盖旧DB。

## 不扩大结论

云端实际运行的是Linux后台进程、物理SQLite及回环HTTP。JSDOM的Storage/WebLocks是明确的按origin分区、文件持久化适配器；不是原生WebView2落盘验收。Windows独占socket、无覆盖rename、真实软件窗口完整关闭重开及原profile仍须原协调任务在目标机验收，本任务未调用用户电脑。

旧工作区没有origin记录时，首次升级启动只建立未来稳定origin，保障之后建立的原键；不能凭空找回旧随机端口中的历史意图，不扫描旧profile或猜日志迁移。旧未知请求仍需先查原任务历史，不能拿新origin当原key已核对。不得删除origin文件来换端口。移动工作区还须保留对应profile。

正式PG/live现有连接与业务选择、自然语义及owner签收仍分开；本轮未创建凭据、扩大安全权限、改main、部署、制作安装包或发布Release。
