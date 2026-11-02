# Agent 任务持久化与本地任务中心（6C）

## 增量迁移

已有七张业务表不变。AgentTask 使用独立 metadata，不混入旧七表初始化测试。迁移只对 agent_tasks 执行显式 Table.create(checkfirst=True)，不对旧库运行 create_all 进行升级、不重建业务表。重复执行安全；仅适用于本次新增表，将来改变任务字段须新增版本迁移。

```powershell
$env:PYTHONPATH=(Resolve-Path backend).Path
$env:DATABASE_URL='sqlite:///' + ((Resolve-Path backend/demo.db).Path -replace '\\','/')
python -m app.db.migrate_agent_tasks
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
# 另一个终端
cd frontend
npm run dev
```

已对现有demo库执行迁移两次，stores=2、products=30、sales/ad/inventory各2700、cost=33、imports=12，业务记录数全部不变。任务表有店铺外键，索引(store_id,created_at)、(status,created_at)。UUID由服务生成。UTC时间写入无时区SQLite字段，工具轨迹时间为ISO UTC。

## 状态和后台机制

queued → running → completed / partial_failed / failed / unsupported。服务启动将遗留queued和running原子更新为interrupted，提示重新提交，不自动重放。终态不可再次启动。抢占采用UPDATE WHERE status=queued的rowcount判定，重复或并发执行仅一方成功；完成仅允许running转终态。手动重复POST会创建新任务，不提供跨请求幂等键。

FastAPI BackgroundTasks运行同步函数于线程池，响应发送后执行，不阻塞事件循环。创建Session、抢占Session、分析工具Session、保存Session彼此独立，网络执行期间不长期持有事务。异常保存稳定错误码，不保存原始provider异常、请求头或Key。LLM超时及有限重试沿用6B配置；没有可取消的全任务硬超时。进程被杀可能来不及保存轨迹，重启标记中断。后台持久化数据库故障时可能仍留running，需重启恢复或人工检查。

仅支持单个Uvicorn进程，不支持多worker/多实例共享恢复逻辑；否则一个进程启动可能打断另一个实例任务。线程池不是可靠队列，不保证重启恢复、不提供取消/租约/分布式调度。正常退出等待后台完成，强制退出在下一次启动恢复。

## JSON和凭证边界

report_json严格使用Report.model_dump(mode='json')；trace_json为TaskTrace：schema_version、RouteDecision、ExecutionTrace列表。Decimal在报告里为字符串，不保存ORM。结构化路由与工具轨迹在终态一次写入，运行中不提供虚构百分比，也不提供实时节点流。脱敏已配置模型密钥及Bearer字符串，错误只保存允许码；不应在问题或SKU中提交任何凭证，任意自定义秘密不能保证自动识别。

## API

POST /api/v1/agent/tasks：输入店铺、问题、日期和可选SKU，拒绝状态及额外字段；202返回task_id/status/created_at。

```json
{"store_id":1,"user_query":"分析 DEMO-001 的贡献利润","start_date":"2026-01-01","end_date":"2026-03-31","selected_sku":"DEMO-001"}
```

GET /api/v1/agent/tasks?store_id=1&status=completed&page=1&page_size=10 返回items、total、page、page_size；按创建时间倒序，ID作为稳定并列排序。

GET /api/v1/agent/tasks/{UUID}?store_id=1 返回基本信息、status、selected_agents、intent、report_json、trace_json、error_code/error_summary及时间。不存在或与显式store_id不匹配返回404；SKU必须属于当前店铺。列表要求store_id，详情store_id可选，这不是用户权限校验。

## 前端

/agent-tasks：真实店铺列表、demo默认日期、可选SKU、示例问题、提交保护、两秒轮询、终态停止；任务ID存URL query，刷新可恢复查看。离开页面清理定时器，历史分页可重新打开任务，部分失败/中断明确提示。轮询请求失败会停止并展示错误，点击历史任务可重试读取，不自动重复提交任务。建议从未执行任何经营动作。

## 安全和验收边界

仅限本地可信演示，没有真实用户认证和店铺授权；后续在get_task_service/路由依赖处加入principal和授权，不得绑定0.0.0.0暴露公网。新迁移添加任务表，业务数据不变，不覆盖demo.db。

自动化与浏览器QA使用Fake LLM、临时数据库。manual_task_server.py是独立手工验收服务（端口8002），不用于正常运行。真实LLM页面端到端本轮未执行；6B.1真实模型验收不能冒充本轮持久化端到端验收。任务7审批和模拟执行均未实现。


## 本轮实际验收结果

后端 python -m pytest backend/tests -q：85 passed in 18.83s（原76项无回归）；npm run build：TypeScript及Vite通过，无大包警告。浏览器在Fake LLM临时库验证提交、运行态、轮询完成、结构化报告/工具轨迹、历史点击、刷新task_id恢复；1440×900和390×844正常，控制台无error。未做真实LLM页面调用。

实际POST返回202：

```json
{"task_id":"5f8de059-06c9-40e7-8624-f8ecddc4cadf","status":"queued","created_at":"2026-10-29T03:21:31.855792"}
```

该请求客户端总耗时2.25秒，Fake runner特意延迟3秒，响应未等待图执行结束。列表GET返回200，total=2、page=1、page_size=1。实际完成任务详情GET返回200（节选）：

```json
{"task_id":"b78d6a52-e8f4-4f85-bfd5-a1cbb9234982","status":"completed","intent":"profit","selected_agents":["profit"],"error_code":null}
```

报告包含 DEMO-001贡献利润 -10286.6500 USD 以及 profit:0:contribution_profit 引用；工具轨迹包含 profit_agent/analyze_profit/warning 和UTC起止时间。该临时库生命周期仅限验收进程，不是生产业务数据库。
