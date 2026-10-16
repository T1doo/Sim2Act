# 明确新建准备的状态与地址同步修复（2026-10-16）

本轮只修复 P-A 准备/同意入口的“明确新建准备”，不签收实际 P-A/P-B 或历史 Cold。基线 `2b6120c944cc177e023f090ad1cecfe8368493ba`，冻结实际测试提交 `9f7be1d07aabc0c8bfbdfea56c60d72b468ec846`，分支 `dev/pa-trial-new-intent-20261016`。

## 已复现的问题与修复

父级发现旧 trial-new 只删除内存条目，仍保留 URL 中的 trial-project/trial-key；clear 清空目标卡列表后，用户再刷新目标卡，会从旧 fragment 复活 UNKNOWN，无法开始另一份准备。旧38PASS从未点击trial-new，不能覆盖此路径。

先在基线真实交付组件上增加两项红测：准备成功→new→refresh；批准并撤回成功→new→refresh。**实际2FAIL，12deselected，RC1**，均在“refresh后prepare应可用”失败；未使用前端函数替身。原始XML/log、实际HTTP资产/回执和失败proof完整保留，证明页面执行的产品JS仍为2b基线。

新建操作只允许known/rejected：先递增旧entry.operation，失效旧continuation；仅当当前地址中的project/key与明确放弃的条目匹配时删除这两个参数，以replaceState保留路径、query、其他fragment和history.state；再删除当前条目并清空视图。刷新目标卡后没有旧UNKNOWN，用户选择范围，第二个真实POST使用不同新key。准备与原key恢复也同步当前地址。

popstate/hashchange本身不调用API，只失效预览、勾选和旧响应。返回同项目合法旧链接时，建立无私有receipt的UNKNOWN，必须明确GET原key。若当前还有另一key的sending/UNKNOWN，不允许历史地址丢弃该意图，会保持当前原key及地址，先读取它。无trial参数的历史项也不能自动清除现有意图。没有全局删除cold或lost-response恢复逻辑，没有自动重发POST。

本轮仅三文件改动：natural-goal.js及两份页面测试。服务器Python、资格门、anchors、预算、模型、worker、权限、DDL与配置均无差异；原合同预算和期限不变。

## 实际回归与证据

基本修复2PASS/12deselected；新增导航矩阵5PASS/12deselected。五条新页面路径分别为：准备后新建、批准撤回后新建、back/forward旧键只读恢复、旧consent迟到回复在第二准备后释放、第二准备响应未决时back不能替换原key且可先GET恢复。都通过真实DOM点击trial-new→trial-refresh→选择范围→第二POST，并检查key不同。没有把状态直接改成成功。

最终冻结组合 **43 PASS /0 FAIL /0 ERROR /0 SKIP，RC0**，耗时66.7047393321991秒。507源文件前后哈希一致，HEAD不变，测试结束时工作区干净。原始最终XML SHA256：`0aacc13fb1f3bb4cc10b340abfbae05c873a3eedf9d17a61147e310e87253d4e`。

其中17个完整交付页面场景、398个检查、19次页面boot，每次读取实际21个HTML/CSS/JS资产并核哈希，保留91份原trial HTTP交互。包含原12场景的cold/lost-cold、准备/同意/撤回丢回执、真实400 OUTCOME_UNKNOWN、版本、过期、READ撤权和迟到结果；未知结果仍锁定新建并只GET原key。测试停用已有后台轮询以确定性观察组件历史事件，不代表产品所有后台HTTP都停止。

全部17页面场景前后实际查询Run、Attempt及非同意预算记录，断言不变；这些准备/同意操作新增Run、槽、模型外发=0，并保留HTTPTransport外发即失败的钩子。其余26项是14个原准备HTTP测试、8个旧API测试、4个旧gate回归。两个旧admission夹具明确建立并claim测试Run，仅验证拒绝，不是本入口副作用或实际模型运行。三项重复准备撤权/缺seal专测只验证拒绝和私有body读取顺序，不夸称全部43都完整比较业务前后状态。

Ruff（涉及的Python页面测试）PASS；两个JS文件node --check实际PASS。产品Python无变动，mypy本轮NOT_RERUN；上一轮tools.py两项既有错误不宣称消失。没有真实模型、付费API、凭据或权限扩张；没有部署、强推或改main/core。

红绿fixture仅在进程退出后无损压缩，逐文件及symlink读回校验后移除解包重复副本；原log/XML未动。*_PACKED.json和tar.xz保存原始字节。所有红绿失败/通过历史与最终记录随证据包保留，不累计成独立验收次数。独审仅允许读取源/Git/保存的证据，不运行SQL/API/测试；最终记录随包封存，推送后校验写在仓库外。

## 未验范围

只签收本轮新建准备缺口修复。原软件资格审查、实际P-A/P-B执行、历史Cold仍NOT_ACCEPTED；没有放宽软件门或补做真实执行，也不称后续LIVE_BLOCKED分支已达。PG、Windows、原生浏览器、人工语义、真实provider、旧库升级、远端CI均NOT_RUN。已拒绝浏览器/私有SQL工具路径未尝试。

报告与原始回执在 `docs/evidence/pa-trial-new-intent-20261016/`：完整包trial-new-intent-evidence.tar.xz、MANIFEST/ARCHIVE、公开红/最终XML、组件红测、原始HTTP及页面proof。基线2b的历史报告/包和相关保护引用保持。
