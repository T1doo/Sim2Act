唯一两臂原件复核通过；观测扰动候选无实质信号，立即否定并停止。没有发现新增P1/P2，也不提出下一轮probe。

执行脚本SHA256仍为开跑前ACK的 `76a11c066ac485ca65022f18ad0c6fcf5a01ad40de98101b49e17808f720dcbc`。receipt记录deep→outer两个子进程，均exit0、各producer1，45秒上限内完成。两臂f9dfcf151源码/Schema/包/lock清单、before/after和实存文件完全一致。原observer/helper与已审封存SHA保持一致。

仅producer body：deep wall3.866211830秒/threadCPU3.865326304秒；outer wall3.797118195秒/threadCPU3.796848015秒。outer约少0.0691秒、1.787% wall（CPU1.772%）；固定顺序单对不能作统计推断，此结果不支持把原完整失败归因于深observer。

独立逐字节比较初始6435字节、末579257字节，两个完整输入均同；有序SQL/原参数956105字节、2831行同，SHA `dc54565dcf8dee3a55f0662abb64b07cf01c70daf98a3dece119db52485e1189`。逐行解析重算：setup15SELECT+1BEGIN、scope_setup1BEGIN、producer2814SELECT，无其他SQL。CGR check2028/input_key2158/add130一致。源库和双复制库SHA均9a9bdfcf…；changes0、blocked0、返回guard active且同原guard、真实clock identity不变。

原observer确实active：DORMANT codec.bytes2170、input_bytes2158、check2028、SHA3169、firstbinding1、validator132；56安装/56恢复均RESTORED，secondary0、返回无异常。actual Mock调用0；observer内静态expected fullPB stage计数不是运行证据。

完整输入与SQL哈希、精确原件索引及结构化复核在FINAL-RESULT-REVIEW.json。本人只读文件、哈希与SQL JSON，没有打开SQLite、执行producer/测试/Worker/模型或更改仓库。

本次只有同源同输入dormant测量，不能解释原37.279秒完整G0、不能证明30秒租约通过，不能提升原PB FAIL_NOT_ACCEPTED及W5/G1/finalguard NOT_REACHED。该候选到此结束，不补跑、不延长租约、不修改产品。
