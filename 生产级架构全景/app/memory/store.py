"""
文件：app/memory/store.py
所属模块：★★★ 简历③ 长期记忆 Store
参考原文：globex/06_extract.md

【做什么】
PreferenceStore 抽象接口：read / write / delete / read_relevant。

【解决的问题】
业务只依赖接口；后端可从内存 → Redis/Postgres → OpenSearch Hybrid 替换，
而不改 Agent 注入时机。

【read vs read_relevant】
- read：管理/调试全量
- read_relevant(user, query, top_k≈5)：注入 prompt，防 50 条偏好炸上下文

【和其他文件】
- in_memory_store.py / vector_store.py：实现
- 主 Agent 启动：read_relevant → prompts.long_term_preferences
- Reflect：抽取器 → write
"""
