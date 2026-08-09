"""
简历②演示：普通（盲目）压缩 vs Cache-Aware（断点后）压缩。

不调用任何 LLM API。用假 messages 展示：
1. Breakpoint 画在哪里（最近 K 个工具调用之前）
2. 盲目压缩：动到「本该稳定」的前缀 → 前缀指纹变了（模拟 cache miss）
3. Cache-Aware：断点前指纹不变，只压断点后 → 前缀可复用（模拟 cache hit）

运行（任意 Python 3 即可，无第三方依赖）：
    python demo_cache_breakpoint.py
或在仓库内：
    python 生产级架构全景/demos/demo_cache_breakpoint.py
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass
class Msg:
    role: str  # system / user / assistant / tool
    content: str
    is_tool: bool = False


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def prefix_fingerprint(messages: list[Msg]) -> str:
    blob = "\n".join(f"{m.role}:{m.content}" for m in messages)
    return fingerprint(blob)


def build_fake_history() -> list[Msg]:
    """模拟：system + 用户需求 + 若干轮工具，足够看出断点。"""
    return [
        Msg("system", "你是跨境购物 Agent。须遵守用户预算与材质约束。"),
        Msg("user", "旅行三件套，预算300，不要塑料，小众一点。"),
        Msg("assistant", "先拆需求并检索。"),
        Msg("tool", "item_search amazon: [很长的候选列表A...]" + ("x" * 200), True),
        Msg("assistant", "继续查 shopee。"),
        Msg("tool", "item_search shopee: [很长的候选列表B...]" + ("y" * 200), True),
        Msg("assistant", "继续查 ebay。"),
        Msg("tool", "item_search ebay: [很长的候选列表C...]" + ("z" * 200), True),
        Msg("assistant", "准备比价。"),
        Msg("tool", "price_compare: ranked=[...]" + ("p" * 80), True),
        Msg("user", "再看看有没有帆布款。"),  # 当前追问：每轮都变
    ]


def tool_indices(messages: list[Msg]) -> list[int]:
    return [i for i, m in enumerate(messages) if m.is_tool]


def compute_breakpoint(messages: list[Msg], keep_recent: int = 3) -> int:
    """断点 = 最近 keep_recent 个工具消息中，最早那一个的下标。
    该下标之前：稳定区；从该下标起：可压缩区。
    """
    idxs = tool_indices(messages)
    if not idxs:
        return len(messages)
    if len(idxs) <= keep_recent:
        return idxs[0]
    return idxs[-keep_recent]


def naive_compress_all(messages: list[Msg]) -> list[Msg]:
    """盲目压缩：连早期轮次一起改写成摘要 → 破坏稳定前缀。"""
    out: list[Msg] = []
    for m in messages:
        if m.role == "system" or (m.role == "user" and out == []):
            out.append(m)
            continue
        if m.is_tool or m.role == "assistant":
            out.append(Msg(m.role, f"[摘要]{m.content[:40]}…", m.is_tool))
        else:
            out.append(m)
    return out


def cache_aware_compress(messages: list[Msg], keep_recent: int = 3) -> list[Msg]:
    """Cache-Aware：断点前原样复制；断点后工具结果截断/摘要。"""
    bp = compute_breakpoint(messages, keep_recent=keep_recent)
    head = list(messages[:bp])  # 一字不动
    tail: list[Msg] = []
    for m in messages[bp:]:
        if m.is_tool and len(m.content) > 60:
            tail.append(Msg(m.role, m.content[:60] + "…[truncated]", True))
        else:
            tail.append(m)
    return head + tail


def total_chars(messages: list[Msg]) -> int:
    return sum(len(m.content) for m in messages)


def main() -> None:
    history = build_fake_history()
    bp = compute_breakpoint(history, keep_recent=3)
    idxs = tool_indices(history)

    print("=== 1. 假历史与 Breakpoint ===")
    print(f"工具消息下标: {idxs}")
    print(f"keep_recent=3 → breakpoint_idx={bp}")
    print("断点前（稳定，应保 cache）:")
    for i, m in enumerate(history[:bp]):
        print(f"  [{i}] {m.role}: {m.content[:50]}…")
    print("断点后（可压缩）:")
    for i, m in enumerate(history[bp:], start=bp):
        print(f"  [{i}] {m.role}: {m.content[:50]}…")

    stable_prefix_fp = prefix_fingerprint(history[:bp])
    print(f"\n稳定前缀指纹: {stable_prefix_fp}")
    print(f"原始总字符: {total_chars(history)}")

    naive = naive_compress_all(history)
    aware = cache_aware_compress(history, keep_recent=3)
    naive_bp = compute_breakpoint(naive, keep_recent=3)
    # 对 naive：用「原断点位置」切前缀，看是否被改坏
    naive_prefix_fp = prefix_fingerprint(naive[:bp] if bp <= len(naive) else naive)
    aware_prefix_fp = prefix_fingerprint(aware[:bp])

    print("\n=== 2. 盲目压缩 vs Cache-Aware ===")
    print(f"盲目压缩后总字符: {total_chars(naive)}")
    print(f"  原稳定区前缀指纹: {naive_prefix_fp}")
    print(
        f"  与压缩前相同? {naive_prefix_fp == stable_prefix_fp}  "
        f"← False 表示前缀被改写，Prompt Cache 会 miss（命中率暴跌）"
    )

    print(f"Cache-Aware后总字符: {total_chars(aware)}")
    print(f"  稳定区前缀指纹: {aware_prefix_fp}")
    print(
        f"  与压缩前相同? {aware_prefix_fp == stable_prefix_fp}  "
        f"← True 表示前缀可复用，对应原文 Cache-Aware ~80% 命中叙事"
    )

    print("\n=== 3. 面试一句话 ===")
    print(
        "盲目压缩省了后面的字，却改了盖章线前的历史；"
        "Cache-Aware 只动断点后，线前指纹不变，才能又省 token 又保 cache。"
    )


if __name__ == "__main__":
    main()
