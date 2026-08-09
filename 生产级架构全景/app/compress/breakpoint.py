"""
文件：app/compress/breakpoint.py ｜ ⏳ 简历② 占位待补
参考原文：globex/05_extract.md

【占位说明】
这里将实现 Cache Breakpoint 的核心逻辑：在对话历史里找到一个"稳定缓存区
和可压缩区"的分界点，断点之前的内容一字不动（保 Prompt Cache 命中率），
断点之后的早期轮次做摘要压缩。是简历"Cache Breakpoint上下文压缩"那条的
核心文件。会在学习模块②时补全完整讲解，包括"80%缓存命中率"数字的原文
出处（globex/05_extract.md 有几乎逐字对应的原始数据）。

真实代码现状：globex-agent 里还没有这个文件（排在阶段5，未开始）。
"""
