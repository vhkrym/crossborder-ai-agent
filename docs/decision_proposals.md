# 结构化经营建议（7A）

仅供人工审核，尚未执行。没有批准、驳回、预算调整、采购或Amazon API。

## 可信数据与一致性

AgentTask当前只保存Report和TaskTrace，没有完整可信工具结果。禁止从报告文本抽取数字。生成器要求completed、有合法Report、路由及成功/警告工具轨迹，逐项验证店铺、日期、SKU一致后，重新调用现有analytics服务；只分析来源任务实际执行的专业维度。

SQLite BEGIN IMMEDIATE建立同一生成事务的快照并串行化生成器；复算及写入同一事务，不等待LLM，不修改七表。证据属于“建议生成时点”，不冒充原任务执行时点；业务数据变化可能导致与旧报告不同。evidence_json保存schema_version、generated_at(UTC)、source_task_id、store_id、日期、tool和完整SKU指标，Decimal序列化为字符串，null保留。limitations明确复算时点及业务缺失。只信任本地数据库和服务，无法防御直接篡改数据库的管理员。

## 集中规则

规则及阈值集中在app/analytics/decisions.py：

| 类型 | 条件 | 建议 |
|---|---|---|
| profit_review | 有效贡献利润<0，币种正常 | 复核定价、成本、退款 |
| ad_budget_review | 有效ACOS>1（100%） | 人工检查投放与预算 |
| replenishment_review | 现有引擎risk为stockout或at_risk | 人工复核需求和补货计划 |
| overstock_review | 有效覆盖天数>365，快照和历史可用 | 评估促销、库存处理 |
| cost_change_review | 实际采用的历史成本上涨，成本版本总单位费用上升，生效日前后现有利润服务返回有效利润率且后期更低 | 复核采购及价格 |

成本比较只在任务日期内部真实生效点划分前后区间。保存两个成本日期、单位成本及两个区间分析完整结果；不能证明成本是利润率下降的唯一原因。无法获取前后有效利润率、成本或一致币种时跳过，返回cost_change_requires_historical_margin_comparison。没有成本变化标记时不会仅凭文本推断。断货导致销量失真时仍可建议人工复核，但不虚构补货量。阈值之外的日期完整性、缺货条件复用既有分析引擎。

## 模型与幂等

DecisionProposal：UUID proposal_id，source_task_id，store_id，sku，proposal_type，title，description，risk_level，suggested_action，evidence_json，limitations_json，status，created_at/updated_at。状态仅draft/pending_review，生成时pending_review，无变更API。

复合外键(source_task_id,store_id)关联AgentTask，防跨店铺归属；来源任务、店铺日期、状态索引支持查询。唯一键(source_task_id,sku,proposal_type)。为完整幂等新增最小decision_generations记录（来源任务主键、生成时间、跳过原因），包括零建议结果也冻结。重复调用返回已保存决策及原跳过原因，不按新数据追加；要重新评估需新分析任务。数据库串行化及唯一键防并发重复。

## 迁移

```powershell
$env:PYTHONPATH=(Resolve-Path backend).Path
# 明确DATABASE_URL指向已有demo.db
python -m app.db.migrate_decisions
```

前置agent_tasks已迁移。仅增加两张决策相关表和agent_tasks(task_id,store_id)唯一索引，不改七张业务表、Task字段或已有数据。不用create_all修改旧结构，重复迁移安全；后续字段更改需新增版本迁移。

## API

POST /api/v1/decisions/generate 请求仅允许 {"source_task_id":"UUID"}，拒绝store_id/指标/证据等额外字段。响应source_task_id、store_id、proposals、skipped_reasons、reused。非completed（包括partial_failed）或无可信轨迹返回409；任务不存在404。

GET /api/v1/decisions?store_id=1&proposal_type=profit_review&status=pending_review&risk_level=high&page=1&page_size=10；GET /api/v1/decisions/{UUID}返回完整证据。无效详情ID返回404。无建议时proposals=[]，skipped_reasons说明原因。

## 前端与边界

/decisions可从最近100个completed任务选择生成，按店铺/类型/风险筛选，分页查看、点击详情、跳转来源任务报告。不提供审批/执行按钮。桌面及移动端复用现有SaaS布局。

仅本地可信演示，无真实用户身份和店铺授权；必须绑定127.0.0.1，不得开放公网。生成不调用LLM。SQLite写锁期间可能等待其他写事务，演示规模之外需优化。源报告必须合法但其自由文本不参与判断。证据JSON中的历史建议补货量是现有分析指标，不是系统授权执行量。


## 实际验收

来源真实完成任务54d99d16-8159-4029-8116-19724ea79604，生成21条：亏损3、高ACOS1、补货复核14、积压1、成本变化2。DEMO-001至005五类异常均有持久化证据。DEMO-005总单位成本15.9000→22.9000 USD，2026-02-15生效，前后区间利润率约45.28%→24.78%，不宣称唯一因果。

POST generate实际200、reused=true、21条；GET列表cost_change_review实际200、total=2；GET详情200、pending_review。重复迁移/生成成功，七表及AgentTask数量不变。浏览器验证1440/390布局、列表详情和来源任务跳转，无审批或执行按钮、无控制台error。建议生成本身不调用LLM。

回归中发现6A工具回滚归还连接后才恢复query_only可能污染连接池，已最小修复为在同一连接上先恢复再回滚。未修改经营指标公式。
