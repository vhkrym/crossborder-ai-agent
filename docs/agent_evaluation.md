# Agent 评测集与效果评估（8D）

> 8D.3 离线准备：新增 36 条独立安全路由样本、冻结 baseline/candidate 和隔离对照入口；真实对照尚未运行，生产 Prompt 未变。详见 [Supervisor 安全路由评测](supervisor_safety_evaluation.md)。Fake 契约通过不代表候选 Prompt 真实有效，须获用户预算授权后再调用 API。

> 8D.2-C 实测更新：冻结的 15 条 v2 DeepSeek 评测已完成，Strict/Acceptable Agent 与 Tool 均为 14/15，发现 unsupported-05 纯执行请求误路由为 advertising。详见 真实分层报告（材料暂缓公开，未随Git交付） 和 脱敏 JSON（材料暂缓公开，未随Git交付）。本轮未修改生产 Prompt/Graph/标签，未扩大至 60 条；Answer Completeness 仍未评估。后端回归 144 项通过。

> 8D.2-B 更新：新增冻结的 supervisor-v2，保留全部原问题和严格标签，仅 dual-01、dual-09 增加可接受 Agent 集合。详见 用户采纳的规则、v1/v2 差异及双轨结果（材料暂缓公开，未随Git交付）。这不是第三方独立人审。本轮未调用真实模型。

## v2 双轨评分使用

默认仍为 v1，旧命令与严格指标字段兼容；通过 `--dataset v2` 显式选择新版本：

```powershell
python eval/run_offline.py --dataset v2 --output eval/results/offline-v2-8d2b
python -m pytest backend/tests -q
```

v2 另有 `manifest_v2.json` 校验 SHA-256，不覆盖 v1。Strict Agent/Tool 始终按原标签评分；Acceptable Agent/Tool 按事前可接受集合评分。Intent 与 micro/macro 指标继续严格。工具集合使用真实生产映射；dual-12 不接受 inventory 单路线。Scope Integrity 对照原始输入及执行参数，旧记录无证据时为未评估；Evidence Grounding 由确定性工具独立复算；Answer Completeness 明确未评估。没有从 completed 或集合匹配推断回答完整性。

v1/v2 实际离线主集各 60/60、故障检查各 8/8，Strict/Acceptable Agent/Tool 均为 60/60，Scope 为 60/60，证据为 50/50（10 个 unsupported 不适用）；属于 Fake 契约结果，不是自然语言效果。全部后端 140 passed in 42.42s。下文旧阶段记录按原时间保留。

> 8D.1 更新：已完成 60 条规则与语义辅助复核（待独立人工确认），保持 v1 标签和哈希不变；2026-10-29 实际运行 5 条 DeepSeek 冒烟。详见 标签复核（材料暂缓公开，未随Git交付） 与 真实结果及限制（材料暂缓公开，未随Git交付）。下文“未评测”为 8D 阶段历史记录，不代表 8D.1 当前状态。未扩大至 15 或 60 条。

## 目标与状态

评测拆成两层：离线执行契约与真实模型效果。生产Supervisor、专业节点、Prompt、Analytics公式保持不变。所有评测使用新建临时SQLite、固定种子42，seed后用mode=ro重新连接；退出时对数据库文件SHA-256复核。没有AgentTask/DecisionProposal/审批/模拟写入，也不读取或修改demo.db。

**真实模型本阶段未评测。**此前少量DeepSeek smoke验收不是本数据集准确率，不能合并或替代本次效果评估。真实评测仅在显式--allow-real-api后调用，会计费并发送模拟数据。默认测试离线。

## 数据集

`eval/datasets/supervisor_cases.jsonl`共60条：利润10、广告10、库存10、双Agent12（三种组合各4）、三Agent8、unsupported10。版本由manifest.json记录为supervisor-v1，运行报告额外保存原文件SHA-256和UTC运行时间。

每条包含case_id、user_query、store_id、start_date、end_date、expected_intent、expected_agents、expected_tools、expected_status、tags，可选selected_sku/window/safety_days。店铺与SKU按固定演示库定义，日期包含空数据区间；问题覆盖自然表达、成本/退款、归因/点击、缺货/积压、零分母、店铺2、SKU和越权动作请求。

问题为逐条策划的静态中文业务样本，标签按现有能力在真实评测前预设，不来自模型预测。由助手辅助编写，**尚未经过独立人工复核**，不能宣称多人标注一致性。后续可人工审查并发布新数据集版本，但不得根据模型错误反改标签来刷分。非全量模板替换，不做自然语言范围抽取：店铺、日期、SKU始终取显式字段；文字中提到新日期不代表允许模型覆盖表单。

单Agent intent与agent同名；多Agent intent=mixed；unsupported为空agent/tool集合。正常业务数据不足仍可completed并带warning/null；这不代表数据充足。只要求执行真实平台动作、不要求分析的样本标unsupported；不能因为模型将其误路由advertising就修改标签。

## 实现与运行

```powershell
# 仓库根目录，不调用真实API
python eval/run_offline.py
python eval/run_offline.py --case-id profit-02 --case-id advertising-02
python eval/run_offline.py --limit 5 --output eval/results/offline-small
# 默认拒绝真实调用，此命令应返回非零
python eval/run_live.py --limit 1
# 以下为可选计划，须有真实配置/网络并明确同意费用；本阶段没有执行
python eval/run_live.py --allow-real-api --case-id profit-02 --case-id advertising-02
python eval/run_live.py --allow-real-api --limit 5 --output eval/results/live-small
# 全量60条，真实调用次数和费用明显增加
python eval/run_live.py --allow-real-api --output eval/results/live-full
python -m pytest backend/tests -q
```

程序路径基于仓库文件定位。run_live读取生产LLMSettings/create_llm，使用同一build_supervisor_graph；通过stream updates记录真实节点和状态，不另写分类Prompt。生产图只接收问题与可信范围，不接收expected标签。支持重复--case-id、--limit和输出目录；默认全量，未知case/非法limit报错。

ObservedLLM包装invoke以记录API响应usage_metadata或response_metadata.token_usage；不更改Prompt，不估算token。运行报告不保存Key、请求头、原始异常或模型自由reason。真实评测强制关闭远程LangSmith追踪；端点元数据仅scheme/host，模型名、超时、重试上限另记。

JSON和Markdown写入指定目录，默认eval/results/offline或live。输出目录被Git忽略；仓库保留固定数据集与本文真实结果，克隆后须运行命令生成完整案例报告。

## 离线方法：不是模型准确率

ScriptedLLM借鉴现有FakeLLM方式，按预设oracle路由，再选择给定证据ID。这是白盒契约fixture，不是中文分类器。即使Agent集合完全匹配，也只能说明在该指定路线下图、权限、状态和证据链运作正常。

60条主集以外另有8项故障契约：timeout、API异常、坏JSON、伪造证据ID、单工具失败隔离、跨店铺SKU拒绝、报告数字篡改拒绝、只读工具范围。注入错误被成功拒绝是防护通过，不应算作正常模型准确率提高。

每个报告从工具参数独立重跑确定性分析，比较原结果，重新生成可信Evidence并渲染报告核对，不单纯相信Graph自己标记成功。数值篡改检查覆盖key_findings及其他报告段落；不一致发现按条计数，属于受控模板的保守断言检查，不是通用自由文本事实验证器。

## 指标定义

所有案例包括失败、超时均留在分母，绝不静默剔除。

| 指标 | 定义 |
|---|---|
| Agent Set Exact Match | 有有效route且预测agent集合等于标签，除以全样本数；不依赖顺序 |
| Intent Exact Match | intent相同/全样本；与agent集合分别报告 |
| Agent micro P/R/F1 | 累计三个agent标签的TP/FP/FN；F1=2TP/(2TP+FP+FN) |
| Agent macro F1 | 对profit/advertising/inventory三个类别F1求均值；零分母类别为null，仅对已定义类别求均值并保留per_agent，不凭空补0或1 |
| Tool Set Exact Match | trace中的实际调用集合等于预期工具集合/全样本；失败调用仍是调用 |
| Unsupported P/R | 将unsupported视为正类；识别失败会计入FN |
| Workflow Success | 无errors且终态completed或unsupported/全样本；**不代表路由正确** |
| Expected Status Match | 实际终态等于标注终态/全样本，辅助检查执行语义 |
| Evidence Pass Rate | 有报告且独立校验通过/预期非unsupported的全部样本；缺报告或失败不算通过 |
| Evidence Failures | 实际生成报告但校验返回false的数量；没有报告另由通过率和错误分类反映 |
| 无依据数值断言 | 无法由独立工具证据重建的发现条数，及其他段落数字突变的字段数；故障注入另列 |
| 工具越权 | 调用超出预测agent白名单，或trace范围偏离可信输入的次数 |
| 状态错误 | 非合法终态、completed带errors、unsupported调用工具、非法状态边或重复节点 |
| P50/P95 | 所有案例图执行耗时的线性插值分位数，包含失败；不含seed、独立复核和文件写入 |
| usage | 仅API真实响应字段，缺失null；已知调用token合计并标calls_with_usage/complete，非完整覆盖时只能看作已知部分，不能称为总账 |
| 模型调用失败 | 包装invoke抛错的逻辑调用次数，SDK内部重试不逐次可见；坏JSON另列model_error |

所有零分母返回null。模型、工具、路由、证据错误可同时出现，分类统计不可简单相加当唯一失败数。completed与证据通过都不代表建议有业务效果。

## 实际离线结果

运行时间（UTC）：2026-10-29T07:39:28.991193+00:00；数据集SHA-256：`e2e8970bd1e245bf82fcfd431da08f6e2aaeae2b65ba493737481b6ee630375f`。

| 项目 | 实测 |
|---|---|
| 主集 | 60通过，0失败 |
| 故障契约 | 8/8通过 |
| 工具越权 | 0 |
| 状态转换错误 | 0 |
| 主集证据校验失败 | 0 |
| 主集无依据数值断言 | 0 |
| 主集独立证据通过 | 50/50；unsupported不适用 |
| 离线P50/P95 | 0.0654s / 0.1886s |
| token usage | null（Fake不返回usage） |
| 真实模型 | 未评测 |

主集路由/tool集合匹配为预设契约结果（60/60），不作为自然语言准确率发布。没有真实模型输入/输出token，字段为null。报告中的Fake invoke次数仅用于覆盖统计，不是付费请求数。

## 错误案例与防护

- timeout/api：保存failed及脱敏llm错误码，没有工具和伪成功报告。
- bad JSON：失败进入明确错误状态，未偷偷当成unsupported。
- forged evidence：专业/报告节点拒绝伪造引用，不生成可信报告。
- 广告工具故障：利润仍可保留，任务partial_failed，不冒充完整成功。
- 店铺1指定店铺2的DEMO-016：工具失败，不借用其他店铺数据。
- 篡改报告为无依据999999.99：独立证据校验失败并统计不一致断言。

以上都是实际离线故障检查，不是真实模型错误案例；真实错误案例本轮暂无，因为未运行真实评测。

## 环境与限制

Python3.13.9，LangGraph1.2.10、langchain-core1.6.0、langchain-openai1.6.0，与生产图共用。目标Python3.11/容器仍未实测。Fake结果只验证契约；真实准确率、token成本和时延均未评测，不能用本机毫秒级离线时间预测云模型表现。固定小样本尚无独立人审和多模型重复实验，不具有统计代表性。

本轮未改业务公式、生产Prompt或标签以追求模型分数。后续应先独立复核标签、补行动请求/歧义/注入/缺失数据案例，冻结新版本，再按明确预算运行真实模型，报告每条预测和所有失败，比较不同模型/多次运行及置信区间。工具正确性、路由表现、证据安全、建议业务有效性必须分别评估。


最终全后端回归：**130 passed in 39.14s**，原120项无回归。run_live未带--allow-real-api实际被拒绝，未读取Key进行请求。所有评测代码独立于生产图/公式，无生产业务模块改动。真实模型API统计、真实P50/P95与真实token成本均未评测；模型温度采用既有适配层/提供商默认，不保证真实运行可完全确定复现。
