# 历史 A/B 脱敏交付摘要

本地来源：eval/results/safety-ab-live-01/{baseline.json,candidate.json,paired_results.json}。原始文件含案例、结果和调用轨迹，保留本地，不直接公开提交。本轮未调用模型，未编辑原始证据。

历史两组各12条；Baseline严格匹配9/12、不支持召回3/6；Candidate严格匹配12/12、不支持召回6/6；合法样本两组均6/6通过。共56次调用、168038 token，usage完整。Baseline有3条执行/混合请求错误completed，Candidate该面板0条。小样本且设计阶段已可见，不证明泛化安全，不构成自动发布授权。

逐文件SHA256由本轮只读Get-FileHash核查，具体归档清单见GIT_DELIVERY_CHECKLIST.md。公开交付只保留本摘要和哈希，不复制原始模型载荷；原始证据的受控存储与备份由用户确认。
