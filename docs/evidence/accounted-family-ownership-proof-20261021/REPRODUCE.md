# 离线复现

实际执行工作区 `/workspace/Sim2Act`，CPython 3.12.14、pytest 9.0.2。原始执行目录 `/tmp/sim2act-accounted-proof-20261021`。业务禁止 tripwires 见 conftest；不加载 repo conftest/自动插件、不创建业务 fixture、不开 DB、不建 Worker/InternModel、不调用 Mock/网络，不重放业务窗口。

为免重写证据原件，复现时将本目录的 `PROTOTYPE/*.py` 与 `pytest.ini` 复制到一个新的临时目录（如 `/tmp/accounted-proof-replay`）；在 `/workspace/Sim2Act` 根目录运行：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=/workspace/Sim2Act/src:/tmp/accounted-proof-replay \
.venv/bin/python -B -m pytest \
  -c /tmp/accounted-proof-replay/pytest.ini \
  --confcutdir=/tmp/accounted-proof-replay \
  /tmp/accounted-proof-replay/test_accounted.py
```

输入仅读取已归档的 `docs/evidence/g0-monitored-third-20261021/RUN/mock-exchanges.jsonl`。test 文件中的 REPO 固定为本次路径；异地复现先将其改为实际仓库根，明确这不是本次原件。`owned_graph.before-unicode.py` 是修复前原型，不能覆盖最终版本用于正常通过结果。

历史执行顺序：完整首轮 7 passed/3 failed→仅选失败相关项定位轮 1 passed/2 failed→完整 10 passed→独审 surrogate 反例用修复前代码且 importlib 模式实际复现 1 failed/10 deselected→修复后完整 11 passed。所有日志和各轮 tripwire 输出保留；最后一轮耗时只解释离线测试，不预测 G0。
