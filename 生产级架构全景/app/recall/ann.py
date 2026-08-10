"""
文件：app/recall/ann.py
所属模块：★★★ 简历④ 三塔向量召回
参考原文：globex/04_1_extract.md、11item_search_fork_reproduction.md

【做什么】
AnnClient：用请求向量在 Item 向量索引上做近似最近邻，返回带 score 的商品 meta。

【解决的问题】
百万～千万 SKU 上暴力扫库不可行；需要高 QPS、低 P99 的纯向量检索。

【技术选型（背一句）】
- 召回层：Faiss（HNSW + IP）——训练好的三塔向量、批量重建索引、延迟极致
- 应用层记忆/RAG：OpenSearch——标量过滤、全文、混合检索更重要
- 度量：归一化向量 + Inner Product ≈ cosine

【红线：后过滤捞不回】
若 ANN 只取 Top-K 再按 platform 过滤，目标平台商品可能已被截断。
对策：over-fetch（top_k * N 再滤）或按平台分索引 / fork 子 Agent 分平台搜。

【和其他文件】
- towers.py：提供 emb
- item_search：platform / top_k / 双通道合并
- reranker.py（背景）：Top-100 之后精排，不替代 ANN

【面试抓手】
- 「被 ANN 丢掉的，过滤阶段救不回来」
- 索引文件 + meta.json 版本要和模型版本一起发版/回滚
"""

from __future__ import annotations

from typing import Protocol


class AnnClient(Protocol):
    """生产形态：faiss.read_index + meta；见原文 11 章骨架。"""

    def search(self, emb: list[float], top_k: int, platform: str) -> list[dict]: ...


def overfetch_hint(top_k: int, platforms: int = 1) -> int:
    """学习用提示：单平台过滤时建议多召倍数。

    原文骨架常见 top_k * 3；多平台混在一个索引时更要放大或拆索引。
    """
    return top_k * max(3, platforms)


# 全景学习说明：真实 Faiss 依赖 ANN_INDEX_PATH。
# 本地理解请跑 demos/demo_tri_tower_recall.py（暴力点积模拟 ANN）。
