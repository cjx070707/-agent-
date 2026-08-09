"""
文件：app/api/monitor.py ｜ 背景板（非简历重点）
参考原文：globex/10_基础模块与模型配置_核心提取.md

工具执行前后统一调用 Monitor 上报事件，Monitor 从 ContextVar 读出当前
thread_id，再交给 connection.py 的 ConnectionManager 路由到对应的
WebSocket 连接。工具本身只管调 Monitor，不直接依赖 WebSocket，两者解耦。
"""
