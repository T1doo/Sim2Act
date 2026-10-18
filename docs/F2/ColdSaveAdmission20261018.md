# Cold SAVE最小修复：一次fresh mock整链通过

源码冻结 `fd96df814e8c0fb6db6651ce77eb484951240ecc`，基线 [f89未合格检查点](ProductionTrialStages20261018.md)。本轮 **4 PASS，B的9个原窗口全部执行**，原generate3→Source2→Cold2、同Run结果、artifact及PENDING owner入口断言通过。这里只确认本轮mock资格，未签整体F2、真实语义或LIVE。

## 改动与安全边界

唯一生产改动在 `pa_spec_apps._advance_local`：原1257处写后`commit_guard`原位保留，在其连续读取外建立新的`_journal_reads`。前面的SAVE intent/artifact/effect写入已清除旧读段，新的完整证明不会跨过这些写入；读段结束后再执行后续写入。原写前guard、写序、CAS、终态fresh、30秒lease及Run预算不变，没有新增executor、Grant、缓存类型或预算。

新读段仍限exact JournalTrialBinding、test SQLite和同Store/连接/事务/driver/线程/write epoch；其它绑定保持原nullcontext。独审移除新增包装后确认整个生产模块AST与基线一致。本轮1生产文件改变、137生产blob未变，另1测试文件改变。

测试拆出本轮实际gen3的`generated_prefix`，B只依赖它；A再继续原Source2/Cold2完整资格。A/C/D函数AST与B九窗口的断言主体不变。本次明确B→A→C→D且无fail-fast，Cold SAVE失败也不会遮住B的9个原窗口。

## 真实量测与实际执行

Cold Run为 `run_f4b0367077c4438183b90460d173ea66`；原失败Run `run_569084ed382a40ae80a0560eed94655a`没有恢复、续期或重放。

| Cold SAVE位置 | 线程CPU / wall秒 | SELECT等SQL次数 | write epoch | guard结束lease剩余 |
| --- | --- | ---: | ---: | ---: |
| 1220写前guard | 2.28478 / 2.287506 | 3681 | 195 | 25.953399秒 |
| 1261写后guard | 2.77929 / 2.779830 | 3713 | 201 | 23.162011秒 |

两处位于同一原事务；写后guard在新读段内、内部epoch不变。Cold事务到commit事件为11.315883秒/16370 SQL，BEGIN IMMEDIATE driver等待0.000381509秒，事件时仍余18.678297秒lease。这个SQLAlchemy事件在driver commit完成之前，不能当作完整driver commit时长；原结果及owner回读断言另证实际提交成功。所有原controller check无error。详见 [被动原始guard](../evidence/cold-save-admission-20261018/author/fresh-once/offline-guard.json)与 [闭合汇总](../evidence/cold-save-admission-20261018/author/closed-summary.json)。

此前两个串行只读组件诊断保留原失效lease拒绝，原DB SHA前后相同。单独当前准入两模式均3390 SELECT，未重现历史完整31.750秒；scope/audit/current组合3731→3627 SELECT，主要CPU在bound/lineage。历史栈缺1220/1257外层caller，不能补称已证明其唯一耗时或唯一布尔原因。本轮fresh量测证明新路径在原lease内成功；一次mock运行不是负载或普遍性能保证。

唯一fresh命令从 `2026-10-18T17:30:51.046278+00:00` 到 `17:39:53.983473+00:00`，pytest540.32秒、outer542.936816秒、exit0，900秒timeout未触发。原始 [精确argv/开始结束](../evidence/cold-save-admission-20261018/author/fresh-once/execution.json)、[JUnit](../evidence/cold-save-admission-20261018/author/fresh-once/junit.xml)、[stdout](../evidence/cold-save-admission-20261018/author/fresh-once/pytest.stdout)保留。

- B：本轮gen3之后实际执行原9窗口，含无写真实到期、撤权及write epoch失效，来源标记clones=false。
- A：实际7次原InternModel+MockTransport调用；Source/Cold成功、原结果及owner验收入口断言通过，7份raw/canonical响应哈希分别复算且相异。
- C/D：错误业务schema拒绝、同URL第二Store隔离，foreign SQL0，各handler1且无重发；已知计账accepted不等于业务接受。

本轮9次mock=整链7+负向2，真实模型0；652输入/138生产、runner/guard执行前后哈希无漂移。Ruff两文件及源码diffcheck通过。未重跑旧19/12/8/9矩阵。

## 定向回归、独审与限制

在明确标记的原失败合成副本上先执行原9个组件窗口；首次脚本随后构造旧Journal Worker，被软件指纹已变正确拒绝、exit1原件保留，旧合同未更改。补充命令不重跑9窗口，以合法generic Worker（无旧pa_trial安装）核旧SAVE入口及新_source_reads中的原guard均Stale worker lease拒绝，55表不变。该组件回归不替代fresh资格。见 [旧lease回归](../evidence/cold-save-admission-20261018/author/expired-lease-regression/expired-lease-regression.json)与 [首次拒绝原件](../evidence/cold-save-admission-20261018/author/targeted.stderr)。

暂时断连后先核原命令已exit0、无在途进程，再接续执行；没有重复启动、第二写入者或删除未知锁/进程。原f89的全部失败保持原样：旧14次记录=5PASS/8ERROR/1fixture FAIL，新增4PASS后累计18=9PASS/8ERROR/1FAIL；mock累计旧33+本次9=42。组件脚本不算额外pytest PASS。旧满盘独审报告仍NOT_RECOVERED。

[最终独审](../evidence/cold-save-admission-20261018/review/final-independent-review.md)仅核封存文件、源码、原始记录，未打开DB、重跑产品或读取私有holdout；作者纯文件汇总不冒充独立DB重建。封存SHA、复制数量及DB外部保留说明见 [证据README](../evidence/cold-save-admission-20261018/README.md)。后续普通推送另有delivery元数据核验。

真实API已有用户授权和配置key存在/非空事实；当前账户余额、强制无新增费用及真实source/controller受审安装仍未证实，本修复真实请求0、未新增网络探测。Windows/native、PG、远端CI、真实语义/人工验收、新PB/AT10及本片浏览器重验NOTRUN。未改main、强推、部署、费用、凭据或安全权限。
