# 父级最终选择：P-A single + 一项超界资料

本段更新 triage.md 的初始六步/Goal mismatch建议；最终采用 `ready(data,'single')`，不实施PB首次logic页、不执行mismatch例、不下载。预期Mock 3 generation + 1 PA v1 + 1 page PA v2 = 5，实际仍须由新原件判定，不能写成六步双模型。

唯一错误输入为正常保存的2049个ASCII字节、单行TXT及明确引用它的匹配Goal，全部fixture材料/Goal均先于页面PREPARE保存。它能由普通控件送达服务端：internal.js:1273只按txt/md填材料选项；:1274独立Goal选项；:1279–80核精确引用但不核长度；:1283真实POST review。pa_material_bindings.target:158–165允许<=4096字节/64行并核Goal快照；pa_spec_apps.target:569/source_check:84–85进入natural.bounded_source；natural_specs.py:88–97对>2048抛INVALID_INPUT，api.py:220–229将其映射HTTP400。该错误既非前端挡住的mismatch，也不需要篡造请求。静态路径不表示已实际PASS。

有限新实际路径：统一目录选择已保存PA/实例→页面选择v1→PREPARE/逐项SIMULATED ACCEPT与理由/明确ack/DECIDE→选超界材料+匹配Goal预览→实际400、可见错误、全表/模型/Run/Grant零delta→改选THIRD材料/Goal→正常预览/新同意/同实例v2 Worker→v1与v2同Run/成果回读。旧接受ledger原字节保留但STALE，新v2sequence0/PENDING不继承；无下载、关闭、恢复或故障矩阵。真实模型0，人工选择是合成声明非真人语义评价。旧PA peruse本来已有完整page，本轮是当前统一入口与原接受到未见输入的连续资格，不是新executor/Grant/泛化承诺。

仅只读确认，产品执行/HTTP/Worker/模型/SQL均0；本目录与所有旧sealed目录界限独立。
