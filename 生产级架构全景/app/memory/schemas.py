"""
文件：app/memory/schemas.py
所属模块：★★★ 简历③ 长期记忆 Store
参考原文：globex/06_extract.md

【做什么】
定义 PreferenceEntry：一条跨会话偏好/黑名单/历史选择记录的数据结构。

【解决的问题】
Store 不存原始聊天，只存可注入、可衰减、可排序的小条目，控制注入体积。

【关键字段】
- key / category(preference|history|blacklist) / content
- confidence、updated_at（软衰减与合并）
- embedding 或关键词侧写（read_relevant 用）

【面试一句】
「记忆是结构化条目，不是把对话存盘再全文塞回 prompt。」
"""
