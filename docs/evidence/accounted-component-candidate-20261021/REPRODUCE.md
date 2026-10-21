# 无业务窗口的复现

本次实际环境 CPython 3.12.14、pytest 9.0.2。测试在独立 `/tmp/sim2act-accounted-component-20261021` 目录运行，仅读既有交换字节。新增 repo test 根据已导入 `natural_spec_runtime.__file__` 定位实际 checkout，不硬编码保存环境。

在仓库根运行以下命令会创建一个新的临时目录，只复制本片 tripwire harness 和当前新 test，不覆盖存证或加载 repo conftest。不会运行原业务 fixture，不创建 Store/Worker/InternModel、不打开 DB、不调用 Mock 或网络。

```bash
task_proof_dir=$(mktemp -d /tmp/accounted-component-replay.XXXXXX)
cp docs/evidence/accounted-component-candidate-20261021/HARNESS/* "$task_proof_dir/"
cp tests/test_cold_accounted_component.py "$task_proof_dir/"
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH="$PWD/src" .venv/bin/python -B -m pytest \
  -c "$task_proof_dir/pytest.ini" --confcutdir="$task_proof_dir" \
  "$task_proof_dir/test_cold_accounted_component.py"
```

实际静态检查：

```bash
.venv/bin/ruff check src/sim2act/cold_accounted.py \
  src/sim2act/_cold_accounted_values.py tests/test_cold_accounted_component.py
.venv/bin/mypy --follow-imports=silent src/sim2act/cold_accounted.py \
  src/sim2act/_cold_accounted_values.py
```

输出位置与 timing 会变化；以本目录原始 RUN 文件记录实际本轮结果。测试中的 producer/full-guard stub 只用于本组件连线与复制反例，不可移到产品代码当作生产证明。无新业务授权、第四窗口、G0 性能或完整 PB 验收含义。
