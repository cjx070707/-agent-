"""
文件：app/recall/ann.py ｜ ⏳ 简历④ 占位待补
参考原文：globex/04_1_extract.md

【占位说明】
这里将实现 Faiss（HNSW + IP）近似最近邻检索，把 towers.py 编码出的融合向量
拿去检索 Item 向量库，返回 Top-100 候选。会在学习模块④时补全完整讲解，包括
为什么召回层用 Faiss、应用层（长期记忆/RAG）用 OpenSearch，两套向量基础
设施的选型差异。

真实代码现状：globex-agent 里还没有这个文件。
"""
