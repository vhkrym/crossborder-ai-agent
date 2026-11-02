# 文档与演示材料验收（8C）

本轮仅修改文档及真实截图，不修改业务实现。README面向GitHub访客，架构图对应单后端模块、真实LangGraph条件边、状态机与数据库关系。演示指南使用新建独立库/新任务，不依赖历史任务ID。

实际结果：后端120 passed in 35.38s；前端Node回归3 passed；npm run typecheck及npm run build成功，无大包警告。没有调用真实LLM，没有改写demo.db；截图读取已保存的真实DeepSeek报告和本地模拟结果。

新增截图六张：dashboard、profit、advertising、inventory、agent-report、decisions，均为实际运行页面JPEG，约1.6MB，非AI生成。总览为视口截图，其余为完整长页。图片不含.env、密钥或真实客户信息。

链接、Mermaid和PowerShell文档检查结果在下文补充。Docker构建网络阻断和容器部署/Python3.11/Nginx/volume未验证边界保持不变。


## 实际文档检查结果

- 扫描README、docs下全部Markdown及frontend/README，共47个本地链接，缺失0；包含全部6张图片引用。
- README、development、demo_guide、architecture、known_limitations没有硬编码历史任务UUID；临时验收端口不用于访客启动指南。
- 11个PowerShell代码块通过PowerShell Parser语法检查，未执行覆盖.env、重置库或重新付费模型调用。命令结构已对照seed脚本、迁移模块、requirements及package scripts核实；目标Python3.11安装步骤不等于本机实测3.11。
- README一张总图、architecture七张分层/Agent路由/任务状态/建议流程/审批状态/模拟状态/ER图，临时本地Mermaid页面浏览器显示8/8 diagrams rendered。首次Windows临时服务器.mjs MIME为text/plain，改文档检查服务器MIME后渲染成功；项目服务未修改。
- Docker描述保留镜像网络构建失败、容器/Nginx/volume/Python3.11未验收；无生产认证或Amazon集成承诺。历史文档当时端口/ID保留为验收档案，不冒充新访客步骤。

六张图片实际来自原生开发服务器的既有模拟业务页面，报告为持久化真实DeepSeek结果（不是本轮重新调用）；截图时仅GET读取。总览1440×900视口，其余长页面。浏览器未观察到error；没有.env或秘密配置界面。

## 尚未完成

Docker镜像仍需网络恢复后构建；容器内Linux/Python3.11、Nginx反向代理/SPA、volume重启/重建持久化仍未验证。没有生产负载、安全审计或统计Agent准确率结论。可进入8D建立评测集，但需明确离线Fake回归和真实模型效果评测的区别，并保留部署欠项。
