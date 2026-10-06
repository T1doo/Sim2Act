# E19独立只读复验

同工作区/root/e16_readonly_review，不改repo/无LIVE。初读API owner/跨instance/exactapproval/currentgrant/stopmetadata未发现具体越权；实际Node VM/minimalDOM复现同app迟到create callback抢回B选择，并指出history refresh旧id风险。主开发补instanceGeneration在POST、列表回读后重验；独立迟到create前B/后B、迟到refresh前C/后C，两交错PASS。不是生产数据事故或真实浏览器。

首轮18SQLitePASS/1warning4.93秒。补最小PG角色项后最终18PASS/1PGSKIP/1warning5.50秒；新增结束本页旧意图按钮独立3检查PASS：成功GET当前历史后只清本页pending、POST0；GET失败保留；GET在途切B后迟到A回执保留B和A旧意图。无新增具体问题。

最终SHA256：

| 文件 | SHA256 |
| --- | --- |
| src/sim2act/internal_api.py | 0ac3da9bd704e41209fb9e6ac2ecb9a3155cd01d2ab9118f32b96e58133e6c7e |
| src/sim2act/lifecycle.py | 4a3d5533921a601070e816280b52461ba083fc2a02f726b08667285feba0d2cf |
| src/sim2act/web/internal.js | 9518694ed171499367d13c7d20d8f2f068359424e8940cf6dbb93f0867357adc |
| tests/test_internal_api.py | 1529cb99759364efaf59b9d71acaf88dcc45adcc53592c21c34fd0b13da8c4ea |

未独立执行PG、完整aggregate、CI或真实浏览器；Node脚本仅合成最小DOM。PG/CI由主开发另记录。不签收正式发布/完整P-A/P-B/F2或视觉。

最终aaf07f4另对app.js通用showRun diff做只读静态复核：内部结果明确0模型/结果版本；回读和命令返回检查task/project/token/请求generation，无具体新增错误。SHA256 eff6180cea9e2a83cac7d0141efc0e0babca34c8f153fd678ebf6ebaa5e1aad9与主开发一致；未独立执行新增29DOM/PG/CI。前四文件hash保持最终复验值。
