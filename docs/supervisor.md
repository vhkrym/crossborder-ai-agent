# Supervisor 编排（6B）

保留6A build_graph，新增 build_supervisor_graph(llm, session_factory)。无业务API、持久化、审批或经营动作。

## 配置与调用

backend/.env.example：LLM_BASE_URL、LLM_API_KEY、LLM_MODEL；LLM_TIMEOUT 默认30秒（1～120），LLM_MAX_RETRIES 默认1（0～2）。Key使用SecretStr。适配 langchain-openai==1.6.0 / ChatOpenAI，普通文本JSON加Pydantic校验，不依赖兼容端点支持工具调用或原生JSON模式。无效JSON、空输出、超时和API错误明确失败；不保存原异常、Key或请求头。

```python
from app.agents.llm import create_llm
from app.agents.supervisor_state import SupervisorState
from app.agents.supervisor_graph import build_supervisor_graph
state = SupervisorState(task_id='demo',store_id=1,user_query='分析利润与广告风险',start_date='2026-01-01',end_date='2026-03-31')
# 单意图例：user_query='分析商品贡献利润'
result = build_supervisor_graph(create_llm()).invoke(state.model_dump(),config={'recursion_limit':10})
```

RouteDecision：intent 为 profit/advertising/inventory/mixed/unsupported；selected_agents 最多三个、不重复、与意图一致；reason 为规划理由，confidence 可空，自评不是校准概率。拒绝额外字段，模型不能传入店铺或日期。用户权限仍需未来入口校验。

## 图与权限

START → Supervisor → 所选专业Agent（按profit、advertising、inventory顺序）→ Report → validate → END。Supervisor失败或unsupported直接结束。条件边无回边、每专业节点最多一次。最多七节点、五次LLM调用，重试只由SDK有限执行。

专业Agent闭包仅持有自己的一个工具，参数来自可信状态，模型不能更改店铺/日期/SKU。复用6A只读Session和业务服务，每次调用记录UTC时间、参数、状态、错误码和摘要。专业解释失败或工具失败保留其他结果，有可用报告则partial_failed，全部失败则failed。

状态继承6A输入、工具结果、错误和轨迹，新增route、evidence、expert_selections、report。不保存ORM。执行图独立，未覆盖6A。

## 证据报告

Evidence包括id、agent、sku、metric、工具原值、单位、源路径。专业Agent只能选择自己证据ID，Report只能选专业Agent已验证的ID，伪造/越权引用拒绝。中文报告字段为 problem_understanding、key_findings、business_risks、suggested_actions、evidence_and_limits、evidence_ids。

所有数字由程序从工具原值填模板，LLM不能输出数字或自由经营结论；最终重新渲染并比对。null显示不可计算，比例用小数、金额保留十进制字符串。例如：DEMO-001：贡献利润 = -10286.6500 USD [profit:0:contribution_profit]。退款不改变销量，广告归因额不等于店铺销售额，在途不算可售，需求不足不编造补货量。建议固定为人工复核，不声称已执行。不同指标口径不合并或自动裁决，失败和限制明确列出。

为可靠性第一版文案受限：LLM负责路由和证据重点组织，解释采用受控模板。报告最多20个引用，不能保证模型选全关键证据。真实路由效果与兼容端点格式仍需验收。

## 测试

```powershell
python -m pytest backend/tests -q
# 可选：发送demo分析数据给配置提供商，可能产生费用
python backend/scripts/smoke_supervisor.py --allow-real-api --query '分析利润与广告风险'
```

自动化使用Fake LLM和临时数据库。本次未执行真实smoke，不读取或输出Key。Python3.13.9验证，3.11未实测。状态包含用户问题，未来持久化需隐私策略；部署勿擅自启用远程追踪。
