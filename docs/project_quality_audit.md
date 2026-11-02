# 项目整体质量审计与端到端回归（8A）

审计日期：2026-10-29，Asia/Shanghai。范围为现有FastAPI/SQLAlchemy、SQLite迁移与事务、LangGraph及工具、任务→建议→审批→模拟关联、Vue六页及配置保护。没有新增业务模块、修改经营公式或调用真实LLM/Amazon。运行环境Python3.13.9、Node24.21.0；Python3.11、Linux/Docker尚未验证。

## 证据等级

- **实际验证**：下列命令输出、临时库HTTP全链路、并发/失败测试、浏览器操作、只读数据哈希及已配置密钥精确匹配扫描。
- **代码审查**：依赖关系、SQL/Session边界、权限与部署风险、配置/Prompt/工具能力边界。代码存在不等于全部运行场景验证。
- **尚未验证**：本轮真实模型质量和网络兼容性、Docker/Linux、多进程压力、强制杀进程/断电持久性、全浏览器组合、完整安全扫描及Git历史秘密扫描。

## 基线与最终结果

先执行 python -m pytest backend/tests -q：**110 passed in 23.36s**。

修复及强化后相同命令：**112 passed in 26.14s**。新增快照失败回归、HTTP完整链路回归，另强化现有旧CHECK迁移测试的非空数据保留。

frontend目录 npm test：**3 passed**，Node原生测试，无新增依赖；npm run build包含vue-tsc，成功，最大JS分块334.37kB，无大包警告。前端测试验证了所用请求保护函数，不冒充完整Vue自动化组件/浏览器测试。

## 发现、复现与修复

| 等级 | 问题 | 复现/证据 | 修复与回归 |
|---|---|---|---|
| P2，已修复 | 模拟输入快照校验在异常处理外，失败留下running | 临时库将中断后pending记录快照设为空，execute抛ValidationError；新增测试修复前真实失败 | services/simulations.py先读取原始快照，再在受保护try中校验；test_invalid_snapshot_is_failed_not_running通过，状态simulation_failed |
| P2，已修复 | 决策深链只有ID，审计查询却读取调用参数row.store_id，导致缺参422 | Decisions.vue onMounted/来源链接使用仅proposal_id对象，调用审计时无store_id；人工浏览器复核修复后的深链返回完整表单，无422 | fetchDecisionBundle先加载服务端Proposal，再用其store_id查审计；Node深链仅ID回归、浏览器实际深链/批准通过 |
| P2，已修复关键读路径 | 决策列表/详情/模拟列表/来源任务异步请求无过期响应保护，先发后到可覆盖新店铺/新选择 | 代码审查定位直赋值；Node延迟Promise反序完成复现旧值回写场景 | createRequestGuard用于上述读取，切店铺重置模拟分页/详情，卸载失效；同步及异步反序测试通过。未对每个Vue事件建立自动化组件测试 |
| P3，测试缺口已补 | 原有独立模块测试未覆盖整个业务链路同一次HTTP回归；旧CHECK测试空表不足证明数据保留 | 审查现有测试范围 | test_full_http_chain；旧CHECK测试新增实际决策行并逐行比较迁移前后 |

本轮未调整任何利润、广告或库存公式。

## 完整HTTP业务链路（实际验证）

新增test_full_chain.py：Temporary SQLite→seed→四个迁移按序执行两次→创建AgentTask(202)→真正StateGraph搭配Fake LLM选择三个Agent→确定性工具→报告保存→建议生成→批准前模拟409→人工批准和审计→模拟成功→模拟详情、历史、审计查询。

验证task/proposal/audit/simulation所有ID关联、store=1、SKU=DEMO-001、贡献利润-10286.6500；重复建议与模拟幂等；重复审批409且日志只有一次；店铺2历史为空；完成任务/模拟recover返回0，不误中断终态；链路结束再次执行迁移，七表完整行哈希仍相等。部分失败、unsupported、无效JSON、超时、不可修改审计、模拟失败、中断和并发竞争由原有测试一并通过。

## 数据库与Session审查

实际测试检查应用引擎PRAGMA foreign_keys=1、foreign_key_check为空、唯一键和非法外键拒绝、多Session审批/模拟竞争仅一次、审计写失败回滚状态、任务重复抢占失败。服务方法with Session创建关闭，工具在同一连接恢复query_only再回滚；请求与后台Session分离，网络图执行不持有任务更新事务。

迁移依赖顺序：业务初始化→migrate_agent_tasks→migrate_decisions→migrate_decision_approvals→migrate_decision_simulations。显式增量建表，不以create_all升级已有表。审批CHECK采用事务复制；本轮非空旧表测试证明ID/证据/整行保留，重复执行安全。模拟终态及审计有不可改/删触发器。完整链路还验证已有审计和模拟后重跑迁移。

对现有demo.db仅只读查询：七表完整行哈希与既有demo.pre7c.db一致，记录数为2、30、2700、2700、2700、33、12；本轮没有重置、迁移或写入demo.db。临时浏览器库独立于demo，退出即销毁。

## Agent、配置与凭证审查

Supervisor JSON经过Pydantic白名单/一致性校验，可信店铺日期SKU只由状态传工具；专业Agent仅持有各自工具，不能调用审批或模拟。Report只选择验证过的证据ID，程序填入原值并复核；null保留、广告归因额不等于收入、无impressions不造CTR，工具不会调用经营动作。Fake测试覆盖伪造证据、范围篡改、partial_failed/unsupported/超时/错误。

LLMSettings使用SecretStr与.env绝对路径；模型timeout/retries有上限；持久化只保存类型化报告/轨迹、脱敏码，配置密钥及Bearer串经scrub处理。实际扫描Git非忽略文件（当前工作文件，非历史），已配置密钥精确匹配结果为空。没有打印密钥。此检查不保证不存在其他未知凭证，也未运行通用SAST/依赖漏洞扫描。不要在问题中输入秘密，不得擅自开启外部LangSmith追踪。

## 前端浏览器实际验收

使用扩展后的已有manual_task_server.py --port 8007，全部Session指向临时库，模型明确Fake，应用不运行全局真实库启动恢复；Vue 5180代理该服务。

实际打开/读取：overview净收入607283.40、profit负贡献利润-10286.65、advertising ACOS132.30%、inventory滞销积压；任务中心空状态→提交DEMO-001→running轮询→completed报告→刷新task_id。随后对该临时任务生成建议、直接打开仅ID的decisions深链、输入意见/二次确认批准、二次确认模拟、读取simulation_completed和历史。当前浏览器会话error日志为空。任务ID e64558a0-6c73-4a5c-a867-c41ea3a1c04d，决策ID ac639cf2-1a88-49c2-87e1-082968d15765，均仅用于临时验收。

决策及模拟页实际检查1440×900/390×844，移动视口390、内容宽375，无页面横向溢出；宽表可横向滚动。没有宣称六页所有移动断点/所有失败弹窗逐一浏览器重放。404/409/重复提交和失败路径主要由HTTP自动化覆盖。本轮没有重新通过浏览器驳回，驳回API回归通过。模拟与审批记录在前端可见，不展示业务改善百分比。

## 尚未解决的具体风险（代码审查，非通过项）

| 等级 | 风险及边界 |
|---|---|
| P1，公网阻断项 | 无登录/RBAC/用户店铺授权。store_id与UUID不构成授权，固定local_demo身份不能证明是真人。只能127.0.0.1可信演示，不允许公开端口 |
| P1，多实例阻断项 | 每进程启动会把所有遗留queued/running标为interrupted，无法区分其他仍活跃实例。必须单worker/单实例；本轮未实现租约或可靠队列 |
| P2 | 无全任务硬超时/取消，只有每次模型timeout和有限重试；BackgroundTasks无可靠恢复。任务POST网络重试可创建第二个任务并重复付费，不具备请求幂等键 |
| P2 | SQLite单写锁，建议复算BEGIN IMMEDIATE期间阻塞其他写入；默认锁超时后可能返回500，尚无全局busy→503映射或生产压测 |
| P2 | SQLite Numeric不是全范围精确定点，现有演示范围输入校验不能替代严格财务账本。字符串/整数型约束仍需输入层；不用于真实账务 |
| P2 | 损坏快照本轮已标记failed，但详情Schema仍会拒绝损坏快照，可能500；这仅可由数据库损坏/管理员写入触发，需人工修复，未新增宽松响应掩盖数据损坏 |
| P2 | 生成决策是生成时点复算，不是原任务完整工具快照；当前语义已注明，数据变化时不可当同一时点证据。直接数据库管理员可绕过不可变触发器，不具备不可抵赖性 |
| P3 | 前端仍有any和自由dict、列表加载提示不统一、来源任务选择最多100条、部分错误码为英文；未做全量组件端到端自动化或所有请求路径竞态覆盖 |
| P3 | 依赖未建立完整跨平台锁文件，Python3.11和Linux容器未实测；当前本机测试并不证明Docker部署成功 |

## 是否进入8B

**建议进入仅本地演示的Docker Compose部署工作**，前提：绑定127.0.0.1、单后端worker、持久化SQLite卷、显式按序迁移、秘密通过本地环境注入且不打包.env、关闭未授权远程追踪。Compose本轮未实现/未验证。不能据此宣称生产可用或安全公网部署。上述P1项若计划公网/多实例，必须先解决。
