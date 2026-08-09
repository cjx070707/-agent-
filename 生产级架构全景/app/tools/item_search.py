"""
文件：app/tools/item_search.py ｜ 背景板（非简历重点，真实代码已在 globex-agent 实现）

跨平台商品检索，是商品数据的入口，一次只搜一个平台（多平台并行靠简历①的
dispatch_tool fork 实现，不是这个工具自己并行）。正式生产版本的内部实现是
简历④的三塔向量召回（见 app/recall/towers.py），当前是静态目录 mock。
"""
