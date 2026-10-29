# 经营分析引擎

所有接口要求 store_id、start_date、end_date，sku 可选；日期包含首尾，反向区间返回 422，店铺或指定 SKU 不存在返回 404。金额 JSON 使用十进制字符串，比例使用小数比例（0.2 表示 20%）。units、currency、日期和 reasons 显式返回。dashboard overview 返回三类 SKU 明细，未额外计算跨指标总计。

净销售收入 = gross_sales - refund_amount；退款为当天确认的正金额，不减少销量，不自动冲回历史采购成本。每笔销售按 record_date 匹配不晚于当天的最新成本。采购、物流、平台费用分别乘售出数量。贡献利润 = 净收入 - 三类成本 - 同 SKU 同区间广告支出。贡献利润率 = 贡献利润 / 净收入，净收入 <=0 返回 null。缺失成本、无销售、币种不一致时不输出确定利润。销售和广告单独查询、Python Decimal 聚合，避免 JOIN 乘法与 SQLite SUM 浮点累积。成本上涨标记比较本期实际销售采用的成本版本，不表示销售期外的涨价。

广告 ACOS=支出/归因销售额，ROAS=归因销售额/支出，CPC=支出/点击，转化率=订单/点击。零分母 null，并返回对应原因。模型没有曝光量，不提供 CTR；归因销售额不能当成店铺收入或与其相加。

库存按 end_date 截止取最新日末快照。销量窗口为 end_date-window+1 到 end_date，包含零销量记录；必须每个自然日有记录才能视为历史完整，缺失日不默认为零。日均销量=窗口销量/window，可售=on_hand-reserved，覆盖天数=可售/日均销量。目标库存=日均销量*(提前期+safety_days)，建议补货=max(0,ceil(目标-可售))。在途独立展示，无预计到货日期，不抵扣补货。快照缺失、过期或历史不足时风险 unknown、补货量 null；零销量覆盖天数 null。有库存但零销量标记 zero_sales_stock；库存为零标记 stockout，即使观察销量为零也保留断货标记，同时补货量 null 并返回 demand_censored_by_stockout。

库存接口 start_date 只用于统一参数校验，实际销量窗口由 window 决定，响应 start_date 返回实际窗口起点；overview 的 start_date 用于利润/广告，库存窗口由 window 单独指定。window 默认30（1～365），safety_days 默认7（0～365）。无未来数据参与查询。

请求示例：

```text
/api/v1/dashboard/overview?store_id=1&start_date=2026-01-01&end_date=2026-03-31
/api/v1/analytics/profit?store_id=1&start_date=2026-01-01&end_date=2026-03-31&sort_by=profit_margin&descending=false
/api/v1/analytics/advertising?store_id=1&sku=DEMO-002&start_date=2026-01-01&end_date=2026-03-31
/api/v1/analytics/inventory-risk?store_id=1&start_date=2026-03-02&end_date=2026-03-31&window=30&safety_days=7
```

开发服务需明确 DATABASE_URL 指向 demo.db 后启动，默认开发库不会自动替换或初始化。不存在表时须先初始化目标库。分析只读，测试使用独立临时数据库。

限制：无汇率换算、税费、退货成本冲回或财务净利润；币种异常时聚合金额不可视为可比，须先处理 reasons。实际销量受断货限制，零销量不等于零需求（003 会出现无法可靠建议补货数量，返回 null 且风险为 stockout），没有订单/需求预测不能推断缺货需求。004 在非零低销量时通过超过365天覆盖天数标记 slow_moving_stock（演示阈值）。缺失日期可能是无销售也可能是导入缺失，当前保守标记历史不足。没有快照 freshness 容忍窗口。查询按 SKU 执行，适合演示规模，后续扩展需批量优化及分页。SQLite 金额存储限制沿用 database.md。


## Overview summary（5B）

新增只读 summary，提供 Decimal 净收入/贡献利润/总广告ACOS、断货及低库存SKU数和未知库存SKU数。汇总复用本次店铺/SKU范围的明细，利润不完整不返回部分利润伪装完整总计；币种异常时金额指标不可用。库存截至end_date，窗口由window指定。其他三个接口summary为null，不改变现有指标计算。
