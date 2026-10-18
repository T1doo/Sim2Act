# 首次直接更换已有授权 CSV

基线 `6a8444fbae08cc14ebe0c25de673b9788429815d`。上一片[首版保留Goal换列](InitialColumnRevision20261018.md)仅修改同一CSV的列，不等于换材料，也不关闭本缺口。原F2-T07/T08要求在明确依赖变更后独立检查、精确版本批准、保留实例及旧数据；本片复用原材料修订/CHECK/Release/采纳合同，不添加executor、Grant或权限入口。

已实现的有限范围：原spec1/Goal1的业务实例可直接选择另一份已有用户/项目/App三方授权的CSV，无需先做列修订或下一Goal。原Release尚未固定列，界面须明确选择A和B共有的数值列；首版新规格固定该列，因此影响明确包含SOURCE及ACTION，仍APP独立重验并尊重ACTION人工锁。旧已采纳材料分支的冻结结构和计算不变，原Release/Goal/材料/权限/历史不覆写。新Run使用B的新内容/hash，旧A结果仅历史；语义UNKNOWN、人工PENDING。

原first source descriptor明确为ORIGINAL_CSV_RELEASE/spec1/column:null，不伪造已采用的父修订。只读历史重构使用原不可变Release和完整Goal版本；当前新工作仍检查原graph、权限、Goalhead、数据/实例CAS。原key/双锚/恢复和页面账号项目实例代次隔离继续复用，未受理和结果不明仍按原控制器处理。

授权前置必须区分：普通材料导入只授用户及项目运行身份，当前没有给既有CSV App追加材料权限的页面；本片不补或绕过它。“已有授权”必须包括App对B的resource.read与data.aggregate_csv。合成验收会在测量和derive之前明确预置这两项App/B Grant，其他创建走原API；产品换材料操作前后Grant逐字相等。不能将此前置说成空白页面已授予B或普通未授权材料可直接使用。

最小实际链：初始Release1、原Goal1、同一App/iid，A amount10/20→旧30/v1；直接材料入口选择B amount100/250，保留amount及Goal，独立CHECK350、分别确认Release2及原iid采纳，再显式新Run350/v2，冷页读取旧A30和新B350及各自Release。无Goal PUT，无任何先行列修订或采用。用原Worker/mock固定工具，不调用真实模型。

既有全部失败/observer更正/封存保持。沿用Git/auth拒绝，不重试远端、不换路；同一普通开发分支本地提交。Win/native、PG、真实语义/人工签收及远端CI未执行不认领。

## 实际闭合与边界

本片完成首次直接换材料：原spec1/Goal1不先换列，显式选择已有授权B及共同amount列；原Worker执行旧A30/v1、独立CHECK B350、新业务B350/v2，冷页从同一实例读取各自Release/hash。结果仅证明合成固定求和；语义UNKNOWN、同Run人工PENDING。

API三个针对节点PASS（pytest17.77秒），覆盖材料/hash/权限拒绝、ACTION锁和原证明缓存的写入/事务/撤权边界；测试导入排序后仅两项import交换，保留执行hash及独立重构/AST桥。最终安装包新页21项检查/84次HTTP、冷页9项检查/56次GET，三个普通Worker job均SUCCEEDED/fence1，0模型Attempt/Reservation；完整Grant表及Goal/原历史不变。安装并非干净机器依赖下载验证，JSDOM真实HTTP和原事件处理器不等于原生浏览器验收。

此前两个混合API窗口180/240秒超时，旧兼容长节点NOT_COMPLETED；fixture HTTPX错误、18秒终态观察失败、整页300秒超时、Ruff导入排序失败和只读剖析辅助字段错误均保留原件，不改签。一次Release剖析显示原材料证明重复15次；复用既有同事务/写epoch缓存，每次仍重新授权及读取原源字节，写入失效。合成启动器为等待Worker保留下一次写入时机。最终整页观察边界按三个原300秒Run设900秒，产品Run预算、租约、执行器和权限不变；不以较短旧窗口唯一归因为饥饿。

最终证据、源码桥、失败原件及有限独审见[交付记录](../evidence/first-material-direct-20261018/README.md)。App追加B授权页面、跨软件版本自动接续、真实语义与签收、Windows/native、PG及远端CI仍未验证或未提供；完整F2/R0不提升。沿用远端访问拒绝，本轮不重试、不推送，当前远端HEAD未知。旧满盘最终独审未恢复。
