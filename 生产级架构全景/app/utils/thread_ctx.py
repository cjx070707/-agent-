"""
文件：app/utils/thread_ctx.py ｜ 背景板（非简历重点）

对 ContextVar 用法的封装/工具函数，方便 context.py 和 fork_guard.py 之类
的模块复用同一套"读写当前上下文变量"的辅助函数，避免重复写样板代码。
"""
