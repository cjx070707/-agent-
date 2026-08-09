"""
文件：app/compress/breakpoint.py
所属模块：★★★ 简历② Cache Breakpoint
参考原文：globex/05_extract.md（定稿）；接入叙事见 globex/14_extract.md
配套验证：../../demos/demo_cache_breakpoint.py
定稿纪律：只把「可压缩区」标在断点之后；断点前一字不动（不以 14 章压前缀的示例为准）

【做什么】
在 messages 历史上计算 Cache Breakpoint 下标：该下标之前是稳定缓存区，
从该下标起是可压缩区。

【解决的问题】
多轮 Agent 上下文膨胀后若整段乱摘要，会改写本应稳定的前缀，打穿 Prompt Cache。
先画「盖章线」，后面的压缩才知道哪些能动、哪些不能动。

【输入 / 输出】
- 输入：消息列表 + keep_recent（最近保留多少次「工具调用」不划进稳定区）
- 输出：breakpoint_idx（int）。messages[:idx] 稳定；messages[idx:] 可压。

【定位策略（原文）】
收集所有工具消息下标，取「最近 keep_recent 个」里最早的那个下标作为断点。
最近 K 轮最不稳定，放线后；线前留给 cache。

【和其他文件的连接】
- compressor.py：只压缩 breakpoint 之后的片段
- 主 AgentLoop：每步结束后调用 compute_breakpoint，再决定是否 compress
- 与 fork：fork 减少灌进主线的垃圾；breakpoint 治理主线仍变长的历史
- 与 Store：本文件管会话内 token，不管跨会话偏好

【技术栈】
纯逻辑即可；厂商 cache_control 在真正调模型时打在「稳定前缀」上（叙事层）。

【关键逻辑（理解用）】
```python
def compute_breakpoint(messages, keep_recent=3) -> int:
    tool_idxs = [i for i, m in enumerate(messages) if is_tool(m)]
    if not tool_idxs:
        return len(messages)
    if len(tool_idxs) <= keep_recent:
        return tool_idxs[0]
    return tool_idxs[-keep_recent]
```

【面试可能被追问】
- 为什么最近 K 轮放线后而不是缓存？→ 它们最容易变，缓存它们前缀会频繁失效。
- keep_recent 太大/太小？→ 太大省得少；太小稳定区短、可压空间大但最近上下文可能不够用——工程折中。
"""
