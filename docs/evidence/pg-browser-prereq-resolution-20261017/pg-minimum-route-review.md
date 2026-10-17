# PostgreSQL 最小正常路线：只读审查

审查源 `4694681d281885184b0dfa52dc3f3c710a547454`。本审查仅阅读仓库，无安装、启动、PG连接、环境/凭据文件读取、apt重试或browser探针。当前无PG binaries/DSN/image/container及apt配置EACCES是父级提供的新观察；原轮证据见docs/F2/CsvPGBrowserAcceptance20261016.md，不把历史PG成功当当前服务存在。

现授权内不能凭缺失资源自行启动合规PG。pyproject.toml已有psycopg[binary]客户端依赖，不能代替PG服务端。README.md:49、docs/Installation.md:47起明确要求管理员先准备独立数据库、迁移身份和最低CRUD应用身份；API/worker不自动迁移。src/sim2act/config.py:30仅接受显式postgresql+psycopg应用URL，不自动找.env。没有已提供服务和应用配置时，改认证为trust、造新角色/密码、重用WindowsCI.ps1临时角色harness或新docker集群均不符合本次禁止新增凭据/权限/改认证的边界。禁止修改apt读权限或换APT配置绕过父级EACCES；本审查未重复读取拒绝路径。

最小平台动作：在指定环境提供一个可达的隔离PG库（可直接提供既有服务，无需本机PG binaries），预先完成当前schema迁移及现有应用角色schema USAGE/业务表CRUD，且应用角色没有superuser/CREATEDB/CREATEROLE/owner/schema CREATE等能力；平台预注入明确获准的现有应用配置（DATABASE_URL、私有DATA_DIR、MOCK/LIVE=false）和已有合成本机身份令牌，不在聊天或日志输出秘密。管理员/迁移凭据不交给API/worker。若没有这些现有身份，需平台另行获得配置/创建身份的授权；agent不能默认为已获准。

资源就绪后可复用的既有Linux入口（下列尚未执行；应用配置已由平台预置，不读/创建.env）：

```bash
PYTHONPATH=src /workspace/sim2act-venv/bin/python scripts/manage.py doctor
PYTHONPATH=src /workspace/sim2act-venv/bin/python scripts/manage.py start --port 8000
PYTHONPATH=src /workspace/sim2act-venv/bin/python scripts/manage.py status --port 8000
# 浏览器按FirstUse执行CSV文件选择、明确保存/Release/实例/Run v1及实际下载。
PYTHONPATH=src /workspace/sim2act-venv/bin/python scripts/manage.py stop
PYTHONPATH=src /workspace/sim2act-venv/bin/python scripts/manage.py start --port 8000
PYTHONPATH=src /workspace/sim2act-venv/bin/python scripts/manage.py status --port 8000
# 正常关闭/重开受保护浏览器，同身份/项目回读原实例/Run/v1，无新POST。
```

Doctor必须实际STRUCTURAL_READY并保留脱敏原件；这只确认PG结构/权限，不代表产品流程。首次浏览器四步验收按既有docs/FirstUse.md及CsvPGBrowserAcceptance20261016.md执行，新合成CSV amount=10/20→v1字符串30；quantity新提交v2=15另算新Run，不能混作重启只读恢复。不得以SQLite/JSDOM/纯接口取代PG及真实浏览器。

不能直接运行全pytest当作本次最小验证：tests/conftest.py:16的PG env会CREATE/DROP SCHEMA，runtime_role:47会生成密码并CREATE ROLE LOGIN；其权限和副作用与已经预建的普通应用角色不同。Test.ps1 -Suite R0也显式拒绝。浏览器正常保护路径由父级另查，本审查未代签；PG与四步仍NOT_RUN。
