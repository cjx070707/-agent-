"""
文件：app/api/server.py ｜ 背景板（非简历重点）
参考原文：globex/15_extract.md

FastAPI 服务入口：POST /api/task 创建后台 Agent 任务并立即返回 thread_id；
WS /ws/{thread_id} 推送实时事件；POST /api/task/{thread_id}/cancel 取消
任务。这一层还没在 globex-agent 里实现（阶段2 Task 7）。
"""
