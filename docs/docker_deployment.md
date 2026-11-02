# Docker Compose 本地可信演示部署（8B）

## 前置条件与安全边界

Windows Docker Desktop，启用WSL2/Linux containers，Docker Compose插件；建议至少4GB可用内存及足够磁盘。无需更改全局Node/Python。容器镜像Python3.11、Node24构建Vue、Nginx非root静态服务。后端仅1 worker，无reload。

仅frontend发布127.0.0.1:8080，backend没有宿主机ports。容器内部监听0.0.0.0是正常的。没有用户登录/RBAC/店铺授权，只能本地可信使用，不得改成公网绑定。无Docker socket挂载、不使用host network、不增加数据库/队列服务。

基础镜像明确使用Docker官方registry-1.docker.io地址，避免本机某些失效加速源返回HTML。仍需Docker Hub网络可用；没有切换第三方镜像或修改全局Docker配置。基础镜像使用版本标签，尚未锁定digest，不代表供应链生产加固。

## 配置与一键启动（仓库根目录PowerShell）

```powershell
Copy-Item .env.docker.example .env.docker
# 本地编辑.env.docker，勿把密钥发到聊天或提交仓库
# 无密钥也可先启动Dashboard

docker compose --env-file .env.docker config --quiet
docker compose --env-file .env.docker up --build -d
docker compose --env-file .env.docker ps
```

.env.docker包含LLM_BASE_URL、LLM_API_KEY、LLM_MODEL，默认空；LLM_TIMEOUT默认30、LLM_MAX_RETRIES默认1。配置真实兼容端点后才可运行模型任务。未配置时Dashboard可用，AI任务保存failed/llm_not_configured，明确没有调用模型，不会伪装成功。

SQLITE_PATH=/data/demo.db必须为容器内绝对路径，保持在/data卷下；改成/data/other.db是选择另一个数据库，不是覆盖旧库。FRONTEND_PORT默认8080，可改端口数字，发布IP固定127.0.0.1。访问 http://127.0.0.1:8080；六页SPA深链由Nginx回退index.html，/api原样代理backend:8000，不需要开放CORS。ENVIRONMENT=production关闭后端API文档。

不要直接运行带真实配置的docker compose config并分享输出，它会展开运行时密钥；使用--quiet。宿主机管理员可通过docker inspect读取环境变量，本方案不是专用秘密管理系统。

## 构建与密钥隔离

两个构建上下文是仓库根目录，.dockerignore采用允许清单：只允许后端app/requirements和前端源码/锁文件/测试/配置；最后再次排除所有.env/.env.*、数据库、密钥、虚拟环境、缓存、node_modules/dist。backend/.env既不进入上下文也不COPY，Dockerfile没有密钥ARG/ENV。镜像不会复制本地demo.db。真实凭证仅Compose运行时environment注入。LANGSMITH_TRACING/LANGCHAIN_TRACING_V2固定false，避免未授权外部追踪。

后端UID/GID10001，镜像/data预设相同所有者，首次named volume复制目录权限；不以root启动或运行时自动chown宿主机目录。前端使用Nginx官方非root镜像。Python启动入口不用shell，.gitattributes统一LF，避免PowerShell路径、CRLF与chmod问题。

## 首次初始化与后续启动

数据库保存在Compose named volume demo-data的/data，不依赖F盘路径。只有目标SQLite文件不存在时调用现有seed_demo，固定种子生成2店铺/30SKU/90天数据，然后显式按序执行：任务表→决策表→审批约束/审计→模拟表。现有文件从不自动seed；要求原七表齐全且至少有店铺，再只执行迁移。已有空文件/不完整库拒绝启动，不能靠清库掩盖问题。首次初始化中断可能留下不完整文件，下次明确失败，需要备份检查后人工恢复，不能盲目覆盖。

迁移完成及foreign_key_check通过后才exec Uvicorn。任一步失败非零退出，不继续启动服务，不输出原配置异常。后端health只访问/api/v1/health，不调用模型；frontend依赖backend service_healthy。该接口是存活检查，不是持续数据库可写检查。

启动时已有AgentTask queued/running及Simulation pending/running标记interrupted，终态保留；没有可靠队列、自动重试或多实例租约，不能扩容backend。正常停止宽限60秒，强制结束的任务下次标记中断。

## 日志、停止、更新与持久化

```powershell
docker compose --env-file .env.docker logs --tail 100 backend frontend
docker compose --env-file .env.docker restart
docker compose --env-file .env.docker down
docker compose --env-file .env.docker up -d
# 更新源码后重建容器，保留卷
docker compose --env-file .env.docker up --build -d --force-recreate
```

普通down只删除容器和网络，不删除named volume。**docker compose down -v会删除持久化数据**，请勿在日常停止/更新时使用，本轮验收不运行该命令。不要改变Compose项目名后误以为原卷丢失（新项目名会创建新卷）。

## 备份与恢复

备份使用SQLite backup API，不复制可能正在写入的裸文件。先创建宿主机backups目录（Git忽略）。以下示例使用固定备份名，会替换同名备份，正式保留多版本请自行更名：

```powershell
New-Item -ItemType Directory -Force backups | Out-Null
docker compose --env-file .env.docker exec backend python -c "import sqlite3,os; from sqlalchemy.engine import make_url; src=sqlite3.connect(make_url(os.environ['DATABASE_URL']).database); dst=sqlite3.connect('/data/demo.backup.db'); src.backup(dst); dst.close(); src.close()"
docker compose --env-file .env.docker cp backend:/data/demo.backup.db ./backups/demo.backup.db
```

恢复会覆盖目标卷中的数据库，先备份当前数据、确认恢复文件并停止应用：

```powershell
docker compose --env-file .env.docker stop frontend backend
docker compose --env-file .env.docker cp ./backups/demo.backup.db backend:/data/restore.db
docker compose --env-file .env.docker run --rm --no-deps --entrypoint python backend -c "import sqlite3,os; from sqlalchemy.engine import make_url; src=sqlite3.connect('/data/restore.db'); dst=sqlite3.connect(make_url(os.environ['DATABASE_URL']).database); src.backup(dst); dst.close(); src.close()"
docker compose --env-file .env.docker up -d
```

## 常见问题

- 找不到dockerDesktopLinuxEngine：启动Docker Desktop并等待Linux Engine Ready，再docker version确认Server。
- 镜像清单/层返回text/html：常见为失效镜像加速或网络拦截，检查可信网络。不要使用未知镜像，不要把凭证写入镜像源URL。
- 拉镜像/安装包超时：先确认Docker Desktop代理/网络；项目不修改全局网络配置。缺网络不能认定构建通过。
- /data Permission denied：检查卷来源/UID10001权限；不要改成root或删卷来掩盖问题，先备份后修复卷权限。
- 迁移失败：容器不会启动Uvicorn。检查旧结构、迁移顺序与备份，不运行seed覆盖已存在库。
- 8080占用：修改FRONTEND_PORT后up，IP仍是127.0.0.1。
- Dashboard为空：确认连接的是预期named volume/SQLITE_PATH，不是宿主机demo.db；容器首次拥有独立演示数据。
- AI任务失败：先配置有效LLM三个变量，再up -d --force-recreate backend，restart不会更新环境值；无配置时failed是预期行为。

真实模型测试可能计费并把演示经营数据发送给所配置提供商；是否实际调用必须与Fake回归明确分开。审批和模拟无外部经营动作。Docker Compose仅是本地部署方案，不解决身份授权、SQLite并发和可靠队列限制。


## 本轮真实验证记录与未验证项

1. 最初docker version只有Client，desktop-linux引擎管道不存在；稍后Server可用，确认为Docker Desktop4.87.0 / Engine29.7.2 / linux-amd64，Compose5.4.0。
2. docker compose --env-file .env.docker.example config --quiet成功；解析结果验证backend无ports、frontend仅127.0.0.1:8080、named volume、service_healthy、默认sqlite:////data/demo.db、示例Key为空。
3. docker compose build第一次失败：本机加速源返回text/html镜像元数据/层；官方registry-1直连重试在auth.docker.io匿名token连接超时失败。没有修改全局Docker配置，没有使用未知替代镜像。
4. docker compose up -d --no-build --pull never实际失败：No such image crossborder-demo-backend:latest。docker compose ps成功但无容器。引擎创建了空的crossborder-demo_demo-data卷及网络，保留未删除，未执行down -v。
5. 因构建网络阻断，没有启动成功的容器，8080访问、Nginx实际代理/SPA、镜像内无密钥验证、容器重启/重建持久化和容器内真实LLM链路均**尚未验证**。本轮未调用真实LLM。
6. 宿主机Python3.13.9测试、Node24前端构建/3项测试实际通过；Docker镜像目标Python3.11，尚未实际运行。容器启动逻辑在临时SQLite完成首次初始化、重复启动不重seed、用户修改保留、迁移失败阻断、旧业务字段不兼容拒绝的回归。该测试不等于Docker volume持久化实测。

本轮未触碰宿主机demo.db。静态配置完成，可以进入8C整理README，但文档必须保留“容器实测因网络未完成”，修复Docker官方仓库访问后补做上述容器验收。


最终宿主机结果：python -m pytest backend/tests -q → **120 passed in 34.06s**；npm test → **3 passed**；npm run build包含TypeScript校验并成功，无大包警告。最终Compose静态校验再次成功。只读完整行哈希确认宿主机demo.db七张经营业务表仍与既有pre7c备份一致。Docker/Linux/Python3.11运行、named volume重启保留、真实LLM及容器业务链路仍未验证，不能用宿主机测试代替。
