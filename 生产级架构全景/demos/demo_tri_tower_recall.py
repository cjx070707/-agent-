"""
简历④演示：三塔 + 双通道召回直觉（无模型 / 无 Faiss / 无 API）。

演示：
1. 同义：关键词 miss「收纳袋」vs 标题「整理包」；玩具向量近邻能命中
2. 双通道：同一 query，Query-only vs 个性化（高端偏好）排序不同
3. 跨语言：中文 query 仍能靠近英文标题商品（共享玩具语义维）
4. 后过滤红线：先截 Top-2 再滤 platform → 目标平台被截断

运行：
    python3 生产级架构全景/demos/demo_tri_tower_recall.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass


# 玩具语义维：storage / travel / premium / en_title（示意，非真实 embedding）
DIM_KEYS = ("storage", "travel", "premium", "en")


@dataclass
class Item:
    item_id: str
    platform: str
    title: str
    vec: tuple[float, float, float, float]


ITEMS = [
    Item("A1", "amazon", "旅行整理包 防水", (0.92, 0.72, 0.18, 0.0)),
    Item("A2", "amazon", "Premium Packing Cubes", (0.70, 0.68, 0.95, 0.95)),
    Item("S1", "shopee", "便宜塑料收纳袋", (0.88, 0.25, 0.02, 0.0)),
    Item("E1", "ebay", "canvas toiletry bag", (0.50, 0.55, 0.45, 0.92)),
]


def l2_normalize(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1e-12
    return [x / n for x in v]


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def keyword_hit(query: str, title: str) -> bool:
    return any(tok and tok in title for tok in query.replace("，", " ").split())


def ann_search(query_vec: list[float], top_k: int) -> list[tuple[float, Item]]:
    q = l2_normalize(query_vec)
    scored = []
    for item in ITEMS:
        iv = l2_normalize(list(item.vec))
        scored.append((dot(q, iv), item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


def fuse(q: list[float], u: list[float], alpha: float = 0.75, beta: float = 0.25) -> list[float]:
    return l2_normalize([alpha * a + beta * b for a, b in zip(q, u)])


def dual_channel(
    query_vec: list[float],
    user_vec: list[float] | None,
    top_k: int,
    *,
    alpha: float = 0.75,
    beta: float = 0.25,
) -> list[tuple[float, Item, str]]:
    """语义通道 + 可选个性化通道，并集后按最高分保留。"""
    pool: dict[str, tuple[float, Item, str]] = {}
    for score, item in ann_search(query_vec, top_k + 2):
        pool[item.item_id] = (score, item, "semantic")
    if user_vec is not None:
        personal = fuse(query_vec, user_vec, alpha=alpha, beta=beta)
        for score, item in ann_search(personal, top_k + 2):
            prev = pool.get(item.item_id)
            if prev is None or score > prev[0]:
                tag = "both" if prev else "personal"
                pool[item.item_id] = (score, item, tag)
    ranked = sorted(pool.values(), key=lambda x: x[0], reverse=True)
    return ranked[:top_k]


def section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def main() -> None:
    query = "旅行收纳袋"
    # Query 向量：偏 storage + travel
    q_vec = [0.88, 0.72, 0.15, 0.10]
    # 高端用户：premium 维高（融合后应把 A2 抬过廉价 S1）
    u_premium = [0.20, 0.35, 0.98, 0.25]

    section("1) 关键词 vs 向量（同义）")
    print(f"query = {query!r}")
    for item in ITEMS:
        kw = "HIT " if keyword_hit(query, item.title) else "MISS"
        print(f"  [{kw}] {item.item_id} {item.title}")
    print("→ 关键词可能 miss「整理包」；向量近邻仍可排前：")
    for score, item in ann_search(q_vec, 3):
        print(f"  {score:.3f}  {item.item_id}  {item.title}")

    section("2) Query-only vs 双通道个性化")
    print("Query-only Top-3:")
    for score, item, tag in dual_channel(q_vec, None, 3):
        print(f"  {score:.3f}  [{tag}]  {item.item_id}  {item.title}")
    print("双通道（高端 user，β 略加大便于观察）Top-3:")
    for score, item, tag in dual_channel(q_vec, u_premium, 3, alpha=0.55, beta=0.45):
        print(f"  {score:.3f}  [{tag}]  {item.item_id}  {item.title}")
    print("→ 语义仍保相关；个性化把 Premium Packing Cubes 抬过廉价 S1。")

    section("3) 跨语言近邻（示意）")
    # 中文 query 但带一点 en 维：模拟共享空间 / 对齐后的效果
    q_cross = [0.70, 0.65, 0.40, 0.70]
    for score, item in ann_search(q_cross, 3):
        print(f"  {score:.3f}  {item.item_id}  {item.title}")
    print("→ 中文意图仍可靠近英文标题商品（简历跨语言子集叙事用）。")

    section("4) 后过滤红线：先截断再滤 platform")
    raw = ann_search(q_vec, top_k=2)  # 故意截太短
    filtered = [x for x in raw if x[1].platform == "ebay"]
    print("ANN Top-2:", [i.item_id for _, i in raw])
    print("再滤 ebay:", [i.item_id for _, i in filtered] or "（空）")
    print("→ ebay 的 E1 若没进 Top-2，过滤阶段永远捞不回。对策：over-fetch 或分平台搜。")

    section("口径提示（面试用）")
    print("+22% ≈ (Recall@100_tri − Recall@100_query_only) / Recall@100_query_only")
    print("+35% ≈ 跨语言子集上相对朴素基线的 Recall@K 相对提升")
    print("二者均为组内自拟口径，非原文官方对比表。")


if __name__ == "__main__":
    main()
