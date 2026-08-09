"""
文件：app/memory/vector_store.py ｜ ⏳ 简历③ 占位待补
参考原文：globex/06_extract.md 第 404 行起 + globex/04_1_extract.md 第 6.4 节
（"黑名单全量 + 偏好 Top-K"）、第 509 行（迁移到 OpenSearch 后端）

【占位说明】
`PreferenceStore` 接口的向量检索实现，原文第 04-1 章明确要求"黑名单全量
返回 + 软偏好向量 Top-K"（黑名单不能被 Top-K 截断掉），后端迁移到
OpenSearch Hybrid Query。会在学习模块③时补全完整讲解。

真实代码现状：globex-agent 里还没有这个文件。
"""
