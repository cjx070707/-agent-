"""
文件：app/memory/vector_store.py
所属模块：★★★ 简历③ 长期记忆 Store
参考原文：globex/06_extract.md、globex/04_1_extract.md（黑名单全量 + 偏好 Top-K）

【做什么】
带向量/混合检索的 Store 实现叙事：query 编码后与条目 embedding 算相关度，
再叠置信度与软衰减；黑名单可全量或加权，避免被 Top-K 截断。

【解决的问题】
关键词不够时的语义相关（「洗漱包」仍能召回材质黑名单）。

【面试一句】
「相关读取 = 相关度 × 置信度 × 时间衰减 + 黑名单加权；后端可以是 PG/Redis/OpenSearch。」
"""
