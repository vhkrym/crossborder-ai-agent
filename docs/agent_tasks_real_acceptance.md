# 6C.1 真实 LLM 前端端到端验收

2026-10-29，模型deepseek-chat，真实配置从backend/.env加载，未输出Key。FastAPI 127.0.0.1:8003，Vue 127.0.0.1:5176，未使用manual_task_server或FakeLLM。仅绑定回环地址。

通过Vue提交原问题：请分析店铺 1 在 2026 年第一季度的经营情况，重点关注利润亏损、广告投放效率和库存风险，并给出改进建议。

任务ID：54d99d16-8159-4029-8116-19724ea79604。store_id=1，2026-01-01至2026-03-31，SKU不限。

后端访问日志记录POST /api/v1/agent/tasks → 202 Accepted，前端URL收到有效UUID，页面实际观察running/分析中和两秒轮询，再转completed。queued较短未在页面截取，不冒充观察到queued。

创建UTC 03:28:02.765417，开始03:28:02.777546，完成03:28:13.634021，执行10.856475秒。intent=mixed，selected_agents=[profit,advertising,inventory]。实际production runner使用create_llm和build_supervisor_graph，无测试依赖覆盖。

工具轨迹：profit_agent/analyze_profit（03:28:08.203107～03:28:09.886531），advertising_agent/analyze_advertising（03:28:09.887960～03:28:11.151233），inventory_agent/analyze_inventory（03:28:11.152004～03:28:12.450036），均为UTC，状态warning、error=null。warning是业务异常，不是模型调用失败。

报告包含20条证据，独立只读重跑确定性工具并重建证据，对全部20条发现逐字校验原值、单位和引用，全部通过。DEMO-001贡献利润-10286.6500 USD，DEMO-002 ACOS 1.322975342837716320473830916，DEMO-003 stockout、可售0，DEMO-004 slow_moving_stock。建议是人工复核的受控模板，不声称已执行。

Vue正确展示报告、建议、路由及三个工具轨迹。刷新携带task_id的URL后完成态和报告恢复，浏览器控制台error列表为空，后端本次日志未出现错误。未发现需要修复的代码问题。

业务表计数前后相同：stores2、products30、sales_records2700、ad_records2700、inventory_snapshots2700、cost_records33、data_imports12。确定性工具及复核使用只读策略；仅agent_tasks写入本次验收任务，未重置demo.db。

结论：真实前后端完整链路通过，可开始任务7的本地审批与模拟执行开发。仍无用户认证/店铺级授权，不得对公网开放；报告措辞仍为受控证据模板，验收一次成功不是统计准确率证明。
