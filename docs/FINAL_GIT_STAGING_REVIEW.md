# 最终逐文件暂存审核（2026-11-02）

本轮检查全部7项已跟踪修改及128项未跟踪文件，共135项。仅安全静态审核，不执行暂存/提交/推送。具体每文件类别、SHA256、决定见下表。SHA绑定本轮审核内容，内容变化应重新检查。

扫描：每个文件读取字节，匹配当前.env中密钥、常见Key/Token/私钥模式、带凭证或token参数URL、邮箱及密码赋值。无配置密钥命中、无邮箱或敏感URL命中。测试命中为sk-evaluation-secret-never-save、sk-safety-test-secret-do-not-save和fake-test-key，均为明确测试夹具，可保留。文本未检出不等于完整个人信息保证；截图未做像素审查因此保守排除。公开URL为回环地址、公开DeepSeek端点或示例端点；文档包含项目本机路径与合成任务ID，不作为认证凭证。

## 逐文件决定

| 路径 | 类型 | 决定 | SHA256 |
|---|---|---|---|
| .dockerignore | configuration | ALLOW：当前版本可暂存 | 0ab2b9e46a34a6c4824ae94ec74057ee9d0ab0ca4ced08e1ac1ffb86434ca645 |
| .env.docker.example | configuration | ALLOW：当前版本可暂存 | 875ca3c01827ace65b9aaa0b5c203de998f708fa4d6b2b868c675189b98fc2a6 |
| .gitattributes | configuration | ALLOW：当前版本可暂存 | 92d927ae417c8503591ffa168f633811a1b090b0ea44c91010218ddfbff896f9 |
| .gitignore | configuration | ALLOW：当前版本可暂存 | ec8ff90668fbeb6f08771854e7bc435981b347d04fce45d42d02503fd3fa5368 |
| README.md | documentation | ALLOW：当前版本可暂存 | 1af473a45dcb72d03fcc49f80ea98345c477180c3ab9009a42be637e744e8ebb |
| backend/.env.example | configuration | ALLOW：当前版本可暂存 | cbd47f1b3655e9645e64dbfd006077b95902ab5489219967273e5560eb20fffb |
| backend/Dockerfile | configuration | ALLOW：当前版本可暂存 | 76b9a2d3cc547641822f597c24b5cdbe022c2f9b12a0852d7f04c58ebc08be30 |
| backend/app/agents/graph.py | source | ALLOW：当前版本可暂存 | b12209dde66170bbbdc05e6051e175948484986b20be2862f7781cd42d6839a5 |
| backend/app/agents/llm.py | source | ALLOW：当前版本可暂存 | 79df1842bfaa619fe76b06e20698e5e8692f89ef7842b6d8ed2c42f2fd7edad3 |
| backend/app/agents/nodes.py | source | ALLOW：当前版本可暂存 | 9a3cecf4cae0b66bc32e08fbd5a25323e160d0174b9cac9bac55ecf1c9c55907 |
| backend/app/agents/reporting.py | source | ALLOW：当前版本可暂存 | 4fbe82b7c23f76261daff6f04d18b81c64c8bf93dd899fc25439d01575b6373a |
| backend/app/agents/state.py | source | ALLOW：当前版本可暂存 | 4a1650653dff62173957fab6a89bc845e06a4e6f118b63e8364fc2adf44e79eb |
| backend/app/agents/supervisor_graph.py | source | ALLOW：当前版本可暂存 | 435f13ed4849ca464d8acef0c67c6895ccc12a13af2f547665a33f84d13582ae |
| backend/app/agents/supervisor_state.py | source | ALLOW：当前版本可暂存 | df07abf4209ff0d5aae8757ed51aaea5172082f09d6449b9d4938a2e5a8eab39 |
| backend/app/agents/trace.py | source | ALLOW：当前版本可暂存 | 33f8dd90d8576b3dadbe2498a918b2afc3b669f92ee63bf1adc84183498014cd |
| backend/app/analytics/advertising.py | source | ALLOW：当前版本可暂存 | 763b4bc458791ac431d216a07ad1ca817e6d5775c2cabff1d6d16451cbfd1210 |
| backend/app/analytics/common.py | source | ALLOW：当前版本可暂存 | 9e07e720e9398c0d8ac30e053b445c19045bfd48b6ffc20c5fe42bbd0ecb6d1c |
| backend/app/analytics/decisions.py | source | ALLOW：当前版本可暂存 | ddd48848541540142a7a26e1e79f49ef066536aac992ead54b971c8f7fb49d29 |
| backend/app/analytics/inventory.py | source | ALLOW：当前版本可暂存 | 0c93508770dfade3af68df2b6c64290bd4f0d7042cb512ab473ca6655722cd7d |
| backend/app/analytics/profit.py | source | ALLOW：当前版本可暂存 | 14b254a8271ad33096f50c03158f1db857ace4602fcc3d1c377b3356c8718cf5 |
| backend/app/api/v1/agent_tasks.py | source | ALLOW：当前版本可暂存 | 3ac6891cde1390eab61a17a49739f8d937579b9c8cb777e3b340d54f10b97e28 |
| backend/app/api/v1/analytics.py | source | ALLOW：当前版本可暂存 | f5f5cc75a56390608eee540426469b164ab395be4d88bfcac523d825ff4dbb36 |
| backend/app/api/v1/decision_approvals.py | source | ALLOW：当前版本可暂存 | 0b5802e27c5484a6d037b72d744345630a726bf3b9f512b3d9cb613da98b1b2c |
| backend/app/api/v1/decisions.py | source | ALLOW：当前版本可暂存 | 14d0be257ff03103d37f6333d9693ff2fe18d017e06f3c05d81961df27226234 |
| backend/app/api/v1/router.py | source | ALLOW：当前版本可暂存 | e80eda0e012c09c371efc0f3ce1bd7ae2db5185371e37ebda0b37b59287202fa |
| backend/app/api/v1/simulations.py | source | ALLOW：当前版本可暂存 | 24cd05401e697cde039479e558b12b3abb5b658b8b1dd16474bb4b790115779e |
| backend/app/core/container_startup.py | source | ALLOW：当前版本可暂存 | a3c4aa12342f627bf0da68020bf1f6a42d620ac6f6c78383b2cf783e27249026 |
| backend/app/db/migrate_agent_tasks.py | source | ALLOW：当前版本可暂存 | 2fa2db97146dc0e15819400b5b9f2f5cea969277151b01996173d88b18db1121 |
| backend/app/db/migrate_decision_approvals.py | source | ALLOW：当前版本可暂存 | 133cde102b5f3d7c9417568c0195c634648dce0d216141e3d859e53ad070a8dc |
| backend/app/db/migrate_decision_simulations.py | source | ALLOW：当前版本可暂存 | 9ee1bc7137312aad15c42badf8345be561b3bc4fa3814bab03de6b6bba91d733 |
| backend/app/db/migrate_decisions.py | source | ALLOW：当前版本可暂存 | 129882250ba458cc07ad9cc2d51ad671e16056806a666e973478a8e731c2416e |
| backend/app/main.py | source | ALLOW：当前版本可暂存 | cc571114c115e9ebe2237d96d11ea1a2742de22746754580b3636382b92883fc |
| backend/app/models/agent_task.py | source | ALLOW：当前版本可暂存 | 4d9b1c777970440a4334c428b3949405a80d22d11f4dc86eb586e42d53618c3f |
| backend/app/models/decision.py | source | ALLOW：当前版本可暂存 | c26302133f811aa7e72bd3be6d3705bb1b02240a14c8ffc9879d0aec4de113e8 |
| backend/app/models/decision_audit.py | source | ALLOW：当前版本可暂存 | 8b5b8cdddeff5c8d7edc8014dbc54a1aa8a4e8f424c290671ea04effa0003ae0 |
| backend/app/models/decision_simulation.py | source | ALLOW：当前版本可暂存 | e8859f3e99449676eed991902f8c4aa6c729afe432db82ded63d63df44de418b |
| backend/app/schemas/agent_tasks.py | source | ALLOW：当前版本可暂存 | ae85c15a51cc947dd2084407f3f8628f646f1e7afdd5f57edcfc1ceb4b268b22 |
| backend/app/schemas/decision_approvals.py | source | ALLOW：当前版本可暂存 | f651301885f5cdf42f0b219fadd6a2a51a494c3345d66fe0a49b0c68f72c7305 |
| backend/app/schemas/decisions.py | source | ALLOW：当前版本可暂存 | b85a769f9c9b8b4b305da58f9e66caad4a4eb6155202c46e4e57a88f3a909ce7 |
| backend/app/schemas/simulations.py | source | ALLOW：当前版本可暂存 | b0e548a24a931562e371625df097eac77e2ca3c8732f5b7a2783e449c89bdc66 |
| backend/app/services/agent_tasks.py | source | ALLOW：当前版本可暂存 | d91950f93a0543b7d42cc0fdef360e3929918ba3f4fd6da3feea4e3b86b3b7db |
| backend/app/services/decision_approvals.py | source | ALLOW：当前版本可暂存 | c2421f4191531e6d9cd52d33cac2638b04655c1b23d057c046bef17e26b59e3a |
| backend/app/services/decisions.py | source | ALLOW：当前版本可暂存 | 275e18642d10b18339e472ee9ae0abfd1fa19f9fa7c2230f6c19c436d36baeaa |
| backend/app/services/simulation_engine.py | source | ALLOW：当前版本可暂存 | 0473ad30e169b2b43e732cf9a15cd7243f706e5d1396dafa4a4cca66698f4b7d |
| backend/app/services/simulations.py | source | ALLOW：当前版本可暂存 | 91b3722b5d5e33c8f3960d2bd3faa32f50304fc7a89a1842960613d062f818cd |
| backend/app/tools/analytics_tools.py | source | ALLOW：当前版本可暂存 | caac43f6ec27e036dfc6febdd2b60ba3e15dd4f503028190442eab52d16f8319 |
| backend/requirements.txt | configuration | ALLOW：当前版本可暂存 | dcc5fa0201b0ba29d937543a219dd58323c87385ee1e629e87504cd8545045c7 |
| backend/scripts/smoke_supervisor.py | source | ALLOW：当前版本可暂存 | a3312cdf53d38ed6e1891747e6e5179c61ce25a6b4ac23cfe7432d3d30ecc770 |
| backend/tests/manual_task_server.py | test | ALLOW：当前版本可暂存 | b33e9097323d83b3d49d30d88197fa3dd2ee4b5401093f04218f0f17c415823e |
| backend/tests/test_ab_budget.py | test | ALLOW：当前版本可暂存 | 11a47330f1ee8b74d1d2e7fac2ae877ec3ae08ca523288a36614329b1b17eae8 |
| backend/tests/test_agent_foundation.py | test | ALLOW：当前版本可暂存 | 5c5bf3f21599a67de252200aade11ea38d2d2ca54661ba7ee416be6a6f2c312a |
| backend/tests/test_agent_tasks.py | test | ALLOW：当前版本可暂存 | 77853bbdeef52af8ab6175b40ee7caf772862065c152a308a41e0248357e5c5c |
| backend/tests/test_container_startup.py | test | ALLOW：当前版本可暂存 | 4669c80b59a063d0027ef3aae8b7ca6c16eda168c93db549fa79cc548d661a3e |
| backend/tests/test_decision_approvals.py | test | ALLOW：当前版本可暂存 | 260d40fcb3e805503266f799799fa7989292db0281c0cab799271f72fecb9a87 |
| backend/tests/test_decisions.py | test | ALLOW：当前版本可暂存 | cf34b8c64f5e2623fdeefd23ecc87b7cc3a9ca3f3baee3a02934562aa0ef7896 |
| backend/tests/test_evaluation.py | test | ALLOW：当前版本可暂存 | 9c56bf0e34f2cc6a70af2ae8ab1def41f8560202b78ec69e8ee228223d7f5bc7 |
| backend/tests/test_evaluation_v2.py | test | ALLOW：当前版本可暂存 | e59c597e96a4d3d5fe4c80ef68af427808ef29dba59c0b35acdaae6eadb3366c |
| backend/tests/test_full_chain.py | test | ALLOW：当前版本可暂存 | f856671e54e8ba587f169b78fb6c3151de4ec54563eb6cfee4aabde3be59909b |
| backend/tests/test_live_selection.py | test | ALLOW：当前版本可暂存 | 8bcb3ca85120bca666b1bd71b28e6df9be53807bf34524661a8d39133e265e74 |
| backend/tests/test_safety_routing.py | test | ALLOW：当前版本可暂存 | 3a37dfad5fbae616b226b3f8725086c3f3674c9c38dbb96a8bc527b217a8550e |
| backend/tests/test_simulations.py | test | ALLOW：当前版本可暂存 | 33ed2e5722fe9843f49f15ea03b91dffdd4d093837f92306b1b959cff3fe81b9 |
| backend/tests/test_stores.py | test | ALLOW：当前版本可暂存 | 975381c9b6961431785edd08fe2738c06beefdf23d58f04275cd63c46e4a2117 |
| backend/tests/test_supervisor.py | test | ALLOW：当前版本可暂存 | 51b8b7177bcbf6cd5d2c8b463571ebddbba7c5701b320b411cbe70b33d843bc7 |
| compose.yaml | configuration | ALLOW：当前版本可暂存 | 783bd40336a9abf56fd6a392e278645030e28bd477c9ad48211c30e1a9a26ff4 |
| docs/FINAL_DELIVERY_REPORT.md | documentation | ALLOW：当前版本可暂存 | 5ce975f4ede55ea1e28c6e2cb945de962931b0c0f5882dd6a9ec715fa2e9ed90 |
| docs/FINAL_DEMO_ACCEPTANCE.md | documentation | ALLOW：当前版本可暂存 | 032ed25ece5a353f9559091ad7a26debb44b776d13409112bbe9c649f761634d |
| docs/FINAL_REGRESSION_REPORT.md | documentation | ALLOW：当前版本可暂存 | c0aea0407fe0156e2f0768ec6f417019076872572fa2485d4484555afc36560f |
| docs/GIT_DELIVERY_CHECKLIST.md | documentation | ALLOW：当前版本可暂存 | cf0af8b5d9a596fa44214c987d7d419b3e71d05ccf04dd20048a9600a07e0376 |
| docs/SAFETY_AB_DELIVERY_SUMMARY.md | documentation | ALLOW：当前版本可暂存 | 61b6519cad190fa0a10549143a757f3bc2e09c547bb59dc8f6c9593e76e6106b |
| docs/agent_evaluation.md | documentation | ALLOW：当前版本可暂存 | db42b4fd6c2cda7087527ce24b5a57fffceca6d02a26c44368e2640653b4183f |
| docs/agent_foundation.md | documentation | ALLOW：当前版本可暂存 | ca479265e508b9a12f633ef1bd12e79f741a4c5a7677a00ae5612af32b9f007e |
| docs/agent_tasks.md | documentation | ALLOW：当前版本可暂存 | 13b32a7a0ab28eeab8b42a7a4d2885cd90bd876f94760d721346c94f6d5be0b7 |
| docs/agent_tasks_real_acceptance.md | documentation | ALLOW：当前版本可暂存 | 48ae69ebc2e990d8954cba6b746e3faa763303b4aacb304a73d5148bbfafa0ef |
| docs/architecture.md | documentation | ALLOW：当前版本可暂存 | 902a5d045ac731e8a5a927ed8d487eccddbdef8fb1835cd9a7238dcc36e07866 |
| docs/decision_approvals.md | documentation | ALLOW：当前版本可暂存 | f9601e49bbf1551afebe857ea2824e89643b8f330cda04567d779802934fac42 |
| docs/decision_proposals.md | documentation | ALLOW：当前版本可暂存 | d8e2173a49018002c15fb79222aed413dc00efa1c3296e6c6d64062e680541b1 |
| docs/decision_simulations.md | documentation | ALLOW：当前版本可暂存 | f65b2969347952712cc847f8ce5a8b501fcda241873255ad1a178db0d7a14897 |
| docs/demo_guide.md | documentation | ALLOW：当前版本可暂存 | a9beb1163f5e058d890a5b3c3034a5810b1cddad1957cf0571f477b5efd040b4 |
| docs/development.md | documentation | ALLOW：当前版本可暂存 | 79b308c5842e60b0f64b95a28717c4f19c5b6cd79a26024f2e978ded55ee8b69 |
| docs/docker_deployment.md | documentation | ALLOW：当前版本可暂存 | 2d5da88697c0df194e940348c04869c57d05579177d3ca0d2ec60897905aa58e |
| docs/documentation_validation.md | documentation | ALLOW：当前版本可暂存 | 8cfe926d844f6ddcf1de5c2ec63096de57405e0ce3282cbf881d0ae3a0f584aa |
| docs/images/README.md | documentation | HOLD：不暂存，需公开范围审核 | 6e083fca93331173fc2fd83581edffe12f86da54fd8c96c57d60024bf49d3fd6 |
| docs/images/advertising.jpg | documentation | HOLD：不暂存，需公开范围审核 | dd726cf2ba06bfaf2d2d10f40fd73d352063beb56ef77118c21a54e2186b7cad |
| docs/images/agent-report.jpg | documentation | HOLD：不暂存，需公开范围审核 | 90d685fd540e0a7ce89ee1ea03b67f586ae57f8273c59356da8b28b84147a2ef |
| docs/images/dashboard.jpg | documentation | HOLD：不暂存，需公开范围审核 | 2436fd5e425da4b6178d8ff5c18316215ca468cefeb4f78c75ca6906b3ca859d |
| docs/images/decisions.jpg | documentation | HOLD：不暂存，需公开范围审核 | d7a1265a3afcf6f8c38f4ca7b79afe65b666ef11dbb2d1be15426897bba1905c |
| docs/images/inventory.jpg | documentation | HOLD：不暂存，需公开范围审核 | db2a7b84a20a5e7bbb066287189ae9601d3d9f2ea7794dc3907da77f6d034afd |
| docs/images/profit.jpg | documentation | HOLD：不暂存，需公开范围审核 | c29169fdae21b2b2eef531adcb1abb8b17a4e7287d127a3cb06221d3b48e8229 |
| docs/known_limitations.md | documentation | ALLOW：当前版本可暂存 | 58bc8dc17eaf27f0209791bb5d0fae3dce7cd6869397ee48cbbf624c7a5d1a0f |
| docs/llm_acceptance.md | documentation | ALLOW：当前版本可暂存 | f5f72156430779cc1243eab1eee6015f56b4959989c382fa1937ee8f3cccca49 |
| docs/project_quality_audit.md | documentation | ALLOW：当前版本可暂存 | b3e98f159abe10776f03b6d5d0b561d4a5b5494c1b143c007823d00dca268627 |
| docs/supervisor.md | documentation | ALLOW：当前版本可暂存 | f1d6a9e8d5afeae7de6aea3a22d49137d6c9b3d911ef6a9ae466f1181fce9a2f |
| docs/supervisor_safety_evaluation.md | documentation | ALLOW：当前版本可暂存 | 01e827aba177ebbfbe60e32bb02e317e279fd7201fa9a857c069a0b70e08dd92 |
| eval/__init__.py | evaluation | ALLOW：当前版本可暂存 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| eval/ab_budget.py | evaluation | ALLOW：当前版本可暂存 | 6344c33dd0089b18c53405d2bd7255c9cc7166d3d26da7f1591f65e183d825f4 |
| eval/common.py | evaluation | ALLOW：当前版本可暂存 | d452ab81d6b7d29cd3f0d860315b895f4559aec0bce30fc522fe2bef28878668 |
| eval/datasets/build_safety_dataset.py | evaluation | ALLOW：当前版本可暂存 | 02aeb44801972cd48bc7e31c33f1c5068d62eb60e84687975a87e6b7b58cbcfc |
| eval/datasets/live_stratified_15.json | evaluation | ALLOW：当前版本可暂存 | 40785d5618a01e40b2a52cef02c17f978eafb3c5d93772b39b8d3ac83fa9181d |
| eval/datasets/live_stratified_15.sha256 | evaluation | ALLOW：当前版本可暂存 | 566c2cf9f45ce4060d203e374d8ca77dd37e183393949e112243baca9e7b27cf |
| eval/datasets/manifest.json | evaluation | ALLOW：当前版本可暂存 | 63398f0bcd1221c4f2074eec31125b589148d2dccf422bb6136d91be75ad044c |
| eval/datasets/manifest_v2.json | evaluation | ALLOW：当前版本可暂存 | d805c06651e9e2d67277e2d0fa7dfe944de6efee7a7a34642b3771fa776a1c87 |
| eval/datasets/safety_ab_12.json | evaluation | ALLOW：当前版本可暂存 | 1fcfd81c3a751e50500e5da7d2f15fcf01c2733b3e6455ec7350ec50c54ba9f6 |
| eval/datasets/safety_ab_12.sha256 | evaluation | ALLOW：当前版本可暂存 | 992ed79e7b7b7088db3b908e899b48fc65305cef1ca79303eeffd7be2176bf5f |
| eval/datasets/safety_routing_cases.jsonl | evaluation | ALLOW：当前版本可暂存 | 5bf66de6360367e0a2245c9dc4ad4f7ba51ac5c14b0630c1e80932eeee8d2ddd |
| eval/datasets/safety_routing_manifest.json | evaluation | ALLOW：当前版本可暂存 | 9f7e3d5c005b39148a00245a10808da520d728d947011c496436e1280d0f1762 |
| eval/datasets/supervisor_cases.jsonl | evaluation | ALLOW：当前版本可暂存 | e2e8970bd1e245bf82fcfd431da08f6e2aaeae2b65ba493737481b6ee630375f |
| eval/datasets/supervisor_cases_v2.jsonl | evaluation | ALLOW：当前版本可暂存 | ad129023db612feb01a23c473922545dac044a22a0f3b12381d8d7bd0fcb8b5d |
| eval/live_selection.py | evaluation | ALLOW：当前版本可暂存 | 4ce88c10a57938557bb93e7fb8b3c314a2049aaa7f065228aea91dcf6045c268 |
| eval/metrics.py | evaluation | ALLOW：当前版本可暂存 | 11578cb1ddb4eb77f9c61251f244a66d546f7a79d344fb6c8debb858b5de5a12 |
| eval/prompts/baseline.txt | evaluation | ALLOW：当前版本可暂存 | 5f62e167a2f74cb8510b63fac07edcc0116e82a8c5af8ad925e7e05225e91573 |
| eval/prompts/candidate.txt | evaluation | ALLOW：当前版本可暂存 | 2a291323e32b61c1c458a483e111daeaaa1d7c7f0866bdef7da491f55c1da887 |
| eval/reviews/ambiguous_cases_for_review.md | evaluation | HOLD：不暂存，需公开范围审核 | 1628da4dafaf0c4cf87d92f1f8eb34ce86bc6e454e0cc3cdde4fb2fcee8fd885 |
| eval/reviews/build_label_review.py | evaluation | HOLD：不暂存，需公开范围审核 | 2d079db04ca83dd0d3eaf1e24bc79a1d83159e10a6da2a0c94176c1467857a7b |
| eval/reviews/label_review.md | evaluation | HOLD：不暂存，需公开范围审核 | e82a3e9739fd6921e4b7c7191d13c229a0fc36472f8219298bbf80ba32d7b32e |
| eval/reviews/live_smoke_8d1.json | evaluation | HOLD：不暂存，需公开范围审核 | 9e7dbf9155a320dd8c8dcfc398c99cf24d28307abcbda79059cbe2a4aff369dc |
| eval/reviews/live_smoke_8d1.md | evaluation | HOLD：不暂存，需公开范围审核 | af3df8435a8cc03bc2f9e6d1a1e9d7a357c775ea7683475524c1472e05819802 |
| eval/reviews/live_stratified_15.json | evaluation | HOLD：不暂存，需公开范围审核 | 281a84ee3b26ca647883649323867812f04a88f2c83224fcb53a2e6e76c12ba5 |
| eval/reviews/live_stratified_15.md | evaluation | HOLD：不暂存，需公开范围审核 | befa36ca95c883acf4cd3fa64be65fc8e8704e5cf142bcbf2262824211773148 |
| eval/reviews/safety_ab_12.md | evaluation | HOLD：不暂存，需公开范围审核 | a7832ca38163fb5051e91d0435fe9af0be2751d53eee9237caa6553043007907 |
| eval/reviews/safety_ab_12_live.json | evaluation | HOLD：不暂存，需公开范围审核 | dd851177175d734ea3f5ff37fe98906c218042193c6593c2e42dad44538a5b5d |
| eval/reviews/v2_label_decisions.md | evaluation | HOLD：不暂存，需公开范围审核 | 9a8babb19f19c6c3a13cf53ebb94785e0577904f64978de4d716f8b1e86d3b8b |
| eval/run_live.py | evaluation | ALLOW：当前版本可暂存 | e3d5d6d32ff2b0f7b0675ea88fde6b76c9890d246f12e9503e8760536cb6c00f |
| eval/run_offline.py | evaluation | ALLOW：当前版本可暂存 | 94df2f68332e3d8e8cfc3f158642fea14adb274fc87dffce131da5bdcc78da45 |
| eval/run_safety.py | evaluation | ALLOW：当前版本可暂存 | 631527bacce7a9366e2adcdede1431fab3274a25fa5da152ee18e6157ae464cd |
| eval/safety.py | evaluation | ALLOW：当前版本可暂存 | fa233cbec34c34b267928cff952c037131eb6b1296abd83114f7fc1be5467d42 |
| eval/safety_ab.py | evaluation | ALLOW：当前版本可暂存 | 6dc6aa09cdcedf8087c4a22a72af5faee606f9e6d161cd07e829922e544c6af0 |
| frontend/Dockerfile | configuration | ALLOW：当前版本可暂存 | 8efd17eb5fb89a53a5cef228f134c61caad847902fc89689d477d62648ea327b |
| frontend/nginx.conf | configuration | ALLOW：当前版本可暂存 | 1a946458cbe09e273ac2294fe05abe32a1bc10848491ac9da921fbb4e6ab30fa |
| frontend/package.json | configuration | ALLOW：当前版本可暂存 | 1286ee121e3d8118ba8687569fd96d78d943acdd564bc0646da1301827c23107 |
| frontend/src/AgentTasks.vue | source | ALLOW：当前版本可暂存 | 2c1f502324f5b5f802ede5f7587337863289fd4b535296d05fb3c0ebca85a96a |
| frontend/src/App.vue | source | ALLOW：当前版本可暂存 | 2f6848cefd9eafd1ab98d35fbe62c9148bfce5b64a63de631c849e492649ad30 |
| frontend/src/Decisions.vue | source | ALLOW：当前版本可暂存 | 5c71adbd599223bdf7f499f434ba7eaf039ef3a9535de0fff4dae7bdec203aa5 |
| frontend/src/main.ts | source | ALLOW：当前版本可暂存 | 02c56cbeb7a39958608bd7af38aba9c493b28c1e83192aeba3d9e9c3c6723274 |
| frontend/src/requestGuard.ts | source | ALLOW：当前版本可暂存 | f5b9b9d8366717daf5097287885f5143f25e243c144bbca5df32f7d75f8e8a7f |
| frontend/tests/request-guard.test.ts | test | ALLOW：当前版本可暂存 | 3c71f996329ca0cdca668b834ae8c7bb3b99f5204a37815ceeac53d7101e8999 |

## 白名单可执行命令

以下都是单个具体文件，不使用通配符；仅供用户执行。本审核报告自身与命令文件为新增交付文档，可一并暂存。现有已跟踪未修改文件无需重新添加。

```powershell
# 在项目根目录执行，逐文件暂存
git add -- '.dockerignore'
git add -- '.env.docker.example'
git add -- '.gitattributes'
git add -- '.gitignore'
git add -- 'README.md'
git add -- 'backend/.env.example'
git add -- 'backend/Dockerfile'
git add -- 'backend/app/agents/graph.py'
git add -- 'backend/app/agents/llm.py'
git add -- 'backend/app/agents/nodes.py'
git add -- 'backend/app/agents/reporting.py'
git add -- 'backend/app/agents/state.py'
git add -- 'backend/app/agents/supervisor_graph.py'
git add -- 'backend/app/agents/supervisor_state.py'
git add -- 'backend/app/agents/trace.py'
git add -- 'backend/app/analytics/advertising.py'
git add -- 'backend/app/analytics/common.py'
git add -- 'backend/app/analytics/decisions.py'
git add -- 'backend/app/analytics/inventory.py'
git add -- 'backend/app/analytics/profit.py'
git add -- 'backend/app/api/v1/agent_tasks.py'
git add -- 'backend/app/api/v1/analytics.py'
git add -- 'backend/app/api/v1/decision_approvals.py'
git add -- 'backend/app/api/v1/decisions.py'
git add -- 'backend/app/api/v1/router.py'
git add -- 'backend/app/api/v1/simulations.py'
git add -- 'backend/app/core/container_startup.py'
git add -- 'backend/app/db/migrate_agent_tasks.py'
git add -- 'backend/app/db/migrate_decision_approvals.py'
git add -- 'backend/app/db/migrate_decision_simulations.py'
git add -- 'backend/app/db/migrate_decisions.py'
git add -- 'backend/app/main.py'
git add -- 'backend/app/models/agent_task.py'
git add -- 'backend/app/models/decision.py'
git add -- 'backend/app/models/decision_audit.py'
git add -- 'backend/app/models/decision_simulation.py'
git add -- 'backend/app/schemas/agent_tasks.py'
git add -- 'backend/app/schemas/decision_approvals.py'
git add -- 'backend/app/schemas/decisions.py'
git add -- 'backend/app/schemas/simulations.py'
git add -- 'backend/app/services/agent_tasks.py'
git add -- 'backend/app/services/decision_approvals.py'
git add -- 'backend/app/services/decisions.py'
git add -- 'backend/app/services/simulation_engine.py'
git add -- 'backend/app/services/simulations.py'
git add -- 'backend/app/tools/analytics_tools.py'
git add -- 'backend/requirements.txt'
git add -- 'backend/scripts/smoke_supervisor.py'
git add -- 'backend/tests/manual_task_server.py'
git add -- 'backend/tests/test_ab_budget.py'
git add -- 'backend/tests/test_agent_foundation.py'
git add -- 'backend/tests/test_agent_tasks.py'
git add -- 'backend/tests/test_container_startup.py'
git add -- 'backend/tests/test_decision_approvals.py'
git add -- 'backend/tests/test_decisions.py'
git add -- 'backend/tests/test_evaluation.py'
git add -- 'backend/tests/test_evaluation_v2.py'
git add -- 'backend/tests/test_full_chain.py'
git add -- 'backend/tests/test_live_selection.py'
git add -- 'backend/tests/test_safety_routing.py'
git add -- 'backend/tests/test_simulations.py'
git add -- 'backend/tests/test_stores.py'
git add -- 'backend/tests/test_supervisor.py'
git add -- 'compose.yaml'
git add -- 'docs/FINAL_DELIVERY_REPORT.md'
git add -- 'docs/FINAL_DEMO_ACCEPTANCE.md'
git add -- 'docs/FINAL_REGRESSION_REPORT.md'
git add -- 'docs/GIT_DELIVERY_CHECKLIST.md'
git add -- 'docs/SAFETY_AB_DELIVERY_SUMMARY.md'
git add -- 'docs/agent_evaluation.md'
git add -- 'docs/agent_foundation.md'
git add -- 'docs/agent_tasks.md'
git add -- 'docs/agent_tasks_real_acceptance.md'
git add -- 'docs/architecture.md'
git add -- 'docs/decision_approvals.md'
git add -- 'docs/decision_proposals.md'
git add -- 'docs/decision_simulations.md'
git add -- 'docs/demo_guide.md'
git add -- 'docs/development.md'
git add -- 'docs/docker_deployment.md'
git add -- 'docs/documentation_validation.md'
git add -- 'docs/known_limitations.md'
git add -- 'docs/llm_acceptance.md'
git add -- 'docs/project_quality_audit.md'
git add -- 'docs/supervisor.md'
git add -- 'docs/supervisor_safety_evaluation.md'
git add -- 'eval/__init__.py'
git add -- 'eval/ab_budget.py'
git add -- 'eval/common.py'
git add -- 'eval/datasets/build_safety_dataset.py'
git add -- 'eval/datasets/live_stratified_15.json'
git add -- 'eval/datasets/live_stratified_15.sha256'
git add -- 'eval/datasets/manifest.json'
git add -- 'eval/datasets/manifest_v2.json'
git add -- 'eval/datasets/safety_ab_12.json'
git add -- 'eval/datasets/safety_ab_12.sha256'
git add -- 'eval/datasets/safety_routing_cases.jsonl'
git add -- 'eval/datasets/safety_routing_manifest.json'
git add -- 'eval/datasets/supervisor_cases.jsonl'
git add -- 'eval/datasets/supervisor_cases_v2.jsonl'
git add -- 'eval/live_selection.py'
git add -- 'eval/metrics.py'
git add -- 'eval/prompts/baseline.txt'
git add -- 'eval/prompts/candidate.txt'
git add -- 'eval/run_live.py'
git add -- 'eval/run_offline.py'
git add -- 'eval/run_safety.py'
git add -- 'eval/safety.py'
git add -- 'eval/safety_ab.py'
git add -- 'frontend/Dockerfile'
git add -- 'frontend/nginx.conf'
git add -- 'frontend/package.json'
git add -- 'frontend/src/AgentTasks.vue'
git add -- 'frontend/src/App.vue'
git add -- 'frontend/src/Decisions.vue'
git add -- 'frontend/src/main.ts'
git add -- 'frontend/src/requestGuard.ts'
git add -- 'frontend/tests/request-guard.test.ts'
git add -- 'docs/FINAL_GIT_STAGING_REVIEW.md'
```

## 必须排除与人工确认

HOLD表中每一文件均不在命令内。六张截图未经独立像素检查，不能依据说明文档断言无敏感信息；docs/images/README.md随截图组暂缓。eval/reviews中的JSON保留原始模型预测，Markdown含内部评审/历史预测；本轮不批准公开，连同生成脚本整组暂缓。源码测试和冻结合成样本不属于原始模型响应，允许按表交付。

必须排除：backend/.env、backend/demo.db、backend/demo.pre7b.db、backend/demo.pre7c.db、backend/local.db、.acceptance-tmp所有文件、frontend/node_modules、frontend/dist、所有Python缓存和日志。eval/results/safety-ab-live-01/baseline.json、candidate.json、paired_results.json及其他原始eval/results文件均只本地保留，不提交。忽略不等于删除，未改动任何原证据。

独立备份：待用户确认。仅验证仓库内原始目录与先前SHA清单，未发现/未验证异地或独立介质上的副本；仓库内存在原始文件不能称已备份。用户提供备份位置后需核对三份文件SHA及访问权限。

## 一致性与交付限制

白名单逐文件来自git diff --name-only与git ls-files --others --exclude-standard交集清点；排除全部images/reviews。检查没有数据库扩展、临时路径、缓存、.env密钥配置或eval/results；配置例外仅公开.example。git diff --check通过，暂存区此前为空。未修改业务代码、生产Prompt、冻结样本、原始评测或数据库。原始评测未调用或重跑。

README引用被暂缓截图会在本次交付中缺图，部分文档/评测脚本可能引用被暂缓review证据；不要声称这些链接已完整交付。这不影响源码功能，但最终完整公开交付应解决引用或另行批准材料，本轮不改原文。

建议commit message：`Deliver local commerce AI demo, tests and acceptance documentation`。

用户执行白名单后检查：

```powershell
git diff --cached --check
git diff --cached --name-only
git diff --cached --stat
git diff --cached
```

结论：可以进入限定白名单的最终暂存审核阶段；尚不建议立即完成最终公开提交。仍需确认独立备份及HOLD材料公开范围/缺图引用，并核对实际暂存快照。此结论不代表生产发布批准或通用秘密扫描认证。

## 恢复暂存复核（2026-11-02）

三份原始JSON与仓库外备份逐字节SHA256一致，BACKUP_MANIFEST.txt存在并已读取核对。此前备份待确认记录为历史状态，当前已验证。

修复16处HOLD相对链接，替换为材料暂缓公开文字，未纳入HOLD。四份修改文档重新检查：无密钥、模型原始载荷或敏感URL新增；以下新哈希替代原表，保留旧值供追溯：

- README.md：433467b59a63a9af1eb41682cd6f5b89a18f5a951bb05f9a0f57e3e6f56e497f → 1af473a45dcb72d03fcc49f80ea98345c477180c3ab9009a42be637e744e8ebb
- docs/agent_evaluation.md：b777192c7bfe05efcfa8dd9ef2930a491e0dad383bd4d31d2ebf2c0751315aa9 → db42b4fd6c2cda7087527ce24b5a57fffceca6d02a26c44368e2640653b4183f
- docs/demo_guide.md：8c6f7722c123f8b6cd79d0b7bfd780ee1fa7f43eeeec94fc581af4bac055bb4c → a9beb1163f5e058d890a5b3c3034a5810b1cddad1957cf0571f477b5efd040b4
- docs/supervisor_safety_evaluation.md：b686e6fbab825804496f64f73ed0c240b4c67ed2c728f225aad6f6a1688fa839 → 01e827aba177ebbfbe60e32bb02e317e279fd7201fa9a857c069a0b70e08dd92

本审核报告移除本机绝对路径启动命令，仅含项目相对路径、SHA及公开审核信息，可暂存。此前缺图链接风险已按上述修复。
