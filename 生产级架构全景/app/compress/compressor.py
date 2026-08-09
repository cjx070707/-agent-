"""
文件：app/compress/compressor.py
所属模块：★★★ 简历② Cache Breakpoint
参考原文：globex/05_extract.md
配套验证：../../demos/demo_cache_breakpoint.py

【做什么】
对「断点之后」的消息做截断/摘要类压缩，再与断点前原样拼接。
绝不改写 messages[:breakpoint]。

【解决的问题】
在保住 Prompt Cache 前缀的前提下，把总 token 压到可控（简历叙事：10+ 轮约 30k 水位）。
并尽量不丢掉预算/材质等硬约束（约束遗漏率是评估项，不是可选项）。

【输入 / 输出】
- 输入：全量 messages、breakpoint_idx、压缩策略（截断长度 / 摘要规则）
- 输出：新 messages = 原样前缀 + 压缩后缀

【和其他文件的连接】
- breakpoint.compute_breakpoint → 本文件只消费 idx
- 主 loop 每步后：bp = compute...; state.messages = compress(messages, bp)
- L0 工具截断（middleware）：单次工具结果别爆；本文件管多轮历史——两层互补
- 盲目压缩对照组：见 demo 里 naive_compress_all（会改前缀指纹）

【技术栈】
复刻可用规则截断；生产可用再调一次小模型做摘要，但摘要 prompt 必须「保留约束清单」。

【关键逻辑（理解用）】
```python
def compress_after_breakpoint(messages, bp: int) -> list:
    head = messages[:bp]          # 禁止修改
    tail = shrink(messages[bp:])  # 截断/摘要
    return head + tail
```

【面试可能被追问】
- 和「工具结果截断」区别？→ 截断是单次 Observation；这里是多轮历史盖章线治理。
- 命中率 80% 怎么来？→ 原文 Cache-Aware 表；机制上等于前缀不被改写。
- 14 章若压缩了断点前？→ 本全景以 05 为准，视为不应采用的示例。
"""
