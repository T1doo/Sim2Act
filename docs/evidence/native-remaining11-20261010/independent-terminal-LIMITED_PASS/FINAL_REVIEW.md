# LIMITED_PASS — 实际终态与267文件公开证据限定审计

精确源码 `180a4710405b9c06d1e7cc7213b3ffd073d05567`，唯一 run `38031437108` / job `114153034590` / attempt1。只读重构实际日志、验证导出和文案；本轮独审没有运行测试、CI或PG，没有修改仓库或refs。

实际 JSON transport 解码后的UTF8原件4,797,111字节，SHA256 `5d4dc70dbeebccd4e704f3fe65c366f99221691b9878fad6fa6449a0cf37ecd5`。独立解析113个完整收集块，2250个唯一节点；固定11与原manifest精确一致，2239明确deselected。59个可见事件按同PID及原生顺序闭合，11start/11finish、33个setup/call/teardown全passed、唯一exit0，actual Report strict verified且suite_complete。11PASS/0SKIP/0FAIL。这里没有将收集2250称为执行通过。

9个实际浏览器JSON/PNG按各自chunk index重组，全部字节数和SHA与私有原件及公开文件相同。分层检查数分别69/39/33/29/16/26/19/22，有嵌套，不求和作独立总数。Windows Server2025/安装Edge的限定结果保留；Win11 NOT_RUN，mobile仅viewport，原agent/protocol visualReview NOT_REVIEWED未改。六截图粗观察明确属于作者有限末态检查，不作本独审视觉签收；protocol desktopBLOCK/narrowUNKNOWN不同场景没有合并。

核验JUnit113.781秒、工程步骤129秒、Edge步骤141秒、整个job359秒。原900/240/150预算未改。上述数属于不同层级，未相加作完整工程容量。原9002 full run耗尽900只完成591/2234且Edge未执行，支持那次所需预算严格>900；当前完整尾部成本及足够最小预算UNKNOWN，全套容量仍BLOCKED。

公开根 `docs/evidence/native-remaining11-20261010` 的267文件（不含自身manifest）逐项SHA/大小及集合精确，已保存被审manifest快照，SHA `950444cb1df2aa7ed6febd921f3ec8e01ee993b83b3ba3cf07806a1d9ab906d4`。六白名单共260项，另6白名单+README=267：author21、historical-pg14、d49BLOCK55、5385BLOCK64、180aLIMITED83、native23。全部与private源逐字节一致，historical两项重命名private_source_path也一致；旧BLOCK/故障日志未覆盖，完整私有transport/job日志未冒充公开excerpt。此签收对象是该267快照，之后追加本审计材料需另更新manifest，不追认未来文件。

363冻结文件在终态解析与出版核验前后均与Git精确180a及工作树一致；69产品文件逐字节等于47388f573746daa27f8d5790ca358eef91378ad5。仅docs待发布差异。读取父代理两PG节点原始XML/配置声明/被动profile：2PASS/0SKIP、页面10检查/28HTTP，锁receipt402条、跨度1.647557399秒、resources/graph均200且project-first；原阈值和observer未改，清理0|0|0及owned容器/卷消失。它们是父代理执行证据，独审未执行PG；两个历史超时OPEN不关闭、不认定当前成本为历史根因。

保全三次自编审计器错误：line-anchor漏抓2个分块；简化jobs返回缺head_sha/timestamps却被错误要求；文案等价语句被精确字面检查误拒。三者的原脚本/日志及修正器均保留，无产品/公开数据故障。

结论仅LIMITED_PASS，支持实际剩余11限定通过和当前267证据保真。原26的15+11来自不同源码run，非同一run26通过；2250全套、Win11/R0/native整体、semantic/owner/正式发布仍不验收。PROJECT PENDING/BLOCKED_PARTIAL，LIVE0。两个历史OPEN及HTTP200损坏反馈其他入口限制保留。

复制范围见本根COPY_WHITELIST.json；完整私有job原件和transport由作者私有根保全，不复制到此白名单。
