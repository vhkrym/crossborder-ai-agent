# Git 最终交付清单（2026-11-02）

## 工作区状态

已执行git status --short、git diff --check、git diff --stat、git ls-files、git status --ignored --short。已跟踪52个文件，7项修改，76插入4删除；此统计不含未跟踪内容。调整忽略规则后、生成两份报告前有126个未跟踪文件，报告生成后另增2项。无暂存、提交或推送。

diff --check通过，有CRLF转LF提示。backend/.pytest_cache枚举权限不足，已有缓存忽略规则。未跟踪文件以 `git ls-files --others --exclude-standard` 的逐文件清单为准，不用status的目录折叠数量代替。

## .gitignore调整

新增 `.acceptance-tmp/`、`*.log`、`.vite/`、`.vite-temp/`、`*.tsbuildinfo`。原规则已覆盖Python缓存、pytest缓存、node_modules（含frontend）、frontend/dist、venv、所有*.db / *.db-* / *.sqlite*、.env和.env.*、key/pem。保留!.env.example与!.env.docker.example，公开示例中的LLM_API_KEY为空。

git check-ignore实际确认验收临时目录、前端依赖/产物、backend/.env和demo.db均被忽略。未修改源码、生产Prompt、冻结样本、原始数据库或历史结果。

## 应提交

以下为具体路径或路径规则，均须逐文件审核；不要整体批量添加目录。

- 已跟踪修改：backend/.env.example、backend/app/api/v1/router.py、backend/app/main.py、backend/requirements.txt、frontend/package.json、frontend/src/App.vue、frontend/src/main.ts。
- 根配置：.gitignore、.gitattributes、.dockerignore、.env.docker.example、compose.yaml、README.md。
- 后端源码：backend/app/agents/*.py、backend/app/analytics/*.py、backend/app/api/v1/*.py、backend/app/core/*.py、backend/app/db/migrate_*.py、backend/app/models/*.py、backend/app/schemas/*.py、backend/app/services/*.py、backend/app/tools/*.py。
- 后端工程与测试：backend/Dockerfile、backend/scripts/*.py、backend/tests/*.py、backend/pytest.ini、backend/requirements.txt。
- 前端：frontend/src/*.vue、frontend/src/*.ts、frontend/src/*.css、frontend/tests/*.ts、frontend/Dockerfile、frontend/nginx.conf；保留已有package-lock.json、vite.config.ts、tsconfig.json、index.html及frontend/.env.example。
- 文档：docs/*.md（包括本清单与SAFETY_AB_DELIVERY_SUMMARY.md），不直接包含docs/images图片。
- 评测代码：eval/*.py、eval/__init__.py；冻结资源eval/datasets/*.json、*.jsonl、*.sha256及build_safety_dataset.py；eval/prompts/baseline.txt、candidate.txt。交付构建脚本不代表应重新运行覆盖冻结样本；提交Candidate资源不等于发布。

## 应忽略

- .acceptance-tmp/**、**/__pycache__/**、**/.pytest_cache/**、*.pyc、*.log、.vite/、.vite-temp/、*.tsbuildinfo。
- frontend/node_modules/**、frontend/dist/**、.venv/**、venv/**。
- backend/.env及其他本地.env配置（公开示例例外）、*.pem、*.key。
- backend/demo.db、backend/demo.pre7b.db、backend/demo.pre7c.db、backend/local.db、临时SQLite及其journal/WAL文件。
- eval/results/**、backups/**、volumes/**。忽略不等于删除，本轮均保留。

## 应本地归档：原始历史证据

保留eval/results/safety-ab-live-01三份原始文件，不强制添加。SHA256如下：

| 文件（相对该目录） | SHA256 |
|---|---|
| baseline.json | F4077C419694D8DAD6F3FEE67392BCC9FBAA6251A0118CC33493F51716F8B513 |
| candidate.json | DF94CE250306E008C6340CA0442CC5137EEC69B401119990D02FE2C44465C0AB |
| paired_results.json | DAEF424372FCA79BED151C3BD8C90820D713E1B0DF8344F690522620470A0ACD |

Git提交[脱敏摘要](SAFETY_AB_DELIVERY_SUMMARY.md)及本哈希表。原始结果含查询、可信范围、预测和调用轨迹，即使无Key也应先审查公开范围。用户可将原目录只读复制到受控备份位置并核对SHA和访问权限；本轮未复制或删除。当前本地路径不是异地备份。

## 需要用户确认

- docs/images/*：截图可能含UI内部信息，须人工逐图检查，再决定提交。
- eval/reviews/*：包括live_smoke_8d1.json/.md、live_stratified_15.json/.md、safety_ab_12_live.json、safety_ab_12.md、标签评审文档及build_label_review.py。历史原始JSON优先本地归档；Markdown与脚本逐项审阅后才能交付。该目录当前未忽略，严禁直接git add eval。
- 冻结集和评测代码当前未跟踪，Git无法证明相对可信提交历史未变；已有内置哈希校验通过不替代可信归档比对。
- 尚未进行完整Git历史秘密扫描；用户确认最终暂存内容和仓库公开范围。

## 敏感信息检查边界

只读按backend/.env中当前完整Key精确匹配既有已跟踪/未跟踪候选和指定三份原始JSON，扫描未发现匹配（未输出Key）。示例配置为空值。该扫描不能发现其他历史Key、其他类型秘密或截图像素中的信息；忽略规则也不能移除已跟踪秘密。原始响应和reviews不能因当前Key未命中而认定可公开。

## 建议命令（本轮未执行）

根目录PowerShell；先审阅，再逐文件暂存，避免git add .或目录级批量添加：

```powershell
git status --short
git ls-files --others --exclude-standard
git diff --check
git diff
git add -p -- backend/.env.example backend/app/api/v1/router.py backend/app/main.py backend/requirements.txt frontend/package.json frontend/src/App.vue frontend/src/main.ts
# 对照“应提交”规则审核逐文件清单，再一次添加一个明确文件，例如：
git add -- .gitignore
git add -- docs/GIT_DELIVERY_CHECKLIST.md
git add -- docs/SAFETY_AB_DELIVERY_SUMMARY.md
# 继续逐文件添加其余已审核源码、测试、文档及冻结资源
git diff --cached --check
git diff --cached --stat
git diff --cached --name-only
git diff --cached
# 完成下方最后检查后由用户自行提交
git commit -m "Deliver local commerce AI demo and acceptance evidence"
```

## 提交前最后检查

1. 逐项核对未跟踪清单，确保源码、测试、示例、锁文件、冻结资源完整纳入。
2. 暂存区不得包含.env、数据库、原始results、缓存、构建产物及未经审查的截图/reviews。
3. 对暂存内容进行秘密扫描和人工review，核对证据SHA与受控备份。
4. git diff --cached --check通过；本轮仅忽略规则和文档调整，未重跑业务测试，保留此前166/3及构建结果来源。
5. 保留Baseline安全FAIL和Candidate未发布说明，不把Git提交等同生产上线。

结论：已具备进入逐文件审核和暂存的条件；尚不能宣称无需人工复核即可安全提交。仍需确认截图/reviews公开范围、历史证据归档及最终暂存内容。本轮未执行git add/commit/push，未修改远程配置。
