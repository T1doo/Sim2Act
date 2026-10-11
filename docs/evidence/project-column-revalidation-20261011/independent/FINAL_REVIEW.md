只读独立审查：LIMITED PASS，2026-10-11。

有限合同：至多16个已有canonical固定CSV单求和草案，全部成员已有可信派生图。一次指定共享材料的baseline_column→column绑定草案overlay；全部同源应用各执行baseline/patched三步既有DAG worker。其他源应用全部节点和人工锁保持。受影响应用内任何人工锁拒绝；非CSV、额外未知、PROJECT、SEMANTIC或MODEL_CANDIDATE依赖拒绝。现有固定CSV APP语义免责声明继续UNKNOWN，不表示语义验收。

最终独立执行为11个后端探针PASS、12个页面检查PASS，0个最终FAIL、0个SKIP。后台使用SQLite、真实Worker及NoModel（任何模型调用会失败），TestClient进程内HTTP。页面通过IPC连到同一真实HTTP路径；JSDOM载入实际产品JS/HTML，使用虚构offline.test基址，无原生浏览器和实网fetch。最终源码前后SHA及页面载入文件SHA已核一致，见product-source-sha256.json、backend-probes.json和ui-pass.json。

后端实测：四个实际worker旧/新结果30/15、GET零写、精确不可变截止拒绝、篡改Run时间不能续期、receipt插入后自然撤权全事务回滚、重签FINISH+seal的bool/int损坏拒绝、真实queued取消拒绝、receipt插入后时间达到deadline全事务回滚、四类finite未知/语义边拒绝。有限guard的四类输入为直接构造可信接口输入，其余通过真实HTTP/SQLite运行。

页面实测：同列禁用；首次明确422可改正；四真实worker允许有限候选；空checks、重复app、空output即使重签outcome hash均拒绝且恢复只GET；隐藏同key不同列POST拒绝回执后保留原body/key，历史不同定义不能解除UNKNOWN。

独审发现和已修内容：最终截止>=及提交末尾全量load；按当前route设置核预算；冻结accepted_at/deadline；不可变payload使用fingerprint防Python bool/int等值；保存完整原intent并核old/new/目标版本；peer图/授权revision；精确PASS检查覆盖；first rejection恢复；actual.output完整key集合。首次产品页面FAIL为重签空output真空every导致错误启用finalize，ui-first.log及ui-fail.json保留；修复后ui-second.log/ ui-pass.json 12检查通过。另backend-first.log为独审脚本误用delivery_graph_requests无id复合主键，非产品失败；修正后的backend-second.log、backend-final.log及冻结backend-frozen.log均保留。不同旧源码结果保留在backend-probes-prior.json/backend-probes-before-authority.json；它们不代表最后冻结版本。

静态复核：所有项目成员/current authority/图/raw locks/预算在build+load中整体冻结；start复用propose_tx/enqueue_tx，后序失败整组回滚；outcome复用inspect_job_tx的独立全部步骤核算及csv_check的Fraction oracle；finalize只有完整PASS后单事务保存FINISH/seal，并在提交前再次load及deadline guard；所有原canonical、resources、release、instance及业务数据未改。最终检查git diff --check及新增Python文件ruff --no-cache均PASS。

NOT RUN：PostgreSQL及CRUD角色、Windows、原生浏览器/Edge、旧源码创建数据后升级、完整P-A/P-B、真实模型/付费API、远端CI、部署。此次独审未编辑产品/作者测试、未推送、未扩大网络权限；最终commit/push与作者关联测试由主代理完成。不对整体F2/R0或owner语义验收作通过结论。

最终产品SHA256：
{
  "src/sim2act/project_column_patches.py": "ee612dc424628053c1103ab8018ade64d67c50db5531736760da132838f5dd43",
  "src/sim2act/web/project-columns.js": "27ef49bea4b6797d4fea99d56602ef47b758262e5cb0d5d3c116981cacab39c6",
  "src/sim2act/api.py": "4fdd0ce4e4c9ea7e6d4365e8f6830932a0bb81b993a9fe77337317fc3d7bb83d",
  "src/sim2act/web/delivery-graph.js": "37b1e99bb596df49c79eaa654f6d7763edd47f45bed37180118c54d2552bbcb7",
  "src/sim2act/web/index.html": "48bf4c35370fe254f819f9280891f5e6ae95c307116f9242663166a48a41a4fb"
}
