"""
文件：app/tools/category_insight.py ｜ 背景板（非简历重点，真实代码已在 globex-agent 实现）

基于品类知识库返回选购常识和爆款信息，不查询具体商品。目前读的是静态品类
卡片，正式生产版本应该接 RAG（第 13 章），用 OpenSearch 语义+全文混合检索。
"""
