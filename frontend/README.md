# Vue 经营分析工作台

本机验证 Node 24.21.0 / npm 11.19.0。依赖锁定见 package-lock.json；不需要升级全局 Node。

仓库根目录 PowerShell 启动后端（使用已有独立 demo 库，不会重建）：

```powershell
$env:DATABASE_URL = 'sqlite:///' + ((Resolve-Path backend/demo.db).Path -replace '\\','/')
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

另一个 PowerShell：

```powershell
cd frontend
npm install
npm run dev
npm run typecheck
npm run build
```

访问 http://127.0.0.1:5173。四条路由 /overview、/profit、/advertising、/inventory。

店铺来自 GET /api/v1/stores，无固定 ID。默认日期 2026-01-01～2026-03-31；切换店铺、日期、观察天数重新查询，SKU 输入确认或失焦后查询。接口请求取消过时响应，错误清除旧数据，null 展示 —。金额转 Number 仅用于显示格式化，不用于业务运算。总览仅显示 SKU 明细，不计算总计。ECharts 已安装，图表留待5B。

.env.example 可配置 BACKEND_URL（Vite代理目标）与 VITE_API_BASE_URL。开发默认 /api/v1 同源代理，无需放宽后端 CORS。生产部署须将 /api 反向代理到后端，SPA 路由回退到 index.html；跨域部署需另行配置明确 CORS 白名单。无登录/鉴权功能，不应公开暴露后端。

安装与构建已验证，构建有大包体积警告（Element Plus 全量引入），后续可按需加载。npm 报 esbuild 安装脚本未授权，但当前构建正常，不影响本机验证。


## 任务 5B

新增总览 KPI、利润排行与利润率、广告 ACOS 与支出对比、库存覆盖图。所有图表来自分析 API，点击条形自动筛选 SKU，清空 SKU 可恢复全量。利润页支持三个指标降序排列；库存页支持状态筛选。覆盖图上限90天，tooltip保留真实值；null不按零处理。风险提示包含文字和图标。

ECharts 按需注册 Bar/Grid/Tooltip/Legend/Canvas，ResizeObserver 随容器重绘并在卸载时释放；Element Plus 使用构建插件按需引入，图表和渲染器分块，不提高体积警告阈值。最终最大 JS 分块 416.61 kB，无大包警告。此前5A全量入口约1030.22 kB。

后端 overview 新增 summary：net_revenue、contribution_profit、acos、inventory_risk_skus、inventory_unknown_skus、reasons。金额和比例仍为Decimal字符串；贡献利润缺失任一SKU成本时null；ACOS用合计花费除以合计归因销售额，不平均各SKU ACOS。币种异常时金额KPI不可计算。库存风险数只包含stockout/at_risk，不包含积压和未知；未知单列。所有KPI遵循当前店铺/SKU筛选，利润广告按请求日期，库存按截止日期和观察窗口。

验证：npm run build 内含 vue-tsc；后端51项测试通过。浏览器验证四页、图表点击、店铺切换、截止日期变更，1440×900桌面和390×844移动端；读取控制台无error。未建立前端自动化端到端回归套件。移动端表格支持水平滚动，图表单列，未提供复杂图表缩放或导出。
