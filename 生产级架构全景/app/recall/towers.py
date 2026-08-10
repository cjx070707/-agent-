"""
文件：app/recall/towers.py
所属模块：★★★ 简历④ 三塔向量召回
参考原文：globex/04_0_extract.md、11item_search_fork_reproduction.md

【做什么】
对外提供 TowerClient：在线编码 Query / User 向量。
Item 塔在离线灌库流水线里批量跑，不在每次 item_search 热路径上现算。

【解决的问题】
- 关键词召不回同义 / 场景意图
- 双塔无法单独建模「长期偏好 ≠ 本次 query」
- 让 item_search 拿到可 ANN 的请求向量

【三塔分工】
- Query 塔：即时意图（当前搜索词 + 可选 RAG 增强词）
- User 塔：长期偏好（点击/购买/画像文本）
- Item 塔：商品特征（标题/类目/属性/历史成交 query）——离线

【双通道（运行时，跟第 11 章）】
- 语义通道：只用 query_emb → ANN（始终开）
- 个性化通道：user_emb 与 query 融合后 → ANN（有 user_id 才开）
- 两路结果并集去重，由 item_search 编排（本文件只负责 encode）

【和其他文件】
- ann.py：吃 embedding，返回 Top-K meta
- app/tools/item_search.py：调 encode + search，拼 Candidate
- app/memory/*：文本偏好注入 prompt，≠ User 塔向量

【面试抓手】
- 「Agent 不直接搜向量，工具内部调 TowerClient」
- 融合可用加权：normalize(α·q + β·u)；工程上也可两路分别 ANN
"""

from __future__ import annotations

from typing import Protocol


class TowerClient(Protocol):
    """生产形态：HTTP 调独立 Tower 服务（见原文 11 章骨架）。"""

    async def encode_query(self, query: str) -> list[float]: ...

    async def encode_user(self, user_id: str) -> list[float]: ...


def fuse_query_user(
    query_vec: list[float],
    user_vec: list[float],
    alpha: float = 0.75,
    beta: float = 0.25,
) -> list[float]:
    """个性化请求向量：即时意图为主，长期偏好为辅。

    学习用纯 Python；生产可在服务端完成并 L2 normalize。
    """
    if len(query_vec) != len(user_vec):
        raise ValueError("query/user dim mismatch")
    mixed = [alpha * q + beta * u for q, u in zip(query_vec, user_vec)]
    norm = sum(x * x for x in mixed) ** 0.5 or 1e-12
    return [x / norm for x in mixed]


# 全景学习说明：真实 httpx 客户端依赖 TOWER_*_ENDPOINT，见 globex/11。
# 本地理解请跑 demos/demo_tri_tower_recall.py（玩具向量，无 HTTP）。
