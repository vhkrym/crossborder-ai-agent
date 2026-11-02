# 审批后本地模拟执行（7C）

仅创建本地模拟工单/评估草案，不调用LLM、Amazon或其他平台，不修改预算、价格、销量、库存或成本，不声称指标改善。

## 模型与状态

DecisionSimulation：UUID simulation_id，唯一proposal_id，source_task_id，approval_audit_id，store_id，sku，proposal_type，action_type，status，input_snapshot_json，output_json，limitations_json，error_code/error_summary和UTC创建/起止时间。复合外键proposal/store、来源任务外键、审批审计外键，按店铺/日期和状态索引。

创建仅接受approved且存在对应approve审计的决策。输入快照使用Pydantic SimulationInput，完整保存创建时Proposal与Audit；Decimal证据为十进制字符串。输出SimulationOutput明确simulation_only=true，包含来源、动作、摘要、输入依据及限制。无外部凭证。

pending → running → simulation_completed / simulation_failed；启动时pending/running → interrupted，不自动重试，不宣称可靠队列。唯一proposal_id加SQLite BEGIN IMMEDIATE防并发重复创建，pending抢占使用条件UPDATE；终态不可重跑，同决策后续请求返回原记录。模拟为短小本地计算，POST同步线程内完成，不需要后台调度；遇到并发请求可返回原pending/running。数据库不可写时可能保留未完成状态，启动恢复处理；仅支持单进程本地演示。

终态记录由数据库触发器禁止UPDATE，所有模拟历史禁止DELETE；API无PATCH/DELETE。数据库管理员仍能绕过文件/触发器，非防管理员审计系统。

## 五类动作

| 决策类型 | action_type | 产物 |
|---|---|---|
| profit_review | profit_review_ticket | 利润复核模拟工单 |
| ad_budget_review | ad_optimization_assessment | 投放优化评估模拟工单 |
| replenishment_review | replenishment_plan_draft | 补货计划评估草案，不新增数量 |
| overstock_review | stock_clearance_assessment | 库存清理评估模拟工单 |
| cost_change_review | cost_review_ticket | 成本复核模拟工单 |

输入依据可能含原分析中的建议数量，该数字仅作为历史证据，不是本次下单量。输出不编造收益/ACOS改善/补货量。

## API

POST /api/v1/decisions/{proposal_id}/simulate 请求{}，禁止店铺、身份、状态及任何经营参数。200返回simulation_id/status/reused；未批准或缺少审批审计409，不存在404。

GET /api/v1/simulations?store_id=1&status=simulation_completed&proposal_type=cost_change_review&page=1&page_size=10 返回items/total/page/page_size。GET /api/v1/simulations/{UUID} 返回完整输入快照、输出、审批关联、错误和时间。仅本地可信演示，无真实身份授权，不得绑定公网；详情UUID不构成访问授权。

## 迁移

```powershell
$env:PYTHONPATH=(Resolve-Path backend).Path
# DATABASE_URL明确指向已有demo.db，审批迁移已完成
python -m app.db.migrate_decision_simulations
```

仅增加decision_simulations及保护触发器，显式事务、重复安全，不修改已有表。已备份backend/demo.pre7c.db，迁移两次；七表、DecisionProposal和DecisionAudit完整行哈希均与备份一致。备份.db受gitignore保护。

## 实际本地验收

经Vue二次确认，对approved DEMO-005决策ffaf606b-034c-4282-ab8b-68b9a64f353b创建模拟：

```json
{"simulation_id":"e89238a8-fac0-4aee-996e-a0a95ea4c223","status":"simulation_completed","reused":false}
```

重复POST实际200、reused=true；simulation_only=true，action_type=cost_review_ticket，approval_audit_id=84e28c1b-9cd0-4b96-8e45-65dc92422ae9。proposal仍approved，审计日志未改变；七表、决策及审计与pre7c备份逐行SHA-256一致。前端展示结果、完整建议/审批快照、限制与历史，可跳转来源决策/任务。

后端110 passed in 26.43s，原97项无回归，使用临时库、不调用模型；覆盖五动作、状态拒绝、幂等并发、失败与真实pending/running遗留恢复、外键和API不可修改。npm run build含vue-tsc通过，无大包警告。浏览器验证1440和390视口、二次确认与完成结果、无控制台error；390视口document宽375，无横向页面溢出。

已完成7C；没有真实执行、可靠队列、自动重试或生产级身份鉴别。模拟完成只表示本地工单记录生成成功，绝不表示经营目标达成。
