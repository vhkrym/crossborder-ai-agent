# 人工审批与审计（7B）

## 状态机

7A生成建议实际初始状态pending_review，不增加多余draft步骤。仅允许draft→pending_review（submit）、pending_review→approved（approve）、pending_review→rejected（reject）。approved/rejected为终态，重复操作409，不产生第二条有效审计。批准不等于执行，本阶段没有模拟执行或真实经营操作。

## 本地身份与边界

后端固定reviewer_id=local-demo-reviewer、identity_source=local_demo。请求extra=forbid，不接受客户端身份、店铺或status字段。query store_id用于显示范围一致性检查，不是用户授权。没有登录、RBAC、店铺级用户权限，不可宣称生产级人工身份鉴别；必须只绑定127.0.0.1，不得公网开放。AI图和工具未接入审批API；无认证本地调用者仍可直接调用接口，系统不能密码学证明操作者是人。生产前必须接认证、RBAC、授权及必要CSRF保护。

## API

```text
POST /api/v1/decisions/{proposal_id}/submit?store_id=1
POST /api/v1/decisions/{proposal_id}/approve?store_id=1
POST /api/v1/decisions/{proposal_id}/reject?store_id=1
GET  /api/v1/decisions/{proposal_id}/audit?store_id=1
```

请求仅comment（最长2000），reject必须非空白；approve空白时后端补确认说明。成功200返回proposal和audit；无效ID/店铺范围不匹配404，非法状态409，缺失驳回意见/伪造额外字段422。无PATCH/DELETE审计接口。列表已支持approved/rejected筛选。网络失败后先重新读取，重试终态返回409，不能当成新审批。

## 原子性与审计

SQLite BEGIN IMMEDIATE串行化审批事务；UPDATE WHERE proposal_id/store_id/status=expected，只有rowcount=1可以记录审计。状态与日志在一个事务提交，审计失败则状态回滚。审计包含UUID、proposal/store复合外键、action、from/to、固定演示身份、意见、UTC时间。按proposal/time索引，proposal/action唯一约束，转换CHECK约束。数据库UPDATE/DELETE触发器阻止修改删除已有日志；普通API无更改入口。数据库文件管理员仍可删除触发器/篡改文件，不是防管理员的不可抵赖账本。生成说明、证据及七表不随审批改变。

## 迁移

```powershell
$env:PYTHONPATH=(Resolve-Path backend).Path
# 明确DATABASE_URL指向已有demo.db；先备份并停止其他写进程
python -m app.db.migrate_decision_approvals
```

SQLite不能ALTER既有CHECK，迁移采用显式事务：建立新状态约束临时表、完整复制列、核对行数、替换旧表、重建索引；新建审计表和不可变触发器，foreign_key_check后提交。失败回滚。不关闭外键，不修改七表。旧决策表已有未知子表引用或不认识的CHECK结构时可能拒绝迁移，需人工设计下一版本。

本次已用SQLite backup备份为backend/demo.pre7b.db；迁移两次，21决策逐行一致，AgentTask1、生成批次1均保留；七表2/30/2700/2700/2700/33/12不变，PRAGMA foreign_keys=1。备份.db受gitignore保护。

## 前端与实际验收

审批详情完整证据、当前状态、意见输入、二次确认、loading保护、审计历史；终态不显示操作按钮。页面明确本地身份及批准不执行。无批量审批。

实际通过页面批准DEMO-005成本变化建议ffaf606b-034c-4282-ab8b-68b9a64f353b，pending_review→approved；驳回DEMO-010成本变化建议9bb57240-8304-42c3-af38-2ee2af384d3b，pending_review→rejected。两次均经确认，终态隐藏按钮、时间线显示固定身份和意见。审计GET200，重复approve均409。

批准审计示例：audit_id=84e28c1b-9cd0-4b96-8e45-65dc92422ae9，action=approve，reviewer_id=local-demo-reviewer，identity_source=local_demo，created_at=2026-10-29T03:52:40.411686 UTC。未调用模型或任何执行工具。

测试：97 passed in 21.32s，原91项无回归；并发approve/reject只能一方成功、仅一条日志；审计写入异常回滚；旧CHECK迁移重复安全；只用临时数据库。npm run build含vue-tsc通过，无大包警告。浏览器1440/390布局与审批/驳回/时间线通过，控制台无error。

## 7C边界

可进入本地模拟执行开发，但7B批准不创建执行任务，也不改变预算或库存。7C须另定义执行授权范围、幂等、执行审计和可逆模拟，不可把本地演示身份当生产认证。
