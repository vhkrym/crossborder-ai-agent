# 6B.1 真实 LLM 联调验收

日期：2026-10-29（Asia/Shanghai）。真实模型 deepseek-chat，端点 https://api.deepseek.com。密钥已加载但未记录。配置原位于.env.example，已迁移到被Git忽略的backend/.env，并恢复示例占位，禁止提交真实配置。

使用既有 scripts/smoke_supervisor.py，补充 --sku 可信输入、mode=ro SQLite URI、耗时及脱敏摘要。范围固定店铺1，2026-01-01至2026-03-31。工具结束后独立重新执行确定性分析并逐字段比较，报告重新渲染检查证据及原值。没有修改经营公式或demo.db。

| 真实案例 | 状态 | Agents / 工具 | 秒 | 证据/数值 |
|---|---|---|---:|---|
| DEMO-001贡献利润 | completed | profit / analyze_profit | 6.94 | 通过 |
| DEMO-002广告效率 | completed | advertising / analyze_advertising | 6.86 | 通过 |
| DEMO-003库存风险 | completed | inventory / analyze_inventory | 7.31 | 通过 |
| DEMO-001利润和广告 | completed | profit+advertising / 两工具 | 8.29 | 通过 |
| 巧克力蛋糕问题 | unsupported | 无 | 4.53 | 不适用；正确未执行工具 |

DEMO-001净收入94448.0000 USD，贡献利润-10286.6500 USD，利润率-0.1089133703201761816025749619；广告支出5474.6500 USD，ACOS 0.1552561024511897489823339873。DEMO-002广告支出13272.0000 USD，归因10031.9330 USD，ACOS 1.322975342837716320473830916。DEMO-003可售0、在途200、stockout，覆盖天数及建议补货量null，没有虚构需求或补货量。

## 首次失败与最小修复

首个案例首次耗时25.09秒，llm_api_error，无路由/工具/报告。脱敏异常链为OpenAIConnectionError → APIConnectionError → TypeError，根因 Decompressor.decompress() 不支持 output_buffer_limit 参数，是本机响应解压兼容问题，不是模型JSON失败。适配层增加 Accept-Encoding: identity，避免压缩响应后全部案例成功。未升级全局依赖或修改模型业务公式。增加不联网配置回归测试。

修复后五案例 errors 均为空，无JSON解析错误、超时或证据引用错误。工具warning反映真实负利润/高ACOS/断货，不代表调用失败。首个案例终端中文编码显示异常不影响JSON原值或证据验证，其余执行使用PYTHONIOENCODING=utf-8。

## 执行命令

```powershell
$env:PYTHONIOENCODING='utf-8'
python backend/scripts/smoke_supervisor.py --allow-real-api --sku DEMO-001 --query '分析 DEMO-001 的贡献利润'
python backend/scripts/smoke_supervisor.py --allow-real-api --sku DEMO-002 --query '分析 DEMO-002 的广告效率'
python backend/scripts/smoke_supervisor.py --allow-real-api --sku DEMO-003 --query '分析 DEMO-003 的库存风险'
python backend/scripts/smoke_supervisor.py --allow-real-api --sku DEMO-001 --query '分析 DEMO-001 的利润和广告表现'
python backend/scripts/smoke_supervisor.py --allow-real-api --query '请介绍如何烤巧克力蛋糕，与电商经营无关'
python -m pytest backend/tests -q
```

限制：真实验收为每案例一次成功运行，非统计路由准确率评测；报告仍为证据模板，不是自由推理长报告；没有任务持久化、权限API或经营动作。可进入6C，但仍须补用户权限、运行约束及更大真实问题评测集。Fake回归不得代替本页真实调用结果。
