"""
文件：app/memory/in_memory_store.py
所属模块：★★★ 简历③ 长期记忆 Store
参考原文：globex/06_extract.md

【做什么】
PreferenceStore 的内存实现，用于先跑通写/读/相关召回逻辑。

【解决的问题】
不先上 Redis 也能验证：Reflect 写入 → 新会话 read_relevant → 注入。

【次生产级叙事】
内存仅开发；灰度/生产换 Redis 或 Postgres，接口不变。
"""
