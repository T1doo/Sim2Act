# CSV 应用使用切片独立复审

结果通过。独立发现并实际HTTP复现旧成功冒认发送中新意图、ABA恢复入口/冻结列不同步、合法格式但未绑定实例回执误闭合三项，首FAIL与中间FAIL保留；主任务已修复。两实例列表问题先作静态发现，初独立driver失败属等待资料不足，不能伪称旧实现运行证据。

当前6个独立oracle通过：发送中成果区分、ABA恢复、双实例切换、来源回执绑定、已接受GET-only恢复、实际撤权403及合成版本篡改。最终Grant/Principal整行保持，正常worker真实3Run/2结果；0LIVE。

source只限CSV固定材料的column参数、未发布内部实例；candidate.task_proof/extraction为真实inspect结构。没有业务API/DDL/新权限或worker变化。新PG/native/pixels仍未测，不借同时冻结CI提升。

复制清单在deliverables.json；只复制logs/json/py/cjs，不复制fixture.db或整个artifact树。复现从本repo工作目录用现有venv/NODE_PATH运行清单pytest wrappers；wrappers与driver位于本/tmp目录，均复用现有test_application_use合成fixture，控制故障明确区分。未commit/push/CI/模型请求。
