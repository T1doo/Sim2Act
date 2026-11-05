# v3显式模型工具名称边界

83e3ac5a正式Run run_3d62da52184744c8b6740140de36716e首响应为tool_calls，但名称read不在其声明的resource.read工具集中，原协议拒绝；用量2464 tokens，两个会话exit0/PG停止。保留原失败和捕获，不在v2回读时补认别名。

新增natural-checked-candidate4096.v3：仅新协议向模型声明read、check_candidate，执行身份固定映射至resource.read、spec.check_candidate。schema参数不变，read仍须精确匹配绑定材料；没有新增执行器/工具或接受未声明名称。recipe操作符仍用原canonical codec名称，不把模型答案或recipe重写成模板。

模型原始响应、assistant历史和后续消息保留短名称；执行调用与读取/检查回执比对只按协议固定映射。第一次测试捕获到历史读取仍直接用短名比对原注册回执，修复两处后回读链通过。传输和解析不修改原始捕获字节或hash。

sender的捕获重新验证仅从原冻结run_contracts读取协议标识；只有v3应用新解析，旧协议仍用原解析路径。原来read的v2 UNKNOWN捕获不会被新版改认VALID。空/截断接收不填补、不退预算或重发。

测试：v3工具/预算/Core三请求/旧wire兼容最终14 PASS；首两轮各13 PASS/1 FAIL保留。旧sender独立8 PASS（历史调用点修复前快照，sender本身未再改）；不合并为最终同包验收。新Core模拟模型按声明名称返回，不是改写真实模型响应。没有新联网模型请求。

当前v3尚未生成新资格/Windows包，未签正式P-A成功。图标已从83e3ac5a实际EXE提取核对，多尺寸ICO存在；最新原生窗口仍未操作，图标代码不替代生命周期和业务验收。
