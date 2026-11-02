# 本地开发（Windows PowerShell）

最新结果：此前后端166、前端3、类型检查及构建通过，本轮仅文档审查，未重跑模型或自动化。pytest 默认临时目录若出现权限错误，可用 `python -m pytest backend/tests -q -p no:cacheprovider --basetemp=.acceptance-tmp`；该目录仅为验收产物，不应提交。当前根目录未提供已创建的 .venv，安装章节须先执行。

已有离线浏览器入口：根目录 `python backend/tests/manual_task_server.py --port 8002`；frontend 终端设置 `$env:BACKEND_URL='http://127.0.0.1:8002'` 后 `npm run dev -- --port 5173 --strictPort`。入口自动创建临时种子 SQLite 并迁移，固定 Profit Fake，不调用真实模型；停止服务后临时库不保证保留。它不是生产配置开关，不能验证真实自然语言路由。独立真实演示库启动仍按下文迁移流程，勿操作原始 demo.db。

所有命令从仓库根目录执行，除非标明进入frontend。目标Python3.11；本机已验证Python3.13.9。使用`py -3.11`前须已安装对应解释器/Windows启动器；若没有py，使用已安装解释器的绝对路径替代，不要假称已测试3.11。Node.js使用24.x，与本机、Docker构建目标和Node原生TypeScript测试相符；不需要升级全局工具来运行现有项目。

## 安装

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
```

现有.env不要覆盖。环境变量优先于backend/.env；本地默认DATABASE_URL指向backend/local.db，**不会自动切到demo.db**。默认ENVIRONMENT=development启用/docs；production关闭文档。缺LLM配置时普通Dashboard可用，AI任务明确failed，不回退Fake结果。

| 配置 | 用途 |
|---|---|
| DATABASE_URL | SQLite绝对路径 |
| ENVIRONMENT | development或production |
| LLM_BASE_URL | OpenAI-compatible端点，如https://api.deepseek.com |
| LLM_API_KEY | 本地真实密钥，不提交、不输出 |
| LLM_MODEL | 例如deepseek-chat |
| LLM_TIMEOUT | 默认30秒，范围1～120 |
| LLM_MAX_RETRIES | 默认1，范围0～2 |

## 演示数据库与迁移

```powershell
if (-not (Test-Path backend/demo.db)) { .\.venv\Scripts\python.exe backend/scripts/seed_demo_data.py }
$env:PYTHONPATH = (Resolve-Path backend).Path
$env:DATABASE_URL = 'sqlite:///' + ((Resolve-Path backend/demo.db).Path -replace '\','/')
.\.venv\Scripts\python.exe -m app.db.migrate_agent_tasks
.\.venv\Scripts\python.exe -m app.db.migrate_decisions
.\.venv\Scripts\python.exe -m app.db.migrate_decision_approvals
.\.venv\Scripts\python.exe -m app.db.migrate_decision_simulations
```

seed使用真实现有模型、绝对文件定位、默认种子42、90天。不要对已有真实业务库运行seed；已有demo被修改时seed会拒绝混入，不提供自动清库。迁移必须按序，先备份；不删除已有数据。迁移版本边界见对应模块文档。

为面试创建全新独立演示库而不碰原库（若同名文件已存在，请手工选择新名称）：

```powershell
.\.venv\Scripts\python.exe backend/scripts/seed_demo_data.py --database backend/interview.demo.db
$env:DATABASE_URL = 'sqlite:///' + ((Resolve-Path backend/interview.demo.db).Path -replace '\','/')
# 在该DATABASE_URL下依次执行上面的四个迁移
```

新库没有旧任务、审批或模拟，适合完整演示；不要重置原demo.db。

## 启动

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

仅一进程，不加多worker。常规开发可自行加--reload，但重载会触发恢复，将遗留任务标interrupted；演示LLM任务期间建议不启用reload。

另一个终端：

```powershell
cd frontend
npm ci
npm run dev -- --port 5173
```

前端读取frontend/.env中的BACKEND_URL（Vite代理目标，默认http://127.0.0.1:8000）、VITE_API_BASE_URL（默认/api/v1）；前端文件**不得设置LLM密钥或任何VITE_*秘密**。修改后重启Vite。SPA路径/overview、/profit、/advertising、/inventory、/agent-tasks、/decisions。

## 回归与可选真实调用

```powershell
# 根目录
.\.venv\Scripts\python.exe -m pytest backend/tests -q
# frontend目录
cd frontend
npm test
npm run typecheck
npm run build
```

自动化使用临时数据库和Fake LLM，包含HTTP业务全链路，无外部模型请求。Node测试需要Node24的TypeScript支持。目标版本与本轮结果见[文档验收](documentation_validation.md)。

配置好真实提供商后，可在根目录显式运行（可能计费并发送模拟经营数据）：

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe backend/scripts/smoke_supervisor.py --allow-real-api --sku DEMO-001 --query '分析 DEMO-001 的贡献利润'
```

不要把真实联调和Fake测试混为一谈。smoke使用独立demo.db只读分析，任务中心则写AgentTask。无Amazon操作。

## 常见问题

- 找不到app：根目录设置PYTHONPATH=backend，或启动Uvicorn指定--app-dir backend。
- no such table：确认DATABASE_URL指向已seed并完成迁移的文件；别对旧库盲目create_all/覆盖。
- Dashboard空：选择真实店铺列表、日期2026-01-01～2026-03-31，检查proxy/backend端口。
- 前端显示422/404：检查日期顺序、SKU归属、字段是否多传；不要手工伪造状态或证据。
- 409：当前状态不允许操作，先刷新详情。approved/rejected不可重审；模拟请求复用原记录。
- 任务interrupted：进程重启的预期恢复结果；没有自动恢复队列，需要重新提交新任务。
- 任务llm_not_configured/llm_api_error：本地核对三个变量、端点和网络，勿在终端打印完整配置或密钥。
- Docker无法拉镜像：见[Docker部署](docker_deployment.md)，不把配置校验成功当成部署成功。
