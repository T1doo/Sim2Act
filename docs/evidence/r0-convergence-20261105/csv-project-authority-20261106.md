# 同实例第二批复用与授权锁顺序

真实 Windows 打包版20aba026、专用PostgreSQL、合成报名数据。通过正常Goal固定CSV能力模板建立独立演示应用，不称为模型生成。原实例 `iinstance_9c5a67df71e94c7c88ef5da15a227432` 第一批金额6240/v1；第二批实际8000/v2，均6条，来源、Run与Release各自保留。原采用读取超时，随后用实例history中的原approval_id确认已提交，没有重发采用命令；第二批新运行原定请求键幂等回读一致。

页面授权、冻结材料和独立CHECK已实际执行；CHECK原键 `33aa944a-38e9-46ac-b7e0-ae924fe3e93e` 后台PASS。后续Release/采用/第二批计算经过原API接续，不能签成全程UI通过。新旧成果的冷页切换暴露真实HTTP500；诊断回环API使用原打包代码，只增加脱敏日志，捕获psycopg.errors.DeadlockDetected，授权Grant锁形成循环。

仅在Release读取入口加锁的局部尝试未解决目录与实例列表的交错读取，已经撤回。最终在Store.authorize进入时使用原lock_project，再检查资源及两类身份的Grant，统一project→Grant顺序。项目所有权条件、授权有效期、撤回、资源/hash、真实查询与语义状态不变，不增加缓存或授权例外。

当前源码叠加同源已验证native二进制后，在真实专用PG的回环诊断API复验成功：旧6240/v1、新8000/v2、历史切换及界面JSON/CSV下载；没有500或死锁，页面脚本错误0，专用进程干净退出。协议任务注册表仍报告缺少可选Evaluation asset（400），并非该CSV案例通过证明；该未完成能力单列，未隐藏。

针对性SQLite回归3 PASS：授权SQL形状和实时撤回/过期、直接材料预览及原字节/权限边界。见csv-project-authority.xml。前一局部方案的长回归因该方案被实际复现证伪而停止，不当作PASS。

这些是修正源码的实际验证，尚不是新冻结Windows包验收。下一步重新封存软件资格、构建，并用同一持久工程重新核对。全部失败原记录保留在项目内video-reuse-demo-20261106；不会用最终截图改写之前的失败。
