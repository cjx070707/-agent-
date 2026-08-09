"""
文件：app/recall/reranker.py ｜ 背景板（非简历重点）
参考原文：globex/04_2_extract.md

三塔（bi-encoder）召回 Top-100 之后，用 cross-encoder Reranker 精排出
Top-10——因为 Query 和 Item 分别独立编码，向量生成时彼此看不见，存在物理
上限，Reranker 是这个上限的必备补丁。目前 globex-agent 里未实现。
"""
