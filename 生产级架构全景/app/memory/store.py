"""
文件：app/memory/store.py ｜ ⏳ 简历③ 占位待补
参考原文：globex/06_extract.md 第 126 行起（`PreferenceStore` 抽象接口）

【占位说明】
原文这里定义的是 `PreferenceStore` 抽象接口（读写偏好的统一方法签名，
包括 `read_relevant(user_id, query)` 只读最相关的几条，避免全量注入
撑爆 prompt），不是存储的具体实现。具体实现在 `in_memory_store.py` /
`vector_store.py`。会在学习模块③时补全完整讲解，包括"72%命中率"这个
数字的口径怎么合理化。

真实代码现状：globex-agent 里还没有这个文件（排在阶段4/5，未开始）。
"""
