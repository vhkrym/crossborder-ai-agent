# Agent 基础架构（6A）

不接入模型、不执行经营动作。StateGraph 为 START → execute_tools → summarize → END，调用方显式指定白名单工具。工具逐个执行，无自动重试。任一失败则任务 failed，其他成功结果保留；数据警告为 warning，不伪装为错误或完整数据。

## 状态

AgentState 是 Pydantic 模型，继承工具输入参数：store_id、start_date、end_date、selected_sku、window、safety_days；另有 task_id、user_query、intent、selected_tools。中间输出 tool_results、errors、traces、execution_status；最终输出 final_answer。schema_version 预留序列化演进。字段拒绝额外输入，日期区间、SKU、工具白名单及窗口范围受校验。状态不保存 ORM/Session/连接。task_id 当前仅是调用方标识，不提供幂等或持久化。

## 独立工具调用

```python
from app.tools.analytics_tools import build_tools
from app.agents.graph import build_graph
from app.agents.state import AgentState

params = dict(store_id=1, start_date='2026-01-01', end_date='2026-03-31')
tools = build_tools()
profit = tools['analyze_profit'].invoke({**params, 'selected_sku':'DEMO-001'})
ads = tools['analyze_advertising'].invoke({**params, 'selected_sku':'DEMO-002'})
inventory = tools['analyze_inventory'].invoke({**params, 'selected_sku':'DEMO-003', 'window':30, 'safety_days':7})
state = AgentState(**params, task_id='demo-task', user_query='检查经营情况', selected_tools=['analyze_profit'])
result = build_graph().invoke(state.model_dump())
```

运行前明确设置 DATABASE_URL，测试不使用已有 demo.db。默认工厂来自现有 SessionLocal；测试通过 sessionmaker 注入独立数据库。

输出 ToolResult 包含 tool、parameters、status、data、conventions、anomalies、error。data 复用 AnalysisResponse，包含单位、币种、日期、SKU 明细和 reasons；JSON 模式金额为字符串、null 不改零。例如利润负值产生 DEMO-001:negative_profit，广告 ACOS>1 产生 DEMO-002:high_acos，库存产生 DEMO-003:stockout；缺失快照和零分母保留原业务原因。

直接函数的输入 ValidationError 交给调用方处理；LangChain 调用也执行 args_schema 校验。店铺/SKU 不存在返回 failed/store_or_sku_not_found，数据库异常返回 failed/database_error；图节点捕获其他工具异常为 tool_execution_error，不把原异常文本写入状态。

## 只读与轨迹

工具创建私有Session、关闭autoflush、不执行commit，执行后rollback并关闭；SQLite使用query_only强化只读，结束恢复连接设置。不可向工厂注入携带待提交对象的共享Session。非SQLite数据库目前只保证代码路径只读，若扩展需使用只读账号。

ExecutionTrace 包含 node、tool、parameters、status、UTC started_at/ended_at、error、summary；结果整理节点无工具名。不记录数据库URL、密钥、SQL或user_query；状态本身仍含用户输入，应由未来持久化层管理隐私。未配置远程追踪；部署时不要擅自开启外部LangSmith上报。

## 版本与限制

锁定 langgraph==1.2.10、langchain-core==1.6.0（无需完整langchain或模型供应商包）。安装元数据分别要求Python>=3.10、>=3.10且<4；本机Python3.13.9真实验证，Python3.11尚未实测。

没有Supervisor、LLM、Agent API、前端任务页、状态持久化、checkpoint、执行授权、并发调度或经营动作。final_answer只是确定性执行摘要，业务结论应读取结构化结果，不冒充自然语言智能报告。调用者需要在未来API入口验证店铺权限，store_id作用域不是用户授权机制。单次工具数最多3，重复名字去重；每次图调用重新执行，不复用输入中的旧结果。
