# v2本地候选冻结独审

审查源：c9e9f3fc9787350d1e7997860234694b270a6a7f。
前版：0f0819a6a481841a0221cc69f75959326f264529；原产品基线986799d766e98744e29e038543299af13785ea36。

有限结论：本次范围diff、轻测和实际包同源核验无剩余阻断；**新完整prepare及独立进程verify仍须实际通过，才可称限定candidate交付**。本报告不预先签收正在运行的完整链。

## 范围调整与历史失败

0f→c9仅修改local_candidate_demo.py、mock-fixtures.json与LocalCandidate.md。产品src相对986799d仍无差异；打包工具及10case轻测试文件与0f逐字相同。目录/link/原子输出、精确loopback origin guard、readonly middleware、MockTransport、不读真实环境配置、无Worker重复驱动等边界均保留。

P-A改为生成保存后的原实例/runs、input={}，绑定原保存材料与Goal，真实Worker.once一次；同intent重复提交仍核同Run。P-B从该成功成果按原extraction-options/review/commit合同提取保存，原内部Release/instance，再明确新材料+Goal per-use review/commit；不造executor/Grant，不改变预算/lease/fence/版本/幂等。receipt以submission区分ORIGINAL_SAVED_MATERIAL_AND_GOAL与EXPLICIT_NEW_MATERIAL_GOAL_PER_USE_REVIEW，并明确pa_new_material_per_use=NOT_RUN_IN_THIS_CANDIDATE。

独立逐对象核验recipe、原source及pb_use材料均不变；原pa_use材料仅重命名为pb_target，供提取目标使用。文档准确披露前包首次全链失败与当前限定范围。这是夹具范围调整，不是产品修复；不能把新链未来PASS写成前包PASS或P-A新材料使用验证。

前包真实失败保持：run_be5e46f6c8794042bc18f2f9ca7ea6a7一次claim/fence1后仍RUNNING、error null、resource.read VERIFIED、零runtime Attempt。原目录、prepare日志与只读proof均保留；不能推断该失败由P-A重绑定导致或与旧F9同因。审查者没有重放该Run、修改产品或开启新自然fixture。

## 独立实际轻测

/workspace/sim2act-venv/bin/python -m pytest -q tests/test_local_candidate_demo.py --basetemp=/tmp/f2-local-candidate-independent-c9e9f3fc --junitxml=/tmp/f2-local-candidate-independent-c9e9f3fc.xml。

实际10PASS、0FAIL、0ERROR、0SKIP、RC0、终端1.91秒。覆盖已有目录保留、不读真实配置哨兵、普通Store拒SQLite、六类未知/link数据拒绝、输出writer不跟随link、真实loopback普通首页及授权GET、四种foreign origin和四种写方法拒绝、全库持久行不变。已有FastAPI/Starlette弃用warning保留，未升级依赖。此轻测不是完整自然链、实际浏览器或跨平台验收。

## 实际v2包独立只读核验

/workspace/local-candidate-artifacts-v2/Sim2Act-local-candidate-c9e9f3fc9787.zip：134条目，133manifest条目加manifest本身；无重复/越界/link/额外条目，逐项bytes/SHA256正确；131个Git来源文件逐字匹配c9，wheel113个产品文件与包内src逐字相同，余项仅dist-info。没有私有配置（仅.env.example）、DB、日志、tests、历史evidence、.git、node_modules或venv混入。build.log位于zip外，不作为分享deliverable。

zip SHA256：082d1e4dae16e0dece011f719fe22a9142b195f4464d46310c4ec44539f65701。
wheel SHA256：824157288bc83d3e8cff7d0e0681d9c93d5038534aa590b47f2504166711e9b0。
manifest SHA256：ee93fd3f430427b75bd747a752ffc95be702d7e33e785f910f2d175211fe1423。

未解压/安装/执行该包；主线程正在另行用v2包新venv、新目录实际执行，不将其未来结果写入本报告已通过。

## 原始独立证据

- /tmp/f2-local-candidate-independent-c9e9f3fc.xml 及 .log。
- /tmp/f2-local-candidate-independent-c9e9f3fc-delta-proof.json。
- /tmp/f2-local-candidate-independent-c9e9f3fc-package-proof.json。
- /tmp/f2-local-candidate-independent-c9e9f3fc-review-manifest.json：各原件SHA256、JUnit原始属性和范围。
- /tmp/f2-verify-local-candidate-package.py：本次逐文件Git/wheel对比只读验核脚本，SHA256 961f83d0c0ba7572b0ae279050d90e4561e83870e69ca5ffd73a15264db5af6a。

未调用真实模型/凭据探测，未执行PG、Windows、原生浏览器、远端CI、部署或锁矩阵。自然LIVE仍BLOCKED/NOT_IMPLEMENTED；前轮45P1F、定向2P、独立9P、自然双Run未触发恢复、旧F9时序未复现均保持，不合并为单批全绿。

新完整链及独立进程冷读待实际PASS和原始回执核验，之后才可称本限定candidate交付。
