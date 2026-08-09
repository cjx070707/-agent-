"""
文件：app/api/context.py ｜ 背景板（非简历重点）
参考原文：globex/10_基础模块与模型配置_核心提取.md

用 ContextVar 保存当前请求的 thread_id 和 session_dir，让深层函数（比如
某个工具内部想上报事件）不用一层层显式传参就能拿到"当前是谁的请求"。
和简历①里 fork_guard 用 ContextVar 是同一种技术手段，只是这里管的是
"请求身份"而不是"fork 深度"。
"""
