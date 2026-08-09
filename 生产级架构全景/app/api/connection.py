"""
文件：app/api/connection.py ｜ 背景板（非简历重点）
参考原文：globex/15_extract.md

维护 thread_id -> WebSocket 连接 的映射（ConnectionManager），负责把
Monitor 上报的事件推送到正确的前端连接，以及连接断开时的清理。
"""
