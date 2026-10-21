# 最后小修设计：精确 conditional Release roots

只读设计同意，尚未签修改后的代码或回归：lifecycle.py:373–405 的 owned_release_pointer 默认 key 为 `release-pointer:`+user+`:`+rid；natural_live_admission.py:338–350 在原 bound/instance 对照后调用它，可能在 native frontier 激活后懒新增根。

允许在发行前从已经原 fullguard 的 `cold-trial:bound.binding` / `source_binding` 的 snapshot.release_id，配原 graph.binding.contract.principal_id，推导最多两个去重 exact key。必须 exact str，字符串构造前预算预费；不提前调用 SQL、不用任意 prefix/任意 Release ID 白名单。根值仍由原 owned_release_pointer、项目权限和 immutable_release_pointer 生产/校验并留在 fresh frontier。只增加根名准入，不新增授权或省略原 field checks。后续字节/工作上界仍归 monitor 独审，不能仅凭“最多两根”称值大小已封闭。

测试的 no-runtime-callers 检查可只给 `_cold_accounted_native.py` 增加明确私有 import 例外，保留其余禁止，并加 `_accounted_candidate` signature 默认 None 断言。原 private/default-off 事实不变。receipt/proof 的 18/7 len 在遍历 keys 前拒绝是正确最小收口。

333 pass/3 fail 的前一轮应保留原件，不改写成通过；根侧新冻结 SHA 和最终原件到齐后再另给最后确认。早先 FINAL-NATIVE-STATIC-ACK 仅属于旧哈希。

本独审不执行任何测试/产品/DB/Worker/Mock/G0/prepare/commit，仓库写入 0。
