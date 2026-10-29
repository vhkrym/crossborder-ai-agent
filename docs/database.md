# 数据库模型与口径

## 初始化

在仓库根目录的 PowerShell 中执行：

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
.\.venv\Scripts\python.exe -m app.db.init_db
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini backend/tests
```

统一入口 init_db 使用 create_all，只创建缺失表，不删除数据，不在每次启动时重建。已有表结构的升级需要后续迁移。应用共享 SQLite 引擎启用 foreign_keys；外部自行创建的 SQLite 引擎也必须启用该 PRAGMA。

## 表关系

- stores：name、marketplace、market、currency；整数主键 id。
- products：store_id 外键指向 stores；(store_id, sku) 唯一，SKU 在店铺间可重复。
- sales_records、ad_records、inventory_snapshots、cost_records：各自整数主键；store_id 外键指向 stores，(store_id, sku) 复合外键指向 products。删除被引用的店铺或商品受 RESTRICT 限制。
- data_imports：独立导入任务记录，尚未关联导入的事实行。

## 业务字段

销售 record_date 是店铺当地业务日期。quantity 为售出件数（非负，未扣退货）；gross_sales 为折扣后的商品销售额、退款前、不含税费和运费；refund_amount 为当日确认的商品退款正数。净商品收入 = gross_sales - refund_amount。退款可能对应历史订单，因此允许当天退款超过销售额。索引支持店铺/SKU/日期和店铺/日期查询。

广告 spend 是广告支出，attributed_sales 是广告平台归因窗口内报告的销售额，不等于店铺总销售额，不能与总销售额相加。clicks、orders 为平台口径计数。广告按店铺/SKU/日期建立索引；当前不支持无 SKU 的品牌广告。

库存 on_hand 包含 reserved；available = on_hand - reserved，不含 inbound。约束所有数量及 lead_time_days 非负，reserved 不超过 on_hand。每个店铺/SKU/日期唯一。snapshot_date 是历史观测日期，绝不能直接称为当前库存；消费者必须指定截至日期、取不晚于该日期的最新快照，并检查时效。当前没有库存实时查询服务。

成本 purchase_cost、logistics_cost、platform_fee_per_unit 均为每件成本，同一店铺/SKU/effective_from 唯一。services.costs.get_applicable_cost(session, store_id, sku, business_date) 返回不晚于业务日期的最新成本，没有则返回 None，调用方不得默认为零。生效直到下一条成本记录生效。唯一索引同时支持日期查找。

导入 filename 仅保存名称；data_type 限制为六种业务表名。status 限制为 pending、processing、completed、failed；total_rows、success_rows、failed_rows 非负，成功加失败不超过总数（处理中允许部分完成）。error_summary 可为空；created_at 保存 UTC 无时区时间。状态转换及完成时计数一致性由未来导入服务负责。

## 金额与限制

金额均为 Decimal / Numeric(18,4)，非负；currency 应为 ISO 三位代码。当前未进行汇率换算，也未在数据库约束币种与店铺一致；服务必须验证币种再计算。所有必填字段均 NOT NULL。

SQLite 的 Numeric 使用类型亲和性，底层可能以 REAL 存储，不保证任意大数或超过四位小数的精确存储与范围校验；当前测试验证常用四位小数读回及 Decimal 运算，不能代表严格财务账本保证。导入层应使用 Decimal 解析并校验精度；严格账本应迁移到支持原生定点数的数据库或采用最小货币单位整数方案。

销售和广告允许同日多行，尚无来源维度、导入关联或幂等去重键；不能重复导入后直接求和。库存仅支持日粒度；未支持仓库维度。未提供 ORM relationship 导航属性，关系通过显式外键和查询表达。SQLite 不严格验证字符串长度及整数类型，后续输入层需要校验。未实现数据库迁移、导入处理和经营分析。


## 任务 2.1 补充规则

金额仍用 Numeric(18,4)，通过 core.money.Money 绑定前校验：仅接受 Decimal、十进制字符串、整数，拒绝 float、bool、非有限数、负数及超过 999999.9999 的输入。范围在舍入前校验，四位小数采用 ROUND_HALF_UP。Python 计算直接使用 Decimal。SQLite 驱动内部仍可能用二进制浮点，不能保证完整 Decimal(18,4) 精度；回归测试明确验证大金额失真及演示上界读回。演示范围并非对所有值的精度证明；严格账本的最小替代方案为万分单位整数列，需要后续受控迁移，本次未实施。直接 SQL 可绕过 Python 校验。

导入新增必填 store_id、source_type（file/api，默认 file）、file_hash（64 位小写十六进制），店铺受外键保护。对原始文件字节计算 SHA-256；API 来源对确定的原始载荷字节计算。唯一身份为 (store_id, source_type, data_type, file_hash)。重命名不改变身份，不同店铺允许相同文件。同日多笔销售仍合法。

pending/processing 重复请求复用任务；completed 返回已有结果；failed 复用原任务重试并重置计数及错误。未来处理器须用带旧状态条件的原子 UPDATE 抢占。事实行与 completed 状态在一个事务提交；任何错误（包括部分成功）回滚全部事实行，再独立标记 failed。不支持已落库部分成功后整文件重放。唯一键保障身份并发互斥，事务处理器、状态转换及实际哈希计算尚未实现，不能声称端到端 exactly-once。不同字节但业务相同仍可能重复。店铺资料导入也须先建立目标店铺身份。

成本按 effective_from <= 业务日期选最新记录，生效当天包含，无记录返回 None。库存是历史观测，不等同实时库存。表关系沿用前文，但 data_imports 现在通过 store_id 关联 stores。

create_all 不升级已有表，不删除数据；本次未操作已有数据库。旧数据库投入使用前须另行备份、受控迁移并补齐店铺及真实文件指纹，不能伪造 hash。新初始化数据库直接采用新结构。
