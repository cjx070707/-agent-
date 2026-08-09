"""
文件：app/api/events.py ｜ 背景板（非简历重点）
参考原文：globex/07_extract.md

定义 AGUI 事件的数据结构（session_created / tool_start / tool_end / fork /
task_result / task_cancelled / error），是前端"实时看到 Agent 在干什么"的
协议层，不是 Agent 决策逻辑本身。
"""
