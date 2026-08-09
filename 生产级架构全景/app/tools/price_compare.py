"""
文件：app/tools/price_compare.py ｜ 背景板（非简历重点，真实代码已在 globex-agent 实现）

用静态 FX 把跨平台候选归一到同一币种（CNY）后按价格排序，是候选合流后的
确定性计算，不需要 fork（不需要"思考"，也没有并行检索的必要）。
"""
